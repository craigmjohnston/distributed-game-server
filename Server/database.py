import sqlite3
import argparse
import os

import yaml
import gevent

import network
import config
from config import MSG, DBQUERY
from utility import enum

class InvalidQueryException(Exception):
	def __init__(self, query):
		self.query = query

	def __str__(self):
		return repr(self.query) + ' is not a valid query.'

class QueryQueue:
	"""Queues database queries in a first-in-first-out fashion. Requires that
	types of query be initialised using add_query_type, which links a callback
	with each query type. When next_query() is called, the queue passes the
	data for the oldest query to the relevant callback, then removes the query
	from the queue. Queries that make use of the id parameter in add_query()
	are compared with previous queries of that type; if the id matches with an
	older query, the older query is removed and replaced by the newer query.

	"""
	def __init__(self):
		self.query_queue = []
		self.queries = {}
		self.callbacks = {}

	def add_query_type(self, type, callback):
		"""Link a callback with a query type. This should be done before adding
		any queries of the specified type.

		type -- the query type to be linked.
		callback -- the callback to be run when a query with the matching type
					is processed.

		"""
		self.callbacks[type] = callback
		self.queries[type] = {}

	def add_query(self, query):
		"""Add a query to the queue. If the id parameter is given, check whether
		a query of the same type with the same id already exists and remove it
		from the queue if it does, replacing it with the new query.

		type -- the query type. Should be one that has been previously linked to
				a callback function.
		data -- the data to pass to the relevant callback function when the
				query is processed.
		id -- (optional) the query id, to be compared to older queries of the
			  same type.

		"""
		if query.id is None:
			self.query_queue.append(query)
		elif self.queries[query.type] is not None:
			if self.queries[query.type][query.id] is not None:
				old_query = self.queries[query.type]
				self.query_queue.remove(old_query)
			self.queries[query.type][query.id] = query
			self.query_queue.append(query)

	def next_query(self):
		"""Process the next query and then remove it from the queue."""
		if len(self.query_queue) > 0:
			query = self.query_queue[0]
			if query.data is not None:
				query.result = self.callbacks[query.type](query.data)
			else:
				query.result = self.callbacks[query.type]()
			self.query_queue.remove(query)
			if query.id is not None: self.queries[query.type][query.id] = None

class Query:
	"""Query class used for passing query data and results between greenlets."""
	def __init__(self, type, id=None, data=None):
		self.type = type
		self.id = id
		self.data = data
		self.result = None

class Database:
	def __init__(self):
		db_exists = os.path.exists('data.db')

		self.connection = sqlite3.connect('data.db')		
		self.cursor = self.connection.cursor()

		# make sure TEXT outputs as a bytestring and not unicode
		self.connection.text_factory = str

		# check whether the database already exists, create it if it doesn't		
		if not db_exists:
			self.create_database()

		# set up the query types in the query queue
		self.query_queue = QueryQueue()
		self.query_queue.add_query_type(DBQUERY.GS_SYSTEMSINFO, 
										self.get_gameserver_data)
		self.query_queue.add_query_type(DBQUERY.GW_STARTINFO, 
										self.get_gateway_data)
		self.query_queue.add_query_type(DBQUERY.GS_UPDATE, 
										self.server_update)
		self.query_queue.add_query_type(DBQUERY.GW_NEWPLAYER,
										self.new_player)

	def begin(self):
		processing_greenlet = gevent.spawn(self.process_queue)
		connect_greenlet = gevent.spawn(self.accept_connections)
		gevent.joinall([processing_greenlet, connect_greenlet])

	def create_database(self):
		print "Creating database from SQL dump"
		with open ("res/database.sql", "r") as sqlfile:
			data = sqlfile.read()		
		self.cursor.executescript(data)

	def process_queue(self):
		while True:
			self.query_queue.next_query()
			gevent.sleep()

	def accept_connections(self):
		"""Callback for when a client connection is accepted. Starts an infinite
		loop that receives data from the client, passes it to a handler, then
		sends a YAML dump of the result from the handler back to the client.

		socket -- the socket the client is connected through
		address -- IP address of the client

		"""
		sock = network.Socket()
		sock.bind(config.SERVER_DATABASE_ADDRESS)
		sock.listen(config.SOCKET_DATABASE_MAX_QUEUE)
		print "Accepting connections"
		while True:
			c_sock, address = sock.accept()
			print "Connection from " + str(address)
			gevent.spawn(self.receive_input, c_sock)

	def receive_input(self, sock):
		while True:
			msg = sock.wait_for_message()
			if msg is None:
				print "Connection from " + str(sock.address) + " closed"
				break
			response = self.handle_query(msg.data)
			sock.send_message(MSG.DB_RESPONSE, [msg.id, response])

	def handle_query(self, query):
		"""Parses a query and passes the query data to the relevant method,
		depending on the query type. Returns the result of the actual database
		query. If it does not recognise the query type, it raises an
		InvalidQueryException.

		raw_query -- the raw query from the client

		"""
		# allow for queries with no data attached
		if isinstance(query, (list, tuple)):
			query_type, data = query
		else:
			query_type = query
			data = []

		if query_type == DBQUERY.GS_SYSTEMSINFO: # gameserver data
			print "Systems info request"
			query_object = Query(DBQUERY.GS_SYSTEMSINFO, None, data)
		elif query_type == DBQUERY.GW_STARTINFO: # gateway data
			print "Gateway data request"
			query_object = Query(DBQUERY.GW_STARTINFO)
		elif query_type == DBQUERY.GS_UPDATE: # update from gameserver
			print "Update from server"
			query_object = Query(DBQUERY.GS_UPDATE, None, data)
		elif query_type == DBQUERY.GW_NEWPLAYER:
			username, password, solar_system, x, y = data
			query_object = Query(DBQUERY.GW_NEWPLAYER, None, data)
		else:
			raise InvalidQueryException(query)

		self.query_queue.add_query(query_object)

		while query_object.result is None:
			gevent.sleep()
		return query_object.result

	# get the data necessary for a server at startup
	# provided a list of solar systems the server contains
	def get_gameserver_data(self, data):
		"""Pull the data necessary for a gameserver to function properly,
		including solar system, solar system entity, and player data. Return
		as Dictionary separating data into categories.

		solar_systems -- a list of the solar systems to gather data about
		
		"""		
		local_systems, edge_systems = data
		local_systems = [str(system) for system in local_systems]
		csv_solar_systems = ','.join(local_systems)
		if edge_systems and edge_systems != [None]:
			edge_systems = [str(system) for system in edge_systems]
			csv_edge_systems = ','.join(edge_systems)
		self.cursor.execute('SELECT id, name, size \
							 FROM solar_system \
							 WHERE id IN (' + csv_solar_systems + ');')
		solar_system_data = self.cursor.fetchall()
		if edge_systems and edge_systems != [None]:
			self.cursor.execute('SELECT id, name \
							 FROM solar_system \
							 WHERE id IN (' + csv_edge_systems + ');')
			edge_system_data = self.cursor.fetchall()
		else:
			edge_system_data = []
		self.cursor.execute('SELECT e.solar_system_id, e.orbit_radius, e.orbit_speed, e.id, w.id \
							 FROM solar_system_entity AS e \
							 INNER JOIN wormhole AS w \
								ON e.id = w.mouth_a_entity_id OR e.id = w.mouth_b_entity_id \
							 WHERE e.solar_system_id IN (' + csv_solar_systems + ');')
		wormhole_data = self.cursor.fetchall()
		if edge_systems and edge_systems != [None]:
			self.cursor.execute('SELECT e.solar_system_id, e.orbit_radius, e.orbit_speed, e.id, w.id \
								 FROM solar_system_entity AS e \
								 INNER JOIN wormhole AS w \
									ON e.id = w.mouth_a_entity_id OR e.id = w.mouth_b_entity_id \
								 WHERE e.solar_system_id IN (' + csv_edge_systems + ');')
			edge_wormhole_data = self.cursor.fetchall()
		else:
			edge_wormhole_data = []
		self.cursor.execute('SELECT p.id, p.size, p.colour, p.name, e.orbit_radius, \
							 e.orbit_speed, e.solar_system_id \
							 FROM planet AS p \
							 LEFT JOIN solar_system_entity AS e \
							 ON p.entity_id=e.id \
							 WHERE e.solar_system_id IN (' + csv_solar_systems + ')')
		planet_data = self.cursor.fetchall()
		self.cursor.execute('SELECT id, name, x_position, y_position, \
							 solar_system_id \
							 FROM player \
							 WHERE solar_system_id IN (' + csv_solar_systems + ');')
		player_data = self.cursor.fetchall()
		return [solar_system_data, edge_system_data, 
				[wormhole_data, edge_wormhole_data], planet_data, player_data]

	def get_gateway_data(self):
		"""Pull a list of players; a list of solar systems and average
		traffic readings; and a list of wormholes and average traffic readings.
		Return a Dictionary, with the data sorted into categories.

		"""
		self.cursor.execute('SELECT id, traffic FROM solar_system;')
		solar_system_data = self.cursor.fetchall()
		self.cursor.execute('SELECT w.id, w.traffic, ea.solar_system_id, eb.solar_system_id \
							 FROM wormhole AS w \
							 LEFT JOIN solar_system_entity AS ea \
							 	ON w.mouth_a_entity_id = ea.id \
							 LEFT JOIN solar_system_entity AS eb \
							 ON w.mouth_b_entity_id = eb.id;')
		wormhole_data = self.cursor.fetchall()
		self.cursor.execute('SELECT id, name, password_hash, solar_system_id \
							 FROM player;')
		player_data = self.cursor.fetchall()
		return [solar_system_data, wormhole_data, player_data]

	def server_update(self, dirty_players):
		self.cursor.executemany('UPDATE player \
								SET x_position=(?), y_position=(?), \
									solar_system_id=(?) \
								WHERE id=(?)', ((x, y, s_id, p_id) 
												for p_id, x, y, s_id 
												in dirty_players))
		return True

	def new_player(self, data):
		username, password, solar_system, x, y = data
		self.cursor.execute("INSERT INTO player \
							 (name, password_hash, solar_system_id, x_position, y_position) \
							 VALUES ('%s', '%s', %i, %i, %i)" % (username, password, 
							 									 solar_system, x, y,))
		return self.cursor.lastrowid

database = Database()
database.begin()