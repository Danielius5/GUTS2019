#!/usr/bin/python

import json
import socket
import logging
import binascii
import struct
import argparse
import random
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
parser.add_argument('-n', '--name', default='TeamA:TestingBot', help='Name of bot')
args = parser.parse_args()

# Set up console logging
if args.debug:
	logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.DEBUG)
else:
	logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.INFO)


# Connect to game server
GameServer = ServerComms(args.hostname, args.port)

# Spawn our tank
logging.info("Creating tank with name '{}'".format(args.name))
GameServer.sendMessage(ServerMessageTypes.CREATETANK, {'Name': args.name})

me = {}
enemy = {}
def getInfo():
	global me, enemy
	while True:
		message = GameServer.readMessage()
		if(not args.name == message.get("Name")):
			enemy = message
			# logging.info("enemy appeared")
		else:
			me = message

def spin():
	while True:
		GameServer.sendMessage(ServerMessageTypes.TOGGLETURRETRIGHT)
x = threading.Thread(target=getInfo)
x.start()
#y = threading.Thread(target=spin)
#y.start()
sleep(1)

shot = False
while True:
    if(enemy.get("Name") and shot == False):
        x_e = enemy.get("X")
        x_m = me.get("X")
        
        y_e = enemy.get("Y")
        y_m = me.get("Y")
        
        x = x_e - x_m
        y = y_e - y_m
        
        
#        tankEnemyAngle_pos_x = math.atan2((y_m - y_e), (x_m - x_e)) / math.pi * 180
        tankEnemyVector = np.array([x, y])
        
#        tankEnemyVector_len = np.dot(tankEnemyVector,tankEnemyVector)
        tankEnemyAngle = np.arccos(np.dot(tankEnemyVector, np.array([-1,0])/np.linalg.norm(tankEnemyVector))) / math.pi * 180
        
        if x >= 0 and y >= 0: # 2nd quadrant
            tankEnemyAngle = 450 - tankEnemyAngle
            print("2nd quadrant", tankEnemyAngle)
        elif x > 0 and y < 0: #3rd quadrant
            tankEnemyAngle = 90 + tankEnemyAngle
            print("3rd quadrant", tankEnemyAngle)
        elif x <= 0 and y < 0: #4th quadrant
            tankEnemyAngle = 90 + tankEnemyAngle
            print("4th quadrant", tankEnemyAngle)
        else: #1st quadrant
            tankEnemyAngle = 90 - tankEnemyAngle
            print("1st quadrant", tankEnemyAngle)
        
#        tankEnemyAngle = tankEnemyAngle_pos_x - 90
        tankEnemyAngle = 45+180
        
        logging.info(tankEnemyAngle)

        GameServer.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount': tankEnemyAngle})
        sleep(5)
        GameServer.sendMessage(ServerMessageTypes.FIRE)
        shot = True