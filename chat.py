#!/usr/local/bin/python3
from threading import Thread, Lock, Event
import json

from util import HTTP
import chatserv
import coms.io as io

class Chat(Thread):
	def __init__(self, room, key = None, server = None, port = None, session = None, transport = None):
		if room <= 0: raise Exception('Invalid room id') #TODO: ConnectionError
		Thread.__init__(self, name='chat-' + str(room))
		self.daemon = True

		self.id = room
		self.key = key
		self.server = server
		self.port = port
		self.session = session
		self.transport = transport

		self.connected = False
		self.connecting = True
		self.reconnecting = False
		self.userlist = {}

		chatserv.chats[self.id] = self
		self.start()
	def run(self):
		if self.key == None:
			data = io.spider('community')
			if 'exception' in data: raise Exception(data['exception']['message']) #wiki doesn't have chat, probably
			elif not isinstance(data['chatkey'], str): raise Exception('Chatkey is false')
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
			del chatserv.chats[self.id]
	def sendMessage(message):
		pass
	def sendCommand(command, args):
		pass
