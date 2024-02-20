"""
--- INFETCH
1) ip -> ar
2) mem -> dr

Задача - как реализовать переход без условий? Решения:
1) в каждой команде есть бит, всегда равный единице
2) помимо cr и zero flag, микрокоманде подаётся бит, равный единице
3) в каждой микрокоманде есть бит, который определяет, требуется проверка или нет
4) ничего из вышеперечисленного, ведь при каждом безусловном переходе существует какой-то бит (например, тип команды),
    который, очевидно, равен единице
пока что склоняюсь к четвертому

// TODO: результат действий по идее сохраняется в DSTBUF, а затем либо в 1 из регистров либо в память
// но в принципе его можно сразу положить в DR

// TODO: ARMEM и/или ARRD при работе с памятью

// TODO: пока что считаем, что по дефолту на каждом входе АЛУ нули и алу выполняет сумму

// TODO: написать про упрощение - add a b могло бы поместиться в одной команде, но размещается в двух

// TODO: выбор регистра можно ускорить, название регистра - 0001, 0010, 0100, 1000 - тут 1 это из какого регистра читаем
// или можно сказать - унифицировать
// последние 4 бита из dr идут на выбор регистра

// TODO: написать в отчете про выбор между:
1) обобщением команд с двумя аргументами, двумя буферными регистрами, лишними действиями и даже обращениями к памяти,
но при этом простой и компактный микрокод
2) микрокод для всех комбинаций команд с типами аргументов с видами адресаций

// TODO: изменить компилятор, чтобы он расставлял все флаги (проверяемые здесь биты)
предполагается, что команда будет представлена как множество флагов, равный единице, например
{"twoArg", "add", "arg_indirect", "dest_is_register", "arg_is_register", ""}


на вход схемы, проверяющей бит, подаётся CR, zero-flag и всегда равный единице бит

"""

from enum import Enum


class Latches(str, Enum):
    IPRD = "instruction-pointer-read"
    IPWR = "instruction-pointer-write"
    ARWR = "address-register-write"
    ARMEM = "address-register-to-memory"  # = записать в память
    MEMTODR = "memory-to-data-register"
    DRRD = "data-register-read"
    DRWR = "data-register-write"
    CRRD = "command-register-read"
    CRWR = "command-register-write"
    LONE = "one-in-left-alu"
    ARGBUFRD = "argument-buffer-read"
    ARGBUFWR = "argument-buffer-write"
    DSTBUFRD = "destination-buffer-read"
    DSTBUFWR = "destination-buffer-write"
    REGRD = "register-read-by-dr"  # прочесть указанный в последних 4 битах dr регистр
    REGWR = "write-register"
    ALUSUB = "alu-subtraction-mode"
    SHB = "shift-byte"

    def __str__(self):
        return str(self.value)


class Micro:
    commands = [
        {"label": "INFETCH",
         "control_flow": False, "latches": {Latches.IPRD, Latches.ARWR}},
        {"control_flow": False, "latches": {Latches.ARMEM, Latches.MEMTODR, Latches.IPRD, Latches.LONE, Latches.IPWR}},
        {"control_flow": False, "latches": {Latches.DRRD, Latches.CRWR}},
        {"control_flow": True, "check": "noArg", "zero_flag_required": False, "goto": "NOARG"},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "TWOARG"},

        {"label": "BRANCH",
         "control_flow": True, "check": "jmp", "zero_flag_required": False, "goto": "JMP"},
        {"control_flow": True, "check": "branch", "zero_flag_required": True, "goto": "INFETCH"},
        {"label": "JMP",
         "control_flow": False, "latches": {Latches.CRRD, Latches.IPWR}},
        {"control_flow": True, "check": "branch", "zero_flag_required": False, "goto": "INFETCH"},  # 100%

        {"label": "TWOARG",
         "control_flow": True, "check": "dest_indirect", "zero_flag_required": False, "goto": "DESTISINDIRECT"},
        {"label": "DESTISREGDIRECT",
         "control_flow": False, "latches": {Latches.REGRD, Latches.DSTBUFWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "ARGFETCH"},  # 100%
        {"label": "DESTISINDIRECT",
         "control_flow": True, "check": "dest_is_register", "zero_flag_required": False, "goto": "LBL1"},
        {"control_flow": False, "latches": {Latches.CRRD, Latches.ARWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "DESTFROMMEM"},  # 100%
        {"label": "LBL1",
         "control_flow": False, "latches": {Latches.REGRD, Latches.ARWR}},
        {"label": "DESTFROMMEM",
         "control_flow": False, "latches": {Latches.ARMEM, Latches.MEMTODR}},
        {"control_flow": False, "latches": {Latches.DRRD, Latches.DSTBUFWR}},

        {"label": "ARGFETCH",
         "control_flow": False, "latches": {Latches.IPRD, Latches.ARWR}},
        {"control_flow": False, "latches": {Latches.ARMEM, Latches.MEMTODR, Latches.IPRD, Latches.LONE, Latches.IPWR}},
        {"control_flow": True, "check": "arg_indirect", "zero_flag_required": False, "goto": "ARGISINDIRECT"},
        {"label": "ARGISDIRECT",
         "control_flow": True, "check": "arg_is_register", "zero_flag_required": False, "goto": "ARGISREGDIRECT"},
        {"control_flow": False, "latches": {Latches.CRRD, Latches.ARGBUFWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "EXECUTION"},  # 100%
        {"label": "ARGISREGDIRECT",
         "control_flow": False, "latches": {Latches.REGRD, Latches.ARGBUFWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "EXECUTION"},  # 100%
        {"label": "ARGISINDIRECT",
         "control_flow": True, "check": "arg_is_register", "zero_flag_required": False, "goto": "LBL2"},
        {"control_flow": False, "latches": {Latches.CRRD, Latches.ARWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "ARGFROMMEM"},  # 100%
        {"label": "LBL2",
         "control_flow": False, "latches": {Latches.REGRD, Latches.ARWR}},
        {"label": "ARGFROMMEM",
         "control_flow": False, "latches": {Latches.ARMEM, Latches.MEMTODR}},
        {"control_flow": False, "latches": {Latches.DRRD, Latches.ARGBUFWR}},

        {"label": "EXECUTION",
         "control_flow": True, "check": "add_or_cmp", "zero_flag_required": False, "goto": "ADDORCMP"},
        {"label": "MOVORSHB",
         "control_flow": True, "check": "shb", "zero_flag_required": False, "goto": "SHB"},
        {"label": "MOV",
         "control_flow": False, "latches": {Latches.ARGBUFRD, Latches.DSTBUFWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "FINISHEXECUTION"},  # 100%
        {"label": "SHB",
         "control_flow": False, "latches": {Latches.ARGBUFRD, Latches.DSTBUFWR, Latches.SHB}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "FINISHEXECUTION"},  # 100%
        {"label": "ADDORCMP",
         "control_flow": True, "check": "cmp", "zero_flag_required": False, "goto": "CMP"},
        {"label": "ADD",
         "control_flow": False, "latches": {Latches.DSTBUFRD, Latches.ARGBUFRD, Latches.DSTBUFWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "FINISHEXECUTION"},  # 100%
        {"label": "CMP",
         "control_flow": False, "latches": {Latches.DSTBUFRD, Latches.ARGBUFRD, Latches.ALUSUB, Latches.DSTBUFWR}},

        # если mov a 1, то cr->dr, db -> regwrite; если mov [1] 1, то cr -> ar, db -> dr, memwr;
        # если mov [a], 1, то cr -> dr, regread -> ar, потом то же, что и в предыдущем случае
        {"label": "FINISHEXECUTION",
         "control_flow": True, "check": "arg_indirect", "zero_flag_required": False, "goto": "RESULTWHENDESTINDIRECT"},
        {"label": "RESULTTOREGDIRECT",
         "control_flow": False, "latches": {Latches.CRRD, Latches.DRWR}},
        {"control_flow": False, "latches": {Latches.DSTBUFRD, Latches.REGWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "INFETCH"},  # 100%
        {"label": "RESULTWHENDESTINDIRECT",
         "control_flow": True, "check": "dest_is_register", "zero_flag_required": False, "goto": "RESULTTOREGINDIRECT"},
        {"label": "RESULTTOVALINDIRECT",
         "control_flow": False, "latches": {Latches.CRRD, Latches.ARWR}},
        {"control_flow": False, "latches": {Latches.DSTBUFRD, Latches.DRWR}},
        {"control_flow": False, "latches": {Latches.ARMEM}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "INFETCH"},  # 100%
        {"label": "RESULTTOREGINDIRECT",
         "control_flow": False, "latches": {Latches.CRRD, Latches.DRWR}},
        {"control_flow": False, "latches": {Latches.REGRD, Latches.ARWR}},
        {"control_flow": False, "latches": {Latches.DSTBUFRD, Latches.DRWR}},
        {"control_flow": False, "latches": {Latches.ARMEM}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "INFETCH"},  # 100%

    ]
