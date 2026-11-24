from cpu import cpu as central_processing_unit
from ssd import ssd as solid_state_drive
import gpu.gpu as graphical_processing_unit
import os # only used for loading the init.pc file

graphical_processing_unit.WINDOW = True # the frames go into a pyqt window


class Computer:
    
    CYCLE_CAP = 2000000
    """how many instructions one run may take. a game at 10 frames a second
    spends some 400 of them per frame, so this is a few minutes of playing"""

    def __init__(self, cpu_handler: central_processing_unit.CPU, architecture : int = None, name: str = "homemadepc"):
        self.cpu = cpu_handler
        self.ssd = solid_state_drive.SSD()
        
        self.arch = "ARCH" + str(architecture)
        self.name = name

        self.runtime_file = ""
        print(self.cpu.byte.BITLENGTH)
        if architecture == 8:
            self.runtime_file = "cpu/rom/runtime.8.cobj"
        if architecture == 16:
            self.runtime_file = "cpu/rom/runtime.16.cobj"
        if architecture == 32:
            self.runtime_file = "cpu/rom/runtime.32.cobj"
        print(f"starting {self.name} on {self.cpu.ARCH}\nloading runtime: {self.runtime_file}")
        print(f"keyboard: {self.cpu.keyboard.kind}"
              + ("" if self.cpu.keyboard.available
                 else "  - nothing will react to a key press"))
        """this is the init punch-card file to initialize the cpu"""
        total_bytes = 0
        with open(self.runtime_file, "r") as f:
            lines = f.readlines()
            for line in lines:
                instructions = line.split(" ")
                instructions[-1] = instructions[-1].rstrip("\n")
                total_bytes += len(instructions)
                self.cpu.sram.add(instructions)
            self.cpu.sram.__reset__()
        print(f"loaded {total_bytes} bytes in sram")
        self.cycle()

    def cycle(self):
        counter = 0
        # `not a or b` was true whenever there was no fetch error, whatever
        # the execute error said - both have to be clear to carry on
        while not (self.cpu.FETCH_ERROR or self.cpu.EXECUTE_ERROR):

            if self.cpu.HALTED:
                print("cpu halted")
                break


            self.cpu.fetch()
            if self.cpu.FETCH_ERROR:
                print(f"ERROR: CPU({self.cpu.ARCH}) occurred a fetch error: {self.cpu.ERROR_HINT}")
                break

            self.cpu.execute()
            if self.cpu.EXECUTE_ERROR:
                print(f"ERROR: CPU({self.cpu.ARCH}) occurred a execute error: {self.cpu.ERROR_HINT}")
                break

        self.display_registers(integer_mode=True)
        print(f"IP: {self.cpu.sram.instruction_pointer} - PC: {self.cpu.PC}")
        graphical_processing_unit.screen.hold() # the last frame stays until you close it

    def display_registers(self, integer_mode:bool = False):
        if not integer_mode:
            for reg_name, reg_val in self.cpu.register.register_opcodes.items():
                print(f"{reg_name}: {reg_val}")
            return
        else:
            for reg_name, reg_val in self.cpu.register.register_opcodes.items():
                print(f"{self.cpu.byte.convert(reg_name)}: {self.cpu.byte.convert(reg_val)}")
            return
        
        
def start_computer():
    available = [8, 16, 32]
    PC = None
    PCARCH = None
    try:
        PCARCH = int(input("what architecture should the pc run on? (8/16/32) > "))
    except Exception:
        print("invalid input, try again")
        return start_computer()
    if PCARCH not in available:
        print("this architecture does not exist")
        return start_computer()
    name = input("enter the name for your computer: ")
    if PCARCH == 8:
        PC = Computer(central_processing_unit.CPU8B(), 8, name)
    elif PCARCH == 16:
        PC = Computer(central_processing_unit.CPU16B(), 16, name)
    elif PCARCH == 32:
        PC = Computer(central_processing_unit.CPU32B(), 32, name)
    return 0
    
start_computer()
    