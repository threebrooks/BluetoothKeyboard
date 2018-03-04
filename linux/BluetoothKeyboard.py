#!/usr/bin/python

import uinput
import subprocess
import sys, inspect
import json
import subprocess
import time
from bluetooth import *

APP_VERSION = "1.0.0"

uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"

time.sleep(5)

def getAllKeys():
  out = []
  for name, obj in inspect.getmembers(uinput):
    if ((name.upper() == name) and (not name.startswith("_"))):
      out.append(obj)
  return out

device = uinput.Device(getAllKeys())

subprocess.call(['systemctl','restart','bluetooth'])

server_sock=BluetoothSocket( RFCOMM )
server_sock.bind(("",PORT_ANY))
server_sock.listen(1)

port = server_sock.getsockname()[1]

advertise_service( server_sock, "RetroPieController",
        service_id = uuid,
        service_classes = [ uuid, SERIAL_PORT_CLASS ],
        profiles = [ SERIAL_PORT_PROFILE ], 
        #                   protocols = [ OBEX_UUID ] 
        )

client_sock = None
client_info = None

xAccum = 0
yAccum = 0
lastXInt = 0
lastYInt = 0
while True:
    try:
        print("Making discoverable")
        ps = subprocess.Popen(('bluetoothctl'), stdin=subprocess.PIPE)
        ps.communicate('power on\npairable on\ndiscoverable on\nagent NoInputNoOutput\ndefault-agent\n\nexit\n')
        print("Waiting for connection")
        server_sock.settimeout(60)
        client_sock, client_info = server_sock.accept()
        print("Accepted connection from "+ str(client_info))

        client_sock.send(APP_VERSION)
    
        while True:
            data = client_sock.recv(1024)
            if len(data) == 0: continue
            for msgString in str(data).split("@@@"):
              if (msgString == ""): continue
              #print msgString
              js = json.loads(msgString)
              type = js['type']
              if (type == "KEY"):
                if (js['pressed'] == "true"):
                  press = 1
                else:
                  press = 0
                for keyStringEl in js['keylist'].split("|"):
                  if (keyStringEl == "HEARTBEAT"): continue
                  key = getattr(uinput, keyStringEl);
                  #print "Emitting "+keyStringEl
                  device.emit(key, press)
              elif (type == "MOUSE"):
                if (js['absrel'] == "REL"):
                  xAccum += js['dx'] 
                  yAccum += js['dy'] 
                  xError = xAccum-lastXInt
                  yError = yAccum-lastYInt
                  if (abs(xError) > 0.5 or abs(yError) > 0.5):
                    newX = int(round(xAccum))
                    newY = int(round(yAccum))
                    deltaX = newX-lastXInt
                    deltaY = newY-lastYInt
                    if (deltaX != 0 or deltaY != 0):
                      #print "Emitting mouse move "+str(deltaX)+","+str(deltaY)
                      device.emit(uinput.REL_X, newX-lastXInt, syn=False)
                      device.emit(uinput.REL_Y, newY-lastYInt)
                      lastXInt = newX
                      lastYInt = newY
                elif (js['absrel'] == "ABS"):
                  device.emit(uinput.ABS_X, int(js['x']), syn=False)
                  device.emit(uinput.ABS_Y, int(js['y']))

    except:
        print("Lost connection\n"+str(sys.exc_info()[0]))
        if (client_sock != None): client_sock.close()
        continue
    
server_sock.close()

