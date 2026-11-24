from cpu.bytes import Byte, Byte8, Byte16, Byte32

class ALU:
    
    def __init__(self, byte_handler: Byte):
        self.byte = byte_handler

    def add(self, bitstring_a: str, bitstring_b: str):
        if not self.byte.isbitstring(bitstring_a) or not self.byte.isbitstring(bitstring_b):
            return False
        return self.byte.bitstring( (self.byte.convert(bitstring_a) + self.byte.convert(bitstring_b)) )

    def sub(self, bitstring_a: str, bitstring_b: str):
        if not self.byte.isbitstring(bitstring_a) or not self.byte.isbitstring(bitstring_b):
            return False
        return self.byte.bitstring( (self.byte.convert(bitstring_a) - self.byte.convert(bitstring_b)) )

    def mul(self, bitstring_a: str, bitstring_b: str):
        if not self.byte.isbitstring(bitstring_a) or not self.byte.isbitstring(bitstring_b):
            return False
        return self.byte.bitstring( (self.byte.convert(bitstring_a) * self.byte.convert(bitstring_b)) )

    def div(self, bitstring_a: str, bitstring_b: str):
        if not self.byte.isbitstring(bitstring_a) or not self.byte.isbitstring(bitstring_b):
            return False
        return self.byte.bitstring( (self.byte.convert(bitstring_a) // self.byte.convert(bitstring_b)) )

    def ddv(self, bitstring_a: str, bitstring_b: str):
        if not self.byte.isbitstring(bitstring_a) or not self.byte.isbitstring(bitstring_b):
            return False
        return self.byte.bitstring((self.byte.convert(bitstring_a) / self.byte.convert(bitstring_b)))

    def mod(self, bitstring_a: str, bitstring_b: str):
        if not self.byte.isbitstring(bitstring_a) or not self.byte.isbitstring(bitstring_b):
            return False
        return self.byte.bitstring((self.byte.convert(bitstring_a) % self.byte.convert(bitstring_b)))

    def shr(self, bitstring_a: str, bitstring_b: str):
        if not self.byte.isbitstring(bitstring_a) or not self.byte.isbitstring(bitstring_b):
            return False
        return self.byte.bitstring((self.byte.convert(bitstring_a) >> self.byte.convert(bitstring_b)))

    def shl(self, bitstring_a: str, bitstring_b: str):
        if not self.byte.isbitstring(bitstring_a) or not self.byte.isbitstring(bitstring_b):
            return False
        return self.byte.bitstring((self.byte.convert(bitstring_a) << self.byte.convert(bitstring_b)))

    def eq(self, bitstring_a: str, bitstring_b: str):
        if not self.byte.isbitstring(bitstring_a) or not self.byte.isbitstring(bitstring_b):
            return False
        return self.byte.bitstring((self.byte.convert(bitstring_a) == self.byte.convert(bitstring_b)))

    def neq(self, bitstring_a: str, bitstring_b: str):
        if not self.byte.isbitstring(bitstring_a) or not self.byte.isbitstring(bitstring_b):
            return False
        return self.byte.bitstring((self.byte.convert(bitstring_a) != self.byte.convert(bitstring_b)))

    def gt(self, bitstring_a: str, bitstring_b: str):
        if not self.byte.isbitstring(bitstring_a) or not self.byte.isbitstring(bitstring_b):
            return False
        return self.byte.bitstring((self.byte.convert(bitstring_a) > self.byte.convert(bitstring_b)))

    def ge(self, bitstring_a: str, bitstring_b: str):
        if not self.byte.isbitstring(bitstring_a) or not self.byte.isbitstring(bitstring_b):
            return False
        return self.byte.bitstring((self.byte.convert(bitstring_a) >= self.byte.convert(bitstring_b)))

    def lt(self, bitstring_a: str, bitstring_b: str):
        if not self.byte.isbitstring(bitstring_a) or not self.byte.isbitstring(bitstring_b):
            return False
        return self.byte.bitstring((self.byte.convert(bitstring_a) < self.byte.convert(bitstring_b)))

    def le(self, bitstring_a: str, bitstring_b: str):
        if not self.byte.isbitstring(bitstring_a) or not self.byte.isbitstring(bitstring_b):
            return False
        return self.byte.bitstring((self.byte.convert(bitstring_a) <= self.byte.convert(bitstring_b)))

class ALU8(ALU):
    def __init__(self):
        super().__init__(Byte8())

class ALU16(ALU):
    def __init__(self):
        super().__init__(Byte16())

class ALU32(ALU):
    def __init__(self):
        super().__init__(Byte32())