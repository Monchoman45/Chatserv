#!/usr/local/bin/python3
from threading import Thread, Event
import json

from util import HTTP
import chatserv
import coms.io as io

chats = {}

class Chat(Thread):
	def __init__(self, room, key = None, server = None, port = None, session = None, transport = None):
		global chats
		if isinstance(room, int):
			if room <= 0:
				raise Exception('Invalid room id') #TODO: ConnectionError
				self.id = room
				self.domain = None
		else: #assume domain name
			self.id = None
			self.domain = room
		Thread.__init__(self, name='chat-' + str(room), daemon=True)
		self.key = key
		self.server = server
		self.port = port
		self.session = session
		self.transport = transport

		self.connected = Event()
		self.userlist = {}

		if self.id != None: chats[self.id] = self
		self.start()
	def run(self):
		global chats
		if self.id == None or self.key == None:
			if self.domain: data = io.spider(self.domain)
			else: data = io.spider('community')
			if 'exception' in data: raise Exception(data['exception']['message'])
			elif not isinstance(data['chatkey'], str): raise Exception('Chatkey is false')

			if self.id == None:
				self.id = data['roomId']
				chats[self.id] = self
			if self.key == None: self.key = data['chatkey']
			if self.server == None: self.server = data['nodeHostname']
			if self.port == None: self.port = data['nodePort']

		#FIXME: This forces chat2-2 if you don't specify a server yourself, which would make connecting to
		#halo or runescape impossible by room id. Not that you'd ever have to, but it would.
		#Most domains are on chat2-2 though, so this should at least accidentally not break most wikis.
		if self.server == None: self.server = 'chat2-2.wikia.com'
		if self.port == None: self.port = 80 #it's not worth wasting time making an HTTP request when it's just going to be 80
		if self.session == None: self.session = io.session(self.id, self.key, self.server, self.port)
		if self.transport == None: self.transport = 'xhr-polling' #this will be important if websockets are ever allowed again
		try: io.transports[self.transport].connect(self) #connect
		finally: #dead
			del chats[self.id]
	def sendMessage(self, message):
		self.connected.wait()
		message = {'attrs': {'msgType': 'chat', 'text': message}}
		io.transports[self.transport].send(self, json.dumps(message))
	def sendCommand(self, command, args = {}):
		self.connected.wait()
		command = {'attrs': {'msgType': 'command', 'command': command}}
		for i in args: command['attrs'][i] = args[i]
		io.transports[self.transport].send(self, json.dumps(command))

