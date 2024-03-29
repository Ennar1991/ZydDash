/* ZydDash BLE for ESP32 by Ennar1991
 * Based on Arduino example sketches
 */

#include "Arduino.h"
#include "BLEDevice.h"
//#include "BLEScan.h"

#include <U8g2lib.h>

#ifdef U8X8_HAVE_HW_SPI
#include <SPI.h>
#endif
#ifdef U8X8_HAVE_HW_I2C
#include <Wire.h>
#endif

#define BTN_SWITCH_SCREEN 5 /* Connect a button to GND here to switch display screens */
#define BTN_MIN 1
#define BTN_MAX 100
char btnCnt = 0;    // counts up when physical button is pressed. Counts down when physical button is released.
bool btnState = false;  // is false when logical button is in released state and true when logical button is in pressed state
bool btnPulse = false;  // is true for one loop iteration when btnState becomes true

uint32_t telemetryMillis = 0;  // Internal variable to determine when next to ask for telemetry
uint32_t scanMillis = 0;       // Internal BLE scan interval helper to get rid of delay() in loop

//Select an appropriate display from these presets or change to another type (see u8g2 wiki)
//These are the most common OLED displays
// U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/ U8X8_PIN_NONE);
U8G2_SH1106_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, /* reset=*/U8X8_PIN_NONE);

//YOUR SCOOTER DATA HERE
//Scooter name (Bluetooth name)
static String devicename = "HW_EPF1";  // for some reason the scooter does not transmit its MAC address without asking. Use name instead.

//Select one of the following systems
#define SYSTEM_36V
//#define SYSTEM_48V
//#define SYSTEM_52V
//#define SYSTEM_60V
//#define SYSTEM_CUSTOM

// The remote service we wish to connect to.
static BLEUUID serviceUUID("0000f1f0-0000-1000-8000-00805f9b34fb");
// The characteristic of the remote service we are interested in.
static BLEUUID sendUUID("0000f1f1-0000-1000-8000-00805f9b34fb");  // Transmit Channel  CLI--> SRV
static BLEUUID readUUID("0000f1f2-0000-1000-8000-00805f9b34fb");  // Receive Channel SRV--> CLI

static boolean doConnect = false;
static boolean connected = false;
static boolean doScan = false;
static BLERemoteCharacteristic* pWriteCharacteristic;
static BLERemoteCharacteristic* pReadCharacteristic;

static BLEAdvertisedDevice* myDevice;

struct {
  int gear = 0;
  int soc = 0;
  float actualSpeed = 0;
  float voltage = 0;
  float current = 0;
  int temperature = 0;
  float tripkm = 0;
  float totalkm = 0;
  int speed1 = 0;
  int speed2 = 0;
  int speed3 = 0;
  int packet = 0;
  uint32_t timestamp = 0;
  float energy = 0;
} zydtechTelemetry;

enum displayModes {
  DISPLAY_PAGE_SUMMARY,
  DISPLAY_PAGE_TRIP,
  DISPLAY_PAGE_BARS,
  DISPLAY_PAGE_WATTS
};

displayModes displayMode = DISPLAY_PAGE_BARS;


#ifdef SYSTEM_36V
float MinVoltage=31.0; //Minimum discharge voltage (for bargraph), usually 3.1 to 3.2 V per cell
float MaxVoltage=42.0; //Maximum charge voltage, usually 4.2 V per cell
#endif
#ifdef SYSTEM_48V
float MinVoltage=37.2;
float MaxVoltage=50.4;
#endif
#ifdef SYSTEM_52V
float MinVoltage=43.4;
float MaxVoltage=58.8;
#endif
#ifdef SYSTEM_60V
float MinVoltage=46.5;
float MaxVoltage=63.0;
#endif

//You're free to enter a custom setup here
#ifdef SYSTEM_CUSTOM
float MinVoltage=0.0;
float MaxVoltage=100.0;
#endif


void outputData(displayModes displayMode) {
  // Prints the telemetry data to the serial interface in a formatted way
  Serial.print("Speed: ");
  Serial.print(zydtechTelemetry.actualSpeed);

  Serial.print("km/h - Volts: ");
  Serial.print(zydtechTelemetry.voltage);

  Serial.print("V - Current: ");
  Serial.print(zydtechTelemetry.current);

  Serial.print("A - Temp: ");
  Serial.print(zydtechTelemetry.temperature);

  Serial.print("°C - Trip: ");
  Serial.print(zydtechTelemetry.tripkm);

  Serial.print("km - Total: ");
  Serial.print(zydtechTelemetry.totalkm);

  Serial.print("km - Gear: ");
  Serial.print(zydtechTelemetry.gear);

  Serial.print(" - Energy: ");
  Serial.print(zydtechTelemetry.energy / 3600);

  Serial.print(" Wh - SOC: ");
  Serial.print(zydtechTelemetry.soc);

  Serial.println("%");

  char textbuffer[32] = {};
  u8g2.clearBuffer();  // clear the internal memory

  switch (displayMode) {
    default:
    case DISPLAY_PAGE_SUMMARY:                   // Prints a summary of data
      u8g2.setFont(u8g2_font_busdisplay8x5_tr);  // choose a suitable font
      sprintf(textbuffer, "Total:  %06.1f km", zydtechTelemetry.totalkm);
      u8g2.drawStr(00, 10, textbuffer);
      sprintf(textbuffer, "Trip:   %04.1f km", zydtechTelemetry.tripkm);
      u8g2.drawStr(00, 20, textbuffer);
      sprintf(textbuffer, "Speed:  %04.1f km/h", zydtechTelemetry.actualSpeed);
      u8g2.drawStr(00, 30, textbuffer);
      sprintf(textbuffer, "Power:  %05.1f W  %04.1f A", zydtechTelemetry.voltage * zydtechTelemetry.current, zydtechTelemetry.current);
      u8g2.drawStr(00, 40, textbuffer);
      sprintf(textbuffer, "Batt:   %03d %%  %04.1f V", zydtechTelemetry.soc, zydtechTelemetry.voltage);
      u8g2.drawStr(00, 50, textbuffer);
      sprintf(textbuffer, "Energy: %05.1f Wh", zydtechTelemetry.energy / 3600);
      u8g2.drawStr(00, 60, textbuffer);
      break;
    case DISPLAY_PAGE_TRIP:                   // prints a large trip counter
      u8g2.setFont(u8g2_font_busdisplay8x5_tr);  // choose a suitable font
      u8g2.drawStr(50, 10, "TRIP");
      u8g2.setFont(u8g2_font_logisoso42_tn);  // choose a suitable font
      sprintf(textbuffer, "%04.1f Km", zydtechTelemetry.tripkm);
      u8g2.drawStr(20, 60, textbuffer);
      break;
    case DISPLAY_PAGE_WATTS:                   // prints a large wattmeter
      u8g2.setFont(u8g2_font_busdisplay8x5_tr);  // choose a suitable font
      u8g2.drawStr(42, 10, "POWER");
      u8g2.setFont(u8g2_font_logisoso42_tn);  // choose a suitable font
      sprintf(textbuffer, "%04d", (int)(zydtechTelemetry.voltage * zydtechTelemetry.current));
      u8g2.drawStr(20, 60, textbuffer);
      break;
  

    case DISPLAY_PAGE_BARS:                      // outputs speed (S), amps (A), volts (V), soc(B), Power (P) as bars
      u8g2.setFont(u8g2_font_busdisplay8x5_tr);  // choose a suitable font
      u8g2.drawStr(00, 10, "B");
      u8g2.drawStr(00, 20, "V");
      u8g2.drawStr(00, 30, "A");
      u8g2.drawStr(00, 40, "P");
      u8g2.drawStr(00, 50, "S");

      for (int i = 0; i <= 40; i += 10) {
        u8g2.drawFrame(10, i, 118, 10);
      }
      u8g2.drawBox(10, 0, ((float)zydtechTelemetry.soc / 100.0) * 118, 10);
      u8g2.drawBox(10, 10, (((float)zydtechTelemetry.voltage - MinVoltage) / (MaxVoltage-MinVoltage)) * 118, 10);
      u8g2.drawBox(10, 20, abs((float)zydtechTelemetry.current / 16.0) * 118, 10);
      u8g2.drawBox(10, 30, abs(((float)zydtechTelemetry.voltage * (float)zydtechTelemetry.current) / 600.0) * 118, 10);
      u8g2.drawBox(10, 40, ((float)zydtechTelemetry.actualSpeed / 30) * 118, 10);

      sprintf(textbuffer, "Total:  %06.1f km", zydtechTelemetry.totalkm);
      u8g2.drawStr(00, 60, textbuffer);

      break;
  }
  //Debug output: Button
  //u8g2.setFont(u8g2_font_busdisplay8x5_tr);  // choose a suitable font
  //sprintf(textbuffer, "%d", btnCnt);
  //u8g2.drawStr(100, 60, textbuffer);

  u8g2.sendBuffer();  // transfer internal memory to the display
  
}

static void notifyCallback(
    BLERemoteCharacteristic* pBLERemoteCharacteristic,
    uint8_t* pData,
    size_t length,
    bool isNotify) {
  zydtechTelemetry.packet++;

  if (length == 25 and pData[0] == 175) {  // Telemetry Data from address 0xAF
    if (pData[1] == 0) {                   // Packet Type 1
      zydtechTelemetry.gear = pData[4] + 1;
      zydtechTelemetry.soc = pData[5];
      zydtechTelemetry.actualSpeed = (pData[6] * 256 + pData[7]) * 0.001;
      zydtechTelemetry.voltage = (pData[10] * 256 + pData[11]) * 0.1;

      if (pData[12] < 128)
        zydtechTelemetry.current = (pData[12] * 256 + pData[13]) * 0.01;
      else
        zydtechTelemetry.current = (65535 - (pData[12] * 256 + pData[13])) * (-0.01);
      zydtechTelemetry.temperature = pData[14];
      zydtechTelemetry.tripkm = (pData[16] * 256 + pData[17]) * 0.1; //pData[15] * 65536 Byte 15 might have a different role, discovered with Hiboy firmware
      zydtechTelemetry.totalkm = (pData[18] * 65536 + pData[19] * 256 + pData[20]) * 0.1;

      // Calculate used energy (Ws) since boot
      if (zydtechTelemetry.timestamp != 0) {
        zydtechTelemetry.energy += (zydtechTelemetry.voltage * zydtechTelemetry.current) * ((float)(millis() - zydtechTelemetry.timestamp) * 0.001);
      }

      zydtechTelemetry.timestamp = millis();

      //Debug output of raw data
      /*
      for(int i=0; i<length;i++) {
        Serial.print(pData[i],HEX);
        Serial.print('-');
      }
      Serial.println();
      */
      outputData(displayMode);

    } else if (pData[1] == 1) {  // Packet Type 2
      zydtechTelemetry.speed1 = pData[4];
      zydtechTelemetry.speed2 = pData[5];
      zydtechTelemetry.speed3 = pData[6];
    }

  }

  else {
    if (pData[0] == 1) {
      // controller "UF" packet
      // nothing implemented yet
    }
  }
}

class MyClientCallback : public BLEClientCallbacks {
  void onConnect(BLEClient* pclient) {
    u8g2.clearBuffer();                        // clear the internal memory
    u8g2.setFont(u8g2_font_busdisplay8x5_tr);  // choose a suitable font
    u8g2.drawStr(0, 10, "Connected!");
    u8g2.sendBuffer();
  }

  void onDisconnect(BLEClient* pclient) {
    connected = false;
    Serial.println("onDisconnect");
    u8g2.clearBuffer();                        // clear the internal memory
    u8g2.setFont(u8g2_font_busdisplay8x5_tr);  // choose a suitable font
    u8g2.drawStr(0, 10, "Disconnected!");
    u8g2.sendBuffer();
    doScan = true;
  }
};

bool connectToServer() {
  Serial.print("Forming a connection to ");
  Serial.println(myDevice->getAddress().toString().c_str());

  BLEClient* pClient = BLEDevice::createClient();
  Serial.println(" - Created client");

  pClient->setClientCallbacks(new MyClientCallback());

  // Connect to the remove BLE Server.
  pClient->connect(myDevice);  // if you pass BLEAdvertisedDevice instead of address, it will be recognized type of peer device address (public or private)
  Serial.println(" - Connected to server");
  pClient->setMTU(517);  // set client to request maximum MTU from server (default is 23 otherwise)

  // Obtain a reference to the service we are after in the remote BLE server.
  BLERemoteService* pRemoteService = pClient->getService(serviceUUID);
  if (pRemoteService == nullptr) {
    Serial.print("Failed to find our service UUID: ");
    Serial.println(serviceUUID.toString().c_str());
    pClient->disconnect();
    return false;
  }
  Serial.println(" - Found our service");

  // Obtain a reference to the characteristic in the service of the remote BLE server.
  pWriteCharacteristic = pRemoteService->getCharacteristic(sendUUID);
  pReadCharacteristic = pRemoteService->getCharacteristic(readUUID);
  if (pReadCharacteristic == nullptr) {
    Serial.print("Failed to find our characteristic UUID: ");
    Serial.println(readUUID.toString().c_str());
    pClient->disconnect();
    return false;
  }
  Serial.println(" - Found our characteristic");

  // Read the value of the characteristic.
  if (pReadCharacteristic->canRead()) {
    std::string value = pWriteCharacteristic->readValue();
    Serial.print("The characteristic value was: ");
    Serial.println(value.c_str());
  }

  if (pReadCharacteristic->canNotify())
    pReadCharacteristic->registerForNotify(notifyCallback);

  connected = true;
  return true;
}
/**
 * Scan for BLE servers and find the first one that advertises the service we are looking for.
 */
class MyAdvertisedDeviceCallbacks : public BLEAdvertisedDeviceCallbacks {
  /**
   * Called for each advertising BLE server.
   */
  void onResult(BLEAdvertisedDevice advertisedDevice) {
    Serial.print("BLE Advertised Device found: ");
    Serial.println(advertisedDevice.toString().c_str());

    // We have found a device, let us now see if it contains the service we are looking for.
    // if (advertisedDevice.haveServiceUUID() && advertisedDevice.getAddress()== BLEAddress /* && advertisedDevice.isAdvertisingService(serviceUUID)*/) {
    if (strcmp(advertisedDevice.getName().c_str(), devicename.c_str()) == 0 /* && advertisedDevice.isAdvertisingService(serviceUUID)*/) {
      BLEDevice::getScan()->stop();
      myDevice = new BLEAdvertisedDevice(advertisedDevice);
      doConnect = true;
      doScan = true;

    }  // Found our server
  }    // onResult
};     // MyAdvertisedDeviceCallbacks

void setup() {
  pinMode(BTN_SWITCH_SCREEN, INPUT_PULLUP);

  u8g2.setBusClock(1000000);
  u8g2.begin();
  u8g2.setBusClock(1000000);
  u8g2.clearBuffer();                        // clear the internal memory
  
  u8g2.setFont(u8g2_font_busdisplay8x5_tr);  // choose a suitable font
  u8g2.drawStr(0, 20, "*ZydDash BLE*");
  u8g2.drawStr(0, 30, "2022 by Ennar");
  
  u8g2.drawStr(0, 50, "Connecting to");
  u8g2.drawStr(0, 60, devicename.c_str());
  
  u8g2.sendBuffer();  // transfer internal memory to the display

  Serial.begin(115200);
  Serial.println("Starting Arduino BLE Client application...");
  BLEDevice::init("");

  // Retrieve a Scanner and set the callback we want to use to be informed when we
  // have detected a new device.  Specify that we want active scanning and start the
  // scan to run for 5 seconds.
  BLEScan* pBLEScan = BLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);
  pBLEScan->setActiveScan(true);
  pBLEScan->start(0, false);
}  // End of setup.

// This is the Arduino main loop function.
void loop() {
  // If the flag "doConnect" is true then we have scanned for and found the desired
  // BLE Server with which we wish to connect.  Now we connect to it.  Once we are
  // connected we set the connected flag to be true.
  if (doConnect == true) {
    if (connectToServer()) {
      Serial.println("We are now connected to the BLE Server.");
      doScan = false;
    } else {
      Serial.println("We have failed to connect to the server; there is nothin more we will do.");
      doScan = true;
    }
    doConnect = false;
  }

  // If we are connected to a peer BLE Server, update the characteristic each time we are reached
  // with the current time since boot.
  if (connected && millis() > telemetryMillis) {
    telemetryMillis = millis() + 1000;
    String newValue = "A";
    // Serial.println("Setting new characteristic value to \"" + newValue + "\"");

    // Set the characteristic's value to be the array of bytes that is actually a string.
    pWriteCharacteristic->writeValue(newValue.c_str(), newValue.length());
  } else if (doScan && millis() > scanMillis) {
    // scanMillis=millis()+5000;
    doScan = false;
    BLEDevice::getScan()->start(0);  // this is just example to start scan after disconnect, most likely there is better way to do it in arduino
  }

  // debounced button handling
  if (digitalRead(BTN_SWITCH_SCREEN) == 0) {  // physical button
    btnCnt++;

  } else if (digitalRead(BTN_SWITCH_SCREEN) == 1) {
    btnCnt--;
    btnPulse = false;
  }

  if (btnCnt <= BTN_MIN) {
    btnCnt = BTN_MIN;
    btnState = false;
  }

  if (btnCnt == BTN_MAX && btnState == false) {
    btnPulse = true;  // generate ONE impulse when counting up
    btnState = true;
    btnCnt = BTN_MAX;
  } else {
    btnPulse = false;  // generate ONE impulse when counting up
  }

  if (btnCnt > BTN_MAX) btnCnt = BTN_MAX;

  if (btnPulse) {
    switch (displayMode) {
      case DISPLAY_PAGE_BARS:
        displayMode = DISPLAY_PAGE_SUMMARY;
        break;
      case DISPLAY_PAGE_SUMMARY:
        displayMode = DISPLAY_PAGE_TRIP;
        break;
      case DISPLAY_PAGE_TRIP:
        displayMode = DISPLAY_PAGE_WATTS;
        break;
      case DISPLAY_PAGE_WATTS:
        displayMode = DISPLAY_PAGE_BARS;
        break;
    }
  }

  delay(1);  // Throttle main loop and yield control
}  // End of loop