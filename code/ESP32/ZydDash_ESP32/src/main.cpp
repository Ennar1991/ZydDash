/* ZydDash BLE for ESP32 by Ennar1991
 * Based on Arduino example sketches
 */

#include "Arduino.h"
#include "BLEDevice.h"
//#include "BLEScan.h"

// The remote service we wish to connect to.
static BLEAddress BLEAddress("c7:36:39:34:66:19");
static String devicename = "HW_UG018376"; //for some reason the scooter does not transmit its MAC address without asking. Use name instead.
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

void outputData() {
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
  Serial.print(zydtechTelemetry.energy/3600);

  Serial.print(" Wh - SOC: ");
  Serial.print(zydtechTelemetry.soc);

  Serial.println("%");
}

static void notifyCallback(
    BLERemoteCharacteristic* pBLERemoteCharacteristic,
    uint8_t* pData,
    size_t length,
    bool isNotify) {
  /*
    Serial.print("Notify callback for characteristic ");
    Serial.print(pBLERemoteCharacteristic->getUUID().toString().c_str());
    Serial.print(" of data length ");
    Serial.println(length);
    Serial.print("data: ");
    Serial.println((char*)pData);
  */
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
        zydtechTelemetry.current = (65536 - (pData[12] * 256 + pData[13])) * (-0.01);
      zydtechTelemetry.temperature = pData[14];
      zydtechTelemetry.tripkm = (pData[15] * 65536 + pData[16] * 256 + pData[17]) * 0.1;
      zydtechTelemetry.totalkm = (pData[18] * 65536 + pData[19] * 256 + pData[20]) * 0.1;

      // Calculate used energy (Ws) since boot
      if (zydtechTelemetry.timestamp != 0) {
        zydtechTelemetry.energy += (zydtechTelemetry.voltage * zydtechTelemetry.current) * ((float)(millis() - zydtechTelemetry.timestamp) * 0.001);
      }

      zydtechTelemetry.timestamp = millis();
      outputData();

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
  }

  void onDisconnect(BLEClient* pclient) {
    connected = false;
    Serial.println("onDisconnect");
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
  Serial.begin(115200);
  Serial.println("Starting Arduino BLE Client application...");
  BLEDevice::init("");

  // Retrieve a Scanner and set the callback we want to use to be informed when we
  // have detected a new device.  Specify that we want active scanning and start the
  // scan to run for 5 seconds.
  BLEScan* pBLEScan = BLEDevice::getScan();
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  pBLEScan->setInterval(1349);
  pBLEScan->setWindow(449);
  pBLEScan->setActiveScan(true);
  pBLEScan->start(5, false);
}  // End of setup.

// This is the Arduino main loop function.
void loop() {
  // If the flag "doConnect" is true then we have scanned for and found the desired
  // BLE Server with which we wish to connect.  Now we connect to it.  Once we are
  // connected we set the connected flag to be true.
  if (doConnect == true) {
    if (connectToServer()) {
      Serial.println("We are now connected to the BLE Server.");
    } else {
      Serial.println("We have failed to connect to the server; there is nothin more we will do.");
    }
    doConnect = false;
  }

  // If we are connected to a peer BLE Server, update the characteristic each time we are reached
  // with the current time since boot.
  if (connected) {
    String newValue = "A";
    // Serial.println("Setting new characteristic value to \"" + newValue + "\"");

    // Set the characteristic's value to be the array of bytes that is actually a string.
    pWriteCharacteristic->writeValue(newValue.c_str(), newValue.length());
  } else if (doScan) {
    BLEDevice::getScan()->start(0);  // this is just example to start scan after disconnect, most likely there is better way to do it in arduino
  }

  delay(1000);  // Delay a second between loops.
}  // End of loop