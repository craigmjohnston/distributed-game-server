from OpenGL.GL import *

import math
import numpy

import utility

from OpenGL.arrays import vbo

def draw_line_vbo(vbo, length, position, colour, width=1, stipple=False, 
	loop=False, rotation=None):
	"""Draws a line from a vertex buffer object.

	vbo 		vertex buffer object to draw
	length		number of vertices in the vertex buffer object
	position 	(x, y) tuple position to draw to
	colour		(r, g, b, a) float tuple colour to draw in
	width 		width of the line in pixels
	stipple 	whether to draw a dashed line
	loop 		whether to link the first and last vertices and create a loop
	rotation	degrees which the drawing should be rotated by

	"""
	x, y = position
	# setup
	glPushMatrix()
	glEnable(GL_LINE_SMOOTH)
	glEnable(GL_BLEND)
	glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
	glLineWidth(width)
	glColor4f(*colour)
	# draw
	glTranslatef(x, y, 0)
	if rotation is not None:
		glRotatef(-rotation, 0, 0, 1)
	glBindBuffer(GL_ARRAY_BUFFER, vbo)
	glVertexPointer(2, GL_FLOAT, 0, None)
	glEnableClientState(GL_VERTEX_ARRAY)
	if loop:
		glDrawArrays(GL_LINE_LOOP, 0, length)
	else:
		glDrawArrays(GL_LINE_STRIP, 0, length)
	glFlush()
	# tidy up
	glDisableClientState(GL_VERTEX_ARRAY)
	#glTranslatef(-x, -y, 0)
	glPopMatrix()
	glLineWidth(1)

def arrowhead_vbo(position, size):
	"""Creates a vertex buffer object for an arrowhead.

	position	(x, y) tuple position of the point of the arrowhead
	size		length (in pixels) of the lines of the arrowhead
	"""
	x, y = position	
	verts = [x-size, y-size, x, y, x+size, y-size]
	buf = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, buf)
	glBufferData(GL_ARRAY_BUFFER, numpy.array(verts, dtype=numpy.float32), 
		GL_STATIC_DRAW)
	return buf

def line_vbo(start, end):
	"""Creates a vertex buffer object for an arrowhead.

	position	(x, y) tuple position of the point of the arrowhead
	size		length (in pixels) of the lines of the arrowhead
	"""
	x, y = start
	x2, y2 = end
	verts = [x, y, x2, y2]
	buf = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, buf)
	glBufferData(GL_ARRAY_BUFFER, numpy.array(verts, dtype=numpy.float32), 
		GL_STATIC_DRAW)
	return buf

def circle_vbo(position, radius):
	verts = []
	seg = 360
	cx, cy = position
	theta = 2*math.pi / float(seg)
	c = math.cos(theta)
	s = math.sin(theta)
	x = radius
	y = 0
	for i in range(seg):	
		verts.extend([x+cx, y+cy])
		t = x
		x = c * x - s * y
		y = s * t + c * y

	buf = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, buf)
	glBufferData(GL_ARRAY_BUFFER, numpy.array(verts, dtype=numpy.float32), GL_STATIC_DRAW)
	return buf

def circle(position, radius, colour, width=1, stipple=False):
	#glLoadIdentity()	
	glEnable(GL_LINE_SMOOTH)
	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
	r, g, b, a = colour
	seg = 360
	cx, cy = position

	theta = 2*math.pi / float(seg)
	c = math.cos(theta)
	s = math.sin(theta)
	x = radius
	y = 0

	glColor4f(r, g, b, a)
	glLineWidth(width)
	glBegin(GL_LINE_LOOP)
	for i in range(seg):
		glVertex2d(x+cx,y+cy)
		t = x
		x = c * x - s * y
		y = s * t + c * y
	glEnd()
	glLineWidth(1)

def line(points, colour, width=1, stipple=False):	
	glEnable(GL_LINE_SMOOTH)
	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
	if stipple:
		glLineStipple(10, 0xAAAA)
		glEnable(GL_LINE_STIPPLE)
	glLineWidth(width)
	r, g, b, a = colour
	glColor3f(r, g, b)
	glBegin(GL_LINE_STRIP)
	for x, y in points:
		glVertex2d(x,y)
	glEnd()
	if stipple:
		glDisable(GL_LINE_STIPPLE)
	glLineWidth(1)

def rect(position, size, colour, width=1, stipple=False):
	x, y = position
	width, height = size
	line([[x, y], [x+width, y], [x+width, y+height], [x, y+height], [x, y]], colour)

def arrowhead(position, colour, length, width=1, rotation=0):
	x, y = position
	glPushMatrix();
	glTranslatef(x, y, 0);
	if rotation != 0:
		glRotatef(math.degrees(-rotation), 0, 0, 1)
	glEnable(GL_LINE_SMOOTH)
	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
	glLineWidth(width)
	r, g, b, a = colour
	glColor4f(r, g, b, a)
	glBegin(GL_LINE_STRIP)
	glVertex2d(-length,-length)
	glVertex2d(0,0)
	glVertex2d(length,-length)
	glEnd()
	glLineWidth(1)
	glTranslatef(-x, -y, 0);
	glPopMatrix()

def arc(pos_x, pos_y, radius, start, end, width=1):
	glEnable(GL_LINE_SMOOTH)
	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
	for j in range(width):
		glBegin(GL_LINE_LOOP)	
		for i in range(start, end):			
			angle = 2 * math.pi * i / 360
			x = pos_x + math.cos(angle)*(radius-j)
			y = pos_y + math.sin(angle)*(radius-j)
			glVertex2d(x,y)
		glEnd()

def spiral_vbo(position, radius, rotations):
	"""Creates a vertex buffer object for a circle.

	position	(x, y) tuple position of the center of the circle
	radius		radius of the circle in pixels
	"""
	verts = []
	seg = 360
	for i in range(seg*rotations):
		x = math.sin(math.radians(i))*(radius*(1.0/(seg*rotations))*((seg*rotations)-i))
		y = math.cos(math.radians(i))*(radius*(1.0/(seg*rotations))*((seg*rotations)-i))
		verts.extend([x, y])

	buf = glGenBuffers(1)
	glBindBuffer(GL_ARRAY_BUFFER, buf)
	glBufferData(GL_ARRAY_BUFFER, numpy.array(verts, dtype=numpy.float32), 
		GL_STATIC_DRAW)
	return buf