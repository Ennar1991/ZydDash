import asyncio
import time
from bleak import BleakClient
import PySimpleGUI as sg

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

maxWatts=500
barSize=20

#Notify Callback
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
            if(status['timestamp']!=0):
                status['energy']+=status['voltage']*status['amps']*(time.time()-status['timestamp'])
            status['timestamp']=time.time() #this packet has the V/A info, needed for Wh calculation

        elif(data[1]==1):
            status['speed1']=data[4]
            status['speed2']=data[5]
            status['speed3']=data[6]
            
    else:
        if(data[0]==1): #controller "UF" packet
            pass    #nothing implemented yet

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
            [sg.Text('Total distance',s=(labelXsize,1)), sg.Text(k='-TOTALTEXT-', s=(textXsize,1))]
             ]
    window = sg.Window('ePF-1 GUI', layout, finalize=True, keep_on_top=True)
    return window

#main loop, must be created as asyncio thread
async def main(address):
    client = BleakClient(address)
    try:
        print("Connecting")
        await client.connect()
        await client.start_notify(READ_UUID, callback)
        print("Connected.")
        maxspeed=22

        while True:
            event, values = window.read(timeout=100)
            #time.sleep(0.1)
            if event == sg.WIN_CLOSED or event == 'Exit':
                break
            
            
            window['-SPEEDBAR-'].update(status['speed'])
            window['-SPEEDTEXT-'].update('{:0.3f} km/h'.format(status['speed']))
            
            window['-POWERBAR-'].update(status['voltage']*status['amps'])
            window['-POWERTEXT-'].update('{:0.2f} W'.format(status['voltage']*status['amps']))
            
            window['-BATBAR-'].update(status['soc'])
            window['-BATTEXT-'].update('{} %'.format(status['soc']))
            
            window['-GEARTEXT-'].update('{}'.format(status['gear']))
            window['-TRIPTEXT-'].update('{:0.1f} km'.format(status['tripkm']))
            window['-TOTALTEXT-'].update('{:0.1f} km'.format(status['totalkm']))
            
            
            
            if(time.time()-status['timestamp'])>0.2:
                send_data = await client.write_gatt_char(SEND_UUID, b'\xaa')
                
            #scale bargraph based on selected gear
            if status['gear']==1:
                maxspeed=status['speed1']
            elif status['gear']==2:
                maxspeed=status['speed2']
            elif status['gear']==3:
                maxspeed=status['speed3']
            
            #print dashboard-like information
            print("Speed: {:0.3f} km/h {}, Odo: {:0.1f} km, Power: {:0.2f} W {}, Energy: {:0.3f} Wh, Bat: {} % ".format(status['speed'], bar(status['speed'],maxspeed,barSize),status['totalkm'], status['voltage']*status['amps'], bar(status['voltage']*status['amps'],maxWatts,barSize), status['energy']/3600, status['soc']), end='\r')
            
            
    except Exception as e:
        print(e)
    finally:
        print("Exiting")
        await client.disconnect()
        window.close()

window = make_window()
asyncio.run(main(address))
