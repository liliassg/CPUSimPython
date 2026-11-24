from cpu.bytes import Byte, Byte8, Byte16, Byte32


class StaticRam:
    def __init__(self, byte_handler: Byte):
        self.byte = byte_handler
        self.instruction_pointer = 0
        self.instruction: list[list[str]] = []

    def get(self):
        """get the next instruction sequence from the instruction"""
        stack_data: list[str] = []
        try:
            stack_data = self.instruction[self.instruction_pointer]
        except IndexError:
            return False
        if stack_data is None or len(stack_data) == 0:
            return False
        self.instruction_pointer += 1
        return stack_data


    def store(self, sp_index: int, data: list[str]):
        """store data at a specific instruction pointer position\nif the sp index is higher than the actual instruction data, it creates empty instruction sequences"""
        current_stack_data_width = len(self.instruction)
        if sp_index >= current_stack_data_width:
            for i in range(sp_index - current_stack_data_width):
                self.instruction.append([])
            self.instruction.append(data)
            return True
        self.instruction[sp_index] = data
        return True

    def add(self, data: list[str]):
        """store data in the instruction"""
        self.store(self.instruction_pointer, data)
        self.__inc__()
        return True

    def at(self, sp_index: int):
        try:
            return self.instruction[sp_index]
        except IndexError:
            return False

    def rem(self):
        """remove the current instruction sequence from the instruction\ndecrements the instruction pointer"""
        try:
            self.instruction[self.instruction_pointer].clear()
        except IndexError:
            return False
        self.__dec__()
        return True

    def __edit__(self, sp_index: int):
        """set the instruction pointer to a specific position"""
        self.instruction_pointer = max(0, sp_index)

    def __inc__(self):
        """increment the instruction pointer"""
        self.instruction_pointer += 1

    def __dec__(self):
        """decrement the instruction pointer"""
        if self.instruction_pointer > 0:
            self.instruction_pointer -= 1

    def __reset__(self):
        """reset the instruction pointer"""
        self.instruction_pointer = 0

    def __clear__(self):
        """clear the instruction data"""
        self.instruction = []

    def __last__(self):
        """return the last instruction pointer number"""
        self.__dec__()
        num = self.instruction_pointer
        self.__inc__()
        return num


        
        
class StaticRam8B(StaticRam):
    def __init__(self):
        super().__init__(Byte8())
        
class StaticRam16B(StaticRam):
    def __init__(self):
        super().__init__(Byte16())
        
class StaticRam32B(StaticRam):
    def __init__(self):
        super().__init__(Byte32())