#!/usr/local/bin/python3
from threading import Thread, Lock
import json

from util import HTTP
import chatserv, api

class Chat(Thread):
	def __init__(self, room, key = None, server = None, port = None, session = None, transport = None):
		if room <= 0: raise Exception('Invalid room id') #TODO: ConnectionError
		Thread.__init__(self, name='chat-' + str(room))

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
		if self.key == None or self.server == None:
			#FIXME: this will always make the server chat2-2, which would make connecting to
			#halo or runescape impossible by room id. Not that you'd ever have to, but it would.
			#most domains are on chat2-2 though, so this should at least accidentally not break most wikis.
			data = api.spider('community')
			if 'exception' in data: raise Exception(data['exception']['message']) #wiki doesn't have chat, probably
			elif not isinstance(data['chatkey'], str): raise Exception('Chatkey is false')
			if self.key == None: self.key = data['chatkey']
			if self.server == None: self.server = data['nodeHostname']
			if self.port == None: self.port = data['nodePort']
		if self.port == None: self.port = 80 #it's not worth wasting time making an HTTP request when it's just going to be 80
		if self.session == None: self.session = api.session(self.id, self.key, self.server, self.port)
		if self.transport == None: self.transport = 'xhr-polling' #this will be important if websockets are ever allowed again
		try: _trans_receive[self.transport](self) #connect
		finally: #dead
			del chatserv.chats[self.id]
	def sendMessage(message):
		pass
	def sendCommand(command, args):
		pass

def __xhr_poll(sock):
	while(True):
		response = HTTP.get(
			'http://' + sock.server + ':' + sock.port + '/socket.io/1/xhr-polling/' + sock.session + '/',
			{
				'name': chatserv.user,
				'key': sock.key,
				'roomId': sock.id,
				'client': 'Chatserv',
				'version': chatserv.version
			},
			{'Cookie': chatserv.session}
		)
		if response.status == 200:
			data = response.read().decode('utf-8')
			if data[0] != '\ufffd': data = '\ufffd' + str(len(data)) + '\ufffd' + data
			data = data.split('\ufffd')
			i = 1 #data[0] is an empty string
			while i < len(data): #sorry, but range() is stupid. Ain't no one got time for that
				if int(data[i]) != len(data[i + 1]): raise Exception('Message length mismatch') #TODO: ProtocolError
				message = data[i + 1]

				#NOTE: we don't need this anymore, and 8:: causes a continue, so it's easier to increment here
				i += 2
				print(message)

				#no switch, so these are in frequency order
				if message[0] == '8': #noop
					continue
				elif message[0] == '4': #json
					json.loads(message[4:])
					#TODO: handle
				elif message[0] == '0': #disconnect
					raise Exception() #TODO: something nicer?
				elif message[0] == '1': #connect
					sock.connecting = False
					sock.connected = True
					sock.sendCommand('initquery')
				elif message[0] == '7': #error
					raise Exception(message[4:])
				else:
					raise Exception('Received unimplemented data type ' + message[0])

		elif response.status == 404: continue #this is what Torus does, I still don't know if it's good or bad
		else: raise Exception('Bad HTTP status ' + response.status)

def __xhr_send(sock, message):
	#TODO: thread this. Also, the response is worthless
	HTTP.post(
		'http://' + sock.server + ':' + sock.port + '/socket.io/1/xhr-polling/' + sock.session + '/?name=' + chatserv.user + '&key=' + sock.key + '&roomId=' + sock.id + '&client=Chatserv&version=' + chatserv.version,
		'5:::' + json.dumps({'name': 'message', 'args': [message]}),
		{'Cookie': chatserv.session}
	)

_trans_send = {'xhr-polling': __xhr_send}
_trans_receive = {'xhr-polling': __xhr_poll}
