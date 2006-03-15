
import pprint

from types import *
from xstruct import pack, unpack, hexbyte

# Squash warnings about hex/oct
import warnings

versions = ["TP03"]
version = "TP03"

class Structure(object):
	def __init__(self, name, longname, description="", example="", **kw):
		self.name = name
		self.longname = longname
		self.description = description
		self.example = example
	
	def check(self, value):
		raise SyntaxError("Not Implimented")

	def __str__(self):
		return "<%s %s %s>" % (self.__class__.__name__.split('.')[-1], hex(id(self)), self.name)
	__repr__ = __str__

class StringStructure(Structure):
	def check(self, value):
		if not isinstance(value, StringTypes):
			raise ValueError("Value must be a string type")

	xstruct = 'S'

class CharacterStructure(StringStructure):
	def __init__(self, *args, **kw):
		Structure.__init__(self, *args, **kw)

		if kw.has_key('size'):
			self.size = kw['size']
		else:
			self.size = 1
	
	def xstruct(self):
		if self.size == 1:
			return 'c'
		return str(self.size)+'s'
	xstruct = property(xstruct)

	def check(self, value):
		StringStructure.check(self, value)
		if len(value) != self.size:
			raise ValueError("Value is not the correct size! Must be length %i" % self.size)
			
class IntegerStructure(Structure):
	sizes = {
		8: ('b', 'B', None), 
		16: ('h', 'H', 'n'),
		32: ('i', 'I', 'j'),
		64: ('q', 'Q', 'p'),
	}
	
	def __init__(self, *args, **kw):
		Structure.__init__(self, *args, **kw)

		if kw.has_key('size'):
			size = kw['size']
		else:
			size = 32
		
		if kw.has_key('type'):
			type = kw['type']
		else:
			type = 'signed'
		
		if not size in self.sizes.keys():
			raise ValueError("Only supported sizes are %r not %i" % (self.sizes.keys(),size))
		self.size = size

		if not type in ("signed", "unsigned", "semisigned"):
			raise ValueError("Type can only be signed, unsigned or semisigned")
		self.type = type

	def xstruct(self):
		if self.type == "signed":
			xstruct = self.sizes[self.size][0]
		elif self.type == "unsigned":
			xstruct = self.sizes[self.size][1]
		elif type == "semesigned":
			xstruct = self.sizes[self.size][2]
		return xstruct
	xstruct = property(xstruct)

	def check(self, value):
		if not isinstance(value, (IntType, LongType)):
			raise ValueError("Value must be a number")

		# Do a bounds check now
		if self.type == "signed":
			max = 2**(self.size-1)-1
			min = -2**(self.size-1)
		elif self.type == "unsigned":
			max = 2**self.size-1
			min = 0
		elif self.type == "semisigned":
			max = 2**self.size-2
			min = -1

		if value < min:
			raise ValueError("Value is too small! Must be bigger then %i" % min)
		
		if value > max:
			raise ValueError("Value is too big! Must be smaller then %i" % max)
		
class ListStructure(Structure):
	def __init__(self, *args, **kw):
		Structure.__init__(self, *args, **kw)

		if kw.has_key('structures'):
			structures = kw['structures']
		else:
			structures = []
		
		if not isinstance(structures, (TupleType, ListType)):
			raise ValueError("Argument must be a list or tuple")

		for structures in structures:
			if not isinstance(structures, Structure):
				raise ValueError("All values in the list must be structures!")
		self.structures = structures
		
	def xstruct(self):
		xstruct = "["
		for struct in self.structures:
			xstruct += struct.xstruct
		return xstruct+"]"

	def check(self, list):
		if not isinstance(list, (TupleType, ListType)):
			raise ValueError("Value must be a list or tuple")
		
		for item in list:
			if len(self.structures) != 1:
				if not isinstance(item, (TupleType, ListType)):
					raise ValueError("Value items must be a list or tuple not %r" % type(item))

				if len(item) != len(self.structures):
					raise ValueError("Value item was not the correct size (was %i must be %i)" % (len(item), len(self.structures)))
			
				for i in xrange(0, len(self.structures)):
					self.structures[i].check(item[i])
			else:
				self.structures[0].check(item)

class PacketMeta(type):
	def get_structures(cls):
		parent = cls.__bases__[0]
		print "----------------------------"
		print cls, parent

		r = []
		if parent != Packet:
			r += parent.structures
		if cls.__dict__.has_key('_structures'):
			r += cls._structures
		print cls, r
		print "----------------------------"
		return r

	def set_structures(cls, value):
		cls._structures = value
	structures = property(get_structures, set_structures)

	def __str__(self):
		return "<dynamic-class '%s' at %s>" % (self.name, hex(id(self)))
	__repr__ = __str__

class Packet(object):
	__metaclass__ = PacketMeta
	name = "Root Packet"

	def __init__(self, *arguments):
		self.structures = self.__class__.structures

		print self.structures, len(self.structures)
		print arguments, len(arguments)
		
		if len(arguments) < len(self.structures):
			raise ValueError("Not enough arguments given")
		
		arguments = list(arguments)
		
		self.arguments = []
		# Check each argument is valid
		for structure in self.structures:
			argument = arguments.pop(0)
			structure.check(argument)
			self.arguments.append(argument)

	def xstruct(self):
		xstruct = ""
		for structure in self.structures:
			xstruct += structure.xstruct
		return xstruct
	xstruct = property(xstruct)
	
	def __str__(self):
		print self.xstruct, self.arguments
		return pack(self.xstruct, *self.arguments)

class Objects(object):
	pass
objects = Objects()

import xml.parsers.expat

class Parser(object):
	def __init__(self):
		self.mode = []
		self.attrs = []
		self.structures = []

	def StartElementHandler(self, name, attrs):
		print "Start", name, attrs
		self.mode.append(name)
		self.attrs.append(attrs)
		
		if name in ("packet",):
			# Figure out what this packet is based on
			if attrs.has_key("base"):
				base = eval("objects." + attrs['base'])
			else:
				base = Packet

			class NewPacket(base):
				pass
			self.packet = NewPacket

		if name in ("structure",):
			self.structures.append([])

	def EndElementHandler(self, name):
		print "End", name
		if name != self.mode[-1]:
			raise ValueError("Element matching error")
		name = self.mode.pop(-1)
		attrs = self.attrs.pop(-1)

		print name, self.mode
		print attrs, self.attrs
		print "----------------------------------"
		# Packet Attributes
		if name in ("direction",):
			if self.mode[-1] != "packet":
				raise ValueError("Got a %s when not in a structure!" % name)
				
			self.attrs[-1][name] = self.data
			del self.data
		
		# Finished a packet
		if name in ("packet",):
			for key, value in attrs.items():
				setattr(self.packet, key, value)
		
			global objects
			setattr(objects, self.packet.name, self.packet)
			del self.packet

		# Finished a structure
		if name in ("structure",):
			if self.mode[-1] == "packet":
				self.packet.structures = self.structures.pop(-1)
				return
			
			if self.mode[-1] == "list":
				self.attrs[-1]['structures'] = self.structures.pop(-1)
				return
		
		# Structure components
		types = ("string", "character", "integer", "list",)
		if name in types:
			if self.mode[-1] != "structure":
				raise ValueError("Got a %s when not in a structure!" % name)
			
			nattrs = {}
			for key, value in attrs.items():
				if key in ("size",):
					value = long(value)
				nattrs[str(key)] = value
			
			self.structures[-1].append(eval(name.title() + "Structure")(**nattrs))
		
		# Structure components Attributes
		if name in ("longname", "description", "example",):
			if not self.mode[-1] in types:
				raise ValueError("Got a %s when not in a structure component!" % name)
			
			self.attrs[-1][name] = self.data
			del self.data

		# Special case as it's in "packet" and "structure"
		if name in ("name",):
			if self.mode[-1] == "packet":
				self.packet.name = self.data
				return

			if self.mode[-2] == "structure":
				self.attrs[-1]['name'] = self.data
				return

			raise ValueError("Got a name when not in structure!")
			
	def CharacterDataHandler(self, data):
		self.data = data

	def CreateParser(cls):
		p = xml.parsers.expat.ParserCreate()
		c = cls()

		print "dict", type(c), c.__dict__, cls.__dict__
		for name in cls.__dict__.keys():
			if name.startswith('__') or name == "CreateParser":
				continue
			
			value = getattr(c, name)
			if callable(value):
				setattr(p, name, value)

		return p
	CreateParser = classmethod(CreateParser)

if __name__ == "__main__":
	parser = Parser.CreateParser()
	parser.ParseFile(file("packet.xml", "r"))

	print objects
	print dir(objects)

	print objects.Okay("TP03", 2, 3, 23, "Test")
