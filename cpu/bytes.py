
class Byte:
    """Byte Base Object. Do not use, expect Byte to be a Byte8 Object"""
    def __init__(self):
        
        self.BYTELENGTH: int= 1
        self.BITLENGTH: int = 8
        self.ENDIAN: str = "big"
        
        # CONSTANTS
        
        self.BITSTRING = 0
        
    ###### NonConst Methods 
        
    def convert(self, value):
        """convert an integer to a bitstring like 1b1b0b0b1b1b
            or a bitstring to an integer"""
        if isinstance(value, int):
            return self.bitstring(value, self.BITLENGTH)
        if not isinstance(value, str):
            return False
        return self.tobytes(value, return_bytes=False)
    
    def represent(self, integer: int, to_bytes: bool = False):
        return self.tobytes(self.bitstring(integer, self.BITLENGTH), to_bytes)
            
    def rawbits(self, num: int, byte_length: int = None):
        """return a bytes of an integer with the length = n"""
        if byte_length is None:
            byte_length = self.BYTELENGTH
        
        return num.to_bytes(length=byte_length)
    
    def tobytes(self, bitstring: str, return_bytes=True):
        """return a byte from a bitstring. can disassemble n bits"""
        byte_list = [b for b in bitstring.split("b") if b][::-1]
        total_num = 0
        n = 1
        for bit in byte_list:
            if bit == "1":
                total_num += n
            n = n * 2
        if return_bytes:
            return int(total_num).to_bytes(length=self.BYTELENGTH)
        return int(total_num)
    
    #### BitString Methods

    
    def bitstring(self, x, bit_length: int = None, endian: str = None):
        """make a bitsring from an int/list/bytes object"""
        if bit_length is None:
            bit_length = self.BITLENGTH
        if endian is None:
            endian = self.ENDIAN

        byte_string = ""
        if x is True:
            b = "1b"*bit_length
            if endian == "big":
                return b
            else:
                return b[::-1]
        if x is False:
            b= "0b"*bit_length
            if endian == "big":
                return b
            else:
                return b[::-1]
        if type(x) == type([]):
            for i in x:
                byte_string += str(i)
                
        if type(x) == type(int(0).to_bytes()):
            num = int(x)
            for _ in range(bit_length):
                byte_string += (str(num % 2))
                num //= 2
                
        if type(x) == type(int(3)):
            num = int(x)
            for _ in range(bit_length):
                byte_string += (str(num % 2))
                num //= 2
            
        if type(x) == type(""):
            if self.isbitstring(x):
                return x
        sep_bytes = ""
        for char in byte_string:
            if char != "1" and char != "0":
                return "0b"*bit_length
            sep_bytes = sep_bytes + char + "b"
        byte = sep_bytes[:-1]
        byte = byte[::-1]
        if endian == "little":
            return byte[::-1] + "b"
        return byte + "b"


    def flipendian(self, bitstring: str):
        return bitstring[::-1]
                
            
    ##### Check Methods
    
    
    def isnull(self, bitstring: str):
        """check if a bitstring is a null"""
        return self.convert(bitstring) == 0
    
    def isbitstring(self, x):
        if type(x) != type(""):
            return False
        if "b" not in x:
            return False
        return True
        
        

class Byte8(Byte):
    def __init__(self):
        super().__init__()

class Byte16(Byte):
    def __init__(self):
        super().__init__()
        self.BITLENGTH = 16
        self.BYTELENGTH = 2

class Byte32(Byte):
    def __init__(self):
        super().__init__()
        self.BITLENGTH = 32
        self.BYTELENGTH = 4
        
