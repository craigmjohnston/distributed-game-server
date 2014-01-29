import sys
import math
import random

import config
import utility
import graphics

# debug
SPEED = 100
ROTATE_SPEED = math.radians(180)
PROJECTILE_LENGTH = 5
FIRING_DELAY = 1.0/5

class Ship:
	INPUT = utility.enum('FORWARD', 'LEFT', 'RIGHT', 'FIRE', 'INTERACT') #TODO: move to config?

	def __init__(self, position=None, colour=None, projectile_pool=None):
		self.x, self.y = position if position is not None else (0,0)
		self.colour = colour
		self.projectile_pool = projectile_pool
		self.direction = 0
		self.speed = SPEED
		self.rotate_speed = ROTATE_SPEED
		self.input = [False for i in range(len(Ship.INPUT.reverse_mapping))]
		self.lastfired = 0
		self.draw()

	def set_position(self, x, y):
		self.x = config.SCREEN_WIDTH / 2 + x
		self.y = config.SCREEN_HEIGHT / 2 + y

	def draw(self):
		self.vbo = graphics.arrowhead_vbo((0, 0), 5)

	def update(self, delta):
		self.lastfired += delta

		if self.input[Ship.INPUT.FORWARD]:
			self.move(self.speed*delta)
		if self.input[Ship.INPUT.LEFT]:
			self.rotate(-self.rotate_speed*delta)
		elif self.input[Ship.INPUT.RIGHT]:
			self.rotate(self.rotate_speed*delta)
		if self.input[Ship.INPUT.FIRE]:
			pass#self.fire()			

	def render(self):
		graphics.draw_line_vbo(vbo=self.vbo, length=3, position=(self.x, self.y), colour=self.colour, width=2, rotation=math.degrees(self.direction))

	def fire(self):
		if self.lastfired >= FIRING_DELAY:
			self.projectile_pool.append(Projectile((self.x, self.y), self.direction, config.PROJECTILE_SPEED, self.colour))
			self.lastfired = 0

	def move(self, distance):
		self.x += math.sin(self.direction)*distance
		self.y += math.cos(self.direction)*distance

	def rotate(self, angle):
		self.direction += angle

	def set_input(self, key, state):
		self.input[key] = state

class Projectile:
	def __init__(self, projectile_id, position, direction, speed, colour):
		self.id = projectile_id
		self.x, self.y = position
		self.direction = direction
		self.speed = speed
		self.colour = colour
		self.draw()

	def draw(self):
		self.vbo = graphics.line_vbo((0, 0), (0, PROJECTILE_LENGTH))

	def render(self):
		graphics.draw_line_vbo(vbo=self.vbo, length=2, position=(self.x, self.y), colour=self.colour, width=3, rotation=math.degrees(self.direction))

	def update(self, delta):
		self.move(self.speed*delta)

	def move(self, distance):
		self.x += math.sin(self.direction)*distance
		self.y += math.cos(self.direction)*distance

	def set_position(self, x, y):
		self.x = config.SCREEN_WIDTH / 2 + x
		self.y = config.SCREEN_HEIGHT / 2 + y