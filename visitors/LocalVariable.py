import ast

class LocalVariableExtraction(ast.NodeVisitor):    

    def __init__(self) -> None:
        super().__init__()
        self.results = dict()
        self.stack_position = 0

    def visit_FunctionDef(self, node):
        # check for local variables in body
        visit_function_body = FunctionBodyVisitor()
        visit_function_body.visit(node)
        self.results.update(visit_function_body.results)

        # allocate return address 
        self.stack_position = visit_function_body.stack_position + 2

        # check for parameters
        for args in node.args.args:
            self.results['m' + str(args.arg)] = [self.stack_position, 'p']
            self.stack_position += 2

        # if there are None values in the dicitionary, retval is included
        for n, v in self.results.items():
            if v is None:
                self.results[n] = [self.stack_position, 'r']
                self.stack_position += 2

        
class FunctionBodyVisitor(ast.NodeVisitor):

    def __init__(self) -> None:
        super().__init__()
        self.results = dict()
        self.stack_position = 0
        self.return_id = 0

    def visit_Assign(self, node):
        if len(node.targets) != 1:
            raise ValueError("Only unary assignments are supported")

        # finding all variables in function body
        if node.targets[0].id not in self.results:
            self.results['m' + node.targets[0].id] = [self.stack_position, 'l']
            self.stack_position += 2            

    def visit_Return(self, node):
        self.results['RetVal' + str(self.return_id)] = None
        self.return_id += 1