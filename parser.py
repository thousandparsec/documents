
import pprint

from types import *
from xstruct import pack, unpack, hexbyte

# Squash warnings about hex/oct
import warnings

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

		# Useless for us properties
		if name in ("notes", "note", "example"):
			return

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
			if not objects.has_key(self.packet.name):
				setattr(objects, self.packet.name, self.packet)
			else:
				# Better check the prebuilt one is identical
				print "Ignoring packet of type %s because it is hand coded."
			del self.packet

		# Finished a structure
		if name in ("structure",):
			if self.mode[-1] == "packet":
				structures = self.structures.pop(-1)
				self.packet.structures = structures

				for structure in structures:
					# FIXME: This doesn't seem the correct place to put this....
					def StructurePropertySet(self, value, name=structure.name):
						structure.check(value)
						setattr(self, "__%s" % name, value)
	
					def StructurePropertyGet(self, name=structure.name):
						return getattr(self, "__%s" % name)
	
					setattr(self.packet, name, property(StructurePropertyGet, StructurePropertySet, structure.description))
					return
			
			if self.mode[-1] == "list":
				self.attrs[-1]['structures'] = self.structures.pop(-1)
				return
		
		# Structure components
		types = ("string", "character", "integer", "list", "group",)
		if name in types:
			if self.mode[-1] != "structure":
				raise ValueError("Got a %s when not in a structure!" % name)
			
			nattrs = {}
			for key, value in attrs.items():
				if key in ("size",):
					value = long(value)
				nattrs[str(key)] = value
			
			self.structures[-1].append(eval(name.title() + "Structure")(**nattrs))
		
		# Properties of a packet or structure
		if name in ("name", "longname", "description", "example",):
			if self.mode[-1] == "packet":
				if name == "description":
					name = "__doc__"
				setattr(self.packet, name, self.data)

			if self.mode[-2] == "structure":
				if not self.mode[-1] in types:
					raise ValueError("Got a %s when not in a structure component!" % name)
				self.attrs[-1][name] = self.data
			del self.data

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
