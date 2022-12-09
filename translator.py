import argparse
import ast
from visitors.GlobalVariables import GlobalVariableExtraction
from visitors.LocalVariable import LocalVariableExtraction
from visitors.TopLevelProgram import TopLevelProgram
from visitors.FunctionDefinition import FunctionDefinitionVisitor
from generators.StaticMemoryAllocation import StaticMemoryAllocation
from generators.StackMemoryAllocation import StackMemoryAllocation
from generators.EntryPoint import EntryPoint

def main():
    input_file, print_ast = process_cli()
    with open(input_file) as f:
        source = f.read()
    node = ast.parse(source)
    if print_ast:
        print(ast.dump(node, indent=2))
    else:
        process(input_file, node)
    
def process_cli():
    """"Process Command Line Interface options"""
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', help='filename to compile (.py)')
    parser.add_argument('--ast-only', default=False, action='store_true')
    args = vars(parser.parse_args())
    return args['f'], args['ast_only']

def process(input_file, root_node):
    print(f'; Translating {input_file}')
    global_extractor = GlobalVariableExtraction()
    global_extractor.visit(root_node)
    memory_alloc = StaticMemoryAllocation(global_extractor.results)

    local_extractor = LocalVariableExtraction()
    local_extractor.visit(root_node)
    stack_alloc = StackMemoryAllocation(local_extractor.results)

    print('; Branching to top level (tl) instructions')
    print('\t\tBR tl')
    memory_alloc.generate()

    if local_extractor.results:
        stack_alloc.generate()
        function_def = FunctionDefinitionVisitor(local_extractor.results)
        function_def.visit(root_node)
        epfd = EntryPoint(function_def.finalize())
        epfd.generate(True) 
        
    top_level = TopLevelProgram('tl', local_extractor.results)
    top_level.visit(root_node)
    ep = EntryPoint(top_level.finalize())
    ep.generate() 

if __name__ == '__main__':
    main()
