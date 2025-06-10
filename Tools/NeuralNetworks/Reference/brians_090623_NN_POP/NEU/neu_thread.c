/*
 *  neu_thread.c
 *  nn_test_2
 *
 *  Created by Brian Cox on 4/18/09.
 *  Copyright 2009 Brian Cox. All rights reserved.
 *
 */

#include "neu_thread.h"

#include <fcntl.h>   // File control definitions //
#include <stdio.h>
#include <ctype.h>
#include <pthread.h>

#include "messages.h"
#include "timutils.h"
#include "simdefs.h"
#include "neural_simulation.h"
#include "carlstructs.h"
#include "init.h"

#include "main.h"

// -------------------------------------------------------

#define SEED_CONST 7
#define FEEDBACK_RATIO 0.2 //0.1
#define BCM_SLOPE 1
#define BCM_MAX 1
#define DECAY_EPSILON 0.01
#define LEARNING_RATE 0.1
#define ACTIVATION_BIAS 5

#define NORMALIZATION_FACTOR 11
#define THRESHOLD_VALUE 0.65
#define INHIBITORY_WEIGHT 2 //1.5

#define PLASTICITY 0

extern sync_t thread_initialized;
extern int NEU_Thread_Initialized;
extern int quit;
pthread_mutex_t NEU_data_mutex = PTHREAD_MUTEX_INITIALIZER;

extern int VIS_Thread_Initialized;

extern int ClampOutputFlag;
extern int LearningFlag;
extern int OutputPatternSelect; // 0-3 or 0-4 different patterns
extern float OutputPattern[NUM_OUTPUTS]; // 0-3 or 0-4 different patterns
extern int InputPatternSelect; // 0-3 or 0-4 different patterns
extern float InputPattern[NUM_OUTPUTS * NUM_INPUTS]; // 0-3 or 0-4 different patterns
// -----------------------------------------------------------------------------------
//
//		setting variable definitions
//
// -----------------------------------------------------------------------------------

int i,j; // indicies

/*
#if( NUM_NEURONS == 21 )  // NO CROSS-INHIBITORY FEEDBACK
float Nij [NUM_NEURONS] [NUM_NEURONS] = {	
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{1,1,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,1,1,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,1,1,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,1,1,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0},
{1,1,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,1,1,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,1,1,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,1,1,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0} };
#endif
*/

/*
#if( NUM_NEURONS == 21 ) 
float Nij [NUM_NEURONS] [NUM_NEURONS] = {	
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
{1,1,0,1,1,0,0,0,0,0,-1,-1,-1,0,0,0,0,0,0,0,0},
{0,1,1,0,1,1,0,0,0,-1,0,-1,-1,0,0,0,0,0,0,0,0},
{0,0,0,1,1,0,1,1,0,-1,-1,0,-1,0,0,0,0,0,0,0,0},
{0,0,0,0,1,1,0,1,1,-1,-1,-1,0,0,0,0,0,0,0,0,0},
{1,1,0,1,1,0,0,0,0,0,0,0,0,0,-1,-1,-1,0,0,0,0},
{0,1,1,0,1,1,0,0,0,0,0,0,0,-1,0,-1,-1,0,0,0,0},
{0,0,0,1,1,0,1,1,0,0,0,0,0,-1,-1,0,-1,0,0,0,0},
{0,0,0,0,1,1,0,1,1,0,0,0,0,-1,-1,-1,0,0,0,0,0},
{0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,-1,-1,-1},
{0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,-1,0,-1,-1},
{0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,-1,-1,0,-1},
{0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,-1,-1,-1,0} };
#endif
*/
extern float Nij [MAX_NUM_NEURONS] [MAX_NUM_NEURONS];

/*
 #if( NUM_NEURONS == 21 ) 
 extern float Nij [NUM_NEURONS] [NUM_NEURONS] = {	
 {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
 {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
 {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
 {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
 {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
 {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
 {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
 {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
 {0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0},
 {1,1,0,1,1,0,0,0,0,0,-1,-1,-1,0,0,0,0,0,0,0,0},
 {0,1,1,0,1,1,0,0,0,-1,0,-1,-1,0,0,0,0,0,0,0,0},
 {0,0,0,1,1,0,1,1,0,-1,-1,0,-1,0,0,0,0,0,0,0,0},
 {0,0,0,0,1,1,0,1,1,-1,-1,-1,0,0,0,0,0,0,0,0,0},
 {1,1,0,1,1,0,0,0,0,0,0,0,0,0,-1,-1,-1,0,0,0,0},
 {0,1,1,0,1,1,0,0,0,0,0,0,0,-1,0,-1,-1,0,0,0,0},
 {0,0,0,1,1,0,1,1,0,0,0,0,0,-1,-1,0,-1,0,0,0,0},
 {0,0,0,0,1,1,0,1,1,0,0,0,0,-1,-1,-1,0,0,0,0,0},
 {0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,-1,-1,-1},
 {0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,-1,0,-1,-1},
 {0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,-1,-1,0,-1},
 {0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,-1,-1,-1,0} };
 #endif
 */

//float Wij [NUM_NEURONS] [NUM_NEURONS]; // weight matrix
extern float Wij [MAX_NUM_NEURONS] [MAX_NUM_NEURONS]; // weight matrix
extern float THij [MAX_NUM_NEURONS]; // threshold array
float Ui [NUM_NEURONS]; // input neuronal activation
float Vi [NUM_NEURONS]; // output
extern float Vis_Ui [NUM_NEURONS]; // output
extern float Neur_Ui [NUM_NEURONS]; // output
float Yi [NUM_NEURONS]; // activation output
// Yi = (act func) * Vi = Ui * Wij * Nij

float OMi [NUM_NEURONS]; // sliding activation threshold

float fTemp = 0;

int time_step = 0;

float thetaY = 0;
float deltaW = 0;

// for visualization
extern float VisLayer1[9];
extern float VisLayer2[8];
extern float VisLayer3[4];

extern FILE* inputFile;

// -----------------------------------------------------------------------------------
//
//		end setting variable definitions
//
// -----------------------------------------------------------------------------------


// ---------------------------------------------
//
//		NEU Thread
//
// ---------------------------------------------
void *NEU_Thread(void *arg) 

{
	

	printf("Hello, World! From NEU Thread!!!\n");
	//NEU_Thread_Initialized = TRUE;
	
	//int i, j;
	int status;
	 
	status = pthread_mutex_lock (&thread_initialized.mutex);
	if (status != 0) 
		{
		err_abort (status, "Lock mutex");
		}
	 
	NEU_Thread_Initialized = TRUE;
	 
	status = pthread_mutex_unlock (&thread_initialized.mutex);
	if (status != 0) 
		{
		err_abort (status, "thread_initialized unlock mutex");
		}

	// ------	END INIT THREAD	-------------------------------------------
	
	// ------	SET UP NETWORK HERE	-------------------------------------------
	
	/*
	// INPUT patterns
	srand(SEED_CONST); // seed constant
	for (i = 0; i < (NUM_INPUTS * NUM_OUTPUTS); i++ )
	{
		fTemp = (rand()	% 100); // generate random activation 
		fTemp /= 100; // normalize 0-1
		InputPattern[i] = fTemp;
		printf("random input pattern %i = %f \n",i,InputPattern[i]);
	}
	*/
	
	/*
	printf("\n");
	// OUTPUTS for clamp
	for (i = 0; i < (NUM_OUTPUTS); i++ )
	{
		for (j = 0; j < (NUM_OUTPUTS); j++ )
		{
			OutputPattern[j + NUM_OUTPUTS * i] = 0;
			if(j == i)
			{
				OutputPattern[j + NUM_OUTPUTS * i] = 1;
			}
		printf("fixed output pattern %i = %f \n",(j + NUM_OUTPUTS * i),OutputPattern[(j + NUM_OUTPUTS * i)]);
		}
	}
	*/

	/*
	printf("\n");
	for (i = 0; i < (NUM_OUTPUTS * NUM_OUTPUTS); i++ )
	{
		printf("fixed output pattern %i = %f \n",i,OutputPattern[i]);
	} 
	*/
	
	srand(time(0)); // seed variable
	
	// ==================================	
	// ----------------------------------
    // INITIALIZE MATRICIES
	// ----------------------------------
	// ==================================
	
	// ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    // init input activation matrix
	// vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

	printf("\n");
	for (i = 0; i < NUM_NEURONS; i++ )
	{
		//fTemp = (rand()	% 100); // generate random activation 
		//fTemp /= 100; // normalize 0-1
		//Ui[i] = fTemp;
		//Yi[i] = fTemp; // testing
		//OMi[i] = fTemp; // testing
		
		Ui[i] = 0;
		Yi[i] = 0; // testing
		OMi[i] = THRESHOLD_VALUE; // testing	
		
		//printf("random = %f \n",Ui[i]);
	}
	
	/*
	for (i = 0; i < 9; i++ )
	{
		VisLayer1[i] = Ui[i] * 255;
	}
	
	for (i = 0; i < 8; i++ )
	{
		VisLayer2[i] = Ui[i + 9] * 255;
	}

	for (i = 0; i < 4; i++ )
	{
		VisLayer3[i] = Ui[i + 17] * 255;
	}
	*/
	
	// ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    // init weight matrix
	// vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
	//	THIS IS DONE IN MAIN.C FROM FILE
	
	/*
	// set weights to zero
	for (i = 0; i < NUM_NEURONS; i++ ) //rows
	{
		for (j = 0; j < NUM_NEURONS; j++ ) // cols
		{
			Wij[i][j] = 0;
			//printf("weight %u%u = %f \n",i,j,Wij[i][j]);
		}
	}
	*/
	
	/*
	//randomize weights
	for (i = 0; i < NUM_NEURONS; i++ )
	{
		for (j = 0; j < NUM_NEURONS; j++ )
		{
			if( i > j )
			{
				fTemp = (rand()	% 100); // generate random activation 
				fTemp /= 20; // normalize 0-2
				Wij[i][j] = fTemp;
				Wij[i][j] *= Nij[i][j]; 
				
				// RECIPRICAL FEEDBACK CONNECTIONS
				fTemp = Wij[i][j];
				fTemp *= FEEDBACK_RATIO;
				Wij[j][i] = fTemp;

			}
			//printf("weight %u%u = %f \n",i,j,Wij[i][j]);
		}
	}
	*/
	
	// ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    // setup inhibitory neurons
	// vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
	//	NOT NEEDED FOR THIS
	/*
	for (i = (NUM_NEURONS-NUM_OUTPUTS-1); i < NUM_NEURONS; i++ )
	{	
		for (j = (NUM_NEURONS-NUM_OUTPUTS-1); j < NUM_NEURONS; j++ )
		{
			Wij[i][j] = INHIBITORY_WEIGHT;
			if(i == j)
			{
				Wij[i][j] = 0;
			}
		}
	}
	*/
	
	/*
	//print weights
	printf("weight matrix = \n");
	for (i = 0; i < NUM_NEURONS; i++ )
	{
		for (j = 0; j < NUM_NEURONS; j++ )
		{
			printf("%f ",Wij[i][j]);
		}
		printf("\n");
	}	
	*/
	
	// ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    // init connectivity matrix
	// vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
	/*
	// mirror connectivity
	// RECIPRICAL CONNECTIONS
	for (i = 0; i < NUM_NEURONS; i++ )
	{
		for (j = 0; j < NUM_NEURONS; j++ )
		{
			if( i > j )
			{
				Nij[j][i] = Nij[i][j];
			}
			//printf("weight %u%u = %f \n",i,j,Wij[i][j]);
		}
	}
	*/
	
	/*
	//print connectivity
	printf("connectivity matrix = \n");
	for (i = 0; i < NUM_NEURONS; i++ )
	{
		for (j = 0; j < NUM_NEURONS; j++ )
		{
			printf("%f ",Nij[i][j]);
		}
		printf("\n");
	}
	*/
	
	// ------	END SET UP	-------------------------------------------
	
	usleep (100000);
	
	while (quit == NO_EXIT) 
		{
			//printf("hello from NEU loop\n");
			
			//usleep (1000);
			
			status = pthread_mutex_lock (&NEU_data_mutex);
			if (status != 0) 
			{
				printf("hello from abort!! %d \n", status);
				err_abort (status, "Lock mutex");
			}
			
			//printf("hello from NEU loop");
			
			// ==================================	
			// ----------------------------------
			// SET INPUT ACTIVATION
			// ----------------------------------
			// ==================================
			
			//Ui[0] = 0.5;
			//Ui[53] = 0.5;
			
			//Ui[0] = Neur_Ui[0];
			//Ui[53] = Neur_Ui[53];
			
			Ui[0] = Vis_Ui[0];
			Ui[53] = Vis_Ui[53];
			
			// ==================================	
			// ----------------------------------
			// EVALUATE NEURONAL ACTIVATION
			// ----------------------------------
			// ==================================
			
			/*
			// ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
			// evaluate Ui * Wij = Vi
			// vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
			for (i = 0; i < NUM_NEURONS; i++ )
			{
				Vi[i] = 0;
				for (j = 0; j < NUM_NEURONS; j++ )
				{
					fTemp = Ui[j]; // input
					fTemp *= Wij[i][j]; // weights
					//fTemp *= (Nij[i][j]) * (Nij[i][j]); // connectivity
					Vi[i] += fTemp; // output
				}
			}	
			*/
			
			// ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
			// evaluate Ui * Wij = Vi
			// vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
			for (i = 0; i < NUM_NEURONS; i++ )
			{
				Vi[i] = 0;
				for (j = 0; j < NUM_NEURONS; j++ )
				{
					if( (Nij[i][j] == 1) || (Nij[i][j] == -1))
					{
					fTemp = Ui[j]; // input
					fTemp *= Wij[i][j]; // weights
					//fTemp *= (Nij[i][j]) * (Nij[i][j]); // connectivity
					Vi[i] += fTemp; // output
					}
				}
			}	
			
			// ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
			// threshhold activation function
			// vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
			for (i = 0; i < NUM_NEURONS; i++ )
			{				
				fTemp = Vi[i];
				//fTemp -= ACTIVATION_BIAS;
				fTemp -= THij[i]; // changed 090624
				fTemp *= -1;
				fTemp *= 0.98;// testing
				Yi[i] = 1 / (1 + exp(fTemp));
			}

			// ==================================	
			// ----------------------------------
			// CLAMP OUTPUT FOR SUPERVISED LEARNING
			// ----------------------------------
			// ==================================


			/*
			// ------------------
			// UPDATE THRESHOLD
			// ------------------
			if(LearningFlag)
			{
				for (i = 0; i < NUM_NEURONS; i++ )
				{
					for (j = 0; j < NUM_NEURONS; j++ )
					{
						OMi[i] = THRESHOLD_VALUE; // 0.65; //1.0;//0.5;
					}
				}
			}
			*/
			
			/*
			// ------------------
			// SETUP CONTRASTED OUTPUT
			// ------------------
			if(ClampOutputFlag) 
			{
				for (i = 0; i < 4; i++ )
				{
					Yi[i + 17] = 0;
					//printf("fixed output pattern %i = %f \n",i,OutputPattern[i + (4 * OutputPatternSelect)]);
				}
				Yi[OutputPatternSelect + 17] = 1;
			}
			*/
			 
			// ==================================	
			// ----------------------------------
			// MODIFY WEIGHTS WITH BCM RULE
			// ----------------------------------
			// ==================================
			
#if PLASTICITY
			if(LearningFlag)
			{
				//printf("\n");
				for (i = 0; i < NUM_NEURONS; i++ )
				{
					for (j = 0; j < NUM_NEURONS; j++ )
					{
						if( i > j ) // feedforward connections only
						{
							if (Nij[i][j] == 1) // check connectivity
							{
								if (Yi[i] > (OMi[i] / 2 )) // second half of BCM curve
								{
									thetaY = (Yi[i] - OMi[i] ) * BCM_SLOPE;
									if (thetaY > BCM_MAX )
									{
										thetaY = BCM_MAX;
									}
								}
								else
								{
									thetaY = (-1) * Yi[i] * BCM_SLOPE; // first half of BCM curve
								}
								
								deltaW = 0; // init
								deltaW += thetaY;
								deltaW *= ( Ui[j] ); // NOTE: j INDEX !!! pre-synaptic cell
								deltaW -= DECAY_EPSILON * (Wij[i][j]); // decay term
								deltaW *= LEARNING_RATE; 
								Wij[i][j] += deltaW ; // modify weight
								Wij[i][j] *= Nij[i][j]; // make sure there is a connection
								
								if (Wij[i][j] < 0)
								{
									Wij[i][j] = 0; // floor of zero
								}

								Wij[j][i] = Wij[i][j]; //
								Wij[j][i] *= FEEDBACK_RATIO;

								//printf("%f ",deltaW);
							}
							else
							{
								Wij[i][j] = 0; // floor of zero
								Wij[j][i] = 0; //
								//printf("0.000000 ");
							}
						}
						else
						{
							//printf("0.000000 ");
						}
					}
					//printf("\n");

				} // end BCM rule
				
			} // end Learning Flag
#endif		

			// ==================================	
			// ----------------------------------
			// MODIFY WEIGHTS USING NORMALIZATION
			// ----------------------------------
			// ==================================
			
#if PLASTICITY			
			if(LearningFlag)
			{
				//printf("\n");
				for (i = 0; i < NUM_NEURONS; i++ )
				{
					fTemp = 0; // weight sum
					for (j = 0; j < NUM_NEURONS; j++ )
					{
						if( i > j ) // feedforward connections only
						{
							if(Nij[i][j] == 1)
							{
								fTemp += Wij[i][j];
							}
						}
					}
					fTemp /= NORMALIZATION_FACTOR; // normalizing sum of weights
					
					for (j = 0; j < NUM_NEURONS; j++ )
					{
						if( i > j ) // feedforward connections only
						{
							if (fTemp > 0)
							{
							Wij[i][j] /= fTemp;
							Wij[i][j] *= Nij[i][j];
							}

							Wij[j][i] = Wij[i][j]; //
							Wij[j][i] *= FEEDBACK_RATIO;

						}
					}
				}
			}
#endif							


			// ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
			// setup inhibitory neurons
			// vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
			/*
			for (i = 0; i < NUM_NEURONS; i++ )
			{	
				for (j = 0; j < NUM_NEURONS; j++ )
				{
					if(Nij[i][j] == -1)
					{
						Wij[i][j] = INHIBITORY_WEIGHT;
					}

				}
			}
			*/
			
			// ==================================	
			// ----------------------------------
			// UPDATE INPUT ACTIVATION
			// ----------------------------------
			// ==================================
			
			for (i = 0; i < NUM_NEURONS; i++ )
			{
				//if ( i > (NUM_INPUTS - 1))
				//{ 
					// PERSISTANCE
					fTemp = Ui[i] * 0.10;
					Ui[i] = Yi[i] * 0.90;
					Ui[i] += fTemp;
			
					// NO PERSISTANCE
					//Ui[i] = Yi[i]; // update activation for all neurons except input neurons

				//}
			}
			
			// ------------------
			// SWITCH INPUT IMAGE BASED ON KEYSTROKE
			// ------------------	
			/*
			for (i = 0; i < NUM_INPUTS; i++ )
			{
				Ui[i] = InputPattern[i + NUM_OUTPUTS * InputPatternSelect];
			}
			*/
			
			// ==================================	
			// ----------------------------------
			// UPDATE VISUALIZATION
			// ----------------------------------
			// ==================================
			
			for (i = 0; i < NUM_NEURONS; i++ )
			{
				Neur_Ui[i] = Ui[i];
			}
			
			Ui[0] = Neur_Ui[0];
			Ui[53] = Neur_Ui[53];
			
			/*
			for (i = 0; i < 9; i++ )
			{
				VisLayer1[i] = Ui[i] * 255;
			}
			
			for (i = 0; i < 8; i++ )
			{
				VisLayer2[i] = Ui[i + 9] * 255;
			}
			
			for (i = 0; i < 4; i++ )
			{
				VisLayer3[i] = Ui[i + 17] * 255;
			}
			*/
			
		// ---------------------------------------------
		//
		//		PUT NEU MUTEX LOCKED CODE HERE
		//
		// ---------------------------------------------
			
		status = pthread_mutex_unlock (&NEU_data_mutex);
		if (status != 0) 
			{
			err_abort (status, "Unlock mutex");
			}


		usleep (100);

		}  // end while quit == no exit

	fprintf (stderr, "NEU thread exiting\n");
	
}