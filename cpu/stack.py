import cpu.bytes as byte


class Stack:
    def __init__(self, byte_handler: byte.Byte, depth: int = 128):
        self.byte = byte_handler
        self.stack: list[int] = []
        self.DEPTH = depth

    def push(self, value: int):
        if len(self.stack) >= self.DEPTH:
            return False          # overflow
        self.stack.append(value)
        return True

    def pop(self):
        if not self.stack:
            return False          # underflow
        return self.stack.pop()

    def peek(self):
        return self.stack[-1] if self.stack else False

    def __depth__(self):
        return len(self.stack)

class Stack8B(Stack):
    def __init__(self):
        super().__init__(byte.Byte8())

class Stack16B(Stack):
    def __init__(self):
        super().__init__(byte.Byte16(), depth=256)

class Stack32B(Stack):
    def __init__(self):
        super().__init__(byte.Byte32(), depth=512)