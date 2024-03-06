import logging
import sys

from isa import read_code
from micro import Micro, Signals


class DataPathError(Exception):
    pass


class DataPath:
    """
       reg_wr (decoder)◄────┬─────────────────────────────┐   *arg_reg
          │   │             │                             │    ▲
          ▼   ▼             └──────────►┌────┐            │    │  ┌───────────────────────────────────────────────────┐
       ┌───────┐                        │    │            │    │  │                                                   │
       │ MUX   │   dst_read────────────►│    │            │    │  │                                                   │
       └┬──────┘►┌───┐                  │    │    ┌────┐  │    │  │    ┌──────────────┐◄────dr_write                  │
        │   bit_0│ a ├─────────────┬───►│MUX │    │    │◄─┴────┴──┴────┤              │                               │
        │  ┌────►└───┘             │    │    │    │    │               │data_reg      │     ┌──────────────┐          │
        │  │           ┌────────┬──┼───►│    │    │    │  to_micro     └──────────────┘◄────┤    MUX       │          │
        │  │ bit_1     │        │  │    │    │    │    │      ▲                             │              │◄──────┐  │
        ├──┼────►┌───┬─┘ ┌──────┼──┼───►│    ├─┐  │    │      │                             └──────────────┘       │  │
        │  │     │ b │   │      │  │    │    │ │  │    │◄─────┴───┬──────────────┐◄────cr_write       ▲  ▲         │  │
        │  ├────►└───┘   │ ┌────┼──┼───►│    │ │  │MUX │          │ command_reg  │                    │  │         │  │
        │  │             │ │    │  │    │    │ │  │    │◄─────    └──────────────┘◄───────────────────┤  │         │  │
      b │  │ bit_2       │ │    │  │    └────┘ │  │    │     cr_read                                  │  mem_rd    │  │
      i ├──┼────►┌───┬───┤ │    │  │           │  │    │◄───────────────┬──────────────┬─────ip_write │  │         │  │
      t │  │     │ c │   │ │    ▼  ▼      ┌────┘  │    │                │ instr_pointer│              │ ┌┘         │  ▼
 in   _ │  ├────►└───┘   │ │   ┌────┐     │       │    │◄──────┐        └──────────────┘◄─────────────┤ │ ┌────────┴───┐
 │    3┌┘  │    output◄┐ │ │   │    │     │       │    │       └─────┐                                │ │ │    MEM     │
 │     ▼   │           │ │ │   │    │     │       │    │◄────dr_read │  ┌──────────────┬─────ab_write │ │ │            │
 ├──►(or)──┼────►┌───┬─┘ └─┼──►│MUX │     │       │    │             └──┤    arg_buffer│              │ │ └────────────┘
 │         │     │ d │     │   │    │     │       │    │◄────ip_read    └──────────────┘◄─────────────┤ │  ▲   ▲   ▲
 └─►┌─┐  ┌─┼────►└───┴─────┴──►│    │     │     ┌─┤    │                                              │ └──┘   │   │
    │ │  │ │                   │    │     │     │ └────┘◄────ab_read    (=0?)───────────────►┌───┐    │        m   │
    │M├──┘ │       arg_read───►│    │     ▼     │                         │    shift_byte    │ z ├─┐  │        e   │
    │U│    │                   │    ├───►(+)──┐ ├────┐             ┌───┐  │        │     ───►└───┘ │  │        m   │
┌──►│X│    │      *arg_reg────►└────┘     ▲   │ │    │  alu_sub───►│   │  │        │     set_zero  │  │        _   │
│   │ │    │ dst_write                    │ (+1)└─┐  │             │MUX│  │        │               │  │        w   │
│ ─►└─┘    │ ───►┌───────────────┐  ┌───┐ │ ▲ │   ▼  │             │   │  │        ▼               ▼  │        r   │
│ input    │     │ dst_buffer    ├─►│   ├─┘ │ ├─►(+)─┼────────────►│   ├──┴──►(shift_byte)   to_micro │            │
│          ├────►└───────────────┘  │MUX│   │ │      │             │   │           │                  │            │
│          │                        │   │   │ │      ▼             │   │           ├──────────────────┘            │
│          │              dst_read─►└───┘   │ └────►(-)───────────►│   │           │                               │
│          │                                │                      └───┘           │    ar_write───►┌────────────┐ │
│          │                              left_inc                                 │                │address_reg ├─┘
└──────────┴───────────────────────────────────────────────────────────────────────┴──low_21_bits──►└────────────┘
    """

    address_size = 21

    a = 0
    b = 0
    c = 0
    d = 0
    db = 0
    dr = 0
    cr = 0
    ip = 0
    ab = 0
    ar = 0
    zero = False

    input_buffer = None
    output_buffer = None

    def __init__(self, input_buffer):
        self.input_buffer = input_buffer
        self.output_buffer = []

    def read_reg(self, reg):
        if reg == "a":
            return self.a
        if reg == "b":
            return self.b
        if reg == "c":
            return self.c
        if reg == "d":
            return self.d
        raise DataPathError

    def write_reg(self, reg, val):
        if reg == "a":
            self.a = val
        elif reg == "b":
            self.b = val
        elif reg == "c":
            self.c = val
        elif reg == "d":
            self.d = val
        else:
            raise DataPathError

    def do_io(self, signals):
        if Signals.OUT in signals:
            self.d &= 0xFFFFFFFF
            high_byte = (self.d >> 24) & 0xFF
            if high_byte > 126 or (high_byte < 32 and high_byte != 10):
                high_byte_char = "\\x{:02x}".format(high_byte)
            else:
                high_byte_char = chr(high_byte)
            logging.debug("output: %s << %s", repr("".join(self.output_buffer)), repr(high_byte_char))
            self.output_buffer.append(high_byte_char)
        if Signals.IN in signals:
            symbol_code = 0
            try:
                symbol_code = ord(self.input_buffer.pop(0))
            except IndexError:
                pass
            assert -128 <= symbol_code <= 127, "input token is out of bound: {}".format(symbol_code)
            self.d = symbol_code  # read to low byte
            logging.debug("input: %s", repr(chr(symbol_code)))

    def read_left_and_right_alu(self, signals):
        alu_left = 0
        if Signals.REGRDDST in signals:
            alu_left = self.read_reg(self.cr["dest_reg"])
        if Signals.REGRDARG in signals:
            alu_left = self.read_reg(self.cr["arg_reg"])
        if Signals.DSTBUFRD in signals:
            alu_left = self.db
        if Signals.LINC in signals:
            alu_left += 1

        alu_right = 0
        if Signals.DRRD in signals:
            alu_right = self.dr
        if Signals.CRRD in signals:
            alu_right = self.cr
        if Signals.IPRD in signals:
            alu_right = self.ip
        if Signals.ARGBUFRD in signals:
            alu_right = self.ab
        return alu_left, alu_right

    def do_alu_math(self, signals, alu_left, alu_right):
        if not isinstance(alu_right, int) and alu_left == 0:
            res = alu_right.copy()
            if "value" in res:  # превращаем {"value": 123} в 123
                res = res["value"]
        elif Signals.ALUSUB in signals:
            res = alu_left - alu_right
            if Signals.SETZ in signals:
                self.zero = res == 0
        else:
            res = alu_left + alu_right
            if Signals.SETZ in signals:
                self.zero = res == 0

        if isinstance(res, int) and Signals.SHB in signals:
            res = res << 8
        return res

    def write_to_registers(self, signals, res):
        if Signals.ARWR in signals:
            if isinstance(res, int):
                self.ar = res % (2**self.address_size)
            else:
                self.ar = res["address"]

        if Signals.IPWR in signals:
            if isinstance(res, int):
                self.ip = res % (2**self.address_size)
            else:
                self.ip = res["address"]

        if Signals.CRWR in signals:
            self.cr = res
        if Signals.ARGBUFWR in signals:
            self.ab = res
        if Signals.DSTBUFWR in signals:
            self.db = res

        if Signals.REGWR in signals:
            self.write_reg(self.cr["dest_reg"], res)

    def memory_read_or_write(self, signals, res, memory):
        if Signals.DRWR in signals:
            if Signals.MEMRD in signals:
                if isinstance(memory[self.ar], int):
                    self.dr = memory[self.ar]
                else:
                    self.dr = memory[self.ar].copy()
            else:
                self.dr = res
        if Signals.MEMWR in signals:
            if isinstance(self.dr, int):
                memory[self.ar] = self.dr
            else:
                memory[self.ar] = self.dr.copy()

    def simulate_tick(self, memory, signals):
        self.do_io(signals)
        alu_left, alu_right = self.read_left_and_right_alu(signals)
        res = self.do_alu_math(signals, alu_left, alu_right)
        self.write_to_registers(signals, res)
        self.memory_read_or_write(signals, res, memory)


class ControlUnit:
    """
┌──────────────────────┐
│                      │
│                   ┌──┴───────────┐
│ ┌─────────────────┤              │
│ │                 │ microcode    │◄─────┐
│ │ latch_mc_ptr───►│              │      │
│ │                 │              │◄──┐  │
│ │      read_mc───►└─────┬────────┘   │  │
│ │                       │            │  │
│ │                    signals         │  │
│ │                       │           CR  │
│ │                       ▼            │  │
│ │                 ┌───────────────┬──┘ zero
│ │                 │               │     │
│ │      input─────►│   DataPath    ├─────┘
│ │                 │               │
│ │                 └┬───┬──────────┴───►output
│ │                  │   │     ▲
│ │                 AR   DR    │
│ │                  │   │     └────┐
│ │                  ▼   ▼          │
│ │                  ┌──────────┐   │
│ └─────────────────►│          ├───┘
│                    │ memory   │
└───────────────────►│          │
                     └──────────┘
    """

    data_path = None
    micro = None
    memory = None
    signals_from_micro = None

    _tick = 0

    def __init__(self, memory, data_path, micro):
        self.data_path = data_path
        self.micro = micro
        self.memory = memory
        self.signals_from_micro = {}

    def tick(self):
        self._tick += 1

    def current_tick(self):
        return self._tick

    def simulate_tick(self):
        self.signals_from_micro = self.micro.simulate_tick_and_return_signals(self.data_path.cr, self.data_path.zero)

        if Signals.HLT in self.signals_from_micro:
            raise StopIteration()

        self.data_path.simulate_tick(self.memory, self.signals_from_micro)
        self.tick()

    def __repr__(self):
        return "TICK: {} IP: {} DR: {} CR: {} ARG_BUF: {} a: {} b: {} c: {} d: {} DST_BUF: {} AR: {}".format(
            self._tick,
            self.data_path.ip,
            self.data_path.dr,
            self.data_path.cr,
            self.data_path.ab,
            self.data_path.a,
            self.data_path.b,
            self.data_path.c,
            self.data_path.d,
            self.data_path.db,
            self.data_path.ar,
        )


def simulation(code, input_tokens, memory_size, limit):
    micro = Micro()
    data_path = DataPath(input_tokens)
    memory = [0] * memory_size
    for i in range(len(code)):
        memory[i] = code[i]
    control_unit = ControlUnit(memory, data_path, micro)

    instr_counter = 0

    try:
        while instr_counter < limit:
            command_before_tick = data_path.cr
            control_unit.simulate_tick()
            if command_before_tick != data_path.cr:
                instr_counter += 1
            logging.info(control_unit)
    except EOFError:
        logging.warning("Input buffer is empty!")
    except StopIteration:
        pass

    if instr_counter >= limit:
        logging.warning("Limit exceeded!")
    logging.info("output_buffer: %s", repr("".join(data_path.output_buffer)))
    return "".join(data_path.output_buffer), instr_counter, control_unit.current_tick()


def main(code_file, input_file):
    code = read_code(code_file)
    with open(input_file, encoding="utf-8") as file:
        input_text = file.read()
        input_token = []
        for char in input_text:
            input_token.append(char)

    output, instr_counter, ticks = simulation(code, input_tokens=input_token, memory_size=1000, limit=10000)
    print("".join(output))
    print("instr_counter: ", instr_counter, "ticks:", ticks)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    main(code_file, input_file)
