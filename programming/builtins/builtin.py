import os
import random

class Builtins:
    def __init__(self):
        self.builtins_path = "programming/builtins/"
        self.file_ending = ".descr"
        self.symbols = {}

    def collect_symbols(self, filename: str):
        """collect symbols for a file like gpu.casm"""
        file = filename.split(".")[0] + self.file_ending
        lines = []
        if not os.path.exists(file):
            raise FileNotFoundError(f"{filename} doesnt exist on that path")
        with open(file, "r") as data:
            raw_lines = data.readlines()
            for l in raw_lines:
                lines.append(l.rstrip("\r\n"))
            data.close()
        if len(lines) == 0:
            return None
        parsed = {}
        statement = None
        for line in lines:
            if len(line) == 0:
                continue
            if self.is_statement(line):
                statement = self.parse_statement(line, parsed)
                continue

            if self.is_call(line):
                self.parse_call(line, statement, parsed)
                statement = None
                continue
            self.parse_expression(line, statement, parsed)
            continue
        self.symbols[filename.split(".")[0]] = parsed
        return True

    def get_modules(self):
        all_module = []
        for k, v in self.symbols.items():
            all_module.append(k)
        return all_module

    def get_all_functions(self):
        functions = []
        for k, v in self.symbols.items():
            for a, b in v.items():
                functions.append(a)
        return functions

    def get_functions(self, module):
        all_functions = []
        for k, v in self.symbols[module].items():
            all_functions.append(k)
        return all_functions

    def get_function(self, module, name):
        """get the function symbol. name=high level name"""
        return self.symbols[module].get(name)["function"]

    def get_parameters(self, module, name):
        """get the parameter symbol. name=high level name"""
        return self.symbols[module].get(name)["parameters"]

    def get_parameter_count(self, module, name):
        count = 0
        for k, v in self.symbols[module].get(name)["parameters"].items():
            if k == "buffer":
                continue
            elif k == "bufferlen":
                continue
            count += len([0])
        return count

    def get_parameter(self, module, name: str, num: int):
        num = str(num)
        return self.symbols[module].get(name)["parameters"][num]

    def get_returns(self, module, name):
        return self.symbols[module].get(name)["returns"]

    def has_buffer(self, module, name):
        if len(self.symbols[module].get(name)["parameters"]["buffer"]) > 0:
            return True
        return False

    def get_buffer(self, module, name):
        return self.symbols[module].get(name)["parameters"]["buffer"]

    def get_buffer_len(self, module, name):
        return self.symbols[module].get(name)["parameters"]["bufferlen"]

    def is_register(self, parameter_data: list):
        return parameter_data[0].startswith("&")

    def is_memory(self, parameter_data: list):
        return parameter_data[0].startswith("%")

    def is_pointer(self, parameter_data: list):
        return parameter_data[0].startswith("%&")

    ################# PARSER ##################

    def is_statement(self, line: str):
        no_p = line.endswith(":")
        w_p = False
        try:
            w_p = line.split("->")[0]
            w_p = w_p.strip()
            w_p = w_p.endswith(":")
        except ValueError:
            pass
        return no_p or w_p is not False

    def parse_statement(self, line:str, parsed:dict):
        statement_name = ""
        returns = []
        try:
            statement_name, returns = line.split("->")
            statement_name = statement_name.strip()
            statement_name, _ = statement_name.split(":")
            returns = returns.strip()
            try:
                returns = returns.split(",")
            except ValueError:
                pass
        except ValueError:
            statement_name = line.split(":")[0]
        parsed[statement_name] = { "parameters": { "buffer" : [], "bufferlen": [] }, "function": "", "returns": returns if not len(returns) == 0 else None }
        return statement_name

    def is_call(self, line: str):
        return line.startswith("call=")

    def parse_call(self, line: str, name: str, parsed: dict):
        _, function_name = line.split("=")
        parsed[name]["function"] = function_name

    def parse_expression(self, line:str, name:str, parsed:dict):
        default = None
        try:
            parameter_index, register_index, default = line.split("=")
        except ValueError:
            parameter_index, register_index = line.split("=")
        spec = None

        if parameter_index.startswith("*"): # no param
            _, spec = parameter_index.split("<")
            spec, _ =  spec.split(">")
        else:
            if parameter_index.endswith(">"):  # is a specified argument
                parameter_index, spec = parameter_index.split("<")
                spec, _ = spec.split(">")


        if spec is not None:
            if spec == "buf":
                parsed[name]["parameters"]["buffer"].append([register_index, default])
                return
            elif spec == "buflen":
                parsed[name]["parameters"]["bufferlen"].append([register_index, default])
                return
        parsed[name]["parameters"][parameter_index] = [register_index, default]
        return

if __name__ == "__main__":

    builtin = Builtins()
    file = input("enter a builtin file: ")
    if file == "":
        file = ["gpu.casm", "io.casm"]
        for f in file:
            builtin.collect_symbols(f)
    else:
        builtin.collect_symbols(file)
    print("SYMBOLS=", builtin.symbols)
    for mod in builtin.get_modules():
        print(f"Module: {mod}")
        functions = builtin.get_functions(mod)
        print(f"FUNCTIONS={functions}")
        rnd_function = functions[random.randint(0, len(functions) - 1)]
        print(f"Random Function: {rnd_function}")
        parameter = builtin.get_parameter_count(mod, rnd_function)
        print(f"This function has {parameter} Parameters")
        returns = builtin.get_returns(mod, rnd_function)
        print(f"This function returns: {returns}")
