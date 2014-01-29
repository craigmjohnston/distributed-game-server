DROP TABLE IF EXISTS player;
CREATE TABLE player (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	name VARCHAR(40) NOT NULL,
	password_hash VARCHAR(256) NOT NULL,
	x_position INTEGER NOT NULL,
	y_position INTEGER NOT NULL,
	solar_system_id INTEGER NOT NULL,
	CONSTRAINT fk_solar_system
		FOREIGN KEY (solar_system_id)
		REFERENCES solar_system(id)
);

DROP TABLE IF EXISTS solar_system;
CREATE TABLE solar_system (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	name VARCHAR(256) NOT NULL,
	size INTEGER NOT NULL,
	traffic REAL DEFAULT 0
);

DROP TABLE IF EXISTS solar_system_entity;
CREATE TABLE solar_system_entity (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	solar_system_id INTEGER NOT NULL,
	orbit_radius INTEGER NOT NULL,
	orbit_speed REAL NOT NULL,
	CONSTRAINT fk_solar_system
		FOREIGN KEY (solar_system_id)
		REFERENCES solar_system(id)
);

DROP TABLE IF EXISTS wormhole;
CREATE TABLE wormhole (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	mouth_a_entity_id INTEGER NOT NULL,
	mouth_b_entity_id INTEGER NOT NULL,
	traffic REAL DEFAULT 0,
	CONSTRAINT fk_solar_system_entity_a
		FOREIGN KEY (mouth_a_entity_id)
		REFERENCES solar_system_entity(id),
	CONSTRAINT fk_solar_system_entity_b
		FOREIGN KEY (mouth_b_entity_id)
		REFERENCES solar_system_entity(id)
);

DROP TABLE IF EXISTS planet;
CREATE TABLE planet (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	entity_id INTEGER NOT NULL,
	name VARCHAR(256) NOT NULL,
	size INTEGER NOT NULL,
	colour INTEGER NOT NULL,
	CONSTRAINT fk_solar_system_entity
		FOREIGN KEY (entity_id)
		REFERENCES solar_system_entity(id)
);