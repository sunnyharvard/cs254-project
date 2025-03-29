#include <math.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

#define LIST_SIZE 5

// Shared list and previous list for comparison
int list[LIST_SIZE];
int prev_list[LIST_SIZE];
float q = 0.1;

// Mutex for synchronizing list access
pthread_mutex_t list_mutex;

// 10MB (tweak size depending on CPU cache size)
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

#define MAX_SECRET 1048576
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

// Black box mitigator function that processes secrets and updates the list
int black_box_mitigator(int (*target_function)(int),
                        unsigned long long secrets[]) {
  // Allocate array to store the outputs
  int *outputs = malloc(LIST_SIZE * sizeof(int));

  // Iterate through secrets and call the target function, updating output list
  // every q seconds
  for (int i = 0; i < LIST_SIZE; i++) {
    outputs[i] = target_function(secrets[i]);
    pthread_mutex_lock(&list_mutex);
    list[i] = outputs[i];
    pthread_mutex_unlock(&list_mutex);
  }

  free(outputs);
  return 0;
}

// Thread function to print the list at intervals of q
void *q_interval(void *arg) {
  clock_t start_time = clock();
  while (1) {
    pthread_mutex_lock(&list_mutex);

    // Compare current list with previous list
    int is_same = 1;
    for (int i = 0; i < LIST_SIZE; i++) {
      if (list[i] != prev_list[i]) {
        is_same = 0;
        break;
      }
    }

    if (is_same) {
      q *= 2;
      if (q > 16)
        q = 16; // Cap q to prevent excessive delay
    } else {
      q = 0.1; // Reset q
      clock_t current_time = clock();
      double time_elapsed =
          (double)(current_time - start_time) / CLOCKS_PER_SEC;
      // Print the current list
      printf("Current List: ");
      for (int i = 0; i < LIST_SIZE; i++) {
        printf("%d ", list[i]);
      }
      printf("\n");
      // Print elapsed time since program started
      printf("Time spent: %f seconds\n", time_elapsed);
    }
    start_time = clock();

    // Copy current list to previous list
    for (int i = 0; i < LIST_SIZE; i++) {
      prev_list[i] = list[i];
    }

    pthread_mutex_unlock(&list_mutex);

    sleep(q); // Sleep for q seconds before next print
  }
  return NULL;
}

int main(void) {
  flush_cache();
  unsigned long long secrets[] = {pow(2, 17), pow(2, 18), pow(2, 19),
                                  pow(2, 20), pow(2, 21)};

  // Initialize list as all 0s
  for (int i = 0; i < LIST_SIZE; i++) {
    list[i] = 0;
  }

  // Initialize the mutex
  if (pthread_mutex_init(&list_mutex, NULL) != 0) {
    perror("Mutex initialization failed");
    return 1;
  }

  // Create the thread to print the list at intervals of q
  pthread_t print_thread;
  if (pthread_create(&print_thread, NULL, q_interval, NULL) != 0) {
    perror("Failed to create print thread");
    return 1;
  }

  // Run the black box mitigator to process the secrets and update the list
  black_box_mitigator(diff_output_timing_leak, secrets);

  pthread_join(print_thread, NULL);
  pthread_mutex_destroy(&list_mutex);

  return 0;
}

// FUTURE WORK:
// take program, only look at public info, make guess at how long program should
// take. when off the guess => make the delay.  use LLM to make guess of q + see
// where timing leak is + insert delay??
// new mitgation stat => liek second paper + add the lang context