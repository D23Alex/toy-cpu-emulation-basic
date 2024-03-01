from enum import Enum
import json


class Opcode(str, Enum):
    IN = "in"
    OUT = "out"
    HLT = "hlt"

    ADD = "add"
    MOV = "mov"
    CMP = "cmp"
    SHB = "shb"

    JMP = "jmp"
    JZ = "jz"

    def __str__(self):
        return str(self.value)


def write_code(filename, code):
    with open(filename, "w", encoding="utf-8") as file:
        buf = []
        for instr in code:
            buf.append(json.dumps(instr))
        file.write("[" + ",\n ".join(buf) + "]")


def read_code(filename):
    with open(filename, encoding="utf-8") as file:
        code = json.loads(file.read())

    return code
