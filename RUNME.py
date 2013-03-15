#!/usr/local/bin/python3

if __name__ != '__main__': raise ImportError

import os
import io

dir = os.path.dirname(os.path.abspath(__file__))
os.mkdir('database')
files = ['commands', '*', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
for i in files:
	with io.open('database/' + files[i] + '.frag', 'wb') as file: file.write(b'\x00\x00\x00\x00')
