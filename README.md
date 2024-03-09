# Computer Systems Architecture lab 3

- Преподаватель: Пенской Александр Владимирович.
- `asm | cisc | neum | mc | tick | struct | stream | port | pstr | prob1 | [4]char`
- Базовый вариант.

Примечания:
- На всех схемах предполагается, что чтение (из регистров или из памяти) происходит на фронте сигнала тактового генератора, а запись -- на спаде.

## Язык программирования

``` ebnf
program ::= { line }

line ::= label instr [ comment ] "\n"
       | instr [ comment ] "\n"
       | label {data}
       | [ comment ] "\n"

label ::= label_name ":"

instr ::= op0
        | op1 label_name
        | op2 dest arg
        
op0 ::= "in"
      | "out"
      | "hlt"

op1 ::= "jmp"
      | "jz"
      
op2 ::= "add"
      | "cmp"
      | "mov"
      | "shb"
      
dest ::= a
      | b
      | c
      | d
      | [a]
      | [b]
      | [c]
      | [d]
      | "[" { <any of "0-9"> } "]"
      | "[" label_name "]"
      
arg ::= a
      | b
      | c
      | d
      | [a]
      | [b]
      | [c]
      | [d]
      | ["["] { <any of "0-9"> } ["]"]
      | ["["] label_name ["]"]
      
data ::= {<any of integer or string>}

integer ::= [ "-" ] { <any of "0-9"> }-

string ::= "'" <any symbols except "\n"> "'"

label_name ::= <any of "a-z"> { <any of "a-z"> }

comment ::= ";" <any symbols except "\n">
```

Код выполняется последовательно. Операции:

- `in` -- ввести извне значение и сохранить в младшем байте регистра d (символ)
- `out` -- напечатать значение из старшего байта регистра d (символ)
- `hlt` -- остановка системы
- `jmp addr` -- безусловный переход по заданному адресу или метке
- `jz addr` -- условный переход по заданному адресу или метке, если значение флага zero равно нулю
- `add dest arg` -- выполнение операции сложения dest и arg, поместить результат в dest
- `cmp dest arg` -- присвоить флагу zero значение 1 если arg == dest, 0 иначе
- `mov dest arg` -- поместить присвоить dest значение arg
- `shb dest arg` -- выполнить циклический сдвиг arg влево на 1 байт, полученное значение присвоить dest

Метки для переходов определяются на тех же строчках, куда необходимо совершить переход:

``` asm
label: in
```

И в другом месте (неважно, до или после определения) сослаться на эту метку:

``` asm
jmp label   ; --> `jmp 123`, где 123 - номер инструкции после объявления метки
```

Транслятор поставит на место использования метки адрес той инструкции, перед которой она определена.

В программе не может быть дублирующихся меток, определенных в разных местах с одним именем.

Память выделяется статически, при запуске модели. Видимость данных -- глобальная.


## Организация памяти

Регистры:
1. `a`, `b`, `c` (32 бита) -- регистры общего назначения, доступные программисту.
2. `d` (32 бита) -- доступный программисту регистр, через который происходит ввод-вывод. Ввод осуществляется в младший байт, вывод -- из старшего.
3. `AR` (21 бит) - адресный регистр, хранит адрес необходимой ячейки при обращении к памяти.
4. `DR` (32 бита) - регистр данных, хранит данные, записываемые в память или считываемые из неё.
5. `IP` (21 бит) - счётчик команд.
6. `CR` (32 бита) - регистр команд, хранит выполняемую инструкцию.
7. `DB` (32 бита) -- dest buffer -- буферный регистр для хранения первого аргумента двухаргументных команд (в коде именуется dest или destination, так как именно сюда будет записан результат)
8. `AB` (32 бита) -- argument buffer -- буферный регистр для хранения второго аргумента двухаргументных команд (в коде именуется argument или arg)
9. `Z` (1 bit) -- zero-flag.



ОЗУ:
1. Общая память для команд и данных. Одно слово -- 32 бита. Каждая ячейка может содержать как данные (одно 32 битное знаковое число или от 1 до 4 символов), так и команду или часть команды.
2. Homoiconicity -- не поддерживается (например, переместить команду или записать её в регистр можно, но производить арифметические операции нельзя; при попадании не команды в регистр команд симуляция прерывается)
3. Инструкции либо занимают целиком 1 машинное слово, либо 2 расположенных подряд машинных слова.
4. Для всех типов команд используется абсолютная адресация.
5. Команды с двумя аргументами могут считывать аргументы из памяти или записывать результат в память. Для этого литерал нужно поместить в квадратные скобки, например:
``` asm
label: 123
add a [b]; увеличить значение регистра a на число, хранящееся в памяти по адресу, равному значению регистра b
mov [label] 456; записать по адресу метки label (то есть по адресу 123) число 456
```
6. Знаковое число занимает одну ячейку
7. Строка занимает `1 + len(str)` ячеек, в первой хранится её длина, в каждой из последующих, хранится один символ.
8. На этапе компиляции литералы помещаются в память последовательно, начиная с адреса 1.
9. Размерность памяти -- 21, то есть существует возможность адресовать 2^21 слов.

## Система команд

Особенности процессора:

- Машинное слово -- 32 бита, знаковое.
- Доступ к памяти осуществляется по адресу, хранящемуся в специальном регистре `address_register` или `AR`.
- Обработка данных осуществляется по текущему адресу операциями `+` и `-`, а также через ввод/вывод.
- Поток управления:
    - инкремент `PC` после каждой инструкции;
    - условный (`jz`) и безусловный (`jmp`) переходы (использование см. в разделе транслятор).

### Набор инструкций

| Язык | Инструкция   | Кол-во тактов | Описание                                                    |
|:-----|:-------------|:--------------|:------------------------------------------------------------|
|`add` | addition     | 15-21         | 2 аргумента, сложить как знаковые числа, записать в первый  |
|`cmp` | comparison   | 15-21         | 2 аргумента, сравнить, выставить флаг zero                  |
|`mov` | writing      | 15-21         | 2 аргумента, первый - куда записать, второй - что записать  |
|`shb` | byte shift   | 15-21         | 2 аргумента, как `mov`, но сдвинуть второй аргумент на байт |
|`in`  | input        | 9             | ввести извне значение и сохранить в `d`                     |
|`out` | output       | 9             | напечатать значение из текущей ячейки (символ)              |
|`hlt` | halt         | 7             | остановка                                                   |
|`jmp` | jump to addr | 7             | безусловный переход                                         |
|`jz`  | jump if zero | 7 или 8       | переход, если в `Z` 1                                       |

Примечания: 
1. количество тактов предусматривает переход к декодированию след инструкции, то есть запись в счётчик микрокоманд нуля после выполнения (для всех команд, кроме hlt).
2. Количество тактов в команде jz зависит от того, чему равен `Z`.
3. Количество тактов в командах с двумя аргументами зависит от вида адресации каждого из аргументов. Из регистра в регистр - 15 тактов. Из памяти в память - до 21 такта.

### Кодирование инструкций

- Машинный код сериализуется в список JSON.
- Двухаргументные инструкции, в которых вторым аргументом выступает не регистр, а число (immediate value) или адрес, представлены двумя элементами списка, где второй элемент -- этот самый адрес или это самое число.
- Все остальные команды представлены одним элементом списка.
- Структура команд без аргументов: первый бит (бит двух аргументов) это 0, второй бит (бит отсутствия аргументов) это 1, третий бит (бит команды ввода-вывода) это 0 или 1, четвёртый бит в командах ввода вывода - это 1 для `in`, 0 для `out`.
- Структура команд ветвления: первый бит (бит двух аргументов) это 0, второй бит (бит отсутствия аргументов) это 0, третий бит это 1 для `jmp`, 0 для `jz`.
- Структура команд 2 аргументов: первый бит (бит двух аргументов) это 1, далее идут биты (1 аргумент регистр? 2 аргумент регистр? обращение к памяти для 1 аргумента? обращение к памяти для 2 аргумента?), далее в 2 битах закодировано 4 команды...
- Следующие 2 бита таких команд отведены под номер регистра, в который, возможно, будет запись, затем ещё 2 бита на регистр, из которого, возможно, будет чтение. оставшийся 21 бит - адрес (число), по которому, возможно, запишется результат...
- Следующее слово - число, являющееся вторым аргументом, или адрес второго аргумента. Исключение - при операции с двумя регистрами второго слова нет, команда кодируется одним словом.

Пример:

```json
[
    {"word_number": 0, "opcode": "jmp", "flags": ["branch", "jmp"], "address": 3},
    {"word_number": 1, "type": "twoArg", "opcode": "mov", "flags": ["twoArg", "arg_indirect", "dest_is_register"], "dest_reg": "a"},
    {"address": 6},
    {"word_number": 3, "type": "twoArg", "opcode": "mov", "flags": ["twoArg", "arg_indirect", "dest_is_register"], "dest_reg": "a"},
    {"address": 7},
    {"word_number": 5, "type": "noArg", "opcode": "hlt", "flags": ["noArg"]},
    {"value": 123},
    {"value": 456}
]
```

Этот код выполнится следующим образом: сначала выполнится переход на последнюю из команд `mov`, а первая будет пропущена. Затем в регистр `a` будет записано 456.
Первая из `mov` команд записала бы туда 123, то есть содержимое 6 ячейки, а не 7, но в данном примере исполниться ей не суждено.


где:

- `flags` - перечисленные ранее равные 1 биты
- `opcode` -- строка с кодом операции;
- `dest_reg`, `arg_reg` -- регистры-аргументы;
- `address` -- 21 битное число
- `value` -- 32 битное число
- `term` -- информация о связанном месте в исходном коде (если есть).

Типы данных в модуле [isa](./python/isa.py), где:

- `Opcode` -- перечисление кодов операций;

## Транслятор

Интерфейс командной строки: `translator.py <input_file> <target_file>`

Реализован в модуле [translator](./python/translator.py)

Метки из программы исчезают, а на место обращений к ним подставляются конкретные адреса.

Выполнение программы начинается с инструкции, помеченной меткой `start`.

## Модель процессора

Интерфейс командной строки: `machine.py <machine_code_file> <input_file>`

Реализовано в модуле: [machine](./python/machine.py).

### DataPath

``` text
       reg_wr (decoder)◄────┬───────────────dst_reg────────┬───►*arg_reg                                                
          │   │             │                              │                                                            
          ▼   ▼             └──────────►┌────┐             │      ┌───────────────────────────────────────────────────┐ 
       ┌───────┐                        │    │             │      │                                                   │ 
       │ MUX   │   dst_read────────────►│    │             │      │                                                   │ 
       └┬──────┘►┌───┐                  │    │    ┌────┐   │      │    ┌──────────────┐◄────dr_write                  │ 
        │   bit_0│ a ├─────────────┬───►│MUX │    │    │◄──┼──────┴────┤              │                               │ 
        │  ┌────►└───┘             │    │    │    │    │   │           │data_reg      │     ┌──────────────┐          │ 
        │  │           ┌────────┬──┼───►│    │    │    │   │           └──────────────┘◄────┤    MUX       │          │ 
        │  │ bit_1     │        │  │    │    │    │    │   │     ┌──►to_micro               │              │◄──────┐  │ 
        ├──┼────►┌───┬─┘ ┌──────┼──┼───►│    ├─┐  │    │   │     │                          └──────────────┘       │  │ 
        │  │     │ b │   │      │  │    │    │ │  │    │◄──┴─────┴┬──────────────┐◄────cr_write       ▲  ▲         │  │ 
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
```

Реализован в классе `DataPath`.

`MEM` -- однопортовая память, поэтому либо читаем, либо пишем.

Сигналы (множество сигналов возвращается функцией simulate_tick устройства микропрограммного управления и передаётся в качестве аргумента функции simulate_tick DataPath):

- `cr_read`, `dr_read`, `ip_read`, `dr_read`, `ab_read`, `dst_read`, `ar_write`, `set_zero` - прочитать значение соответствующего регистра и подать на один из входов АЛУ.
- `cr_write`, `dr_write`, `ip_write`, `dr_write`, `ab_write`, `dst_write`, `ar_write`, `set_zero` - выполнить запись в соответствующий регистр.
- `dst_read` - считать и подать на левый вход АЛУ содержимое одного из регистров `a`, `b`, `c`, `d`. Какого именно - определяется по битам 8-9 регистра `data_reg`.
- `arg_read` - считать и подать на левый вход АЛУ содержимое одного из регистров `a`, `b`, `c`, `d`. Какого именно - определяется по битам 10-11 регистра `data_reg`.
- `alu_sub` - выполнить не сложение, а вычитание (левый вход АЛУ - правый вход АЛУ).
- `in` - извлечь из входного буфера значение и записать в `d`.
- `mem_rd` - считать слово, находящееся по адресу, содержащемуся в `address_reg`, из памяти в `data_register`.
- `mem_wr` - записать слово слово, находящееся в `data_reg`, по адресу, содержащемуся в `address_reg`.

## Microcode

- Существует память микрокоманд, в которой хранятся микрокоманды двух типов: операционные(control_flow) и управляющие.
- Управляющие микрокоманды содержат сигналы (записать в регистр, прочитать из регистра, сделать ввод-вывод и т.д.).
Операционные микрокоманды содержат:
	- номер бита `command_register`
	- бит, равенство которого единице требует равенства содержимого регистра `Z` единице
	- адрес перехода
- Регистр `mc_ptr` содержит адрес микрокоманды, которую требуется выполнить.

Принцип работы (один такт):
1. Прочитать из памяти микрокоманд нужную микрокоманду по адресу, содержащемуся в `mc_ptr` (в начале симуляции там находится число 0).
2. Проверить тип команды. Если это управляющая микрокоманда, то содержащиееся в ней управляющие сигналы передаются на вентили.
3. Если это операционная микрокоманда, то сигналы не передаются, а при условиях равенства указанного бита `command_register` единице и равенства  `Z` единице или отсутствия бита требования этого равенства, содержащийся в микрокоманде адрес перехода записывается в регистр `mc_ptr`.
4. В ином случае (в том числе, если перед нами управляющая микрокоманда), содержимое `mc_ptr` инкрементируется.

Принцип написания микрокода:
- Первые несколько микрокоманд составляют т.н. instruction fetch (цикл выборки команды). Его результат - инкремент счётчика команд и помещение выполняемой команды в `data_register` и `command_register`.
- Затем в зависимости от типа микрокоманды происходит goto в "блок" микрокоманд определённого типа (микрокоманды для обработки инструкции без аргументов, для обработки jump'ов и для инструкций с 2 аргументами). В конце каждого такого блока goto на нулевую микрокоманду, то есть instruction fetch уже следующей микрокоманды.
- Инструкции с двумя аргументами самые сложные, так как каждый из аргументов может быть адресован по разному. Принцип работы - поместить первый аргумент в один буфер, второй аргумент в другой буфер (эти операции общие для всех инструкций с двумя аргументами), затем выполнить зависящее от типа команды действие.

Как устроены микрокоманды?
- Всего микрокоманд в памяти - 63. Необходимый для их адресации размер `mc_ptr` - 6 бит.
- Размер микрокоманды - 24 бита. Первый бит показывает тип микрокоманды.
- У управляющих микрокоманды последующие 23 бита - это управляющие сигналы. 1 бит на сигнал.
- У операционных после первого бита идёт бит требования `Z = 0`, затем 5 битов - номер проверяемого на равенство единице бита в `command_register`, затем 6 битов - адрес перехода, затем нули.

Реализация на Python:
- Память микрокоманд реализована в виде списка структур (структура это pyton dict).
- Помимо всего, перечисленного ранее, представляющая микрокоманду структура, может содержать т.н. label. Каждый label - это просто имя, дающееся микрокоманде.
- Label'ы существуют исключительно для удобства чтения и восприятия модели, разумеется, в компьютере ничего такого нет.
- Label указывается в атрибуте goto микрокоманды - это инструкция, к которой нужно выполнить переход. Очевидно, что в реальной микрокоманде это не название, а конкретное число - номер микрокоманды.
- Исключительно для удобства чтения и модификации микрокода goto атрибуты содержат названия, а не адреса и существует функция `mc_pointer_by_label`, которая заменяет label на адрес.

Примечание по микрокоду - существует следующий tradeoff: у команд с двумя аргументами по большей части общий алгоритм выполнения выборка команды, выборка адресации. В связи с этим два варианта:
1. Сделать микрокоманды, выполняющие выборку первого и второго аргумента и помещающие их в соответсвующие буферы, общими для всех команд этого типа. Результат - компактнее и проще микрокод, но больше шагов в некоторых случаях, за счёт выполнения ненужных инструкций. Например, `mov` проще `add` тем, что ей на самом деле не нужен первый аргумент, она его просто перепишет. Но раз мы выбрали этот путь, сэкономить на этом не выйдет.
2. Для каждой двухаргументной инструкции иметь в микрокоде выборку первого (может быть) и второго аргумента. Это более оптимизированный и преспособленный к дальнейшим изменениям способ, но он требует больше микрокода.

Был выбран первый вариант в виду его компактности.


``` text
                         signals                                
                             ▲                                  
                             │                                  
                    ┌────────┴───────────┐                      
                    │MUX(0 if not cf)    │                      
                    └────────────────────┘                      
                    ▲           ▲  ▲  ▲                         
                    │           │  │  │                         
                  (neg)         │  │  │                         
                    │           signals                         
                control_flow?   │  │  │                         
                    │ ┌─────────┴──┴──┴──┐                      
        ┌───────┬───┼─┤  micro_command   │                      
        │       │   │ └────────────────┬─┘◄──────────────┐      
        │ check_bit │                  │                 │      
        │       │   └─control_flow?──┐ │                 │      
        │       ▼                    │ └─────┐           │      
        │    ┌─────────┐             │       │           │      
        │    │decoder  │             │    goto_addr     ┌┴─────┐
        │    └──┬──────┘             │       │          │MC_MEM│
        │       │                    │       │  ┌─────┐ │      │
 zero_required? ▼                    ▼       ▼  ▼     │ │      │
        │      (xor)──►(non_zero)─►(and)─►┌───────┐   │ │      │
        │       ▲                    ▲    │ MUX   │ (+1)└──────┘
  read_mcg)     │                    │    └┬──────┘   │    ▲  ▲ 
        │     command_reg            │     │          └──┐ │  │ 
        │                            │     └─►┌──────┐   │ │  │ 
Z─────►(or)──────────────────────────┘        │mc_ptr├───┴─┘  │ 
                            latch_mc_ptr─────►└──────┘        │ 
                                                              │ 
                                 read_mc──────────────────────┘ 
```

Реализован в классе `Micro`

- `latch_mc_ptr` -- сигнал для обновления счётчика микрокоманд в Micro.
- `read_mc` -- сигнал для чтения микрокоманды из памяти микрокоманд.

Особенности работы модели:

- Цикл симуляции осуществляется в функции `simulate_tick_and_return_signals`.
- Остановка моделирования осуществляется при:
    - превышении лимита количества выполняемых инструкций;
    - исключении `EOFError` -- если нет данных для чтения из порта ввода;
    - исключении `StopIteration` -- если выполнена инструкция `halt`.

### ControlUnit

``` text
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
```

Реализован в классе `ControlUnit`.

- Microcode (реализовано в [micro](./python/micro.py)).
- Метод `simulate_tick` моделирует выполнение одного такта процессора.

Сигнал:

- `latch_mc_ptr` -- сигнал для обновления счётчика микрокоманд в Micro.
- `read_mc` -- сигнал для чтения микрокоманды из памяти микрокоманд.

Особенности работы модели:

- Цикл симуляции осуществляется в функции `simulation`.
- Шаг моделирования соответствует одной инструкции с выводом состояния в журнал.
- Для журнала состояний процессора используется стандартный модуль `logging`.
- Количество инструкций для моделирования лимитировано.
- Остановка моделирования осуществляется при:
    - превышении лимита количества выполняемых инструкций;
    - исключении `EOFError` -- если нет данных для чтения из порта ввода;
    - исключении `StopIteration` -- если выполнена инструкция `hlt`.
    
### Описание и аргументация странных решений

`Реализация чтения и записи регистров общего назначения`
Стандартным решением для чтения и записи регистров были бы ветвления микрокода по флагам команды, отвечающим за чтение/запись соответствующих регистров.
В моём случае используется следующая особенность -- во всяком случае, когда происходит чтение из регистров или запись в регистры, в регистре `command_register` всегда содержится адрес регистра, из которого читаем или в который пишем.
Поэтому адрес регистра, выступающего в роли `destination` в командах с двумя аргументами, вместе с сигналом `dst_read`, указывающим на необходимость чтения регистра `destination` на левый вход АЛУ, поступает на мультиплексор, осуществляющий в зависимости от входных данных выбор нужного регистра.
Аналогичная ситуация происходит с регистром, выступающим в роли  `argument` и сигналом `arg_read`.
Такой подход предполагает более сложную схему, но позволяет использовать меньше тактов для выполнения команды с двумя аргументами.
Также стоит обратить внимание на то, как реализована запись в регистр `d`. Эта процедура не характерна для других регистров общего назначения, так как только этот регистр используется для io операций.
Записано значение в него будет в случае, если подан сигналы `in` или указано записать в регистр и указанным регистром в `command_register` является `d`.
Записано в него будет либо значение, посчитанное в АЛУ, либо ввод пользователя (`input`), в зависимости от наличия сигнала `in`.

## Тестирование

Тестирование выполняется при помощи golden test-ов.

1. Тесты для языка `asm` реализованы в: [golden_asm_test.py](./python/golden_asm_test.py). Конфигурации:
    - [python/golden/cat_asm.yml](python/golden/cat_asm.yml)

Запустить тесты: `poetry run pytest . -v`

Обновить конфигурацию golden tests:  `poetry run pytest . -v --update-goldens`

CI при помощи Github Action:

``` yaml
defaults:
  run:
    working-directory: ./python

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.11

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install poetry
          poetry install

      - name: Run tests and collect coverage
        run: |
          poetry run coverage run -m pytest .
          poetry run coverage report -m
        env:
          CI: true

  lint:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.11

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install poetry
          poetry install

      - name: Check code formatting with Ruff
        run: poetry run ruff format --check .

      - name: Run Ruff linters
        run: poetry run ruff check .
```

где:

- `poetry` -- управления зависимостями для языка программирования Python.
- `coverage` -- формирование отчёта об уровне покрытия исходного кода.
- `pytest` -- утилита для запуска тестов.
- `ruff` -- утилита для форматирования и проверки стиля кодирования.

Пример использования и журнал работы процессора на примере `cat`:

``` shell
$ cat examples/foo_input.txt
foo
$ cat examples/cat.asm
,[.,]
$ ./translator.py examples/cat.asm target.out
source LoC: 1 code instr: 6
$ cat target.out
[{"word_number": 0, "opcode": "jmp", "flags": ["branch", "jmp"], "address": 1},
   {"word_number": 1, "type": "noArg", "opcode": "in", "flags": ["noArg", "io", "in"]},
   {"word_number": 2, "type": "twoArg", "opcode": "cmp", "flags": ["twoArg", "dest_is_register", "add_or_cmp", "cmp"], "dest_reg": "d"},
   {"value": 0},
   {"word_number": 4, "type": "branch", "opcode": "jz", "flags": ["branch"], "address": 7},
   {"word_number": 5, "type": "noArg", "opcode": "out", "flags": ["noArg", "io"]},
   {"word_number": 6, "type": "branch", "opcode": "jmp", "flags": ["branch", "jmp"], "address": 1},
   {"word_number": 7, "type": "noArg", "opcode": "hlt", "flags": ["noArg"]},
   {"word_number": 8, "type": "noArg", "opcode": "hlt", "flags": ["noArg"]}]
$ ./machine.py target.out examples/foo_input.txt
INFO    machine:simulation    TICK: 1 IP: 0 DR: 0 CR: 0 ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 0
  INFO    machine:simulation    TICK: 2 IP: 1 DR: {'word_number': 0, 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: 0 ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 0
  INFO    machine:simulation    TICK: 3 IP: 1 DR: {'word_number': 0, 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 0, 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 0
  INFO    machine:simulation    TICK: 4 IP: 1 DR: {'word_number': 0, 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 0, 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 0
  INFO    machine:simulation    TICK: 5 IP: 1 DR: {'word_number': 0, 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 0, 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 0
  INFO    machine:simulation    TICK: 6 IP: 1 DR: {'word_number': 0, 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 0, 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 0
  INFO    machine:simulation    TICK: 7 IP: 1 DR: {'word_number': 0, 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 0, 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 0
  INFO    machine:simulation    TICK: 8 IP: 1 DR: {'word_number': 0, 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 0, 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 0
  INFO    machine:simulation    TICK: 9 IP: 1 DR: {'word_number': 0, 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 0, 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 1
  INFO    machine:simulation    TICK: 10 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 0, 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 1
  INFO    machine:simulation    TICK: 11 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 1
  INFO    machine:simulation    TICK: 12 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 1
  INFO    machine:simulation    TICK: 13 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 1
  INFO    machine:simulation    TICK: 14 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 1
  INFO    machine:simulation    TICK: 15 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 1
  DEBUG   machine:do_io         input: 'f'
  INFO    machine:simulation    TICK: 16 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 0 AR: 1
  INFO    machine:simulation    TICK: 17 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 0 AR: 1
  INFO    machine:simulation    TICK: 18 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 0 AR: 2
  INFO    machine:simulation    TICK: 19 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 0 AR: 2
  INFO    machine:simulation    TICK: 20 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 0 AR: 2
  INFO    machine:simulation    TICK: 21 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 0 AR: 2
  INFO    machine:simulation    TICK: 22 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 0 AR: 2
  INFO    machine:simulation    TICK: 23 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 2
  INFO    machine:simulation    TICK: 24 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 2
  INFO    machine:simulation    TICK: 25 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 2
  INFO    machine:simulation    TICK: 26 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 2
  INFO    machine:simulation    TICK: 27 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 3
  INFO    machine:simulation    TICK: 28 IP: 4 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 3
  INFO    machine:simulation    TICK: 29 IP: 4 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 3
  INFO    machine:simulation    TICK: 30 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 3
  INFO    machine:simulation    TICK: 31 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 3
  INFO    machine:simulation    TICK: 32 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 3
  INFO    machine:simulation    TICK: 33 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 3
  INFO    machine:simulation    TICK: 34 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 3
  INFO    machine:simulation    TICK: 35 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 3
  INFO    machine:simulation    TICK: 36 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 3
  INFO    machine:simulation    TICK: 37 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 3
  INFO    machine:simulation    TICK: 38 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 4
  INFO    machine:simulation    TICK: 39 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 4
  INFO    machine:simulation    TICK: 40 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 4
  INFO    machine:simulation    TICK: 41 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 4
  INFO    machine:simulation    TICK: 42 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 4
  INFO    machine:simulation    TICK: 43 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 4
  INFO    machine:simulation    TICK: 44 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 4
  INFO    machine:simulation    TICK: 45 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 4
  INFO    machine:simulation    TICK: 46 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 5
  INFO    machine:simulation    TICK: 47 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 5
  INFO    machine:simulation    TICK: 48 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 5
  INFO    machine:simulation    TICK: 49 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 5
  INFO    machine:simulation    TICK: 50 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 5
  INFO    machine:simulation    TICK: 51 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 5
  INFO    machine:simulation    TICK: 52 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 5
  DEBUG   machine:do_io         output: '' << 'f'
  INFO    machine:simulation    TICK: 53 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 5
  INFO    machine:simulation    TICK: 54 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 5
  INFO    machine:simulation    TICK: 55 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 6
  INFO    machine:simulation    TICK: 56 IP: 7 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 6
  INFO    machine:simulation    TICK: 57 IP: 7 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 6
  INFO    machine:simulation    TICK: 58 IP: 7 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 6
  INFO    machine:simulation    TICK: 59 IP: 7 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 6
  INFO    machine:simulation    TICK: 60 IP: 7 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 6
  INFO    machine:simulation    TICK: 61 IP: 1 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 6
  INFO    machine:simulation    TICK: 62 IP: 1 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 6
  INFO    machine:simulation    TICK: 63 IP: 1 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 1
  INFO    machine:simulation    TICK: 64 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 1
  INFO    machine:simulation    TICK: 65 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 1
  INFO    machine:simulation    TICK: 66 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 1
  INFO    machine:simulation    TICK: 67 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 1
  INFO    machine:simulation    TICK: 68 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 1
  INFO    machine:simulation    TICK: 69 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 102 DST_BUF: 102 AR: 1
  DEBUG   machine:do_io         input: 'o'
  INFO    machine:simulation    TICK: 70 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 102 AR: 1
  INFO    machine:simulation    TICK: 71 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 102 AR: 1
  INFO    machine:simulation    TICK: 72 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 102 AR: 2
  INFO    machine:simulation    TICK: 73 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 102 AR: 2
  INFO    machine:simulation    TICK: 74 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 102 AR: 2
  INFO    machine:simulation    TICK: 75 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 102 AR: 2
  INFO    machine:simulation    TICK: 76 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 102 AR: 2
  INFO    machine:simulation    TICK: 77 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 78 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 79 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 80 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 81 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 82 IP: 4 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 83 IP: 4 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 84 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 85 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 86 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 87 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 88 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 89 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 90 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 91 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 92 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 4
  INFO    machine:simulation    TICK: 93 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 4
  INFO    machine:simulation    TICK: 94 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 4
  INFO    machine:simulation    TICK: 95 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 4
  INFO    machine:simulation    TICK: 96 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 4
  INFO    machine:simulation    TICK: 97 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 4
  INFO    machine:simulation    TICK: 98 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 4
  INFO    machine:simulation    TICK: 99 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 4
  INFO    machine:simulation    TICK: 100 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  INFO    machine:simulation    TICK: 101 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  INFO    machine:simulation    TICK: 102 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  INFO    machine:simulation    TICK: 103 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  INFO    machine:simulation    TICK: 104 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  INFO    machine:simulation    TICK: 105 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  INFO    machine:simulation    TICK: 106 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  DEBUG   machine:do_io         output: 'f' << 'o'
  INFO    machine:simulation    TICK: 107 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  INFO    machine:simulation    TICK: 108 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  INFO    machine:simulation    TICK: 109 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 6
  INFO    machine:simulation    TICK: 110 IP: 7 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 6
  INFO    machine:simulation    TICK: 111 IP: 7 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 6
  INFO    machine:simulation    TICK: 112 IP: 7 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 6
  INFO    machine:simulation    TICK: 113 IP: 7 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 6
  INFO    machine:simulation    TICK: 114 IP: 7 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 6
  INFO    machine:simulation    TICK: 115 IP: 1 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 6
  INFO    machine:simulation    TICK: 116 IP: 1 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 6
  INFO    machine:simulation    TICK: 117 IP: 1 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 1
  INFO    machine:simulation    TICK: 118 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 1
  INFO    machine:simulation    TICK: 119 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 1
  INFO    machine:simulation    TICK: 120 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 1
  INFO    machine:simulation    TICK: 121 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 1
  INFO    machine:simulation    TICK: 122 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 1
  INFO    machine:simulation    TICK: 123 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 1
  DEBUG   machine:do_io         input: 'o'
  INFO    machine:simulation    TICK: 124 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 1
  INFO    machine:simulation    TICK: 125 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 1
  INFO    machine:simulation    TICK: 126 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 127 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 128 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 129 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 130 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 131 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 132 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 133 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 134 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 135 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 136 IP: 4 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 137 IP: 4 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 138 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 139 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 140 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 141 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 142 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 143 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 144 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 145 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 3
  INFO    machine:simulation    TICK: 146 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 4
  INFO    machine:simulation    TICK: 147 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 4
  INFO    machine:simulation    TICK: 148 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 4
  INFO    machine:simulation    TICK: 149 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 4
  INFO    machine:simulation    TICK: 150 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 4
  INFO    machine:simulation    TICK: 151 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 4
  INFO    machine:simulation    TICK: 152 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 4
  INFO    machine:simulation    TICK: 153 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 4
  INFO    machine:simulation    TICK: 154 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  INFO    machine:simulation    TICK: 155 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  INFO    machine:simulation    TICK: 156 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  INFO    machine:simulation    TICK: 157 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  INFO    machine:simulation    TICK: 158 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  INFO    machine:simulation    TICK: 159 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  INFO    machine:simulation    TICK: 160 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  DEBUG   machine:do_io         output: 'fo' << 'o'
  INFO    machine:simulation    TICK: 161 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  INFO    machine:simulation    TICK: 162 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 5
  INFO    machine:simulation    TICK: 163 IP: 6 DR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 6
  INFO    machine:simulation    TICK: 164 IP: 7 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 5, 'type': 'noArg', 'opcode': 'out', 'flags': ['noArg', 'io']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 6
  INFO    machine:simulation    TICK: 165 IP: 7 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 6
  INFO    machine:simulation    TICK: 166 IP: 7 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 6
  INFO    machine:simulation    TICK: 167 IP: 7 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 6
  INFO    machine:simulation    TICK: 168 IP: 7 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 6
  INFO    machine:simulation    TICK: 169 IP: 1 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 6
  INFO    machine:simulation    TICK: 170 IP: 1 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 6
  INFO    machine:simulation    TICK: 171 IP: 1 DR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 1
  INFO    machine:simulation    TICK: 172 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 6, 'type': 'branch', 'opcode': 'jmp', 'flags': ['branch', 'jmp'], 'address': 1} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 1
  INFO    machine:simulation    TICK: 173 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 1
  INFO    machine:simulation    TICK: 174 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 1
  INFO    machine:simulation    TICK: 175 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 1
  INFO    machine:simulation    TICK: 176 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 1
  INFO    machine:simulation    TICK: 177 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 111 DST_BUF: 111 AR: 1
  DEBUG   machine:do_io         input: '\x00'
  INFO    machine:simulation    TICK: 178 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 111 AR: 1
  INFO    machine:simulation    TICK: 179 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 111 AR: 1
  INFO    machine:simulation    TICK: 180 IP: 2 DR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 181 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 1, 'type': 'noArg', 'opcode': 'in', 'flags': ['noArg', 'io', 'in']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 182 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 183 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 184 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 111 AR: 2
  INFO    machine:simulation    TICK: 185 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 2
  INFO    machine:simulation    TICK: 186 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 2
  INFO    machine:simulation    TICK: 187 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 2
  INFO    machine:simulation    TICK: 188 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 2
  INFO    machine:simulation    TICK: 189 IP: 3 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 3
  INFO    machine:simulation    TICK: 190 IP: 4 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 3
  INFO    machine:simulation    TICK: 191 IP: 4 DR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 3
  INFO    machine:simulation    TICK: 192 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 3
  INFO    machine:simulation    TICK: 193 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 3
  INFO    machine:simulation    TICK: 194 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 3
  INFO    machine:simulation    TICK: 195 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 3
  INFO    machine:simulation    TICK: 196 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 3
  INFO    machine:simulation    TICK: 197 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 3
  INFO    machine:simulation    TICK: 198 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 3
  INFO    machine:simulation    TICK: 199 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 3
  INFO    machine:simulation    TICK: 200 IP: 4 DR: {'value': 0} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 4
  INFO    machine:simulation    TICK: 201 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 2, 'type': 'twoArg', 'opcode': 'cmp', 'flags': ['twoArg', 'dest_is_register', 'add_or_cmp', 'cmp'], 'dest_reg': 'd'} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 4
  INFO    machine:simulation    TICK: 202 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 4
  INFO    machine:simulation    TICK: 203 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 4
  INFO    machine:simulation    TICK: 204 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 4
  INFO    machine:simulation    TICK: 205 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 4
  INFO    machine:simulation    TICK: 206 IP: 5 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 4
  INFO    machine:simulation    TICK: 207 IP: 7 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 4
  INFO    machine:simulation    TICK: 208 IP: 7 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 4
  INFO    machine:simulation    TICK: 209 IP: 7 DR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 7
  INFO    machine:simulation    TICK: 210 IP: 8 DR: {'word_number': 7, 'type': 'noArg', 'opcode': 'hlt', 'flags': ['noArg']} CR: {'word_number': 4, 'type': 'branch', 'opcode': 'jz', 'flags': ['branch'], 'address': 7} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 7
  INFO    machine:simulation    TICK: 211 IP: 8 DR: {'word_number': 7, 'type': 'noArg', 'opcode': 'hlt', 'flags': ['noArg']} CR: {'word_number': 7, 'type': 'noArg', 'opcode': 'hlt', 'flags': ['noArg']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 7
  INFO    machine:simulation    TICK: 212 IP: 8 DR: {'word_number': 7, 'type': 'noArg', 'opcode': 'hlt', 'flags': ['noArg']} CR: {'word_number': 7, 'type': 'noArg', 'opcode': 'hlt', 'flags': ['noArg']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 7
  INFO    machine:simulation    TICK: 213 IP: 8 DR: {'word_number': 7, 'type': 'noArg', 'opcode': 'hlt', 'flags': ['noArg']} CR: {'word_number': 7, 'type': 'noArg', 'opcode': 'hlt', 'flags': ['noArg']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 7
  INFO    machine:simulation    TICK: 214 IP: 8 DR: {'word_number': 7, 'type': 'noArg', 'opcode': 'hlt', 'flags': ['noArg']} CR: {'word_number': 7, 'type': 'noArg', 'opcode': 'hlt', 'flags': ['noArg']} ARG_BUF: 0 a: 0 b: 0 c: 0 d: 0 DST_BUF: 0 AR: 7
  INFO    machine:simulation    output_buffer: 'foo'
```

Пример проверки исходного кода:

``` shell
(venv) [aleksei@bplate7009 python]$ poetry run pytest . -v
================================================================================================================================================= test session starts ==================================================================================================================================================
platform linux -- Python 3.11.6, pytest-7.4.4, pluggy-1.4.0 -- /home/aleksei/study/csa/toy-cpu-emulation/venv/bin/python
cachedir: .pytest_cache
rootdir: /home/aleksei/study/csa/toy-cpu-emulation/python
configfile: pyproject.toml
plugins: golden-0.2.2
collected 4 items                                                                                                                                                                                                                                                                                                      

golden_asm_test.py::test_translator_asm_and_machine[golden/euler_asm.yml] PASSED                                                                                                                                                                                                                                 [ 25%]
golden_asm_test.py::test_translator_asm_and_machine[golden/cat_asm.yml] PASSED                                                                                                                                                                                                                                   [ 50%]
golden_asm_test.py::test_translator_asm_and_machine[golden/hello_user_asm.yml] PASSED                                                                                                                                                                                                                            [ 75%]
golden_asm_test.py::test_translator_asm_and_machine[golden/hello_world_asm.yml] PASSED                                                                                                                                                                                                                           [100%]

================================================================================================================================================== 4 passed in 33.42s ==================================================================================================================================================
(venv) [aleksei@bplate7009 python]$ 

```

```text
| ФИО                          | алг             | LoC | code байт | code инстр. | инстр. | такт. | вариант                                                               |
| Дорморезов Алексей Сергеевич | hello           | 11  | -         | 12          | 83     | 1252  | asm | cisc | neum | mc | tick | struct | stream | port | pstr | prob1 |
| Дорморезов Алексей Сергеевич | cat             | 6   | -         | 8           | 20     | 214   | asm | cisc | neum | mc | tick | struct | stream | port | pstr | prob1 |
| Дорморезов Алексей Сергеевич | hello_user_name | 40  | -         | 33          | 236    | 3596  | asm | cisc | neum | mc | tick | struct | stream | port | pstr | prob1 |
```
