// fortify_test.c
#include <stdio.h>

/* Commenting out or not using the string.h header will cause this
 * program to use the unprotected strcpy function.
 */
#include <string.h>

#include <stdlib.h>

int copy(char *buf, int len)
{
	char foo[18];
	int err;

	err = memcpy(foo, buf, len);

	printf("%s: %i\n", foo, err);
}


int main(int argc, char **argv)
{
	char buffer[3];
	char foo[10];
	int i;

	if (argc < 2)
		return -1;

	i = atoi(argv[1]);

	//__builtin___sprintf_chk(buffer, 0, __builtin_object_size(buffer, 0), "d: %d\n", i);
	//__builtin_sprintf(buffer, "d: %d\n", i);
	//snprintf(buffer,sizeof(buffer), "d: %d\n", i);
	//printf("buffer: %s\n", buffer);
	//memcpy(foo, buffer, i);
	
	//printf("foo: %s\n", foo);
	
	copy(argv[2], i);
	return 0;
}


