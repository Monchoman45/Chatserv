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
	else: return Context(target, *command[i + 1:])

class Context():
	def __init__(self, callable, *args, **kwargs):
		self.callable = callable
		self.args = args
		self.kwargs = kwargs
	def __call__(self):
		self.callable(*self.args, **self.kwargs)

class Command():
	def __init__(self, callable, kwargs={}):
		self.callable = callable
		self.kwargs = kwargs
	def __call__(self, *args):
		self.callable(*args, **self.kwargs)

def quit(*args):
	chatserv.logout()

commands = {
	'logout': 'quit',
	'quit': Command(quit)
}
