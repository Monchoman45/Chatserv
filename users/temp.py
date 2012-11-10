#!/usr/local/bin/python3
import chatserv

local = {}
#global is a reserved word. It's kind of annoying, really -
#global variables aren't as dangerous as python makes them out to be.
glob = {}

def update_user(room, name, props):
	room = int(room)
	if room not in local: local[room] = {}
	if name not in local[room]: local[room][name] = props
	else:
		for i in props: local[room][name][i] = props[i]
	if name not in glob: glob[name] = {}
	if room not in glob[name]: glob[name][room] = local[room][name] #pointer, saves memory
def update_room(room):
	chatserv.chats[int(room)].sendCommand('initquery')

def remove_user(room, name):
	room = int(room)
	if room in local and name in local[room]: del local[room][name]
	else: pass #complain?
	if name in glob and room in glob[name]: del glob[name][room]
def remove_room(room):
	room = int(room)
	if room in local: del local[room]
	for name in glob:
		if room in glob[name]: del glob[name][room]

