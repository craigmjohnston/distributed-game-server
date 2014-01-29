import gevent
from gevent import socket

import time
import math

import config
from utility import enum

def convert_to_base_n(intval, base):
	"""Converts an integer to a specified base, returning the new number as
	an iterator of its symbols.

	"""
	column = intval	
	base = float(base) # need to do float arithmetic
	output = []
	while column > base:
		column /= base
		output.append(int((column - math.floor(column))*base))
	output.append(int(column))
	return reversed(output)

def int_to_ascii(intval):
	"""Packs an integer into the smallest ascii string possible"""
	ascii = ""
	if intval < 0:
		intval *= -1
		ascii += chr(config.NEGATIVE_CHAR)
	basen = convert_to_base_n(intval, 127)	
	for column in basen:
		ascii += chr(column+128)
	return ascii

def ascii_to_int(ascii):
	negative = False
	if ascii[0] == chr(config.NEGATIVE_CHAR):
		ascii = ascii[1:]
		negative = True
	cols = [ord(char)-128 for char in reversed(ascii)]
	total = 0
	for i in range(len(cols)):
		total += cols[i] * 127**i
	total *= -1 if negative else 1
	return total

def parse_data(string, level=0):
	if len(string) == 0:		
		return None
	if string[0] == "i":
		return ascii_to_int(string[1:])
	elif string[0] == "f":
		return float(string[1:])
	elif string[0] == "l" or string[0] == "t":
		out = []
		for var in string[1:].split(chr(config.MSG_TOP_DELIMITER+level)):
			varout = parse_data(var, level+1)			
			out.append(varout)		
		return out if string[0] == "l" else tuple(out)
	elif string[0] == "s":
		return string[1:]
	elif string[0] == "n":		
		return None
	return None

def package_data(data, level=0):
	if data is None:
		return "n"
	if isinstance(data, (list, tuple)):		
			out = "l" if isinstance(data, list) else "t"
			for i in range(len(data)):
				packaged = package_data(data[i], level+1)
				if packaged is not None:
					if i > 0:
						out += chr(config.MSG_TOP_DELIMITER+level)				
					out += packaged			
			return out
	elif isinstance(data, (int, long)):
		return "i" + int_to_ascii(data)
	elif isinstance(data, float):
		return "f" + str(data)
	elif isinstance(data, basestring):
		return "s" + data
	else:
		raise TypeError("Can't package: \"" + str(data) + "\" - can only package lists, tuples, ints, floats, and strings.")
	

class Socket:
	def __init__(self, sock=None, address=None):
		self.socket = socket.socket() if sock is None else sock
		self.address = address
		self.msg_id_counter = 0
		self.start_time = time.time()
		self.ignored_messages = []
		self.leftover = ""

	def send_message(self, msg_type, data=None):
		msg_time = round((time.time()-self.start_time), config.MSG_TIME_ACCURACY)
		msg = Message(time=msg_time, msg_id=self.msg_id_counter, 
					  msg_type=msg_type, data=data)
		self.msg_id_counter += 1
		self.socket.send(msg.package())
		return msg

	def check_ignored_messages(self, msg_type=None):
		try:
			return (msg for msg in self.ignored_messages 
					if msg_type is None 
					or msg.type == msg_type).next()
		except StopIteration:
			return None

	def ignore_message(self, msg):
		self.ignored_messages.append(msg)

	def wait_for_message(self, msg_type=None):
		msg = self.check_ignored_messages(msg_type)
		if msg is not None: 
			return msg
		while True:
			msg = self.get_next_message()
			if msg is None:
				return None
			print "Message (id: %i, type: %i, from: (%s, %i))" % (msg.id, msg.type, self.address[0], self.address[1])
			if (msg_type is None 
				or (isinstance(msg_type, (list, tuple)) and msg.type in msg_type) 
				or msg.type == msg_type): 
				return msg
			self.ignore_message(msg)

	def get_next_message(self):
		data = self.leftover
		while data.find(config.MSG_END_CHAR) == -1:
			try:
				data += self.socket.recv(config.SOCKET_RECV_MAX_BYTES)
			except IOError:
				return None
		self.leftover = data[data.find(config.MSG_END_CHAR)+1:]		
		data = data[:-(len(self.leftover)+1)]
		return Message.from_string(data)

	def connect(self, address):
		self.address = address
		return self.socket.connect(address)

	def bind(self, address):
		return self.socket.bind(address)

	def listen(self, queue):
		return self.socket.listen(queue)

	def accept(self):
		sock, address = self.socket.accept()
		return Socket(sock=sock, address=address), address

	def recv(self):
		try:
			return self.socket.recv(config.SOCKET_RECV_MAX_BYTES)
		except IOError:
			return None

	def send(self, data):
		self.socket.send(data)

	def close(self):
		self.socket.shutdown(socket.SHUT_RDWR)
		self.socket.close()


class Message:
	def __init__(self, time=None, msg_id=None, msg_type=None, data=None):
		self.time = time
		self.id = msg_id
		self.type = msg_type
		self.data = data
		self.packaged = None

	@classmethod
	def from_string(cls, string):
		msg = Message()
		parsed = parse_data(string)
		msg.time, msg.id, msg.type, msg.data = parsed
		msg.packaged = string
		return msg

	def package(self):
		if self.time is None:
			self.time = time.time()
		self.packaged = package_data([self.time, self.id, self.type, self.data]) + config.MSG_END_CHAR
		return self.packaged