
from xstruct import pack, unpack, hexbyte

class PacketMeta(type):
	def get_structures(cls):
		parent = cls.__bases__[0]
		r = []
		if parent != Packet:
			r += parent.structures 
			print "parent", parent
		if cls.__dict__.has_key('_structures'):
			r += cls._structures
			print "cls", cls
		print r
		return r

	def set_structures(cls, value):
		cls._structures = value
	structures = property(get_structures, set_structures,"""\
		get_structures() -> [<structure>,]

		A list of structures. Cascades up the parent classes.

		For example,

		>>>class A:
		>>> __metaclass__ = PacketMeta
		>>>	pass
		>>>
		>>>A.structure = [1,]
		>>>
		>>>class B(A):
		>>>	pass
		>>>
		>>>B.structure = [2,]
		>>>
		>>>print B.structure
		[<structure 0x123456>, <structure 0x7890123>,]
		""")

	def __str__(self):
		return "<dynamic-class '%s' at %s>" % (self.name, hex(id(self)))
	__repr__ = __str__

class Packet(object):
	__metaclass__ = PacketMeta
	name = "Root Packet"

	def __init__(self, *arguments):
		self.structures = self.__class__.structures

		if len(arguments) < len(self.structures):
			raise ValueError("Not enough arguments given")
		
		arguments = list(arguments)
		
		# Check each argument is valid
		print arguments, self.structures
		for structure in self.structures:
			argument = arguments.pop(0)
			structure.check(argument)
			setattr(self, structure.name, argument)

	def xstruct(self):
		xstruct = ""
		for structure in self.structures:
			xstruct += structure.xstruct
		return xstruct
	xstruct = property(xstruct)
	
	def __str__(self):
		# FIXME: This won't work with a GroupStructure!
		arguments = []
		for structure in self.structures:
			arguments.append(getattr(self, structure.name))

		print self.xstruct, arguments
		return pack(self.xstruct, *arguments)

