# Decoding the memory map

Reading the memory map with MODBUS style telemetry commands in UF mode, either with a Logic Analyzer or with the GUI python script

## Reading the memory map with trial and error

Address | Confirmed function
--- | ---
00 | control bits, low byte corresponds to gear and lamp status
09 | Acceleration response (16-bit val)
0a | Brake response (16-bit val)
20 | maximum speed (km/h*0.1)
25 | 
26 | battery voltage (V*0.1)
27 | battery amperage (A*0.01)
28 | temperature (read only high-byte, °C)
29 | various control bits, unknown except for gear select and lamp status
2F..30 | total kilometers (read-only, km*0.001)

## writing something to memory

Recreating my old total kilometer record of approx. 1000 km before a firmware upgrade destroyed it, resetting it to zero:

target value=1000.000 km=0x000f4240

writing location 0x002f=0x4240: `01 17 00 2f 00 01 00 2f 00 01 02 42 40 53 3b`

writing location 0x0030=0x000f: `01 17 00 30 00 01 00 30 00 01 02 00 0f 11 a5`

...was unsuccessful. It looks like the memory for the total km's is write protected, which is good, but won't help me restore my original 1000 km record.

changing an interesting looking parameter at address 0x02

`01 17 00 02 00 01 00 02 00 01 02 55 55 0b e9` original 5555

`01 17 00 02 00 01 00 02 00 01 02 22 22 6c 3f` test 2222

...also didn't work.

##reading beyond 0x9f

It is indeed possible to read MUCH beyond 0x9f. I've upgraded the GUI tool to read quite far into the memory.

Starting at 0x0116 are located the four text strings that appear in the firmware upgrade screen. They are stored in reverse byte order, with a length of 16 bytes (8 addresses) each. I found out because 0x20 corresponds to an ASCII space character, and there seemed to be quite a lot of them at once. They are indeed used as padding for the text strings.

around the 0x01a0 mark there seems to be a repetitve data structure that repeats three times, suspiciously correlating to the three gears that can be selected. I haven't found any meaning in this data yet.

Firmware seems to start around 0x04bf.