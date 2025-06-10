/*
 *  vis_thread.c
 *  nn_alpha_1
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
int vi = 0, vj = 0;
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

//#define SCALE_FACTOR 25
//#define SCALE_FACTOR 12
//#define SCALE_FACTOR 18
#define SCALE_FACTOR 18

#define S_F SCALE_FACTOR
#define MARGIN 10

float InputUnitOne = 0.5, InputUnitTwo = 0.5;
int ColorRed, ColorGreen, ColorBlue;
int Color;

void drawNeuronCircle(IplImage *in, float neuronValue, CvPoint neuronLocation, int neuronRadius);
CvPoint neuronOutLoc;
int neuronOutRadius;
int xTemp, yTemp;

extern FILE* outputFile;
extern int printWeightFlag;
extern int homeostasisFlag;
extern int RandomInputFlag;
float fTemp_vis = 0;
int RandCountDown = 0;
extern int BlankInputFlag;
float avgOutput, errorOutput;
float weightMax;

extern float VisWij [MAX_NUM_NEURONS] [MAX_NUM_NEURONS]; // weight matrix

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
	cvMoveWindow( "UnitOne", xPos + (INPUT_LAYER - 1.5) * S_F / 2, yPos + S_F);
	cvResizeWindow ( "UnitOne", imgUnit1->width, imgUnit1->height );
	
	IplImage *imgUnit2 = cvCreateImage( cvSize( 3 * SCALE_FACTOR, 3 * SCALE_FACTOR ), 8, 3 );
	cvNamedWindow( "UnitTwo", 1 );	
	cvShowImage( "UnitTwo", imgUnit2 );	
	cvMoveWindow( "UnitTwo", xPos + (INPUT_LAYER - 1.5) * S_F / 2, yPos + 10 * S_F + MARGIN * 2);
	cvResizeWindow ( "UnitTwo", imgUnit2->width, imgUnit2->height );
	
	IplImage *imgUnit3 = cvCreateImage( cvSize( 3 * SCALE_FACTOR, 3 * SCALE_FACTOR ), 8, 3 );
	cvNamedWindow( "UnitThree", 1 );	
	cvShowImage( "UnitThree", imgUnit3 );	
	cvMoveWindow( "UnitThree", xPos + (INPUT_LAYER - 1.5) * S_F / 2, yPos + 19 * S_F + MARGIN * 4);
	cvResizeWindow ( "UnitThree", imgUnit3->width, imgUnit3->height );
	
	// ------------------
	// GAUSSIAN LAYERS
	// ------------------
	IplImage *imgGauss1 = cvCreateImage( cvSize( INPUT_LAYER * SCALE_FACTOR, 4 * SCALE_FACTOR ), 8, 3 );
	cvNamedWindow( "GaussOne", 1 );	
	cvShowImage( "GaussOne", imgGauss1 );	
	cvMoveWindow( "GaussOne", xPos, yPos + 5 * S_F + MARGIN * 1);
	cvResizeWindow ( "GaussOne", imgGauss1->width, imgGauss1->height );

	IplImage *imgGauss2 = cvCreateImage( cvSize( INPUT_LAYER * SCALE_FACTOR, 4 * SCALE_FACTOR ), 8, 3 );
	cvNamedWindow( "GaussTwo", 1 );	
	cvShowImage( "GaussTwo", imgGauss2 );	
	cvMoveWindow( "GaussTwo", xPos, yPos + 14 * S_F + MARGIN * 3);
	cvResizeWindow ( "GaussTwo", imgGauss2->width, imgGauss2->height );
	
	IplImage *imgGauss3 = cvCreateImage( cvSize( INPUT_LAYER * SCALE_FACTOR, 4 * SCALE_FACTOR ), 8, 3 );
	cvNamedWindow( "GaussThree", 1 );	
	cvShowImage( "GaussThree", imgGauss3 );	
	cvMoveWindow( "GaussThree", xPos + 0 * S_F, yPos + 23 * S_F + MARGIN * 5);
	cvResizeWindow ( "GaussThree", imgGauss3->width, imgGauss3->height );
	
	// ------------------
	// POPULATION LAYER
	// ------------------
	IplImage *imgPop1 = cvCreateImage( cvSize( INPUT_LAYER * SCALE_FACTOR, INPUT_LAYER * SCALE_FACTOR ), 8, 3 );
	cvNamedWindow( "PopOne", 1 );	
	cvShowImage( "PopOne", imgPop1 );	
	cvMoveWindow( "PopOne", xPos + (INPUT_LAYER + 1) * S_F + MARGIN, yPos + 9 * S_F);
	cvResizeWindow ( "PopOne", imgPop1->width, imgPop1->height );
	
	IplImage *imgWeight1 = cvCreateImage( cvSize( INPUT_LAYER * SCALE_FACTOR, INPUT_LAYER * SCALE_FACTOR ), 8, 3 );
	cvNamedWindow( "WeightOne", 1 );	
	cvShowImage( "WeightOne", imgWeight1 );	
	cvMoveWindow( "WeightOne", xPos + 2 * (INPUT_LAYER + 1) * S_F + 2 * MARGIN, yPos + 9 * S_F);
	cvResizeWindow ( "WeightOne", imgWeight1->width, imgWeight1->height );
	
	usleep (100000);
	
	srand(time(0)); // seed variable
	
	 while (quit == NO_EXIT) 
	 {
		usleep (1000);
		 
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
		 
		 if(RandomInputFlag)
		 {
			 RandCountDown ++;
		 }
		 
		 //if(RandCountDown > 10)
		//if(RandCountDown > 25)
		//if(RandCountDown > 5)
		if(RandCountDown > 3)

		{
			 //srand(time(0)); // seed variable
			 
			 fTemp_vis = (rand() % 100); // generate random activation 
			 fTemp_vis /= 100; // normalize 0-1
			 //fTemp_vis /= 2; // normalize 0-1
			 fTemp_vis *= (.35); // normalize 0-1
			 //fTemp_vis += .25; // normalize 0-1
			 fTemp_vis += .4; // normalize 0-1
			 InputUnitOne = fTemp_vis;
			 
			 fTemp_vis = (rand() % 100); // generate random activation 
			 fTemp_vis /= 100; // normalize 0-1
			 //fTemp_vis /= 2; // normalize 0-1
			 fTemp_vis *= (.35); // normalize 0-1
			 //fTemp_vis += .25; // normalize 0-1
			 fTemp_vis += .4; // normalize 0-1
			 InputUnitTwo = fTemp_vis;
			 RandCountDown = 0;
			 //RandomInputFlag = 0;
			 BlankInputFlag = 1;
		 }
		 
		 
		 for (vi = 0; vi < NUM_NEURONS; vi++ )
		 {
			 Vis_Ui[vi] = Neur_Ui[vi]; // = Ui[i];
		 }
		 
		 Vis_Ui[0] = InputUnitOne; // set to input value
		 //Vis_Ui[53] = InputUnitTwo; // set to input value
		 Vis_Ui[4*INPUT_LAYER + 1] = InputUnitTwo; // set to input value
		 
		 Neur_Ui[0] = Vis_Ui[0]; // = Ui[i];
		 //Neur_Ui[53] = Vis_Ui[53]; // = Ui[i];
		 Neur_Ui[4*INPUT_LAYER + 1] = Vis_Ui[4*INPUT_LAYER + 1]; // = Ui[i];
		 
		 if(ClampOutputFlag)
		 {
			 //Vis_Ui[275] = (InputUnitTwo + InputUnitOne) / 2;
			 //Neur_Ui[275] = Vis_Ui[275];
			 Vis_Ui[(4*INPUT_LAYER + 1)*2 + (INPUT_LAYER * INPUT_LAYER)] = (InputUnitTwo + InputUnitOne) / 2;
			 Neur_Ui[(4*INPUT_LAYER + 1)*2 + (INPUT_LAYER * INPUT_LAYER)] = Vis_Ui[(4*INPUT_LAYER + 1)*2 + (INPUT_LAYER * INPUT_LAYER)];
		 }
		 
		 Color = (Vis_Ui[0]) * 4;
		 //printf("%d\n", Color);
		 
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
		 
		 
		 //cvCircle(imgUnit1, cvPoint(38, 38), 30, CV_RGB(ColorRed, ColorGreen , ColorBlue), -1, 0, 0);
		 cvCircle(imgUnit1, cvPoint(1.5*S_F, 1.5*S_F), (1.2*S_F), CV_RGB(ColorRed, ColorGreen , ColorBlue), -1, 0, 0);
		 
		 neuronOutLoc = cvPoint(1.5*S_F, 1.5*S_F);
		 neuronOutRadius = 1.2*S_F;
		 drawNeuronCircle(imgUnit2, Vis_Ui[4*INPUT_LAYER + 1], neuronOutLoc, neuronOutRadius);
		 
		 for (vi = 0; vi < 4*INPUT_LAYER; vi++ )
		 {
			 yTemp = (vi / INPUT_LAYER);
			 xTemp = vi - ((INPUT_LAYER) * (yTemp));
			 neuronOutLoc = cvPoint((xTemp * S_F) + S_F/2, (yTemp * S_F) + S_F/2);
			 neuronOutRadius = (0.83 * S_F) / 2;
			 drawNeuronCircle(imgGauss1, Vis_Ui[vi + 1], neuronOutLoc, neuronOutRadius);
			 //drawNeuronCircle(imgGauss1, 0.5, neuronOutLoc, neuronOutRadius); //TESTING
		 }
	
		 for (vi = 0; vi < 4*INPUT_LAYER; vi++ )
		 {
			 yTemp = (vi / INPUT_LAYER);
			 xTemp = vi - ((INPUT_LAYER) * (yTemp));
			 //neuronOutLoc = cvPoint((xTemp * S_F) + 13, (yTemp * S_F) + 13);
			 //neuronOutRadius = 10;
			 neuronOutLoc = cvPoint((xTemp * S_F) + S_F/2, (yTemp * S_F) + S_F/2);
			 neuronOutRadius = (0.83 * S_F) / 2;
			 drawNeuronCircle(imgGauss2, Vis_Ui[vi + (4 * INPUT_LAYER + 1) + 1], neuronOutLoc, neuronOutRadius);
			 //drawNeuronCircle(imgGauss1, 0.5, neuronOutLoc, neuronOutRadius); //TESTING
		 }
	
		 for (vi = 0; vi < (INPUT_LAYER * INPUT_LAYER); vi++ )
		 {
			 yTemp = (vi / INPUT_LAYER);
			 xTemp = vi - ((INPUT_LAYER) * (yTemp));
			 //neuronOutLoc = cvPoint((xTemp * S_F) + 13, (yTemp * S_F) + 13);
			 //neuronOutRadius = 10;
			 //Vis_Ui[106] = 128; //testing
			 //Vis_Ui[190] = 128; //testing
			 //Vis_Ui[274] = 128; //testing
			 neuronOutLoc = cvPoint((xTemp * S_F) + S_F/2, (yTemp * S_F) + S_F/2);
			 neuronOutRadius = (0.83 * S_F) / 2;
			 drawNeuronCircle(imgPop1, Vis_Ui[vi + (4 * INPUT_LAYER + 1) * 2], neuronOutLoc, neuronOutRadius);
			 //drawNeuronCircle(imgGauss1, 0.5, neuronOutLoc, neuronOutRadius); //TESTING
		 }
	
		 weightMax = 0.25; // nominal zero
		 for (vj = (4 * INPUT_LAYER + 1) * 2; vj < ((4*INPUT_LAYER + 1)*2 + (INPUT_LAYER * INPUT_LAYER)); vj++ )
		 {
			 vi = (4*INPUT_LAYER + 1)*2 + (INPUT_LAYER * INPUT_LAYER);
			 if(VisWij[vi][vj] > weightMax)
			 {
			 weightMax = VisWij[vi][vj];
			 }
			 
		 }
		 
		 //printf("Weight Max = %f\n", weightMax);
		 
		//if (weightMax < 1)
		//{
		//	weightMax = 1; // default
		//}
		 
		 for (vj = 0; vj < (INPUT_LAYER * INPUT_LAYER); vj++ )
		 {
			 vi = (4*INPUT_LAYER + 1)*2 + (INPUT_LAYER * INPUT_LAYER); // pre-synaptic
			 yTemp = (vj / INPUT_LAYER);
			 xTemp = vj - ((INPUT_LAYER) * (yTemp));
			 //neuronOutLoc = cvPoint((xTemp * S_F) + 13, (yTemp * S_F) + 13);
			 //neuronOutRadius = 10;
			 neuronOutLoc = cvPoint((xTemp * S_F) + S_F/2, (yTemp * S_F) + S_F/2);
			 neuronOutRadius = (0.83 * S_F) / 2;
			 drawNeuronCircle(imgWeight1, (VisWij[vi][vj + (4*INPUT_LAYER + 1)*2] / weightMax), neuronOutLoc, neuronOutRadius);
		 }
		 
		 //neuronOutLoc = cvPoint(38, 38);
		 //neuronOutRadius = 30;
		 //drawNeuronCircle(imgUnit3, Vis_Ui[275], neuronOutLoc, neuronOutRadius);
		 neuronOutLoc = cvPoint(1.5*S_F, 1.5*S_F);
		 neuronOutRadius = 1.2*S_F;
		 drawNeuronCircle(imgUnit3, Vis_Ui[(4 * INPUT_LAYER + 1)*2 + (INPUT_LAYER * INPUT_LAYER)], neuronOutLoc, neuronOutRadius);
		 
		 for (vi = 0; vi < (4 * INPUT_LAYER); vi++ )
		 {
			 yTemp = (vi / INPUT_LAYER);
			 xTemp = vi - ((INPUT_LAYER) * (yTemp));
			 //neuronOutLoc = cvPoint((xTemp * S_F) + 13, (yTemp * S_F) + 13);
			 //neuronOutRadius = 10;
			 neuronOutLoc = cvPoint((xTemp * S_F) + S_F/2, (yTemp * S_F) + S_F/2);
			 neuronOutRadius = (0.83 * S_F) / 2;
			 drawNeuronCircle(imgGauss3, Vis_Ui[vi + (4 * INPUT_LAYER + 1) * 2 + (INPUT_LAYER * INPUT_LAYER) + 1], neuronOutLoc, neuronOutRadius);
			 //drawNeuronCircle(imgGauss1, 0.5, neuronOutLoc, neuronOutRadius); //TESTING
		 }
		 
		 c = cvWaitKey(100);
		 
		 //usleep (100);
		 
		 
		 status = pthread_mutex_unlock (&VIS_data_mutex);
		 if (status != 0) 
		 {
			 err_abort (status, "Unlock mutex");
		 }
		 
		 // ---------------------------------------------
		 //
		 //		PUT VIS MUTEX UN-LOCKED CODE BELOW
		 //
		 // ---------------------------------------------
		 
		 
		 //cvSmooth( imgGauss1, imgGauss1, CV_GAUSSIAN, 3, 3, 0, 0);
		 
		 cvShowImage( "UnitOne", imgUnit1 );
		 cvShowImage( "UnitTwo", imgUnit2 );
		 cvShowImage( "UnitThree", imgUnit3 );
		 
		 cvShowImage( "GaussOne", imgGauss1 );
		 cvShowImage( "GaussTwo", imgGauss2 );
		 cvShowImage( "GaussThree", imgGauss3 );
		 
		 cvShowImage( "PopOne", imgPop1 );
		 cvShowImage( "WeightOne", imgWeight1 );
		 
		 //c = cvWaitKey(100);
		 
		 usleep (10);
		 
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
				 
				 printWeightFlag = 1;
				 
				 /*
				 //print weights
				 printf("\n");
				 for (n = 0; n < NUM_NEURONS; n++ )
				 {
					  fprintf(outputFile, "input Neuron = %i\n", n);
					 for (m = 0; m < NUM_NEURONS; m++ )
					 {
						 printf("%f ",Wij[n][m]);
						 fprintf(outputFile, "%f ", Wij[n][m]);
					 }
					 printf("\n");
					 fprintf(outputFile, "\n");
				 }
				 */
				 
				 break;
				 
			 case 'c':
			 case 'C':
				 ClampOutputFlag = !ClampOutputFlag; // toggle flag
				 printf("clamp flag = %i\n", ClampOutputFlag);
				 break;
				 
			 case 'r':
			 case 'R':
				 RandomInputFlag = !RandomInputFlag; // toggle flag
				 printf("random flag = %i\n", RandomInputFlag);
				 break;				 
				 
			 case 'l':
			 case 'L':
				 LearningFlag = !LearningFlag; // toggle flag
				 printf("learning flag = %i\n", LearningFlag);
				 break;
				 
			 case 'h':
			 case 'H':
				 homeostasisFlag = !homeostasisFlag; // toggle flag
				 printf("homeostasis flag = %i\n", homeostasisFlag);
				 break;
				 
			 case 'U':				 
			 case 'u':
				 avgOutput = (InputUnitTwo + InputUnitOne) / 2;
				 errorOutput = (avgOutput - Neur_Ui[(4 * INPUT_LAYER + 1) * 2 + (INPUT_LAYER * INPUT_LAYER)]) * 100;
				 printf("InputOne=%f, InputTwo=%f, Avg=%f, NeurOut=%f, Error=%f\n", InputUnitOne, InputUnitTwo, avgOutput, Neur_Ui[(4 * INPUT_LAYER + 1) * 2 + (INPUT_LAYER * INPUT_LAYER)], errorOutput);
				 
				 if (InputUnitTwo < 0.95)
				 {
					 InputUnitTwo += 0.025;
				 }
				 
				 //printf("%f\n", InputUnitTwo);
				 break;
				 
			 case 'N':	 
			 case 'n':
				 avgOutput = (InputUnitTwo + InputUnitOne) / 2;
				 errorOutput = (avgOutput - Neur_Ui[(4 * INPUT_LAYER + 1) * 2 + (INPUT_LAYER * INPUT_LAYER)]) * 100;
				 printf("InputOne=%f, InputTwo=%f, Avg=%f, NeurOut=%f, Error=%f\n", InputUnitOne, InputUnitTwo, avgOutput, Neur_Ui[(4 * INPUT_LAYER + 1) * 2 + (INPUT_LAYER * INPUT_LAYER)], errorOutput);
				 
				 if (InputUnitTwo > 0.05)
				 {
					 InputUnitTwo -= 0.025;
				 }
				 
				 //printf("%f\n", InputUnitTwo);
				 break;

			 case 'T':				 
			 case 't':
				 avgOutput = (InputUnitTwo + InputUnitOne) / 2;
				 errorOutput = (avgOutput - Neur_Ui[(4 * INPUT_LAYER + 1) * 2 + (INPUT_LAYER * INPUT_LAYER)]) * 100;
				 printf("InputOne=%f, InputTwo=%f, Avg=%f, NeurOut=%f, Error=%f\n", InputUnitOne, InputUnitTwo, avgOutput, Neur_Ui[(4 * INPUT_LAYER + 1) * 2 + (INPUT_LAYER * INPUT_LAYER)], errorOutput);
				 
				 if (InputUnitOne < 0.95)
				 {
					 InputUnitOne += 0.025;
				 }

				 break;
				 
			 case 'V':	 
			 case 'v':
				 avgOutput = (InputUnitTwo + InputUnitOne) / 2;
				 errorOutput = (avgOutput - Neur_Ui[(4 * INPUT_LAYER + 1) * 2 + (INPUT_LAYER * INPUT_LAYER)]) * 100;
				 printf("InputOne=%f, InputTwo=%f, Avg=%f, NeurOut=%f, Error=%f\n", InputUnitOne, InputUnitTwo, avgOutput, Neur_Ui[(4 * INPUT_LAYER + 1) * 2 + (INPUT_LAYER * INPUT_LAYER)], errorOutput);
				 
				 if (InputUnitOne > 0.05)
				 {
					 InputUnitOne -= 0.025;
				 }
				 
				 //printf("%f\n", InputUnitOne);
				 //printf("%d\n", Color);
				 break;
		 }
		 
		 /*
		 status = pthread_mutex_unlock (&VIS_data_mutex);
		 if (status != 0) 
		 {
			 err_abort (status, "Unlock mutex");
		 }
		 */
		 
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
	cvDestroyWindow("WeightOne");
	
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
