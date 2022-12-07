
class StaticMemoryAllocation():

    def __init__(self, global_vars: dict()) -> None:
        self.__global_vars = global_vars

    def generate(self):
        print('; Allocating Global (static) memory')
        for n, v in self.__global_vars.items():
            if v is None:
                print(f'{str(n+":"):<9}\t.BLOCK 2') # reserving memory for unknown value
            elif v is not None and n.isupper() and n[0] == '_':
                print(f'{str(n+":"):<9}\t.EQUATE ' + str(v)) # reserving memory for constant variable
            elif v is not None:
                print(f'{str(n+":"):<9}\t.WORD ' + str(v)) # reserving memory for known value
