import random
import math

from OpenGL.GL import *

import pygame
import pygame.font
pygame.font.init()

# enum function taken from: http://stackoverflow.com/a/1695250
def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)    
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)

def random_planet_name():
	return random.choice(config.PLANET_NAMES)

def distance(a, b):
	ax, ay = a
	bx, by = b
	return math.floor(math.sqrt((bx-ax)**2 + (by-ay)**2))

def distance_morethan(a, b, value):
	ax, ay = a
	bx, by = b
	return (bx-ax)**2+(by-ay)**2 > value**2

def opengl_error(msg=None):
	msg = "(" + msg + ") " if msg is not None else ""
	error = glGetError()
	if error != GL_NO_ERROR:
		print msg + "An OpenGL error has occured: " + gluErrorString(error)

class Colour:
	def __init__(self, colour):		
		self.rgba = self.hex_to_rgba(colour)
		self.r, self.g, self.b, self.a = self.rgba
		self.rgb = (self.r, self.g, self.b)
		self.int = colour

	def to_rgba_f(self):
		return ((1.0/255)*self.r, (1.0/255)*self.g, (1.0/255)*self.b, (1.0/255)*self.a)

	def hex_to_rgba(self, hex):
		r = (hex >> 24) & 0xFF
		g = (hex >> 16) & 0xFF
		b = (hex >> 8) & 0xFF
		a = hex & 0xFF
		return (r, g, b, a)

class Rect:
	def __init__(self, position, size):
		self.x, self.y = position
		self.width, self.height = size

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

class Widget:
	def __init__(self, position, size):
		self.x, y = position
		self.width, height = size
		self.rect = Rect(position, size)
		self.clicked = False
		self.visible = True

	def collides_with_point(self, point):
		return self.rect.collides_with_point(point)

	def activate(self):
		pass

	def on_click(self, point, hook):
		self.clicked = True
		hook.append(self.on_unclick)

	def on_unclick(self, point):
		self.clicked = False
		if self.collides_with_point(point):
			self.activate

	def render(self):
		if not self.visible:
			return

class WidgetGroup:
	def __init__(self, *widgets, **kwargs):
		self.widgets = widgets
		self.active_when_invisible = False
		self.visible = True
		self.tag = kwargs['tag']
		self.tags = {}
		top, left, bottom, right = 0, 0, 0, 0
		for widget in widgets:
			if widget.tag is not None:
				self.tags[widget.tag] = widget
			try:
				if widget.rect.left < left:
					left = widget.rect.left
				if widget.rect.right > right:
					right = widget.rect.right
				if widget.rect.top > top:
					top = widget.rect.top
				if widget.rect.bottom < bottom:
					bottom = widget.rect.bottom
			except:
				pass
		self.rect = Rect((left, bottom), (right-left, top-bottom))

	def __getitem__(self, key):
		return self.tags[key]

	def collides_with_point(self, point):
		return self.rect.collides_with_point(point)

	def on_click(self, point, hook):	
		if self.visible or self.active_when_invisible:	
			for widget in self.widgets:
				if widget.collides_with_point(point):
					widget.on_click(point, hook)
					break

	def on_unclick(self, point):
		if self.visible or self.active_when_invisible:	
			for widget in self.widgets:
				if widget.collides_with_point(point):
					widget.on_unclick(point)
					break

	def render(self):
		if not self.visible:
			return
		for widget in self.widgets:
			widget.render()

class UIManager: # handles widgets
	def __init__(self, screen_size):
		self.screen_width, self.screen_height = screen_size

		self.widgets = []
		self.unclick_hooks = []
		self.tags = {}

	def __getitem__(self, key):
		return self.tags[key]

	def on_click(self, position, hook):
		for widget in self.widgets:
			if widget.collides_with_point(position):
				widget.on_click(position, self.unclick_hook)

	def on_unclick(self, position):
		for hook in self.unclick_hooks:
			hook(position)
		self.unclick_hooks = []

	def add_widgets(self, *widgets):
		self.widgets.extend(widgets)
		for widget in widgets:
			if widget.tag is not None:
				self.tags[widget.tag] = widget

	def render(self):
		for widget in self.widgets:
			widget.render()

class Text:
    def __init__(self, text, font, colour, position, is_number=False, spacing=None, tag=None):
        self.text = text
        self.font = font
        self.colour = colour
        self.position = position
        self.is_number = is_number
        if self.is_number:          
            self.spacing = spacing*self.font.size('m')[0]
        self.visible = True
        self.tag = tag
        self.draw()

    def draw(self):		
		if self.is_number:
			textures = glGenTextures(11)
			numbers = [self.font.render(str(x), True, self.colour.rgb) for x in range(10)]
			point = self.font.render('.', True, self.colour.rgb)
			self.NUMBERS = []
			for i, number in enumerate(numbers):
				width, height = number.get_size()
				data = pygame.image.tostring(number, "RGBA", 1)
				texture = textures[i]
				glBindTexture(GL_TEXTURE_2D, texture)
				glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
				glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
				glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
				self.NUMBERS.append(self.createTexDL(texture, width, height))
			width, height = point.get_size()
			data = pygame.image.tostring(point, "RGBA", 1)
			texture = textures[10]
			glBindTexture(GL_TEXTURE_2D, texture)
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
			glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
			self.POINT = self.createTexDL(texture, width, height)
		else:
			surface = self.font.render(self.text, True, self.colour.rgb)			
			data = pygame.image.tostring(surface, "RGBA", 1)
			width, height = surface.get_size()			
			texture = glGenTextures(1)
			glBindTexture(GL_TEXTURE_2D, texture)
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
			glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
			self.list = self.createTexDL(texture, width, height)
		self.rect = self.calculate_rect()

    def createTexDL(self, texture, width, height):
        newList = glGenLists(1)
        glNewList(newList, GL_COMPILE);
        glBindTexture(GL_TEXTURE_2D, texture)
        glBegin(GL_QUADS)
        glColor3f(1.0, 1.0, 1.0)
        glTexCoord2f(0, 0); glVertex2f(0, 0)    # Bottom Left Of The Texture and Quad
        glTexCoord2f(0, 1); glVertex2f(0, height)    # Top Left Of The Texture and Quad
        glTexCoord2f(1, 1); glVertex2f(width, height)    # Top Right Of The Texture and Quad
        glTexCoord2f(1, 0); glVertex2f(width, 0)    # Bottom Right Of The Texture and Quad
        glEnd()
        glEndList()
        return newList

    def calculate_rect(self):
		if self.is_number:
			strnumber = str(self.text)
			x, y = self.position
			shift_left = 0
			width = 0
			height = self.font.size('0')[1]
			for i in range(len(strnumber)):
				if strnumber[i] != '.':             
					width += i*self.spacing-shift_left
				else:
					width += i*self.spacing-shift_left
					shift_left += self.spacing*0.4
			return Rect((x, y), (width, height))
		else:
			x, y = self.position
			width, height = self.font.size(self.text)
			return Rect((x, y), (width, height))

    def set_text(self, text):
        if self.text != text:
            self.text = text
            if not self.is_number:
                self.draw()

    def set_colour(self, colour):
        self.colour = colour
        self.draw()

    def render(self):    	
        if self.visible:
            if not self.is_number:                
                glEnable(GL_TEXTURE_2D)
                glTranslatef(self.position[0], self.position[1], 0)
                glCallList(self.list)
                glDisable(GL_TEXTURE_2D)                
                glTranslatef(-self.position[0], -self.position[1], 0)
            else:
                self.blit_number()

    def blit_number(self):
        strnumber = str(self.text)
        x, y = self.position
        shift_left = 0
        for i in range(len(strnumber)):
            if strnumber[i] != '.':
            	glEnable(GL_TEXTURE_2D)
                glTranslatef(x+i*self.spacing-shift_left, y, 0)
                glCallList(self.NUMBERS[int(strnumber[i])])
                glDisable(GL_TEXTURE_2D)                
                glTranslatef(-(x+i*self.spacing-shift_left), -y, 0)
            else:
            	glEnable(GL_TEXTURE_2D)
                glTranslatef(x+i*self.spacing-shift_left, y, 0)
                glCallList(self.POINT)
                glDisable(GL_TEXTURE_2D)                
                glTranslatef(-(x+i*self.spacing-shift_left), -y, 0)
                shift_left += self.spacing*0.4

class Button:
	def __init__(self, position, text, font, background_colour, text_colour, onclick_callback, hover_colour=None, click_colour=None, size=None):
		self.x, self.y = position
		self.text = text
		self.background_colour = background_colour
		self.onclick_callback = onclick_callback
		self.hover_colour = hover_colour if hover_colour is not None else background_colour
		self.click_colour = click_colour if click_colour is not None else background_colour
		label_size = font.size(self.text)
		self.label = Text(text, font, text_colour, (self.x+label_size[1]/2, self.y+label_size[1]/2))
		if size == None:
			self.rect = pygame.Rect(self.x, self.y, label_size[1]+label_size[0], label_size[1]*2)
		else:
			width, height = size
			self.rect = pygame.Rect(self.x, self.y, width, height)
		self.hover = False
		self.visible = True
		self.clicked = False

	def collides_with_point(self, point):
		return self.rect.collidepoint(point)

	def render(self, surface):
		if self.visible:
			if self.clicked:
				colour = self.click_colour
			elif self.hover:
				colour = self.hover_colour
			else:
				colour = self.background_colour
			pygame.draw.rect(surface, colour, self.rect)
			self.label.render(surface)

	def on_hover(self):
		self.hover = True

	def on_nohover(self):
		self.hover = False

	def on_click(self, point):
		self.clicked = True

	def on_unclick(self, point):
		if self.clicked:
			self.onclick_callback(self, point)
		self.clicked = False