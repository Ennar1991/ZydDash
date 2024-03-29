# BLE Telemetry

## Overview
The app communicates with the scooter's display through BLE 4.1
The app uses AT commands for high-level data like access control (password check/change, name change) and proprietary protocols for the low-level data (Telemetry, configuration, commands).
The low-level protocols are largely based on MODBUS but have their own special features. It is worth checking out e.g. https://ozeki.hu/p_5873-modbus-function-codes.html for further information about MODBUS.

Used tools are: 
* nRF Connect on any Android mobile phone
* Android's own bluetooth HCI logging ability, turn on in the developer options
* wireshark for decoding HCI log files
* ePowerFun app
* HobbyWing/Zydtech UniScooter app
* HobbyWing HW Link V2 app

## BLE telemetry
The scooter exposes two custom services. I will separate them into 'high level data' and 'low level data'. Both services are split into two characteristics, one for writing a request and one for reading back the result.

### High level data service
UUID beginning with 0000f2f0

Char 1 (Client-transmit F2F1) UUID beginning with: 0000f2f1

Char 1 (Client-receive F2F2) UUID beginning with: 0000f2f2


I have found the following commands to work:
* AT+PWD[123456] 
  * Asks to check if the 6-digit password provided in the [] brackets is correct. There is no real security or access control provided by this password, it is only a placebo for the app.
  * Response type 1: `OK+PWD:Y` (password is correct)
  * Response type 2: `OK+PWD:N` (password is not correct and connection is subsequently terminated)
* AT+PWDM[123456]
  * Changes the password to the 6-digit password provided in the [] brackets. No knowledge of the old password is required to do this.
* AT+NAME[NewName]
  * Changes the scooter's name to the new name provided in the [] brackets. No knowledge of the password is required to do this. Renaming the scooter to something not starting with HW_ (HobbyWing) or e.g. ePF (ePowerFun) can break compatibility with some vendor's apps that are looking for names starting with "their" abbreviation.

### Low level data service
UUID beginning with `0000f1f0`

Char 1 (Client-receive) UUID beginning with `0000f1f2`

Char 2 (Client-transmit) UUID beginning with `0000f1f1`


Here lie the really interesting bits. Sending any hex value to characteristic `0000f1f1` will trigger a burst of twelve notifications, sent on characteristic `0000f1f2`. Looking closely, these are two different but repeating data structures.

Sending a protocol conform data string, you can configure the three speeds (for the three selectable 'gears'), light on/off, reset the trip distance counter, lock/unlock the scooter, select a gear.

#### App control/telemetry request

The app sends configuration/control requests in the following form:
`af 00 0a 82 03 05 0f 14 67 3d` looking somewhat like MODBUS, but not quite. The Checksum is indeed the Big-endian MODBUS-CRC.

Byte | Value | Explanation, function
--- | --- | ---
00 | 0xAF | Address, always 0xAF for an ePowerFun scooter (0xAB for other vendors)
01 | 0x00 | Sub-address, always 0x00
02 | 0x0A | Total number of bytes contained in this message (including head and checksum)
03 | 0x82 | configuration bits (nd currently selected gear, see below
04 | 0x03 | Unknown, always 0x03
05 | 0x05 | Speed for 1st gear in km/h
06 | 0x0F | Speed for 2nd gear in km/h
07 | 0x14 | Speed for 3rd gear in km/h
08 | 0x67 | Checksum High-Byte
09 | 0x3D | Checksum Low-Byte

The app will sometimes send other kinds of requests that I haven't fully understood yet.

##### Configuration/control bits (Byte 3):

Bit |  Explanation, function
--- | ---
7 | 0=Scooter locked, 1=Scooter unlocked
6 | ?
5 | ?
4 | ?
3 | 1=Reset trip distance
2 | 0=Lights off, 1=Lights on
1 | Gear select, combine with bit 0
0 | Gear select, 0=1st gear, 1=2nd gear, 2=3rd gear

#### Scooter response to control/telemetry request

The scooter will always respond with a burst of notifications, regardless of what is sent on characteristic `0000f1f1`.
The response will be divided into two distinct types of packages, although longer, with an identical protocol to the app request.

##### Packet type 1
`AF 00 19 01 02 30 00 00 00 00 01 70 00 00 18 00 01 10 00 01 10 0C 02 06 0C`

Byte | Value | Explanation, function
--- | --- | ---
00 | 0xAF | Address, always 0xAF for an ePowerFun scooter (0xAB or 0xA5 for other vendors)
01 | 0x00 | Sub-address, 0x00 for packet 1
02 | 0x19 | Total number of bytes contained in this message (including head and checksum)
03 | 0x01 | Unknown, always 0x01
04 | 0x02 | Selected gear (here: 3rd gear selected)
05 | 0x30 | State of Charge (SOC) of battery in %, 0x30=48 %
06 | 0x00 | Actual speed High-Byte (16 Bit total)
07 | 0x00 | Actual speed Low-Byte, km/h*0.001 (Example: 0x3B44=15172=15.172 km/h)
08 | 0x00 | Actual speed High-Byte (Copy)
09 | 0x00 | Actual speed Low-Byte (Copy)
10 | 0x01 | Battery voltage High-Byte (16 Bit total)
11 | 0x70 | Battery voltage Low-Byte, V*0.1 (Example: 0x0170=368=36.8 V)
12 | 0x00 | Amperage High-Byte (16 Bit total)
13 | 0x00 | Amperage Low-Byte, A*0.01 (Example: 0x001F=31=0.31 A)
14 | 0x18 | Temperature in °C (Example: 0x18=24=24 °C)
15 | 0x00 | Unknown, Padding? Always "D9" with Hiboy S2 firmware
16 | 0x01 | Trip distance  High-Byte (16 Bit total)
17 | 0x10 | Trip distance  Low-Byte, km*0.1 (Example: 0x0110=272=27.2 km)
18 | 0x00 | Total distance High-Byte (24 Bit total)
19 | 0x01 | Total distance Middle-Byte
20 | 0x10 | Total distance Low-Byte, km*0.1 (Example: 0x000110=272=27.2 km)
21 | 0x0C | Unknown, always 0x0C
22 | 0x02 | Selected gear (Copy)
23 | 0x06 | Checksum High Byte (16 Bits total)
24 | 0x0C | Checksum Low Byte

##### Packet type 2:
Byte | Value | Explanation, function
--- | --- | ---
00 | 0xAF | Address, always 0xAF for an ePowerFun scooter (0xAB for other vendors)
01 | 0x01 | Sub-address, 0x01 for packet 2
02 | 0x19 | Total number of bytes contained in this message (including head and checksum)
03 | 0x03 | Unknown, always 0x03
04 | 0x05 | Speed for 1st gear in km/h
05 | 0x0F | Speed for 2nd gear in km/h
06 | 0x16 | Speed for 3rd gear in km/h
07 | 0x00 | Always 0x00
...
22 | 0x00 | Always 0x00
23 | 0x40 | Checksum High Byte (16 Bits total)
24 | 0xD2 | Checksum Low Byte

#### Special commands/Upgrade mode

Sending a magic control request configures the display into "UF" mode, usually only seen when updating the firmware. This also happens with the Uniscooter app when changing the parameters for acceleration and brake response:

`a5 00 ff 00 00 00 00 5a`

To get out of "UF" mode, send:

`a5 ff 00 00 00 00 00 5a`

while in "UF" mode, the app seems to be directly communicating with the motor driver instead of the display. This is indicated by the address changing and the protocol resembling 16-bit MODBUS even more:

Modbus Function Code 03 (read multiple holding registers) is used:

Request: `01 03 00 30 00 05 85 c6` (Address 01, Function Code 03, start at address 0x0030, read 0x0005 registers, checksum)

Response: `01 03 00 30 0a 00 00 00 30 00 00 00 00 00 00 d3 27` (Address 01 responding to Function Code 03, starting at address 0x0030, 0x0a databytes will follow, [data], checksum)

Writing registers is achieved with Function Code 17, but with its own quirks. See the display telemetry document for more details.
