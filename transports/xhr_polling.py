#!/usr/local/bin/python3
import sys, json

from util import HTTP
import chatserv

#chatserv.io.transports['xhr-polling']: sys.modules[__name__]]

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
			{'Cookie': chatserv.session},
			timeout=30
		)
		if sock._Chat__killed.isSet(): break
		if response.status == 200:
			print('---------------------------------------')
			data = response.read().decode('utf-8')
			#noop is the single most common event (by far) and by definition cannot be sent with another message.
			#skipping out on the string functions and loop overhead most of the time should help supress context
			#switching overhead and GIL overhead as well
			if data == '8::': continue

			if data[0] != '\ufffd': data = '\ufffd' + str(len(data)) + '\ufffd' + data
			data = data.split('\ufffd')
			i = 1 #data[0] is an empty string
			while i < len(data): #sorry, but range() is stupid. Ain't no one got time for that
				if int(data[i]) != len(data[i + 1]): raise Exception('Message length mismatch') #TODO: ProtocolError
				message = data[i + 1]
				print(message)

				#we don't need this anymore, and 8:: causes a continue, so it's easier to increment here
				i += 2

				#no switch, so these are in frequency order
				if message[0] == '4': #json
					event = json.loads(message[4:])
					chatserv.stack.put(chatserv.StackContext(chatserv.io.receive, sock, event))
					if event['event'] == 'disableReconnect':
						sock.connected.clear()
						return
					elif event['event'] == 'forceReconnect': pass #re auth and such
				elif message[0] == '8': #noop - just in case
					continue
				elif message[0] == '0': #disconnect
					sock.connected.clear()
					return
				elif message[0] == '1': #connect
					if sock.connected.is_set(): continue #why it sometimes spams 1:: is beyond me
					sock.connected.set()
					sock.sendCommand('initquery')
				elif message[0] == '7': #error
					sock.connected.clear()
					raise Exception(message[4:])
				else:
					sock.connected.clear()
					raise Exception('Received unimplemented data type ' + message[0])

		elif response.status == 404: continue #this is what Torus does, I still don't know if it's good or bad
		else: raise Exception('Bad HTTP status ' + response.status)
	sock.connected.clear()

def send(sock, message):
	#TODO: the response is worthless
	HTTP.post(
		'http://' + sock.server + ':' + str(sock.port) + '/socket.io/1/xhr-polling/' + sock.session + '/?name=' + chatserv.user + '&key=' + sock.key + '&roomId=' + str(sock.id) + '&client=Chatserv&version=' + str(chatserv.version),
		'5:::' + json.dumps({'name': 'message', 'args': [message]}),
		{'Content-Type': 'text/plain', 'Cookie': chatserv.session},
		timeout=10
	)
