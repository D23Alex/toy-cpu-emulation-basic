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


class TranslatorException(Exception):
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
            raise TranslatorException("label == reg name")  # label == reg name
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


def place_instruction(line):
    if line[0] in no_arg_instructions:
        if len(line) > 1:
            raise TranslatorException("arity in a no arg instruction")
        no_arg_flags = ["noArg"]
        if line[0] != "hlt":
            no_arg_flags.append("io")
            if line[0] == "in":
                no_arg_flags.append("in")
        memory.append(
            {"word_number": len(memory), "type": "noArg", "opcode": symbol2opcode(line[0]), "flags": no_arg_flags}
        )
    elif line[0] in branching_instructions:
        if len(line) != 2:
            raise TranslatorException("arity in a branching instruction")
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
    elif line[0] in two_arg_instructions:
        if len(line) != 3:
            raise TranslatorException("arity in a two arg instruction")

        dest, arg = line[1], line[2]
        dest_indirect = is_indirect(dest)
        arg_indirect = is_indirect(arg)
        dest, arg = extract_from_brackets(dest), extract_from_brackets(arg)
        dest_is_register, arg_is_register = dest in registers, arg in registers
        dest, arg = convert_to_int_if_int(dest), convert_to_int_if_int(arg)

        if not is_indirect(dest) and isinstance(dest, int):
            raise TranslatorException("add 1, smth")

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
    else:
        raise TranslatorException("unknown")


def place_int(n):
    if n > 2147483647 or n < -2147483648:
        raise TranslatorException("int oub")
    memory.append({"value": n})


def place_string(string):
    current_word = 0
    memory.append({"value": len(string)})
    chars_placed = 0
    for char in string:
        current_word += ord(char) << 8 * (3 - (chars_placed % 4))
        chars_placed += 1
        if chars_placed % 4 == 0:
            memory.append({"value": current_word})
            current_word = 0
    if chars_placed % 4 != 0:
        memory.append({"value": current_word})


def place_data(line):
    if len(line) == 0:
        raise TranslatorException("no data")
    for term in line:
        if term[0] == "w" and isinstance(convert_to_int_if_int(term[1:]), int):
            for i in range(convert_to_int_if_int(term[1:])):
                place_int(0)
        elif isinstance(convert_to_int_if_int(term), int):
            place_int(convert_to_int_if_int(term))
        elif term[0] == "'" and term[-1] == "'":
            place_string(term[1:-1])
        else:
            raise TranslatorException("some wrong with data")


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
            raise TranslatorException("data without label")  # ошибка - данные без метки
        else:
            place_data(line)

    for word in memory:
        for keyword in {"value", "address"}:
            if keyword in word and isinstance(word[keyword], str):
                if word[keyword] not in label_mapping and word[keyword] not in registers:
                    raise TranslatorException("undeclared label", word[keyword])
                if word[keyword] not in registers:
                    word[keyword] = label_mapping[word[keyword]]
    return memory


def main(source, target):
    """Функция запуска транслятора. Параметры -- исходный и целевой файлы."""
    with open(source, encoding="utf-8") as f:
        source = f.read()

    code = translate(source)

    write_code(target, code)
    print("source LoC:", len(source.split("\n")), "machine words:", len(code))


if __name__ == "__main__":
    assert len(sys.argv) == 3, "Wrong arguments: translator.py <input_file> <target_file>"
    _, source, target = sys.argv
    main(source, target)
