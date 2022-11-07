# Commands

This is a list of commands that I've encountered and understood. 
All commands start with a target address and a Function code. 
The commands also contain start addresses and length information, and always end with a MODBUS CRC Checksum.
The responses repeat the target address and function code, just like MODBUS does.
All commands are 16-bit oriented and use 16-bit addresses and values.

## Combined read and write

This is the most common command used. It requests a read operation after writing its own data. This is useful for reading back results after poking the controller with a write.

### Request

`TA 17 RAH RAL RL WAH WAL WL NN D1H D1L ... DnH DnL CSH CSL`

Byte | Code | Function
--- | --- | ---
00 | TA | Target address. 0x01= ESC, 0xAF=ePowerFun display
01 | 0x17 | Function code: combined read and write
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

### Response

`TA 17 RAH RAL NN D1H D1L ... DnH DnL CSH CSL`

Byte | Code | Function
--- | --- | ---
00 | TA | Target address. 0x01= ESC, 0xAF=ePowerFun display
01 | 0x17 | Function code: combined read and write
02 | RAH | Read address start High-byte
03 | RAL | Read address start Low-byte
04 | NN | number of databytes (2*number of registers)
05 | D1H | Data 1 High-Byte
06 | D1L | Data 1 Low-Byte
N-3 | DnH | Data n High-Byte
N-2 | DnL | Data n Low-Byte
N-1 | CSH | Checksum High-Byte
N | CSL | Checksum Low-Byte


### Example

The display regularly sends this request:
`01 17 00 26 00 0c 00 2b 00 01 02 00 00 72 59`

Explanation:
Byte(s) | Code | Function
--- | --- | ---
00 | 01 | Target address 01
01 | 17 | Function Code 17: Combined read and write
02-03 | 00 26 | start address for reading (0x0026)
04-05 | 00 0c | number of registers to read (12)
06-07 | 00 2b | start address for writing (0x002b, this is the throttle/brake register)
08-09 | 00 01 | number of registers to write (1)
10 | 02 | number of databytes (2)
11-12 | 00 00 | data (throttle/brake position)
13-14 | 72 59 | Checksum

## Read registers

Reads multiple registers from memory

### Request 

`TA 03 RAH RAL RLH RLL CSH CSL`

Byte | Code | Function
--- | --- | ---
00 | TA | Target address. 0x01= ESC, 0xAF=ePowerFun display
01 | 0x03 | Function code: read registers
02 | RAH | Read address start High-byte
03 | RAL | Read address start Low-byte
04 | RLH | Read length High-Byte
05 | RLL | Read length Low-Byte
06 | CSH | Checksum High-Byte
07 | CSL | Checksum Low-Byte

### Response

`TA 03 RAH RAL NN D1H D1L ... DnH DnL CSH CSL`

Byte | Code | Function
--- | --- | ---
00 | TA | Target address. 0x01= ESC, 0xAF=ePowerFun display
01 | 0x03 | Function code: read registers
02 | RAH | Read address start High-byte
03 | RAL | Read address start Low-byte
04 | NN | number of databytes (2*number of registers)
05 | D1H | Data 1 High-Byte
06 | D1L | Data 1 Low-Byte
N-3 | DnH | Data n High-Byte
N-2 | DnL | Data n Low-Byte
N-1 | CSH | Checksum High-Byte
N | CSL | Checksum Low-Byte


## Set bit

Sets bits at the requested address, not fully confirmed

### Request

To Do

`TA 10 WAH WAL WLH WLL NN D1H D1L ... DnH DnL CSH CSL`

Byte | Code | Function
--- | --- | ---
00 | TA | Target address. 0x01= ESC, 0xAF=ePowerFun display
01 | 0x10 | Function code: Set bits
02 | WAH | Write address start High-byte
03 | WAL | Write address start Low-byte
04 | WLH | Write length High Byte (this many 16-bit registers)
05 | WLL | Write length Low Byte (this many 16-bit registers)
06 | NN | number of databytes (2*WL)
07 | D1H | Data 1 High-Byte
08 | D1L | Data 1 Low-Byte
N-3 | DnH | Data n High-Byte
N-2 | DnL | Data n Low-Byte
N-1 | CSH | Checksum High-Byte
N | CSL | Checksum Low-Byte

### Response

To Do. Not fully understood yet.

Response: `01 10 00 00 00 01 01 c9`