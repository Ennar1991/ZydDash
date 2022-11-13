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

regs=8192
memorymap=[0]*regs #16-bit registers

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
        print("UF '{}'".format(data))
        if(data[0]==1): #controller "UF" packet
            if(data[1]==3 or data [1]==23): # Read address function code or combined write/read
                startAddress=(data[2]*256)+data[3]
                dataLength=int(data[4]/2)
                for i in range(0,dataLength):
                    memorymap[startAddress+i]=data[5+(2*i)]*256+data[6+(2*i)]

def busRead(targetAddr,startReadAddr,numReadRegs,numDatabytesMethod=True):
    #Function Code 0x03
    writeString=targetAddr.to_bytes(1, byteorder='big')
    writeString+=b'\x03'
    writeString+=startReadAddr.to_bytes(2, byteorder='big')
    writeString+=numReadRegs.to_bytes(2, byteorder='big')
    writeString+=libscrc.modbus(writeString).to_bytes(2, byteorder='little')
    print("W {}".format(writeString))
    return writeString
    

def busWriteAndRead(targetAddr,startReadAddr,numReadRegs,StartWriteAddr,numWriteRegs,data:bytearray,numDatabytesMethod=True): #numDatabytesMethod False=wrong implementation for Display, True=right implementation for Controller
    #Function Code 0x17
    writeString=targetAddr.to_bytes(1, byteorder='big')
    writeString+=b'\x17'
    writeString+=startReadAddr.to_bytes(2, byteorder='big')
    writeString+=numReadRegs.to_bytes(2, byteorder='big')
    writeString+=StartWriteAddr.to_bytes(2, byteorder='big')
    writeString+=numWriteRegs.to_bytes(2, byteorder='big')
    
    if numDatabytesMethod==True:
        #correct implementation of MODBUS bytes count
        #returns the number of now following databytes, disregarding head and CRC
               
        if(len(data) % 2 == 1): #pad data
            print("Pad")
            data+=b'\x00'
        
        if int(len(data)/2) != numWriteRegs:
            Exception('invalid number of writeRegs/data length')
        
    writeString+=len(data).to_bytes(1,byteorder='big')
    writeString+=data
    writeString+=libscrc.modbus(writeString).to_bytes(2, byteorder='little')
    print(writeString)
    return writeString
    
    

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
    spinXSize=10
    layout=[[sg.Text('Speed',s=(labelXsize,1)), sg.ProgressBar(22, orientation='h', s=(barXsize,20), k='-SPEEDBAR-'),sg.Text(k='-SPEEDTEXT-', s=(textXsize,1))],
            [sg.Text('Input Power',s=(labelXsize,1)), sg.ProgressBar(maxWatts, orientation='h', s=(barXsize,20), k='-POWERBAR-'),sg.Text(k='-POWERTEXT-', s=(textXsize,1))],
            [sg.Text('Battery SOC',s=(labelXsize,1)), sg.ProgressBar(100, orientation='h', s=(barXsize,20), k='-BATBAR-'),sg.Text(k='-BATTEXT-', s=(textXsize,1))],
            [sg.Text('Selected Gear',s=(labelXsize,1)),sg.Text(k='-GEARTEXT-', s=(textXsize,1))],
            [sg.Text('Trip distance',s=(labelXsize,1)), sg.Text(k='-TRIPTEXT-', s=(textXsize,1))],
            [sg.Text('Total distance',s=(labelXsize,1)), sg.Text(k='-TOTALTEXT-', s=(textXsize,1))],
            [sg.Text('Energy',s=(labelXsize,1)), sg.Text(k='-WATTHOURSTEXT-', s=(textXsize,1))],
            [sg.Text('Temperature',s=(labelXsize,1)), sg.Text(k='-TEMPTEXT-', s=(textXsize,1))],
            [sg.Button('Reset Trip', k='-RESETTRIP-'), sg.Button('UF mode ON', k='-UFON-'), sg.Button('UF mode OFF', k='-UFOFF-')],
            [sg.Text('The following tools work in UF mode only. Direct memory edits can and will easily break things. You have been warned.')],
            [sg.Button('Dump memory', k='-READMEMORY2-'),sg.Spin('Registers', initial_value=256, k='-REGISTERS-', s=(10,1)), sg.Button('Scan Bus')],
            [sg.Button("Write Accel"), sg.Spin('0', s=(spinXSize,1),initial_value=30000,k='-ACCEL-'),
             sg.Button("Write Brake"), sg.Spin('0', s=(spinXSize,1),initial_value=30000,k='-BRAKE-'),
             sg.Button("Write Speed"), sg.Spin('0',s=(spinXSize,1),initial_value=220,k='-SPEED-'),
             sg.Button('Read Mem', k='-READMEMORY-'),sg.Button('Write Mem'), sg.Input('0000', s=(spinXSize,1),k='-ADDR-'), sg.Input('0000', s=(spinXSize,1),k='-VALUE-')],
            [sg.Button('Read Model Name',k='-READMODEL-'), sg. Button('Write Model Name', k='-WRITEMODEL-'), sg.Input('Hacked by Ennar ',k='-MODELNAME-')],
            [sg.Button('Read Hardware Version',k='-READHARDWARE-'), sg. Button('Write Hardware Version', k='-WRITEHARDWARE-'), sg.Input('',k='-HARDWARE-')],
            [sg.Button('Read Bootl Version',k='-READBOOTLOADER-'), sg. Button('Write Bootl Version', k='-WRITEBOOTLOADER-'), sg.Input('',k='-BOOTLOADER-')],
            [sg.Button('Read Firmware Version',k='-READFIRMWARE-'), sg. Button('Write Model Name', k='-WRITEFIRMWARE-'), sg.Input('',k='-FIRMWARE-')],
            [sg.Button('Read Controller Code',k='-READCODE-'), sg. Button('Write Model Name', k='-WRITECODE-'), sg.Input('',k='-CODE-')],
            [sg.Table([[0],[10],[20],[30],[40],[50],[60],[70],[80],[90]], ['Addr','0000','0001','0002','0003','0004','0005','0006','0007','0008','0009','000a','000b','000c','000d','000e','000f'], num_rows=32, k='-MEMORYMAP-')]
            ]
    window = sg.Window('ePF-1 GUI by Ennar', layout, finalize=True, keep_on_top=True)
    return window

def saveDump():
    f=open('memDump.bin','wb')
    for i in memorymap:
        f.write(i.to_bytes(2, byteorder='big'))
    f.close()
    

def tableMap(datatable):
    memMap= [ [0]*17 for i in range(int(regs/16))]
    for row in range(0,int(regs/16)):
        memMap[row][0]='{:02x}'.format(row*16)
        for col in range(0,16):
            memMap[row][1+col]='{:04x}'.format(datatable[(row*16)+col])

    return memMap            

#main loop, must be created as asyncio thread
async def main(address):
    #public regs
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
            event, values = window.read(timeout=30)
            #time.sleep(0.1)
            #print(values)
            regs=int(values['-REGISTERS-'])
            
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
                print('Read Addr. {}'.format(int(values['-ADDR-'],base=16))) 
                send_data = await client.write_gatt_char(SEND_UUID, busRead(1, int(values['-ADDR-'],base=16),1))
                #read_data= await client.read_gatt_char(READ_UUID)
                window['-MEMORYMAP-'].update(tableMap(memorymap))
            
            if event == '-READMEMORY2-':
                #send_data = await client.write_gatt_char(SEND_UUID, b'\xa5\x00\xff\x00\x00\x00\x00\x5a')
                #telemetryOn=False
                #memorymap=[0]*regs
                for i in range (0,int(regs/16)):
                    mydata=b'\x01\x03'+(i*16).to_bytes(2, byteorder='big')+b'\x00\x10'
                    
                    mycrc=libscrc.modbus(mydata).to_bytes(2, byteorder='little')
                    print(mydata+mycrc)
                    send_data = await client.write_gatt_char(SEND_UUID, mydata+mycrc)
                    time.sleep(0.1)
                window['-MEMORYMAP-'].update(tableMap(memorymap))
                saveDump()
            
            if event == 'Write Accel':
                send_data = await client.write_gatt_char(SEND_UUID, busWriteAndRead(1,9,1,9,1,int(values['-ACCEL-']).to_bytes(2, byteorder='big')))
                time.sleep(0.2)
                window['-MEMORYMAP-'].update(tableMap(memorymap))
            
            if event == 'Write Brake':
                send_data = await client.write_gatt_char(SEND_UUID, busWriteAndRead(1,10,1,10,1,int(values['-BRAKE-']).to_bytes(2, byteorder='big')))
                time.sleep(0.2)
                window['-MEMORYMAP-'].update(tableMap(memorymap))
            
            if event == 'Write Speed':
                send_data = await client.write_gatt_char(SEND_UUID, busWriteAndRead(1,32,1,32,1,int(values['-SPEED-']).to_bytes(2, byteorder='big')))
                time.sleep(0.2)
                window['-MEMORYMAP-'].update(tableMap(memorymap))
            
            if event == 'Write Mem':
                send_data = await client.write_gatt_char(SEND_UUID, busWriteAndRead(1,int(values['-ADDR-'],base=16),1,int(values['-ADDR-'],base=16),1,int(values['-VALUE-'],base=16).to_bytes(2, byteorder='big')))
                time.sleep(0.2)
                window['-MEMORYMAP-'].update(tableMap(memorymap))
            
            if event =='Scan Bus':
                for i in range(0,256):
                    print(i,end=': ')
                    send_data = await client.write_gatt_char(SEND_UUID, busRead(i,0,1))
                    time.sleep(0.1)
            
            if event == sg.WIN_CLOSED or event == 'Exit':
                break
            
            if event=='-READMODEL-':
                hwaddress=278 #228 for Hiboy S2/365pro, 278 for ePF-1
                send_data = await client.write_gatt_char(SEND_UUID, busRead(1, hwaddress,8))
                time.sleep(0.1)
                window['-MEMORYMAP-'].update(tableMap(memorymap))
                modelname=memorymap[hwaddress:hwaddress+8]
                model=b''
                for i in modelname:
                    model+=i.to_bytes(2,'little')
                
                window['-MODELNAME-'].update(model.decode("iso8859-1"))
            
            if event=='-WRITEMODEL-':
                hwaddress=278 #228 for Hiboy S2/365pro, 278 for ePF-1
                modelname=b''
                model=values['-MODELNAME-'].encode().ljust(16,b' ')[:16]
                for i in range(0,len(model),2):
                    modelname+=model[i+1].to_bytes(1,'big')
                    modelname+=model[i].to_bytes(1,'big')
                    
                send_data = await client.write_gatt_char(SEND_UUID, busWriteAndRead(1,hwaddress,8,hwaddress,8,modelname))
                time.sleep(0.1)
                window['-MEMORYMAP-'].update(tableMap(memorymap))
           
            
            if event=='-READHARDWARE-':
                hwaddress=286 #236 for Hiboy S2/365pro, 286 for ePF-1
                send_data = await client.write_gatt_char(SEND_UUID, busRead(1,hwaddress,8))
                time.sleep(0.1)
                window['-MEMORYMAP-'].update(tableMap(memorymap))
                modelname=memorymap[hwaddress:hwaddress+8]
                model=b''
                for i in modelname:
                    model+=i.to_bytes(2,'little')
                
                window['-HARDWARE-'].update(model.decode("iso8859-1"))
            
            if event=='-WRITEHARDWARE-':
                hwaddress=286 #236 for Hiboy S2/365pro, 286 for ePF-1
                modelname=b''
                model=values['-HARDWARE-'].encode().ljust(16,b' ')[:16]
                for i in range(0,len(model),2):
                    modelname+=model[i+1].to_bytes(1,'big')
                    modelname+=model[i].to_bytes(1,'big')
                    
                send_data = await client.write_gatt_char(SEND_UUID, busWriteAndRead(1,hwaddress,8,hwaddress,8,modelname))
                time.sleep(0.1)
                window['-MEMORYMAP-'].update(tableMap(memorymap))
           
            
            
            
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
            
            if telemetryOn==True and (time.time()-status['timestamp'])>0.1:
                send_data = await client.write_gatt_char(SEND_UUID, b'\xaa')
                
            #scale bargraph based on selected gear
            if status['gear']==1:
                maxspeed=status['speed1']
            elif status['gear']==2:
                maxspeed=status['speed2']
            elif status['gear']==3:
                maxspeed=status['speed3']
            
            #print dashboard-like information
            #if telemetryOn==True:
            #    print("Speed: {:0.3f} km/h {}, Odo: {:0.1f} km, Power: {:0.2f} W {}, Energy: {:0.3f} Wh, Bat: {} % ".format(status['speed'], bar(status['speed'],maxspeed,barSize),status['totalkm'], status['voltage']*status['amps'], bar(status['voltage']*status['amps'],maxWatts,barSize), status['energy']/3600, status['soc']))
            
            
    except Exception as e:
        print(e)
    finally:
        print("Exiting")
        await client.disconnect()
        window.close()

window = make_window()
asyncio.run(main(address))
