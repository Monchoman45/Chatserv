#!/usr/local/bin/python3
import sys
import json

from util import HTTP
import chatserv

#transports = {}
from transports import *
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

	__events[message['event']](sock, data)
	#TODO: run custom event handlers bound with a function decorator or something

def __initial(sock, data):
	for model in data['collections']['users']['models']: __updateUser(sock, model)

def __chat_add(sock, data):
	#TODO: log
	if data['attrs']['text'][0] == '!':
		command = chatserv.commands.select(data['attrs']['text'][1:])
		if command == None: sock.sendMessage('No command ' + data['attrs']['text'])
		else: command()

def __join(sock, data):
	__updateUser(sock, data)

def __updateUser(sock, data):
	props = {
		'mod': data['attrs']['isModerator'],
		'staff': data['attrs']['isStaff'],
		'admin': data['attrs']['isCanGiveChatMode'],
		'statusState': data['attrs']['statusState'],
		'statusMessage': data['attrs']['statusMessage'],
		'edits': data['attrs']['editCount']
	}
	if data['attrs']['since']: props['since'] = data['attrs']['since']['0']
	else: props['since'] = None
	chatserv.users.temp.update_user(sock.id, data['attrs']['name'], props)

def __part(sock, data):
	chatserv.users.temp.remove_user(sock.id, data['attrs']['name'])

def __logout(sock, data):
	chatserv.users.temp.remove_user(sock.id, data['attrs']['leavingUserName'])

def __ban(sock, data):
	__kick(sock, data)

def __kick(sock, data):
	if data['attrs']['kickedUserName'] == chatserv.name: sock.kill()

def __openPrivateRoom(sock, data):
	if data['attrs']['roomId'] not in chatserv.chats: chatserv.PrivateChat(data['attrs']['users'], data['attrs']['roomId'], sock)

def __forceReconnect(sock, data):
	pass

def __disableReconnect(sock, data):
	pass

__events = {
	'initial': __initial,
	'chat:add': __chat_add,
	'join': __join,
	'updateUser': __updateUser,
	'part': __part,
	'logout': __logout,
	'ban': __ban,
	'kick': __kick,
	'openPrivateRoom': __openPrivateRoom,
	'forceReconnect': __forceReconnect,
	'disableReconnect': __disableReconnect
}
