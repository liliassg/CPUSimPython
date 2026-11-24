import cpu.cpu as CPU
# not used anymore
"""
    General Instruction
            0: "tsl", # tick sleep
            1: "imo", # instruction mode / opcode mode
            2: "drg", # target register mode
            3: "reg", # reg mode
            4: "imm", # immediate mode
            5: "fin", # run exec
    Opcode Instruction
            0: "nop",
            1: "mov",
            2: "add",
            3: "sub",
            4: "mul",
            5: "div",
            6: "jnz",
            7: "jgz",
            8: "jne",
            9: "jgt",
            10: "jmp",
            11: "call",
            12: "syscall",
            13: "ret",
            14: "eq",
            15: "neq",
            16: "le",
            17: "ge",
            18: "lt",
            19: "gt",
            20: "shl",
            21: "shr",
            22: "and",
            23: "xor",
            24: "or",
            25: "xnor",
            26: "not",
            27: "nand",
            28: "nor",
            29: "nul",
            30: "mod"
    Register Instruction
    0-26

syntax: mov &2, 3   === OPCODE REG, IMMEDIATE   & = reg value   no & = IMMEDIATE
        xor &3, &3
"""
import os
cpu: CPU = None
arch = input("Enter a architecture(8/16/32): ")
if arch == "8":
    cpu = CPU.CPU8()
elif arch == "16":
    cpu = CPU.CPU16()
elif arch == "32":
    cpu = CPU.CPU32()
else:
    print("Invalid architecture")
    exit(1)

def tokenize(text: str):
    if text == "save":
        return "save"
    if text == "run":
        return "run"
    text = text.removeprefix(",")
    segs: list[str] = text.split(" ")
    tmp = {"instruction": None, "reg": 0, "imm": 0, "dreg": False, "syscall": False}

    # single keywords
    is_syscall = False
    # none yet

    if segs and segs[0]:
        first = segs[0].strip().rstrip(",").lower()
        if first:
            op_byte = cpu.instruction.opcode(first, False)
            if op_byte is not None:
                tmp["instruction"] = op_byte
    got_one_reg = False
    opcodes: list[str] = []
    for k, v in cpu.instruction.opcodes.items():
        opcodes.append(v.lower())

    for seg in segs:
        seg_norm = seg.strip().rstrip(",").lower()
        if seg_norm in opcodes:
            tmp["instruction"] = cpu.instruction.opcode(seg_norm, False)

        if is_syscall:
            # syscall ID follows the keyword; store as bitstring
            tmp["imm"] = cpu.byte.convert(int(seg_norm))
            break
        if seg_norm in ("sys", "syscall"):
            tmp["syscall"] = True
            is_syscall = True

        if seg.startswith("&"):
            try:
                seg, _ = seg.split(",")
            except ValueError:
                pass
            if got_one_reg:
                tmp["dreg"] = True
                reg_val = int(seg[1:])
                tmp["imm"] = cpu.byte.bitstring(reg_val)
                break
            reg_val = int(seg[1:])
            tmp["reg"] = cpu.byte.bitstring(reg_val)
            got_one_reg = True
        if seg.isdigit():
            tmp["imm"] = cpu.byte.bitstring(int(seg))
    return tmp

def show_registers():
    display_string:str = ""
    for reg_name, reg_val in cpu.register.register_opcodes.items():
        display_string += f"{cpu.byte.convert(reg_name)}: {cpu.byte.convert(reg_val)}   "
    return display_string

def show_counters():
    return f"IP: {cpu.sram.instruction_pointer} PC: {cpu.PC}"

def show_stack():
    return f"SP: {cpu.stack.call_stack}  CS: {cpu.stack.stack}"

def main():
    dump = []
    all_code = []
    run_mode = True
    print("Welcome to CASM 0.0.0\nThis Assembler is a tiny version of CASM, only featuring OPCODE, &int, int or OPCODE, &int, &int\n&=Register")
    while True:

        if not len(all_code) == 0:
            txt: str = ""
            for i in all_code:
                txt += i
            print(txt)

        text = input("Enter a text: ")
        code = tokenize(text)

        if code == "save":
            file = input("Enter a file name: ")
            with open(f"cpu/rom/{file}", "w", encoding="utf-8") as f:
                for line in dump:
                    f.write(f"{line}\n")
            exit(0)

        if code == "run":
            run_mode = True
            continue

        all_code.append(text + "\n")

        binary: str = ""

        if isinstance(code, dict):
            # Correct byte order expected by CPU.fetch():
            # - Syscall: sys → <id> → fin
            # - Normal:  imo → <opcode> → reg → imm (or reg) → [drg] → fin
            if code.get("syscall"):
                binary = (
                    f"{cpu.instruction.instruction('sys', False)} {code['imm']} {cpu.instruction.instruction('fin', False)}"
                )
            elif code["dreg"]:
                binary = (
                    f"{cpu.instruction.instruction('imo', False)} {code['instruction']} "
                    f"{cpu.instruction.instruction('reg', False)} {code['reg']} "
                    f"{cpu.instruction.instruction('imm', False)} {code['imm']} "
                    f"{cpu.instruction.instruction('drg', False)} {cpu.instruction.instruction('fin', False)}"
                )
            else:
                binary = (
                    f"{cpu.instruction.instruction('imo', False)} {code['instruction']} "
                    f"{cpu.instruction.instruction('reg', False)} {code['reg']} "
                    f"{cpu.instruction.instruction('imm', False)} {code['imm']} "
                    f"{cpu.instruction.instruction('fin', False)}"
                )
        if run_mode and isinstance(code, dict):
            byte = binary.split(" ")
            cpu.sram.add(byte)
            # add() increments the instruction pointer; move back so fetch() reads the just-added line
            cpu.sram.__dec__()
            cpu.fetch()
            if cpu.FETCH_ERROR:
                print(f"casm caused FETCH ERROR: {cpu.ERROR_HINT}")
                yn = input("Do you wish to continue? (y/n): ")
                if yn == "n":
                    exit(0)
                else:
                    run_mode = False
            else:
                cpu.execute()
                if cpu.EXECUTE_ERROR:
                    print(f"casm caused EXECUTE_ERROR: {cpu.ERROR_HINT}")
                    yn = input("Do you wish to continue? (y/n): ")
                    if yn == "n":
                        exit(0)
                    else:
                        run_mode = False
                print(show_registers())
                print(show_counters())
                print(show_stack())

        if binary:
            dump.append(binary)


main()