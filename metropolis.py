import numpy as np
from random import random, randint
import sys
import copy
from network import *
from hamiltonian import *
from visualization import *
np.seterr(all='raise') #For debugging

'''
	Runs 200 steps of parameter updates, each step having 50 000 monte carlo steps for 
	estimating local energy.
	The code as is took approximately 16 hours to run on a server with
	64GB of RAM and a 16 core xeon processor. 

	Tune steps to 100/1000 for more managable load. 
	
	Details of algorithms and neural net are provided in accompanying paper. 

	There were many underflow errors in the process of debugging, so manual checks were
	added to detect those. Slightly imprecise results may result due to the neglecting of 
	certain terms to fix errors. 

	Todo in the future: Fix underflow errors and swap datatypes to complex
'''

if __name__ == '__main__':

	network = RadialBasisFunctionNetwork(2, 1, 10)

	#print(network.a)
	#print(network.b)
	#print(network.c)

	ham = Hamiltonian2DOscillator(1, 1, 0.5, 4, 2)

	# Parameters for 2d oscillator
	energy_x = 4
	energy_y = 2
	
	#Max number of basis functions for hamiltonian
	max_qn = 10
	steps = 200   #Reconfiguration steps
	iterations = 50000   #Number of monte carlo steps per iteration

	size_ops = 2 * network.num_centers + network.num_centers * network.in_dim

	#Initialization
	for i in range(steps):

		#Refresh parameteres
		O = np.zeros((size_ops,1),dtype=np.complex)

		O_star = np.zeros((size_ops,1),dtype=np.complex) 
		EO = np.zeros((size_ops,1),dtype=np.complex)
		Oij = np.zeros((size_ops,size_ops),dtype=np.complex)

		F = np.zeros((size_ops,1),dtype=np.complex)
		S = np.zeros((size_ops,size_ops),dtype=np.complex)

		state_new = np.zeros((2,))

		#Current state 
		state = np.zeros(shape=(2,))
		
		#Trial state
		state_trial = copy.deepcopy(state)
				
		#Initalize with random start state
		for _ in range(iterations):
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
				state = copy.deepcopy(state_trial)
				

		accepted_new = 0
		energy = 0


		#Now do the actual metropolis algorithm
		for ll in range(iterations):
			#print(ll)
			#print(state_trial)

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
				state = copy.deepcopy(state_trial)
				accepted_new += 1
				
	
			#Ground state expectation energy, the first term of E_local
			E = ham.product(state) + ham.perturbed_energy(state, network)

			energy += E

			network.stochastic_reconfig(state)

			#print(np.shape(network.o_a))
			#print(np.shape(network.o_b))
			#print(np.shape(network.o_c))
			parameters = np.concatenate((network.o_a, network.o_b, network.o_c))
			#print(parameters)



			# Calculate the intermediate step matrices for covariance and force
			for j in range(size_ops):
				if not np.abs(parameters[j]) < 1e-100:
					O[j] += parameters[j]
					O_star[j] += parameters[j]
					EO[j] += E * parameters[j]

				for k in range(size_ops):
					if np.abs(parameters[j]) < 1e-100 or np.abs(parameters[k]) < 1e-100:
						Oij[j,k] += 0.0
						#print('val', parameters[j], parameters[k])
					else:
						Oij[j,k] += parameters[j] * parameters[k]

		print("Accepted: ", accepted_new)

		# Expectation values for energy and the operators
		energy /= iterations
		O /= iterations 
		O_star /= iterations 
		EO /= iterations 
		Oij /= iterations 

		print ("Iteration ", i, " with energy ", energy)

		#Regularization term to add to the matrix S diagonal elements
		# given by max(100 * 0.9^k, 0.0001)
		m = 100 * np.power(0.9, i + 1) 
		regularization_const = m if m > 0.0001 else 0.0001
		single_regularized_element = 0 	 	 	 	

		try:
			for p in range(size_ops):
				F[p] = EO[p] - energy * O_star[p]

				for q in range(size_ops):
					S[p,q] = Oij[p,q] - O_star[p] * O[q]
				single_regularized_element = regularization_const * S[p,p]

				S[p,p] += single_regularized_element
		except FloatingPointError:
			print("TOO SMALL", Oij[p,q], O_star[p], O[q])
		
		dd = np.zeros((size_ops))

		#Pseudo inverse in case S is singular
		dd = -0.2 * np.linalg.pinv(S).dot(F)

		da = np.zeros((network.num_centers))
		db = np.zeros((network.num_centers))
		dc = np.zeros((network.num_centers, network.in_dim))

		da = dd[0:network.num_centers]
		db = dd[network.num_centers:2 * network.num_centers]
		for l in range(network.num_centers):
			dc[l] = dd[network.num_centers * 2 + l * network.in_dim + l % 2]

		#print(da,db,dc)
		network.update_parameters(da,db,dc)

	#print(network.a, network.b, network.c)
	Visualize(network)
	print(network.psi(np.array([0,0])))
