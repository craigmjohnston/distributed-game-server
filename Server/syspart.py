import partition
from partition import WeightedNode, Edge

class System:
	def __init__(self, system_id, traffic):
		self.id = system_id
		self.traffic = traffic
		self.connections = []
		self.server = None

class Wormhole:
	def __init__(self, wormhole_id, traffic, system_a, system_b):
		self.system_a = system_a
		self.system_b = system_b
		self.traffic = traffic
		self.system_a.connections.append(self.system_b)
		self.system_b.connections.append(self.system_a)

def parse_to_graph(systems):
	nodes = []
	nodes_by_system_id = {}
	for system in systems:
		node = WeightedNode(system, system.traffic)
		nodes.append(node)
		nodes_by_system_id[system.id] = node
	for system in systems:
		node = nodes_by_system_id[system.id]
		for con in system.connections:
			exists = False
			for edge in node.connections:
				if # ------------- finish this!

def parse_from_graph(subsets):
	pass

def partition_systems(systems, wormholes, parts):
	if len(systems) % parts > 0:
		raise ValueError("len(systems) must be a multiple of parts")
	nodes = parse_to_graph(systems)
	subsets = partition.partition_graph(nodes, parts)
	return parse_from_graph(subsets)