#!/usr/bin/python

import json
import socket
import logging
import binascii
import struct
import argparse
import threading
import math
import numpy as np
from time import sleep

class ServerMessageTypes(object):
	TEST = 0
	CREATETANK = 1
	DESPAWNTANK = 2
	FIRE = 3
	TOGGLEFORWARD = 4
	TOGGLEREVERSE = 5
	TOGGLELEFT = 6
	TOGGLERIGHT = 7
	TOGGLETURRETLEFT = 8
	TOGGLETURRETRIGHT = 9
	TURNTURRETTOHEADING = 10
	TURNTOHEADING = 11
	MOVEFORWARDDISTANCE = 12
	MOVEBACKWARSDISTANCE = 13
	STOPALL = 14
	STOPTURN = 15
	STOPMOVE = 16
	STOPTURRET = 17
	OBJECTUPDATE = 18
	HEALTHPICKUP = 19
	AMMOPICKUP = 20
	SNITCHPICKUP = 21
	DESTROYED = 22
	ENTEREDGOAL = 23
	KILL = 24
	SNITCHAPPEARED = 25
	GAMETIMEUPDATE = 26
	HITDETECTED = 27
	SUCCESSFULLHIT = 28
    
	strings = {
		TEST: "TEST",
		CREATETANK: "CREATETANK",
		DESPAWNTANK: "DESPAWNTANK",
		FIRE: "FIRE",
		TOGGLEFORWARD: "TOGGLEFORWARD",
		TOGGLEREVERSE: "TOGGLEREVERSE",
		TOGGLELEFT: "TOGGLELEFT",
		TOGGLERIGHT: "TOGGLERIGHT",
		TOGGLETURRETLEFT: "TOGGLETURRETLEFT",
		TOGGLETURRETRIGHT: "TOGGLETURRENTRIGHT",
		TURNTURRETTOHEADING: "TURNTURRETTOHEADING",
		TURNTOHEADING: "TURNTOHEADING",
		MOVEFORWARDDISTANCE: "MOVEFORWARDDISTANCE",
		MOVEBACKWARSDISTANCE: "MOVEBACKWARDSDISTANCE",
		STOPALL: "STOPALL",
		STOPTURN: "STOPTURN",
		STOPMOVE: "STOPMOVE",
		STOPTURRET: "STOPTURRET",
		OBJECTUPDATE: "OBJECTUPDATE",
		HEALTHPICKUP: "HEALTHPICKUP",
		AMMOPICKUP: "AMMOPICKUP",
		SNITCHPICKUP: "SNITCHPICKUP",
		DESTROYED: "DESTROYED",
		ENTEREDGOAL: "ENTEREDGOAL",
		KILL: "KILL",
		SNITCHAPPEARED: "SNITCHAPPEARED",
		GAMETIMEUPDATE: "GAMETIMEUPDATE",
		HITDETECTED: "HITDETECTED",
		SUCCESSFULLHIT: "SUCCESSFULLHIT"
	}
    
	def toString(self, id):
		if id in self.strings.keys():
			return self.strings[id]
		else:
			return "??UNKNOWN??"


class ServerComms(object):
	'''
	TCP comms handler
	
	Server protocol is simple:
	
	* 1st byte is the message type - see ServerMessageTypes
	* 2nd byte is the length in bytes of the payload (so max 255 byte payload)
	* 3rd byte onwards is the payload encoded in JSON
	'''
	ServerSocket = None
	MessageTypes = ServerMessageTypes()
	
	
	def __init__(self, hostname, port):
		self.ServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.ServerSocket.connect((hostname, port))

	def readTolength(self, length):
		messageData = self.ServerSocket.recv(length)
		while len(messageData) < length:
			buffData = self.ServerSocket.recv(length - len(messageData))
			if buffData:
				messageData += buffData
		return messageData

	def readMessage(self):
		'''
		Read a message from the server
		'''
		messageTypeRaw = self.ServerSocket.recv(1)
		messageLenRaw = self.ServerSocket.recv(1)
		messageType = struct.unpack('>B', messageTypeRaw)[0]
		messageLen = struct.unpack('>B', messageLenRaw)[0]
		
		if messageLen == 0:
			messageData = bytearray()
			messagePayload = {'messageType': messageType}
		else:
			messageData = self.readTolength(messageLen)
			logging.debug("*** {}".format(messageData))
			messagePayload = json.loads(messageData.decode('utf-8'))
			messagePayload['messageType'] = messageType
			
		logging.debug('Turned message {} into type {} payload {}'.format(
			binascii.hexlify(messageData),
			self.MessageTypes.toString(messageType),
			messagePayload))
		return messagePayload
		
	def sendMessage(self, messageType=None, messagePayload=None):
		'''
		Send a message to the server
		'''
		message = bytearray()
		
		if messageType is not None:
			message.append(messageType)
		else:
			message.append(0)
		
		if messagePayload is not None:
			messageString = json.dumps(messagePayload)
			message.append(len(messageString))
			message.extend(str.encode(messageString))
			    
		else:
			message.append(0)
		
		logging.debug('Turned message type {} payload {} into {}'.format(
			self.MessageTypes.toString(messageType),
			messagePayload,
			binascii.hexlify(message)))
		return self.ServerSocket.send(message)


# Parse command line args
parser = argparse.ArgumentParser()
parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
parser.add_argument('-H', '--hostname', default='127.0.0.1', help='Hostname to connect to')
parser.add_argument('-p', '--port', default=8052, type=int, help='Port to connect to')
parser.add_argument('-n', '--name', default='TeamDominos:TestingBot', help='Name of bot')
args = parser.parse_args()

# Set up console logging
if args.debug:
	logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.DEBUG)
else:
	logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.INFO)


# Connect to game server
GameServer = ServerComms(args.hostname, args.port)

# Spawn our tank
#logging.info("Creating tank with name '{}'".format(args.name))
#GameServer.sendMessage(ServerMessageTypes.CREATETANK, {'Name': args.name})

me = {}
enemy = {}
def getInfo():
    global me, enemy
    while True:
        message = GameServer.readMessage()
#        print(message)
        if(not args.name == message.get("Name")):
            enemy = message
			# logging.info("enemy appeared")
        else:
            me = message
    return me
            
info_message = {}
            
#def storeInfo():
#    while True:
#        message = GameServer.readMessage()
#        for key in message:
#            info_message[key] = message.get(key)

def spin():
	while True:
		GameServer.sendMessage(ServerMessageTypes.TOGGLETURRETRIGHT)

def vector_heading(x, y):
    x = -x
    vector = np.array([x,y])
    vector_dot = np.dot(vector,np.array([0,1]))
    vector_len = np.linalg.norm(vector)
    angle = np.arccos(vector_dot/vector_len) / math.pi * 180
    
    if x >= 0 and y >= 0:
        angle = 270 - angle
    elif x > 0 and y < 0:
        angle = 270 - angle
    elif x <= 0 and y < 0:
        angle = angle - 90
    else:
        angle = angle + 270
    return angle

class AllyTank:
    
    def __init__(self):
        global me
        self.name = args.name
        GameServer.sendMessage(ServerMessageTypes.CREATETANK, {'Name': args.name})
        logging.info("Creating tank with name '{}'".format(args.name))
        self.x = me.get("X")
        self.y = me.get("Y")
        self.ammo = me.get("Ammo")
        self.hp = me.get("Health")
        self.heading = me.get("Heading")
        self.turret_heading = me.get("TurretHeading")
        while self.x == None:
            self.update_vals()
        
    def update_vals(self):
        global me
        self.x = me.get("X")
        self.y = me.get("Y")
        self.ammo = me.get("Ammo")
        self.hp = me.get("Health")
        self.heading = me.get("Heading")
        self.turret_heading = me.get("TurretHeading")
    
    def go_to(self, x, y):
        vector_x = x - self.x
        vector_y = y - self.y
        heading = vector_heading(vector_x, vector_y)
        vector = np.array([vector_x, vector_y])
        GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': heading})
        distance = np.sqrt(np.dot(vector,vector))
        self.forward(distance)
        return
    
    def aim_at(self, x, y):
        vector_x = x - self.x
        vector_y = y - self.y
        heading = vector_heading(vector_x, vector_y)
        GameServer.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount': heading})
        return heading
    
    def shoot(self):
        GameServer.sendMessage(ServerMessageTypes.FIRE)
        return
    
    def shoot_at(self, x, y):
        self.aim_at(x,y)
        self.shoot
        return
        
    def head_to_goal(self):
        if self.y < 0:
            self.go_to(0,-102)
        else:
            self.go_to(0,102)
        return
    
    def forward(self, dist = None):
        if dist == None:
            GameServer.sendMessage(ServerMessageTypes.TOGGLEFORWARD)
        else:
            GameServer.sendMessage(ServerMessageTypes.MOVEFORWARDDISTANCE, {"Amount": dist})
        return
    
    def bee_line(self, times = 10):
        for i in range(times):
            heading = self.heading + np.sin(np.sqrt(self.x*self.x + self.y*self.y)*(math.pi/2))*3
            GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': heading})
        return
    
#    def nearest_health(self):
        


        
info_thread = threading.Thread(target=getInfo)
info_thread.start()
sleep(1)

tank1 = AllyTank()
update_thread = threading.Thread(target=tank1.update_vals)
tank1.head_to_goal()
sleep(10)
tank1.go_to(0,-tank1.y)