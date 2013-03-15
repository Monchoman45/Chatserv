#!/usr/local/bin/python3
import os
import struct
import json

import chatserv
from util.frag import FragmentIndex

#No need to do file io every time we need a persistent value, so cache all data
commands = {}
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

def update_command(path, props):
	if path not in commands: raise Exception #commands can't be created on the fly, so their access can't either
	else:
		if 'commands' in __changes:
			if path in __changes['commands']:
				if __changes['commands'][path] == __CHANGE_REMOVE: __changes['commands'][path] = __CHANGE_REPLACE #already exists
				elif __changes['commands'][path] != __CHANGE_REPLACE: raise Exception #something bad happened
			else: __changes['commands'][path] = __CHANGE_REPLACE
		else: __changes['commands'] = {path: __CHANGE_REPLACE}

	for i in props: commands[path][i] = props[i]

	if len(__changes['commands']) > 10: chatserv.stack.put(chatserv.StackContext(flush, 'commands'))

def update_user(name, props = {}):
	if name[0] in userfiles: filename = name[0]
	else: filename = '*'

	if name not in users:
		users[name] = {
			'access': {'global': {}},
			'kicks': [],
			'bans': [],
		}
		if filename in __changes:
			if name in __changes[filename]:
				if __changes[filename][name] == __CHANGE_REMOVE: __changes[filename][name] = __CHANGE_REPLACE #already exists
				elif __changes[filename][name] != __CHANGE_ADD: raise Exception #something bad happened
			else: __changes[filename][name] = __CHANGE_ADD
		else: __changes[filename] = {name: __CHANGE_ADD}
	else:
		if filename in __changes:
			if name in __changes[filename]:
				if __changes[filename][name] == __CHANGE_REMOVE: __changes[filename][name] = __CHANGE_REPLACE
			else: __changes[filename][name] = __CHANGE_REPLACE
		else: __changes[filename] = {name: __CHANGE_REPLACE}

	for i in props: users[name][i] = props[i]

	if len(__changes[filename]) > 10: chatserv.stack.put(chatserv.StackContext(flush, filename))
def update_room(room, props = {}):
	room = int(room)
	filename = '0' #TODO

	if name not in rooms:
		rooms[room] = {}
		if filename in __changes:
			if name in __changes[filename]:
				if __changes[filename][room] == __CHANGE_REMOVE: __changes[filename][room] = __CHANGE_REPLACE #already exists
				elif __changes[filename][room] != __CHANGE_ADD: raise Exception #something bad happened
			else: __changes[filename][room] = __CHANGE_ADD
		else: __changes[filename] = {room: __CHANGE_ADD}
	else:
		if filename in __changes:
			if room in __changes[filename]:
				if __changes[filename][room] == __CHANGE_REMOVE: __changes[filename][room] = __CHANGE_REPLACE
			else: __changes[filename][room] = __CHANGE_ADD
		else: __changes[filename] = {room: __CHANGE_REPLACE}

	for i in props: rooms[room][i] = props[i]

	if len(__changes[filename]) > 10: chatserv.stack.put(chatserv.StackContext(flush, filename))

def remove_user(name):
	if name[0] in userfiles: filename = name[0]
	else: filename = '*'

	if name in users:
		del users[name]
		if filename in __changes:
			if name in __changes[filename]:
				if __changes[filename][name] == __CHANGE_REPLACE: __changes[filename][name] = __CHANGE_REMOVE
				elif __changes[filename][name] == __CHANGE_ADD: del __changes[filename][name]
			else: __changes[filename][name] = __CHANGE_REMOVE
		else: __changes[filename] = {name: __CHANGE_REMOVE}
	else: pass #complain?

	if len(__changes[filename]) > 10: chatserv.stack.put(chatserv.StackContext(flush, filename))
def remove_room(room):
	room = int(room)
	filename = '0' #FIXME: more than one file

	if room in rooms:
		del rooms[room]
		if filename in __changes:
			if room in __changes[filename]:
				if __changes[filename][room] == __CHANGE_REPLACE: __changes[filename][room] = __CHANGE_REMOVE
				elif __changes[filename][room] == __CHANGE_ADD: del __changes[filename][room]
			else: __changes[filename][room] = __CHANGE_REMOVE
		else: __changes[filename] = {room: __CHANGE_REMOVE}
	else: pass #complain?

	if len(__changes[filename]) > 10: chatserv.stack.put(chatserv.StackContext(flush, filename))

def flush(filename):
	file = __files[filename]
	index = __indexes[filename]
	changes = __changes[filename]
	if filename in userfiles: ref = users
	elif filename in roomfiles: ref = rooms
	else: ref = commands

	for i in changes:
		#TODO: optimize
		if changes[i] == __CHANGE_REPLACE:
			file.replace(i, json.dumps(ref[i]))
		if changes[i] == __CHANGE_ADD:
			file.append(i, json.dumps(ref[i]))
		if changes[i] == __CHANGE_REMOVE:
			file.remove(i)
		else: pass #complain?
	__changes[filename] = {}

#@close_thing
def flush_all():
	for file in __changes: flush(file)

#@init_thing
def init():
	for name in userfiles:
		file = FragmentIndex('database/' + name + '.frag')
		index = file.entries()
		__files[name] = file
		__indexes[name] = index
		file.seek(file.ilen + 4)
		for entry in index: users[entry.name.decode('utf-8')] = json.loads(file.read(entry.dlen).decode('utf-8'))

	for name in roomfiles:
		file = FragmentIndex('database/' + name + '.frag')
		index = file.entries()
		__files[name] = file
		__indexes[name] = index
		file.seek(file.ilen + 4)
		for entry in index: rooms[entry.name.decode('utf-8')] = json.loads(file.read(entry.dlen).decode('utf-8'))

	file = FragmentIndex('database/commands.frag')
	index = file.entries()
	__files['commands'] = file
	__indexes['commands'] = index
	file.seek(file.ilen + 4)
	for entry in index: commands[entry.name.decode('utf-8')] = json.loads(file.read(entry.dlen).decode('utf-8'))
