def enum(*sequential, **named):
	"""enum function taken from: http://stackoverflow.com/a/1695250"""
	enums = dict(zip(sequential, range(len(sequential))), **named)
	reverse = dict((value, key) for key, value in enums.iteritems())
	enums['reverse_mapping'] = reverse
	return type('Enum', (), enums)

class Rect:
	def __init__(self, position, size):
		self.width, self.height = size
		self.update_position(*position)		

	def update_position(self, x, y):
		self.x = x
		self.y = y
		self.left = self.x
		self.right = self.x+self.width
		self.top = self.y+self.height
		self.bottom = self.y
		self.topleft = (self.x, self.y+self.height)
		self.topright = (self.x+self.width, self.y+self.height)
		self.bottomleft = (self.x, self.y)
		self.bottomright = (self.x+self.width, self.y)

	def collides_with_point(self, point):
		x, y = point
		if x < self.left or x > self.right:
			return False
		if y < self.bottom or y > self.top:
			return False
		return True

	def collides_with(self, other):
		if self.right < other.left:
			return False
		if self.left > other.right:
			return False
		if self.bottom > other.top:
			return False
		if self.top < other.bottom:
			return False
		return True