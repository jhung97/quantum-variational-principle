import numpy as np
from random import random, randint
import sys
from network import *
from hamiltonian import *

if __name__ == '__main__':

	network = RadialBasisFunctionNetwork(2,1,10)
	ham = Hamiltonian2DOscillator(1,1,0.5)

	# Parameters for 2d oscillator
	energy_x = 4
	energy_y = 2
	
	#Max number of basis functions for hamiltonian
	max_qn = 40
	steps = 200
	

	size_ops = 2 * network.num_centers + network.num_centers * network.in_dim
	o = np.zeros((size_ops,1))
	op = np.zeros((size_ops,1))
	ep = np.zeros((size_ops,1))
	opo = np.zeros((size_ops,size_ops))

	F = np.zeros((size_ops,1))
	S = np.zeros((size_ops,size_ops))

	for i in range(steps):
		
		# Do metropolis to estimate energy
		
		iterations = 100
		
		state_new = np.zeros((2,))

		#Current state 
		state = np.random.random_integers(max_qn,size=(2,))
		
		#Trial state
		state_trial = state
		
		accepted_new = 0
		
		#Initial energy calculation for random start state
		for _ in range(iterations // 20):
			#Generate new trial state
			randn = randint(0,1)
			randn2 = (randint(0,1) - 0.5) * 2 #Change state up or down, randn2 is +/- 1
			state_trial[randn] = state[randn] + randn2 
		
			#Keep states within [0,maxqn] because state should be a vector of allowed quantum numbers
			state_trial[0] = state_trial[0] if state_trial[0] >= 0 else 0
			state_trial[0] = state_trial[0] if state_trial[0] < max_qn else max_qn - 1
			state_trial[1] = state_trial[1] if state_trial[1] >= 0 else 0
			state_trial[1] = state_trial[1] if state_trial[1] < max_qn else max_qn - 1
			
			prob = network.psi(state_trial) / network.psi(state)

			#print(state_trial, state)

			if random.random() < np.linalg.norm(prob) ** 2:
				state = state_trial
				accepted_new += 1
				
			
		accepted_new = 0
		energy = 0
		


		#Now do the actual metropolis algorithm
		for ll in range(iterations):
			#print(ll)
			#Generate trial states again
			randn = randint(0,1)
			randn2 = (randint(0,1) - 0.5) * 2
			state_trial[randn] = state[randn] + randn2

			state_trial[0] = state_trial[0] if state_trial[0] >= 0 else 0
			state_trial[0] = state_trial[0] if state_trial[0] < max_qn else max_qn - 1
			state_trial[1] = state_trial[1] if state_trial[1] >= 0 else 0
			state_trial[1] = state_trial[1] if state_trial[1] < max_qn else max_qn - 1

			prob = network.psi(state_trial) / network.psi(state)
			
			#Change state if acceptance probability is high enough
			if random.random() < np.linalg.norm(prob) ** 2:
				state = state_trial
				accepted_new += 1
				
	
			#Ground state expectation energy, the first term of E_local
			E = ham.product(state)
			
			#sum over all the states, n'
			state_prime = state

			# The energy calculation depends on if one of the states is the ground state
			# This calculates E
			if not (state[0] or state[1]): #Both dimensions are ground state
				state_prime[0] = state[0] + 1
				coeff1 = np.sqrt(state_prime[0] / 2)
				E += -coeff1 * energy_x * network.psi(state_prime) / network.psi(state)
				
				state_prime[1] = state[1] + 1
				coeff2 = np.sqrt(state_prime[1] / 2)
				E += -coeff2 * energy_y * network.psi(state_prime) / network.psi(state)

			elif (not state[0] and state[1]):
				state_prime[0] = state[0] + 1
				coeff1 = np.sqrt(state_prime[0] / 2)
				E += -coeff1 * energy_x *network.psi(state_prime) / network.psi(state)

				state_prime = state

				state_prime[1] = state[1] + 1
				coeff2 = np.sqrt(state_prime[1] / 2)

				E += -coeff2 * energy_y * network.psi(state_prime) / network.psi(state)
				state_prime[1] = state[1] - 1
				coeff2 = np.sqrt(state[1] / 2)
				E += -coeff2 * energy_y * network.psi(state_prime) / network.psi(state)

			elif (state[0] and not state[1]):
				state_prime[0] = state[0] + 1
				coeff1 = np.sqrt(state_prime[0] / 2)

				E += -coeff1 * energy_x * network.psi(state_prime) / network.psi(state)  
				state_prime[0] = state[0] - 1 

				coeff1 = np.sqrt(state[0] / 2)

				E += -coeff1 * energy_x * network.psi(state_prime) / network.psi(state)  

				state_prime = state

				state_prime[1] = state[1] + 1
				coeff2 = np.sqrt(state_prime[1] / 2)
				E += -coeff2 * energy_y * network.psi(state_prime) / network.psi(state)  
			else:
				state_prime = state
				state_prime[0] = state[0] + 1 
				coeff1 = np.sqrt(state_prime[0] / 2)

				E += -coeff1 * energy_x * network.psi(state_prime) / network.psi(state)
				state_prime[0] = state[0] - 1 

				coeff1 = np.sqrt(state[0] / 2.0)

				E += -coeff1 * energy_x * network.psi(state_prime) / network.psi(state)

				state_prime = state

				state_prime[1] = state[1] + 1
				coeff2 = np.sqrt(state_prime[1] / 2)

				E += -coeff2 * energy_y * network.psi(state_prime) / network.psi(state)
				state_prime[1] = state[1] - 1
				coeff2 = np.sqrt(state[1] / 2)

				E += -coeff2 * energy_y * network.psi(state_prime) / network.psi(state)


			#Neural net training, adjust parameters of network with stochastic reconfiguration
			energy += E

			network.stochastic_reconfig(state)

			#print(np.shape(network.o_a))
			#print(np.shape(network.o_b))
			#print(np.shape(network.o_c))
			parameters = np.concatenate((network.o_a, network.o_b, network.o_c))
			#print(parameters)
			for j in range(size_ops):
				o[j] += parameters[j]
				op[j] += parameters[j]
				ep[j] += E * parameters[j]

				for k in range(size_ops):
					opo[j][k] += parameters[j]*parameters[k]

		energy /= iterations
		o /= iterations
		op /= iterations
		ep /= iterations
		opo /= iterations

		print ("Iteration ", i, " with energy ", energy)

		m = 100 * np.power(0.9, i + 1) 
		tempc = m if m > 0.0001 else 0.0
		tempd = 0 	 	 	 	

		for p in range(size_ops):
			F[p] = ep[p] - energy * op[p]

			for q in range(size_ops):
				S[p][q] = opo[p][q] - op[p] * o[q]
				tempd = tempc * S[p][p]

				S[p][p] += tempd

		dd = np.zeros((size_ops))
		dd = -0.2 * np.linalg.inv(S).dot(F)

		da = np.zeros((network.num_centers))
		db = np.zeros((network.num_centers))
		dc = np.zeros((network.num_centers, network.in_dim))

		da = dd[0:network.num_centers]
		db = dd[network.num_centers:2 * network.num_centers]
		for l in range(network.num_centers):
			dc[l] = dd[network.num_centers * 2 + l * network.in_dim + l % 2]

		network.update_parameters(da,db,dc)

	#print(network.a, network.b, network.c)

	print(network.psi(np.array([0,0])))