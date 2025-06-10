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
//#define DECAY_EPSILON 0.01
//#define DECAY_EPSILON 0.001
#define DECAY_EPSILON 0.0
#define LEARNING_RATE 0.02
//#define LEARNING_RATE 0.4
//#define LEARNING_RATE 0.01
#define ACTIVATION_BIAS 5

#define NORMALIZATION_FACTOR 11
#define POP_NORM_FACTOR 100
#define THRESHOLD_VALUE 0.65
//#define THRESHOLD_VALUE 0.65
#define INHIBITORY_WEIGHT 2 //1.5

#define PLASTICITY 0
#define POP_PLASTIC 0
#define POP_PLASTIC_NORM 0

#define CEREBELLAR_PLASTIC 1
#define HOMEOSTASIS_PLASTIC 1

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
int ni = 0, nj = 0;

extern float Nij [MAX_NUM_NEURONS] [MAX_NUM_NEURONS];

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
extern int printWeightFlag;
extern FILE* outputFile;

int i_post,j_pre; // indicies
int learningCountdown = 0;
int normalizeFlag = 0;
extern int homeostasisFlag;
float maxNeuronActivation = 0;
#define MAX_NEURON_ACTIVATION 0.9;
float popWeight = 2;

extern int RandomInputFlag;
extern int BlankInputFlag;

extern float VisWij [MAX_NUM_NEURONS] [MAX_NUM_NEURONS]; // weight matrix

extern float learningRate;

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
	for (ni = 0; ni < NUM_NEURONS; ni++ )
	{
		
		Ui[ni] = 0;
		Yi[ni] = 0; // testing
		OMi[ni] = THRESHOLD_VALUE; // testing	
		
		//printf("random = %f \n",Ui[i]);
	}
	

	
	// ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    // init weight matrix
	// vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
	//	THIS IS DONE IN MAIN.C FROM FILE
	
	
	// ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    // setup inhibitory neurons
	// vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

	
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
			
			//usleep (1000); //sleep at end
			
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
			
			if(ClampOutputFlag)
			{
				//Ui[275] = Vis_Ui[275];
				//Ui[275] = Neur_Ui[275];
				//OMi[275] = Neur_Ui[275];
				//OMi[275] = Vis_Ui[275];
			}
			
			
			// ==================================	
			// ----------------------------------
			// EVALUATE NEURONAL ACTIVATION
			// ----------------------------------
			// ==================================
			
			
			// ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
			// evaluate Ui * Wij = Vi
			// vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
			for (ni = 0; ni < NUM_NEURONS; ni++ )
			{
				Vi[ni] = 0;
				for (nj = 0; nj < NUM_NEURONS; nj++ )
				{
					if( (Nij[ni][nj] == 1) || (Nij[ni][nj] == -1))
					{
					fTemp = Ui[nj]; // input
					fTemp *= Wij[ni][nj]; // weights
					Vi[ni] += fTemp; // output
					}
				}
			}	
			
			// ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
			// threshhold activation function
			// vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
			for (ni = 0; ni < NUM_NEURONS; ni++ )
			{				
				fTemp = Vi[ni];
				//fTemp -= ACTIVATION_BIAS;
				fTemp -= THij[ni]; // changed 090624
				fTemp *= -1;
				fTemp *= 0.98;// testing
				Yi[ni] = 1 / (1 + exp(fTemp));
			}

			// ==================================	
			// ----------------------------------
			// CLAMP OUTPUT FOR SUPERVISED LEARNING
			// ----------------------------------
			// ==================================

			if(ClampOutputFlag)
			{
				/*
				//Ui[275] = Vis_Ui[275];
				//Ui[275] = Neur_Ui[275];
				//OMi[275] = Neur_Ui[275];
				OMi[275] = Yi[275]; // actual output
				OMi[275] -= Vis_Ui[275]; // desired output
				OMi[275] /= 2; // average
				//OMi[275] += 0.5; // center around 0.5 neutral
				OMi[275] += 0.65; // center around 0.5 neutral
				*/
				
				OMi[275] = 2 * Yi[275];
				OMi[275] -= Vis_Ui[275];
				if( OMi[275] < 0)
				{
					OMi[275] = 0;
				}
				if(OMi[275] > 1)
				{
					OMi[275] = 1;
				}
			}
	
			// ==================================	
			// ----------------------------------
			// MODIFY WEIGHTS WITH CEREBELLAR LEARNING RULE
			// ----------------------------------
			// ==================================
			
#if CEREBELLAR_PLASTIC
			if(LearningFlag)
			{
				learningCountdown += 1;
				if (learningCountdown > 30)
				{
					i_post = 275;
					if (i_post == 275)
					{
						for (j_pre = 106; j_pre < 275; j_pre++ )
						{
							if ((Nij[i_post][j_pre] == 1)) // check connectivity
							{
								thetaY = Vis_Ui[275]; // desired output
								thetaY -= Yi[275]; // actual output
								
								/*
								// OLD
								deltaW = 0; // init
								deltaW += thetaY;
								deltaW *= ( Ui[j_pre] ); // NOTE: j INDEX !!! pre-synaptic cell
								deltaW -= DECAY_EPSILON * (Wij[i_post][j_pre]); // decay term
								deltaW *= LEARNING_RATE; 
								Wij[i_post][j_pre] += deltaW ; // modify weight
								*/
								
								
								// NEW 090904
								deltaW = 0; // init
								deltaW += thetaY;
								deltaW *= ( Ui[j_pre] ); // NOTE: j INDEX !!! pre-synaptic cell
								//deltaW *= ( Ui[j_pre] ); // squared
								deltaW *= learningRate; 
								
								deltaW -= DECAY_EPSILON * (Wij[i_post][j_pre]); // decay term
								//deltaW *= LEARNING_RATE; 
								Wij[i_post][j_pre] += deltaW ; // modify weight
								
								
								if (Wij[i_post][j_pre] < 0)
								{
									Wij[i_post][j_pre] = 0; // floor of zero
								}
								
								//printf("%f ",deltaW);
							}
							
						}
						//printf("\n");
						
					} // end BCM rule
					
					learningCountdown = 0;
					normalizeFlag = 1;
					
				} // end learning countdown
				//learningCountdown = 0;
				//normalizeFlag = 1;
			} // end Learning Flag
#endif	
			
			// ==================================	
			// ----------------------------------
			// MODIFY WEIGHTS WITH BCM RULE
			// ----------------------------------
			// ==================================
		
#if POP_PLASTIC
			if(LearningFlag)
			{
				learningCountdown += 1;
				if (learningCountdown > 9)
				{
				//}
			
				//printf("\n");
				//for (i = 0; i < NUM_NEURONS; i++ )
				//for (i_post = 315; i_post < 328; i_post++ )
				i_post = 275;
				if (i_post == 275)
				//for (i = 106; i < 275; i++ )
				{
					printf("Om[275] = %f\n", OMi[275]);
					//for (j = 0; j < NUM_NEURONS; j++ )
					for (j_pre = 106; j_pre < 275; j_pre++ )
					//for (j = 315; j < 328; j++ )
					{
						if ((Nij[i_post][j_pre] == 1)) // check connectivity
						{
							if (Yi[i_post] > (OMi[i_post] / 2 )) // second half of BCM curve
							{
								thetaY = (Yi[i_post] - OMi[i_post] ) * BCM_SLOPE;
								if (thetaY > BCM_MAX )
								{
									thetaY = BCM_MAX;
								}
							}
							else
							{
								thetaY = (-1) * Yi[i_post] * BCM_SLOPE; // first half of BCM curve
							}
							
							deltaW = 0; // init
							deltaW += thetaY;
							deltaW *= ( Ui[j_pre] ); // NOTE: j INDEX !!! pre-synaptic cell
							deltaW -= DECAY_EPSILON * (Wij[i_post][j_pre]); // decay term
							deltaW *= LEARNING_RATE; 
							Wij[i_post][j_pre] += deltaW ; // modify weight
							//Wij[i][j] *= Nij[i][j]; // make sure there is a connection
							
							
							if (Wij[i_post][j_pre] < 0)
							{
								Wij[i_post][j_pre] = 0; // floor of zero
							}
							
							//if (Wij[i_post][j_pre] > 5)
							//{
							//	Wij[i_post][j_pre] = 5; // floor of zero
							//}
							
							//Wij[j][i] = Wij[i][j]; //
							//Wij[j][i] *= FEEDBACK_RATIO;
							
							//printf("%f ",deltaW);
						}

					}
					//printf("\n");
					
				} // end BCM rule
			
					learningCountdown = 0;
					normalizeFlag = 1;
					
				} // end learning countdown
				//learningCountdown = 0;
				//normalizeFlag = 1;
			} // end Learning Flag
#endif				


			// ==================================	
			// ----------------------------------
			// MODIFY WEIGHTS USING NORMALIZATION
			// ----------------------------------
			// ==================================
			
#if POP_PLASTIC_NORM			
			//if(LearningFlag)
			if(normalizeFlag == 1)
			{
				//printf("\n");
				//for (i = 0; i < NUM_NEURONS; i++ )
				//for (i_post = 315; i_post < 328; i_post++ ) // post-synaptic 
				//for (i = 106; i < 275; i++ )
				i_post = 275;
				if (i_post == 275)
				{
					fTemp = 0; // weight sum
					//for (j = 0; j < NUM_NEURONS; j++ )
					for (j_pre = 106; j_pre < 275; j_pre++ ) // pre synaptic
					//for (j = 315; j < 328; j++ )
					{
						if((Nij[i_post][j_pre] == 1))
						{
							//printf("index = %i",j);
							fTemp += Wij[i_post][j_pre];
						}

					}
					printf("sum = %f\n",fTemp);
					
					fTemp /= POP_NORM_FACTOR; // normalizing sum of weights
					
					//for (j = 0; j < NUM_NEURONS; j++ )
					for (j_pre = 106; j_pre < 275; j_pre++ )
					//for (j = 315; j < 328; j++ )
					{
							if (fTemp > 0)
							{
								Wij[i_post][j_pre] /= fTemp;
								//Wij[i][j] *= Nij[i][j];
							}
							
							//Wij[j][i] = Wij[i][j]; //
							//Wij[j][i] *= FEEDBACK_RATIO;
					}
				}
				normalizeFlag = 0;
			}
#endif	
			
	
#if HOMEOSTASIS_PLASTIC			
			if(homeostasisFlag == 1)
			{
				learningCountdown += 1;
				if (learningCountdown > 9)
				{
					maxNeuronActivation = 0;
					for (i_post = 106; i_post < 275; i_post++ ) // pre synaptic
					{
						maxNeuronActivation += Yi[i_post]; //average activation
						//if (Yi[i_post] > maxNeuronActivation)
						//{
						//	maxNeuronActivation = Yi[i_post]; // find maximum activation
						//	printf("max activation = %f %i \n", maxNeuronActivation, i_post);
						//}
					}
					
					//thetaY = 30; //0.8 ; //MAX_NEURON_ACTIVATION; // desired output
					//thetaY = 7.75; //0.8 ; //MAX_NEURON_ACTIVATION; // desired output // USING CENTER SURROUND WEIGHTING
					thetaY = 15.0; //0.8 ; //MAX_NEURON_ACTIVATION; // desired output // USING CENTER SURROUND WEIGHTING
					thetaY -= maxNeuronActivation; // actual output
					
					deltaW = 0; // init
					deltaW += thetaY;
					deltaW *= 0.01; // LEARNING_RATE;
					printf("deltaW = %f \n", deltaW);
					popWeight += deltaW;
					
					for (i_post = 106; i_post < 275; i_post++ ) // pre synaptic
					{
						//for (j_pre = 93; j_pre < 106; j_pre++ ) // pre synaptic
						for (j_pre = 80; j_pre < 106; j_pre++ ) // pre synaptic
						{
							if((Nij[i_post][j_pre] == 1))
							{
								Wij[i_post][j_pre] = popWeight;
								
								//Wij[i_post][j_pre] += deltaW ; // modify weight
								
								//if (Wij[i_post][j_pre] < 0)
								//{
									//Wij[i_post][j_pre] = 0; // floor of zero
								//}
							}
						}
						//for (j_pre = 40; j_pre < 53; j_pre++ ) // pre synaptic
						for (j_pre = 27; j_pre < 53; j_pre++ ) // pre synaptic
						{
							if((Nij[i_post][j_pre] == 1))
							{
								Wij[i_post][j_pre] = popWeight;
								//Wij[i_post][j_pre] += deltaW ; // modify weight
								
								//if (Wij[i_post][j_pre] < 0)
								//{
									//Wij[i_post][j_pre] = 0; // floor of zero
								//}
							}
						}
					}
					printf("weight1 = %f \n", Wij[106][27]);
					printf("weight2 = %f \n", Wij[106][40]);
					learningCountdown = 0;
				}
				
			}
#endif
			// ==================================	
			// ----------------------------------
			// UPDATE INPUT ACTIVATION
			// ----------------------------------
			// ==================================
			
			for (i_post = 0; i_post < NUM_NEURONS; i_post++ )
			{
				//if ( i > (NUM_INPUTS - 1))
				//{ 
					// PERSISTANCE
	
					fTemp = Ui[i_post] * 0.10;
					Ui[i_post] = Yi[i_post] * 0.90;
					Ui[i_post] += fTemp;
				
					// NO PERSISTANCE
					//Ui[i] = Yi[i]; // update activation for all neurons except input neurons

				//}
			}
			
			if(BlankInputFlag)
			{
				for (i_post = 0; i_post < NUM_NEURONS; i_post++ )
				{
					Ui[i_post] = 0;
					Yi[i_post] = 0;
				}
				BlankInputFlag = 0;
			}
			
			// ==================================	
			// ----------------------------------
			// UPDATE VISUALIZATION
			// ----------------------------------
			// ==================================
			
			for (i_post = 0; i_post < NUM_NEURONS; i_post++ )
			{
				Neur_Ui[i_post] = Ui[i_post];
			}
			
			for (i_post= 0; i_post < NUM_NEURONS; i_post++ )
			{
				for (j_pre= 0; j_pre < NUM_NEURONS; j_pre++ )
				{
					VisWij[i_post][j_pre] = Wij[i_post][j_pre];
				}
			}
			
			Ui[0] = Neur_Ui[0];
			Ui[53] = Neur_Ui[53];
			//Ui[275] = Neur_Ui[275];
			
			if(ClampOutputFlag)
			{
				//Ui[275] = Neur_Ui[275];
				//OMi[275] = Neur_Ui[275];
			}
			
			if(printWeightFlag)
			{
				
				for (i_post	= 106; i_post < 275; i_post++ )
					//for (i = 315; i < 328; i++ )
					//for (i = 106; i < 275; i++ )
				{
					fprintf(outputFile, "input Neuron = %i\n", i_post);
					//for (j = 0; j < NUM_NEURONS; j++ )
					for (j_pre = 250; j_pre < 275; j_pre++ )
					//for (j = 106; j < 275; j++ )
					{
						printf("%f ",Wij[i_post][j_pre]);
						fprintf(outputFile, "%f ", Wij[i_post][j_pre]);	
					}
					printf("\n");
					fprintf(outputFile, "\n");
				}
				
				/*		
				for (i = 320; i < 323; i++ ) // post-synaptic
				{
					fprintf(outputFile, "input Neuron = %i\n", i);
					for (j = 116; j < 265; j++ ) // pre synaptic
					{
						printf("%f ",Wij[i][j]);
						fprintf(outputFile, "%f ", Wij[i][j]);
					}
					printf("\n");
					fprintf(outputFile, "\n");
				}
				*/
				
				printWeightFlag = 0;
			}
			

			
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


		usleep (10);

		}  // end while quit == no exit

	fprintf (stderr, "NEU thread exiting\n");
	
	return(0);
}