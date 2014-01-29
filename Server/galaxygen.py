import random
import math

STARNAMES = []
ROMAN_NUMERAL = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
MIN_MARGIN = 1 # 1 pixel either side of a planet
MINIMUM_DISTANCE = 100
PLANET_MASS = 2000000.0
G = 1.2*(10**-4)

def generate_system(system=None, min_planets=-1, max_planets=-1,
					min_system_size=-1, max_system_size=-1, 
					min_planet_size=-1, max_planet_size=-1, wormhole_size=-1,
					min_planet_speed=-1, max_planet_speed=-1, 
					min_wormhole_speed=-1, max_wormhole_speed=-1):
	# choose a name	
	system.name = random.choice(STARNAMES)
	STARNAMES.remove(system.name)
	# generate system
	planet_count = random.randint(min_planets, max_planets)	
	system.size = random.randint(min_system_size, max_system_size)
	available_radius = system.size - wormhole_size*len(system.connections)*2

	for i in range(planet_count):		
		size = random.randint(min_planet_size, max_planet_size)
		colour = (random.randint(0x0, 0xFFFFFF) * 0x100) + 0xFF # prepare for awful colour clashing!
		name = system.name + " " + ROMAN_NUMERAL[i]
		available_margin = (available_radius 
							- ((max_planet_size+MIN_MARGIN)*(planet_count-i)
								+ size))
		if available_margin != MIN_MARGIN*2:
			margin = random.randint(MIN_MARGIN*2, available_margin)
		else:
			margin = available_margin
		available_radius -= margin + size
		planet = Planet(name, size, margin, colour=colour)		
		system.planets.append(planet)
	#print len(system.planets)
	# position the planets and wormholes
	wormhole_positions = random.sample(range(planet_count+1), len(system.connections))
	wormhole_speeds = [0 for i in range(len(system.connections))]
	i = 0
	last_position = MINIMUM_DISTANCE
	for planet in system.planets:
		while i in wormhole_positions:
			wormhole_index = wormhole_positions.index(i)
			wormhole_positions[wormhole_index] = last_position
			wormhole_speeds[wormhole_index] = distance_to_speed(last_position, PLANET_MASS) * ( 1 if bool(random.getrandbits(1)) else -1)
			last_position += wormhole_size*2
			i += 1
		planet.distance = last_position + planet.margin/2
		planet.speed = distance_to_speed(planet.distance, PLANET_MASS) * ( 1 if bool(random.getrandbits(1)) else -1)
		last_position += planet.margin + planet.size
		i += 1
	star = Planet(system.name, random.randint(20, 40), 0, colour=0xFFE545FF)
	star.distance = 0
	star.speed = 0
	system.planets.append(star)
	system.wormhole_distances = wormhole_positions
	system.wormhole_speeds = wormhole_speeds

def distance_to_speed(distance, mass):
	return math.sqrt(G*mass)/float(distance+MINIMUM_DISTANCE)

def generate_galaxy(min_systems=0, max_systems=0, min_connections=0,
			 		max_connections=0, min_planets=0, max_planets=0,
			 		min_system_size=0, max_system_size=0,
			 		min_planet_size=0, max_planet_size=0, wormhole_size=0,
			 		min_planet_speed=0, max_planet_speed=0, min_wormhole_speed=0,
			 		max_wormhole_speed=0, 
			 		seed=None):
	global STARNAMES
	STARNAMES = open("res/starnames.txt").read().splitlines()
	random.seed(seed)
	system_count = random.randint(min_systems, max_systems)
	systems = [System() for i in range(system_count)]
	# connect all of the systems
	for system in systems:
		connections = random.randint(min_connections, max_connections)
		for i in range(connections):
			for other in systems:
				if (other != system and len(other.connections) < max_connections 
					and other not in system.connections):
					system.connections.append(other)
					other.connections.append(system)
					break
	# TODO: make sure galaxy is connected completely
	# generate the specifics of the systems (size, planets, etc.)
	for system in systems:
		generate_system(system=system, min_planets=min_planets, max_planets=max_planets, 
						min_system_size=min_system_size, max_system_size=max_system_size,
						min_planet_size=min_planet_size, max_planet_size=max_planet_size, wormhole_size=wormhole_size,
						min_planet_speed=min_planet_speed, max_planet_speed=max_planet_speed, 
						min_wormhole_speed=min_wormhole_speed, max_wormhole_speed=max_wormhole_speed)
	return systems


class System:
	def __init__(self, name="", planets=None, connections=None, size=0, 
				 wormhole_distances=None, wormhole_speeds=None):
		self.name = name
		self.planets = [] if planets is None else planets
		self.connections = [] if connections is None else connections
		self.size = size
		self.wormhole_distances = [] if wormhole_distances is None else wormhole_distances
		self.wormhole_speeds = [] if wormhole_speeds is None else wormhole_speeds
		self.system_id = 0

	def __eq__(self, other):
		if not isinstance(other, System):
			return False
		return self.name == other.name


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