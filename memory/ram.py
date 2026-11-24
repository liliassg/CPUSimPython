from cpu.bytes import Byte, Byte8, Byte16, Byte32

class MemoryDevice:
    def __init__(self, byte_handler: Byte):
        self.byte = byte_handler
        self.digital = {}

    def write(self, bitstring_address: str, data: str):
        if not self.byte.isbitstring(bitstring_address) or not self.byte.isbitstring(data):
            return False
        self.digital[bitstring_address] = data
        return True

    def load(self, bitstring_address: str):
        if not self.byte.isbitstring(bitstring_address):
            return False
        # a cell nobody has written yet reads as zero. Raising here breaks every
        # "mov %N, imm", because writing a cell now reads it first.
        return self.digital.get(bitstring_address, self.byte.bitstring(0))



class MIO8B(MemoryDevice):
    def __init__(self):
        super().__init__(Byte8())

class MIO16B(MemoryDevice):
    def __init__(self):
        super().__init__(Byte16())

class MIO32B(MemoryDevice):
    def __init__(self):
        super().__init__(Byte32())