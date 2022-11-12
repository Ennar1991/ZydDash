# ZydDash
Alternative dashboard display for Zydtech based electric scooters using BLE

Wanting to have a more permanent dashboard with more usable information while also collecting more detailed battery data and not sacrificing my phone, I went and decoded the data protocol of my ePowerFun ePF-1 which uses a Zydtech HW9027 or similar motor driver. The display has a built-in bluetooth module for communicating with an app supplied by the vendor.
Decoding most of the Bluetooth telemetry and commands for the Display/Driver combo has been very straightforward, although there is more to discover in the Update mode. 

So far, the interesting bits like current speed, voltage, total distance etc. can be read by using a BLE app and a bit of decoding.

To read up on my findings, go to `BLE_Telemetry.md`.

The display data bus is discussed in-depth in `Display_Telemetry_Analyzing.md`

More on the individual registers can be seen in `decoding_memory.md`

The scooter's data protocols, which are primarily based on MODBUS, are explained in `commands.md` 

An example app is provided with `ePF1_gatt.py`. Find out your scooter's BLE MAC and characteristic UUIDs and look for the first byte in the telemetry packets. It typically starts with `AF`, `AB` or `A5`. The app will connect to your scooter and try to read and interpret the data received on the bluetooth interface.

All further development is continued in `ePF1_gatt_gui.py` which is an extended and GUIfied version of the core code. You will need to install pysimplegui and libscrc to run it.
