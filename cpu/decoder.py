from cpu.bytes import Byte, Byte8, Byte16, Byte32

class Decoder:
    def __init__(self, byte_handler: Byte):
        self.byte = byte_handler



    def extend(self, bitstring: str, extend_value: int, endian: str=None):
        """extend a bitstring with n bits. 1000 [8] -> 10000000000"""
        if endian is None:
            endian = self.byte.ENDIAN

        if endian == 'little':
            for _ in range(extend_value):
                bitstring += "0b"
        elif endian == 'big':
            tmp = ""
            for _ in range(extend_value):
                tmp += "0b"
            bitstring = tmp + bitstring

        return bitstring

    def isset(self, bitstring: str, pos: int, endian: str=None):
        """check if a bit on a specific position is set. starting pos=1 endian=little: counting from left to right"""
        if endian is None:
            endian = self.byte.ENDIAN

        bits: list = bitstring.split("b")[:-1]
        count: int = 1
        if endian == "big":
            bits = bits[::-1]
        for bit in bits:
            if pos == count:
                return bit == "1"
            count += 1
        return False

    def flip(self, bitstring: str, pos: int, endian: str=None):
        if endian is None:
            endian = self.byte.ENDIAN
        bits: list = bitstring.split("b")[:-1]
        counter: int = 1
        if endian == 'big':
            bits = bits[::-1]
        for bit in bits:
            if pos == counter:
                if bit == "1":
                    bits[counter-1] = "0"
                if bit == "0":
                    bits[counter-1] = "1"
            counter += 1
        return self.byte.bitstring(bits, endian=endian)




class Decoder8B(Decoder):
    
    def __init__(self):
        super().__init__(Byte8())


class Decoder16B(Decoder):
    def __init__(self):
        super().__init__(Byte16())


class Decoder32B(Decoder):
    def __init__(self):
        super().__init__(Byte32())



