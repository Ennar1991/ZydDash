# Display Telemetry Analyzing
This document is my notebook for analyzing the display bus protocol. The finished analysis will be polished and compacted and released in another file.

The scooter's display, marked HW6173_LCD1_V1.4 has an on-board BLE module (chip label unfortunately not readable), supported by an 8051 based "CMS8S5880" microcotroller. I haven't bothered yet to reverse engineer the entire pcb as it isn't needed for my purpose.

## Hardware connection
The pinout of it's 4-pin connector to the motor driver is as follows:
Pin | Label | Function
--- | --- | ---
1 | TX | Combined RX/TX
2 | - | GND, likely switched
3 | + | VCC (roughly 12 V when ON)
4 | Key | Shorted to + when button is pressed

## Serial interface

The "TX" pin is interesting as it is used for bidirectional communication, continuing the MODBUS approach. It is using 3.3 V logic levels. The display is powered by roughly 12 V supplied by the motor controller, whenever the "Key" signal is activated or when the display keeps on actively communicating. This needs further research down the line and I expect the same kind of protocols used as in the BLE telemetry (only other more low-level stuff like accelerator position and light outputs on/off).

Hooking up a Logic Analyzer to the TX and - pins i got the Serial Interface parameters fairly quickly:

115200 baud/s, 8N1. This is excellent for signal analysis and command injection, should that be even necessary.

The protocol looks at first glance somewhat like the protocol used for the BLE telemetry, starting with an address and function code byte. There are two distinctly different messages sent by the display and the controller, both differing in length. I'm assuning that the short message is sent by the display and the long message is sent by the controller. I haven't yet disconnected the display to find out.

Example: 

Request (Display): `01 17 00 26 00 0c 00 2b 00 01 02 00 00 72 59`

Response (Controller): `01 17 00 26 18 01 a2 00 00 00 00 0d 02 00 00 00 00 00 5a 00 fb 11 b7 69 d6 00 01 00 00 8e ce`

The frame interval between each request/response pair is approcximately 20 ms, contributing to the excellent control feeling of the accelerator/brake (they respond without any noticeable delay when driving).

### Start-up/Power on

During experimenting I recorded the startup sequence when you hold down the button to turn the scooter off and on. Upon holding the button to turn the scooter on, the following sequence happens on the bus:

Request `01 17 00 26 00 0c 00 2b 00 01 02 00 00 72 59` is sent.

Response `01 17 00 26 18 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ca 9f` is sent ONCE (24 times 0x00)

Note: This seems to be similar to the otherr protocol heads, although with a slightly different structure:

Byte | Guess of function
--- | ---
01 | Address
17 | Function Code/Subadress (MODBUS "Report Slave ID")
00 26 | Starting address
18 | Number of data bytes (excluding head and checksum)
(24 times 00) | data
ca 9f | checksum, MODBUS-CRC16 Big Endian

Request `01 17 00 26 00 0c 00 2b 00 01 02 00 00 72 59` is sent and repeated 65 times over ~1.5 seconds until the controller turns on

Magic `30 32 30 32 31 38 30 32` this magic sequence is sent EXACTLY ONCE (origin yet unknown), after which the controller and display actively communicate
It corrensponds to "02021802" in ASCII, the meaning of which is still unclear

### Powered up state, resting

After power-up, the following sequences can be observed (accelerator, electronic brake and handbrake in resting state, scooter at resting state).

The Request `01 17 00 26 00 0c 00 2b 00 01 02 00 00 72 59` (Labeling as RQ1, this always stays the same and is always sent before a response arrives)

RQ1/Response `01 17 00 26 18 01 a2 00 00 00 00 0d 02 00 00 00 00 00 e3 00 db 11 b7 69 d6 00 01 00 00 6f 51`

RQ1/Response `01 17 00 26 18 01 a2 00 00 00 00 0d 02 00 00 00 00 01 3d 01 26 11 b7 69 d6 00 01 00 00 03 e8`

RQ1/Response `01 17 00 26 18 01 a2 00 00 00 00 0d 02 00 00 00 00 00 e3 01 2e 11 b7 69 d6 00 01 00 00 05 c0`

RQ1/Response `01 17 00 26 18 01 a2 00 00 00 00 0d 02 00 00 00 00 00 88 01 16 11 b7 69 d6 00 01 00 00 ed 24`

RQ1/Response `01 17 00 26 18 01 a2 00 00 00 00 0d 02 00 00 00 00 00 5a 00 fb 11 b7 69 d6 00 01 00 00 8e ce`

RQ1/Response `01 17 00 26 18 01 a2 00 00 00 00 0d 02 00 00 00 00 00 5a 00 fb 11 b7 69 d6 00 01 00 00 8e ce`



After that, a differend kind of request was slipped inbetween the other request/response pairs:

Request  `01 03 00 22 00 02 04 01 28` which looks *suspiciously* like the "UF" mode protocol

Response `01 03 00 22 04 03 05 0f 16 24 4c`



After that, the "usual" request/response pairs reappeared:

RQ1/Response `01 17 00 26 18 01 a2 00 00 00 00 0c 02 00 00 00 00 00 2d 00 cc 11 b7 69 d6 00 01 00 00 1d b6`

RQ1/Response `01 17 00 26 18 01 a2 00 00 00 00 0c 02 00 00 00 00 00 00 00 b9 11 b7 69 d6 00 01 00 00 d7 48`

RQ1/Response `01 17 00 26 18 01 a2 00 00 00 00 0c 02 00 00 00 00 00 00 00 a8 11 b7 69 d6 00 01 00 00 17 18`

RQ1/Response `01 17 00 26 18 01 a2 00 00 00 00 0c 02 00 00 00 00 00 00 00 9a 11 b7 69 d6 00 01 00 00 5a 79`

RQ1/Response `01 17 00 26 18 01 a2 00 00 00 00 0c 02 00 00 00 00 00 00 00 8d 11 b7 69 d6 00 01 00 00 b1 89`

RQ1/Response `01 17 00 26 18 01 a2 00 00 00 00 0c 02 00 00 00 00 00 00 00 82 11 b7 69 d6 00 01 00 00 f0 79`

RQ1/Response `01 17 00 26 18 01 a2 00 00 00 00 0c 02 00 00 00 00 00 00 00 79 11 b7 69 d6 00 01 00 00 87 4d`

RQ1/Response `01 17 00 26 18 01 a2 00 00 00 00 0c 02 00 00 00 00 00 00 00 70 11 b7 69 d6 00 01 00 00 ed 1d`

RQ1/Response `01 17 00 26 18 01 a2 00 00 00 00 0c 02 00 00 00 00 00 00 00 69 11 b7 69 d6 00 01 00 00 4a 8d`

RQ1/Response `01 17 00 26 18 01 a2 00 00 16 00 0c 02 00 00 00 00 00 00 00 63 11 b7 69 d6 00 01 00 00 7e d8`

RQ1/Response `01 17 00 26 18 01 a2 00 00 16 00 0c 02 00 00 00 00 00 00 00 5c 11 b7 69 d6 00 01 00 00 6b 29`

...

so far the only fields changing are databyte 4, likely represending a control bit and the 14...15th databytes that seem to be a falling or settling value.

Databyte 4 does not correspond to simple button presses.

### Playing around with live view

Using the trigger function of the Saleae Logic software, i fiddled around with the scooter's controls until finding out which databytes are responsible for each function:

#### Request 

`01 17 00 26 00 0c 00 2b 00 01 02 00 00 72 59`

Byte | Databyte | Value | Confirmed Function
--- | --- | --- | ---
00 |    | 01 | Address
01 |    | 17 | Function Code (No MODBUS, maybe "store in register"?)
02 |    | 00 | starting register high-byte
03 |    | 26 | starting register low-byte
04 |    | 00 | number of 16-bit values High-Byte
05 |    | 0c | number of 16-bit values (1/2 number of databytes) Low-Byte
06 | 00 | 00 | 
07 | 01 | 2b |
08 | 02 | 00 |
09 | 03 | 01 |
10 | 04 | 02 |
11 | 05 | 00 | Throttle/Brake position High-Byte
12 | 06 | 00 | Throttle/Brake position Low-Byte (See below)
13 |    | 72 | Checksum High-byte
14 |    | 59 | Checksum Low-byte

The throttle/brake position logic seems to be directly lifted from Hobbywing's RC controllers.
The positions of both the throttle and brake, and also the hand brake switch, are linked together in one single signed 16-bit field. 
There is no extra bit for the hand brake switch. 

Combined, this field clearly represents the center position of an RC control stick usually used for both throttle and acceleration.

Connecting bluetooth doesn't change the reqgular request data, but introduces the tiniest bit of jitter into the stream.

#### Response

`01 17 00 26 18 01 a0 00 00 18 00 0c 01 00 00 00 00 00 00 13 eb 11 e8 6b c0 00 01 00 64 6f 2d`

Byte | Databyte | Value | Confirmed Function
--- | --- | --- | ---
00 |    | 01 | Address
01 |    | 17 | Reply to Function Code
02 |    | 00 | starting register high-byte
03 |    | 26 | starting register low-byte
04 |    | 18 | number of databytes
05 | 00 | 01 | Battery Voltage High-Byte
06 | 01 | a0 | Battery Voltage Low-Byte  V*0.1 (Example: 0x01a0=416=41.6 V)
07 | 02 | 00 | Amperage High-Byte
08 | 03 | 00 | Amperage Low-Byte A*0.01 (Example: 0x001F=31=0.31 A)
09 | 04 | 18 | Controller temperature
10 | 05 | 00 | 
11 | 06 | 0c | Corresponds with lock/unlock
12 | 07 | 01 | Control bits (Bit 4 on when beeper is active, Bit 3= Light on/off, Bits 0..1: Gear select)
13 | 08 | 00 | 
14 | 09 | 00 | 
15 | 10 | 00 | Copy of Request Throttle value High-Byte
16 | 11 | 00 | Copy of Request Throttle value Low-Byte
17 | 12 | 00 | Actual Speed High-Byte 
18 | 13 | 00 | Actual Speed Low-Byte, km/h*0.001 (e.g. 0x55F0=22000=22.000 km/h)
19 | 14 | 13 | Settling value High-Byte
20 | 15 | eb | Settling value Low-Byte, increases with wheel motion, decreases when wheel is stopped. Not related to power-off time-out.
21 | 16 | 11 | Trip Distance Mid-Byte
22 | 17 | e8 | Trip Distance Low-Byte
23 | 18 | 6b | Total Distance Mid-Byte
24 | 19 | c0 | Total Distance Low-byte 
25 | 20 | 00 | Trip Distance High-Byte, km*0.01 (e.g. 0x0011e8=4584=45.84 km; 0x001238=4664=46.64km)
26 | 21 | 01 | Total Distance Mid2 Byte 
27 | 22 | 00 | Total Distance High Byte km*0.001 (e.g. 0x00016ee0=93920=93.920 km). Always counts up regardless of wheel direction
28 | 23 | 64 | 
29 |    | 6f | Checksum High-byte
30 |    | 2d | Checksum Low-Byte
