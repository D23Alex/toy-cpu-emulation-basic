import functools
from enum import Enum
from typing import ClassVar


class Signals(str, Enum):
    IPRD = "instruction-pointer-read"
    IPWR = "instruction-pointer-write"
    ARWR = "address-register-write"
    MEMWR = "write-to-memory"
    MEMRD = "read-from-memory"
    DRRD = "data-register-read"
    DRWR = "data-register-write"
    CRRD = "command-register-read"
    CRWR = "command-register-write"
    LINC = "increment-left-alu"
    ARGBUFRD = "argument-buffer-read"
    ARGBUFWR = "argument-buffer-write"
    DSTBUFRD = "destination-buffer-read"
    DSTBUFWR = "destination-buffer-write"
    REGWR = "write-register"
    ALUSUB = "alu-subtraction-mode"
    SHB = "shift-byte"
    REGRDDST = "REGRDDST"
    REGRDARG = "REGRDARG"
    HLT = "hlt"
    IN = "in"
    OUT = "out"
    SETZ = "set-z"

    def __str__(self):
        return str(self.value)


class Micro:
    mc_pointer = 0

    @functools.cache
    def mc_pointer_by_label(self, label):
        for i in range(len(self.commands)):
            if "label" in self.commands[i] and self.commands[i]["label"] == label:
                return i
        return -1

    def simulate_tick_and_return_signals(self, cr, zero_flag):
        current_mc = self.commands[self.mc_pointer]
        self.mc_pointer += 1
        if not current_mc["control_flow"]:
            return current_mc["signals"]
        if current_mc["check"] in cr["flags"] and (zero_flag or not current_mc["zero_flag_required"]):
            self.mc_pointer = self.mc_pointer_by_label(current_mc["goto"])
        return {}

    commands: ClassVar = [
        {"label": "INFETCH", "control_flow": False, "signals": {Signals.IPRD, Signals.ARWR}},
        {"control_flow": False, "signals": {Signals.MEMRD, Signals.DRWR, Signals.IPRD, Signals.LINC, Signals.IPWR}},
        {"control_flow": False, "signals": {Signals.DRRD, Signals.CRWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "TWOARG"},
        {"control_flow": True, "check": "noArg", "zero_flag_required": False, "goto": "NOARG"},
        {"label": "BRANCH", "control_flow": True, "check": "jmp", "zero_flag_required": False, "goto": "JMP"},
        {"control_flow": True, "check": "branch", "zero_flag_required": True, "goto": "JMP"},
        {"control_flow": True, "check": "branch", "zero_flag_required": False, "goto": "INFETCH"},  # 100%
        {"label": "JMP", "control_flow": False, "signals": {Signals.CRRD, Signals.IPWR}},
        {"control_flow": True, "check": "branch", "zero_flag_required": False, "goto": "INFETCH"},  # 100%
        {"label": "NOARG", "control_flow": True, "check": "io", "zero_flag_required": False, "goto": "IO"},
        {"label": "HLT", "control_flow": False, "signals": {Signals.HLT}},
        {"label": "IO", "control_flow": True, "check": "in", "zero_flag_required": False, "goto": "IN"},
        {"label": "OUT", "control_flow": False, "signals": {Signals.OUT}},
        {"control_flow": True, "check": "noArg", "zero_flag_required": False, "goto": "INFETCH"},  # 100%
        {"label": "IN", "control_flow": False, "signals": {Signals.IN}},
        {"control_flow": True, "check": "noArg", "zero_flag_required": False, "goto": "INFETCH"},  # 100%
        {
            "label": "TWOARG",
            "control_flow": True,
            "check": "dest_indirect",
            "zero_flag_required": False,
            "goto": "DESTISINDIRECT",
        },
        {"label": "DESTISREGDIRECT", "control_flow": False, "signals": {Signals.REGRDDST, Signals.DSTBUFWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "ARGFETCH"},  # 100%
        {
            "label": "DESTISINDIRECT",
            "control_flow": True,
            "check": "dest_is_register",
            "zero_flag_required": False,
            "goto": "LBL1",
        },
        {"control_flow": False, "signals": {Signals.CRRD, Signals.ARWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "DESTFROMMEM"},  # 100%
        {"label": "LBL1", "control_flow": False, "signals": {Signals.REGRDDST, Signals.ARWR}},
        {"label": "DESTFROMMEM", "control_flow": False, "signals": {Signals.DRWR, Signals.MEMRD}},
        {"control_flow": False, "signals": {Signals.DRRD, Signals.DSTBUFWR}},
        {
            "label": "ARGFETCH",
            "control_flow": True,
            "check": "arg_indirect",
            "zero_flag_required": False,
            "goto": "ARGISINDIRECT",
        },
        {
            "label": "ARGISDIRECT",
            "control_flow": True,
            "check": "arg_is_register",
            "zero_flag_required": False,
            "goto": "ARGISREGDIRECT",
        },
        {"label": "ARGISVALUEDIRECT", "control_flow": False, "signals": {Signals.IPRD, Signals.ARWR}},
        {"control_flow": False, "signals": {Signals.IPRD, Signals.LINC, Signals.IPWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "ARGFROMMEM"},  # 100%
        {"label": "ARGISREGDIRECT", "control_flow": False, "signals": {Signals.REGRDARG, Signals.ARGBUFWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "EXECUTION"},  # 100%
        {
            "label": "ARGISINDIRECT",
            "control_flow": True,
            "check": "arg_is_register",
            "zero_flag_required": False,
            "goto": "LBL2",
        },
        {"control_flow": False, "signals": {Signals.IPRD, Signals.ARWR}},
        {"control_flow": False, "signals": {Signals.MEMRD, Signals.DRWR, Signals.IPRD, Signals.LINC, Signals.IPWR}},
        {"control_flow": False, "signals": {Signals.DRRD, Signals.ARWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "ARGFROMMEM"},  # 100%
        {"label": "LBL2", "control_flow": False, "signals": {Signals.REGRDARG, Signals.ARWR}},
        {"label": "ARGFROMMEM", "control_flow": False, "signals": {Signals.DRWR, Signals.MEMRD}},
        {"control_flow": False, "signals": {Signals.DRRD, Signals.ARGBUFWR}},
        {
            "label": "EXECUTION",
            "control_flow": True,
            "check": "add_or_cmp",
            "zero_flag_required": False,
            "goto": "ADDORCMP",
        },
        {"label": "MOVORSHB", "control_flow": True, "check": "shb", "zero_flag_required": False, "goto": "SHB"},
        {"label": "MOV", "control_flow": False, "signals": {Signals.ARGBUFRD, Signals.DSTBUFWR, Signals.SETZ}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "FINISHEXECUTION"},  # 100%
        {
            "label": "SHB",
            "control_flow": False,
            "signals": {Signals.ARGBUFRD, Signals.DSTBUFWR, Signals.SHB, Signals.SETZ},
        },
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "FINISHEXECUTION"},  # 100%
        {"label": "ADDORCMP", "control_flow": True, "check": "cmp", "zero_flag_required": False, "goto": "CMP"},
        {
            "label": "ADD",
            "control_flow": False,
            "signals": {Signals.DSTBUFRD, Signals.ARGBUFRD, Signals.DSTBUFWR, Signals.SETZ},
        },
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "FINISHEXECUTION"},  # 100%
        {
            "label": "CMP",
            "control_flow": False,
            "signals": {Signals.DSTBUFRD, Signals.ARGBUFRD, Signals.ALUSUB, Signals.SETZ},
        },
        {
            "label": "FINISHEXECUTION",
            "control_flow": True,
            "check": "dest_indirect",
            "zero_flag_required": False,
            "goto": "RESULTWHENDESTINDIRECT",
        },
        {"label": "RESULTTOREGDIRECT", "control_flow": False, "signals": {Signals.DSTBUFRD, Signals.REGWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "INFETCH"},  # 100%
        {
            "label": "RESULTWHENDESTINDIRECT",
            "control_flow": True,
            "check": "dest_is_register",
            "zero_flag_required": False,
            "goto": "RESULTTOREGINDIRECT",
        },
        {"label": "RESULTTOVALINDIRECT", "control_flow": False, "signals": {Signals.CRRD, Signals.ARWR}},
        {"control_flow": False, "signals": {Signals.DSTBUFRD, Signals.DRWR}},
        {"control_flow": False, "signals": {Signals.MEMWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "INFETCH"},  # 100%
        {"label": "RESULTTOREGINDIRECT", "control_flow": False, "signals": {Signals.REGRDDST, Signals.ARWR}},
        {"control_flow": False, "signals": {Signals.DSTBUFRD, Signals.DRWR}},
        {"control_flow": False, "signals": {Signals.MEMWR}},
        {"control_flow": True, "check": "twoArg", "zero_flag_required": False, "goto": "INFETCH"},  # 100%
    ]
