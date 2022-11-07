# Commands

This is a list of commands that I've encountered and understood. All commands start with a target address and a Function code. The commands also contain start addresses and length information, and always end with a MODBUS CRC Checksum.
Most commands are 16-bit oriented and use 16-bit addresses and values.

## combined read and write

This is the most common command used. It requests a read operation after writing its own data. This is useful for reading back results after poking the controller with a write.

`TA 17 RAH RAL RL WAH WAL WL NN D1H D1L D2H D2L ... DnH DnL CSH CSL`

Byte | Code | Function
--- | --- | ---
00 | TA | Target address. 01= ESC, AF=ePowerFun display
01 | 17 | Function code combined read and write
02 | RAH | Read address start High-byte
03 | RAL | Read address start Low-byte
04 | RL | Read length (this many 16-bit registers)
05 | WAH | Write address start High-byte
06 | WAL | Write address start Low-byte
07 | WL | Write length (this many 16-bit registers)
08 | NN | number of databytes (2*WL)
09 | D1H | Data 1 High-Byte
10 | D1L | Data 1 Low-Byte
N-3 | DnH | Data n High-Byte
N-2 | DnL | Data n Low-Byte
N-1 | CSH | Checksum High-Byte
N | CSL | Checksum Low-Byte
   





