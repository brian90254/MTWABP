#include "cv.h"
#include "highgui.h"
#include <stdio.h>

#define BLU 0
#define GRN 1
#define RED 2

#define HUE 0
#define SAT 1
#define INT 2

IplImage *image = 0, *visual_data = 0, *hsv = 0, *hue = 0, *mask = 0, *backproject = 0, *histimg = 0, *green_backproject = 0, *red_backproject = 0, *yellow_backproject = 0;
IplImage *test1 = 0;
IplImage *testResize1 = 0;
IplImage *frame1 = 0;

IplImage *maskRed = 0;
IplImage *maskYellow = 0;
IplImage *outputRed = 0;
IplImage *outputYellow = 0;

CvPoint origin;
CvRect selection;
CvRect track_window;
CvBox2D track_box;
CvConnectedComp track_comp;

CvHistogram *yellow_hist = 0;
CvHistogram *green_hist = 0;
CvHistogram *red_hist = 0;
CvCapture* capture = 0;
IplImage* frame = 0;
//int hdims = 16;
int hdims = 64;
float hranges_arr[] = {0,180};
float* hranges = hranges_arr;


double dNorm;
float fConst;
int j;
int xPos, yPos, xyPos, xCenter = 150, yCenter = 200;

int main ()
{

  IplImage *img = cvCreateImage(cvSize(200, 200), IPL_DEPTH_8U, 3);
  
// fill every third channel (all the red ones) with value 255.
  int i;
	int iHalfImg;
	iHalfImg = img->imageSize / 2;
	iHalfImg /= 3;
	iHalfImg *= 3;	
	
  for (i = BLU; i < iHalfImg; i+=3)
    img->imageData[i] = 128;

  for (i = iHalfImg + RED; i < img->imageSize; i+=3)
    img->imageData[i] = 255;
	
	//TEST LINE DRAW
	cvLine(img, cvPoint(10,10), cvPoint(190,190), CV_RGB(0,255,0), 5, CV_AA, 0); 

//CV_FONT_HERSHEY_SIMPLEX
	CvFont fontTest;
	cvInitFont(&fontTest, CV_FONT_HERSHEY_SIMPLEX, 1, 1, 0, 2, CV_AA);
	cvPutText(img, "test text", cvPoint(50,50), &fontTest, CV_RGB(255,255,0));

	/*
	cvNamedWindow ("image", 1);
	cvShowImage ("image", img);
	cvResizeWindow("image",200,200);
	*/
	
// -----------------------------------
//	SETUP BLACK/white IMAGE
// -----------------------------------

	IplImage *imgBlank = cvCreateImage(cvSize(300, 400), IPL_DEPTH_8U, 1);
	IplImage *imgUnity = cvCreateImage(cvSize(300, 400), IPL_DEPTH_8U, 1);
	IplImage *imgRed = cvCreateImage(cvSize(300, 400), IPL_DEPTH_8U, 3);
	IplImage *imgGray = cvCreateImage(cvSize(300, 400), IPL_DEPTH_8U, 3);
	IplImage *imgHueMask = cvCreateImage(cvSize(300, 400), IPL_DEPTH_8U, 3);
	IplImage *imgUnityRed = cvCreateImage(cvSize(300, 400), IPL_DEPTH_8U, 3);
					
	for (i = 0; i < imgUnity->imageSize; i++)
		imgUnity->imageData[i] = 1;
			
	for (i = 0; i < imgBlank->imageSize; i++)
		imgBlank->imageData[i] = 0;
	
	for (i = RED; i < imgRed->imageSize; i+=3)
		//imgRed->imageData[i] = 255;
		imgRed->imageData[i] = 128;
		
	for (i = 0; i < imgGray->imageSize; i++)
		imgGray->imageData[i] = 128;
	
	for (i = HUE; i < imgHueMask->imageSize; i+=3)
		imgHueMask->imageData[i] = 0;
	for (i = SAT; i < imgHueMask->imageSize; i+=3)
		imgHueMask->imageData[i] = 255;
	for (i = INT; i < imgHueMask->imageSize; i+=3)
		imgHueMask->imageData[i] = 255;

	for (i = RED; i < imgUnityRed->imageSize; i+=3)
		imgUnityRed->imageData[i] = 1;
						
	i = 1;
	imgBlank->imageData[i + 60150] = 255;
		
	// -- TEST NORMALIZING ---------------------------------
	for (j = 0; j < 3; j++)
		{
		cvSmooth( imgBlank, imgBlank, CV_GAUSSIAN, 45, 45, 0, 0);
		dNorm = cvNorm(imgBlank, 0, CV_C, 0);
		fConst = 128 / dNorm;

		for (i = 0; i < imgBlank->imageSize; i++)
			imgBlank->imageData[i] *= fConst;
		}
			
	// -----------------------------------------------------
	
	// a visualization window is created with title 'image'
	cvNamedWindow ("imageBlank", 1);
	cvShowImage ("imageBlank", imgBlank);
	cvResizeWindow("imageBlank",300,400);
	cvMoveWindow ( "imageBlank", 350, 320);
	
	
	cvCvtColor( imgRed, imgRed, CV_HSV2BGR); //CV_BGR2HSV );
	cvNamedWindow ("imageRed", 1);
	cvShowImage ("imageRed", imgRed);
	cvResizeWindow("imageRed",300,400);
	cvMoveWindow ( "imageRed", 100, 100);
	
// ---------------------------------------------------

// -----------------------------------
//	SETUP INITIAL GPS PROBABILITY
// -----------------------------------

  IplImage *probGPS = cvCreateImage(cvSize(300, 400), IPL_DEPTH_8U, 1);
    		
	for (i = 0; i < probGPS->imageSize; i++)
		probGPS->imageData[i] = 0;

	xPos = xCenter;
	yPos = yCenter;
	xyPos = xPos + 300 * yPos;
	probGPS->imageData[xyPos] = 255;
	
	xPos = xCenter - 20;
	yPos = yCenter - 10;
	xyPos = xPos + 300 * yPos;
	probGPS->imageData[xyPos] = 192;
	
	xPos = xCenter - 10;
	yPos = yCenter - 20;
	xyPos = xPos + 300 * yPos;
	probGPS->imageData[xyPos] = 164;
			
	// -- TEST NORMALIZING ---------------------------------
	for (j = 0; j < 6; j++)
		{
		cvSmooth( probGPS, probGPS, CV_GAUSSIAN, 45, 45, 0, 0);
		dNorm = cvNorm(probGPS, 0, CV_C, 0);
		fConst = 128 / dNorm;

		cvMul(probGPS, imgUnity, probGPS, fConst);

		/*
		for (i = 0; i < probGPS->imageSize; i++)
			probGPS->imageData[i] *= fConst;
			*/
		}
			
	// -----------------------------------------------------
	
	// a visualization window is created with title 'image'
	cvNamedWindow ("imageProbGPS", 1);
	cvShowImage ("imageProbGPS", probGPS);
	cvResizeWindow("imageProbGPS",300,400);
	cvMoveWindow ( "imageProbGPS", 690, 320);
	
	//cvCopy( probGPS, imgRed, 0 );
	cvCvtColor( probGPS, imgRed, CV_GRAY2BGR); //CV_BGR2HSV );
	cvNot(imgRed,imgRed); // invert
	cvSub(imgRed,imgGray,imgRed,0);
	for (i = SAT; i < imgRed->imageSize; i+=3)
		imgRed->imageData[i] = 255;
	for (i = INT; i < imgRed->imageSize; i+=3)
		imgRed->imageData[i] = 255;
	cvCvtColor( imgRed, imgRed, CV_HSV2BGR); //CV_BGR2HSV );
	//cvNot(imgRed,imgRed); // invert
	cvNamedWindow ("imageRed", 1);
	cvShowImage ("imageRed", imgRed);
	cvResizeWindow("imageRed",300,400);
	cvMoveWindow ( "imageRed", 100, 100);  
	

// ---------------------------------------------------

// -----------------------------------
//	SETUP INITIAL ENCODER PROBABILITY
// -----------------------------------

  IplImage *probENC = cvCreateImage(cvSize(300, 400), IPL_DEPTH_8U, 1);
    		
	for (i = 0; i < probENC->imageSize; i++)
		probENC->imageData[i] = 0;

	xPos = xCenter + 25;
	yPos = yCenter + 25;
	xyPos = xPos + 300 * yPos;
	probENC->imageData[xyPos] = 255;
	
	xPos = xCenter + 50;
	yPos = yCenter + 25;
	xyPos = xPos + 300 * yPos;
	probENC->imageData[xyPos] = 192;
	
	xPos = xCenter + 25;
	yPos = yCenter + 50;
	xyPos = xPos + 300 * yPos;
	probENC->imageData[xyPos] = 164;
			
	// -- TEST NORMALIZING ---------------------------------
	for (j = 0; j < 6; j++)
		{
		cvSmooth( probENC, probENC, CV_GAUSSIAN, 45, 45, 0, 0);
		dNorm = cvNorm(probENC, 0, CV_C, 0);
		fConst = 128 / dNorm;

		cvMul(probENC, imgUnity, probENC, fConst);
		
		/*
		for (i = 0; i < probENC->imageSize; i++)
			probENC->imageData[i] *= fConst;
			*/
		}
			
	// -----------------------------------------------------
	
	// a visualization window is created with title 'image'
	cvNamedWindow ("imageProbENC", 1);
	cvShowImage ("imageProbENC", probENC);
	cvResizeWindow("imageProbENC",300,400);
	cvMoveWindow ( "imageProbENC", 1030, 320);
	
// ---------------------------------------------------
	
	
// -----------------------------------
//	COMBINED IMAGE PROBABILITY
// -----------------------------------

  IplImage *probComb = cvCreateImage(cvSize(300, 400), IPL_DEPTH_8U, 1);
    		
	for (i = 0; i < probComb->imageSize; i++)
		probComb->imageData[i] = 0;

	//fConst = 255 / ( 128 * 128 );
	fConst = 0.015;
	fConst = 1;
	fConst *= 255;
	fConst /= 128;
	fConst /= 128;
	
	// normalize
	//dNorm = cvNorm(probComb, 0, CV_C, 0);
	//fConst = 128 / dNorm;
	
	cvMul(probGPS, probENC, probComb, fConst);
		
	/*
	for (i = 0; i < probComb->imageSize; i++)
		probComb->imageData[i] *= fConst;
	*/		
			
	// a visualization window is created with title 'image'
	cvNamedWindow ("imageProbComb", 1);
	cvShowImage ("imageProbComb", probComb);
	cvResizeWindow("imageProbComb",300,400);
	cvMoveWindow ( "imageProbComb", 350, 320);
	
// ---------------------------------------------------
	
	
// -----------------------------------
//	SETUP MEXICAN HAT NEGATIVE CIRCLE
// -----------------------------------

  IplImage *mexNeg = cvCreateImage(cvSize(300, 400), IPL_DEPTH_8U, 1);
    		
	for (i = 0; i < mexNeg->imageSize; i++)
		mexNeg->imageData[i] = 128;

	xPos = xCenter;
	yPos = yCenter;
	
	cvCircle( mexNeg, cvPoint(xPos,yPos), 40, CV_RGB(0,0,0), -1, 8, 0);

			
	
	// a visualization window is created with title 'image'
	cvNamedWindow ("imageProbGPS", 1);
	cvShowImage ("imageProbGPS", mexNeg);
	cvResizeWindow("imageProbGPS",300,400);
	cvMoveWindow ( "imageProbGPS", 690, 320);
	
// -----------------------------------
//	SETUP MEXICAN HAT POSITIVE GAUSSIAN
// -----------------------------------

  IplImage *mexPos = cvCreateImage(cvSize(300, 400), IPL_DEPTH_8U, 1);
    		
	for (i = 0; i < mexPos->imageSize; i++)
		mexPos->imageData[i] = 0;

	xPos = xCenter;
	yPos = yCenter;
	xyPos = xPos + 300 * yPos;
	mexPos->imageData[xyPos] = 255;

			
	// -- TEST NORMALIZING ---------------------------------
	for (j = 0; j < 6; j++)
		{
		cvSmooth( mexPos, mexPos, CV_GAUSSIAN, 45, 45, 0, 0);
		dNorm = cvNorm(mexPos, 0, CV_C, 0);
		fConst = 128 / dNorm;

		cvMul(mexPos, imgUnity, mexPos, fConst);

		}
		
	// -----------------------------------------------------
	
	// a visualization window is created with title 'image'
	cvNamedWindow ("imageProbENC", 1);
	cvShowImage ("imageProbENC", mexPos);
	cvResizeWindow("imageProbENC",300,400);
	cvMoveWindow ( "imageProbENC", 1030, 320);
	
// ---------------------------------------------------	

// -----------------------------------
//	COMBINED IMAGE PROBABILITY
// -----------------------------------

  IplImage *mexComb = cvCreateImage(cvSize(300, 400), IPL_DEPTH_8U, 1);
    		
	for (i = 0; i < mexComb->imageSize; i++)
		mexComb->imageData[i] = 0;

	//fConst = 255 / ( 128 * 128 );
	fConst = 0.015;
	fConst = 1;
	fConst *= 255;
	fConst /= 128;
	fConst /= 128;
	
	// normalize
	//dNorm = cvNorm(probComb, 0, CV_C, 0);
	//fConst = 128 / dNorm;
	 
	cvAdd(mexPos, mexNeg, mexComb, 0);
		
	/*
	for (i = 0; i < probComb->imageSize; i++)
		probComb->imageData[i] *= fConst;
	*/		
			
	// a visualization window is created with title 'image'
	cvNamedWindow ("imageProbComb", 1);
	cvShowImage ("imageProbComb", mexComb);
	cvResizeWindow("imageProbComb",300,400);
	cvMoveWindow ( "imageProbComb", 350, 320);
	
// ---------------------------------------------------

	// -----------------------------------------------------
	
// ---------------------------------------------------
	

		// tracking window
		track_window.x = 1;
        track_window.y = 1;
        track_window.width = 319;
        track_window.height = 239;
	
	// ----------------- jeffs code below -------------
// ------------------------------------------------

//@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
//@                                                                          @
//@  Title: void Visual_Setup ()                                             @
//@                                                                          @
//@  Description: Allocates the buffers for image processing.                @
//@               Uses OpenCV libraries.                                     @
//@                                                                          @
//@  Input:  none                                                            @
//@  Output: none                                                            @
//@                                                                          @
//@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

        capture = cvCaptureFromCAM(0); 

	if( !capture ) 
		{
		fprintf(stderr,"Could not initialize capturing...\n");
		exit(1);
		}

	//test resize here
	//frame = cvQueryFrame( capture );
	frame1 = cvQueryFrame( capture );	
	frame = cvCreateImage( cvSize(320,240), 8, 3);
	cvResize( frame1, frame, CV_INTER_LINEAR );
	
	image = cvCreateImage( cvGetSize(frame), 8, 3 );
	image->origin = frame->origin;
	hsv = cvCreateImage( cvGetSize(frame), 8, 3 );
	hue = cvCreateImage( cvGetSize(frame), 8, 1 );
	mask = cvCreateImage( cvGetSize(frame), 8, 1 );
	
	//test
	test1 = cvCreateImage( cvGetSize(frame), 8, 1 );
	maskRed = cvCreateImage( cvGetSize(frame), 8, 1 );
	maskYellow = cvCreateImage( cvGetSize(frame), 8, 1 );
	outputRed = cvCreateImage( cvGetSize(frame), 8, 1 );
	outputYellow = cvCreateImage( cvGetSize(frame), 8, 1 );
	//test
	
	green_backproject = cvCreateImage( cvGetSize(frame), 8, 1 );
	red_backproject = cvCreateImage( cvGetSize(frame), 8, 1 );
	yellow_backproject = cvCreateImage( cvGetSize(frame), 8, 1 );
	green_hist = cvCreateHist( 1, &hdims, CV_HIST_ARRAY, &hranges, 1 );
	green_hist = (CvHistogram *)cvLoad("blue.hist",0,0,0);
	red_hist = cvCreateHist( 1, &hdims, CV_HIST_ARRAY, &hranges, 1 );
	red_hist = (CvHistogram *)cvLoad("red.hist",0,0,0);
	yellow_hist = cvCreateHist( 1, &hdims, CV_HIST_ARRAY, &hranges, 1 );
	yellow_hist = (CvHistogram *)cvLoad("yellow.hist",0,0,0);
	
	/*
	cvNamedWindow( "Camera", 1 );
	cvNamedWindow( "Green", 1 );
	cvNamedWindow( "Red", 1 );
	cvNamedWindow( "Yellow", 1 );

	cvNamedWindow( "Test", 1 );
	cvNamedWindow( "OutputRed", 1 );
	cvNamedWindow( "OutputYellow", 1 );
	
	cvResizeWindow ( "Camera", 160, 120);
	cvMoveWindow ( "Camera", 10, 350);
	*/
	
while ( 0 ) 
//while ( 1 )
	{
	frame1 = cvQueryFrame( capture );
	//frame = cvQueryFrame( capture );
	
	if ( !frame1 ) 
		{
		return 0;
		}
	
	// test resize
	cvResize( frame1, frame, CV_INTER_LINEAR );
	
	cvCopy( frame, image, 0 );
	
	// display the camera image in a window
	//cvEllipseBox( image, track_box, CV_RGB(255,0,0), 3, CV_AA, 0 );
	//cvShowImage( "Camera", image );
	//cvResizeWindow ( "Camera", 320, 240);
	//cvMoveWindow ( "Camera", 10, 50);

	// put the image into a color space that can be used for color tracking
	cvCvtColor( image, hsv, CV_BGR2HSV );
	cvSplit( hsv, hue, 0, 0, 0 );

	// find the green and display in a window
	cvCalcBackProject( &hue, green_backproject, green_hist );
	cvShowImage( "Green", green_backproject );
	//cvResizeWindow ( "Green", 160, 120);
	cvResizeWindow ( "Green", 320, 240);
	cvMoveWindow ( "Green", 350, 50);
	
	// find the red and display in a window
	cvCalcBackProject( &hue, red_backproject, red_hist );
	cvShowImage( "Red", red_backproject );
	//cvResizeWindow ( "Red", 160, 120);
	//cvMoveWindow ( "Red", 520, 50);
	cvResizeWindow ( "Red", 320, 240);
	cvMoveWindow ( "Red", 690, 50);
	
	// find the Yellow and display in a window
	cvCalcBackProject( &hue, yellow_backproject, yellow_hist );
	cvShowImage( "Yellow", yellow_backproject );
	//cvResizeWindow ( "Yellow", 160, 120);
	//cvMoveWindow ( "Yellow", 690, 50);
	cvResizeWindow ( "Yellow", 320, 240);
	cvMoveWindow ( "Yellow", 1030, 50);
	
	
// -------------------------------------------------
//		
//		NEW CODE
//
// -------------------------------------------------

	// ----------------------------
	//		RED
	// ----------------------------
	// TEST SMOOTHING
	cvCopy( red_backproject, outputRed, 0 );
	//cvSmooth( outputRed, outputRed, CV_BLUR, 5, 5, 0, 0);				  					  
	//cvThreshold( outputRed, outputRed, 128, 255, CV_THRESH_BINARY );
	
	// test growing / dilate
	//cvDilate(outputRed, outputRed, 0, 15 ); // src,dst,kernal,iterations
	
	cvInRangeS( hsv, cvScalar(0, 192, 64, 0), cvScalar(180, 255, 255, 0), maskRed );
	// mask is the destination, clipping upper and lower pixels
	// smin, vmin and vmax are slider values.
	cvAnd( outputRed, maskRed, outputRed, 0 );
			
	// condition image				
	cvSmooth( outputRed, outputRed, CV_BLUR, 3, 3, 0, 0);				  					  
	cvThreshold( outputRed, outputRed, 32, 255, CV_THRESH_BINARY );
	cvDilate(outputRed, outputRed, 0, 20 ); // src,dst,kernal,iterations		
			
	// TESTING camshift
	cvCamShift( outputRed, track_window, cvTermCriteria( CV_TERMCRIT_EPS | CV_TERMCRIT_ITER, 10, 1 ), &track_comp, &track_box );
		
	track_box.angle = -track_box.angle;			
	cvEllipseBox( image, track_box, CV_RGB(255,0,255), 3, CV_AA, 0 );
	//cvShowImage( "Camera", image );
	
	// test new mask
	//cvAnd( outputRed, yellow_backproject, outputRed, 0 );
	cvShowImage( "OutputRed", outputRed );
	cvResizeWindow ( "OutputRed", 320, 240);
	cvMoveWindow ( "OutputRed", 690, 320);	

	// ----------------------------
	//		YELLOW
	// ----------------------------
	// TEST SMOOTHING
	cvCopy( yellow_backproject, outputYellow, 0 );
	//cvSmooth( outputYellow, outputYellow, CV_BLUR, 5, 5, 0, 0);				  					  
	//cvThreshold( outputYellow, outputYellow, 128, 255, CV_THRESH_BINARY );
	
	// test growing / dilate
	//cvDilate(outputYellow, outputYellow, 0, 10 ); // src,dst,kernal,iterations
	
	cvInRangeS( hsv, cvScalar(0, 128, 64, 0), cvScalar(180, 255, 255, 0), maskYellow );
	// mask is the destination, clipping upper and lower pixels
	// smin, vmin and vmax are slider values.
	cvAnd( outputYellow, maskYellow, outputYellow, 0 );
	
	// condition image				
	cvSmooth( outputYellow, outputYellow, CV_BLUR, 3, 3, 0, 0);				  					  
	cvThreshold( outputYellow, outputYellow, 32, 255, CV_THRESH_BINARY );
	//cvDilate(outputYellow, outputYellow, 0, 10 ); // src,dst,kernal,iterations		
			
	// TESTING camshift
	cvCamShift( outputYellow, track_window, cvTermCriteria( CV_TERMCRIT_EPS | CV_TERMCRIT_ITER, 10, 1 ), &track_comp, &track_box );
	track_box.angle = -track_box.angle;			
	cvEllipseBox( image, track_box, CV_RGB(255,255,0), 3, CV_AA, 0 );
	//cvShowImage( "Camera", image );
	
	// test new mask
	cvShowImage( "OutputYellow", outputYellow );
	cvResizeWindow ( "OutputYellow", 320, 240);
	cvMoveWindow ( "OutputYellow", 1030, 320);	
	
	
	// ---------------------------------
	//		output convolution
	// ---------------------------------
	cvAnd( outputRed, outputYellow, test1, 0 );
	
	// TESTING camshift
	cvCamShift( test1, track_window, cvTermCriteria( CV_TERMCRIT_EPS | CV_TERMCRIT_ITER, 10, 1 ), &track_comp, &track_box );
	//track_window = track_comp.rect;
	track_box.angle = -track_box.angle;			
	cvEllipseBox( image, track_box, CV_RGB(128,128,128), 3, CV_AA, 0 );
	//cvShowImage( "Camera", image );
	
	cvShowImage( "Test", test1 );
	cvResizeWindow ( "Test", 320, 240);
	cvMoveWindow ( "Test", 10, 320);
	
	// show final image ----------------------
	cvShowImage( "Camera", image );
	cvResizeWindow ( "Camera", 320, 240);
	cvMoveWindow ( "Camera", 10, 50);
	
	
	if ( cvWaitKey (1) != -1)
		{
		break;
		}
// ----------------- jeffs code above -------------
// ------------------------------------------------
	}
	
// wait for infinite delay for a keypress
  cvWaitKey (0);

// TEST SAVE IMAGE
cvSaveImage("test.bmp", img);

// memory release for img before exiting the application
  cvReleaseImage (&img);

	//cvReleaseVideoWriter(&writer);

// Self-explanatory
  cvDestroyWindow("image");

  return (0);
}

