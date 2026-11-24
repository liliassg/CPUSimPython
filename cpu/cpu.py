import time

import cpu.bytes as byte
import cpu.decoder as decoder
import cpu.alu.alu as arithmeticlogicunit
import cpu.instruction as instruction_registers # Instruction Registers for Fetch -> Execute cycle
import cpu.register as cpu_registers # classic CPU Registers
import cpu.rom.sram as static_ram # CPU based static Ram used to store Instructions and other Important CPU data
import memory.ram as random_access_memory
import cpu.stack as stack
import gpu.gpu as graphical_processing_unit
import hid.keyboard as keyboard  # hid, not io: io is python's own module name and wins the import


class CPU:
    """CPU Base Class\nIn Production load Instruction Sequences into SRam and execute fetch() -> execute() in a loop"""
    def __init__(self, byte_handler: byte.Byte, decoder_handler: decoder.Decoder, alu_handler: arithmeticlogicunit.ALU,
                 cpu_register: cpu_registers.Register, instruction_register: instruction_registers.Instruction,
                 static_ram_handler: static_ram.StaticRam, memory_handler: random_access_memory.MemoryDevice,
                 stack_handler: stack.Stack, gpu_handler: graphical_processing_unit.GPU, keyboard_handler: keyboard.Keyboard
                 ):
        ###### CPU Handler
        self.byte = byte_handler
        self.decoder = decoder_handler
        self.alu = alu_handler
        self.register = cpu_register
        self.instruction = instruction_register
        self.sram = static_ram_handler
        self.ram = memory_handler
        self.stack = stack_handler
        self.gpu = gpu_handler
        self.keyboard = keyboard_handler
        ###### CPU Flags
            # Status Flags #
        self.FETCH_MODE = False
        self.EXECUTE_MODE = False
        self.HALTED = False
        ### self.JMP_BACK_ON: int = None
            # Error Flags #
        self.FETCH_ERROR = False
        self.EXECUTE_ERROR = False
        self.ERROR_HINT = ""
        ###### CPU Constants
        self._ARCHITECTURE = self.byte.BITLENGTH
        self._ENDIAN_FORMAT = self.byte.ENDIAN

        ###### Global Constants
        self.ARCH = f"CASM{self._ARCHITECTURE}:{self._ENDIAN_FORMAT}"
        """the architecture is the key for separate extern tools to extend the CPU. The CPU.ARCH format (CASM&:&) is used as identifier"""
        self.PC = 0
        """This is The Program Counter. It counts the execute cycles the cpu did"""
        self.EXIT_CODE: int = 0
        """the operand the program passed to exit; 0 when it ended with hlt"""
        ###### CPU Callee-Caller
        ###### Timing
        self.TICK_MS: float = 1.0
        """real milliseconds one tsl unit waits. set it to 0 and nothing waits"""
        self.TICK_LIMIT_MS: float = 5000.0
        """no single tsl may block the machine longer than this"""
        self.WAITED_MS: float = 0.0
        """how long this machine has waited in total, for whoever wants to know"""

        self.ARGUMENTR0 = self.byte.convert(15)
        self.ARGUMENTR1 = self.byte.convert(16)
        self.ARGUMENTR2 = self.byte.convert(17)
        self.ARGUMENTR3 = self.byte.convert(18)
        self.RETURNR0 = self.byte.convert(19)
        self.RETURNR1 = self.byte.convert(20)
        self.RETURNR2 = self.byte.convert(21)
        self.RETURNR3 = self.byte.convert(22)

        ###### CPU Configurations


    def __reset__(self):
        """reset CPU Status Flags to default"""
        self.FETCH_MODE = False
        self.EXECUTE_MODE = False
        self.FETCH_ERROR = False
        self.EXECUTE_ERROR = False
        self.HALTED = False
        self.ERROR_HINT = ""
        ### self.JMP_BACK_ON = None

    def execute(self):
        """
        Execute data from instruction registers
        """
        self.EXECUTE_MODE = True
        self.FETCH_MODE = False
        if self.instruction.reg.SIGNAL_SYSCALL:
            status = self.syscall(self.instruction.reg.SYS)
            if not status:
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu syscall error"
                return
            self.PC += 1
            return
        opcode = self.instruction.reg.retrieve(self.byte.bitstring(1))
        """this is the opcode value. is used to determine the arithmetic operation within the alu"""
        register = self.instruction.reg.retrieve(self.byte.bitstring(3))
        """this is the register value. is interpreted as from_register"""
        immediate = self.instruction.reg.retrieve(self.byte.bitstring(4))
        """this is the immediate value, also can be interpreted as register 2 or as memory value"""
        address = self.instruction.reg.retrieve(self.byte.bitstring(9))
        """this is the value the cpu will set the instruction pointer to"""
        buffer = self.instruction.reg.retrieve(self.byte.bitstring(10))
        """this value is a buffer value that gets written into ram"""
        # single opcodes
        if self.instruction.opcode(opcode) == "jmp":
            self.sram.__edit__(self.byte.convert(address))
            self.__inc_pc__()
            return
        elif self.instruction.opcode(opcode) == "call":
            if not self.stack.push(self.sram.instruction_pointer):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu stack overflow"
                return
            self.sram.__edit__(self.byte.convert(address))
            self.__inc_pc__()
            return
        elif self.instruction.opcode(opcode) == "ret":
            back = self.stack.pop()
            if back is False:
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu stack underflow"
                return
            self.sram.__edit__(back)
            self.__inc_pc__()
            return
        elif self.instruction.opcode(opcode) == "wait":
            # the waiting already happened in fetch, this only moves on
            self.__inc_pc__()
            return
        elif self.instruction.opcode(opcode) == "hlt":
            self.HALTED = True
            self.__inc_pc__()
            return
        elif self.instruction.opcode(opcode) == "exit":
            # exit takes a single source operand and no destination register:
            #   exit 4    imo exit imm 4 fin
            #   exit &4   imo exit drg imm 4 fin
            #   exit %3   imo exit dme imm 3 fin
            code: str
            if self.instruction.reg.SIGNAL_MEMORY_IMMEDIATE:
                code = self.ram.load(self.__ptr_src__(immediate))
            elif not self.instruction.reg.SIGNAL_IMMEDIATE:
                code = self.register.get(immediate)
            else:
                code = immediate
            if code is False or code is None or not self.byte.isbitstring(code):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu exit operand error"
                return
            self.EXIT_CODE = self.byte.convert(code)
            self.HALTED = True
            self.__inc_pc__()
            return
        elif self.instruction.opcode(opcode) == "buf":
            buf_len = len(buffer) # not using imm
            if buf_len <= 0:
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu buf underflow error"
                return
            buf_start = self.byte.convert(self.__ptr_dest__(register))
            if not isinstance(buf_start, int):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu buf address error"
                return
            for n in range(buf_len):
                self.ram.write(self.byte.convert(n + buf_start), buffer[n])
            self.__inc_pc__()
            return
        # single opcodes end
        to_register: str = ""
        """this value will be written to the register or memory if reg.SIGNAL_MEMORY is set"""
        from_register: str = ""
        """this value is the register to work with. for example if you do add &4, 30. This value holds the data of &4 to add 30 in the instruction logic"""
        operand: str = ""
        """this value is the data you use for operation, for example mul &12, 6: from_register holds 12, this value holds 6\nNotice This Value can be used as immediate value, register value and memory value\n
        example: mov %3, &4: immediate: 3, from_register: 4, operand: value of reg(3)\n
        example: mov %255, %244: """
        # print(f"debug data: opcode={opcode}, register={register}, immediate={immediate}")

        ####################    EXECUTE     ####################
        if self.instruction.reg.SIGNAL_IMMEDIATE and self.instruction.reg.SIGNAL_MEMORY_IMMEDIATE:
            self.EXECUTE_ERROR = True
            self.ERROR_HINT = "cpu multi-flag error"
            return
        if self.instruction.reg.SIGNAL_IMMEDIATE:
            # Immediate Signal: immediate represents an Immediate
            operand = immediate
            if self.instruction.reg.SIGNAL_MEMORY:
                from_register = self.ram.load(self.__ptr_dest__(register))
            else:
                from_register = self.register.get(register)
            if from_register is False or from_register is None or not self.byte.isbitstring(from_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu register load error"
                return
        elif self.instruction.reg.SIGNAL_MEMORY_IMMEDIATE:
            # Memory Immediate Signal tells immediate represents a memory value
            operand = self.ram.load(self.__ptr_src__(immediate))
            if self.instruction.reg.SIGNAL_MEMORY:
                from_register = self.ram.load(self.__ptr_dest__(register))
            else:
                from_register = self.register.get(register)
            if operand is False or operand is None or not self.byte.isbitstring(operand):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu ram load error"
                return
        else:
            # no Memory signal, Immediate represents a register
            # pyrefly: ignore[bad-argument-type, bad-assignment]
            if self.instruction.reg.SIGNAL_MEMORY:
                from_register = self.ram.load(self.__ptr_dest__(register))
            else:
                from_register = self.register.get(register)
            if from_register is False or from_register is None or not self.byte.isbitstring(from_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu register load error"
                return
            # pyrefly: ignore[bad-argument-type, bad-assignment]
            operand = self.register.get(immediate)
            if operand is False or operand is None or not self.byte.isbitstring(operand):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu register load error"
                return

        ##### Instruction Logic

        ### Non Register Ops
        if self.instruction.opcode(opcode) == "mov":     # mov &3, 10
            if self.instruction.reg.SIGNAL_IMMEDIATE:
                to_register = immediate
            elif self.instruction.reg.SIGNAL_MEMORY_IMMEDIATE:
                to_register = self.ram.load(self.__ptr_src__(immediate))
            else:
                to_register = self.register.get(immediate)

        ## conditions
        elif self.instruction.opcode(opcode) == "je":   # je &0, &1
            is_eq = self.alu.eq(from_register, operand)
            if not self.byte.isnull(is_eq):
                self.sram.__edit__(self.byte.convert(address))
            self.__inc_pc__()
            return
        elif self.instruction.opcode(opcode) == "jne":   # jne &0, &1
            is_eq = self.alu.eq(from_register, operand)
            if self.byte.isnull(is_eq):
                self.sram.__edit__(self.byte.convert(address))
            self.__inc_pc__()
            return
        elif self.instruction.opcode(opcode) == "jgt":
            is_greater = self.alu.gt(from_register, operand)
            if not self.byte.isnull(is_greater):
                self.sram.__edit__(self.byte.convert(address))
            self.__inc_pc__()
            return
        elif self.instruction.opcode(opcode) == "jlt":
            is_lower = self.alu.lt(from_register, operand)
            if not self.byte.isnull(is_lower):
                self.sram.__edit__(self.byte.convert(address))
            self.__inc_pc__()
            return
        elif self.instruction.opcode(opcode) == "jle":
            is_lower = self.alu.lt(from_register, operand)
            is_equal = self.alu.eq(from_register, operand)
            if not self.byte.isnull(is_equal) or not self.byte.isnull(is_lower):
                self.sram.__edit__(self.byte.convert(address))
            self.__inc_pc__()
            return
        elif self.instruction.opcode(opcode) == "jge":
            is_greater = self.alu.gt(from_register, operand)
            is_equal = self.alu.eq(from_register, operand)
            if not self.byte.isnull(is_equal) or not self.byte.isnull(is_greater):
                self.sram.__edit__(self.byte.convert(address))
            self.__inc_pc__()
            return
        elif self.instruction.opcode(opcode) == "jnz":
            is_zero = self.alu.eq(from_register, self.byte.bitstring(0))
            if self.byte.isnull(is_zero):
                self.sram.__edit__(self.byte.convert(address))
            self.__inc_pc__()
            return
        elif self.instruction.opcode(opcode) == "jz":
            is_zero = self.alu.eq(from_register, self.byte.bitstring(0))
            if not self.byte.isnull(is_zero):
                self.sram.__edit__(self.byte.convert(address))
            self.__inc_pc__()
            return
        ## conditions end

        ### Register ops
        elif self.instruction.opcode(opcode) == "add":   # add &3, 10
            to_register = self.alu.add(from_register, operand)
            if to_register is False or to_register is None or not self.byte.isbitstring(to_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu alu add operation error"
                return
        elif self.instruction.opcode(opcode) == "sub":   # sub &3, 10
            to_register = self.alu.sub(from_register, operand)
            if to_register is False or to_register is None or not self.byte.isbitstring(to_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu alu sub operation error"
                return
        elif self.instruction.opcode(opcode) == "mul":   # mul &3, 10
            to_register = self.alu.mul(from_register, operand)
            if to_register is False or to_register is None or not self.byte.isbitstring(to_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu alu mul operation error"
                return
        elif self.instruction.opcode(opcode) == "div":   # div &3, 10
            to_register = self.alu.div(from_register, operand)
            if to_register is False or to_register is None or not self.byte.isbitstring(to_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu alu div operation error"
                return
        elif self.instruction.opcode(opcode) == "ddv":   # ddv &3, 10
            to_register = self.alu.ddv(from_register, operand)
            if to_register is False or to_register is None or not self.byte.isbitstring(to_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu alu ddv operation error"
                return
        elif self.instruction.opcode(opcode) == "shr":   # shr &3, 10
            to_register = self.alu.shr(from_register, operand)
            if to_register is False or to_register is None or not self.byte.isbitstring(to_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu alu shr operation error"
                return
        elif self.instruction.opcode(opcode) == "shl":   # shl &3, 10
            to_register = self.alu.shl(from_register, operand)
            if to_register is False or to_register is None or not self.byte.isbitstring(to_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu alu shl operation error"
                return
        elif self.instruction.opcode(opcode) == "eq":    # eq &3, 10
            to_register = self.alu.eq(from_register, operand)
            if to_register is False or to_register is None or not self.byte.isbitstring(to_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu alu eq operation error"
                return
        elif self.instruction.opcode(opcode) == "neq":   # neq &3, 10
            to_register = self.alu.neq(from_register, operand)
            if to_register is False or to_register is None or not self.byte.isbitstring(to_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu alu neq operation error"
                return
        elif self.instruction.opcode(opcode) == "gt":    # gt &3, 10
            to_register = self.alu.gt(from_register, operand)
            if to_register is False or to_register is None or not self.byte.isbitstring(to_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu alu gt operation error"
                return
        elif self.instruction.opcode(opcode) == "lt":    # lt &3, 10
            to_register = self.alu.lt(from_register, operand)
            if to_register is False or to_register is None or not self.byte.isbitstring(to_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu alu lt operation error"
                return
        elif self.instruction.opcode(opcode) == "le":    # le &3, 10
            to_register = self.alu.le(from_register, operand)
            if to_register is False or to_register is None or not self.byte.isbitstring(to_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu alu le operation error"
                return
        elif self.instruction.opcode(opcode) == "ge":    # ge &3, 10
            to_register = self.alu.ge(from_register, operand)
            if to_register is False or to_register is None or not self.byte.isbitstring(to_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu alu ge operation error"
                return
        elif self.instruction.opcode(opcode) == "mod":
            to_register = self.alu.mod(from_register, operand)
            if to_register is False or to_register is None or not self.byte.isbitstring(to_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu alu mod operation error"
                return
        elif self.instruction.opcode(opcode) == "inc":
            to_register = self.byte.bitstring(self.byte.convert(from_register) + 1)
        elif self.instruction.opcode(opcode) == "dec":
            to_register = self.byte.bitstring(self.byte.convert(from_register) - 1)
        else:
            self.EXECUTE_ERROR = True
            self.ERROR_HINT = "cpu opcode overflow: possible not implemented error"

        # Writeback to register
        if self.instruction.reg.SIGNAL_MEMORY:
            # in SIGNAL_MEMORY register value represents a memory value
            # print(f"writing to memory[{register}]: {to_register}")
            if not self.ram.write(self.__ptr_dest__(register), to_register):
                self.EXECUTE_ERROR = True
                self.ERROR_HINT = "cpu ram write error"
            self.__inc_pc__()
            return
        status = self.register.set(register, to_register)
        if not status:
            self.EXECUTE_ERROR = True
            self.ERROR_HINT = "cpu register write error"
        self.__inc_pc__()
        return
    def fetch(self):
        """fetch instructions from static ram"""
        self.FETCH_MODE = True
        self.EXECUTE_MODE = False
        self.instruction.reg.reset()

       ### # when jmp happend. read cpu signal for jmp_back
       ### if self.JMP_BACK_ON is not None:
       ###     if self.JMP_BACK_ON == self.sram.instruction_pointer:
       ###         self.sram.instruction_pointer = self.stack.return_address
       ###         self.JMP_BACK_ON = None
        instruction: list[str] = self.sram.get()
        if not instruction or instruction is None:
            self.FETCH_ERROR = True
            self.ERROR_HINT = "cpu sram fetch error. possible null byte sequence"
            return False
        """get the next instruction bytes from sram"""
        mode: int = 0
        """
        mode determines the fetch cycle:
        0: Instruction Mode
        1: Opcode Mode
        """
        target: int = 0
        """
        target determines the fetch cycle command:
        0: opcode
        1: reg
        2: immediate
        3: syscall
        4: adr
        5: buf
        6: tsl
        """
        got_fin = False
        got_opc = False
        got_reg = False
        got_imm = False
        got_tsl = False
        got_drg = False
        got_mem = False
        got_dme = False
        got_sys = False
        got_adr = False
        got_buf = False
        got_ptr = False
        buf_counter = -1
        for instr in instruction:
            if mode == 1:
                mode = 0
                if target == 0:
                    self.instruction.reg.IOP = instr
                    continue
                elif target == 1:
                    self.instruction.reg.IRE = instr
                    continue
                elif target == 2:
                    self.instruction.reg.IIM = instr
                    continue
                elif target == 3:
                    self.instruction.reg.SYS = instr
                elif target == 4:
                    self.instruction.reg.ADR = instr
                elif target == 5:
                    self.instruction.reg.BUF.append(instr)
                    buf_counter -= 1
                    if buf_counter > 0:
                        mode = 1
                elif target == 6:
                    # wait as long as instr says, in ticks. normal ops still
                    # run: the waiting happens while the instruction is being
                    # fetched, so whatever carries the tsl still executes
                    ticks = self.byte.convert(instr)
                    if not isinstance(ticks, int) or ticks < 0:
                        self.FETCH_ERROR = True
                        self.ERROR_HINT = "cpu tsl fetch error: no tick count"
                        return False
                    waited = min(ticks * self.TICK_MS, self.TICK_LIMIT_MS)
                    if waited > 0:
                        self.WAITED_MS += waited
                        self.__hold__(waited)
                continue
            else:
                # 0: TickSleep
                if self.instruction.instruction(instr, True) == "tsl":
                    if got_tsl:
                        self.FETCH_ERROR = True
                        self.ERROR_HINT = "cpu tsl fetch error: invalid instruction sequence"
                        return False
                    got_tsl = True
                    mode = 1
                    target = 6
                    continue
                # 1: Opcode Mode
                elif self.instruction.instruction(instr, True) == "imo":
                    if got_opc:
                        self.FETCH_ERROR = True
                        self.ERROR_HINT = "cpu opc fetch error: invalid instruction sequence"
                    got_opc = True
                    mode = 1
                    target = 0
                    continue
                # Register
                elif self.instruction.instruction(instr, True) == "reg":
                    if got_reg:
                        self.FETCH_ERROR = True
                        self.ERROR_HINT = "cpu reg fetch error: invalid instruction sequence"
                    got_reg = True
                    mode = 1
                    target = 1
                    continue
                # 3: DRG Mode
                elif self.instruction.instruction(instr) == "drg":
                    if got_drg:
                        self.FETCH_ERROR = True
                        self.ERROR_HINT = "cpu drg fetch error: invalid instruction sequence"
                    got_drg = True
                    self.instruction.reg.SIGNAL_IMMEDIATE = False
                    continue
                # 4: Immediate
                elif self.instruction.instruction(instr, True) == "imm":
                    if got_imm:
                        self.FETCH_ERROR = True
                        self.ERROR_HINT = "cpu imm fetch error: invalid instruction sequence"
                    got_imm = True
                    mode = 1
                    target = 2
                    continue
                # 5: Memory mode
                elif self.instruction.instruction(instr, True) == "mem":
                    if got_mem:
                        self.FETCH_ERROR = True
                        self.ERROR_HINT = "cpu mem fetch error: invalid instruction sequence"
                    got_mem = True
                    self.instruction.reg.SIGNAL_MEMORY = True
                    continue
                # 6: With Memory Mode
                elif self.instruction.instruction(instr, True) == "dme":
                    if got_dme:
                        self.FETCH_ERROR = True
                        self.ERROR_HINT = "cpu dme fetch error: invalid instruction sequence"
                    got_dme = True
                    self.instruction.reg.SIGNAL_MEMORY_IMMEDIATE = True
                    continue
                # 7: Finish mode
                elif self.instruction.instruction(instr, True) == "fin":
                    if got_fin:
                        self.FETCH_ERROR = True
                        self.ERROR_HINT = "cpu fin fetch error: invalid instruction sequence"
                    got_fin = True
                    if not got_drg and not got_dme:
                        self.instruction.reg.SIGNAL_IMMEDIATE = True
                    return True
                # 8: Syscall
                elif self.instruction.instruction(instr, True) == "sys":
                    if got_sys:
                        self.FETCH_ERROR = True
                        self.ERROR_HINT = "cpu sys fetch error: invalid instruction sequence"
                        return False
                    got_sys = True
                    self.instruction.reg.SIGNAL_SYSCALL = True
                    mode = 1
                    target = 3
                # 9: Address mode
                elif self.instruction.instruction(instr, True) == "adr":
                    if got_adr:
                        self.FETCH_ERROR = True
                        self.ERROR_HINT = "cpu adr fetch error: invalid instruction sequence"
                        return False
                    got_adr = True
                    mode = 1
                    target = 4
                # 10: Buffer Mode
                elif self.instruction.instruction(instr, True) == "buf":
                    if got_buf:
                        self.FETCH_ERROR = True
                        self.ERROR_HINT = "cpu buf fetch error: invalid instruction sequence"
                        return False
                    got_buf = True
                    # imm says how many words follow, so it has to be in
                    # already - the assembler emits imm before buf
                    buf_counter = self.byte.convert(self.instruction.reg.IIM)
                    if not isinstance(buf_counter, int) or buf_counter <= 0:
                        self.FETCH_ERROR = True
                        self.ERROR_HINT = ("cpu buf fetch error: imm must say "
                                           "how many words follow")
                        return False
                    mode = 1
                    target = 5
                # 11: PTR Mode
                elif self.instruction.instruction(instr, True) == "ptr":
                    if got_ptr:
                        self.FETCH_ERROR = True
                        self.ERROR_HINT = "cpu ptr error: invalid instruction sequence"
                        return False
                    got_ptr = True
                    self.instruction.reg.SIGNAL_PTR = True
                else:
                    self.FETCH_ERROR = True
                    self.ERROR_HINT = f"cpu instruction fetch error: unknown instruction sequence"
                    return False

        self.FETCH_ERROR = True
        self.ERROR_HINT = "cpu fetch error: no fin byte was found"
        return False

    def syscall(self, syscall_byte: str):
        # Syscall Logic
        task = syscall_byte
        if self.instruction.syscall(task, True) == "iip": # increment instruction pointer
            callee = self.byte.convert(self.register.get(self.ARGUMENTR0))
            self.sram.__edit__(self.sram.instruction_pointer + callee)
            return True
        elif self.instruction.syscall(task, True) == "dip": # decrement instruction pointer
            callee = self.byte.convert(self.register.get(self.ARGUMENTR0))
            self.sram.__edit__(self.sram.instruction_pointer - callee)
            return True
        elif self.instruction.syscall(task, True) == "ptv": # print a value to console
            callee = self.register.get(self.ARGUMENTR0)
            print(callee)
            return True
        elif self.instruction.syscall(task, True) == "pti": # print an integer to console
            callee = self.byte.convert(self.register.get(self.ARGUMENTR0))
            print("OUT: ", callee)
            return True
        elif self.instruction.syscall(task, True) == "gip": # get ip
            self.register.set(self.RETURNR0, self.byte.bitstring(self.sram.instruction_pointer))
            return True
        elif self.instruction.syscall(task, True) == "gsp": # get sp
            self.register.set(self.RETURNR0, self.byte.bitstring(self.stack.__depth__()))
            return True
        elif self.instruction.syscall(task, True) == "gpc": # get pc
            self.register.set(self.RETURNR0, self.byte.bitstring(self.PC))
            return True


        elif self.instruction.syscall(task, True) == "gpuint": # init framebuffer
            # convert, not bitstring: the register already holds a word and the
            # gpu counts cells, like every other syscall that reads an argument
            x = self.byte.convert(self.register.get(self.ARGUMENTR0))
            y = self.byte.convert(self.register.get(self.ARGUMENTR1))
            self.gpu.create(x, y)
            return True
        elif self.instruction.syscall(task, True) == "gpupix": # draw a pixel
            x = self.byte.convert(self.register.get(self.ARGUMENTR0))
            y = self.byte.convert(self.register.get(self.ARGUMENTR1))
            c = self.byte.convert(self.register.get(self.ARGUMENTR2))
            if not self.gpu.pixel(x, y, c):
                return False
            return True
        elif self.instruction.syscall(task, True) == "gpurem": # remove a pixel
            x = self.byte.convert(self.register.get(self.ARGUMENTR0))
            y = self.byte.convert(self.register.get(self.ARGUMENTR1))
            # a removed cell carries no colour, so 0 rather than a leftover one
            if not self.gpu.pixel(x, y, 0, pixel=" "):
                return False
            return True
        elif self.instruction.syscall(task, True) == "gpudis": # show the frame
            self.gpu.show()
            return True
        elif self.instruction.syscall(task, True) == "gpucls": # clear the console
            self.gpu.cls()
            return True

        elif self.instruction.syscall(task, True) == "gpuchr": # print a char to console
            x = self.byte.convert(self.register.get(self.ARGUMENTR0))
            y = self.byte.convert(self.register.get(self.ARGUMENTR1))
            c = self.byte.convert(self.register.get(self.ARGUMENTR2))
            char = self.register.get(self.ARGUMENTR3)
            if not self.gpu.pixel(x, y, c, pixel=char):
                return False
            return True
        elif self.instruction.syscall(task, True) == "key": # is key pressed ?
            what_key = self.register.get(self.ARGUMENTR0)
            if what_key is False or what_key is None or not self.byte.isbitstring(what_key):
                self.ERROR_HINT = "cpu key syscall error: no character in the argument register"
                return False
            is_pressed = self.byte.bitstring(self.keyboard.keystate(what_key))
            self.register.set(self.RETURNR0, is_pressed)
            return True




        else:
            return False

    def __hold__(self, milliseconds: float):
        """wait, in slices, so a window can still be moved or closed"""
        left = milliseconds
        while left > 0:
            slice_ms = min(left, 10.0)
            time.sleep(slice_ms / 1000.0)
            self.gpu.pump()
            left -= slice_ms
        return True

    def __ptr_dest__(self, register):
        """the address to write to. in PTR mode the register field names a register that holds the address, so mov %&3, 4 writes where &3 points"""
        if not self.instruction.reg.SIGNAL_PTR:
            return register
        address = self.register.get(register)
        if address is False or address is None or not self.byte.isbitstring(address):
            return False
        return address

    def __ptr_src__(self, immediate):
        """the address to read from. same thing for the immediate field, so mov &15, %&2 reads the cell &2 points at"""
        if not self.instruction.reg.SIGNAL_PTR:
            return immediate
        address = self.register.get(immediate)
        if address is False or address is None or not self.byte.isbitstring(address):
            return False
        return address

    def __inc_pc__(self):
        self.PC += 1
        return True
    def __dec_pc__(self):
        if self.PC > 0:
            self.PC -= 1
            return True
        return False


        
class CPU8B(CPU):
    def __init__(self):
        super().__init__(byte.Byte8(), decoder.Decoder8B(), arithmeticlogicunit.ALU8(), cpu_registers.Register8B(), instruction_registers.Instruction8B(),
                         static_ram.StaticRam8B(), random_access_memory.MIO8B(), stack.Stack8B(), graphical_processing_unit.GPU8B(), keyboard.Keyboard8B())
        
class CPU16B(CPU):
    def __init__(self):
        super().__init__(byte.Byte16(), decoder.Decoder16B(), arithmeticlogicunit.ALU16(), cpu_registers.Register16B(), instruction_registers.Instruction16B(),
                         static_ram.StaticRam16B(), random_access_memory.MIO16B(), stack.Stack16B(), graphical_processing_unit.GPU16B(), keyboard.Keyboard16B())
        
class CPU32B(CPU):
    def __init__(self):
        super().__init__(byte.Byte32(), decoder.Decoder32B(), arithmeticlogicunit.ALU32(), cpu_registers.Register32B(), instruction_registers.Instruction32B(),
                         static_ram.StaticRam32B(), random_access_memory.MIO32B(), stack.Stack32B(), graphical_processing_unit.GPU32B(), keyboard.Keyboard32B())