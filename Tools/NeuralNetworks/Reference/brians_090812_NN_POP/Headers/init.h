#ifndef INIT
#define INIT

#include <stdio.h>
#include "simdefs.h"

//@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
//@                                                             File: init.h @
//@                                                                          @
//@  Title: Initialization header file                                       @
//@                                                                          @
//@  Description: Initializes the network parameters for a simulation.       @
//@                                                                          @
//@                                                                          @
//@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

int  Init_Get_Group_Index (char *grp_name);
BOOL Init_Synapse (int proj_height, int proj_width, int from_height, int from_width, int to_height, int to_width, int from_inx, int to_inx, char *proj_type, double prob); 
void Init_Connection (char *line);
void Init_Group (char *line);
void Init_Network (FILE *fp);

#endif
