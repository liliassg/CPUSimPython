from cpu.bytes import Byte, Byte8, Byte16, Byte32
registers = {
    0: "",
    1: "",
    2: "",
    3: "",
    4: "",
    5: "",
    6: "",
    7: "",
    8: "",
    9: "",
    10: "",
    11: "",
    12: "",
    13: "",
    14: "",
    15: "",
    16: "",
    17: "",
    18: "",
    19: "",
    20: "",
    21: "",
    22: "",
    23: "",
    24: "",
    25: "",
    26: "",
    27: "",
    28: "",
    29: "",
    30: "",
    31: "",
    32: "",
    33: "",
    34: "",
    35: "",
    36: "",
    37: "",
    38: "",
    39: "",
    40: "",
    41: "",
    42: "",
    43: "",
    45: "",
    46: "",
    47: "",
    48: ""

}

def generate_registers(byte_handler: Byte, opcode: dict):
    register_opcodes = {}
    for num, keyword in opcode.items():
        register_opcodes[byte_handler.bitstring(num)] = byte_handler.bitstring(0)
    return register_opcodes
class Register:
    
    def __init__(self, byte_handler: Byte):
        self.byte = byte_handler
        self.register_opcodes = generate_registers(byte_handler, registers)

    def get(self, bitstring_address: str):
        if not self.byte.isbitstring(bitstring_address):
            return False
        return self.register_opcodes.get(bitstring_address)

    def set(self, bitstring_address: str, bitstring_value: str):
        if not self.byte.isbitstring(bitstring_address) or not self.byte.isbitstring(bitstring_value):
            return False
        self.register_opcodes[bitstring_address] = bitstring_value
        return True
        
class Register8B(Register):
    def __init__(self):
        super().__init__(Byte8())
        
class Register16B(Register):
    def __init__(self):
        super().__init__(Byte16())
        
class Register32B(Register):
    def __init__(self):
        super().__init__(Byte32())