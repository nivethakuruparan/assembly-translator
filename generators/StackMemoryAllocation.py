class StackMemoryAllocation():

    def __init__(self, local_vars: dict()) -> None:
        self.__local_vars = local_vars

    def generate(self):
        print('; Allocating local memory to stack')
        for n, v in self.__local_vars.items():
            print(f'{str(n+":"):<9}\t.EQUATE ' + str(v[0])) # reserving memory for local variable
