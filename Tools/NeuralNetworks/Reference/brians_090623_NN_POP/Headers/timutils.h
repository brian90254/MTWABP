#include <sys/time.h>
#include <unistd.h>

#define USEC_PER_SEC 1000000L
#define USEC_PER_MSEC 1000L

long time_elapsed (struct timeval t1, struct timeval t2);

