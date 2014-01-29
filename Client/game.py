import math

import yaml
import pygame
import gevent
from gevent import socket

import config
from config import MSG
import utility
from utility import Text
from player import Player
from planet import Planet
from asteroid import AsteroidCloud
from ship import Ship, Projectile
from wormhole import Wormhole
import network

class Game:
	def __init__(self, preferences=None, function="", username="", password=""):
		self.entities = []
		self.planets = []
		self.ships = []
		self.players = []
		self.projectiles = []
		self.player = Player(position=(config.SCREEN_WIDTH/2, 100), colour=utility.Colour(config.PLAYER_COLOUR).to_rgba_f(), projectile_pool=self.projectiles)

		self.function = function
		self.username = username
		self.password = password

		self.loading = True # is the loading screen showing?

		self.player_id = -1

		self.system_name = ""
		self.system_id = -1
		self.system_size = -1

		self.system_label = None

		self.server_sock = None

		self.last_server_frame = None

		self.keys = None
		self.init_key_config()
		self.unclick_hooks = [] # list of callbacks called on MOUSE1_UP
		self.init_ui()

	def init_key_config(self, preferences=None):
		# use the default key configuration...
		k_forward = config.KEY_FORWARD
		k_left = config.KEY_LEFT
		k_right = config.KEY_RIGHT
		k_fire = config.KEY_FIRE
		k_interact = config.KEY_INTERACT

		# ...unless a configuration exists in the preferences
		if preferences is not None and preferences.get('keys', None) is not None:
			k_forward = preferences['keys'].get('forward', k_forward)
			k_left = preferences['keys'].get('left', k_left)
			k_right = preferences['keys'].get('right', k_right)
			k_fire = preferences['keys'].get('fire', k_fire)
			k_interact = preferences['keys'].get('interact', k_fire)

		self.keys = {k_forward: Ship.INPUT.FORWARD,
					 k_left: Ship.INPUT.LEFT,
					 k_right: Ship.INPUT.RIGHT,
					 k_fire: Ship.INPUT.FIRE,
					 k_interact: Ship.INPUT.INTERACT}

	def init_ui(self): 
		self.system_label = Text("", config.FONT, utility.Colour(0xFFFFFFFF), (20, 20))

	def update_ui(self, delta):
		pass

	def render_ui(self):
		self.system_label.render()

	def update(self, delta):
		if self.server_sock is None:
			if not self.connect_to_server(self.function, self.username, self.password):
				return False
		if not self.loading:
			#self.update_ui(delta)
			for entity in self.entities:
				entity.update(delta)
			for player in self.players:
				player.update(delta)
			self.player.update(delta)
			for projectile in self.projectiles:
				projectile.update(delta)
		return True

	def render(self):
		if not self.loading:
			self.render_ui()
			for entity in self.entities:
				entity.render()
			for player in self.players:
				player.render()
			self.player.render()
			for projectile in self.projectiles:
				projectile.render()

	def logout(self):
		self.server_sock.send_message(MSG.CL_GW_LOGOUT)
		return True

	def connect_to_server(self, function, username, password):
		print "Connecting to server"
		self.server_sock = network.Socket()
		self.server_sock.connect(config.CLIENT_GATEWAY_ADDRESS)
		if function == "register":
			self.server_sock.send_message(MSG.CL_GW_REGISTER, [username, password])
			response = self.server_sock.wait_for_message([MSG.GW_CL_REGISTRATION_SUCCESSFUL, 
													  	  MSG.GW_CL_REGISTRATION_FAILED])
			if response.type == MSG.GW_CL_REGISTRATION_SUCCESSFUL:
				print "Registration successful"
			else:
				print "Registration failed"
				return False
		print "Logging in"
		self.server_sock.send_message(MSG.CL_GW_LOGIN, [username, password])
		response = self.server_sock.wait_for_message([MSG.GW_CL_LOGIN_FAILED, 
													  MSG.GW_CL_LOGIN_SUCCESSFUL])
		if response is None:
			print "Gateway closed connection" # TODO: raise error?
			return False # connection closed
		if response.type == MSG.GW_CL_LOGIN_SUCCESSFUL:
			print "Login successful"
			self.player_id = response.data	
			gevent.spawn(self.receive_server_input)
			return True # login succeeded
		print "Login failed"
		return False # login failed

	def receive_server_input(self):
		print "Receiving server input"
		while True:
			msg = self.server_sock.wait_for_message()
			if msg.type == config.MSG.GW_CL_SYSTEM_INFO:
				self.on_system_info(msg.data)
			elif msg.type == config.MSG.GW_CL_MOVING_SYSTEMS:
				self.on_moving_systems(msg.data)
			elif msg.type == config.MSG.GW_CL_FRAME:
				self.on_server_frame(msg.time, msg.data)

	def send_input(self, key, state):
		self.server_sock.send_message(config.MSG.CL_GW_INPUT, [key, state])

	def on_system_info(self, data):
		system_data = yaml.load(data)
		self.system_id = system_data['id']
		self.system_name = system_data['name']
		self.system_label.set_text(self.system_name)
		self.system_size = system_data['size']
		players = system_data['players']
		planets = system_data['planets']
		wormholes = system_data['wormholes']

		self.entities = []
		self.planets = []
		self.ships = []
		self.players = []
		self.projectiles = []

		# player position
		player = system_data['player']
		x, y = player['position']
		self.player.set_position(x, y)

		star = Planet(id=1, size=0, position=(config.SCREEN_WIDTH/2, config.SCREEN_HEIGHT/2), colour=utility.Colour(0xFFFFFFFF).to_rgba_f())
		self.planets.append(star)
		self.entities.append(star)
		for planet in planets:
			p = Planet(id=planet['id'], size=planet['size'], 
					   orbiting=star, distance=planet['distance'], 
					   speed=planet['speed'], degree=planet['degree'], 
					   colour=utility.Colour(planet['colour']).to_rgba_f())
			self.planets.append(p)
			self.entities.append(p)
		for wormhole in wormholes:
			w = Wormhole(id=wormhole['id'], size=config.WORMHOLE_SIZE, 
						 orbiting=star, distance=wormhole['distance'], 
						 speed=wormhole['speed'], degree=wormhole['degree'], 
						 colour=utility.Colour(config.WORMHOLE_COLOUR).to_rgba_f())
			self.entities.append(w)
		for player_id, name in players:
			self.players.append(Player(projectile_pool=self.projectiles,
									   colour=utility.Colour(config.ENEMY_COLOUR).to_rgba_f(), 
									   player_id=player_id, name=name))
		# turn the loading screen off
		self.loading = False

	def on_moving_systems(self, name):
		self.loading_screen(name)

	def loading_screen(self, system_name):
		self.loading = True

	def on_server_frame(self, time, data):
		if self.last_server_frame is None or time > self.last_server_frame:
			self.last_server_frame = time
			players, projectiles, new_players = data
			# new players
			if new_players and new_players != [None]:
				print "new player"
				for player_id, name in new_players:
					if player_id != self.player_id:
						self.players.append(Player(projectile_pool=self.projectiles,
												   colour=utility.Colour(config.ENEMY_COLOUR).to_rgba_f(), 
												   player_id=player_id, name=name))
			# players
			players_by_id = {pl_id: (pl_x, pl_y, pl_direction, pl_inputs, pl_destroyed, pl_respawn_in)
							 for pl_id, pl_x, pl_y, pl_direction, pl_inputs, pl_destroyed, pl_respawn_in
							 in players}
			for player in self.players:
				player.x, player.y, player.direction, player.inputs, player.destroyed, player.respawn_in = players_by_id[player.id]
			# projectiles
			if projectiles and projectiles != [None]:
				projectiles_by_id = {pr_id: (pr_x, pr_y, pr_direction, pr_player)
									 for pr_id, pr_x, pr_y, pr_direction, pr_player
									 in projectiles}
				for projectile in self.projectiles:
					if projectile.id not in projectiles_by_id:
						self.projectiles.remove(projectile)
					else:
						x, y, projectile.direction, player_id = projectiles_by_id[projectile.id]
						projectile.set_position(x, y)
						del projectiles_by_id[projectile.id]
				for pr_id, pr in projectiles_by_id.iteritems():
					x, y, direction, player_id = pr
					projectile = Projectile(pr_id, (x, y), config.PROJECTILE_SPEED, direction,
											utility.Colour(config.ENEMY_COLOUR if player_id != self.player_id else config.PLAYER_COLOUR).to_rgba_f())
					projectile.set_position(x, y)
					self.projectiles.append(projectile)
			# this player
			my_x, my_y, my_direction, my_inputs, my_destroyed, my_respawning_in = players_by_id[self.player_id]
			if my_destroyed and not self.player.destroyed:
				self.player.destroy(my_respawning_in)
				for planet in self.planets:
					print (planet.x, planet.y)
				print (self.player.x, self.player.y)
			elif self.player.destroyed and not my_destroyed:
				self.player.respawn(my_x, my_y)
			self.player.set_position(my_x, my_y)
			self.player.direction = my_direction

	def on_key(self, key, state):
		if key in config.VALID_KEYS: # only act on valid keys
			self.player.set_input(self.keys[key], state)
			self.send_input(self.keys[key], state)

	def on_click(self, position):
		pass

	def on_unclick(self, position):
		for hook in self.unclick_hooks:
			hook(position)
		self.unclick_hooks = []