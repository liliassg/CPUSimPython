import enum
from cpu.bytes import Byte, Byte8, Byte16, Byte32
import cpu.decoder as decoder

# EASY ACCESS ENUMS [DEPRECATED] [DO NOT USE] [OUTDATED]
class EOpcode(enum.IntEnum):
    """deprecated"""
    NOP = 0
    MOV = 1
    ADD = 2
    SUB = 3
    MUL = 4
    DIV = 5
    JNZ = 6
    JGZ = 7
    JNE = 8
    JGT = 9
    JMP = 10
    CALL = 11
    RET = 12
    JE = 13
    EQ = 14
    NEQ = 15
    LE = 16
    GE = 17
    LT = 18
    GT = 19
    SHL = 20
    SHR = 21
    AND = 22
    XOR = 23
    OR = 24
    XNOR = 25
    NOT = 26
    NAND = 27
    NOR = 28
    NUL = 29
    MOD = 30
    PUSH = 31
    POP = 32
    HALT = 33
class EInstruction(enum.IntEnum):
    """deprecated"""
    TickSleep = 0
    OpcodeMode = 1
    TargetRegisterMode = 2
    RegisterMode = 3
    ImmediateMode = 4
    MemoryMode = 5
    WithMemoryMode = 6
    Finish = 7
    Syscall = 8
    Address = 9
class EInstructionRegisters(enum.IntEnum):
    """deprecated"""
    REG0 = 0
    REG1 = 1
    REG2 = 2
    REG3 = 3
    REG4 = 4
    REG5 = 5
    REG6 = 6
    REG7 = 7
    REG8 = 8
    REG9 = 9
    REG10 = 10
    REG11 = 11
    REG12 = 12
    REG13 = 13
    REG14 = 14
    REG15 = 15
    REG16 = 16
    REG17 = 17
    REG18 = 18
    REG19 = 19
    REG20 = 20
    REG21 = 21
    REG22 = 22
    REG23 = 23
    REG24 = 24

# INSTRUCTION REGISTER CLASS
class InstructionRegisters:
    """
    example:
    IOP=MOV,IIM=3,IRE=2,IAL=0
    The Instruction Registers can only store 1 bitstring
    use the methods store() and retrieve() for production
    casm: mov &3, 3
    """
    def __init__(self, byte_handler: Byte):
        self.byte = byte_handler
        self.SIGNAL_IMMEDIATE = False
        self.SIGNAL_MEMORY = False
        self.SIGNAL_MEMORY_IMMEDIATE = False
        self.SIGNAL_SYSCALL = False
        self.SIGNAL_PTR = False
        self.IOP: str = ""
        """Instruction Register: Opcode"""
        self.IIM: str = ""
        """Instruction Register: Immediate"""
        self.IRE: str = ""
        """Instruction Register: Register"""
        self.SYS: str = ""
        """Instruction Register: Syscall"""
        self.ADR: str = ""
        """Instruction Register: Address"""
        self.BUF: list[str] = []
        """Instruction Register: Buffer"""


    def store(self, data, instruction: str):
        """store a value determined by the *instruction opcode* into the Instruction Register"""
        if isinstance(data, int): #integer
            data = self.byte.bitstring(data)
        if not self.byte.isbitstring(data) or not self.byte.isbitstring(instruction):
            return False
        # 1 -> Opcode
        if self.byte.convert(instruction) == 1:
            self.IOP = data
            return True
        # 2 -> DRG Signal
        if self.byte.convert(instruction) == 2:
            self.SIGNAL_IMMEDIATE = False
            return True
        # 3 -> Register
        if self.byte.convert(instruction) == 3:
            self.IRE = data
            return True
        # 4 -> Immediate        # in drg mode immediate will be interpreted as second register
        if self.byte.convert(instruction) == 4:
            self.IIM = data
            return True
        # 5 -> Memory           # the target is the memory, writes into reg
        if self.byte.convert(instruction) == 5:
            self.IRE = data
            self.SIGNAL_MEMORY = True
            return True
        # 6 -> With Memory      # The Immediate is a mnemory value, writes in immediate
        if self.byte.convert(instruction) == 6:
            self.IIM = data
            self.SIGNAL_MEMORY_IMMEDIATE = True
            return True
        # 8 -> Syscall
        if self.byte.convert(instruction) == 8:
            self.SYS = data
            self.SIGNAL_SYSCALL = True
            return True
        # 9 -> Address
        if self.byte.convert(instruction) == 9:
            self.ADR = data
            return True
        # 10 -> buf
        if self.byte.convert(instruction) == 10:
            self.BUF = data
            return True
        return False

    def retrieve(self, instruction: str):
        if not self.byte.isbitstring(instruction):
            return False
        ret:str
        if self.byte.convert(instruction) == 1:
            ret = self.IOP
            self.IOP = ""
            return ret
        # 2 -> Alu
        #if self.byte.convert(instruction) == 2:
        #    ret = self.IAL
        #    self.IAL = ""
        #    return ret
        # 3 -> Register
        if self.byte.convert(instruction) == 3:
            ret = self.IRE
            self.IRE = ""
            return ret
        # 4 -> Immediate
        if self.byte.convert(instruction) == 4:
            ret = self.IIM
            self.IIM = ""
            return ret
        # 8 -> syscall
        if self.byte.convert(instruction) == 8:
            ret = self.SYS
            self.SYS = ""
            return ret
        # 9 -> address
        if self.byte.convert(instruction) == 9:
            ret = self.ADR
            self.ADR = ""
            return ret
        # 10 -> buf
        if self.byte.convert(instruction) == 10:
            ret = self.BUF
            self.BUF = []
            return ret
        return False

    def reset(self):
        """reset all instruction SIGNAL flags to default"""
        self.SIGNAL_IMMEDIATE = False
        self.SIGNAL_MEMORY = False
        self.SIGNAL_MEMORY_IMMEDIATE = False
        self.SIGNAL_SYSCALL = False
        self.SIGNAL_PTR = False
        self.IIM = ""
        self.IOP = ""
        self.SYS = ""
        self.ADR = ""
        self.IRE = ""
        self.BUF :list[str]= []

# INSTRUCTION CLASS
class Instruction:
    """central Instruction resolver """
    def __init__(self, byte_handler: Byte, decode_handler: decoder.Decoder):
        self.byte = byte_handler
        self.decoder = decode_handler
        self.instructions = {
            0: "tsl", # tick sleep
            1: "imo", # instruction mode / opcode mode
            2: "drg", # target register mode
            3: "reg", # reg mode
            4: "imm", # immediate mode
            5: "mem", # memory mode
            6: "dme", # with memory mode
            7: "fin", # run exec
            8: "sys", # syscall
            9: "adr", # address mode
            10: "buf", # buffer mode
            11: "ptr", # pointer mode
            12: "sgn", # sign mode

        }
        self.syscalls = {
            0: "iip", # increment the instruction pointer by &15
            1: "dip", # decrement the instruction pointer by &15
            2: "ptv", # print a value to console
            3: "pti", # integer print
            4: "gip", # get instruction pointer -> &19
            5: "gsp", # get stack pointer -> &19
            6: "gpc", # get pc -> &19


            9: "key", # write keystate into return register &19, check key str by argument register &15

            14: "gpuint", # initialize a framebuffer &15 x, &16, y
            15: "gpupix", # tell gpu to draw a pixel    &15 x, &16 y, &17 col
            16: "gpurem", # tell gpu to remove a pixel  &15 x, &16 y
            17: "gpudis", # tell gpu to display the framebuffer
            18: "gpucls", # tell gpu to clear the console
            19: "gpuchr", # print a character to framebuffer
        }
        self.opcodes = {
            0: "nop",
            1: "mov",
            2: "add",
            3: "sub",
            4: "mul",
            5: "div",
            6: "jnz", # not zero
            7: "jgz", # greater zero
            8: "jne", # not equal
            9: "jgt", # greater then
            10: "jmp",
            11: "call",
            12: "ret",
            13: "je", # equal
            14: "eq",
            15: "neq",
            16: "le",
            17: "ge",
            18: "lt",
            19: "gt",
            20: "shl",
            21: "shr",
            22: "and",
            23: "xor",
            24: "or",
            25: "xnor",
            26: "not",
            27: "nand",
            28: "nor",
            29: "nul",
            30: "mod",
            31: "push",
            32: "pop",
            33: "hlt",
            34: "jlt", # lower then
            35: "jge", # greater or equal
            36: "jle", # lower or equal
            37: "jz", # is zero
            38: "inc",
            39: "dec",
            40: "exit",
            41: "buf",
            42: "wait", # do nothing for a while. the tsl tag holds the time
        }
        self.registers = {
            0: 0,
            1: 0,
            2: 0,
            3: 0,
            4: 0,
            5: 0,
            6: 0,
            7: 0,
            8: 0,
            9: 0,
            10: 0,
            11: 0,
            12: 0,
            13: 0,
            14: 0,
            15: 0,
            16: 0,
            17: 0,
            18: 0,
            19: 0,
            20: 0,
            21: 0,
            22: 0,
            23: 0,
            24: 0,
            25: 0,
            26: 0,
            27: 0,
            28: 0,
            29: 0,
            30: 0,
            31: 0,
            32: 0
        }
        self.reg = InstructionRegisters(self.byte)

        #init
        self.__gen_instruction__()
        self.__gen_opcode__()
        self.__gen_registers__()
        self.__gen_syscall__()


    def __gen_instruction__(self):
        """generate the instruction dict with the right bit width. can be changed from 8B/16B/32B"""
        instruction_bitstring = {}
        for num, keyword in self.instructions.items():
            instruction_bitstring[self.byte.bitstring(num)] = keyword
        self.instructions = instruction_bitstring
    def __gen_opcode__(self):
        """generate the opcode dict with the right bit width. can be changed from 8B/16B/32B"""
        opcode_bitstring = {}
        for num, keyword in self.opcodes.items():
            opcode_bitstring[self.byte.bitstring(num)] = keyword
        self.opcodes = opcode_bitstring
    def __gen_registers__(self):
        """generate the register dict with the right bit width. can be changed from 8B/16B/32B"""
        register_bitstring = {}
        for num, keyword in self.registers.items():
            register_bitstring[self.byte.bitstring(num)] = self.byte.bitstring(keyword)  # make register 0's to bitsring 0b0b0b0b0...
        self.registers = register_bitstring
    def __gen_syscall__(self):
        """generate the syscall dict with the right bit width. can be changed from 8B/16B/32B"""
        syscall_map = {}
        for num, keyword in self.syscalls.items():
            syscall_map[self.byte.bitstring(num)] = keyword
        self.syscalls = syscall_map

    def instruction(self, bitstring: str, from_bytes: bool = True):
        if from_bytes:
            return self.instructions.get(bitstring, None)
        else:
            for bytecode, value in self.instructions.items():
                if bitstring == value:
                    return bytecode
            return None

    def opcode(self, bitstring: str, from_bytes: bool = True):
        if from_bytes:
            return self.opcodes.get(bitstring, None)
        else:
            for bytecode, value in self.opcodes.items():
                if bitstring == value:
                    return bytecode
            return None

    def register(self, bitstring: str, from_bytes: bool = True):
        if from_bytes:
            return self.registers.get(bitstring, None)
        else:
            for bytecode, value in self.registers.items():
                if bitstring == value:
                    return bytecode
            return None

    def syscall(self, bitstring: str, from_bytes: bool = True):
        if from_bytes:
            return self.syscalls.get(bitstring, None)
        else:
            for bytecode, value in self.syscalls.items():
                if bitstring == value:
                    return bytecode
            return None
        
class Instruction8B(Instruction):
    """Instruction Resolver 8B. Has 32 Register"""
    def __init__(self):
        super().__init__(Byte8(), decoder.Decoder8B())

class Instruction16B(Instruction):
    """Instruction Resolver 16B. Has 40 Registers"""
    def __init__(self):
        super().__init__(Byte16(), decoder.Decoder16B())
        self.registers = {
            0: 0,
            1: 0,
            2: 0,
            3: 0,
            4: 0,
            5: 0,
            6: 0,
            7: 0,
            8: 0,
            9: 0,
            10: 0,
            11: 0,
            12: 0,
            13: 0,
            14: 0,
            15: 0,
            16: 0,
            17: 0,
            18: 0,
            19: 0,
            20: 0,
            21: 0,
            22: 0,
            23: 0,
            24: 0,
            25: 0,
            26: 0,
            27: 0,
            28: 0,
            29: 0,
            30: 0,
            31: 0,
            32: 0,
            33: 0,
            34: 0,
            35: 0,
            36: 0,
            37: 0,
            38: 0,
            39: 0,
            40: 0
        }

class Instruction32B(Instruction):
    """Instruction Resolver 32B Has. 48 Registers"""
    def __init__(self):
        super().__init__(Byte32(), decoder.Decoder32B())
        self.registers = {
            0: 0,
            1: 0,
            2: 0,
            3: 0,
            4: 0,
            5: 0,
            6: 0,
            7: 0,
            8: 0,
            9: 0,
            10: 0,
            11: 0,
            12: 0,
            13: 0,
            14: 0,
            15: 0,
            16: 0,
            17: 0,
            18: 0,
            19: 0,
            20: 0,
            21: 0,
            22: 0,
            23: 0,
            24: 0,
            25: 0,
            26: 0,
            27: 0,
            28: 0,
            29: 0,
            30: 0,
            31: 0,
            32: 0,
            33: 0,
            34: 0,
            35: 0,
            36: 0,
            37: 0,
            38: 0,
            39: 0,
            40: 0,
            41: 0,
            42: 0,
            43: 0,
            44: 0,
            45: 0,
            46: 0,
            47: 0,
            48: 0
        }