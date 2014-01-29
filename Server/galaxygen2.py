import sqlite3
import random	

def generate_galaxy():
	systems = [System() for x in range(200)]
	for system in systems:
		for i in range(3):
			system.planets.append(Planet())
	return systems

class System:
	def __init__(self, name="", planets=[], connections=[], size=0, 
				 wormhole_distances=[], wormhole_speeds=[]):
		self.planets = planets

class Planet:
	def __init__(self, name="", size=0, margin=0, distance=0, colour=None):
		self.name = name
		self.size = size
		self.colour = colour
		self.margin = margin
		self.distance = distance
		self.speed = 0


class Wormhole:
	def __init__(self):
		self.system_a_id = 0
		self.system_b_id = 0
		self.a_distance = 0
		self.a_speed = 0
		self.b_distance = 0
		self.b_speed = 0

"""
This is the start of the actual script which calls the generation function
and commits the results to an sqlite3 database
"""

gsystems = generate_galaxy()

planet_count = 0

for system in gsystems:
	planet_count += len(system.planets)	
print planet_count
print len(gsystems)