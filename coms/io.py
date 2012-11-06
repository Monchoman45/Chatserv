#!/usr/local/bin/python3
import sys
import json

from util import HTTP
import chatserv
from coms import xhr_polling

transports = {'xhr-polling': xhr_polling}

def spider(wiki):
	response = HTTP.get('http://' + wiki + '.wikia.com/wikia.php', {'controller': 'Chat', 'format': 'json', 'client': 'Chatserv', 'version': chatserv.version}, {'Cookie': chatserv.session}).read().decode('utf-8')
	return json.loads(response)

def session(room, key = None, server = None, port = None):
	if room <= 0: raise Exception('Invalid room ' + room)

	if key == False: raise Exception('\'key\' is false')
	elif key == None or hasattr(key, '__call__'):
		data = spider(room)
		if 'exception' in data: raise Exception(data['exeption']['message'])
		if data['chatkey']['key'] == False: raise Exception('\'key\' is false')
		session(room, data['chatkey'], data['nodeHostname'], data['nodePort'], key)

	result = HTTP.get('http://' + server + ':' + port + '/socket.io/1/', {'name': chatserv.user, 'key': key, 'roomId': room, 'client': 'Chatserv', 'version': chatserv.version}, {'Cookie': chatserv.session}).read().decode('utf-8')
	if result[:4] == 'new ': pass #do error things
	else: return result[:result.find(':')]

def receive(sock, message):
	if sock.id not in chatserv.chats or chatserv.chats[sock.id] != sock: raise Exception('Bad call to receive')
	if message['event'] == 'join': data = json.loads(message['joinData'])
	else: data = json.loads(message['data'])

	if message['event'] == 'chat:add' and data['attrs']['name'] == 'Monchoman45' and data['attrs']['text'] == '!quit':
		sys.exit()
	elif message['event'] == 'chat:add' and data['attrs']['text'].lower() == 'ping':
		sock.sendMessage('pong')

