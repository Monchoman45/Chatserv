#!/usr/local/bin/python3
import chatserv

def select(command, prop = None):
	if isinstance(command, str): command = command.strip(' ').split(' ')
	else: command = command[:] #is array, copy it, because a redirect will modify it
	ref = commands
	i = 0;
	target = None
	while command[i] in ref:
		index = ref[command[i]]
		if isinstance(index, dict):
			ref = index
			i += 1
		elif isinstance(index, Command):
			target = index
			break
		elif isinstance(index, str):
			if index[0] == '/':
				command = [index[1:]] + command[i + 1:]
				ref = commands
				i = 0
			else: command = command[:i] + index.split(' ') + command[i + 1:]
		else: break

	if target == None:
		if 'default' in ref and isinstance(ref['default'], Command): target = ref['default']
		else: return None
	if prop == '*': return target
	elif prop != None: return getattr(target, prop)
	else: return CommandContext(target, *command[i + 1:])

class Command(chatserv.Context):
	def __init__(self, callable, **kwargs):
		self.callable = callable
		self.kwargs = kwargs
	def __call__(self, *args):
		return self.callable(*args, **self.kwargs)

#This may be confusing:
#Command is a Context. It is a function with predetermined arguments -
#to be more specific, a function with predetermined kwargs, but not args.
#Command is intended more to store arbitrary data about the function than
#it is to call it in a certain state.
#CommandContext is also a Context. The point of CommandContext /is/ to
#call a Command in a certain state. select() will return this, such that
#you can simply call the object and run the command. However, it also
#recognizes that commands executed by users in chat have several other
#use-dependent variables related to them. This is the variable "context".
#Sorry, but there's really no other name for it.
class CommandContext(chatserv.Context):
	def __call__(self, context):
		if context == None:
			#Command was executed by the system
			context = {
				'user': chatserv.name,
				'room': 0,
				'access': {},
				'match': 'op',
				'scope': 'global'
			}
		return self.callable(context, *self.args)

def quit(context):
	chatserv.logout()
def info_user(context, *user):
	user = ' '.join(user)
	if user in chatserv.users.temp.glob:
		rooms = chatserv.users.temp.glob[user].keys()
		output = []
		for room in rooms:
			if chatserv.chats[room].domain != None: output.append('[[w:c:' + chatserv.chats[room].domain + ':User:' + user + '|' + chatserv.chats[room].domain + ']]')
		length = len(output)
		if length == 1: return '[[User:' + user + '|]] is currently in ' + output[0] + '.'
		elif length == 2: return '[[User:' + user + '|]] is currently in ' + output[0] + ' and ' + output[1] + '.'
		elif length > 0: return '[[User:' + user + '|]] is currently in ' + ', '.join(output[:-1]) + ', and ' + output[-1] + '.'
		else: return '[[User:' + user + '|]] isn\'t online.'
	else: return 'I have no information on [[User:' + user + '|]].'
def info_room(context, domain):
	if domain in chatserv.chats:
		room = chatserv.chats[domain].id
		if room in chatserv.users.temp.local:
			users = chatserv.users.temp.local[room].keys()
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

commands = {
	'info': {
		'user': Command(info_user),
		'room': Command(info_room)
	},
	'logout': 'quit',
	'quit': Command(quit)
}
