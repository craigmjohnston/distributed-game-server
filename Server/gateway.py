import cmd

import gevent

import config
from config import MSG, DBQUERY
import network
from utility import enum
import partition

STATE = enum('WAITING_FOR_DATABASE', 
			 'WAITING_FOR_SERVERS', 
			 'ACCEPTING_PLAYERS')

class System:
	def __init__(self, system_id=-1, server=None, connections=[]):
		self.id = system_id
		self.server = server
		self.connections = connections

class Server:
	def __init__(self, server_id=-1, server_socket=None, ip="", client_port=-1, 
				 server_port=-1, systems=None, neighbours=None):
		self.id = server_id
		self.socket = server_socket
		self.ip = ip
		self.client_port = client_port # address for clients to connect on
		self.server_port = server_port # address for servers to connect on
		self.systems = systems if systems is not None else [] # systems we're responsible for
		self.edge_systems = {}
		self.neighbours = neighbours if neighbours is not None else [] # neighbouring servers

class NeighbourLink:
	def __init__(self, server_a, server_b):
		self.server_a = server_a
		self.server_b = server_b

class Player:
	def __init__(self, player_id, username, password, system_id):
		self.id = player_id
		self.username = username
		self.password = password
		self.system_id = system_id

class Client:
	def __init__(self, client_id, socket, address, authenticated=False, player=None):
		self.id = client_id
		self.client_socket = socket
		self.server_socket = None
		self.address = address
		self.authenticated = authenticated
		self.player = player

class Database:
	def __init__(self, address, group):
		self.group = group
		self.socket = gevent.socket.socket()

class Gateway:
	def __init__(self):
		self.message_id_counter = 0		
		self.state = STATE.WAITING_FOR_SERVERS

		self.player_data = {} # login details and solar system
		self.clients = [] # all connected clients
		self.clients_by_player = {}
		self.servers = []
		self.servers_by_system = {}
		self.servers_by_id = {}
		self.systems_by_id = {}

		self.error = False

	def accept_server_connections(self):
		server_sock = network.Socket()
		server_sock.bind(config.SERVER_GATEWAY_ADDRESS)
		server_sock.listen(config.SOCKET_SERVER_MAX_QUEUE)
		server_count = 0
		print "Accepting server connections"
		while server_count < config.GATEWAY_SERVER_COUNT:
			s_sock, address = server_sock.accept()
			server_count += 1
			print ("Server connection " + str(server_count) + "/" 
				   + str(config.GATEWAY_SERVER_COUNT) + " from " + str(address))
			server = Server(server_id=server_count-1, server_socket=s_sock, ip=address[0])
			self.servers.append(server)
			self.servers_by_id[server.id] = server
			# get the connection information from the server
			msg = server.socket.wait_for_message(MSG.GS_GW_CONNECT_INFO)
			server.client_port, server.server_port = msg.data

	def wait_for_server_loaded(self, server):
		system_info = [system.id for system in server.systems]
		neighbour_info = []
		for neighbourlink in server.neighbours:
			neighbour = neighbourlink.server_a if neighbourlink.server_a != server else neighbourlink.server_b
			neighbour_info.append((neighbour.id, 
								   (neighbour.ip, neighbour.server_port), 
								    [system.id for system in server.edge_systems[neighbour.id]], 
								   neighbour == neighbourlink.server_b))
		msg = server.socket.send_message(MSG.GW_GS_SOLARINFO, [system_info, neighbour_info])
		msg = server.socket.wait_for_message(MSG.GS_GW_READY)
		if msg is None:
			self.error = True

	def receive_server_notifications(self, server):
		while True:
			msg = server.socket.wait_for_message()
			if msg is None:
				print "Server %i has disconnected" % server.id
				break
			if msg.type == MSG.GS_GW_MOVEPLAYER:
				print "Moving player"
				player_id, server_id, system_id = msg.data
				client = self.clients_by_player[player_id]
				client.player.system_id = system_id
				new_server = self.servers_by_id[server_id]
				client.server_socket.close()
				client.server_socket = network.Socket()
				client.server_socket.connect((new_server.ip, new_server.client_port))
				client.server_socket.send_message(MSG.GW_GS_NEWPLAYER, client.player.id)			
				gevent.spawn(self.receive_server_input, client)

	def accept_client_connections(self):
		client_id_counter = 0	
		client_socket = network.Socket()
		client_socket.bind(config.CLIENT_GATEWAY_ADDRESS)
		client_socket.listen(config.SOCKET_CLIENT_MAX_QUEUE)
		print "Accepting client connections"
		while True:
			c_sock, address = client_socket.accept()
			print "Client connection from " + str(address) + " as CLIENT " + str(client_id_counter)
			client = Client(client_id_counter, c_sock, address)
			self.clients.append(client)
			gevent.spawn(self.receive_client_input, client)
			client_id_counter += 1

	def client_disconnect(self, client):
		print "Client " + str(client.id) + " closed connection"
		client.client_socket.close()
		if client.authenticated:
			client.server_socket.send_message(MSG.CL_GW_LOGOUT)
			del self.clients_by_player[client.player.id]
		self.clients.remove(client)

	def receive_client_input(self, client):
		while True:
			if not client.authenticated:
				msg = client.client_socket.wait_for_message([MSG.CL_GW_LOGIN, MSG.CL_GW_REGISTER])
				if msg is None:
					self.client_disconnect(client)
					break					
				username, password = msg.data
				if msg.type == MSG.CL_GW_REGISTER:
					# user registration
					if username not in self.player_data:						
						self.database_sock.send_message(MSG.DB_QUERY, [DBQUERY.GW_NEWPLAYER, [username, password, config.START_SYSTEM, config.START_X, config.START_Y]])
						response = self.database_sock.wait_for_message(MSG.DB_RESPONSE)		
						response_id, player_id = response.data				
						self.player_data[username] = Player(player_id, username, password, config.START_SYSTEM)
						self.systems_by_id[config.START_SYSTEM].server.socket.send_message(MSG.GW_GS_NEWPLAYER, [player_id, username, config.START_SYSTEM, config.START_X, config.START_Y])
						client.client_socket.send_message(MSG.GW_CL_REGISTRATION_SUCCESSFUL)
					else:
						client.client_socket.send_message(MSG.GW_CL_REGISTRATION_FAILED)
				else:
					if self.authenticate_player(username, password):
						client.authenticated = True
						client.player = self.player_data[username]
						self.clients_by_player[client.player.id] = client
						client.client_socket.send_message(MSG.GW_CL_LOGIN_SUCCESSFUL, client.player.id)			
						server = self.servers_by_system[client.player.system_id]
						client.server_socket = network.Socket()
						client.server_socket.connect((server.ip, server.client_port))
						client.server_socket.send_message(MSG.GW_GS_NEWPLAYER, client.player.id)			
						gevent.spawn(self.receive_server_input, client)
					else:
						client.client_socket.send_message(MSG.GW_CL_LOGIN_FAILED)
			else: # authenticated
				data = client.client_socket.recv()
				if data is None:
					self.client_disconnect(client)
					break
				client.server_socket.send(data)

	def receive_server_input(self, client):
		while True:
			data = client.server_socket.recv()
			if not data: # end this greenlet if the socket is closed
				break
			client.client_socket.send(data)
		print "Stopped listening for server input"

	def authenticate_player(self, username, password):
		return self.player_data[username].password == password

	def client_switch_servers(self, client, new_server):
		client.server_sock.shutdown()
		client.server_sock.close()
		client.server_sock = socket.socket(new_server.address)

	def connect_to_database(self):
		# connect to database
		self.database_sock = network.Socket()
		self.database_sock.connect(config.SERVER_DATABASE_ADDRESS)
		self.database_sock.send_message(MSG.DB_QUERY, DBQUERY.GW_STARTINFO)
		response = self.database_sock.wait_for_message(MSG.DB_RESPONSE)
		if response is None:
			print "Database closed connection"
			return		
		msg_id, response_data = response.data
		return response_data

	def partition_systems(self, system_data, wormhole_data):
		p_systems_by_id = {s_id: partition.System(s_id, s_traffic) 
						   for s_id, s_traffic in system_data}
		p_systems = [system for s_id, system in p_systems_by_id.iteritems()]
		p_wormholes = [partition.Wormhole(w_id, traffic,
										  p_systems_by_id[system_a_id], 
										  p_systems_by_id[system_b_id]) 
					   for w_id, traffic, system_a_id, system_b_id in wormhole_data]
		partitioned = partition.partition_systems(p_systems, p_wormholes, self.servers)
		systems = [System(system_id=system.id, server=system.server)
				   for system in partitioned]
		self.systems_by_id = {system.id: system for system in systems}
		self.servers_by_system = {system.id: system.server for system in systems}	
		# connect systems	
		for wormhole in p_wormholes:
			system_a = self.systems_by_id[wormhole.system_a.id]
			system_b = self.systems_by_id[wormhole.system_b.id]
			system_a.connections.append(system_b)
			system_b.connections.append(system_a)
		# assign systems to servers
		for system in systems:
			system.server.systems.append(system)
		# build lists of edge systems
		for server in self.servers:
			for system in server.systems:
				for connection in system.connections:
					if connection.server.id != server.id:
						if connection.server.id not in server.edge_systems:
							link = NeighbourLink(server, connection.server)
							server.neighbours.append(link)
							connection.server.neighbours.append(link)
							server.edge_systems[connection.server.id] = []
							connection.server.edge_systems[server.id] = []
						if connection not in server.edge_systems[connection.server.id]:
							server.edge_systems[connection.server.id].append(connection)
							connection.server.edge_systems[server.id].append(system)

	def initialise_data(self):
		# connect to DB and retrieve startup data
		system_data, wormhole_data, player_data = self.connect_to_database()		
		# build player list for authentication
		self.player_data = {username: Player(player_id, username, password, system_id) 
							for (player_id, username, password, system_id) 
							in player_data}
		return (system_data, wormhole_data)

	def launch(self):
		# initialise data and accept server connections
		init_greenlet = gevent.spawn(self.initialise_data)
		server_accept_greenlet = gevent.spawn(self.accept_server_connections)
		gevent.joinall([init_greenlet, server_accept_greenlet])
		system_data, wormhole_data = init_greenlet.value
		# partition solar system network
		self.partition_systems(system_data, wormhole_data)
		# wait for confirmation of loaded servers
		gevent.joinall([gevent.spawn(self.wait_for_server_loaded, server) 
						for server in self.servers])
		# start accepting client connections and listening for server notifications
		greenlets = [gevent.spawn(self.receive_server_notifications, server) 
						for server in self.servers]
		greenlets.append(gevent.spawn(self.accept_client_connections))
		gevent.joinall(greenlets)

gateway = Gateway()
gateway.launch()