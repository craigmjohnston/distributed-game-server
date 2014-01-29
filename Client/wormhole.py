import sys
import math
import random

import config
import utility
import graphics

class Wormhole:
	def __init__(self, id, orbiting=None, distance=None, degree=None, speed=None, size=None, colour=None, name=None, position=None):
		self.id = id
		self.orbiting = orbiting
		self.distance = distance
		self.degree = degree
		self.speed = speed * 0.5 if speed is not None else None
		self.size = size
		self.colour = colour
		self.name = name
		self.rotation = 0
		
		if self.colour is not None:
			r, g, b, a = self.colour
			self.trail_colour = (r, g, b, 0.2)

		if self.orbiting is None and position is not None:
			self.x, self.y = position
		else:
			self.x, self.y = 0, 0

		if self.size is not None:
			self.draw()
			self.update_rect()

	def draw(self):
		self.vbo = graphics.spiral_vbo((0, 0), self.size, 5)

	def update_rect(self):
		self.rect = utility.Rect((self.x-self.size, self.y-self.size), (self.size*2, self.size*2))

	def get_pos(self):
		return (self.x, self.y)

	def collides_with_point(self, point):
		if self.size is not None:
			return self.rect.collides_with_point(point)
		return False

	def on_click(self, point, unclick_hooks):		
		#self.colour = (0, 0, 1.0, 1.0)
		pass	

	def update(self, delta):
		self.move(delta)
		self.rotation += config.WORMHOLE_SPIN_SPEED*delta

	def move(self, delta):
		if self.orbiting is not None:
			self.degree += self.speed*delta
			if self.speed > 0 and self.degree >= config.MAX_RAD: self.degree -= config.MAX_RAD
			elif self.speed < 0 and self.degree < 0: self.degree = config.MAX_RAD + self.degree
			self.x = self.orbiting.x + math.sin(self.degree)*self.distance
			self.y = self.orbiting.y + math.cos(self.degree)*self.distance
			self.update_rect()

	def render(self):
		if self.size is not None:
			if self.orbiting is not None: # orbit trail
				graphics.circle(self.orbiting.get_pos(), self.distance, self.trail_colour, 1)			
			graphics.draw_line_vbo(vbo=self.vbo, length=360*5, position=self.get_pos(), colour=self.colour, width=2, rotation=-math.degrees(self.rotation))