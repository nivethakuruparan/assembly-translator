import ast

LabeledInstruction = tuple[str, str]

class TopLevelProgram(ast.NodeVisitor):
    """We supports assignments and input/print calls"""
    
    def __init__(self, entry_point, local_vars) -> None:
        super().__init__()
        self.__instructions = list()
        self.__record_instruction('NOP1', label=entry_point)
        self.__should_save = True
        self.__current_variable = None
        self.__in_iteration = False
        self.__visited_global_variables = set()
        self.__elem_id = 0
        self.__local_var = local_vars

    def finalize(self):
        self.__instructions.append((None, '.END'))
        return self.__instructions

    ####
    ## Handling Assignments (variable = ...)
    ####

    def visit_Assign(self, node):
        # remembering the name of the target
        self.__current_variable = node.targets[0].id
        # visiting the left part, now knowing where to store the result
        self.visit(node.value)
        if self.__should_save:
            self.__record_instruction(f'STWA {self.__current_variable},d')
        else:
            self.__should_save = True
        self.__current_variable = None

    def visit_Constant(self, node):
        if self.__in_iteration: # if the variable is in a iteration, LDWA and STWA needed
            self.__record_instruction(f'LDWA {node.value},i')
            self.__visited_global_variables.add(self.__current_variable)
        elif self.__current_variable in self.__visited_global_variables: # if modifying value of variable, LDWA and STWA needed
            self.__record_instruction(f'LDWA {node.value},i')
        else: 
            self.__should_save = False
            self.__visited_global_variables.add(self.__current_variable)
    
    def visit_Name(self, node):
        self.__record_instruction(f'LDWA {node.id},d')

    def visit_BinOp(self, node):
        self.__access_memory(node.left, 'LDWA')
        if isinstance(node.op, ast.Add):
            self.__access_memory(node.right, 'ADDA')
        elif isinstance(node.op, ast.Sub):
            self.__access_memory(node.right, 'SUBA')
        else:
            raise ValueError(f'Unsupported binary operator: {node.op}')

    def visit_Call(self, node):
        match node.func.id:
            case 'int': 
                # Let's visit whatever is casted into an int
                self.visit(node.args[0])
            case 'input':
                # We are only supporting integers for now
                self.__record_instruction(f'DECI {self.__current_variable},d')
                self.__should_save = False # DECI already save the value in memory
            case 'print':
                # We are only supporting integers for now
                self.__record_instruction(f'DECO {node.args[0].id},d')
            case _:
                # check cases of functions
                # 1) the function either has a return value
                # 2) the function either has parameters

                has_params = False
                has_return = False
                param_variables = 0
                return_variables = 0

                for n, v in self.__local_var.items():
                    if v[2] == node.func.id and v[1] == 'p':
                        param_variables += 1
                        has_params = True 
                    elif v[2] == node.func.id and v[1] == 'r':
                        has_return = True 
                        return_variables += 1                   
                
                self.assign_function( node, has_params, has_return, param_variables, return_variables)
                    
    ####
    ## Handling While loops (only variable OP variable)
    ####

    def visit_While(self, node):
        loop_id = self.__identify()
        # entering iteration
        self.__in_iteration = True
        inverted = {
            ast.Lt:  'BRGE', # '<'  in the code means we branch if '>=' 
            ast.LtE: 'BRGT', # '<=' in the code means we branch if '>' 
            ast.Gt:  'BRLE', # '>'  in the code means we branch if '<='
            ast.GtE: 'BRLT', # '>=' in the code means we branch if '<'
            ast.NotEq: 'BREQ', # '!=' in the code means we branch if '=='
            ast.Eq: 'BRNE' # '==' in the code means we branch if '!='
        }
        # left part can only be a variable
        self.__access_memory(node.test.left, 'LDWA', label = f'test_{loop_id}')
        # right part can only be a variable
        self.__access_memory(node.test.comparators[0], 'CPWA')
        # Branching is condition is not true (thus, inverted)
        self.__record_instruction(f'{inverted[type(node.test.ops[0])]} end_l_{loop_id}')
        # Visiting the body of the loop
        for contents in node.body:
            self.visit(contents)
        self.__record_instruction(f'BR test_{loop_id}')
        # Sentinel marker for the end of the loop
        self.__record_instruction(f'NOP1', label = f'end_l_{loop_id}')
        # exiting iteration
        self.__in_iteration = False

    def visit_If(self, node):
        loop_id = self.__identify()
        inverted = {
            ast.Lt:  'BRGE', # '<'  in the code means we branch if '>=' 
            ast.LtE: 'BRGT', # '<=' in the code means we branch if '>' 
            ast.Gt:  'BRLE', # '>'  in the code means we branch if '<='
            ast.GtE: 'BRLT', # '>=' in the code means we branch if '<'
            ast.NotEq: 'BREQ', # '!=' in the code means we branch if '=='
            ast.Eq: 'BRNE' # '==' in the code means we branch if '!='
        }

        self.__access_memory(node.test.left, 'LDWA', label = f'if_{loop_id}') # LDWA
        self.__access_memory(node.test.comparators[0], 'CPWA') # CPWA

        if not node.orelse:
            self.__record_instruction(f'{inverted[type(node.test.ops[0])]} end_f_{loop_id}') # BRANCH to end if condition not met
        else:
            self.__record_instruction(f'{inverted[type(node.test.ops[0])]} else_f_{loop_id}') # BRANCH to else if condition not met
            
        for contents in node.body: # print content of if statement
            self.visit(contents)

        self.__record_instruction(f'BR end_f_{loop_id}') # statement done, BRANCH to end
        
        if node.orelse: # print content of else statement 
            self.__record_instruction(f'NOP1', label = f'else_f_{loop_id}') # end statement
            for contents in node.orelse:
                self.visit(contents)
            self.__record_instruction(f'BR end_f_{loop_id}') # statement done, BRANCH to end
        
        self.__record_instruction(f'NOP1', label = f'end_f_{loop_id}') # end statement

    ####
    ## Not handling function calls 
    ####

    def visit_FunctionDef(self, node):
        """We do not visit function definitions, they are not top level"""
        pass

    ####
    ## Helper functions to 
    ####

    def __record_instruction(self, instruction, label = None):
        self.__instructions.append((label, instruction))

    def __access_memory(self, node, instruction, label = None):
        if isinstance(node, ast.Constant):
            self.__record_instruction(f'{instruction} {node.value},i', label)
        elif isinstance(node, ast.Name) and self.__identify_constant(node.id): # EQUATE
            self.__record_instruction(f'{instruction} {node.id},i', label)
        else:
            self.__record_instruction(f'{instruction} {node.id},d', label)

    def __identify(self):
        result = self.__elem_id
        self.__elem_id = self.__elem_id + 1
        return result

    def __identify_constant(self, name):
        if name.isupper() and name[0] == '_':
            return True
        return False

    def assign_function(self, node, has_params, has_returns, num_params, num_returns):
        if has_params:
            self.__record_instruction(f'SUBSP {(num_params * 2) + (num_returns * 2)},i')
            stack_pointer = 0
            for i in range(len(node.args)):
                self.__record_instruction(f'LDWA {node.args[i].id},d')
                self.__record_instruction(f'STWA {stack_pointer},s')
                stack_pointer += 2
          
        self.__record_instruction(f'CALL {node.func.id}')

        if has_returns:
            self.__record_instruction(f'ADDSP {(num_params * 2)},i')
            self.__record_instruction(f'LDWA {(num_returns * 2) - 2},s')
            self.__record_instruction(f'STWA {node.args[0].id},d')
            self.__record_instruction(f'ADDSP {(num_returns * 2)},i')
            self.__should_save = False
