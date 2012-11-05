#!/usr/local/bin/python3
import json
from util import HTTP
import chatserv

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

