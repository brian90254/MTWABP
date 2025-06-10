#ifndef RANDNUMS
#define RANDNUMS

/*@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
//@                                                                            @
//@     Title:  Random Number Routines                 	       File randnums.h @
//@                                                                            @
//@     Set of routines for generating random numbers.                         @
//@                                                                            @
//@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@*/

#include <stdlib.h>
#include <math.h>

void rndseed (int seed);
double rnd01 ();
double rnduniform (double min, double max);
double gaussdev ();
double rndgauss (double mean, double stdev);

#endif
