import ast

LabeledInstruction = tuple[str, str]

class FunctionDefinitionVisitor(ast.NodeVisitor):    

    def __init__(self, local_vars: dict()) -> None:
        super().__init__()
        self.__function_instructions = list()
        self.local_vars = local_vars

    def visit_FunctionDef(self, node):
        visit_function_body = FunctionBodyVisitor(self.local_vars, node.name)
        visit_function_body.visit(node)
        self.__function_instructions += visit_function_body.finalize()

    def finalize(self):
        return self.__function_instructions


class FunctionBodyVisitor(ast.NodeVisitor):

    def __init__(self, local_vars: dict(), function_name) -> None:
        super().__init__()
        self.__local_vars = local_vars
        self.__instructions = list()
        self.__record_instruction('NOP1', label=function_name)
        self.initialize()
        self.__return_id = 0

        self.__should_save = True
        self.__current_variable = None
        self.__visited_global_variables = set()
        self.__elem_id = 0

    def initialize(self):
        # allocate local variables to stack
        local_stack_count = 0
        for n, v in self.__local_vars.items():
            if v[1] == 'l':
                local_stack_count += 2
        
        if local_stack_count > 0:
            self.__record_instruction(f'SUBSP {local_stack_count},i')

    def finalize(self):
        # deallocate local variables to stack
        local_stack_count = 0
        for n, v in self.__local_vars.items():
            if v[1] == 'l':
                local_stack_count += 2
        
        if local_stack_count > 0:
            self.__record_instruction(f'ADDSP {local_stack_count},i')
        
        self.__instructions.append((None, 'RET'))
        return self.__instructions

    def visit_Assign(self, node):
        # remembering the name of the target
        self.__current_variable = node.targets[0].id
        # visiting the left part, now knowing where to store the result
        self.visit(node.value)
        if self.__should_save:
            is_local = self.check_local(self.__current_variable)
            if is_local[1]:
                self.__record_instruction(f'LDWA {is_local[0]},s')
            else:
                self.__record_instruction(f'LDWA {is_local[0]},d')
        else:
            self.__should_save = True
        self.__current_variable = None

    def visit_Constant(self, node):
        self.__record_instruction(f'LDWA {node.value},i')
            
    def visit_Name(self, node):
        is_local = self.check_local(node.id)
        if is_local[1]:
            self.__record_instruction(f'LDWA {is_local[0]},s')
        else:
            self.__record_instruction(f'LDWA {is_local[0]},d')

    def visit_BinOp(self, node):
        self.__access_memory(node.left, 'LDWA')
        if isinstance(node.op, ast.Add):
            self.__access_memory(node.right, 'ADDA')
        elif isinstance(node.op, ast.Sub):
            self.__access_memory(node.right, 'SUBA')
        else:
            raise ValueError(f'Unsupported binary operator: {node.op}')

    def visit_Return(self, node):
        if not isinstance(node.value, ast.Constant):
            is_local = self.check_local(node.value.id)
            if is_local[1]:
                self.__record_instruction(f'LDWA {is_local[0]},s')
            else:
                self.__record_instruction(f'LDWA {is_local[0]},d')
        else:
            self.__record_instruction(f'LDWA {node.value.value},d')

        self.__record_instruction(f'STWA RetVal{self.__return_id},s')
        self.__return_id += 1

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
                raise ValueError(f'Unsupported function call: { node.func.id}')

    def visit_While(self, node):
        loop_id = self.__identify()
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

    def __record_instruction(self, instruction, label = None):
        self.__instructions.append((label, instruction))

    def check_local(self, name):
        if 'm' + name in self.__local_vars:
            return ('m' + name, True)
        else:
            return (name, False)

    def __access_memory(self, node, instruction, label = None):
        if isinstance(node, ast.Constant):
            self.__record_instruction(f'{instruction} {node.value},i', label)
        elif isinstance(node, ast.Name) and self.__identify_constant(node.id): # EQUATE
            self.__record_instruction(f'{instruction} {node.id},i', label)
        else:
            is_local = self.check_local(node.id)
            if is_local[1]:
                self.__record_instruction(f'LDWA {is_local[0]},s')
            else:
                self.__record_instruction(f'LDWA {is_local[0]},d')

    def __identify(self):
        result = self.__elem_id
        self.__elem_id = self.__elem_id + 1
        return result

    def __identify_constant(self, name):
        if name.isupper() and name[0] == '_':
            return True
        return False
