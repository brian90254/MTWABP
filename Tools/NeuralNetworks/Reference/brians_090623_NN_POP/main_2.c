/*
 *  main.c
 *
 *  Created by Brian Cox on 4/18/09.
 *  Copyright 2009 Brian Cox. All rights reserved.
 *
 */

#include <stdlib.h>
#include <stdio.h>
#include <pthread.h>
#include <unistd.h>


#include "Headers/messages.h"
#include "Headers/timutils.h"
#include "Headers/simdefs.h"
#include "Headers/neural_simulation.h"
#include "Headers/carlstructs.h"
#include "Headers/init.h"

#include "main.h"


// Save weights flags
int save_plastic = FALSE;


int VIS_Thread_Initialized = FALSE;
void *VIS_Thread(void *arg); 
extern pthread_mutex_t VIS_data_mutex;

int NEU_Thread_Initialized = FALSE;
void *NEU_Thread(void *arg); 
extern pthread_mutex_t NEU_data_mutex;



sync_t thread_initialized = {PTHREAD_MUTEX_INITIALIZER, PTHREAD_COND_INITIALIZER, ""};
// WHERE IS THIS DEFINED?????

int quit = NO_EXIT;
int main_state;
struct timeval tim_start_cycle, tim_finish_cycle;
struct timezone tz;
long cycle_time = 0;
long cycle = 0;
long cycle_max;
int save_weights = FALSE; 

int externLoops = 0;

float fTime;

pthread_mutex_t display_status = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t carl_cmd_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t carl_data_mutex = PTHREAD_MUTEX_INITIALIZER;

FILE* inputFile;
FILE* outputFile;
FILE* inputWeightFile;
FILE* outputWeightFile;
FILE* inputThreshFile;

// FLAGS
char flagGPS = 0, flagCAN = 0, flagMOT = 0, flagNAV = 0;
char flagInputFromFile = 0;

// for visualization
float VisLayer1[9];
float VisLayer2[8];
float VisLayer3[4];

int ClampOutputFlag = 0;
int LearningFlag = 0;
int OutputPatternSelect = 0; // 0-3 or 0-4 different patterns
float OutputPattern[NUM_OUTPUTS]; // 0-3 or 0-4 different patterns
int InputPatternSelect = 0; // 0-3 or 0-4 different patterns
float InputPattern[NUM_OUTPUTS * NUM_INPUTS]; // 0-3 or 0-4 different patterns

#define MAXFLDS 400     /* maximum possible number of fields */
#define MAXFLDSIZE 32   /* longest possible field + 1 = 31 byte field */
void parse( char *record, char *delim, char arr[][MAXFLDSIZE],int *fldcnt);
char tmp[1024]={0x0};
int fldcnt=0;
char arr[MAXFLDS][MAXFLDSIZE]={0x0};
int recordcnt=0;

//#define MAX_NUM_NEURONS 25
float Nij [MAX_NUM_NEURONS] [MAX_NUM_NEURONS];
int i,j;
int i_row, j_col;
float Wij [MAX_NUM_NEURONS] [MAX_NUM_NEURONS]; // weight matrix
float THij [MAX_NUM_NEURONS]; // threshold array
float Vis_Ui [NUM_NEURONS]; // output
float Neur_Ui [NUM_NEURONS]; // output

int main (int argc, const char * argv[])

{
	if (argc != 4)
	{
		fprintf (stderr, "USAGE: ./nn_alpha_1 connectivity.txt weights.txt threshold.txt\n");
		exit (1);
	}
	
	else
	{
		flagInputFromFile = 1;
		
		if ((inputFile = fopen (argv[1], "r")) == NULL) 
		{
			fprintf (stderr, "ERROR: cannot open data file\n");
			exit (1);
		}
		
		if ((inputWeightFile = fopen (argv[2], "r")) == NULL) 
		{
			fprintf (stderr, "ERROR: cannot open data file\n");
			exit (1);
		}
		
		if ((inputThreshFile = fopen (argv[3], "r")) == NULL) 
		{
			fprintf (stderr, "ERROR: cannot open data file\n");
			exit (1);
		}
	}
	
	
	outputFile = fopen ("myfile.txt","w"); // text file for writing formatted CAN data to
	
	// --------------------------------
	//	INPUT CONNECTIVITY MATRIX
	// --------------------------------	
	i_row = 0;
	j_col = 0;
	
	while(fgets(tmp,sizeof(tmp),inputFile)!=0) /* read a record */
	{

		j_col = 0;
		
		parse(tmp,",",arr,&fldcnt);    /* whack record into fields */
		for(j_col = 0; j_col < fldcnt; j_col++)
		{                              /* print each field */
			//printf("column number: %3d==%i",j_col,atoi(arr[j_col]));
			Nij[i_row][j_col] = atoi(arr[j_col]);
			//printf("\tNeuron ==%f\n",Nij[i_row][j_col]);
		}

		
		i_row++;
		
	}
	
	//print connectivity
	printf("connectivity matrix = \n");
	for (i = 0; i < NUM_NEURONS; i++ )
	{
		for (j = 0; j < NUM_NEURONS; j++ )
		{

		}

	}
	// --------------------------------
	//	end connectivity matrix
	// --------------------------------	
	
	// --------------------------------
	//	INPUT WEIGHT MATRIX
	// --------------------------------	
	i_row = 0;
	j_col = 0;
	
	while(fgets(tmp,sizeof(tmp),inputWeightFile)!=0) /* read a record */
	{
		
		j_col = 0;
		
		printf("row number: %d\n", i_row);
		parse(tmp,",",arr,&fldcnt);    /* whack record into fields */
		for(j_col = 0; j_col < fldcnt; j_col++)
		{                              /* print each field */

			Wij[i_row][j_col] = atof(arr[j_col]);

		}

		
		i_row++;
		
	}
	
	//print weights
	printf("weight matrix = \n");
	for (i = 0; i < NUM_NEURONS; i++ )
	{
		for (j = 0; j < NUM_NEURONS; j++ )
		{

		}

	}
	// --------------------------------
	//	end weight matrix
	// --------------------------------		
	
	// --------------------------------
	//	INPUT THRESHOLD ARRAY
	// --------------------------------	
	i_row = 0;
	j_col = 0;
	
	while(fgets(tmp,sizeof(tmp),inputThreshFile)!=0) /* read a record */
	{
		
		j_col = 0;
		
		parse(tmp,",",arr,&fldcnt);    /* whack record into fields */

			THij[i_row] = atof(arr[0]);

		i_row++;
		
	}
	
	//print threshold
	printf("threshold array = \n");
	for (i = 0; i < NUM_NEURONS; i++ )
	{

	}
	// --------------------------------
	//	end threshold array
	// --------------------------------	
	
    // insert code here...
    printf("Hello, World! main...\n");
	
	
	int status;

	pthread_t VIS_thread_id;
	pthread_t NEU_thread_id;
	
	
	// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
	//
	// Create threads
	//
	// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
	
	
	status = pthread_create (&VIS_thread_id, NULL, VIS_Thread, NULL);
	if (status != 0) 
	{
		err_abort (status, "Create VIS_Thread");
	}

	
	status = pthread_create (&NEU_thread_id, NULL, NEU_Thread, NULL);
	if (status != 0) 
	{
		err_abort (status, "Create NEU_Thread");
	}

	
	// ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

	
	main_state = MAIN_NEURAL;
	
	while (main_state != MAIN_EXIT) 
	{
		
		switch (main_state) 
		{
			default:				
			case MAIN_NEURAL:
				usleep (100);
				if(	NEU_Thread_Initialized == TRUE) // for testing, this is set after ESC visual thread
				{
					printf("state = %i\n", main_state);
					main_state = MAIN_VISUAL;  // testing only
				}
				break;
				
			case MAIN_VISUAL:
				usleep (100);
				if(	VIS_Thread_Initialized == TRUE) // for testing, this is set after ESC visual thread
				{
					printf("state = %i\n", main_state);
					main_state = MAIN_EXIT;  // testing only
				}

				break;
		} // end switch main_state
		
	} // end while not exit	
	
	
	quit = 1; // used to stop all threads
	
	usleep (500000); // allow time for other threads to quit
	
	printf("state = %i\n", main_state);
	
	fprintf(stderr,"Main exit\n");
	
    return 0;
}


void parse( char *record, char *delim, char arr[][MAXFLDSIZE],int *fldcnt)
{
    char*p=strtok(record,delim);
	
    int fld=0;
	
    while(p)
    {
        strcpy(arr[fld],p);
		fld++;

		p=strtok(NULL,",");

	}		
	*fldcnt=fld;
}
