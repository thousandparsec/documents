"""\
An advanced version of pack/unpack which works with extra TP strutures.

Everything is assumed to be network order, ie you don't need to
prepend every struct with !

Normal stuff from the struct module:

 c	Char
 b	Int8		(8 bit integer)
 B	UInt8		(8 bit unsigned integer)
 h	Int16		(16 bit integer)
 H	UInt16		(16 bit unsigned integer)
 i	Int32		(32 bit integer)
 I	UInt32		(32 bit unsigned integer)
 q	Int64		(64 bit integer)
 Q	UInt64		(64 bit unsigned integer)
 f	float		(32 bit floating point number)
 d	double		(64 bit floating point number)

Extra stuff defined by this module:

 S	String
 Y	Padded String	
 [	List Start		(unsigned int32 length)
 ]	List End	
 {	List Start		(unsigned int64 length)
 }	List End
 n	SInt16			(16 bit semi-signed integer)
 j	SInt32			(32 bit semi-signed integer)
 p	SInt64			(64 bit semi-signed integer)
 t	timestamp		(32 bit unsigned integer)
 T	timestamp		(64 bit unsigned integer)
 
The structure of the data in the list is described by the data inside the
brackets.

Example:
	[L] would be a list of unsigned longs
	It is actually transmitted as <length><data><data><data>
	
Obviously you can't calculate size of an xstruct string. The unpack
function will return the unused data.
"""

import pprint
import struct
import sys
import string
from types import *

# Squash errors about hex/oct
import warnings

_error = struct.error
_pack = struct.pack
_unpack = struct.unpack
_calcsize = struct.calcsize

semi = {'n':(16, 'H'), 'j':(32, 'I'), 'p':(64, 'Q')}
smallints = "njbBhHiI"
times = {'T':'Q', 't':'I'}

def hexbyte(string):
	"""\
	Takes a string and prints out the bytes in hex.
	"""
	s = ""
	for i in string:
		s += str(hex(ord(i)))
		if (ord(i) >= ord('A') and ord(i) <= ord('z')) \
			or (ord(i) >= ord('0') and ord(i) <= ord('9')) \
			or (ord(i) == ord(" ")):
			s += "(%s)" % i
		s += " "
	return s

def pack(struct, *args):
	"""\
	Takes a structure string and the arguments to pack in the format
	specified by string.
	"""
	args = list(args)
	output = ""

	while len(struct) > 0:
		char = struct[0]
		struct = struct[1:]
		
		if char == ' ' or char == '!':
			continue
		elif char == '{':
			# Find the closing brace
			substruct, struct = string.split(struct, '}', maxsplit=1)
			output += pack_list('L', substruct, args.pop(0))
		elif char == '[':
			# Find the closing brace
			substruct, struct = string.split(struct, ']', maxsplit=1)
			output += pack_list('I', substruct, args.pop(0))
		elif char in 'Tt':
			output += pack_time(args.pop(0), times[char])
		elif char == 'S':
			output += pack_string(args.pop(0))
		elif char in string.digits:
			# Get all the numbers
			substruct = char
			while struct[0] in string.digits:
				substruct += struct[0]
				struct = struct[1:]
			# And the value the number applies to
			substruct += struct[0]
			struct = struct[1:]
			
			number = int(substruct[:-1])
			if substruct[-1] == 's':
				output += _pack("!"+substruct, args.pop(0))
			elif substruct[-1] == 'x':
				output += "\0" * number
			else:
				# Get the correct number of arguments
				new_args = []
				while len(new_args) < number:
					new_args.append(args.pop(0))
					
				output += apply(_pack, ["!"+substruct,] + new_args)
		else:
			if char in smallints and isinstance(args[0], long):
				args[0] = int(args[0])
			
			a = args.pop(0)
			if char in semi.keys():
				if a == -1:
					a = 2**semi[char][0]-1
				
				char = semi[char][1]

			try:
				output += _pack("!"+char, a)
			except _error, e:
				print "Struct", char, "Args '%s'" % (a,)
				raise
			
	return output


def unpack(struct, s):
	"""\
	Takes a structure string and a data string.

	((values1,value2), remaining_data)
	
	"""
	output = []
	
	while len(struct) > 0:
		char = struct[0]
		struct = struct[1:]

		if char == ' ' or char == '!':
			continue
		elif char == '{':
			# Find the closing brace
			substruct, struct = string.split(struct, '}', maxsplit=1)
			data, s = unpack_list("L", substruct, s)
			
			output.append(data)
		elif char == '[':
			# Find the closing brace
			substruct, struct = string.split(struct, ']', maxsplit=1)
			data, s = unpack_list("I", substruct, s)
			
			output.append(data)
		elif char in 'Tt':
			data, s = unpack_time(s, times[char])
			
			output.append(data)
		elif char == 'S':
			data, s = unpack_string(s)
			
			output.append(data)
		elif char in string.digits:
			# Get all the numbers
			substruct = char
			while struct[0] in string.digits:
				substruct += struct[0]
				struct = struct[1:]
			# And the value the number applies to
			substruct += struct[0]
			struct = struct[1:]
			
			size = _calcsize(substruct)
			data = _unpack("!"+substruct, s[:size])
			s = s[size:]

			output += data
		else:
			if char in semi.keys():
				substruct = "!"+semi[char][1]
			else:
				substruct = "!"+char

			size = _calcsize(substruct)

			try:
				data = _unpack(substruct, s[:size])
			except _error, e:
				print "Struct", substruct, "Args '%s'" % (s[:size],)
				raise
			s = s[size:]

			if char in semi.keys():
				if data[0] == 2**semi[char][0]-1:
					data = (-1,)
			output += data

	return tuple(output), s

def pack_list(length_struct, struct, args):
	"""\
	*Internal*

	Packs the id list so it can be send.
	"""
	# The length
	output = pack(length_struct, len(args))

	# The list
	for id in args:
		if type(id) == ListType or type(id) == TupleType:
			args = [struct] + list(id)
			output += apply(pack, args)
		else:
			output += pack(struct, id)
		
	return output

def unpack_list(length_struct, struct, s):
	"""\
	*Internal*

	Returns the first string from the input data and any remaining data.
	"""
	output, s = unpack(length_struct, s)
	length, = output

	list = []
	for i in range(0, length):
		output, s = unpack(struct, s)
		if len(output) == 1:
			list.append(output[0])
		else:
			list.append(output)

	return list, s

def pack_string(s):
	"""\
	*Internal*

	Prepares a string to be send out on a wire.
	
	It appends the string length to the beginning and adds a 
	null terminator.
	"""
	s = str(s)
	
	temp = s
	return pack("!I", len(temp)) + temp

def unpack_string(s):
	"""\
	*Internal*

	Returns the first string from the input data and any remaining data.
	"""
	# Totally empty string
	if len(s) == 0:
		return "", s
	
	# Remove the length
	(l, ), s = unpack("I", s)
	if l > 0:
		# Get the string, (we don't need the null terminator so nuke it)
		output = s[:l]
		s = s[l:]
		
		# Remove any extra null terminators.
		if output[-1] == '\0':
			output = output[:-1]
		
		return output, s
	else:
		return "", s


import time
from datetime import datetime

def unpack_time(s, type='I'):
	"""\
	*Internal*

	Returns the datetime object and any remaining data.
	"""
	(l,), s = unpack("!"+type, s)
	if l < 0:
		return None
	return datetime.fromtimestamp(l), s

def pack_time(t, type='I'):
	"""\
	*Internal*

	Returns the datetime object and any remaining data.
	"""
	if t is None:
		t = -1
	else:
		t = time.mktime(t.timetuple())
	s = pack("!"+type, t)
	return s

