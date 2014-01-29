import math

import pygame
try:
	import pygame.font
	pygame.font.init()
except ImportError:
	print "Font module unavailable."

import utility

# window attributes
SCREEN_WIDTH, SCREEN_HEIGHT = (1024, 960)
WINDOW_TITLE = "Dissertation (10021322) Client"
BACKGROUND_COLOUR = utility.Colour(0x05070F00)
FRAMES_PER_SECOND = 60
FRAME_RATE = 1.0/FRAMES_PER_SECOND

# utility constants
MAX_RAD = math.radians(360)

# UI
FONT = pygame.font.Font('Hattori_Hanzo.otf', 24)
FONT_SMALL = pygame.font.Font('Hattori_Hanzo.otf', 16)

UI_TEXT_COLOUR = utility.Colour(0xFFFFFFFF)
BUTTON_TEXT_COLOUR = utility.Colour(0xEEEEEEFF)
BUTTON_BACKGROUND_COLOUR = utility.Colour(0x48C7E7FF)
BUTTON_HOVER_COLOUR = utility.Colour(0xA9E0F1FF)
BUTTON_CLICK_COLOUR = utility.Colour(0xA9E0F1FF)

WORMHOLE_SPIN_SPEED = math.radians(30)
WORMHOLE_SIZE = 30
WORMHOLE_COLOUR = 0x8A9B0FFF

PLAYER_COLOUR = 0x1C7D6DFF
ENEMY_COLOUR = 0xD32F38FF

# user input keys
KEY_FORWARD = pygame.K_UP
KEY_LEFT = pygame.K_LEFT
KEY_RIGHT = pygame.K_RIGHT
KEY_FIRE = pygame.K_SPACE
KEY_INTERACT = pygame.K_RETURN

PROJECTILE_SPEED = 200

# keypresses that will be sent to the server
VALID_KEYS = frozenset([KEY_FORWARD, # TODO: this doesn't take into account preferences
						KEY_LEFT, 
						KEY_RIGHT, 
						KEY_FIRE, 
						KEY_INTERACT])

CLIENT_GATEWAY_ADDRESS = ("127.0.0.1", 31000)

# network values
SOCKET_RECV_MAX_BYTES = 4096

MSG_END_CHAR = chr(1)
MSG_TOP_DELIMITER = 2
NEGATIVE_CHAR = 126

MSG_TIME_ACCURACY = 3 # how many digits after decimal point

MINIMUM_DISTANCE = 40

# Message types
# Type ID format: '[SENDER]_[RECEIVER]_[DESCRIPTION]'
class MSG:
	OK = 0
	# CLIENT to GATEWAY	
	CL_GW_LOGIN = 1
	CL_GW_LOGOUT = 2	
	CL_GW_INPUT = 5
	CL_GW_REGISTER = 7
	# GATEWAY to CLIENT
	GW_CL_LOGIN_SUCCESSFUL = 3
	GW_CL_LOGIN_FAILED = 4
	GW_CL_FRAME = 6
	GW_CL_REGISTRATION_SUCCESSFUL = 8
	GW_CL_REGISTRATION_FAILED = 9
	GW_CL_MOVING_SYSTEMS = 10
	GW_CL_SYSTEM_INFO = 11