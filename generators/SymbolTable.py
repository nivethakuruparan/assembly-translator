class SymbolTable():
    def __init__(self):
        self.variable_name_dict = dict()        

    def generate_name(self, variable_id, function_id=0): # function number (main = 0), # variable number
        return 'F' + str(function_id) + 'V' + str(variable_id)
    