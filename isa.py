from enum import Enum


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
