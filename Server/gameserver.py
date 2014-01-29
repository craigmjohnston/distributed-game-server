import time
import math
import argparse
import random

import yaml
import gevent

import network
import config
from config import DBQUERY, MSG
from utility import enum, Rect

FRAME_RATE = 1.0/100 # length of a frame in seconds
DATABASE_FRAME_RATE = 4.0 # how often in seconds to commit to DB

PLAYER_SPEED = 100 # pixels/second
PLAYER_TURN_SPEED = math.radians(180) # radians/second
PLAYER_FIRE_RATE = 1.0/5 # per second

WORMHOLE_SIZE = 30
PROJECTILE_SIZE = 5
INTERACTION_AREA = 100

PROJECTILE_SPEED = 200 #pixels/second

INPUTS = enum('FORWARD', 'LEFT', 'RIGHT', 'FIRE', 'INTERACT')

PLAYER_SIZE = 5;

class Client:
	def __init__(self, client_socket=None, address=None, player=None):
		self.socket = client_socket
		self.address = address
		self.player = player

class OfflinePlayer:
	def __init__(self, player_id, name, x, y, solar_system):
		self.id = player_id
		self.name = name
		self.x = x
		self.y = y
		self.solar_system = solar_system

class Player:
	def __init__(self, client, id, name, solar_system, position, size, projectiles):
		self.client = client
		self.id = id
		self.name = name
		self.solar_system = solar_system
		self.x, self.y = position
		self.width, self.height = size
		self.rect = Rect(position, size)
		self.projectiles = projectiles # projectile pool
		self.direction = 0
		self.input = [False for i in range(5)] # forward, left, right, fire, interact
		self.last_fired = time.time()
		self.destroyed = False
		self.respawning_in = 0
		self.interacting = False
		self.interaction_point = None
		self.dirty = True

	@classmethod
	def from_offline(cls, offline_player, client, projectiles):
		player = Player(client, offline_player.id, offline_player.name, 
						offline_player.solar_system, (offline_player.x, offline_player.y), 
						(PLAYER_SIZE, PLAYER_SIZE), projectiles)
		client.player = player
		return player

	def get_pos(self):
		return (self.x, self.y)

	def send(self, message_type, *data):
		self.connection.send(message_type, *data)

	def set_input(self, key, state):
		self.input[key] = True if state == 1 else False

	def destroy(self):
		self.destroyed = True
		self.respawning_in = 5

	def respawn(self, x, y):
		self.destroyed = False
		print "respawn at: %i, %i" % (x, y) 
		self.x = x
		self.y = y

	def collides_with(self, entity):
		return self.rect.collides_with(entity.rect)

	def move(self, distance):
		self.x += math.sin(self.direction)*distance
		self.y += math.cos(self.direction)*distance
		self.rect.update_position(self.x, self.y)

	def rotate(self, angle):
		self.direction += angle

	def fire(self):
		if time.time() - self.last_fired > PLAYER_FIRE_RATE:
			self.last_fired = time.time()
			print self.get_pos()
			self.projectiles.append(Projectile(self.get_pos(), 
									(PROJECTILE_SIZE, PROJECTILE_SIZE), 
									self.direction, PROJECTILE_SPEED,
									self, self.solar_system.projectile_id_counter))
			self.solar_system.projectile_id_counter += 1

	def update(self, delta):
		if self.destroyed:
			# if the player has been destroyed, count down and then respawn
			self.respawning_in -= delta
			if self.respawning_in <= 0:
				self.respawning_in = 0
				size = self.solar_system.size
				self.respawn(random.randint(0, size*2)-size, 
							 random.randint(0, size*2)-size)
		else:			
			forward, left, right, fire, interact = self.input			
			if interact and not self.interacting:
				self.interacting = True
				self.interaction_area = Rect((self.x - INTERACTION_AREA/2, self.y - INTERACTION_AREA/2), (INTERACTION_AREA, INTERACTION_AREA))
			# if the player is still in play, act according to their inputs			
			if forward:
				self.move(PLAYER_SPEED*delta)
				self.dirty = True
			if left:
				self.rotate(-PLAYER_TURN_SPEED*delta)				
			elif right:
				self.rotate(PLAYER_TURN_SPEED*delta)
			if fire:
				self.fire()


class Projectile:
	def __init__(self, position, size, direction, speed, player, projectile_id):
		self.x, self.y = position
		self.width, self.height = size
		self.rect = Rect(position, size)
		self.direction = direction
		self.speed = speed
		self.player = player
		self.id = projectile_id
		self.alive_for = 0
		self.destroyed = False

	def move(self, distance):
		self.x += math.sin(self.direction)*distance
		self.y += math.cos(self.direction)*distance

	def update(self, delta):
		self.move(self.speed*delta)
		self.alive_for += delta
		if self.alive_for >= config.PROJECTILE_LIFE:
			self.destroy()

	def destroy(self):
		self.destroyed = True

	def collides_with(self, entity):
		return self.rect.collides_with(entity.rect)


class SolarSystemEntity:
	def __init__(self, id, orbiting=None, distance=None, speed=None, degree=0, position=None):
		self.id = id
		self.orbiting = orbiting
		self.distance = distance
		self.speed = speed
		self.degree = degree
		if self.orbiting is None and position is not None:
			self.x, self.y = position
		elif self.orbiting is None:
			self.x, self.y = 0, 0
		else:
			self.set_position()

	def update(self, delta):
		if self.orbiting is not None:
			self.degree += self.speed*delta
			if self.speed > 0 and self.degree >= config.MAX_RAD: self.degree -= config.MAX_RAD
			elif self.speed < 0 and self.degree < 0: self.degree = config.MAX_RAD + self.degree
			self.set_position()

	def set_position(self):
		if self.orbiting is not None:
			self.x = self.orbiting.x + math.sin(self.degree)*self.distance
			self.y = self.orbiting.y + math.cos(self.degree)*self.distance

	def __eq__(self, other):
		if not isinstance(other, SolarSystemEntity):
			return False
		return self.id == other.id

class Planet(SolarSystemEntity):
	def __init__(self, id, orbiting=None, distance=None, speed=None, degree=0, position=None, name="", size=0, colour=0):
		self.name = name
		self.size = size
		self.colour = colour
		self.rect = Rect((0, 0), (self.size*2, self.size*2))
		SolarSystemEntity.__init__(self, id, orbiting, distance, speed, degree, position)		

	def set_position(self):
		SolarSystemEntity.set_position(self)
		self.rect.update_position(self.x-self.size, self.y-self.size)

class WormholeMouth(SolarSystemEntity):
	def __init__(self, id, orbiting=None, distance=None, speed=None, degree=0, position=None, origin=None, destination=None):
		self.origin = origin
		self.destination = destination
		self.rect = Rect((0, 0), (WORMHOLE_SIZE*2, WORMHOLE_SIZE*2))
		SolarSystemEntity.__init__(self, id, orbiting, distance, speed, degree, position)		

	def set_position(self):
		SolarSystemEntity.set_position(self)
		self.rect.update_position(self.x-WORMHOLE_SIZE, self.y-WORMHOLE_SIZE)

class SolarSystem:
	def __init__(self, id, name):
		self.id = id
		self.name = name

	def add_player(self, player):
		raise NotImplementedError()

	def remove_player(self, player):
		raise NotImplementedError()

class RemoteSolarSystem(SolarSystem):
	"""Represents a solar system hosted on another server."""
	def __init__(self, id, name, server, manager):
		SolarSystem.__init__(self, id, name)
		self.server = server
		self.manager = manager

	def receive_player(self, player, origin_system):
		self.server.send_player(player.id, player.name, self.id, origin_system.id)
		manager.move_player(player, self.server, self)

class LocalSolarSystem(SolarSystem):
	"""Represents a solar system hosted on this server."""
	def __init__(self, id, name, size, manager):
		SolarSystem.__init__(self, id, name)
		self.size = size
		self.manager = manager
		self.players = []
		self.entities = []
		self.wormhole_mouths = []
		self.planets = []
		self.projectiles = []
		self.destroyed = []
		self.pivot = SolarSystemEntity(-1, position=(0, 0))
		self.new_players = []
		self.projectile_id_counter = 0
		self.dirty_players = []

	def get_updates_for_db(self):
		return None

	def add_planet(self, planet):
		self.entities.append(planet)
		self.planets.append(planet)

	def add_wormhole(self, wormhole):
		self.entities.append(wormhole)
		self.wormhole_mouths.append(wormhole)

	def receive_player(self, player, origin_system):
		wormhole = None
		for w in self.wormhole_mouths:
			if w.destination.id == origin_system.id:
				wormhole = w		
		self.add_player(player, (wormhole.x, wormhole.y))

	def remove_player(self, player):
		print "Player removed from solar system %i" % self.id
		self.players.remove(player)

	def add_player(self, player, position): # TODO: do this better
		print "Player added to solar system %i" % self.id
		self.manager.send_map_info(self, player)
		new_player = Player(player.client, player.id, player.name, 
							self, position, (player.width, player.height), 
							self.projectiles)
		player.client.player = new_player
		self.players.append(new_player)
		self.new_players.append(new_player)
		return True

	def update(self, delta):
		# update entities, players and projectiles
		for entity in self.entities:
			entity.update(delta)
		for player in self.players:
			player.update(delta)
			if player.dirty and player not in self.dirty_players:
				self.dirty_players.append(player)
			player.dirty = False
		for projectile in self.projectiles:
			projectile.update(delta)
		# send the player through a wormhole if they interact with it
		for player in (player for player in self.players if not player.destroyed):
			if player.interacting: 
				for wormhole in self.wormhole_mouths:
					if player.interaction_area.collides_with(wormhole.rect):
						self.send_player_to_system(player, wormhole.destination)
						break
				player.interacting = False
				player.interaction_area = None
		# clean up destroyed projectiles
		for projectile in self.projectiles:
			if projectile.destroyed:
				self.projectiles.remove(projectile)
		self.send_frame()

	def collisions(self):
		# destroy any players or projectiles colliding with planets
		for planet in self.planets:			
			for player in (player for player in self.players if not player.destroyed):
				if player.collides_with(planet):
					player.destroy()
					print "player destroyed"
					print player.get_pos(), (planet.x, planet.y)
					self.destroyed.append(player)
			for projectile in self.projectiles:
				if projectile.collides_with(planet):
					self.projectiles.remove(projectile)
					self.destroyed.append(projectile)
		# destroy any players and projectiles colliding with each other
		for projectile in self.projectiles:
			for player in (player for player in self.players if not player.destroyed 
						   and not player == projectile.player):
				if projectile.collides_with(player):
					self.projectiles.remove(projectile)
					player.destroy()
					self.destroyed.extend([player, projectile])

	def send_frame(self):		
		player_data = [[pl.id, pl.x, pl.y, pl.direction, pl.input, pl.destroyed, pl.respawning_in] 
					   for pl in self.players]		
		projectile_data = [[pr.id, pr.x, pr.y, pr.direction, pr.player.id]
						   for pr in self.projectiles]
		new_players = [[pl.id, pl.name] for pl in self.new_players]
		self.new_players = []
		frame_data = [player_data, projectile_data, new_players]
		for player in self.players:
			player.client.socket.send_message(MSG.GW_CL_FRAME, frame_data)

	def send_player_to_system(self, player, system):
		self.players.remove(player)
		player.client.socket.send_message(MSG.GW_CL_MOVING_SYSTEMS, system.name)
		system.receive_player(player, self)

	def get_updates_for_db(self):		
		dirty = [[player.id, player.x, player.y, self.id] for player in self.dirty_players if player in self.players]
		self.dirty_players = []
		return dirty

class Server:
	def __init__(self, server_id=-1, server_socket=None, address=None, systems=None, alpha=True):
		self.id = server_id
		self.socket = server_socket
		self.address = address
		self.systems = systems
		self.alpha = alpha

	def send_player(self, player_id, player_name, destination_system_id, origin_system_id):
		self.socket.send_message(MSG.GS_GS_SENDPLAYER, [player_id, player_name, 
														destination_system_id, 
														origin_system_id])

class Manager:
	def __init__(self):
		self.servers = []
		self.servers_by_system = {}
		self.solar_systems = []
		self.solar_systems_by_id = {} # including edge systems
		self.players = []
		self.players_by_id = {}
		self.last_frame = -1
		self.last_db_frame = -1
		# sockets
		self.gateway_sock = None
		self.database_sock = None

	def begin(self, client_port, server_port):
		# start listening for peer connections
		self.alpha_servers = []
		server_greenlet = gevent.spawn(self.wait_for_other_servers, server_port)
		# connect to the gateway server
		print "Connecting to gateway"
		self.gateway_sock = network.Socket()
		self.gateway_sock.connect(config.SERVER_GATEWAY_ADDRESS)
		# let the gateway know our available ports
		self.gateway_sock.send_message(MSG.GS_GW_CONNECT_INFO, [client_port, server_port])
		print "Waiting for startup data"
		msg = self.gateway_sock.wait_for_message(MSG.GW_GS_SOLARINFO)
		if msg is None:
			print "Gateway closed connection"
			return
		systems, neighbours = msg.data
		print systems, neighbours
		# connect to all our neighbouring servers
		# build neighbour servers
		edge_systems = []
		servers = []
		if neighbours and neighbours != [None]:
			for n_id, n_address, n_edge_systems, n_beta in neighbours:
				server = Server(server_id=n_id, address=n_address, alpha=not n_beta)
				servers.append(server)
				edge_systems.extend(n_edge_systems)
				for system in n_edge_systems:
					self.servers_by_system[system] = server
				if n_beta:
					# connect to the server
					print "Connecting to neighbour (Server %i)" % n_id
					server_socket = network.Socket()
					server_socket.connect(n_address)
					server.socket = server_socket
				else:
					self.alpha_servers.append(server)
		self.servers = servers
		if not self.alpha_servers:
			self.alpha_servers = None
		else:
			server_greenlet.join() # wait until we're connected to all of our neighbours
		print "Connected to all neighbours"
		for server in self.servers:
			gevent.spawn(self.receive_server_input, server)
		print edge_systems
		print servers
		# connect to the database and get solar data
		print "Connecting to database"
		self.database_sock = network.Socket()
		self.database_sock.connect(config.SERVER_DATABASE_ADDRESS)
		self.database_sock.send_message(MSG.DB_QUERY, [DBQUERY.GS_SYSTEMSINFO, [systems, edge_systems]])
		print "Waiting for solar system data"
		msg = self.database_sock.wait_for_message(MSG.DB_RESPONSE)
		if msg is None:
			print "Database closed connection"
			return
		query_id, solar_data = msg.data
		# build the solar systems
		print "Building solar systems"		
		self.build_systems(solar_data)
		# begin accepting client connections
		client_greenlet = gevent.spawn(self.accept_client_connections, client_port)
		# begin processing
		print "Running game server"
		self.last_frame = time.time()
		self.last_db_frame = time.time()
		run_greenlet = gevent.spawn(self.run)
		# send ready signal
		print "Notifying gateway of readiness"
		gateway_greenlet = gevent.spawn(self.receive_gateway_input)
		self.gateway_sock.send_message(MSG.GS_GW_READY)		
		# join the greenlets
		gevent.joinall([client_greenlet, run_greenlet, gateway_greenlet])

	def wait_for_other_servers(self, server_port):
		server_sock = network.Socket()
		server_sock.bind(('127.0.0.1', server_port))
		server_sock.listen(config.SOCKET_CLIENT_MAX_QUEUE)
		early_sockets = []
		while self.alpha_servers is not None: # TODO: this is a mess
			# add any servers that connected early
			if self.alpha_servers and early_sockets:
				for sock, address in early_sockets:
					for server in self.alpha_servers:
						if server.address[0] == address[0]:
							server.address = address
							server.socket = sock
							early_sockets.remove((sock, address))
							self.alpha_servers.remove(server)
							if not self.alpha_servers:
								return
							break
			sock, address = server_sock.accept()
			if self.alpha_servers:
				for server in self.alpha_servers:
					if server.address[0] == address[0]:
						server.address = address
						server.socket = sock
						self.alpha_servers.remove(server)
						if not self.alpha_servers:
							return
						break
			else:
				early_sockets.append((sock, address))

	def receive_gateway_input(self):
		while True:
			msg = self.gateway_sock.wait_for_message()
			if msg is None:
				print "Gateway has disconnected"
				break # TODO: commit to DB
			if msg.type == MSG.GW_GS_NEWPLAYER:
				player_id, username, system_id, x, y = msg.data
				offline_player = OfflinePlayer(player_id, username, 
											   x, y, 
											   self.systems_by_id[system_id])
				self.players.append(offline_player)
				self.players_by_id[player_id] = offline_player

	def receive_server_input(self, server):
		while True:
			msg = server.socket.wait_for_message()
			if msg.type == MSG.GS_GS_SENDPLAYER:
				player_id, player_name, destination_system_id, origin_system_id = msg.data
				system = self.systems_by_id[destination_system_id]
				wormhole = None
				for w in system.wormhole_mouths:
					if w.destination.id == origin_system_id:
						wormhole = w
						break
				offline_player = OfflinePlayer(player_id, player_name, 
											   wormhole.x, wormhole.y, system)
				self.players.append(offline_player)
				self.players_by_id[player_id] = offline_player

	def move_player(self, player, server, system):
		self.gateway_sock.send_message(MSG.GS_GW_MOVEPLAYER, [player.id, server.id, system.id])
		offline_player = self.players_by_id[player.id]
		player.client.socket.close()
		self.players.remove(offline_player)
		del self.players_by_id[player.id]

	def accept_client_connections(self, port):
		client_id_counter = 0
		client_sock = network.Socket()
		client_sock.bind(('127.0.0.1', port))
		client_sock.listen(config.SOCKET_CLIENT_MAX_QUEUE)
		print "Accepting client connections"
		while True:
			c_sock, address = client_sock.accept()
			print "Client " + str(client_id_counter) + " connected"
			client = Client(c_sock, address)
			client.id = client_id_counter
			gevent.spawn(self.receive_client_input, client)
			client_id_counter += 1

	def receive_client_input(self, client):
		while True:
			if client.player is None:
				msg = client.socket.wait_for_message(MSG.GW_GS_NEWPLAYER)
				if msg is None:
					break
				player_id = msg.data
				offline_player = self.players_by_id[player_id]
				system = offline_player.solar_system
				player = Player.from_offline(offline_player, client, system.projectiles)
				client.player = player				
				system.add_player(player, player.get_pos())
			else:
				msg = client.socket.wait_for_message()
				if msg is None:
					"Client " + str(client.id) + " disconnected incorrectly"
					break
				if msg.type == MSG.CL_GW_INPUT:
					key, state = msg.data
					client.player.set_input(key, state)
				elif msg.type == MSG.CL_GW_LOGOUT:
					client.player.solar_system.remove_player(client.player)
					client.socket.close()
					print "Client %i logged out" % client.id
					break

	# TODO: this isn't used anymore
	def handle_client_message(self, msg, client):
		if msg.type == network.MSG.CL_GW_LOGOUT: # log the client out
			client.connected = False
			# remove the player from the game world
			if client.player is not None: # TODO: this isn't going to work
				self.players.remove(client.player)
			# close the socket
			client.sock.shutdown()
			client.sock.close()
		elif msg.type == network.MSG.CL_GW_INPUT:
			pass # handle input

	def run(self):		
		while True:
			delta = time.time() - self.last_frame
			if delta >= FRAME_RATE:
				self.last_frame += delta
				for solar_system in self.solar_systems:
					solar_system.update(delta)
			db_delta = time.time() - self.last_db_frame
			if db_delta >= DATABASE_FRAME_RATE:
				# update database every DB frame
				self.last_db_frame += db_delta
				dirty_players = []
				for solar_system in self.solar_systems:
					dirty_players.extend(solar_system.get_updates_for_db())
				if dirty_players:
					self.database_sock.send_message(MSG.DB_QUERY, 
													[DBQUERY.GS_UPDATE, dirty_players])
			gevent.sleep()

	def build_systems(self, data):
		solar_system_data, edge_system_data, wormhole_data, planet_data, player_data = data

		# build local solar systems
		self.solar_systems = [LocalSolarSystem(s_id, s_name, s_size, self) 
				   		 	  for s_id, s_name, s_size in solar_system_data]
		self.systems_by_id = {system.id: system for system in self.solar_systems}
		# planets
		for (p_id, p_size, p_colour, p_name, p_orbit_radius, p_orbit_speed, 
			 p_system_id) in planet_data:
			system = self.systems_by_id[p_system_id]
			system.add_planet(Planet(p_id, orbiting=system.pivot, 
										 distance=p_orbit_radius, 
										 speed=p_orbit_speed,
										 name=p_name, size=p_size, colour=p_colour))
		# build remote solar systems
		if edge_system_data and edge_system_data != [None]:
			edge_systems = []
			for s_id, s_name in edge_system_data:
				system = RemoteSolarSystem(s_id, s_name, self.servers_by_system[s_id], self)
				self.systems_by_id[s_id] = system
				edge_systems.append(system)
		else:
			edge_systems = []
		# wormholes
		local_wormholes, edge_wormholes = wormhole_data
		wormholes_by_id = {}
		# w_id: id of wormhole mouth, w_wid: id of connecting wormhole
		for w_system, w_orbit_radius, w_orbit_speed, w_id, w_wid in local_wormholes:
			system = self.systems_by_id[w_system]
			if w_wid not in wormholes_by_id:
				wormholes_by_id[w_wid] = []	
			if self.systems_by_id[w_system] not in edge_systems:
				wormhole = WormholeMouth(w_id, orbiting=system.pivot, 
										 distance=w_orbit_radius, 
							  			 speed=w_orbit_speed, origin=system)
				wormholes_by_id[w_wid].append(wormhole)
			else:
				wormhole = WormholeMouth(w_id, origin=system)
				wormholes_by_id[w_wid].append(wormhole)			
			if len(wormholes_by_id[w_wid]) > 1:
				other = wormholes_by_id[w_wid][0] if wormholes_by_id[w_wid][0] != wormhole else wormhole
				other.destination = system
				wormhole.destination = other.origin
		for w_system, w_orbit_radius, w_orbit_speed, w_id, w_wid in edge_wormholes:
			if w_wid in wormholes_by_id:
				wormholes_by_id[w_wid][0].destination = self.systems_by_id[w_system]
		for w_id, wormhole in wormholes_by_id.iteritems():
			for mouth in wormhole:
				mouth.origin.add_wormhole(mouth)
		# player data
		if player_data and player_data != [None]:
			self.players = [OfflinePlayer(p_id, p_name, p_x, p_y, self.systems_by_id[p_system])
					   		for p_id, p_name, p_x, p_y, p_system in player_data]
			self.players_by_id = {player.id: player for player in self.players}

	def send_map_info(self, solar_system, player):
		"""Send a YAML dump of the data for a solar system to a player.

		solar_system 	LocalSolarSystem object to pull data from
		player 			Player object to send through
		"""
		data = {'id': solar_system.id, 
				'name': solar_system.name, 
				'size': solar_system.size,
				'player' : {'position': player.get_pos()},
				'planets': [{'id': planet.id,
							 'distance': planet.distance,
							 'speed': planet.speed, 
							 'degree': planet.degree, 
							 'name': planet.name, 
							 'size': planet.size, 
							 'colour': planet.colour} 
							for planet in solar_system.planets],
				'wormholes': [{'id': wormhole.id,
							   'distance': wormhole.distance, 
							   'speed': wormhole.speed, 
							   'degree': wormhole.degree,
							   'destination': wormhole.destination.name}
							  for wormhole in solar_system.wormhole_mouths],
				'players': [{'id': other_player.id,
							 'name': other_player.name}
							for other_player in solar_system.players]
			   }
		player.client.socket.send_message(MSG.GW_CL_SYSTEM_INFO, yaml.dump(data))

"""
Start the gameserver up
"""
# parse command-line arguments
parser = argparse.ArgumentParser(
	description='Gameserver')
parser.add_argument('client', metavar='client', type=int, 
	help='Port for clients to connect on')
parser.add_argument('server', metavar='server', type=int, 
	help='Port for servers to connect on')
args = parser.parse_args()

manager = Manager()
manager.begin(args.client, args.server)