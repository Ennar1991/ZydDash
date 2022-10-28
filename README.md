# ZydDash
Additional dashboard display for Zydtech based electric scooters using BLE

Wanting to have a more permanent dashboard with more usable information while also collecting more detailed battery data and not sacrificing my phone, I went and decoded the data protocol of my ePowerFun ePF-1 which uses a Zydtech HW9027 controller as an ECU. The display has a built-in bluetooth module for communicating with an app supplied by the vendor.

Decoding most of the telemetry and commands for the Display/ECU combo has been straightforward, although there is more to discover in the Update mode. A detailed description and the so-far decoded protocol will follow shortly.
