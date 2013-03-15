#!/usr/local/bin/python3
if __name__ != 'main': import chatserv
from collections import namedtuple
import time

SCOPE_LOCAL = 1
SCOPE_GLOBAL = 0

#This may be confusing:
#Command is a subclass of Context. It is a function with predetermined
#arguments - to be more specific, a function with predetermined kwargs,
#but not args. Command is intended more to store arbitrary data about
#the function than it is to call it in a certain state. It's used as a
#wrapper for functions that are put in the command tree.
#CommandContext is also a Context. The point of CommandContext /is/ to
#call a Command in a certain state. select() will return this, such that
#you can simply call the object and run the command. However, it also
#recognizes that commands executed by users in chat have several other
#use-dependent variables related to them. This is a CallContext.
class Command(chatserv.Context):
	def __init__(self, callable, **kwargs):
		chatserv.Context.__init__(self, callable, **kwargs)
	def __call__(self, *args):
		return self.callable(*args, **self.kwargs)
class CommandContext(chatserv.Context):
	def __init__(self, callable, path, *args):
		chatserv.Context.__init__(self, callable, *args)
		self.path = path
	def __call__(self, context):
		if context == None: context = CallContext(chatserv.user, 0, {}, SCOPE_GLOBAL, 'op') #Command was executed by the system
		return self.callable(context, *self.args)
CallContext = namedtuple('CallContext', ['user', 'room', 'access', 'scope', 'match'])

AccessMatch = namedtuple('AccessMatch', ['scope', 'match'])

def select(command):
	if isinstance(command, str): command = command.strip().split(' ')
	else: command = command[:] #is array, copy it, because a redirect will modify it
	ref = commands
	i = 0;
	target = None
	while len(command) > i and command[i] in ref:
		index = ref[command[i]]
		if isinstance(index, dict):
			target = index
			ref = index
			if len(command) > i + 1 and command[i + 1] not in ref and '_default' in ref: command.insert(i + 1, '_default')
			i += 1
		elif isinstance(index, Command):
			target = index
			break
		elif isinstance(index, str):
			target = None
			if index[0] == '/':
				command = [index[1:]] + command[i + 1:]
				ref = commands
				i = 0
			else: command = command[:i] + index.split(' ') + command[i + 1:]
		else: break

	if target == None or isinstance(target, dict): return target
	else: return CommandContext(target, ' '.join(command[:i + 1]), *command[i + 1:])

def check(name, room, path):
	# Access works as follows:
	#   There are two types of access, global and local
	#   Global rights apply across all wikis, and imply their corresponding local rights
	#   Local rights apply only in one room, and can be changed by users in that room
	#   Global rights are match only, you must have one of the rights specified to use the command
	#   If a room has not changed any of their rights, the default set is used; if they have, the room will have its own index
	#   If no local rights are specified (or "all" is present), anyone can use the command
	#   Otherwise, if the user has any of the rights specified, they can use the command
	#   Users cannot be given the access rights "mod", "admin", "none", or "all"
	#   Access rights for commands and users can be changed with !access
	#   If the local default has "none", local users cannot add or change rights (command is global only)
	#   Users with proper global privileges, however, can modify a particular wiki's local rights for global-only commands
	# 
	# Special rights:
	#   op: gives access to all commands
	#   mod (local only): requires chatmod right
	#   admin (local only): requires admin (technically, only the isCanGiveChatMode flag)
	#   none: no one can use command (except ops)
	#   all: everyone can use the command
	#     Applies locally, but if no rights are specified, anyone can use the command
	#     Globally, anyone can use the command if they have any global right
	#     Takes precedence over "none" (see matching order)
	#   Staff have implied global op
	#   On monchbox, admin implies global op
	# 
	# Matching order:
	#   global op (including staff and admin on monchbox)
	#   global all
	#   global none
	#   local op
	#   local all
	#   local empty (no rights specified)
	#   local none
	#   local admin
	#   local mod
	#   all other global rights
	#   all other local rights

	if path in chatserv.storage.commands:
		g_com_access = chatserv.storage.commands[path]['global']
		if room in chatserv.storage.commands[path]: l_com_access = chatserv.storage.commands[path][room]
		else: l_com_access = chatserv.storage.commands[path]['default']
	else: return None #bad things

	if name not in chatserv.storage.users:
		g_user_access = {}
		l_user_access = {}
	else:
		g_user_access = chatserv.storage.users[name]['access']['global']
		if room in chatserv.storage.users[name]['access']: l_user_access = chatserv.storage.users[name]['access'][room]
		else: l_user_access = {}
	if name in chatserv.data.users and room in chatserv.data.users[name]: user = chatserv.data.users[name][room]
	else: user = {
		'mod': False,
		'admin': False,
		'staff': False
	}

	#global op
	if (
		name == chatserv.user or #we passed chatserv for some weird reason
		'op' in g_user_access or #user is global op
		user['staff'] or #user is staff
		(room == 387 and user['admin']) #admin on monchbox
	): return AccessMatch(SCOPE_GLOBAL, 'op')

	#global all
	elif 'all' in g_com_access and len(g_user_access) > 0: return AccessMatch(SCOPE_GLOBAL, 'all')
	#global none
	elif 'none' in g_com_access: return False

	#local op
	if 'op' in l_user_access: return AccessMatch(SCOPE_LOCAL, 'op')
	#local all
	elif 'all' in l_com_access: return AccessMatch(SCOPE_LOCAL, 'all')
	#local empty
	elif len(l_com_access) == 0: return AccessMatch(SCOPE_LOCAL, '')
	#local none
	elif 'none' in l_com_access: return False
	#local admin
	elif 'admin' in l_com_access and user['admin']: return AccessMatch(SCOPE_LOCAL, 'admin')
	#local mod
	elif 'mod' in l_com_access and user['mod']: return AccessMatch(SCOPE_LOCAL, 'mod')

	#other global
	for i in g_user_access:
		if i in g_com_access or i in l_com_access: return AccessMatch(SCOPE_GLOBAL, i)
	#other local
	for i in l_com_access:
		if i in l_user_access: return AccessMatch(SCOPE_LOCAL, i)
	return False

def __change(access, changes, user = None):
	if user == None: user = chatserv.user
	add = True
	for change in changes:
		if change[0] == '+' or (change[0] != '-' and add): #+foo,bar -> +foo,+bar; -foo,bar -> -foo,-bar
			add = True
			while len(change) > 0 and (change[0] == '+' or change[0] == '-'): change = change[1:]
			change = change.strip()
			if len(change) > 0 and change not in access: access[change] = [time.time(), user]
		elif change[0] == '-':
			add = False
			while len(change) > 0 and (change[0] == '+' or change[0] == '-'): change = change[1:]
			change = change.strip()
			if len(change) > 0:
				if change in access: del access[change]
			else:
				for j in list(access.keys()): del access[j]
	return access

def access_local(context, changes, mode, *ref):
	changes = changes.split(',')
	ref = ' '.join(ref)

	if mode == 'u' or mode == 'user':
		chatserv.storage.update_user(ref) #create default user if necessary
		access = chatserv.storage.users[ref]['access']
		if context.room not in access: access[context.room] = {}
		access = __change(access[context.room], changes, context.user) #pointer means this is sufficient, don't have to update again
	elif mode == 'c' or mode == 'com' or mode == 'command':
		command = select(ref)
		if command == None: return 'No command ' + ref + '.'
		elif isinstance(command, dict): return 'Can\'t change access for ' + ref + ', it is a directory.'
		access = chatserv.storage.commands[command.path]
		if context.room not in access:
			if 'none' not in access['default'] or context.scope == SCOPE_GLOBAL: access[context.room] = access['default'].copy()
			else: return '!' + ref + ' is a global-only command.'
		access = access[context.room]
		chatserv.storage.update_command(ref, {context.room: __change(access, changes, context.user)})
	else: return 'Invalid mode ' + mode + '. Try "user" or "command".'

	return access_info_local(context, mode, *ref.split(' '))
def access_room(context, room, changes, mode, *ref):
	changes = changes.split(',')
	ref = ' '.join(ref)
	if room in chatserv.chats: room = chatserv.chats[room].id
	else:
		try: room = int(room)
		except: return 'Could not resolve domain ' + room + '.'

	if mode == 'u' or mode == 'user':
		chatserv.storage.update_user(ref) #creates default user if necessary
		access = chatserv.storage.users[ref]['access']
		if context.room not in access: access[context.room] = {}
		access = __change(access[context.room], changes, context.user) #pointer means this is sufficient, don't have to update again
	elif mode == 'c' or mode == 'com' or mode == 'command':
		command = select(ref)
		if command == None: return 'No command ' + ref + '.'
		elif isinstance(command, dict): return 'Can\'t change access for ' + ref + ', it is a directory.'
		access = chatserv.storage.commands[command.path]
		if context.room not in access:
			if 'none' not in access['default'] or context.scope == SCOPE_GLOBAL: access[context.room] = access['default'].copy()
			else: return '!' + ref + ' is a global-only command.'
		access = access[context.room]
		chatserv.storage.update_command(ref, {context.room: __change(access, changes, context.user)})
	else: return 'Invalid mode ' + mode + '. Try "user" or "command".'

	return access_info_room(context, room, mode, *ref.split(' '))
def access_global(context, changes, mode, *ref):
	changes = changes.split(',')
	ref = ' '.join(ref)

	if mode == 'u' or mode == 'user':
		chatserv.storage.update_user(ref) #creates default user if necessary
		__change(chatserv.storage.users[ref]['access']['global'], changes, context.user) #pointer means this is sufficient, don't have to update again
	elif mode == 'c' or mode == 'com' or mode == 'command':
		command = select(ref)
		if command == None: return 'No command ' + ref + '.'
		elif isinstance(command, dict): return 'Can\'t change access for ' + ref + ', it is a directory.'
		chatserv.storage.update_command(ref, {'global': __change(chatserv.storage.commands[command.path]['global'], changes, context.user)})
	else: return 'Invalid mode ' + mode + '. Try "user" or "command".'

	return access_info_global(context, mode, *ref.split(' '))
def access_default(context, changes, *ref):
	changes = changes.split(',')
	ref = ' '.join(ref)

	command = select(ref)
	if command == None: return 'No command ' + ref + '.'
	elif isinstance(command, dict): return 'Can\'t change access for ' + ref + ', it is a directory.'

	chatserv.storage.update_command(ref, {'default': __change(chatserv.storage.commands[command.path]['default'], changes, context.user)})
	return access_info_default(context, *ref.split(' '))
def access_info_all(context, mode, *ref):
	ref = ' '.join(ref)

	message = 'Access for '
	if mode == 'u' or mode == 'user':
		message += '[[User:' + ref + '|]]:'
		if ref in chatserv.storage.users: access = chatserv.storage.users[ref]['access']
		else: return message #we're done, we could do access = {} but nothing else would print
	elif mode == 'c' or mode == 'com' or mode == 'command':
		command = select(ref)
		if command == None: return 'No command ' + ref + '.'
		elif isinstance(command, dict): return 'Can\'t get access for ' + ref + ', it is a directory.'

		message += '!' + ref + ':'
		access = chatserv.storage.commands[command.path]
	else: return 'Invalid mode ' + mode + '. Try "user" or "command".'

	message += '\nGlobal:'
	for i in access['global']: message += '\n&nbsp;&nbsp;&nbsp;' + i + ': ' + time.ctime(access['global'][i][0]) + ' by ' + access['global'][i][1]
	if 'default' in access:
		message += '\n\nDefault:'
		for i in access['default']: message += '\n&nbsp;&nbsp;&nbsp;' + i + ': ' + time.ctime(access['default'][i][0]) + ' by ' + access['default'][i][1]
	if context.room in access and len(access[context.room]):
		message += '\n\nLocal:'
		for i in access[context.room]: message += '\n&nbsp;&nbsp;&nbsp;' + i + ': ' + time.ctime(access[context.room][i][0]) + ' by ' + access[context.room][i][1]
	return message
def access_info_room(context, room, mode, *ref):
	ref = ' '.join(ref)
	if room in chatserv.chats: room = chatserv.chats[room].id
	else:
		try: room = int(room)
		except: return 'Could not resolve domain ' + room + '.'

	message = 'Access in ' + str(room) +  ' for '
	if mode == 'u' or mode == 'user':
		message += '[[User:' + ref + '|]]:'
		if ref in chatserv.storage.users and context.room in chatserv.storage.users[ref]: access = chatserv.storage.users[ref]['access'][context.room]
		else: return message #we're done, we could do access = {} but nothing else would print
	elif mode == 'c' or mode == 'com' or mode == 'command':
		command = select(ref)
		if command == None: return 'No command ' + ref + '.'
		elif isinstance(command, dict): return 'Can\'t get access for ' + ref + ', it is a directory.'

		message += '!' + ref + ':'
		if context.room in chatserv.storage.commands[command.path]: access = chatserv.storage.commands[command.path][context.room]
		else: return message
	else: return 'Invalid mode ' + mode + '. Try "user" or "command".'

	for i in access: message += '\n&nbsp;&nbsp;&nbsp;' + i + ': ' + time.ctime(access[i][0]) + ' by ' + access[i][1]
	return message
def access_info_local(context, mode, *ref):
	ref = ' '.join(ref)

	message = 'Local access for '
	if mode == 'u' or mode == 'user':
		message += '[[User:' + ref + '|]]:'
		if ref in chatserv.storage.users and context.room in chatserv.storage.users[ref]: access = chatserv.storage.users[ref]['access'][context.room]
		else: return message #we're done, we could do access = {} but nothing else would print
	elif mode == 'c' or mode == 'com' or mode == 'command':
		command = select(ref)
		if command == None: return 'No command ' + ref + '.'
		elif isinstance(command, dict): return 'Can\'t get access for ' + ref + ', it is a directory.'

		message += '!' + ref + ':'
		if context.room in chatserv.storage.commands[command.path]: access = chatserv.storage.commands[command.path][context.room]
		else: return message
	else: return 'Invalid mode ' + mode + '. Try "user" or "command".'

	for i in access: message += '\n&nbsp;&nbsp;&nbsp;' + i + ': ' + time.ctime(access[i][0]) + ' by ' + access[i][1]
	return message
def access_info_global(context, mode, *ref):
	ref = ' '.join(ref)

	message = 'Global access for '
	if mode == 'u' or mode == 'user':
		message += '[[User:' + ref + '|]]:'
		if ref in chatserv.storage.users: access = chatserv.storage.users[ref]['access']['global']
		else: return message #we're done, we could do access = {} but nothing else would print
	elif mode == 'c' or mode == 'com' or mode == 'command':
		command = select(ref)
		if command == None: return 'No command ' + ref + '.'
		elif isinstance(command, dict): return 'Can\'t get access for ' + ref + ', it is a directory.'

		message += '!' + ref + ':'
		access = chatserv.storage.commands[command.path]['global']
	else: return 'Invalid mode ' + mode + '. Try "user" or "command".'

	for i in access: message += '\n&nbsp;&nbsp;&nbsp;' + i + ': ' + time.ctime(access[i][0]) + ' by ' + access[i][1]
	return message
def access_info_default(context, *ref):
	ref = ' '.join(ref)

	command = select(ref)
	if command == None: return 'No command ' + ref + '.'
	elif isinstance(command, dict): return 'Can\'t get access for ' + ref + ', it is a directory.'

	message = 'Default access for !' + ref + ':'
	access = chatserv.storage.commands[command.path]['default']
	for i in access: message += '\n&nbsp;&nbsp;&nbsp;' + i + ': ' + time.ctime(access[i][0]) + ' by ' + access[i][1]
	return message

def quit(context):
	chatserv.logout()

def find(context, *user):
	user = ' '.join(user)
	if user in chatserv.data.users[users]:
		rooms = chatserv.data.users[user].keys()
		output = []
		for room in rooms:
			if chatserv.chats[room].domain != None: output.append('[[w:c:' + chatserv.chats[room].domain + ':User:' + user + '|' + chatserv.chats[room].domain + ']]')
		length = len(output)
		if length == 1: return '[[User:' + user + '|]] is currently in ' + output[0] + '.'
		elif length == 2: return '[[User:' + user + '|]] is currently in ' + output[0] + ' and ' + output[1] + '.'
		elif length > 0: return '[[User:' + user + '|]] is currently in ' + ', '.join(output[:-1]) + ', and ' + output[-1] + '.'
		else: return '[[User:' + user + '|]] isn\'t online.'
	else: return 'I have no information on [[User:' + user + '|]].'
def users(context, domain):
	if domain in chatserv.chats:
		room = chatserv.chats[domain].id
		if room in chatserv.data.rooms:
			users = chatserv.data.rooms[room].keys()
			if len(users):
				output = []
				for user in users: output.append('[[w:c:' + domain + ':User:' + user + '|' + user + ']]')
				length = len(output)
				if length == 1: return '[[w:c:' + domain + '|' + domain + ']] currently contains ' + output[0] + '.'
				elif length == 2: return '[[w:c:' + domain + '|' + domain + ']] currently contains ' + output[0] + ' and ' + output[1] + '.'
				else: return '[[w:c:' + domain + '|' + domain + ']] currently contains ' + ', '.join(output[:-1]) + ', and ' + output[-1] + '.'
			else: return '[[w:c:' + domain + '|' + domain + ']] is empty.'
		else: return 'I have no information on [[w:c:' + domain + '|' + domain + ']].'
	else: return 'I have no information on [[w:c:' + domain + '|' + domain + ']].'

def flush(context, filename = None):
	if filename != None: chatserv.storage.flush(filename)
	else: chatserv.storage.flush_all()
	return 'Storage changes flushed.'

commands = {
	'access': {
		'g': 'global',
		'global': Command(access_global),
		'l': 'local',
		'local': Command(access_local),
		'r': 'room',
		'room': Command(access_room),
		'd': 'default',
		'default': Command(access_default),
		'i': 'info',
		'info': {
			'a': 'all',
			'all': Command(access_info_all),
			'g': 'global',
			'global': Command(access_info_global),
			'r': 'room',
			'room': Command(access_info_room),
			'l': 'local',
			'local': Command(access_info_local),
			'd': 'default',
			'default': Command(access_info_default),
			'_default': 'local'
		},
		'_default': 'local'
	},
	'find': Command(find),
	'users': Command(users),
	'flush': Command(flush),
	'logout': 'quit',
	'quit': Command(quit)
}
