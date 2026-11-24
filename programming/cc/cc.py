import sys
"""
file.cc

CC is a higher language then casm Assembly
code like:

#include "gpu.cc"
#define gpu_x 100
#define gpu_y 100

int main() {
    gpu::create(gpu_x, gpu_x) video;
    video.write("Hello World", gpu_x/2, gpu_x/2);
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

class CCLang:

    def __init__(self, parameters: list):
        self.builtins = builtins.Builtins()
        self.lexer = lexer.Lexer()
        self.parser = parser.Parser()
        self.compiler = compiler.Compiler()

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

main()
