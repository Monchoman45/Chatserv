#!/usr/local/bin/python3
from queue import Queue

stack = Queue()

class StackEvent():
	def __init__(self, type):
		self.type = type

class StackCallable(StackEvent):
	def __init__(self, callable, args = (), kwargs = {}):
		StackEvent.__init__(self, 'call')
		self.callable = callable
		self.args = args
		self.kwargs = kwargs

	def run(self):
		self.callable(*self.args, **self.kwargs)

