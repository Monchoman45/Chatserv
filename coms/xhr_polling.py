#!/usr/local/bin/python3
import json

from util import HTTP
import chatserv
import coms.io

def connect(sock):
	while True:
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
			print('---------------------------------------')
			data = response.read().decode('utf-8')
			if data[0] != '\ufffd': data = '\ufffd' + str(len(data)) + '\ufffd' + data
			data = data.split('\ufffd')
			i = 1 #data[0] is an empty string
			while i < len(data): #sorry, but range() is stupid. Ain't no one got time for that
				if int(data[i]) != len(data[i + 1]): raise Exception('Message length mismatch') #TODO: ProtocolError
				message = data[i + 1]

				#we don't need this anymore, and 8:: causes a continue, so it's easier to increment here
				i += 2
				print(message)

				#no switch, so these are in frequency order
				if message[0] == '8': #noop
					continue
				elif message[0] == '4': #json
					chatserv.stack.put(chatserv.StackEvent(coms.io.receive, (sock.id, json.loads(message[4:])), {}))
				elif message[0] == '0': #disconnect
					raise Exception() #TODO: something nicer?
				elif message[0] == '1': #connect
					if sock.connected: continue #why it sometimes spams 1:: is beyond me
					sock.connecting = False
					sock.connected = True
					sock.sendCommand('initquery')
				elif message[0] == '7': #error
					raise Exception(message[4:])
				else:
					raise Exception('Received unimplemented data type ' + message[0])

		elif response.status == 404: continue #this is what Torus does, I still don't know if it's good or bad
		else: raise Exception('Bad HTTP status ' + response.status)

def send(sock, message):
	#TODO: the response is worthless
	HTTP.post(
		'http://' + sock.server + ':' + sock.port + '/socket.io/1/xhr-polling/' + sock.session + '/?name=' + chatserv.user + '&key=' + sock.key + '&roomId=' + sock.id + '&client=Chatserv&version=' + chatserv.version,
		'5:::' + json.dumps({'name': 'message', 'args': [message]}),
		{'Cookie': chatserv.session}
	)
