#!/usr/local/bin/python3
import sys
import json

from util import HTTP
import chatserv
from transports import xhr_polling

transports = {'xhr-polling': xhr_polling}

def spider(wiki):
	response = HTTP.get(
		'http://' + wiki + '.wikia.com/wikia.php',
		{
			'controller': 'Chat',
			'format': 'json',
			'client': 'Chatserv',
			'version': chatserv.version
		},
		{'Cookie': chatserv.session}
	).read().decode('utf-8')
	return json.loads(response)

def session(room, key = None, server = None, port = None):
	if room <= 0: raise Exception('Invalid room ' + room)
	if key == False: raise Exception('\'key\' is false')

	result = HTTP.get(
		'http://' + server + ':' + str(port) + '/socket.io/1/',
		{
			'name': chatserv.user,
			'key': key,
			'roomId': room,
			'client': 'Chatserv',
			'version': chatserv.version
		},
		{'Cookie': chatserv.session}
	).read().decode('utf-8')
	if result[:11] == 'new Error(\'': raise Exception(result[11:-2])
	else: return result[:result.find(':')]

def cajax(method, post):
	return HTTP.post(
		'http://community.wikia.com/index.php?acion=ajax&rs=ChatAjax&method=' + method + '&client=Chatserv&version=' + str(chatserv.version),
		post,
		{'Cookie': chatserv.session}
	).read().decode('utf-8')

def receive(sock, message):
	if sock.id not in chatserv.chats or chatserv.chats[sock.id] != sock: return #probably a race condition
	if message['event'] == 'join': data = json.loads(message['joinData'])
	else: data = json.loads(message['data'])

	if message['event'] == 'chat:add':
		#TODO: log
		if data['attrs']['text'][0] == '!':
			command = chatserv.commands.select(data['attrs']['text'][1:])
			if command == None: sock.sendMessage('No command ' + data['attrs']['text'])
			else: command()
	elif message['event'] == 'openPrivateRoom' and data['attrs']['roomId'] not in chatserv.chats:
		chatserv.PrivateChat(data['attrs']['users'], data['attrs']['roomId'], sock)

