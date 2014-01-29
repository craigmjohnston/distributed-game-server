import sys
import itertools

class Node:
	def __init__(self, value):
		self.value = value
		self.connections = []
		self.D = 0
		self.E = 0
		self.I = 0
		self.marked = False

		@staticmethod
		def connect_nodes(first_node, second_node, weight):
			edge = Edge(first_node, second_node, weight)
			first_node.connections.append(edge)
			second_node.connections.append(edge)

		def connect_to(self, node, weight):
			Node.connect_nodes(self, node, weight)

class WeightedNode(Node):
	def __init__(self, value, weight):
		Node.__init__(self, value)
		self.weight = weight
		self.replacement = None

class Edge:
	def __init__(self, first_node, second_node, weight):
		self.first_node = first_node
		self.second_node = second_node
		self.weight = weight

	def get_other(self, node):
		return self.first_node if node == self.second_node else self.second_node

class SwapPair:
	def __init__(self, a, b, _A, _B, A, B, gain):
		self.a = a
		self.b = b
		self._A = _A
		self._B = _B
		self._A_a_index = _A.index(a)
		self._B_b_index = _B.index(b)
		self.A_a_index = A.index(a)
		self.B_b_index = B.index(b)
		self.gain = gain

	def mark_pair(self):
		self.a.marked = True
		self.b.marked = True

	def test_swap_pair(self):
		self._A[self._A_a_index] = self.b
		self._B[self._B_b_index] = self.a

	def final_swap_pair(self):
		self.A[self.A_a_index] = self.b
		self.B[self.B_b_index] = self.a

def generate_real_nodes(nodes):
	real_nodes = []
	lowest_weight = None
	for node in nodes:
		if lowest_weight is None or node.weight < lowest_weight:
			lowest_weight = node.weight
	for node in nodes:
		approx_weight = int(node.weight / lowest_weight)
		ns = [Node(node.value) for i in range(approx_weight)]		
		for a in ns:
			for b in ns:
				a.connect_to(b, sys.maxint)
		node.replacement = ns[0]
		real_nodes.extend(ns)
	for node in nodes:
		for con in node.connections:
			node.replacement.connect_with(con.get_other(node).replacement, con.weight)
	return real_nodes

def list_without_kth(list, k):
	return l[:k] + l[(k + 1):]

def weight(a, b):
	for con in a.connections:
		if con.other(a) == b:
			return con.weight
	return 0

def gain(a, b):
	return a.D + b.D - 2*weight(a, b)

def sum_edges(subset_a, subset_b):
	edges = []
	for a in subset_a:
		for con in a.connections:
			if con.get_other(a) not in subset_a and con not in edges:
				edges.append(con)
	total = 0
	return sum((edge.weight for edge in edges))

def bipartition(A, B):
	T = sum_edges(A, B)
	current_gain = 1
	mark_count = 0
	while current_gain > 0:
		# make shallow copies of A and B
		_A = list(A)
		_B = list(B)
		# unmark all nodes
		for n in A+B:
			n.marked = False
		swap_pairs = []
		total_gain = 0
		total_gain_history = []
		# while there are unmarked nodes
		while mark_count < len(A)+len(B):			
			best_swap = None
			# calculate D(n) for unmarked nodes
			for a in (a for a in _A if not a.marked):
				a.E = sum_edges([a], _B)
				a.I = sum_edges([a], list_without_kth(_A, _A.index(a)))
				a.D = a.E - a.I
			for b in (b for b in _B if not b.marked):
				b.E = sum_edges([b], _A)
				b.I = sum_edges([b], list_without_kth(_B, _B.index(b)))
				b.D = b.E - b.I
			# find best swap pair
			for a in (a for a in _A if not a.marked):
				for b in (b for b in _B if not b.marked):
					gain = gain(a, b)
					if gain > best_swap.gain:
						best_swap = SwapPair(a, b, _A, _B, A, B, gain)
			# mark the nodes from the best swap and swap them
			best_swap.mark_pair()
			best_swap.test_swap_pair()
			swap_pairs.append(best_swap)
			total_gain += best_swap.gain
			total_gain_history.append(total_gain)
		highest_gain = max(total_gain_history)
		if highest_gain > 0:
			for i in range( total_gain_history.index(highest_gain)):
				swap_pairs[i].final_swap_pair()
		current_gain = highest_gain
	return current_gain

def partition_graph(nodes, parts=2):
	subsets = [nodes[i:i+len(nodes)/parts] for i in range(0, len(nodes), len(nodes)/parts)]
	pairings = (A, B for A, B in itertools.permutations(subsets))	
	for i in range(3):	
		for A, B in pairings:
			bipartition(A, B)
	return subsets