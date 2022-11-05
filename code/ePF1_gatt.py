import asyncio
import time
from bleak import BleakClient

address = "c7:36:39:34:66:19"
READ_UUID = "0000f1f2-0000-1000-8000-00805f9b34fb"
SEND_UUID = "0000f1f1-0000-1000-8000-00805f9b34fb"

status={"gear":0,
        "soc":0,
        "speed":0,
        "voltage":0,
        "amps":0,
        "temperature":0,
        "tripkm":0,
        "totalkm":0,
        "speed1":0,
        "speed2":0,
        "speed3":0,
        "packet":0,
        "lastrec":0,
        "energy":0}

def callback(sender: int, data: bytearray):
    global status
    status['packet']+=1

    if (len(data)==25 and data[0]==175): #telemetry
        if(data[1]==0):
            status['gear']=data[4]+1
            status['soc']=data[5]
            status['speed']=(data[6]*256+data[7])*0.001
            status['voltage']=(data[10]*256+data[11])*0.1
            if(data[12]<128):
                amps=(data[12]*256+data[13])*0.01
            else:
                amps=(65536-(data[12]*256+data[13]))*(-0.01)
            status['amps']=amps
            status['temperature']=data[14]
            status['tripkm']=(data[15]*65536+data[16]*256+data[17])*0.1
            status['totalkm']=(data[18]*65536+data[19]*256+data[20])*0.1
            if(status['lastrec']!=0):
                status['energy']+=status['voltage']*status['amps']*(time.time()-status['lastrec'])
            status['lastrec']=time.time() #this packet has the V/A info, needed for Wh calculation

        elif(data[1]==1):
            status['speed1']=data[4]
            status['speed2']=data[5]
            status['speed3']=data[6]
            
    else:
        if(data[0]==1): #controller "UF" packet
            pass    #nothing implemented yet

def bar(inData,maxData,barlength):
    mystring='['
    try:
        intpercent=int((inData/maxData)*barlength)
        
        if intpercent>barlength:
            intpercent=barlength
        
        for i in  range(0,intpercent):
            mystring+='#'
        for i in  range(0,barlength-intpercent):
            mystring=mystring+'-'
    
    except: 
        pass
    
    mystring=mystring+']'
    return mystring

async def main(address):
    client = BleakClient(address)
    try:
        print("Connecting")
        await client.connect()
        await client.start_notify(READ_UUID, callback)
        print("Connected.")
        while True:
            if(time.time()-status['lastrec'])>0.2:
                send_data = await client.write_gatt_char(SEND_UUID, b'\xaa')

            print("Speed: {:0.3f} km/h {}, Odo: {:0.1f} km, Power: {:0.2f} W {} Energy: {:0.3f} Wh  P{}  ".format(status['speed'], bar(status['speed'],status['speed3'],25),status['totalkm'], status['voltage']*status['amps'], bar(status['voltage']*status['amps'],500,25), status['energy']/3600, status['packet']), end='\r')
            time.sleep(0.1)
    except Exception as e:
        print(e)
    finally:
        print()
        await client.disconnect()

asyncio.run(main(address))
