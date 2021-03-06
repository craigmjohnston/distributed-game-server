import math

from utility import enum

MAX_RAD = math.radians(360)

MINIMUM_DISTANCE = 40
PROJECTILE_LIFE = 3.0 # seconds

START_SYSTEM = 1 # system that all new players start in
START_X = 0
START_Y = 150

"""
Networking
"""
# {FROM}_{TO}_ADDRESS = (ip, port)
SERVER_GATEWAY_ADDRESS = ("127.0.0.1", 30000)
CLIENT_GATEWAY_ADDRESS = ("127.0.0.1", 31000)
GATEWAY_SERVER_ADDRESS = ("127.0.0.1", 32000)
SERVER_DATABASE_ADDRESS = ("127.0.0.1", 33000)

# network values
SOCKET_SERVER_MAX_QUEUE = 512
SOCKET_CLIENT_MAX_QUEUE = 512
SOCKET_DATABASE_MAX_QUEUE = 512
SOCKET_RECV_MAX_BYTES = 4096

GATEWAY_SERVER_COUNT = 2

MSG_END_CHAR = chr(1)
MSG_TOP_DELIMITER = 2
NEGATIVE_CHAR = 126

MSG_TIME_ACCURACY = 3 # how many digits after decimal point

# database query types
DBQUERY = enum('GW_STARTINFO', 'GS_SYSTEMSINFO', 'GS_UPDATE', 'GW_NEWPLAYER')

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
	# GAMESERVER to GATEWAY
	GS_GW_CONNECT_INFO = 22
	GS_GW_READY = 12
	GS_GW_MOVEPLAYER = 13
	# GATEWAY to GAMESERVER
	GW_GS_SOLARINFO = 14
	GW_GS_NEWPLAYER = 23
	# GAMESERVER to GAMESERVER
	GS_GS_SENDPLAYER = 15
	GS_GS_RECVPLAYER = 16
	# GAMESERVER to DATABASE
	GS_DB_SYSTEMINFO = 17
	GS_DB_UPDATE = 18
	GS_DB_CHANGE_SYSTEM = 19
	# DATABASE
	DB_QUERY = 20
	DB_RESPONSE = 21	