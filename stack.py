#!/usr/local/bin/python3
from queue import Queue

stack = Queue()

class Context():
	def __init__(self, callable, *args, **kwargs):
		self.callable = callable
		self.args = args
		self.kwargs = kwargs
	def __call__(self):
		self.callable(*self.args, **self.kwargs)

class StackEvent():
	def __init__(self, type):
		self.type = type

class StackContext(StackEvent, Context):
	def __init__(self, callable, *args, **kwargs):
		StackEvent.__init__(self, 'context')
		Context.__init__(self, callable, *args, **kwargs)

