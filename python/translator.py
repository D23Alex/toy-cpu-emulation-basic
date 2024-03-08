#!/usr/bin/python3
"""Транслятор в машинный код."""

import re
import shlex
import sys

from isa import Opcode, write_code

memory = []
label_mapping = {}

no_arg_instructions = {"hlt", "in", "out"}
branching_instructions = {"jmp", "jz"}
two_arg_instructions = {"add", "mov", "cmp", "shb"}

registers = {"a", "b", "c", "d"}

start_label = "start"


class TranslatorError(Exception):
    pass


def symbol2opcode(symbol):
    return {
        "in": Opcode.IN,
        "out": Opcode.OUT,
        "hlt": Opcode.HLT,
        "mov": Opcode.MOV,
        "add": Opcode.ADD,
        "cmp": Opcode.CMP,
        "shb": Opcode.SHB,
        "jmp": Opcode.JMP,
        "jz": Opcode.JZ,
    }.get(symbol)


def remove_comment(line):
    comment_position = line.find(";")
    if comment_position == -1:
        return line
    return line[0:comment_position]


def convert_to_int_if_int(string):
    try:
        return int(string)
    except ValueError:
        return string


def process_label(line):
    if re.fullmatch("[a-z]+:", line[0]):
        if line[0] in registers:
            raise TranslatorError("label-is-reg-name")
        label_mapping[line[0][0:-1]] = len(memory)
        line.pop(0)
        return True
    return False


def is_indirect(arg):
    return arg[0] == "[" and arg[-1] == "]"


def extract_from_brackets(arg):
    if arg[0] == "[" and arg[-1] == "]":
        return arg[1:-1]
    return arg


def place_no_arg_instruction(line):
    if len(line) > 1:
        raise TranslatorError("arity")
    no_arg_flags = ["noArg"]
    if line[0] != "hlt":
        no_arg_flags.append("io")
        if line[0] == "in":
            no_arg_flags.append("in")
    memory.append(
        {"word_number": len(memory), "type": "noArg", "opcode": symbol2opcode(line[0]), "flags": no_arg_flags}
    )


def place_branching_instruction(line):
    if len(line) != 2:
        raise TranslatorError("arity")
    branch_flags = ["branch"]
    if line[0] == "jmp":
        branch_flags.append("jmp")
    memory.append(
        {
            "word_number": len(memory),
            "type": "branch",
            "opcode": symbol2opcode(line[0]),
            "flags": branch_flags,
            "address": line[1],
        }
    )


def place_two_arg_instruction(line):
    if len(line) != 3:
        raise TranslatorError("arity")

    dest, arg = line[1], line[2]
    dest_indirect = is_indirect(dest)
    arg_indirect = is_indirect(arg)
    dest, arg = extract_from_brackets(dest), extract_from_brackets(arg)
    dest_is_register, arg_is_register = dest in registers, arg in registers
    dest, arg = convert_to_int_if_int(dest), convert_to_int_if_int(arg)

    if not is_indirect(dest) and isinstance(dest, int):
        raise TranslatorError("dest-direct-number")

    two_arg_flags = ["twoArg"]
    command = {
        "word_number": len(memory),
        "type": "twoArg",
        "opcode": symbol2opcode(line[0]),
        "flags": two_arg_flags,
    }
    memory.append(command)
    if dest_indirect:
        two_arg_flags.append("dest_indirect")
    if arg_indirect:
        two_arg_flags.append("arg_indirect")

    if dest_is_register:
        two_arg_flags.append("dest_is_register")
        command["dest_reg"] = dest
    else:
        command["address"] = dest

    if arg_is_register:
        two_arg_flags.append("arg_is_register")
        command["arg_reg"] = arg
    elif arg_indirect:
        memory.append({"address": arg})
    else:
        memory.append({"value": arg})

    if line[0] == "add" or line[0] == "cmp":
        two_arg_flags.append("add_or_cmp")
    if line[0] == "shb":
        two_arg_flags.append("shb")
    if line[0] == "cmp":
        two_arg_flags.append("cmp")


def place_instruction(line):
    if line[0] in no_arg_instructions:
        place_no_arg_instruction(line)
    elif line[0] in branching_instructions:
        place_branching_instruction(line)
    elif line[0] in two_arg_instructions:
        place_two_arg_instruction(line)
    else:
        raise TranslatorError("unknown-command")


def place_int(n):
    if n > 2147483647 or n < -2147483648:
        raise TranslatorError("int-oub")
    memory.append({"value": n})


def place_string(string):
    memory.append({"value": len(string)})
    for char in string:
        memory.append({"value": ord(char)})


def place_data(line):
    if len(line) == 0:
        raise TranslatorError("no-data")
    for term in line:
        if term[0] == "w" and isinstance(convert_to_int_if_int(term[1:]), int):
            for i in range(convert_to_int_if_int(term[1:])):
                place_int(0)
        elif isinstance(convert_to_int_if_int(term), int):
            place_int(convert_to_int_if_int(term))
        elif term[0] == "'" and term[-1] == "'":
            place_string(term[1:-1])
        else:
            raise TranslatorError("bad-data")


def translate(text):
    global memory
    global label_mapping
    memory = []
    label_mapping = {}

    valid_lines = list(
        map(
            lambda line: shlex.split(line, posix=False),
            filter(lambda line: len(line) > 0, map(lambda line: remove_comment(line).strip(), text.split("\n"))),
        )
    )

    valid_lines.append(["hlt"])

    memory.append({"word_number": len(memory), "opcode": "jmp", "flags": ["branch", "jmp"], "address": "start"})
    for line in valid_lines:
        starts_with_label = process_label(line)
        is_instruction = line[0] in no_arg_instructions.union(branching_instructions).union(two_arg_instructions)
        if is_instruction:
            place_instruction(line)
        elif not starts_with_label:
            raise TranslatorError("no-label")  # ошибка - данные без метки
        else:
            place_data(line)

    for word in memory:
        for keyword in {"value", "address"}:
            if keyword in word and isinstance(word[keyword], str):
                if word[keyword] not in label_mapping and word[keyword] not in registers:
                    raise TranslatorError("undeclared-label", word[keyword])
                if word[keyword] not in registers:
                    word[keyword] = label_mapping[word[keyword]]
    return memory


def main(source, target):
    """Функция запуска транслятора. Параметры -- исходный и целевой файлы."""
    with open(source, encoding="utf-8") as f:
        source = f.read()

    try:
        code = translate(source)
        write_code(target, code)
        print("source LoC:", len(source.split("\n")), "machine words:", len(code))
    except TranslatorError as e:
        print("failed to compile - ", repr(e))


if __name__ == "__main__":
    assert len(sys.argv) == 3, "Wrong arguments: translator.py <input_file> <target_file>"
    _, source, target = sys.argv
    main(source, target)
