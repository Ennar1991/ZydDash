# ZydDash
Additional dashboard display for Zydtech based electric scooters using BLE

Wanting to have a more permanent dashboard with more usable information while also collecting more detailed battery data and not sacrificing my phone, I went and decoded the data protocol of my ePowerFun ePF-1 which uses a Zydtech HW9027 or similar motor driver. The display has a built-in bluetooth module for communicating with an app supplied by the vendor.
Decoding most of the Bluetooth telemetry and commands for the Display/Driver combo has been very straightforward, although there is more to discover in the Update mode. 

So far, the interesting bits like current speed, voltage, total distance etc. can be read by using a BLE app and a bit of decoding.