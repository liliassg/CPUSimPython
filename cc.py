import sys
import os
import re
"""
file.cc

CC is a higher language then casm Assembly
code like:

#include "gpu.cc"
#define gpu_x 100
#define gpu_y 100

int main() {
    gpu::create(gpu_x, gpu_x);
    gpu::write("Hello World", gpu_x/2, gpu_x/2);
    gpu::show()
    return 0;
}

generates to:


.arch 32
.extern "builtins/gpu.casm"
.buf text_0 "Hello World"
_start:
    mov &15, 100
    mov &16, 100
    call _initialize_gpu_framebuffer
    mov &15, text_0_len
    mov &16, text_0
    mov &17, 50
    mov &18, 50
    mov &19, 0
    call _write_text_on_framebuffer
    exit 0

"""
import programming.builtins.builtin as builtins
import programming.cc.compiler as compiler
import programming.cc.parser as parser
import programming.cc.lexer as lexer
local_builtins_pt = "programming/builtins/"
builtin_cassembly_files = [
    local_builtins_pt+"gpu.casm", local_builtins_pt+"io.casm",
]

class CCLang:

    def __init__(self, parameters: list):
        self.builtins = builtins.Builtins()
        self.lexer = lexer.Lexer()
        self.parser = parser.Parser()
        self.compiler = compiler.Compiler()
        self.source = self.beside_me(parameters[0])
        self.output = parameters[1]
        self.flag = parameters[2]

        self.load_builtins()
        self.source = self.read_source()

    def beside_me(self, file:str):
        here = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(here, file)

    def load_builtins(self):
        for builtin in builtin_cassembly_files:
            print("loading symbols for: ", builtin)
            self.builtins.collect_symbols(builtin)

    def is_builtin_expression(self, expresson: str):
        """check if a token is a builtin expression, identified by the sector expression like module::function, no braces
        returns True if expression is builtin"""
        try:
            sectorname, function_name = expresson.split(self.lexer.tokens.get("sector"))
        except ValueError:
            return False
        if sectorname not in self.builtins.get_modules():
            raise Exception("no builtin module found with name "+sectorname)
        if function_name not in self.builtins.get_functions(sectorname):
            raise Exception("no builtin function found with name "+function_name+" in "+sectorname)
        return True


    def read_source(self):
        if not os.path.exists(self.source):
            raise FileNotFoundError("path doesnt exist: "+self.source)
        with open(self.source, "r") as read:
            lines = read.readlines()
            read.close()
            if len(lines) <= 0:
                raise Exception("File cant be empty!")
        return lines

def main():
    try:
        file = sys.argv[1]
        dest = sys.argv[2]
        try:
            flag = sys.argv[3]
        except IndexError:
            flag = None
    except IndexError:
        print("Argument Mismatch!\nusage:\n[CASM]\ncc myfile.cc out/mycasm.casm -casm\n[COBJ]\ncc myfile.cc out/mycobj.cobj")
        exit(1)
    cc = CCLang([file, dest, flag])
    print(f"processing file: {file}")
    print(cc.builtins.get_all_functions())
    print(cc.builtins.get_parameters("gpu", "write"))

if __name__ == "__main__":
    main()
