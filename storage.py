#!/usr/local/bin/python3
import os
import struct
import json

import chatserv
from util.frag import FragmentIndex

#No need to do file io every time we need a persistent value, so cache all data
rooms = {}
users = {}

userfiles = ['*', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
roomfiles = [] #TODO

__CHANGE_ADD = 0
__CHANGE_REMOVE = 1
__CHANGE_REPLACE = 2

#As changes are made to persistent data, this change buffer of data points that should be changed grows.
#Each user is a data point, and each room is a data point. Because the data is stored as JSON, the entire
#data point must be written out, so numerous minute changes to the same data point won't bloat the buffer.
#Once the buffer reaches sufficient size for a particular file, a write operation is pushed onto the main
#stack, which will be picked up (possibly immediately) and run as its own operation. This should help keep
#routine operations at consistent execution times - one particular message should always take about the same
#amount of time to process, performing complex read and write operations sometimes would mess up statistics.
__changes = {}

#Cache the index of each file for quicker writing
__indexes = {}

#File pointers
__files = {}

def update_user(name, props):
	if name[0] in userfiles: filename = name[0]
	else: filename = '*'

	if name not in users:
		users[name] = props
		if filename in __changes: __changes[filename][name] = __CHANGE_ADD
		else: __changes[filename] = {name: __CHANGE_ADD}
	else:
		for i in props: users[name][i] = props[i]
		if filename in __changes: __changes[filename][name] = __CHANGE_REPLACE
		else: __changes[filename] = {name: __CHANGE_REPLACE}

	if len(__changes[filename]) > 10: chatserv.stack.put(chatserv.StackContext(flush, filename))
def update_room(room, props):
	room = int(room)
	filename = '0' #TODO

	if name not in rooms:
		rooms[room] = props
		if filename in __changes: __changes[filename][room] = __CHANGE_ADD
		else: __changes[filename] = {room: __CHANGE_ADD}
	else:
		for i in props: rooms[room][i] = props[i]
		if filename in __changes: __changes[filename][room] = __CHANGE_REPLACE
		else: __changes[filename] = {room: __CHANGE_REPLACE}

	if len(__changes[filename]) > 10: chatserv.stack.put(chatserv.StackContext(flush, filename))

def remove_user(name):
	if name[0] in userfiles: filename = name[0]
	else: filename = '*'

	if name in users:
		del users[name]
		if filename in __changes: __changes[filename][name] = __CHANGE_REMOVE
		else: __changes[filename] = {name: __CHANGE_REMOVE}
	else: pass #complain?

	if len(__changes[filename]) > 10: chatserv.stack.put(chatserv.StackContext(flush, filename))
def remove_room(room):
	room = int(room)
	filename = '0' #TODO

	if room in rooms:
		del rooms[room]
		if filename in __changes: __changes[filename][room] = __CHANGE_REMOVE
		else: __changes[filename] = {room: __CHANGE_REMOVE}
	else: pass #complain?

	if len(__changes[filename]) > 10: chatserv.stack.put(chatserv.StackContext(flush, filename))

def flush(filename):
	file = __files[filename]
	index = __index[filename]
	changes = __changes[filename]
	if filename in userfiles: ref = users #user
	else: ref = rooms #room
	for i in changes:
		#TODO: optimize
		if changes[i] == __CHANGE_REPLACE:
			file.replace(i, ref[i])
		if changes[i] == __CHANGE_ADD:
			file.append(i, ref[i])
		if changes[i] == __CHANGE_REMOVE:
			file.remove(i)
		else: pass #complain?
	__changes[filename] = {}

#@init_thing
def init():
	for i in userfiles:
		file = FragmentIndex('database/' + userfiles[i] + '.frag')
		index = file.entries()
		__files[userfiles[i]] = file
		__indexes[userfiles[i]] = index

		file.seek(file.ilen + 4)
		for j in index: users[index[j].name] = json.loads(file.read(index[j].dlen))

	for i in roomfiles:
		file = FragmentIndex('database/' + roomfiles[i] + '.frag')
		index = file.entries()
		__files[roomfiles[i]] = file
		__indexes[roomfiles[i]] = index

		file.seek(file.ilen + 4)
		for j in index: rooms[index[j].name] = json.loads(file.read(index[j].dlen))

