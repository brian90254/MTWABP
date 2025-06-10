#ifndef NEURALSIMULATION
#define NEURALSIMULATION
#include <stdio.h>
#include "simdefs.h"

//@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
//@                                                File: neural_simulation.h @
//@                                                                          @
//@  Title: Neural Simulation Header File                                    @
//@                                                                          @
//@  Description: Contains the structures and routines for the neural        @
//@               simulation.                                                @
//@                                                                          @
//@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

#define CONN_ALLOC_CHUNK        15000   // allocate 15,000 connections at a time

// structure containing all the synaptic connection information for a given conn. type
typedef struct Conn_Struct {
	int group_from;		// presynaptic group identifier
	int neuron_from;	// presynaptic neuron identifier
	int uniqid;		// unique identifier used for saving weights
	float learning_rate;	// learning rate for the connection
	float influence;	// connection specific scale factor for weight normalization.
	float w[2];		// current synaptic weight of the connection
} Conn_T;

// structure containing all the neuronal unit information
typedef struct Neuron_Struct {
	float s[2];	// neural activity
	int num_conn;
	float persistence;	// persistence of neural activity
	Conn_T *conn;	// connections into this neuron
	BOOL plastic;	// TRUE if this neuron has ANY plastic connections.  Used to optimize code.
} Neuron_T;

// structure containing neuron group information
typedef struct Group_Struct {
	int height;
	int width;
	int type;
	Neuron_T *neuron;		// array of pointers to neurons in the group
} Group_T;

void Neural_Simulation ();

#endif
