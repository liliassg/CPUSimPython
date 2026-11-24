import cpu.cpu as CPU
"""
file.casm -> file.cobj

CASM is the assembly of this machine. the cpu is the source of truth: every
opcode, tag and syscall number is read out of cpu/instruction.py, so a new
opcode needs nothing in here but a shape.

syntax:
    .arch 32                        machine width, 8/16/32
    .data [name: value, ...]        compile time constants, may span lines
    .extern "rt/gpu.casm"           assemble another file into this one
    .buf greeting "hello"           a block of words with a name
    .buf greeting "hello" ?200      and at an address you pick
    .include "part.casm"            paste a file in as text
    .org 60000                      where the next .buf block goes
    .equ name value                 one constant without a table
    .ascii name "hi"                .buf without the name being an address
    .asciz name "hi"                the same with a 0 at the end
    .align 4                        pad with nop until the index divides
    .macro name a b                 text macro, $a $b are the arguments
    .endmacro
    .repeat 4                       assemble the body n times
    .endrepeat
    .if name                        assemble the body when the constant is set
    .else
    .endif

    label:                          names the instruction that follows
    .local:                         a label that belongs to the label above it
    rem name                        names it without writing a word

    mov &2, 7                       register, immediate
    mov %100, &3                    memory, register
    mov &2, %&5                     the cell &5 points at
    je &2, 0, label                 compare and jump
    jmp +2                          two instructions on
    buf %200, [7, 8, 9]             a block of words
    buf %200, "hello"               the same as characters
    syscall pti                     by name or by number
    wait 80                         do nothing for 80 ms
    mov &2, "h"                     a character is its number
    mov &2, max_x-1                 constants fold before a word is written

shapes:
    none        imo op fin
    target      imo op adr V fin
    reg_target  imo op [mem] reg L adr T fin
    conditional imo op [mem] [drg|dme] reg L imm R adr T fin
    source_only imo op [drg|dme] imm V fin
    dest_only   imo op [mem] reg D fin
    dest_src    imo op [ptr] [mem] [drg|dme] reg D imm S fin
    block_write imo op [ptr] reg D imm N buf W... fin
    sleep       imo op tsl T fin
    syscall     sys ID fin
"""
import os
import sys
import gpu.strings as strings


class Assembler:

    def __init__(self, arch: int = 32):
        self.arch = arch
        self.cpu = self.make_cpu(arch)
        self.string = self.make_strings(arch)

        self.labels = {}
        """name -> instruction index"""
        self.constants = {}
        """name -> number, folded"""
        self.blocks = {}
        """name -> [address, [words]]"""
        self.macros = {}
        """name -> [parameters, lines]"""
        self.code = []
        """one dict per instruction, in order"""
        self.errors = []
        self.warnings = []
        self.listing = []

        self.origin = 60000
        """where the next .buf block goes"""
        self.base = 0
        """the index the file being written starts at"""
        self.shared = {}
        self.taken = 0
        self.pre_seen = []
        """names the pre scan already read, so they are no duplicates"""
        self.block_origins = {
            8: 200,
            16: 60000,
            32: 60000
        }
        self.ring = 0
        """how many words the blocks have taken so far"""
        self.scope = ""
        """the last global label, so .local can hang off it"""

        # SHAPES
        self.none = ["nop", "ret", "pop", "hlt"]
        self.target = ["jmp", "call", "push"]
        self.reg_target = ["jnz", "jgz", "jz"]
        self.conditional = ["je", "jne", "jgt", "jlt", "jge", "jle"]
        self.dest_src = ["mov", "add", "sub", "mul", "div", "mod", "shl",
                         "shr", "and", "or", "xor", "not", "nand", "nor",
                         "xnor", "nul", "eq", "neq", "lt", "gt", "le", "ge"]
        self.dest_only = ["inc", "dec"]
        self.source_only = ["exit"]
        self.block_write = ["buf"]
        self.sleep = ["wait"]
        self.pseudo = ["rem"]
        self.syscall_words = ["sys", "syscall"]

        self.terminators = ["hlt", "exit", "ret", "jmp"]
        self.entry = "_start"

    def make_cpu(self, arch: int):
        if arch == 8:
            return CPU.CPU8B()
        if arch == 16:
            return CPU.CPU16B()
        return CPU.CPU32B()

    def make_strings(self, arch: int):
        if arch == 8:
            return strings.String8B()
        if arch == 16:
            return strings.String16B()
        return strings.String32B()

    ################# TABLES ##################

    def opcodes(self):
        """name -> number    out of the cpu"""
        table = {}
        for word, name in self.cpu.instruction.opcodes.items():
            table[name] = self.cpu.byte.convert(word)
        return table

    def tags(self):
        table = {}
        for word, name in self.cpu.instruction.instructions.items():
            table[name] = self.cpu.byte.convert(word)
        return table

    def syscalls(self):
        table = {}
        for word, name in self.cpu.instruction.syscalls.items():
            table[name] = self.cpu.byte.convert(word)
        return table

    def is_opcode(self, word: str):
        return word.lower() in self.opcodes()

    def shape(self, name: str):
        """which shape an opcode has. an opcode with none is not encodable"""
        name = name.lower()
        if name in self.none:
            return "none"
        if name in self.target:
            return "target"
        if name in self.reg_target:
            return "reg_target"
        if name in self.conditional:
            return "conditional"
        if name in self.dest_src:
            return "dest_src"
        if name in self.dest_only:
            return "dest_only"
        if name in self.source_only:
            return "source_only"
        if name in self.block_write:
            return "block_write"
        if name in self.sleep:
            return "sleep"
        return None

    def word(self, value: int):
        """a number as a machine word"""
        return self.cpu.byte.bitstring(int(value))

    def tag(self, name: str):
        return self.word(self.tags()[name])

    def fits(self, value: int):
        return 0 <= int(value) < (1 << self.cpu.byte.BITLENGTH)

    def error(self, line: int, text: str):
        self.errors.append(f"line {line + 1}: {text}")
        return False

    def warn(self, line: int, text: str):
        self.warnings.append(f"line {line + 1}: {text}")
        return True

    ################# NUMBERS ##################

    def is_number(self, text: str):
        text = text.strip().replace("_", "")
        if not text:
            return False
        if text.startswith("0x") or text.startswith("0b") or text.startswith("0o"):
            return True
        return text.isdigit()

    def number(self, text: str):
        """a number in any base this assembler knows, or None"""
        text = text.strip().replace("_", "")
        try:
            if text.startswith("0x"):
                return int(text[2:], 16)
            if text.startswith("0b"):
                return int(text[2:], 2)
            if text.startswith("0o"):
                return int(text[2:], 8)
            return int(text, 10)
        except ValueError:
            return None

    def is_character(self, text: str):
        text = text.strip()
        return len(text) >= 3 and text.startswith('"') and text.endswith('"')

    def character(self, text: str):
        """the number of a character literal like "h", or None"""
        body = text.strip()[1:-1]
        if len(body) != 1:
            return None
        found = self.string.get(body, False)
        if found is False or found is None:
            return None
        return self.cpu.byte.convert(found)

    ################# EXPRESSIONS ##################

    def fold(self, text: str, line: int = 0):
        """a compile time expression down to one number, or None"""
        text = text.strip()
        if not text:
            return None
        pieces = self.split_expression(text)
        if pieces is None:
            return None
        self.expr_pieces = pieces
        self.expr_at = 0
        value = self.expr_or()
        if value is None or self.expr_at != len(pieces):
            return None
        return value

    def split_expression(self, text: str):
        """an expression into names, numbers, characters and operators"""
        pieces = []
        at = 0
        while at < len(text):
            char = text[at]
            if char in " \t":
                at += 1
                continue
            if char == '"':
                end = text.find('"', at + 1)
                if end < 0:
                    return None
                pieces.append(text[at:end + 1])
                at = end + 1
                continue
            if char in "()":
                pieces.append(char)
                at += 1
                continue
            if text[at:at + 2] in ("<<", ">>"):
                pieces.append(text[at:at + 2])
                at += 2
                continue
            if char in "+-*/%&|^":
                pieces.append(char)
                at += 1
                continue
            end = at
            while end < len(text) and (text[end].isalnum() or text[end] == "_"):
                end += 1
            if end == at:
                return None
            pieces.append(text[at:end])
            at = end
        return pieces

    def expr_peek(self):
        if self.expr_at >= len(self.expr_pieces):
            return None
        return self.expr_pieces[self.expr_at]

    def expr_take(self):
        piece = self.expr_peek()
        self.expr_at += 1
        return piece

    def expr_or(self):
        left = self.expr_shift()
        while left is not None and self.expr_peek() in ("|", "^", "&"):
            op = self.expr_take()
            right = self.expr_shift()
            if right is None:
                return None
            if op == "|":
                left = left | right
            elif op == "^":
                left = left ^ right
            else:
                left = left & right
        return left

    def expr_shift(self):
        left = self.expr_sum()
        while left is not None and self.expr_peek() in ("<<", ">>"):
            op = self.expr_take()
            right = self.expr_sum()
            if right is None:
                return None
            left = left << right if op == "<<" else left >> right
        return left

    def expr_sum(self):
        left = self.expr_product()
        while left is not None and self.expr_peek() in ("+", "-"):
            op = self.expr_take()
            right = self.expr_product()
            if right is None:
                return None
            left = left + right if op == "+" else left - right
        return left

    def expr_product(self):
        left = self.expr_atom()
        while left is not None and self.expr_peek() in ("*", "/", "%"):
            op = self.expr_take()
            right = self.expr_atom()
            if right is None or (op in ("/", "%") and right == 0):
                return None
            if op == "*":
                left = left * right
            elif op == "/":
                left = left // right
            else:
                left = left % right
        return left

    def expr_atom(self):
        piece = self.expr_take()
        if piece is None:
            return None
        if piece == "(":
            value = self.expr_or()
            if self.expr_take() != ")":
                return None
            return value
        if piece == "-":
            value = self.expr_atom()
            return None if value is None else -value
        if piece == "+":
            return self.expr_atom()
        if self.is_character(piece):
            return self.character(piece)
        if self.is_number(piece):
            return self.number(piece)
        if piece in self.constants:
            return self.constants[piece]
        if piece in self.labels:
            return self.labels[piece]
        return None

    ################# OPERANDS ##################

    def split_operands(self, text: str):
        """the operand part on commas, but not inside "..." or [...]"""
        parts = []
        current = ""
        quoted = False
        depth = 0
        for char in text:
            if char == '"':
                quoted = not quoted
            elif not quoted and char == "[":
                depth += 1
            elif not quoted and char == "]":
                depth = max(0, depth - 1)
            if char == "," and not quoted and depth == 0:
                parts.append(current.strip())
                current = ""
                continue
            current += char
        if current.strip():
            parts.append(current.strip())
        return parts

    def is_block(self, text: str):
        text = text.strip()
        if text.startswith("["):
            return True
        if text.startswith('"') and text.endswith('"') and len(text) > 3:
            return True
        return False

    def block_words(self, text: str, line: int):
        """a block as a list of numbers. [a, b] or "text" """
        text = text.strip()
        words = []
        if text.startswith('"'):
            if not text.endswith('"'):
                self.error(line, f"the string {text} is never closed")
                return None
            for char in text[1:-1]:
                found = self.string.get(char, False)
                if found is False or found is None:
                    self.error(line, f"the string map has no number for {char}")
                    return None
                words.append(self.cpu.byte.convert(found))
            return words
        if not text.endswith("]"):
            self.error(line, f"the block {text} is never closed with ]")
            return None
        body = text[1:-1].strip()
        if not body:
            self.error(line, "a block needs at least one word")
            return None
        for piece in self.split_operands(body):
            value = self.fold(piece, line)
            if value is None:
                self.error(line, f"cannot fold {piece} in a block")
                return None
            if value < 0:
                self.error(line, f"{piece} is negative, and a word cannot be")
                return None
            words.append(value)
        return words

    def operand(self, text: str, line: int):
        """one operand as a dict the encoder understands"""
        text = text.strip()
        out = {"kind": None, "value": None, "name": None, "relative": 0}
        if not text:
            self.error(line, "an empty operand")
            return out

        if self.is_block(text):
            out["kind"] = "block"
            out["value"] = self.block_words(text, line)
            return out

        if text.startswith("%&"):
            value = self.fold(text[2:], line)
            if value is None:
                self.error(line, f"{text} needs a register, by number or by name")
                return out
            out["kind"] = "pointer"
            out["value"] = value
            return out

        if text.startswith("&"):
            value = self.fold(text[1:], line)
            if value is None:
                self.error(line, f"{text} needs a register")
                return out
            out["kind"] = "register"
            out["value"] = value
            return out

        if text.startswith("%"):
            value = self.fold(text[1:], line)
            if value is None:
                self.error(line, f"{text} needs an address")
                return out
            out["kind"] = "memory"
            out["value"] = value
            return out

        if text.startswith("+") or text.startswith("-"):
            magnitude = self.fold(text[1:], line)
            if magnitude is None:
                self.error(line, f"{text} is no relative target")
                return out
            out["kind"] = "relative"
            out["value"] = magnitude
            out["relative"] = -1 if text.startswith("-") else 1
            return out

        value = self.fold(text, line)
        if value is not None:
            out["kind"] = "immediate"
            out["value"] = value
            return out

        out["kind"] = "name"
        out["name"] = self.local_name(text)
        return out

    def local_name(self, name: str):
        """a .local label is stored under the global label it belongs to"""
        if name.startswith(".") and self.scope:
            return self.scope + name
        return name

    ################# SOURCE ##################

    def read(self, path: str):
        """a file as lines, with .include pasted in where it stands"""
        if not os.path.exists(path):
            self.errors.append(f"no such file: {path}")
            return []
        lines = []
        with open(path, "r", encoding="utf-8") as data:
            for raw in data.readlines():
                lines.append(raw.rstrip("\r\n"))
        out = []
        for raw in self.strip_docs(lines):
            body = self.strip_comment(raw)
            if body.strip().startswith(".include"):
                name = self.quoted(body)
                if name is None:
                    self.errors.append(f".include needs a file in quotes: {raw}")
                    continue
                here = os.path.dirname(path)
                out += self.read(os.path.join(here, name))
                continue
            out.append(raw)
        return out

    def strip_docs(self, lines: list):
        """a ;; block runs over lines and is documentation, so it is dropped"""
        out = []
        inside = False
        for raw in lines:
            text = raw.strip()
            if not inside and text.startswith(";;"):
                inside = True
                if text.count(";;") > 1:        # opened and closed on one line
                    inside = False
                out.append("")
                continue
            if inside:
                if ";;" in text:
                    inside = False
                out.append("")
                continue
            out.append(raw)
        return out

    def strip_comment(self, line: str):
        """everything before a ; or a #, outside a string"""
        quoted = False
        for at, char in enumerate(line):
            if char == '"':
                quoted = not quoted
                continue
            if not quoted and char in ";#":
                return line[:at]
        return line

    def quoted(self, line: str):
        """the first "..." on a line"""
        first = line.find('"')
        if first < 0:
            return None
        second = line.find('"', first + 1)
        if second < 0:
            return None
        return line[first + 1:second]

    def join_tables(self, lines: list):
        """a .data table that runs over lines becomes one line again"""
        out = []
        holding = ""
        for raw in lines:
            body = self.strip_comment(raw)
            if holding:
                holding += " " + body.strip()
                if "]" in body:
                    out.append(holding)
                    holding = ""
                else:
                    out.append("")
                continue
            if body.strip().startswith(".data") and "[" in body and "]" not in body:
                holding = body.strip()
                out.append("")
                continue
            out.append(raw)
        if holding:
            self.errors.append("a .data table is never closed with ]")
            out.append(holding)
        return out

    ################# MACROS AND BLOCKS ##################

    def is_directive(self, line: str):
        text = line.strip()
        if not text.startswith("."):
            return False
        if text.split()[0].endswith(":"):
            return False        # .done: is a local label, not a directive
        return True

    def directive_of(self, line: str):
        return line.strip().split()[0].lower()

    def pre_constants(self, lines: list):
        """
        the constants of a file before anything is expanded, because .if and
        .repeat have to know them and they are read much later otherwise
        """
        for raw in lines:
            body = self.strip_comment(raw).strip()
            if body.startswith(".data"):
                self.read_data(body, 0)
                continue
            if body.startswith(".equ"):
                parts = body.split()
                if len(parts) != 3:
                    continue
                value = self.fold(parts[2], 0)
                if value is not None:
                    self.constants[parts[1]] = value
        return True

    def expand(self, lines: list):
        """macros, .repeat and .if, before anything is counted"""
        self.pre_constants(lines)
        out = []
        at = 0
        while at < len(lines):
            raw = lines[at]
            body = self.strip_comment(raw).strip()
            if body.startswith(".macro"):
                at = self.take_macro(lines, at)
                continue
            if body.startswith(".repeat"):
                at = self.take_repeat(lines, at, out)
                continue
            if body.startswith(".if"):
                at = self.take_if(lines, at, out)
                continue
            name = body.split()[0].lower() if body else ""
            if name in self.macros:
                out += self.use_macro(name, body)
                at += 1
                continue
            out.append(raw)
            at += 1
        return out

    def take_macro(self, lines: list, at: int):
        parts = self.strip_comment(lines[at]).split()
        if len(parts) < 2:
            self.errors.append(".macro needs a name")
            return at + 1
        name = parts[1].lower()
        parameters = parts[2:]
        body = []
        at += 1
        while at < len(lines):
            if self.strip_comment(lines[at]).strip().startswith(".endmacro"):
                break
            body.append(lines[at])
            at += 1
        self.macros[name] = [parameters, body]
        return at + 1

    def use_macro(self, name: str, line: str):
        """one macro call, with $a replaced by what was written"""
        parameters, body = self.macros[name]
        given = line.split()[1:]
        given = self.split_operands(" ".join(given))
        out = []
        for raw in body:
            text = raw
            for index, parameter in enumerate(parameters):
                value = given[index] if index < len(given) else ""
                text = text.replace("$" + parameter, value)
            out.append(text)
        return out

    def take_repeat(self, lines: list, at: int, out: list):
        parts = self.strip_comment(lines[at]).split()
        count = self.number(parts[1]) if len(parts) > 1 else None
        if count is None and len(parts) > 1:
            count = self.constants.get(parts[1])
        if count is None:
            self.errors.append(".repeat needs a count")
            count = 0
        body = []
        at += 1
        while at < len(lines):
            if self.strip_comment(lines[at]).strip().startswith(".endrepeat"):
                break
            body.append(lines[at])
            at += 1
        for _ in range(int(count)):
            out += body
        return at + 1

    def take_if(self, lines: list, at: int, out: list):
        parts = self.strip_comment(lines[at]).split()
        name = parts[1] if len(parts) > 1 else ""
        taken = name in self.constants and self.constants[name] != 0
        body = []
        other = []
        where = body
        at += 1
        while at < len(lines):
            text = self.strip_comment(lines[at]).strip()
            if text.startswith(".endif"):
                break
            if text.startswith(".else"):
                where = other
                at += 1
                continue
            where.append(lines[at])
            at += 1
        out += body if taken else other
        return at + 1

    ################# PASS ONE ##################

    def first_pass(self, lines: list):
        """constants, blocks, labels and how long every instruction is"""
        index = 0
        pending = []
        for line, raw in enumerate(lines):
            body = self.strip_comment(raw).strip()
            if not body:
                continue

            if self.is_directive(body):
                self.read_directive(body, line)
                continue

            while body and (":" in body.split()[0]
                            or body.split()[0].endswith(":")):
                name, body = body.split(":", 1)
                name = name.strip()
                if name.startswith("."):
                    name = self.local_name(name)
                else:
                    self.scope = name
                pending.append([name, line])
                body = body.strip()
                if not body:
                    break

            if not body:
                continue

            first = body.split()[0]
            first = first.lower()
            if first in self.pseudo:
                parts = body.split()
                if len(parts) != 2:
                    self.error(line, "rem needs exatly one name")
                    continue
                pending.append([self.local_name(parts[1]), line])
                continue

            for name, where in pending:
                if name in self.labels:
                    self.error(where, f"the label {name} is defined twice")
                self.labels[name] = index
            pending = []

            if not self.is_opcode(first) and first not in self.syscall_words:
                self.error(line, f"unknown opcode: {first}")
                continue
            index += 1

        for name, where in pending:
            self.labels[name] = index
        return index

    def read_directive(self, body: str, line: int):
        name = self.directive_of(body)
        if name == ".arch":
            return True             # handled before the passes
        if name == ".include":
            return True             # handled while reading
        if name == ".data":
            return self.read_data(body, line)
        if name == ".equ":
            parts = body.split()
            if len(parts) != 3:
                return self.error(line, ".equ needs a name and a value")
            value = self.fold(parts[2], line)
            if value is None:
                return self.error(line, f"cannot fold {parts[2]}")
            self.constants[parts[1]] = value
            return True
        if name == ".org":
            parts = body.split()
            value = self.fold(parts[1], line) if len(parts) > 1 else None
            if value is None:
                return self.error(line, ".org needs an address")
            self.origin = value
            self.ring = 0
            return True
        if name == ".extern":
            return True             # handled before the passes
        if name in (".buf", ".ascii", ".asciz"):
            return self.read_block(body, line, zero=name == ".asciz")
        if name == ".align":
            return True
        self.error(line, f"unknown directive: {name}")
        return False

    def read_data(self, body: str, line: int):
        """.data [name: value, name: value]"""
        inside = body[body.find("[") + 1:]
        if "]" in inside:
            inside = inside[:inside.rfind("]")]
        for piece in self.split_operands(inside):
            if not piece.strip():
                continue
            if ":" not in piece:
                self.error(line, f"{piece} is no name: value pair")
                continue
            name, value = piece.split(":", 1)
            name = name.strip()
            if name in self.constants and name not in self.pre_seen:
                self.error(line, f"the constant {name} is defined twice")
                continue
            self.pre_seen.append(name)
            folded = self.fold(value, line)
            if folded is None:
                self.error(line, f"cannot fold {value.strip()} for {name}")
                continue
            self.constants[name] = folded
        return True

    def read_block(self, body: str, line: int, zero: bool = False):
        """.buf name "words" [?address]"""
        parts = body.split(None, 2)
        if len(parts) < 3:
            return self.error(line, f"{parts[0]} needs a name and some words")
        name = parts[1]
        rest = parts[2].strip()
        at = None
        if "?" in rest:
            rest, after = rest.rsplit("?", 1)
            rest = rest.strip()
            at = self.fold(after, line)
            if at is None:
                return self.error(line, f"?{after.strip()} is no address")
        words = self.block_words(rest, line)
        if words is None:
            return False
        if zero:
            words = words + [0]
        if name in self.blocks:
            return self.error(line, f"{name} is already a block")
        if at is None:
            at = self.origin + self.ring
            self.ring += len(words)
        self.blocks[name] = [at, words]
        self.constants[name] = at
        self.constants[name + "_len"] = len(words)
        last = at + len(words) - 1
        if not self.fits(last):
            self.error(line, f"the block {name} runs {at}..{last}, past the end "
                             f"of a {self.cpu.byte.BITLENGTH} bit machine")
        return True

    ################# PASS TWO ##################
    # for

    def second_pass(self, lines: list):
        """every instruction into words, now that the names are known"""
        index = 0
        for line, raw in enumerate(lines):
            body = self.strip_comment(raw).strip()
            if not body:
                continue
            if self.is_directive(body):
                if self.directive_of(body) == ".align":
                    index = self.write_align(body, line, index)
                continue
            while body and (":" in body.split()[0]
                            or body.split()[0].endswith(":")):
                name, body = body.split(":", 1)
                if not name.strip().startswith("."):
                    self.scope = name.strip()
                body = body.strip()
                if not body:
                    break
            if not body:
                continue
            first = body.split()[0].lower()
            if first in self.pseudo:
                continue
            rest = body[len(body.split()[0]):].strip()
            words = self.encode(first, rest, line, self.base + index)
            if words is None:
                continue
            self.code.append({"index": index, "line": line, "source": body,
                              "words": words})
            self.listing.append(f"{index:>4}  {body:<34}{len(words):>3} words")
            index += 1
        return index

    def write_align(self, body: str, line: int, index: int):
        """pad with nop until the next index divides by n"""
        parts = body.split()
        step = self.fold(parts[1], line) if len(parts) > 1 else None
        if step is None or step <= 0:
            self.error(line, ".align needs a number above zero")
            return index
        while index % step:
            words = self.encode("nop", "", line, index)
            self.code.append({"index": index, "line": line,
                              "source": "nop (.align)", "words": words})
            self.listing.append(f"{index:>4}  {'nop (.align)':<34}"
                                f"{len(words):>3} words")
            index += 1
        return index

    def encode(self, name: str, rest: str, line: int, index: int):
        """one instruction as a list of machine words"""
        if name in self.syscall_words:
            return self.encode_syscall(rest, line)
        shape = self.shape(name)
        if shape is None:
            self.error(line, f"{name} has no shape, so it cannot be written")
            return None
        number = self.opcodes().get(name)
        if number is None:
            self.error(line, f"unknown opcode: {name}")
            return None
        given = self.split_operands(rest)
        operands = [self.operand(piece, line) for piece in given]
        for item in operands:
            if item["kind"] == "name":
                self.resolve(item, line, index, shape)
            if item["kind"] == "relative":
                # +2 means two instructions on from this one
                target = index + item["relative"] * item["value"]
                if target < 0:
                    self.error(line, f"a relative target before the first "
                                     f"instruction: {target}")
                    target = 0
                item["kind"] = "immediate"
                item["value"] = target

        if shape == "none":
            return self.row_none(number, operands, line)
        if shape in ("target", "address"):
            return self.row_target(number, operands, line)
        if shape == "reg_target":
            return self.row_reg_target(number, operands, line)
        if shape == "conditional":
            return self.row_conditional(number, operands, line)
        if shape == "dest_src":
            return self.row_dest_src(number, operands, line)
        if shape == "dest_only":
            return self.row_dest_only(number, operands, line)
        if shape == "source_only":
            return self.row_source_only(number, operands, line)
        if shape == "block_write":
            return self.row_block(number, operands, line)
        if shape == "sleep":
            return self.row_sleep(number, operands, line)
        self.error(line, f"the shape {shape} is not written yet")
        return None

    def resolve(self, item: dict, line: int, index: int, shape: str):
        """a bare name is a label, a constant, or nothing"""
        name = item["name"]
        if name in self.labels:
            item["kind"] = "immediate" # i am nod kind :(
            item["value"] = self.labels[name]
            return True
        if name in self.constants:
            item["kind"] = "immediate" # i am kind :)
            item["value"] = self.constants[name]
            return True
        if name in self.syscalls():
            item["kind"] = "syscall" # i am not kind again :(
            item["value"] = self.syscalls()[name]
            return True
        self.error(line, f"unknown name: {name}")
        item["kind"] = "immediate" # i am kind!
        item["value"] = 0
        return False

    def count(self, operands: list, wanted: int, line: int, name: str):
        if len(operands) != wanted:
            self.error(line, f"{name} takes {wanted} operand(s), got {len(operands)}")
            return False
        return True

    def check(self, item: dict, kinds: list, line: int, where: str):
        if item["kind"] not in kinds:
            self.error(line, f"{where} cannot be a {item['kind']}")
            return False
        if item["kind"] in ("register", "pointer") and item["value"] is not None:
            if item["value"] >= len(self.cpu.register.register_opcodes):
                self.warn(line, f"register {item['value']} is outside this machine")
        if item["value"] is not None and isinstance(item["value"], int):
            if not self.fits(item["value"]):
                self.error(line, f"{item['value']} does not fit in "
                                 f"{self.cpu.byte.BITLENGTH} bit")
                return False
        return True

    ################# ROWS ##################

    def row_none(self, number: int, operands: list, line: int):
        if not self.count(operands, 0, line, "this opcode"):
            return None
        return [self.tag("imo"), self.word(number), self.tag("fin")]

    def row_target(self, number: int, operands: list, line: int):
        if not self.count(operands, 1, line, "this opcode"):
            return None
        item = operands[0]
        if not self.check(item, ["immediate"], line, "the target"):
            return None
        return [self.tag("imo"), self.word(number),
                self.tag("adr"), self.word(item["value"]),
                self.tag("fin")]

    def row_reg_target(self, number: int, operands: list, line: int):
        if not self.count(operands, 2, line, "this opcode"):
            return None
        left, target = operands
        if not self.check(left, ["register", "memory", "pointer"], line, "the left side"):
            return None
        row = [self.tag("imo"), self.word(number)]
        row += self.flags(left, None)
        row += [self.tag("reg"), self.word(left["value"]),
                self.tag("adr"), self.word(target["value"]),
                self.tag("fin")]
        return row

    def row_conditional(self, number: int, operands: list, line: int):
        if not self.count(operands, 3, line, "this opcode"):
            return None
        left, right, target = operands
        if not self.check(left, ["register", "memory", "pointer"], line, "the left side"):
            return None
        if not self.check(right, ["register", "memory", "pointer", "immediate"],
                          line, "the right side"):
            return None
        row = [self.tag("imo"), self.word(number)]
        row += self.flags(left, right)
        row += [self.tag("reg"), self.word(left["value"]),
                self.tag("imm"), self.word(right["value"]),
                self.tag("adr"), self.word(target["value"]),
                self.tag("fin")]
        return row

    def row_dest_src(self, number: int, operands: list, line: int):
        if not self.count(operands, 2, line, "this opcode"):
            return None
        dest, src = operands
        if not self.check(dest, ["register", "memory", "pointer"], line, "the destination"):
            return None
        if not self.check(src, ["register", "memory", "pointer", "immediate"],
                          line, "the source"):
            return None
        row = [self.tag("imo"), self.word(number)]
        row += self.flags(dest, src)
        row += [self.tag("reg"), self.word(dest["value"]),
                self.tag("imm"), self.word(src["value"]),
                self.tag("fin")]
        return row

    def row_dest_only(self, number: int, operands: list, line: int):
        if not self.count(operands, 1, line, "this opcode"):
            return None
        dest = operands[0]
        if not self.check(dest, ["register", "memory", "pointer"], line, "the destination"):
            return None
        row = [self.tag("imo"), self.word(number)]
        row += self.flags(dest, None)
        row += [self.tag("reg"), self.word(dest["value"]), self.tag("fin")]
        return row

    def row_source_only(self, number: int, operands: list, line: int):
        if not self.count(operands, 1, line, "this opcode"):
            return None
        value = operands[0]
        if not self.check(value, ["register", "memory", "pointer", "immediate"],
                          line, "the value"):
            return None
        row = [self.tag("imo"), self.word(number)]
        row += self.flags(None, value)
        row += [self.tag("imm"), self.word(value["value"]), self.tag("fin")]
        return row

    def row_block(self, number: int, operands: list, line: int):
        if not self.count(operands, 2, line, "buf"):
            return None
        dest, block = operands
        if not self.check(dest, ["memory", "immediate", "pointer"], line, "the address"):
            return None
        if block["kind"] != "block" or block["value"] is None:
            self.error(line, "buf needs a block of words")
            return None
        words = block["value"]
        if not words:
            self.error(line, "a block needs at least one word")
            return None
        row = [self.tag("imo"), self.word(number)]
        if dest["kind"] == "pointer":
            row.append(self.tag("ptr"))
        row += [self.tag("reg"), self.word(dest["value"]),
                self.tag("imm"), self.word(len(words)),
                self.tag("buf")]
        for value in words:
            if not self.fits(value):
                self.error(line, f"the word {value} does not fit in "
                                 f"{self.cpu.byte.BITLENGTH} bit")
                return None
            row.append(self.word(value))
        row.append(self.tag("fin"))
        return row

    def row_sleep(self, number: int, operands: list, line: int):
        if not self.count(operands, 1, line, "wait"):
            return None
        ticks = operands[0]
        if ticks["kind"] != "immediate":
            self.error(line, "wait reads its ticks out of the instruction, so "
                             "they cannot come from a register")
            return None
        return [self.tag("imo"), self.word(number),
                self.tag("tsl"), self.word(ticks["value"]),
                self.tag("fin")]

    def row_syscall(self, value: int):
        return [self.tag("sys"), self.word(value), self.tag("fin")]

    def encode_syscall(self, rest: str, line: int):
        given = self.split_operands(rest)
        if len(given) != 1:
            self.error(line, "syscall takes one name or number")
            return None
        name = given[0].strip().lower()
        if name in self.syscalls():
            return self.row_syscall(self.syscalls()[name])
        value = self.fold(name, line)
        if value is None:
            self.error(line, f"unknown syscall: {given[0]}")
            return None
        return self.row_syscall(value)

    def flags(self, dest, src):
        """the tags that say which side touches memory"""
        row = []
        pointer = False
        if dest is not None and dest["kind"] == "pointer":
            pointer = True
        if src is not None and src["kind"] == "pointer":
            pointer = True
        if pointer:
            row.append(self.tag("ptr"))
        if dest is not None and dest["kind"] in ("memory", "pointer"):
            row.append(self.tag("mem"))
        if src is not None and src["kind"] == "register":
            row.append(self.tag("drg"))
        if src is not None and src["kind"] in ("memory", "pointer"):
            row.append(self.tag("dme"))
        return row

    ################# UNITS ##################

    def unit(self, path: str, seen: list):
        """
        one file and everything it pulls in with .extern, depth first and
        every file only once. the externs come before the file itself, the
        way the machine needs them: their words are in the sram first.
        """
        real = os.path.abspath(path)
        if real in seen:
            return []
        seen.append(real)
        lines = self.read(path)
        if not lines:
            return []
        out = []
        for extern in self.externs(lines, path):
            out += self.unit(extern, seen)
        out.append({"path": real, "name": os.path.basename(real),
                    "lines": self.expand(self.join_tables(lines)),
                    "labels": {}, "constants": {}, "blocks": {},
                    "base": 0, "count": 0, "external": True})
        return out

    def unit_pass_one(self, unit: dict):
        """the labels, constants and blocks of one file, all still local"""
        self.pre_seen = []
        self.labels = {}
        self.constants = dict(self.shared)
        self.blocks = {}
        self.scope = ""
        self.ring = self.taken
        count = self.first_pass(unit["lines"])
        entry = self.entry_index(unit)
        rows = len(self.blocks)
        if rows:
            self.shift_unit_labels(entry, rows)
            count += rows
        unit["labels"] = self.labels
        unit["constants"] = self.constants
        unit["blocks"] = self.blocks
        unit["count"] = count
        unit["entry"] = entry
        unit["block_rows"] = rows
        for name, value in self.constants.items():
            self.shared[name] = value
        for pair in self.blocks.values():
            self.taken += len(pair[1])
        return count

    def entry_index(self, unit: dict):
        """where the entry label of a file sits, or 0 wen it has none"""
        if self.entry in self.labels:
            return self.labels[self.entry]
        return 0

    def shift_unit_labels(self, entry: int, rows: int):
        """the generated buf rows sit at the entry, so the rest moves along"""
        for name in self.labels:
            if self.labels[name] >= entry and name != self.entry:
                self.labels[name] += rows
        return True

    def prologue(self, units: list):
        """
        one call per external entry point, then the jump into the main file.
        without it an imported file would never initialise itself.
        """
        if len(units) < 2:
            return []
        rows = []
        for unit in units[:-1]:
            if self.entry not in unit["labels"]:
                continue
            target = unit["base"] + unit["labels"][self.entry]
            rows.append([self.tag("imo"), self.word(self.opcodes()["call"]),
                         self.tag("adr"), self.word(target), self.tag("fin")])
        main = units[-1]
        target = main["base"] + main["labels"].get(self.entry, 0)
        rows.append([self.tag("imo"), self.word(self.opcodes()["jmp"]),
                     self.tag("adr"), self.word(target), self.tag("fin")])
        return rows

    def prologue_size(self, units: list):
        if len(units) < 2:
            return 0
        found = 0
        for unit in units[:-1]:
            if self.entry in unit["labels"]:
                found += 1
        return found + 1

    def merge(self, units: list):
        """
        every label as an absolute index. the main file is merged last, so a
        name it defines itself wins over the same name in an import.
        """
        labels = {}
        constants = {}
        for unit in units:
            for name, where in unit["labels"].items():
                labels[name] = unit["base"] + where
            for name, value in unit["constants"].items():
                constants[name] = value
        return labels, constants

    def unit_block_rows(self, unit: dict):
        """the buf instructions this file needs, in the order it declared them"""
        rows = []
        for name, pair in unit["blocks"].items():
            at, words = pair
            row = [self.tag("imo"), self.word(self.opcodes()["buf"]),
                   self.tag("reg"), self.word(at),
                   self.tag("imm"), self.word(len(words)),
                   self.tag("buf")]
            for value in words:
                row.append(self.word(value))
            row.append(self.tag("fin"))
            rows.append(row)
        return rows

    ################# DRIVER ##################

    def architecture(self, lines: list):
        """the .arch of a file, so the machine is built before anything else"""
        for raw in self.strip_docs(lines):
            body = self.strip_comment(raw).strip()
            if not body.startswith(".arch"):
                continue
            parts = body.split()
            if len(parts) < 2:
                continue
            value = self.number(parts[1])
            if value in (8, 16, 32):
                return value
        return None

    def externs(self, lines: list, path: str):
        """every .extern of a file, as paths usually local but later based on PATH coverage"""
        out = []
        for raw in self.strip_docs(lines):
            body = self.strip_comment(raw).strip()
            if not body.startswith(".extern"):
                continue
            name = self.quoted(body)
            if name is None:
                self.errors.append(f".extern needs a file in quotes: {body}")
                continue
            out.append(os.path.join(os.path.dirname(path), name))
        return out

    def assemble(self, path: str):
        """a file into rows of machine words. the whole job"""
        raw_lines = self.read(path)
        if not raw_lines:
            return []
        found = self.architecture(raw_lines)
        if found is not None:
            self.arch = found
            self.cpu = self.make_cpu(found)
            self.string = self.make_strings(found)
        self.origin = self.block_origins.get(self.arch, 60000)

        self.shared = {}
        """constants an import leaves behind for the files after it"""
        self.taken = 0
        """how many words the blocks of the earlier files took"""

        units = self.unit(path, [])
        if not units:
            return []
        units[-1]["external"] = False

        for unit in units:
            self.unit_pass_one(unit)

        size = self.prologue_size(units)
        at = size
        for unit in units:
            unit["base"] = at
            at += unit["count"]

        labels, constants = self.merge(units)
        rows = self.prologue(units)

        for unit in units:
            self.labels = labels
            self.constants = constants
            self.blocks = unit["blocks"]
            self.scope = ""
            self.code = []
            self.listing_of(unit)
            blocks = self.unit_block_rows(unit)
            body = self.unit_rows(unit, labels)
            # the blocks go where the entry label is, not in front of the file or where ever it is
            entry = unit.get("entry", 0)
            rows += body[:entry] + blocks + body[entry:]

        self.labels = labels
        self.constants = constants
        self.check_program(rows)
        return rows

    def listing_of(self, unit: dict):
        self.listing.append(f"; {unit['name']} at #{unit['base']}, "
                            f"{unit['count']} instructions")
        return True

    def unit_rows(self, unit: dict, labels: dict):
        """pass two for one file, with the merged tables and its own base"""
        self.base = unit["base"] + unit.get("block_rows", 0)
        self.second_pass(unit["lines"])
        rows = []
        for entry in self.code:
            rows.append(entry["words"])
        return rows

    def check_program(self, rows: list):
        """the things that are only wrong once the whole file is read"""
        if not rows:
            self.errors.append("the file holds no instructions")
            return False
        if self.entry not in self.labels:
            self.warnings.append(f"there is no {self.entry}, so nothing says "
                                 f"where the program begins")
        last = self.code[-1]["source"].split()[0].lower() if self.code else ""
        if last and last not in self.terminators:
            self.warnings.append(f"the last instruction is {last}, which never "
                                 f"stops the machine")
        return True

    ################# OUTPUT ##################

    def write(self, rows: list, path: str):
        with open(path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(" ".join(row) + "\n")
        return True

    def write_listing(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"; {len(self.code)} instructions, {self.arch} bit\n")
            for name, value in self.constants.items():
                f.write(f"; {name} = {value}\n")
            for name, pair in self.blocks.items():
                f.write(f"; block {name} at {pair[0]}, {len(pair[1])} words\n")
            for name, value in self.labels.items():
                f.write(f"; label {name} -> #{value}\n")
            f.write("\n")
            for row in self.listing:
                f.write(row + "\n")
        return True

    def run(self, rows: list, limit: int = 20000):
        """load the rows into the machine and let it go"""
        for row in rows:
            self.cpu.sram.add(row)
        self.cpu.sram.__reset__()
        steps = 0
        while steps < limit:
            if self.cpu.HALTED or self.cpu.FETCH_ERROR or self.cpu.EXECUTE_ERROR:
                break
            self.cpu.fetch()
            if self.cpu.FETCH_ERROR:
                break
            self.cpu.execute()
            steps += 1
        return steps


def main():
    try:
        file = sys.argv[1]
    except IndexError:
        print("usage:\n  python -m programming.assembler file.casm [out.cobj] [-l] [-r]")
        exit(1)
    try:
        dest = sys.argv[2]
    except IndexError:
        dest = file.rsplit(".", 1)[0] + ".cobj"
    flags = sys.argv[3:]

    casm = Assembler()
    rows = casm.assemble(file)
    for problem in casm.errors:
        print(f"error: {problem}")
    for problem in casm.warnings:
        print(f"warning: {problem}")
    if casm.errors:
        exit(1)

    words = 0
    for row in rows:
        words += len(row)
    print(f"{file} -> {dest}  {len(rows)} instructions, {words} words, {casm.arch} bit")
    casm.write(rows, dest)
    if "-l" in flags:
        casm.write_listing(dest.rsplit(".", 1)[0] + ".lst")
        print(f"listing: {dest.rsplit('.', 1)[0]}.lst")
    if "-r" in flags:
        steps = casm.run(rows)
        print(f"ran {steps} instructions, halted={casm.cpu.HALTED}, "
              f"hint={casm.cpu.ERROR_HINT}")


if __name__ == "__main__":
    main()
