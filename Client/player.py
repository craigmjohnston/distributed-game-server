import config
from ship import Ship

class Player(Ship):
	def __init__(self, position=None, colour=None, 
				 projectile_pool=None, player_id=-1, name=""):
		Ship.__init__(self, position, colour, projectile_pool)
		self.id = player_id
		self.name = name
		self.destroyed = False
		self.respawn_in = -1

	def update(self, delta):
		if self.destroyed:
			self.respawn_in -= delta
		else:
			Ship.update(self, delta)

	def render(self):
		if not self.destroyed:
			Ship.render(self)

	def destroy(self, respawn_in):
		self.destroyed = True
		self.respawn_in = respawn_in

	def respawn(self, x, y):
		self.set_position(x, y)
		self.destroyed = False
		self.respawn_in = -1