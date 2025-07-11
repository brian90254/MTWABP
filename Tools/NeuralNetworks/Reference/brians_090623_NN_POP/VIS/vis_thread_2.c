/*
 *  vis_thread.c
 *
 *  Created by Brian Cox on 1/27/09.
 *  Copyright 2009 Brian Cox for Space-Eight. All rights reserved.
 *
 */

#include "vis_thread.h"

#include "messages.h"
#include "timutils.h"
#include "simdefs.h"
#include "neural_simulation.h"
#include "carlstructs.h"
#include "init.h"

#include "main.h"

#include <stdio.h>
#include <ctype.h>
#include <pthread.h>

extern sync_t thread_initialized;
extern int VIS_Thread_Initialized;
extern int quit;
pthread_mutex_t VIS_data_mutex = PTHREAD_MUTEX_INITIALIZER;

extern int externLoops;

extern int ClampOutputFlag;
extern int LearningFlag;
extern int OutputPatternSelect; // 0-3 or 0-4 different patterns
extern float OutputPattern[NUM_OUTPUTS]; // 0-3 or 0-4 different patterns
extern int InputPatternSelect; // 0-3 or 0-4 different patterns
extern float InputPattern[NUM_OUTPUTS * NUM_INPUTS]; // 0-3 or 0-4 different patterns


#include </usr/local/include/opencv/cv.h>
#include </usr/local/include/opencv/highgui.h>
#include <stdio.h>   //Standard input/output definitions 
#include <string.h>  // String function definitions 
#include <unistd.h>  // UNIX standard function definitions 
#include <fcntl.h>   // File control definitions 
#include <errno.h>   // Error number definitions 
#include <termios.h> // POSIX terminal control definitions 

#include "math.h"
#include <stdio.h>

IplImage *doPyrDown( IplImage *in); // SUB
IplImage *doHisto(IplImage *in, IplImage *hsv, IplImage *hue, CvHistogram *hist); // SUB

IplImage *frame = 0;

IplImage *maskRed = 0;
IplImage *maskYellow = 0;
IplImage *maskBlue = 0;
IplImage *maskGreen = 0;

IplImage *outputRed = 0;
IplImage *outputYellow = 0;
IplImage *outputBlue = 0;
IplImage *outputGreen = 0;
IplImage *outputTemp = 0;

CvHistogram *yellow_hist = 0;
CvHistogram *green_hist = 0;
CvHistogram *red_hist = 0;
CvHistogram *blue_hist = 0;

IplImage *hsv = 0, *hue = 0;

//int hdims = 16;
int hdims = 64;
float hranges_arr[] = {0,180};
float* hranges = hranges_arr;

CvCapture* capture = 0;

CvMemStorage *storage;

int xPos = 20, yPos = 50, xyPos = 0, xCenter = 150, yCenter = 200;

int xBuffer = 10, yBuffer = 30;

char c = 0, d = 0, e = 0;
int i = 0, out = 0, j = 0;
int radius_ball = 0, min_radius = 0, max_radius = 0, radius_threshold = 0, min_dist = 0;
int outputRadiusBall = 10;

char buffer [50];
int n;
int m;

CvRect track_window;
CvBox2D track_box;
CvConnectedComp track_comp;

CvPoint test_1;

int NAV_Thread_Initialized = FALSE;
void *NAV_Thread(void *arg); 
extern pthread_mutex_t NAV_data_mutex;
pthread_t NAV_thread_id;
 
// for visualization
extern float VisLayer1[9];
extern float VisLayer2[8];
extern float VisLayer3[4];

extern float Wij[NUM_NEURONS][NUM_NEURONS];
extern float Vis_Ui [NUM_NEURONS]; // output
extern float Neur_Ui [NUM_NEURONS]; // output

#define SCALE_FACTOR 25
#define S_F SCALE_FACTOR

float InputUnitOne = 0.1, InputUnitTwo = 0.1;
int ColorRed, ColorGreen, ColorBlue;
int Color;

void drawNeuronCircle(IplImage *in, float neuronValue, CvPoint neuronLocation, int neuronRadius);
CvPoint neuronOutLoc;
int neuronOutRadius;
int xTemp, yTemp;

// ---------------------------------------------
//
//		VIS Thread
//
// ---------------------------------------------
void *VIS_Thread(void *arg) 

{
	printf("Hello, World! From VIS Thread!!!\n");
	
	int status;

	status = pthread_mutex_lock (&thread_initialized.mutex);
	if (status != 0) 
	{
		err_abort (status, "Lock mutex");
	}
	
	//PUT ANY THREAD INITIALIZING CODE HERE
	
	status = pthread_mutex_unlock (&thread_initialized.mutex);
	if (status != 0) 
	{
		err_abort (status, "thread_initialized unlock mutex");
	}
	
// --------------------------
//
//	INIT OPENCV VARIABLES HERE
//
// --------------------------
    // insert code here...
    printf("Hello, World!\n");
	
	// --------------------------
	//
	//	START VISUALIZATION HERE
	//
	// --------------------------	
	
	usleep (100000);

	// ------------------
	// UNIT LAYERS
	// ------------------
	IplImage *imgUnit1 = cvCreateImage( cvSize( 3 * SCALE_FACTOR, 3 * SCALE_FACTOR ), 8, 3 );
	cvNamedWindow( "UnitOne", 1 );	
	cvShowImage( "UnitOne", imgUnit1 );	
	cvMoveWindow( "UnitOne", xPos + 6 * S_F, yPos + S_F);
	cvResizeWindow ( "UnitOne", imgUnit1->width, imgUnit1->height );
	
	IplImage *imgUnit2 = cvCreateImage( cvSize( 3 * SCALE_FACTOR, 3 * SCALE_FACTOR ), 8, 3 );
	cvNamedWindow( "UnitTwo", 1 );	
	cvShowImage( "UnitTwo", imgUnit2 );	
	cvMoveWindow( "UnitTwo", xPos + 6 * S_F, yPos + 10 * S_F);
	cvResizeWindow ( "UnitTwo", imgUnit2->width, imgUnit2->height );
	
	IplImage *imgUnit3 = cvCreateImage( cvSize( 3 * SCALE_FACTOR, 3 * SCALE_FACTOR ), 8, 3 );
	cvNamedWindow( "UnitThree", 1 );	
	cvShowImage( "UnitThree", imgUnit3 );	
	cvMoveWindow( "UnitThree", xPos + 6 * S_F, yPos + 19 * S_F);
	cvResizeWindow ( "UnitThree", imgUnit3->width, imgUnit3->height );
	
	// ------------------
	// GAUSSIAN LAYERS
	// ------------------
	IplImage *imgGauss1 = cvCreateImage( cvSize( 13 * SCALE_FACTOR, 4 * SCALE_FACTOR ), 8, 3 );
	cvNamedWindow( "GaussOne", 1 );	
	cvShowImage( "GaussOne", imgGauss1 );	
	cvMoveWindow( "GaussOne", xPos + 1 * S_F, yPos + 5 * S_F);

	IplImage *imgGauss2 = cvCreateImage( cvSize( 13 * SCALE_FACTOR, 4 * SCALE_FACTOR ), 8, 3 );
	cvNamedWindow( "GaussTwo", 1 );	
	cvShowImage( "GaussTwo", imgGauss2 );	
	cvMoveWindow( "GaussTwo", xPos + 1 * S_F, yPos + 14 * S_F);

	IplImage *imgGauss3 = cvCreateImage( cvSize( 13 * SCALE_FACTOR, 4 * SCALE_FACTOR ), 8, 3 );
	cvNamedWindow( "GaussThree", 1 );	
	cvShowImage( "GaussThree", imgGauss3 );	
	cvMoveWindow( "GaussThree", xPos + 1 * S_F, yPos + 23 * S_F);
	
	// ------------------
	// POPULATION LAYER
	// ------------------
	IplImage *imgPop1 = cvCreateImage( cvSize( 13 * SCALE_FACTOR, 13 * SCALE_FACTOR ), 8, 3 );
	cvNamedWindow( "PopOne", 1 );	
	cvShowImage( "popOne", imgPop1 );	
	cvMoveWindow( "PopOne", xPos + 16 * S_F, yPos + 9 * S_F);
	

	
	usleep (100000);
	
	
	 while (quit == NO_EXIT) 
	 {
		usleep (10000);
		 
		 status = pthread_mutex_lock (&VIS_data_mutex);
		 if (status != 0) 
		 {
			 err_abort (status, "Lock mutex");
		 }
		 
		 // ---------------------------------------------
		 //
		 //		PUT VIS MUTEX LOCKED CODE HERE
		 //
		 // ---------------------------------------------

		 // ==================================
		 // ----------------------------------
		 // UPDATE VISUALIZATION
		 // ----------------------------------
		 // ==================================
		 
		 for (i = 0; i < NUM_NEURONS; i++ )
		 {
			 Vis_Ui[i] = Neur_Ui[i]; // = Ui[i];
		 }
		 
		 Vis_Ui[0] = InputUnitOne; // set to input value
		 Vis_Ui[53] = InputUnitTwo; // set to input value
		 
		 Neur_Ui[0] = Vis_Ui[0]; // = Ui[i];
		 Neur_Ui[53] = Vis_Ui[53]; // = Ui[i];
		 
		 Color = (Vis_Ui[0]) * 4;
		 
		 switch (Color)
		 {
			 default:
			 case 0:
				 ColorRed = 0;
				 ColorGreen = (Vis_Ui[0] * 4) * 255;
				 ColorBlue = 255;
				 break;
				 
			 case 1:
				 ColorRed = 0;
				 ColorGreen = 255;
				 ColorBlue = 255 - ((Vis_Ui[0] * 4 - 1) * 255);
				 break;
				 
			 case 2:
				 ColorRed = ((Vis_Ui[0] * 4 - 2) * 255);
				 ColorGreen = 255;
				 ColorBlue = 0;
				 break;
				 
			 case 3:
				 ColorRed = 255;
				 ColorGreen = 255 - ((Vis_Ui[0] * 4 - 3) * 255);
				 ColorBlue = 0;
				 break;
				 
			 case 4:
				 ColorRed = 255;
				 ColorGreen = 0;
				 ColorBlue = 0;
				 break;
		 }
		 
		 
		 cvCircle(imgUnit1, cvPoint(38, 38), 30, CV_RGB(ColorRed, ColorGreen , ColorBlue), -1, 0, 0);
		 
		 
		 neuronOutLoc = cvPoint(38, 38);
		 neuronOutRadius = 30;
		 drawNeuronCircle(imgUnit2, Vis_Ui[53], neuronOutLoc, neuronOutRadius);
		 
		 for (i = 0; i < 52; i++ )
		 {
			 yTemp = (i / 13);
			 xTemp = i - ((13) * (yTemp));
			 neuronOutLoc = cvPoint((xTemp * S_F) + 13, (yTemp * S_F) + 13);
			 neuronOutRadius = 10;
			 drawNeuronCircle(imgGauss1, Vis_Ui[i + 1], neuronOutLoc, neuronOutRadius);
		 }
	
		 for (i = 0; i < 52; i++ )
		 {
			 yTemp = (i / 13);
			 xTemp = i - ((13) * (yTemp));
			 neuronOutLoc = cvPoint((xTemp * S_F) + 13, (yTemp * S_F) + 13);
			 neuronOutRadius = 10;
			 drawNeuronCircle(imgGauss2, Vis_Ui[i + 54], neuronOutLoc, neuronOutRadius);
		 }
	
		 for (i = 0; i < (169); i++ )
		 {
			 yTemp = (i / 13);
			 xTemp = i - ((13) * (yTemp));
			 neuronOutLoc = cvPoint((xTemp * S_F) + 13, (yTemp * S_F) + 13);
			 neuronOutRadius = 10;
			 drawNeuronCircle(imgPop1, Vis_Ui[i + 106], neuronOutLoc, neuronOutRadius);
		 }

		 
		 c = cvWaitKey(100);

		 		 
		 status = pthread_mutex_unlock (&VIS_data_mutex);
		 if (status != 0) 
		 {
			 err_abort (status, "Unlock mutex");
		 }

		 
		 cvShowImage( "UnitOne", imgUnit1 );
		 cvShowImage( "UnitTwo", imgUnit2 );
		 cvShowImage( "UnitThree", imgUnit3 );
		 
		 cvShowImage( "GaussOne", imgGauss1 );
		 cvShowImage( "GaussTwo", imgGauss2 );
		 cvShowImage( "GaussThree", imgGauss3 );
		 
		 cvShowImage( "PopOne", imgPop1 );

		 
		 usleep (100);
		 
		 if ( c == 27 )
		 {
			 break;
		 }
		 

		 switch (c)
		 {
			 default:
			 case 'q':
				 break;

			 case 'W':				 
			 case 'w':
				 //print weights
				 printf("\n");
				 for (n = 0; n < NUM_NEURONS; n++ )
				 {
					 for (m = 0; m < NUM_NEURONS; m++ )
					 {
						 printf("%f ",Wij[n][m]);
					 }
					 printf("\n");
				 }
				 
				 break;
				 
			 case 'c':
			 case 'C':
				 ClampOutputFlag = !ClampOutputFlag; // toggle flag
				 break;
				 
			 case 'l':
			 case 'L':
				 LearningFlag = !LearningFlag; // toggle flag
				 printf("learning flag = %i\n", LearningFlag);
				 break;
				 
			 case 'U':				 
			 case 'u':
				 if (InputUnitTwo < 0.95)
				 {
					 InputUnitTwo += 0.025;
				 }
				 printf("%f\n", InputUnitTwo);
				 break;
				 
			 case 'N':	 
			 case 'n':
				 if (InputUnitTwo > 0.05)
				 {
					 InputUnitTwo -= 0.025;
				 }
				 printf("%f\n", InputUnitTwo);
				 break;

			 case 'T':				 
			 case 't':
				 if (InputUnitOne < 0.95)
				 {
					 InputUnitOne += 0.025;
				 }
				 printf("%f\n", InputUnitOne);
				 printf("%d\n", Color);
				 break;
				 
			 case 'V':	 
			 case 'v':
				 if (InputUnitOne > 0.05)
				 {
					 InputUnitOne -= 0.025;
				 }
				 printf("%f\n", InputUnitOne);
				 printf("%d\n", Color);
				 break;
		 }
		 

		 
	 } // end while no exit
	 
	
	c = cvWaitKey(0);
	

	VIS_Thread_Initialized = TRUE; // TESTING ONLY
	
	fprintf (stderr, "VIS thread exiting\n");
	
	// memory release for img before exiting the application
	
	cvReleaseImage (&imgUnit1);
	cvReleaseImage (&imgUnit2);
	cvReleaseImage (&imgUnit3);
	cvReleaseImage (&imgGauss1);
	cvReleaseImage (&imgGauss2);
	cvReleaseImage (&imgGauss3);
	cvReleaseImage (&imgPop1);
	
	cvDestroyWindow("UnitOne");
	cvDestroyWindow("UnitTwo");
	cvDestroyWindow("UnitThree");

	cvDestroyWindow("GaussOne");
	cvDestroyWindow("GaussTwo");
	cvDestroyWindow("GaussThree");
	
	cvDestroyWindow("PopOne");

	VIS_Thread_Initialized = TRUE; // TESTING ONLY
	
    return 0;
	
	
}


// ==================================
// ----------------------------------
// SUB ROUTINES
// ----------------------------------
// ==================================

void drawNeuronCircle(IplImage *in, float neuronValue, CvPoint neuronLocation, int neuronRadius)
{
	int cRed, cGrn, cBlu, color;
	
	color = (neuronValue) * 4;
	
	switch (color)
	{
		default:
		case 0:
			cRed = 0;
			cGrn = ((neuronValue) * 4) * 255;
			cBlu = 255;
			break;
			
		case 1:
			cRed = 0;
			cGrn = 255;
			cBlu = 255 - (((neuronValue) * 4 - 1) * 255);
			break;
			
		case 2:
			cRed = (((neuronValue) * 4 - 2) * 255);
			cGrn = 255;
			cBlu = 0;
			break;
			
		case 3:
			cRed = 255;
			cGrn = 255 - (((neuronValue) * 4 - 3) * 255);
			cBlu = 0;
			break;
			
		case 4:
			cRed = 255;
			cGrn = 0;
			cBlu = 0;
			break;
	}
	
	
	cvCircle(in, neuronLocation, neuronRadius, CV_RGB(cRed, cGrn , cBlu), -1, 0, 0);
	
	return;
}
