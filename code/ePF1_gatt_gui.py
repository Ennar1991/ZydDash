import asyncio
import time
from bleak import BleakClient
import PySimpleGUI as sg
import libscrc

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
        "timestamp":0,
        "energy":0}

memorymap=[0]*4096 #16-bit registers

maxWatts=500
barSize=20


#Notify Callback
def callback(sender: int, data: bytearray):
    global status
    global memorymap
    global updateMap


    if (len(data)==25 and data[0]==175): #BLE telemetry
        status['packet']+=1
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
            if(status['timestamp']!=0):
                status['energy']+=status['voltage']*status['amps']*(time.time()-status['timestamp'])
            status['timestamp']=time.time() #this packet has the V/A info, needed for Wh calculation

        elif(data[1]==1):
            status['speed1']=data[4]
            status['speed2']=data[5]
            status['speed3']=data[6]
            
    else:
        #print("UF ", end='') 
        #print(data)
        if(data[0]==1): #controller "UF" packet
            if(data[1]==3): # Read address function code
                #print("FC03 (read)")
                startAddress=(data[2]*256)+data[3]
                dataLength=int(data[4]/2)
                #print('startAddress: {}, dataLength: {}'.format(startAddress,dataLength))
                for i in range(0,dataLength):
                    #print("{:04x}: {:02x}{:02x}".format(startAddress+i,data[5+(2*i)],data[6+(2*i)]))
                    memorymap[startAddress+i]=data[5+(2*i)]*256+data[6+(2*i)]
                
            

#Helper function to create a simple bargraph
def bar(inData,maxData,barlength):
    mystring='['
    try:
        intpercent=int((abs(inData)/maxData)*barlength)
        
        if intpercent>barlength:
            intpercent=barlength
        
        for i in  range(0,intpercent):
            if inData>0:
                mystring+='#'
            else:
                mystring+='X'
            
        for i in  range(0,barlength-intpercent):
            mystring=mystring+'-'
    
    except: 
        pass
    
    mystring=mystring+']'
    return mystring

def make_window(theme=None):
    labelXsize=11
    barXsize=20
    textXsize=10
    layout=[[sg.Text('Speed',s=(labelXsize,1)), sg.ProgressBar(22, orientation='h', s=(barXsize,20), k='-SPEEDBAR-'),sg.Text(k='-SPEEDTEXT-', s=(textXsize,1))],
            [sg.Text('Input Power',s=(labelXsize,1)), sg.ProgressBar(maxWatts, orientation='h', s=(barXsize,20), k='-POWERBAR-'),sg.Text(k='-POWERTEXT-', s=(textXsize,1))],
            [sg.Text('Battery SOC',s=(labelXsize,1)), sg.ProgressBar(100, orientation='h', s=(barXsize,20), k='-BATBAR-'),sg.Text(k='-BATTEXT-', s=(textXsize,1))],
            [sg.Text('Selected Gear',s=(labelXsize,1)),sg.Text(k='-GEARTEXT-', s=(textXsize,1))],
            [sg.Text('Trip distance',s=(labelXsize,1)), sg.Text(k='-TRIPTEXT-', s=(textXsize,1))],
            [sg.Text('Total distance',s=(labelXsize,1)), sg.Text(k='-TOTALTEXT-', s=(textXsize,1))],
            [sg.Text('Energy',s=(labelXsize,1)), sg.Text(k='-WATTHOURSTEXT-', s=(textXsize,1))],
            [sg.Text('Temperature',s=(labelXsize,1)), sg.Text(k='-TEMPTEXT-', s=(textXsize,1))],
            [sg.Button('Reset Trip', k='-RESETTRIP-'), sg.Button('UF mode ON', k='-UFON-'), sg.Button('UF mode OFF', k='-UFOFF-'), sg.Button('Read memory 0x20', k='-READMEMORY-'),sg.Button('Dump memory', k='-READMEMORY2-')],
            [sg.Table([[0],[10],[20],[30],[40],[50],[60],[70],[80],[90]], ['Addr','0000','0001','0002','0003','0004','0005','0006','0007','0008','0009','000a','000b','000c','000d','000e','000f'], num_rows=32, k='-MEMORYMAP-')]
            ]
    window = sg.Window('ePF-1 GUI', layout, finalize=True, keep_on_top=True)
    return window

def tableMap(datatable):
    memMap= [ [0]*17 for i in range(256)]
    for row in range(0,256):
        memMap[row][0]='{:02x}'.format(row*16)
        for col in range(0,16):
            memMap[row][1+col]='{:04x}'.format(datatable[(row*16)+col])

    return memMap            

#main loop, must be created as asyncio thread
async def main(address):
    client = BleakClient(address)
    try:
        print("Connecting")
        await client.connect()
        await client.start_notify(READ_UUID, callback)
        print("Connected.")
        maxspeed=22
        telemetryOn=True
        updateMap=True
        while True:
            event, values = window.read(timeout=100)
            #time.sleep(0.1)
            
            if event == '-RESETTRIP-':
                #send_data = await client.write_gatt_char(SEND_UUID, b'\xaf\x00\x0a\x')
                pass
                
            if event == '-UFON-':
                send_data = await client.write_gatt_char(SEND_UUID, b'\xa5\x00\xff\x00\x00\x00\x00\x5a')
                telemetryOn=False
            
            if event == '-UFOFF-':
                send_data = await client.write_gatt_char(SEND_UUID, b'\xa5\xff\x00\x00\x00\x00\x00\x5a')
                telemetryOn=True
            
            if event == '-READMEMORY-':
                mydata=b'\x01\x03\x00\x20\x00\x01'
                mycrc=libscrc.modbus(mydata).to_bytes(2, byteorder='little')
                send_data = await client.write_gatt_char(SEND_UUID, mydata+mycrc)
                #read_data= await client.read_gatt_char(READ_UUID)
                window['-MEMORYMAP-'].update(tableMap(memorymap))
            
            if event == '-READMEMORY2-':
                for i in range (0,256):
                    mydata=b'\x01\x03'+(i*16).to_bytes(2, byteorder='big')+b'\x00\x10'
                    
                    mycrc=libscrc.modbus(mydata).to_bytes(2, byteorder='little')
                    print(mydata+mycrc)
                    send_data = await client.write_gatt_char(SEND_UUID, mydata+mycrc)
                    time.sleep(0.1)
                    window['-MEMORYMAP-'].update(tableMap(memorymap))
                
                #read_data= await client.read_gatt_char(READ_UUID)
                #

            if event == sg.WIN_CLOSED or event == 'Exit':
                break
            
            #window['-MEMORYMAP-'].update(tableMap(memorymap))
            
            window['-SPEEDBAR-'].update(status['speed'])
            window['-SPEEDTEXT-'].update('{:0.3f} km/h'.format(status['speed']))
            
            window['-POWERBAR-'].update(status['voltage']*status['amps'])
            window['-POWERTEXT-'].update('{:0.2f} W'.format(status['voltage']*status['amps']))
            
            window['-BATBAR-'].update(status['soc'])
            window['-BATTEXT-'].update('{} %'.format(status['soc']))
            
            window['-GEARTEXT-'].update('{}'.format(status['gear']))
            window['-TRIPTEXT-'].update('{:0.1f} km'.format(status['tripkm']))
            window['-TOTALTEXT-'].update('{:0.1f} km'.format(status['totalkm']))
            window['-WATTHOURSTEXT-'].update('{:0.3f} Wh'.format(status['energy']/3600))
            window['-TEMPTEXT-'].update('{:} °C'.format(status['temperature']))
            
            if telemetryOn==True and (time.time()-status['timestamp'])>0.2:
                send_data = await client.write_gatt_char(SEND_UUID, b'\xaa')
                
            #scale bargraph based on selected gear
            if status['gear']==1:
                maxspeed=status['speed1']
            elif status['gear']==2:
                maxspeed=status['speed2']
            elif status['gear']==3:
                maxspeed=status['speed3']
            
            #print dashboard-like information
            if telemetryOn==True:
                print("Speed: {:0.3f} km/h {}, Odo: {:0.1f} km, Power: {:0.2f} W {}, Energy: {:0.3f} Wh, Bat: {} % ".format(status['speed'], bar(status['speed'],maxspeed,barSize),status['totalkm'], status['voltage']*status['amps'], bar(status['voltage']*status['amps'],maxWatts,barSize), status['energy']/3600, status['soc']))
            
            
    except Exception as e:
        print(e)
    finally:
        print("Exiting")
        await client.disconnect()
        window.close()

window = make_window()
asyncio.run(main(address))
