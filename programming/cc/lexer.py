
tokens = {
    "lcbrace":"{",
    "rcbrace": "}",
    "statement_end": ";",
    "lbrace": "(",
    "rbrace": ")",
    "seperator": ",",
    "return": "return",
    "assign": "=",
    "add": "+",
    "sub": "-",
    "div": "/",
    "mul": "*",
    "sector": "::",
    "include": "include",
    "string": "\"",
}

class Lexer:

    def __init__(self):
        self.tokens = tokens