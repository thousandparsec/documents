
import copy

from Packet import Packet
import Structures

VERSION = "TP03"

class Header(Packet):
	structures = [
		Structures.Character("version", "Protocol Version", size=4),
		Structures.Integer("sequence", "Sequence Number", size=32, type="unsigned"),
		Structures.Integer("type", "Packet Type", size=32, type="unsigned"),
		Structures.Integer("length", "Length of Packet", size=32, type="unsiged"),
	]

	def __init__(self, *arguments):
		if len(*arguments) == 0:
			# We are building a packet from the wire.
			raise NotImplimented("Not finished yet...")
		else:
			Packet.__init__(self, VERSION, arguments[0], self.__class__.typeno, self.length, *arguments[1:])
	
	def length(self):
		length = 0
		
		# Get the length of the packet
		for item in self.arguments:
			for i in xrange(0, len(self.structures)):
				length += self.structures[i].length(item)

		return length
	length = property(length)
