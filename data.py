#!/usr/local/bin/python3
import chatserv

rooms = {}
users = {}

def update_user(room, name, props):
	room = int(room)
	if room not in rooms: rooms[room] = {}
	if name not in rooms[room]: rooms[room][name] = props
	else:
		for i in props: rooms[room][name][i] = props[i]
	if name not in users: users[name] = {}
	if room not in users[name]: users[name][room] = rooms[room][name] #pointer, saves memory
def update_room(room):
	chatserv.chats[int(room)].sendCommand('initquery')

def remove_user(room, name):
	room = int(room)
	if room in rooms and name in rooms[room]: del rooms[room][name]
	else: pass #complain?
	if name in users and room in users[name]: del users[name][room]
def remove_room(room):
	room = int(room)
	if room in rooms: del rooms[room]
	for name in users:
		if room in users[name]: del users[name][room]

