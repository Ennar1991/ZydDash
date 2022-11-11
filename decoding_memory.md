# Decoding the memory map

Reading the memory map with MODBUS style telemetry commands in UF mode, either with a Logic Analyzer or with the GUI python script

## Reading the memory map with trial and error

Address | Confirmed function | Default Value
--- | --- | ---
00 | control bits, low byte corresponds to gear and lamp status
09 | Acceleration response (16-bit val)
0a | Brake response (16-bit val)
15 | immobilizes the scooter when not set to 1 (no reaction to accel, always braking a bit) | 0001
16 | Influences the vector control, introduces jitter and increases power usage when lower than default | 6aaa
18 | unknown, writable | c03d
19 | unknown, writable | 0027
1a | unknown, writable | 6335
1b | unknown, writable | 0006
1c | unknown, writable | 03fd
1d | unknown, writable | 0000
1e | unknown, writable | 0000
1f | unknown, writable | 0000
20 | maximum speed (km/h*0.1), writable, limited between 06 and dc | dc
24 | ffff when moving wheel forward by hand | 0000
25 | signed, related to speed or amperage | 0000
26 | battery voltage (V*0.1)
27 | battery amperage (A*0.01)
28 | temperature (read only high-byte, °C)
29 | various control bits, unknown except for gear select and lamp status
2b | throttle control value, writing a positive value actually works shortly | 0000
2c | Actual speed
2F..30 | total kilometers (read-only, km*0.001)
3f | unknown, writable | aaaa
40 | unknown, writable. A group of three similarr parameters - related to three gears? | 07b8
41 | unknown, writable | 07c5
42 | unknown, writable | 07c2
49 | unknown, writable | 0861






### control bits in 0x0000

Bit | Confirmed function
--- | ---
16 | turns the controller or display off (some kind of command to the display)


## Writing something to memory

Most parameters are write-protected or limited in their range. The total kilometers cannot be modified for example. This would have been useful to restore my over 1000 km record after a firmware update wiped the total kilometers back to zero.

## Reading beyond 0x9f

It is indeed possible to read MUCH beyond 0x9f, what the app requests normally. I've upgraded the GUI tool to read quite far into the memory. Reading beyond address 1a28 crashes the controller.

Starting at 0x0116 are located the five text strings that appear in the firmware upgrade screen. They are stored in reverse byte order, with a length of 16 bytes (8 addresses) each. I found out because 0x20 corresponds to an ASCII space character, and there seemed to be quite a lot of them at once. They are indeed used as padding for the text strings.

Address | Confirmed function
--- | ---
0116...011d | Scooter model name string, two ASCII characters per register, byte swapped
011e...0125 | Hardware version string, two ASCII characters per register, byte swapped
0126...012d | Bootloader version string, two ASCII characters per register, byte swapped
012e...0135 | Firmware version string, two ASCII characters per register, byte swapped
0136...013d | Controller code string, two ASCII characters per register, byte swapped

around the 0x01a0 mark there seems to be a data structure that repeats three times, suspiciously correlating to the three gears that can be selected. I haven't found any meaning in this data yet.

Firmware seems to start around 0x04bf. I will have to log a complete firmware upgrade with Android's logging capabilities to see what's going on.