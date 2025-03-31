#include <math.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

#define LIST_SIZE 5
#define MAX_SECRET 1048576

int queue[LIST_SIZE];
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
                        unsigned long long secrets[]) {
  int *outputs = malloc(LIST_SIZE * sizeof(int));

  for (int i = 0; i < LIST_SIZE; i++) {
    outputs[i] = target_function(secrets[i]);
    pthread_mutex_lock(&queue_mutex);

    if (queue_size < LIST_SIZE) {
      queue[queue_size++] = outputs[i];
    } else {
      for (int j = 1; j < LIST_SIZE; j++) {
        queue[j - 1] = queue[j];
      }
      queue[LIST_SIZE - 1] = outputs[i];
    }

    pthread_mutex_unlock(&queue_mutex);
  }

  free(outputs);
  return 0;
}

// thread function to print the queue at intervals of q
void *q_interval(void *arg) {
  clock_t start_time = clock();
  while (1) {
    pthread_mutex_lock(&queue_mutex);
    // If the queue is empty, double q
    if (queue_size == 0) {
      q *= 2;
      printf("q doubled to %f\n", q);
      if (q > 16) // Cap q to prevent excessive delay
        q = 16;
    } else if (queue_size >= 1) {
      clock_t current_time = clock();
      double time_elapsed =
          (double)(current_time - start_time) / CLOCKS_PER_SEC;
      int popped = queue[0];
      for (int i = 1; i < LIST_SIZE; i++) {
        queue[i - 1] = queue[i];
      }
      queue_size--;
      printf("Output: %d\n", popped);
      printf("Time spent: %f seconds\n", time_elapsed);
      total_printed++;
      if (queue_size == 0) {
        q /= 2;
        printf("q halved to %f\n", q);
      }
      start_time = clock();
    }

    pthread_mutex_unlock(&queue_mutex);

    // Check if we've printed all outputs
    if (total_printed >=
        LIST_SIZE) // Stop once we've printed the number of secrets
    {
      printf("All outputs printed, exiting...\n");
      break;
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

  // Initialize queue as all 0s
  for (int i = 0; i < LIST_SIZE; i++) {
    queue[i] = 0;
  }

  // Initialize the mutex
  if (pthread_mutex_init(&queue_mutex, NULL) != 0) {
    perror("Mutex initialization failed");
    return 1;
  }

  // Create the thread to print the queue at intervals of q
  pthread_t print_thread;
  if (pthread_create(&print_thread, NULL, q_interval, NULL) != 0) {
    perror("Failed to create print thread");
    return 1;
  }

  // Run the black box mitigator to process the secrets and update the queue
  black_box_mitigator(diff_output_timing_leak, secrets);

  pthread_join(print_thread, NULL);
  pthread_mutex_destroy(&queue_mutex);

  return 0;
}
