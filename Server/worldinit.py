import sqlite3

from galaxygen import generate_galaxy

"""
This is the start of the actual script which calls the generation function
and commits the results to an sqlite3 database
"""

systems = generate_galaxy(min_systems=			60, 
						  max_systems=			200, 
						  min_connections=		1,
			 			  max_connections=		3, 
			 			  min_planets=			2, 
			 			  max_planets=			5,
			 			  min_system_size=		400, 
			 			  max_system_size=		460,
			 			  min_planet_size=		5, 
			 			  max_planet_size=		20, 
			 			  wormhole_size=		30,
			 			  min_planet_speed=		0.349, 
			 			  max_planet_speed=		0.785, 
			 			  min_wormhole_speed=	0.174,
			 			  max_wormhole_speed=	0.349,
			 			  seed=					None)

planet_count = 0

for system in systems:
	planet_count += len(system.planets)	
print planet_count
print len(systems)

# commit the generated galaxy to the database
conn = sqlite3.connect('data.db')
cursor = conn.cursor()

for system in systems:	
	# insert the solar systems
	cursor.execute("INSERT INTO solar_system \
					(name, size) \
					VALUES ('%s', %i);" % (system.name, system.size))
	system.system_id = cursor.lastrowid

for system in systems:
	for i in range(len(system.connections)):
		# insert the wormholes
		connection = system.connections[i]
		if connection != 0: # if the connection hasn't already been done
			print i, system.wormhole_distances, system.wormhole_speeds
			cursor.execute("INSERT INTO solar_system_entity \
							(solar_system_id, orbit_radius, orbit_speed) \
							VALUES (%i, %i, %f);" % (system.system_id, 
													 system.wormhole_distances[i], 
													 system.wormhole_speeds[i]))
			entity_a_id = cursor.lastrowid
			c_i = connection.connections.index(system)
			cursor.execute("INSERT INTO solar_system_entity \
							(solar_system_id, orbit_radius, orbit_speed) \
							VALUES (%i, %i, %f);" % (connection.system_id, 
													 connection.wormhole_distances[c_i], 
													 connection.wormhole_speeds[c_i]))
			entity_b_id = cursor.lastrowid
			cursor.execute("INSERT INTO wormhole \
							(mouth_a_entity_id, mouth_b_entity_id) \
							VALUES (%i, %i);" % (entity_a_id, entity_b_id))
			connection.connections[c_i] = 0
			system.connections[i] = 0
	for planet in system.planets:
		# insert the planets
		cursor.execute("INSERT INTO solar_system_entity \
						(solar_system_id, orbit_radius, orbit_speed) \
						VALUES (%i, %i, %f);" % (system.system_id, 
												 planet.distance, planet.speed))
		entity_id = cursor.lastrowid
		cursor.execute("INSERT INTO planet \
						(entity_id, name, size, colour) \
						VALUES (%i, '%s', %i, %i);" % (entity_id, planet.name, 
													   planet.size, planet.colour))

players = [['craig', 'password', 200, 200, 7]]
for player in players:
	name, password, x, y, system = player
	cursor.execute("INSERT INTO player \
					(name, password_hash, x_position, y_position, solar_system_id) \
					VALUES ('%s', '%s', %i, %i, %i);" % (name, password, x, y, system))
conn.commit()
conn.close()