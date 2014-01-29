class PyOpenGLRecorder:
	def __init__(self, position, size, directory):		
		self.x, self.y = position
		self.width, self.height = size
		self.directory = directory
		if not os.path.exists(self.directory):
    		os.makedirs(self.directory)
		self.frame = 0

	def record(self):
		self.frame += 1
		buf = glReadPixels(self.x, self.y, self.width, self.height, GL_RGB,GL_BYTE)
		img = pygame.image.frombuffer(buf, (self.width, self.height), 'RGB')
		pygame.image.save(img, self.directory + '/frame%06i.bmp'%(self.frame))