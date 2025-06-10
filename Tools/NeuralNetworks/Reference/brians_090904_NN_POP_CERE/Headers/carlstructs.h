#ifndef CARLSTRUCTS
#define CARLSTRUCTS

#include "simdefs.h"

#define DATA_PORT	3490
#define GOODSOCK	"goodsock"

typedef struct carl_cmd_struct{
	unsigned char forward;
	unsigned char turn;
	unsigned char slip;
	unsigned char pan;
	unsigned char tilt;
	char tag[32];
} carl_cmd_t;

typedef struct carl_data_struct {
	int cycle;
	long cycle_time;
	int control_override;
	char behave_state[32];
	char tag[32];
} carl_data_t;

#endif
