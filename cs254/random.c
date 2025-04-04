#include <math.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

#define MAX_SECRET 1048576

// Dynamically calculated size based on the secrets array
int *queue;
int queue_size = 0;
float q = 0.1;
int total_printed = 0;

pthread_mutex_t queue_mutex;
#define CACHE_FLUSH_SIZE (10 * 1024 * 1024)

void flush_cache() {
  char *flush_array = (char *)malloc(CACHE_FLUSH_SIZE);
  for (int i = 0; i < CACHE_FLUSH_SIZE; i++) {
    flush_array[i] = i;
  }
  volatile char temp = flush_array[0]; // prevent optimization
  free(flush_array);
}

// Fibonacci (target func example)
long long fibonacci(int n) {
  if (n <= 1)
    return n;
  return fibonacci(n - 1) + fibonacci(n - 2);
}

// No timing leak
int no_timing_leak(int secret) {
  int result = 0;
  for (int i = 0; i < MAX_SECRET; i++) {
    int mask = (i < secret); // 1 if i < secret, 0 otherwise
    result += mask * ((fibonacci(i % 20)) % 5);
  }
  return 0;
}

// Timing leak where output depends on secret
int diff_output_timing_leak(int secret) {
  int result = 0;
  for (int i = 0; i < secret; i++) {
    result += (fibonacci(i % 20)) % 5;
  }
  return result;
}

// Timing leak where output is constant
int same_output_timing_leak(int secret) {
  int result = 0;
  for (int i = 0; i < secret; i++) {
    result += (fibonacci(i % 20)) % 5;
  }
  return 0;
}

// Black box mitigator function
int black_box_mitigator(int (*target_function)(int),
                        unsigned long long secrets[], int secrets_size) {
  int *outputs = malloc(secrets_size * sizeof(int));

  for (int i = 0; i < secrets_size; i++) {
    outputs[i] = target_function(secrets[i]);
    pthread_mutex_lock(&queue_mutex);

    if (queue_size < secrets_size) {
        queue[queue_size++] = outputs[i];
    } else {
      for (int j = 1; j < secrets_size; j++) {
        queue[j - 1] = queue[j];
      }
      queue[secrets_size - 1] = outputs[i];
    }

    pthread_mutex_unlock(&queue_mutex);
  }

  free(outputs);
  return 0;
}

// Thread function to print the queue at intervals of q
void *q_interval(void *arg) {
  clock_t start_time = clock();
  while (1) {
    pthread_mutex_lock(&queue_mutex);
    // If the queue is empty, double q

    /*logic here: we want to randomize q everytime there is information to be output. We are not keeping track of a q. 
    We will show that this randomization method is inefficient, and does not show a logarithmic bound (in actuality, no bound at all)
   */
    // if (queue_size - queue_size_prev < 0 && !q_updated) { //randomize q if no information output at epoch
    //   q =  ((float)rand()/(float)(RAND_MAX)) * 8.0; //get random q (float) between 0 and 8 
    //   printf("q time randomized %f\n", q); //print when we have nothing is q, event expected
    //   q_updated = 1;
    // } 

    if (queue_size >= 1) {
        clock_t current_time = clock();
        double time_elapsed =
            (double)(current_time - start_time) / CLOCKS_PER_SEC;
        int popped = queue[0];
        for (int i = 1; i < queue_size; i++) {
          queue[i - 1] = queue[i];
        }
        queue_size--;
        q =  ((float)rand()/(float)(RAND_MAX)) * 8.0; //get random q (float) between 0 and 8
        printf("q time randomized %f\n", q); //print when we have nothing is q, event expected
 
        printf("Output: %d\n", popped);
        printf("Time spent: %f seconds\n", time_elapsed);
        total_printed++;
  
        start_time = clock();
    }

    pthread_mutex_unlock(&queue_mutex);

    // Check if we've printed all outputs
    if (total_printed >= queue_size && total_printed >= *(int *)arg) {
      printf("All outputs printed, exiting...\n");
      break; // Exit once all elements are printed
    }

    sleep(q); // Sleep for q seconds before next print
  }
  return NULL;
}

int main(void) {
  flush_cache();
  unsigned long long secrets[] = {pow(2, 17), pow(2, 18), pow(2, 19),
                                  pow(2, 20), pow(2, 21)};
  int secrets_size = sizeof(secrets) / sizeof(secrets[0]);

  // Dynamically allocate memory for the queue based on secrets_size
  queue = malloc(secrets_size * sizeof(int));

  if (queue == NULL) {
    perror("Failed to allocate memory for queue");
    return 1;
  }

  // Initialize the mutex
  if (pthread_mutex_init(&queue_mutex, NULL) != 0) {
    perror("Mutex initialization failed");
    free(queue); // Free allocated memory for queue
    return 1;
  }

  // Create the thread to print the queue at intervals of q
  pthread_t print_thread;
  if (pthread_create(&print_thread, NULL, q_interval, &secrets_size) != 0) {
    perror("Failed to create print thread");
    free(queue); // Free allocated memory for queue
    return 1;
  }

  // Run the black box mitigator to process the secrets and update the queue
  black_box_mitigator(diff_output_timing_leak, secrets, secrets_size);

  pthread_join(print_thread, NULL);
  pthread_mutex_destroy(&queue_mutex);
  free(queue); // Free allocated memory for queue

  return 0;
}
