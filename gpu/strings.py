import cpu.bytes as byte
import cpu.decoder as decoder

class String:
    def __init__(self, byte_handler:byte.Byte, decoder_handler:decoder.Decoder):
        self.byte = byte_handler
        self.decoder = decoder_handler
        self.string_map = {
            0: "a",
            1: "A",
            2: "b",
            3: "B",
            4: "c",
            5: "C",
            6: "d",
            7: "D",
            8: "e",
            9: "E",
            10: "f",
            11: "F",
            12: "g",
            13: "G",
            14: "h",
            15: "H",
            16: "i",
            17: "I",
            18: "j",
            19: "J",
            20: "k",
            21: "K",
            22: "l",
            23: "L",
            24: "m",
            25: "M",
            26: "n",
            27: "N",
            28: "o",
            29: "O",
            30: "p",
            31: "P",
            32: "q",
            33: "Q",
            34: "r",
            35: "R",
            36: "s",
            37: "S",
            38: "t",
            39: "T",
            40: "u",
            41: "U",
            42: "v",
            43: "V",
            44: "w",
            45: "W",
            46: "x",
            47: "X",
            48: "y",
            49: "Y",
            50: "z",
            51: "Z",
            52: "ä",
            53: "Ä",
            54: "ö",
            55: "Ö",
            56: "ü",
            57: "Ü",
            58: "!",
            59: "\"",
            60: "§",
            61: "$",
            62: "%",
            63: "&",
            64: "/",
            65: "(",
            66: ")",
            67: "=",
            68: "?",
            69: "`",
            70: "#",
            71: "+",
            72: "-",
            73: ".",
            74: ",",
            75: "<",
            76: "@",
            77: "€",
            78: "{",
            79: "[",
            80: "]",
            81: "}",
            82: "\\",
            83: "~",
            84: "*",
            85: "_",
            86: ";",
            87: ">",
            88: "|",
            89: "°",
            90: "^",
            91: "0",
            92: "1",
            93: "2",
            94: "3",
            95: "4",
            96: "5",
            97: "6",
            98: "7",
            99: "8",
            100: "9",
            101: " ",
        }

        #init
        self.__gen_string__()

    def __gen_string__(self):
        """generate string map for the right byte size"""
        tmp = {}
        for k, v in self.string_map.items():
            tmp[self.byte.bitstring(k)] = v
        self.string_map = tmp

    def get(self, key: str, from_bytes:bool=True):
        if from_bytes:
            return self.string_map.get(key)
        for k, v in self.string_map.items():
            if key == v:
                return k
        return False



class String8B(String):
    def __init__(self):
        super().__init__(byte.Byte8(), decoder.Decoder8B())

class String16B(String):
    def __init__(self):
        super().__init__(byte.Byte16(), decoder.Decoder16B())

class String32B(String):
    def __init__(self):
        super().__init__(byte.Byte32(), decoder.Decoder32B())
