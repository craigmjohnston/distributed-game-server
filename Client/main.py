import time
import argparse

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import pygame
from pygame.locals import *
import yaml
import gevent

import config
from config import MSG
import utility
from game import Game

last_frame = time.time()
game = None

MOUSE_LEFT = 1
MOUSE_RIGHT = 2
MOUSE_MIDDLE = 3

STATE_UP = 1
STATE_DOWN = 2

#recorder = PyOpenGLRecorder((0, 0), (config.SCREEN_WIDTH, config.SCREEN_HEIGHT), 'record')

"""
Handlers
"""
def handle_mouse(button, state, x, y):
	if button == MOUSE_LEFT:	
		if state == STATE_DOWN:
			game.on_click((x, y))
		else:
			game.on_unclick((x, y))

def handle_key(key, state):
	game.on_key(key, state)

def logout():
	game.logout()

def resize(width, height):    
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()

"""
Initialisation
"""
def run(function, username, password):
	global mouse_history
	init(function, username, password)
	gameloop_greenlet = gevent.spawn(gameloop)
	gameloop_greenlet.join()

def init(function, username, password):
	global game
	pygame.init()
	screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), HWSURFACE|OPENGL|DOUBLEBUF)
	pygame.display.set_caption(config.WINDOW_TITLE)
	resize(config.SCREEN_WIDTH, config.SCREEN_HEIGHT)
	glClearColor(0.1,0.1,0.14,0.0)
	glPointSize(1.0)
	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	gluOrtho2D(0.0, float(config.SCREEN_WIDTH), 0.0, float(config.SCREEN_HEIGHT))
	fs = file('prefs.yaml', 'r')
	preferences = yaml.load(fs)
	fs.close()
	game = Game(preferences, function, username, password)

"""
Game loop
"""
def gameloop():
	while True:
		for event in pygame.event.get():
			if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
				state = True if event.type == pygame.KEYDOWN else False
				handle_key(event.key, state)
			elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.MOUSEBUTTONUP:
				state = STATE_DOWN if event.type == pygame.MOUSEBUTTONDOWN else STATE_UP
				x, y = event.pos
				handle_mouse(event.button, state, x, config.SCREEN_HEIGHT-y)
			elif event.type == QUIT:
				logout()
				return
		if not idle():
			# something bad happened in the loop, close the client
			break
		gevent.sleep()

def idle():
	global last_frame, game
	delta = time.time() - last_frame
	if delta >= config.FRAME_RATE:
		if not game.update(delta):
			return False
		render()
		last_frame += delta
	return True

def render():	
	glClear(GL_COLOR_BUFFER_BIT)
	game.render()
	pygame.display.flip()
	#recorder.record() # OpenGL screen recorder

"""
Start the client up
"""
# parse command-line arguments
parser = argparse.ArgumentParser(
	description='Client')
parser.add_argument('function', metavar='function', type=str, 
	help='Either login or register')
parser.add_argument('username', metavar='username', type=str, 
	help='username')
parser.add_argument('password', metavar='password', type=str, 
	help='password')
args = parser.parse_args()

run(args.function, args.username, args.password)