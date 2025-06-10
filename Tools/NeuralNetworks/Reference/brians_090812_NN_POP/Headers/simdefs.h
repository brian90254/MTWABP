#ifndef SIMDEFS
#define SIMDEFS

#include <math.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "errors.h"

#define MAX_GROUPS 		60
#define MAX_GROUP_HEIGHT	120
#define MAX_GROUP_WIDTH		160
#define MAX_NEURONS		307200 	// maximum number of neurons per group
#define MAX_PROJECTIONS		256	// maximum number of allowed projections
#define MAX_SYNAPSES		1000000	// maximum of 1 million synapses per projection
#define GROUP_MOTOR		0
#define GROUP_NEURAL		1
#define GROUP_PERIPHERAL	2
#define GROUP_VISUAL		3

#define MAX_TIME			10000000
#define WAIT_SIM_IO			40
 
#ifndef BOOL
#define BOOL	int
#endif

#ifndef FALSE
#define FALSE	0
#endif

#ifndef TRUE
#define TRUE	1
#endif

#ifndef ZERO
#define ZERO	0.00000001	// used for floating pt comparison
#endif
#define MIN_CELL_ACTIVITY	0.001

#ifndef PI
#define PI	3.14159265
#endif

#define THREAD_NAME_GUI		"GUI"
#define THREAD_NAME_MOTOR	"MOTOR"
#define THREAD_NAME_PERIPHERAL	"PERIPHERAL"
#define THREAD_NAME_VISUAL	"VISUAL"

#define NO_EXIT			0
#define EXIT_NO_SAVE		1
#define EXIT_SAVE_ALL		2
#define EXIT_SAVE_PLASTIC	3

#endif



