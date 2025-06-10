#ifndef MESSAGES
#define MESSAGES

#include <pthread.h>

typedef struct sync_struct_t {
	pthread_mutex_t mutex;	// Protects access to value 
	pthread_cond_t cond;	// Signals change to value 
	char name [80];
} sync_t;

#endif
