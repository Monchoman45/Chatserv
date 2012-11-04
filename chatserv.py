#!/usr/local/bin/python3
from threading import Thread, Lock
import multiprocessing
import os
import sys
import json
import util.HTTP as HTTP
import api

user = ''
password = ''
session = ''
version = 1

chats = []

def test():
	def cb(data):
		def cb(data):
			print(data)
		api.session(2087, data['chatkey'], data['nodeHostname'], data['nodePort'], cb)
	api.spider('community', cb)

def open(room, key = None, server = None, port = None, session = None, transport = None):

	return Chat(room, key, server, port, session, transport)

class Chat(Thread):
	def __init__(self, room, key, server, port, session, transport):
		Thread.__init__(self, name='chat-' + room)

		self.room = room
		self.key = key
		self.server = server
		self.port = port
		self.session = session
		self.transport = transport

		self.connected = False
		self.connecting = False
		self.userlist = {}

		self.start()
	def run(self):
		global chats
		chats[self.room] = self
		
		#make a socket and connect and stuff

def login(name = None, passw = None):
	global session, user, password
	if name == None: name = user
	if passw == None: passw = password
	print('Logging in...')
	response = HTTP.post('http://community.wikia.com/api.php', {'action': 'login', 'lgname': name, 'lgpassword': passw, 'format': 'json'})
	cookie = response.getheader('Set-Cookie')
	newsession = cookie[:cookie.find(';') + 1]

	HTTP.post('http://community.wikia.com/api.php', {'action': 'login', 'lgname': name, 'lgpassword': passw, 'lgtoken': json.loads(response.read().decode('utf-8'))['login']['token']}, {'Cookie': newsession})
	user = name #this should help prevent race conditions
	password = passw
	session = newsession
	print('Session:', session)

def loggedin():
	return bool(json.loads(HTTP.get('http://community.wikia.com/api.php', {'action': 'query', 'meta': 'userinfo', 'format': 'json'}, {'Cookie': session}).read().decode('utf-8')))

#FIXME: find a better way of passing username/password than through argv
if len(sys.argv) < 3: raise Exception('Must specify username and password')
user = sys.argv[1]
password = sys.argv[2]
login()
test()
