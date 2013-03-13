#!/usr/local/bin/python3
'''
Utility module for reading and writing fragment index files (.frag).
A .frag file is an indexed group of arbitrarily sized named data
fragments.

.frag files consist of two parts, the index and the content body.

The first four bytes of the index are a four byte unsigned little-
endian integer, representing the total byte length of the index, not
counting itself (self.ilen). Immediately following this are fragment
entries. Each fragment entry consists of a one byte unsigned integer
representing the length of the name (nlen), followed by the name
(which must be exactly as long as specified), followed by a four byte
unsigned little-endian integer representing the length of the
fragment data (dlen). The index can contain any number of fragment
entries.

There must be as many fragments as there are fragment entries in the
index. Each fragment has a corresponding entry in the index, at the
same conceptual position - the first fragment corresponds to the
first index entry, the second to the second, and so on. A particular
fragment must be exactly as long as the data length specified by its
index entry. The content has no other restrictions; if it is the
correct length, it can be anything.

Several implications arise from these rules:
   * Fragments can have no name - or, more accurately, have a name
     length of 0.
   * Similarly, fragments can have no data. Like fragments with no
     name, this occurs when the fragment data length is 0.
   * The simplest possible index entry is, then, five null bytes.
   * It also possible for the total index length to be 0. With no
     room for index entries, there cannot be any fragments, and so
     the simplest (and shortest) possible .frag file is four null
     bytes.
   * The maximum name length is 255 bytes. The maximum length for an
     an index entry is therefore 260 bytes.
   * Similarly, the maximum length for both the index and an
     individual fragment is 4 gigabytes.
   * The longest possible .frag file is therefore: 4 + 4294967296 +
     (floor(4294967296 / 5) * 4294967296) = approx. 3.2 exabytes.
   * It takes longer to extract fragments at the end of a file than
     it does to extract fragments at the beginning.
   * It follows, then, that the larger the number of fragments in a
     file, the longer it will take to access fragments at the end.
   * It further follows, then, that if order is unimportant, it is
     more efficient to move fragments accessed more frequently to the
     beginning of the file.
   * Two or more fragments can share the same name.
   * Names don't have to be human-readable strings, they can be
     arbitrary binary data.
   * Although it is impossible for a fragment to be longer than its
     specified length, it can be shorter if padding bytes are used.
   * Allocating a larger number of bytes than needed and using
     padding to fill the space would allow for flexible length data
     (up to a certain point) without changing the absolute position
     of other fragments.
   * If the same concept is applied to fragment names, it becomes
     possible to mathematically skip to a particular entry position.
   * This would effectively eliminate the disadvantage to fragments
     at the end of the file.
   * Furthermore, it would be possible to derive the number of
     fragments in the file based on the total index length.
   * The start of the first fragment is always located at index
     length + 4.
   * The end of the last fragment is not necessarily the end of the
     file (but, arguably, it should be) - it is possible for extra
     "dead bytes" to exist at the end of the file that are not part
     of any fragment if the length of the last fragment is not long
     enough to cover the rest of the file.
   * Such "dead bytes" would be harmless to most operations, however,
     operations like append would suffer.
   * A .frag file can be stored inside another .frag file. In fact,
     a .frag file can store millions of other .frag files that in
     turn store more millions more .frag files.
   * .frag files stored in other .frag files can include fragments
     from the top level file. Consider a .frag file with two index
     entries, where the first corresponds to another .frag file with
     only one index entry. If the nested .frag file does not include
     the corresponding fragment, a further read would return part or
     all of the second fragment of the top level .frag file.
'''

from collections import namedtuple
import struct
import io
import os

Frag = namedtuple('Frag', ['ipos', 'index', 'name', 'dpos', 'dlen', 'data'])

#FragmentIndex: a fully compatible "no assumptions" .frag file reader
class FragmentIndex(io.FileIO):
	def __init__(self, file, chunksize = 4096):
		io.FileIO.__init__(self, file, 'r+')
		self.chunksize = chunksize
		self.ilen = struct.unpack('<I', self.read(4))[0]

	#essentially a dump
	def __iter__(self):
		if self.chunksize > 0 and self.ilen > self.chunksize: buff = self.read(self.chunksize)
		else: buff = self.read(self.ilen)
		self.__iter = {
			'index': 0,
			'ipos': 0,
			'dpos': self.ilen + 4,
			'buff': buff
		}
		self.seek(self.ilen + 4)
		return self

	def __next__(self):
		if self.__iter['ipos'] >= self.ilen:
			del self.__iter
			raise StopIteration
		blen = len(self.__iter['buff'])
		if blen < 260 and blen + self.__iter['ipos'] < self.ilen:
			self.seek(blen + self.__iter['ipos'] + 4)
			if self.ilen - (blen + self.__iter['ipos']) > self.chunksize: self.__iter['buff'] += self.read(self.chunksize)
			else: self.__iter['buff'] += self.read(self.ilen - (blen + self.__iter['ipos']))
			self.seek(self.__iter['dpos'])

		nlen = struct.unpack('<B', self.__iter['buff'][:1])[0]
		name = self.__iter['buff'][1:nlen + 1]
		dlen = struct.unpack('<I', self.__iter['buff'][nlen + 1:nlen + 5])[0]
		frag = Frag(self.__iter['ipos'], self.__['index'], name, self.__iter['dpos'], dlen, self.read(dlen))
		self.__iter['dpos'] += dlen
		self.__iter['ipos'] += nlen + 5
		self.__iter['buff'] = self.__iter['buff'][nlen + 5:]
		self.__iter['index'] += 1
		return frag

	#Close a gap
	#The first `gap` bytes after `start` will be removed from the file.
	#All content between `start + gap` and `end` will be shifted up to overwrite the necessary bytes.
	#Note that this can leave arbitrary bytes at least up to `end`, so it is recommended that you .truncate() the file.
	#`append` will be written at the end of the moved content.
	#If `append` is always considered a keyword argument, applying the same sequential arguments to __insert should
	#	return the file to its original size (but the bytes overwritten are lost forever).
	def __delete(self, gap, start, end = None, append = b''):
		if end == None: end = os.path.getsize(self.name)
		self.seek(start + gap)
		if self.chunksize > 0 and end - (start + gap) > self.chunksize:
			mod = (end - (start + gap)) % self.chunksize
			if mod > 0:
				buff = self.read(mod)
				bpos = start + gap + mod
			else:
				buff = b''
				bpos = start + gap
			self.seek(start)
			self.write(buff)
			while bpos < end:
				self.seek(bpos)
				buff = self.read(self.chunksize)
				self.seek(bpos - gap)
				self.write(buff)
				bpos += self.chunksize
			self.seek(bpos - gap)
			self.write(append)
		else:
			buff = self.read(end - (start + gap)) + append
			self.seek(start)
			self.write(buff)

	#Make a gap
	#A gap of length `gap + len(prepend)` will be created at `start`.
	#All content between `start` and `end` will be shifted down to create the space necessary.
	#Anything between `end` and the end of the file will be overwritten. `end` defaults to the end of the file.
	#`append` will be written directly after the content between `start` and `end` (after it is moved; `append` won't be overwritten).
	#`prepend` will be written at exactly `start + gap`. Directly after `prepend` will be the content between `start` and `end`.
	#Using a gap length of 0 and specifying content for `prepend` is essentially an insertion (hence the name).
	#Try testing this function on a file that contains a memorable sequence (like the alphabet) to help learn how it works.
	#If `append` and `prepend` are always considered keyword arguments, applying the same sequential arguments to __delete should
	#	return the file to its original state (if .truncate() is called immediately after, otherwise arbitrary bytes will exist).
	def __insert(self, gap, start, end = None, prepend = b'', append = b''):
		if end == None: end = self.seek(0, io.SEEK_END)
		else: self.seek(end)
		if self.chunksize > 0 and end - start > self.chunksize:
			mod = (end - start) % self.chunksize
			if mod > 0:
				self.seek(end - mod)
				buff = self.read(mod) + append
				bpos = end - mod
			else:
				buff = append
				bpos = end
			self.seek(bpos + gap + len(prepend))
			self.write(buff)
			while bpos > start:
				bpos -= self.chunksize
				self.seek(bpos)
				buff = self.read(self.chunksize)
				self.seek(bpos + gap + len(prepend))
				self.write(buff)
			self.seek(bpos + gap)
			self.write(prepend)
		else:
			self.seek(start)
			buff = prepend + self.read(end - start) + append
			self.seek(start + gap)
			self.write(buff)

	#Return an array of all the data in the file
	def dump(self):
		self.seek(4)
		if self.chunksize > 0 and self.ilen > self.chunksize: buff = self.read(self.chunksize)
		else: buff = self.read(self.ilen)
		ipos = 0
		dpos = self.ilen + 4
		index = 0
		frags = []
		self.seek(self.ilen + 4)
		while ipos < self.ilen:
			blen = len(buff)
			if blen < 260 and blen + ipos < self.ilen:
				self.seek(blen + ipos + 4)
				if self.ilen - (blen + ipos) > self.chunksize: buff += self.read(self.chunksize)
				else: buff += self.read(self.ilen - (blen + ipos))
				self.seek(dpos)

			nlen = struct.unpack('<B', buff[:1])[0]
			name = buff[1:nlen + 1]
			dlen = struct.unpack('<I', buff[nlen + 1:nlen + 5])[0]
			frags.append(Frag(ipos, index, name, dpos, dlen, self.read(dlen)))
			dpos += dlen
			ipos += nlen + 5
			index += 1
			buff = buff[nlen + 5:]
		return frags

	#Get an array containing every index entry (no data)
	def entries(self):
		self.seek(4)
		if self.chunksize > 0 and self.ilen > self.chunksize: buff = self.read(self.chunksize)
		else: buff = self.read(self.ilen)
		ipos = 0
		entries = []
		index = 0
		while ipos < self.ilen:
			blen = len(buff)
			if blen < 260 and blen + ipos < self.ilen:
				if self.ilen - (blen + ipos) > self.chunksize: buff += self.read(self.chunksize)
				else: buff += self.read(self.ilen - (blen + ipos))

			nlen = struct.unpack('<B', buff[:1])[0]
			name = buff[1:nlen + 1]
			dlen = struct.unpack('<I', buff[nlen + 1:nlen + 5])[0]
			entries.append(Frag(ipos, index, name, dpos, dlen, None))
			ipos += nlen + 5
			buff = buff[nlen + 5:]
			index += 1
		return entries

	#Get the information (ipos, name, dpos, dlen) for the fragment at index `num`
	def index(self, num):
		self.seek(4)
		if self.chunksize > 0 and self.ilen > self.chunksize: buff = self.read(self.chunksize)
		else: buff = self.read(self.ilen)
		ipos = 0
		dpos = self.ilen + 4
		index = 0
		while ipos < self.ilen:
			blen = len(buff)
			if blen < 260 and blen + ipos < self.ilen:
				if self.ilen - (blen + ipos) > self.chunksize: buff += self.read(self.chunksize)
				else: buff += self.read(self.ilen - (blen + ipos))

			nlen = struct.unpack('<B', buff[:1])[0]
			name = buff[1:nlen + 1]
			dlen = struct.unpack('<I', buff[nlen + 1:nlen + 5])[0]
			if index == num: return Frag(ipos, index, name, dpos, dlen, None)
			ipos += nlen + 5
			dpos += dlen
			buff = buff[nlen + 5:]
			index += 1
		return False

	#Get the data of the fragment at index `num`
	def get(self, num):
		pos = self.index(num)
		if pos == False: return False

		self.seek(pos.dpos)
		return Frag(pos.ipos, pos.index, pos.name, pos.dpos, pos.dlen, self.read(pos.dlen))

	#Get the index of the first fragment with the name `name` (no data)
	def pos(self, find):
		if isinstance(find, str): find = find.encode('utf-8') #make bytes

		self.seek(4)
		if self.chunksize > 0 and self.ilen > self.chunksize: buff = self.read(self.chunksize)
		else: buff = self.read(self.ilen)
		ipos = 0
		dpos = self.ilen + 4
		while ipos < self.ilen:
			blen = len(buff)
			if blen < 260 and blen + ipos < self.ilen:
				if self.ilen - (blen + ipos) > self.chunksize: buff += self.read(self.chunksize)
				else: buff += self.read(self.ilen - (blen + ipos))

			nlen = struct.unpack('<B', buff[:1])[0]
			name = buff[1:nlen + 1]
			dlen = struct.unpack('<I', buff[nlen + 1:nlen + 5])[0]
			if name == find: return Frag(ipos, index, name, dpos, dlen, None)
			ipos += nlen + 5
			dpos += dlen
			buff = buff[nlen + 5:]
		return False

	#Get the data of the first fragment with the name `name`
	def find(self, find):
		pos = self.pos(find)
		if pos == False: return False

		self.seek(pos.dpos)
		return Frag(pos.ipos, pos.index, pos.name, pos.dpos, pos.dlen, self.read(pos.dlen))

	#Add a fragment to the end of the file
	def append(self, name, frag):
		if isinstance(name, str): name = name.encode('utf-8')
		if isinstance(frag, str): frag = frag.encode('utf-8')

		nlen = len(name)
		dlen = len(frag)
		#NOTE: this assumes there are no dead bytes at the end of the file.
		#      Parsing through the entire index just to find the end of the last fragment
		#      is an absurd amount of work in contrast to an incredibly safe assumption.
		self.__insert(0, self.ilen + 4, prepend=struct.pack('<B', nlen) + name + struct.pack('<I', dlen), append=frag)

		self.ilen += nlen + 5
		self.seek(0)
		self.write(struct.pack('<I', self.ilen))
		return Frag(self.ilen, None, name, end + nlen + 5, dlen, frag)

	#Add a fragment to the beginning of the file
	def prepend(self, name, frag):
		if isinstance(name, str): name = name.encode('utf-8')
		if isinstance(frag, str): frag = frag.encode('utf-8')

		nlen = len(name)
		dlen = len(frag)
		self.__insert(nlen + 5, self.ilen + 4, prepend=frag) #prepend the data and make space to move the index
		self.__insert(nlen + 5, 4, self.ilen + 4) #shift the index over

		self.ilen += nlen + 5
		self.seek(0)
		self.write(struct.pack('<I', self.ilen) + struct.pack('<B', nlen) + name + struct.pack('<I', dlen))
		return Frag(4, 0, name, self.ilen + nlen + 5, dlen, frag)

	#Replace the data of the first fragment with name `find`
	def replace(self, find, frag):
		if isinstance(find, str): find = find.encode('utf-8')
		if isinstance(find, str): frag = frag.encode('utf-8')

		pos = self.pos(find)
		if pos == False: return False

		ipos = pos.ipos
		dpos = pos.dpos
		flen = pos.dlen #dlen of existing frag
		nlen = len(find)
		dlen = len(frag)

		if flen != dlen: #different lengths, change file size
			self.seek(ipos + nlen + 5)
			self.write(struct.pack('<I', dlen))
			if flen > dlen: #new one is smaller
				self.__delete(flen - dlen, dpos + dlen)
				self.truncate()
			else: self.__insert(dlen - flen, dpos + flen) #new one is bigger
		self.seek(dpos)
		self.write(frag)
		return Frag(ipos, pos.index, find, dpos, dlen, frag)

	#Remove and return the fragment at index `num`
	def pop(self, num = 0):
		pos = self.index(num)
		if pos == False: return False

		ipos = pos.ipos
		dpos = pos.dpos
		dlen = pos.dlen
		nlen = len(pos.name)
		self.ilen -= nlen + 5
		self.seek(0)
		self.write(struct.pack('<I', self.ilen))

		self.__delete(nlen + 5, ipos + 4, dpos)
		self.seek(dpos)
		frag = self.read(dlen)
		self.__delete(dlen + nlen + 5, dpos - (nlen + 5))
		self.truncate()

		return Frag(ipos, pos.index, pos.name, dpos, dlen, frag)

	#Remove and return the first fragment with name `name`
	def remove(self, name):
		if isinstance(name, str): name.decode('utf-8')

		pos = self.pos(name)
		if pos == False: return False

		ipos = pos.ipos
		dpos = pos.dpos
		dlen = pos.dlen
		nlen = len(name)
		self.ilen -= nlen + 5
		self.seek(0)
		self.write(struct.pack('<I', self.ilen))

		self.__delete(nlen + 5, ipos + 4, dpos)
		self.seek(dpos)
		frag = self.read(dlen)
		self.__delete(dlen + nlen + 5, dpos - (nlen + 5))
		self.truncate()

		return Frag(ipos, pos.index, name, dpos, dlen, frag)

	#Ensure correct file size
	def trunc(self):
		if self.chunksize > 0 and self.ilen > self.chunksize: buff = self.read(self.chunksize)
		else: buff = self.read(self.ilen)
		ipos = 0
		dpos = self.ilen + 4
		while ipos < self.ilen:
			blen = len(buff)
			if blen < 260 and blen + ipos < self.ilen:
				if self.ilen - (blen + ipos) > self.chunksize: buff += self.read(self.chunksize)
				else: buff += self.read(self.ilen - (blen + ipos))
			nlen = struct.unpack('<B', buff[:1])[0]
			dlen = struct.unpack('<I', buff[nlen + 1:nlen + 5])[0]
			ipos += nlen + 5
			dpos += dlen
			buff = buff[nlen + 5:]
		self.seek(dpos)
		return self.truncate()

#Convenience functions
def dump(file):
	with FragmentIndex(file) as f: ret = f.dump()
	return ret
def entries(file):
	with FragmentIndex(file) as f: ret = f.entries()
	return ret
def index(file, num):
	with FragmentIndex(file) as f: ret = f.index(num)
	return ret
def get(file, num):
	with FragmentIndex(file) as f: ret = f.get(num)
	return ret
def pos(file, num):
	with FragmentIndex(file) as f: ret = f.pos(num)
	return ret
def find(file, name):
	with FragmentIndex(file) as f: ret = f.find(name)
	return ret
def append(file, name, frag):
	with FragmentIndex(file) as f: ret = f.append(name, frag)
	return ret
def prepend(file, name, frag):
	with FragmentIndex(file) as f: ret = f.prepend(name, frag)
	return ret
def replace(file, name, frag):
	with FragmentIndex(file) as f: ret = f.replace(name, frag)
	return ret
def pop(file, num):
	with FragmentIndex(file) as f: ret = f.pop(num)
	return ret
def remove(file, name):
	with FragmentIndex(file) as f: ret = f.remove(name)
	return ret
def trunc(file):
	with FragmentIndex(file) as f: ret = f.trunc()
	return ret
