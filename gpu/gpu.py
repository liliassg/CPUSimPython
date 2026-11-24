import __main__
import gpu.strings as string
import gpu.screen as screen
import cpu.bytes as byte
import cpu.instruction as instruction
import os # used for cls
import sys # a frame is written in one piece

WINDOW = False
"""set it True before create() and the frames go into a pyqt window"""

ESC = chr(27)
HOME = ESC + "[H"
WIPE_LINE = ESC + "[K"
WIPE_BELOW = ESC + "[J"
CLEAR_ALL = ESC + "[2J" + HOME


def ansi_console():
    """switch on escape handling in the old windows console, once"""
    if os.name != "nt":
        return True
    try:
        import ctypes
        handle = ctypes.windll.kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        ctypes.windll.kernel32.SetConsoleMode(handle, mode.value | 0x0004) # virtual terminal
        return True
    except Exception:
        return False


ANSI = ansi_console()

class GPU:
    def __init__(self, byte_handler: byte.Byte, instruction_handler: instruction.Instruction, string_handler: string.String):
        self.byte = byte_handler
        self.instruction = instruction_handler
        self.string = string_handler

        self.framebuffer: list[list[list[str, int]]] = []
        """the framebuffer represents the frame that will been drawn. each index represents a line on x axis"""
        self.window = None
        """the pyqt window, if there is one. the console is used otherwise"""



    def create(self, x: int, y: int):
        """a framebuffer of y rows by x columns, every cell [glyph, colour]"""
        blank = self.string.get(" ", False)
        framebuffer = []
        for _ in range(y):
            row = []
            for _ in range(x):
                row.append([blank, 0]) # glyph word and colour
            framebuffer.append(row)
        self.framebuffer = framebuffer
        if WINDOW:
            self.window = screen.start(x, y)
        return True

    def pixel(self, x: int, y: int, col: int, pixel: str = None):
        if pixel is None:
            pixel = self.string.get("#", False)
        if x < 0 or y < 0:
            return False
        try:
            cell = self.framebuffer[y][x]
        except IndexError:
            return False
        # cells hold words, the way create fills them and the way gpuchr
        word = self.string.get(pixel, False)
        cell[0] = pixel if not word else word
        cell[1] = col
        return True

    def cls(self):
        if self.window is not None:
            return self.window.clear()
        if not ANSI:
            os.system("cls" if os.name == "nt" else "clear")
            return True
        sys.stdout.write(CLEAR_ALL)
        sys.stdout.flush()
        return True

    def show(self):
        if self.window is not None:
            return self.window.draw(self.glyphs())
        rows = ["".join(self.ascii(cell[0], cell[1]) for cell in row)
                for row in self.framebuffer]
        if ANSI and self.tty():
            picture = HOME + (WIPE_LINE + "\n").join(rows) + WIPE_LINE + WIPE_BELOW
        else:
            picture = "\n".join(rows) + "\n"
        sys.stdout.write(picture)
        sys.stdout.flush()
        return True

    def glyphs(self):
        rows = []
        for row in self.framebuffer:
            rows.append([[self.glyph(cell[0]), cell[1]] for cell in row])
        return rows

    def glyph(self, char: str):
        found = self.string.get(char)
        if found is None:
            return char if isinstance(char, str) and char else " "
        return found

    def ascii(self, char: str, col: int = 0):
        """one cell as terminal text. colur 0 is plain, anything else ansi 256"""
        glyph = self.glyph(char)
        if not col:
            return glyph
        return "\x1b[38;5;" + str(int(col) % 256) + "m" + glyph + "\x1b[0m"

    def pump(self):
        """let the window breathe while the cpu is waiting"""
        if self.window is None:
            return False
        return self.window.pump()

    def tty(self):
        try:
            return sys.stdout.isatty()
        except Exception:
            return False



class GPU8B(GPU):
    def __init__(self):
        super().__init__(byte.Byte8(), instruction.Instruction8B(), string.String8B())

class GPU16B(GPU):
    def __init__(self):
        super().__init__(byte.Byte16(), instruction.Instruction16B(), string.String16B())

class GPU32B(GPU):
    def __init__(self):
        super().__init__(byte.Byte32(), instruction.Instruction32B(), string.String32B())



def test():
    gpu = GPU8B()
    gpu.create(100, 100)
    print(gpu.framebuffer)
