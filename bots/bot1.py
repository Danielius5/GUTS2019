# -*- coding: utf-8 -*-
"""
Created on Sun Oct 20 10:49:52 2019

@author: Zoltan
"""

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
from time import sleep, time

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
            

def spin():
	while True:
		GameServer.sendMessage(ServerMessageTypes.TOGGLETURRETRIGHT)

def vector_heading(x, y):
    #MAJORLY overcomplicated due to messing up the axes, but it works.
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
    
    def __init__(self, name):
        global me
        self.name = name
        GameServer.sendMessage(ServerMessageTypes.CREATETANK, {'Name': name})
        logging.info("Creating tank with name '{}'".format(name))
        self.id = 0
        self.x = 0
        self.y = 0
        self.ammo = 10
        self.hp = 3
        self.heading = 0
        self.turret_heading = 0
        
    def update_vals(self, message):
        self.id = message.get("Id")
        self.x = message.get("X")
        self.y = message.get("Y")
        self.ammo = message.get("Ammo")
        self.hp = message.get("Health")
        self.heading = message.get("Heading")
        self.turret_heading = message.get("TurretHeading")
    
    def go_to(self, x, y):
        vector_x = x - self.x
        vector_y = y - self.y
        heading = vector_heading(vector_x, vector_y)
        vector = np.array([vector_x, vector_y])
        GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': heading})
        distance = np.sqrt(np.dot(vector,vector))
        self.forward(distance)
        return
    
    def toggle_forward(self):
        GameServer.sendMessage(ServerMessageTypes.TOGGLEFORWARD)
        return
    
    def turn_towards(self, x, y):
        vector_x = x - self.x
        vector_y = y - self.y
        heading = vector_heading(vector_x, vector_y)
        GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': heading})
        sleep(np.abs(self.heading - heading) / 200)
        return
    
    def turn_perpendicular(self, x, y):
        vector_x = x - self.x
        vector_y = y - self.y
        heading = vector_heading(vector_x, vector_y)
        if heading <= 270:
            GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': heading+90})
        else:
            GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': heading-90})
        return
        
    def aim_at(self, x, y):
        vector_x = x - self.x
        vector_y = y - self.y
        heading = vector_heading(vector_x, vector_y)
        GameServer.sendMessage(ServerMessageTypes.TURNTURRETTOHEADING, {'Amount': heading})
        sleep(np.abs(self.heading - heading)/180)
        return heading
    
    def shoot(self):
        GameServer.sendMessage(ServerMessageTypes.FIRE)
        return
    
    def shoot_at(self, x, y):
        self.stop_all()
        sleep(0.1)
        self.aim_at(x,y)
        self.shoot()
        return
        
    def head_to_goal(self):
        if self.y < 0:
            self.stop_all()
            self.turn_towards(0,-102)
            self.toggle_forward()
            while last_message["messageType"] != 23:
                continue
            self.stop_all()
        else:
            self.turn_towards(0,102)
            self.toggle_forward()
            while last_message["messageType"] != 23:
                continue
            self.stop_all()
        self.turn_towards(0,0)
        sleep(1)
        return
    
    def forward(self, dist = None):
        if dist == None:
            GameServer.sendMessage(ServerMessageTypes.TOGGLEFORWARD)
        else:
            GameServer.sendMessage(ServerMessageTypes.MOVEFORWARDDISTANCE, {"Amount": dist})
        return
    
    def reverse(self, dist = None):
        if dist == None:
            GameServer.sendMessage(ServerMessageTypes.TOGGLEREVERSE)
        else:
            GameServer.sendMessage(ServerMessageTypes.MOVEBACKWARSDISTANCE, {"Amount": dist})
        return
    
    def stop_all(self):
        GameServer.sendMessage(ServerMessageTypes.STOPALL)
        return
    
    def stop_move(self):
        GameServer.sendMessage(ServerMessageTypes.STOPMOVE)
        return
    
    def stop_turn(self):
        GameServer.sendMessage(ServerMessageTypes.STOPTURN)
        return
     
    def stop_turret(self):
        GameServer.sendMessage(ServerMessageTypes.STOPTURRET)
        return
    
    def bee_line(self, times = 10):
        #Engage in evasive maneouvres
        #AKA: Wiggle
        for i in range(times):
            heading = self.heading + i*(math.pi/2)*10
            GameServer.sendMessage(ServerMessageTypes.TURNTOHEADING, {'Amount': heading})
            sleep(0.5)
        return
    
    def nearest_enemy(self):
        distances = {}
        for enemy in enemy_info:
            enemy_x = enemy_info[enemy].get("X")
            enemy_y = enemy_info[enemy].get("Y")
            distance = np.sqrt(enemy_x**2 + enemy_y**2)
            distances[enemy] = distance
        dist_values = list(distances.values())
        min_dist = min(dist_values)
        ind = dist_values.index(min_dist)
        return list(distances.keys())[ind]
    
    def check_wall(self):
        self.stop_all()
        if np.abs(self.x) > 60:
            self.go_to(0, self.y)
            sleep(1)
        if np.abs(self.y) > 85:
            self.go_to(self.x, 0)
            sleep(1)
        return
    
    def engage_combat(self):
        self.stop_all
        enemy = self.nearest_enemy()
        while enemy_info[enemy].get("Health") > 0:
            enemy_x = enemy_info[enemy].get("X")
            enemy_y = enemy_info[enemy].get("Y")
            self.shoot_at(enemy_x, enemy_y)
            sleep(1)
            self.turn_perpendicular(enemy_x, enemy_y)
            t0 = time()
            counter = 0
            while time() - t0 < 2.5:
                if counter % 2 == 0:
                    self.forward(15)
                else:
                    self.reverse(15)
                counter = counter + 1
                sleep(0.2)
            self.stop_all()
            self.check_wall()
        self.head_to_goal()
        return
    
    def search_and_destroy(self):
        try:
            self.nearest_enemy()
        except:
            enemy_found = False
            GameServer.sendMessage(ServerMessageTypes.TOGGLETURRETLEFT)
            while not enemy_found:
                try:
                    self.nearest_enemy()
                except:
                    if self.y < 25 and self.heading < 180:
                        self.go_to(0, 50)
                    else:
                        self.go_to(0, -50)
                    sleep(1)
                    self.check_wall()
                    continue
                self.stop_turret()
                enemy_found = True
        self.engage_combat()
        return
    
    def shoot_at_nearest(self):
        try:
            self.nearest_enemy()
        except:
            enemy_found = False
            GameServer.sendMessage(ServerMessageTypes.TOGGLETURRETLEFT)
            while not enemy_found:
                try:
                    self.nearest_enemy()
                except:
                    continue
                self.stop_turret()
                enemy_found = True
        enemy = self.nearest_enemy()
        while enemy_info[enemy].get("Health") > 0:
            enemy_x = enemy_info[enemy].get("X")
            enemy_y = enemy_info[enemy].get("Y")
            self.shoot_at(enemy_x, enemy_y)  
        return
    
    def main_loop(self):
        while last_message.get("messageType") != 25:
            self.search_and_destroy() #find and kill an enemy
        while True:
            self.go_to(0,0)
            sleep(2)
            self.shoot_at_nearest()
            snitch_message = last_message
            if snitch_message.get("messageType") == 21:
                if snitch_message.get("Id") in list(ally_info.values):
                    carrier_id = snitch_message.get("Id")
                    if carrier_id == self.id:
                        self.head_to_goal()
                        sleep(5)
                    else:
                        for name in list(ally_info.keys()):
                            if ally_info.get(name).get("Id") == carrier_id:
                                ally_x = ally_info.get(name).get("X")
                                ally_y = ally_info.get(name).get("Y")
                                dist_to_ally = np.sqrt((ally_x - self.x)**2 + (ally_y - self.y)**2)
                                while dist_to_ally > 20:
                                    self.go_to(ally_x,ally_y)
                                    sleep(1)
                                    ally_x = ally_info.get(name).get("X")
                                    ally_y = ally_info.get(name).get("Y")
                                    dist_to_ally = np.sqrt((ally_x - self.x)**2 + (ally_y - self.y)**2)
                                self.shoot_at_nearest()
                    
            

# Parse command line args
parser = argparse.ArgumentParser()
parser.add_argument('-d', '--debug', action='store_true', help='Enable debug output')
parser.add_argument('-H', '--hostname', default='127.0.0.1', help='Hostname to connect to')
parser.add_argument('-p', '--port', default=8052, type=int, help='Port to connect to')
parser.add_argument('-n', '--name', default='TeamDominos:Bot1', help='Name of bot')
args = parser.parse_args()

# Set up console logging
if args.debug:
	logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.DEBUG)
else:
	logging.basicConfig(format='[%(asctime)s] %(message)s', level=logging.INFO)


# Connect to game server
GameServer = ServerComms(args.hostname, args.port)

last_message = {}
ally_info = {}
enemy_info = {}
pickup_info = {}

ally_info_prev = {}
enemy_info_prev = {}
pickup_info_prev = {}

def getInfo():
    global last_message
    global ally_info, enemy_info, pickup_info
    global ally_info_prev, enemy_info_prev, pickup_info_prev
    while True:
        message = GameServer.readMessage()
        last_message = message
        obj_name = message.get("Name")
        obj_type = message.get("Type")
        if obj_name == args.name:
            tank1.update_vals(message)
        elif obj_type == "Tank":
            if obj_name.startswith("TeamDominos"):
                try:
                    ally_info[obj_name]
                except:
                    ally_info[obj_name] = message
                    continue
                ally_info_prev[obj_name] = ally_info[obj_name].copy() #Dict, can copy
                ally_info[obj_name] = message
            else:
                try:
                    enemy_info[obj_name]
                except:
                    enemy_info[obj_name] = message
                    continue
                enemy_info_prev[obj_name] = enemy_info[obj_name].copy() #Dict, must copy
                enemy_info[obj_name] = message
        else:
            pickup_info = message
    return

tank1 = AllyTank(args.name)        
info_thread = threading.Thread(target=getInfo)
info_thread.start()
sleep(1)

tank1.main_loop()