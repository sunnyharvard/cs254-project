# -*- encoding: utf-8 -*-
"""
Implementation of queue-based timing mitigation system inspired by the C implementation
"""

import time
import threading
import queue
import random
import hashlib
import statistics
import matplotlib.pyplot as plt
import numpy as np
from functools import wraps
import secrets
import string

# --------------- Password Hashing Mechanism ---------------

def basic_fib_hash(password, max_length=50):
    """
    Basic Fibonacci hash implementation with potential timing vulnerability.
    
    Computes a hash by adding ASCII values of characters and using them to generate
    Fibonacci-like sequences. Limited to max_length for practical reasons.
    """
    if not password:
        return False
    
    if len(password) > max_length:
        password = password[:max_length]
    
    # Initialize hash value
    hash_value = 0
    
    for char in password:  # timing grows with number of characters in password
        # Get ASCII value of character
        ascii_val = ord(char)
        
        # Compute Fibonacci-like sequence to ascii_val steps
        a, b = 1, 1
        for _ in range(ascii_val):
            a, b = b, a + b
            # Print to simulate computational work that might be timed
            print(f"Finished step in character processing", end='\r')
        
        # Add result to hash value
        hash_value += b
    
    # Make it a fixed length by using standard hashing algorithm
    final_hash = hashlib.sha256(str(hash_value).encode()).hexdigest()
    return final_hash

# --------------- Slow Blackbox Mitigation System ---------------

class SlowBlackbox:
    def __init__(self, initial_interval=0.1):
        self.result_queue = queue.Queue()
        self.output_queue = queue.Queue()
        self.interval = initial_interval
        self.running = False
        self.total_processed = 0
        self.lock = threading.Lock()
        self.printer_thread = None

    def start(self):
        if not self.running:
            self.running = True
            self.printer_thread = threading.Thread(target=self._process_queue)
            self.printer_thread.daemon = True
            self.printer_thread.start()

    def stop(self):
        if self.running:
            self.running = False
            if self.printer_thread:
                self.printer_thread.join(timeout=2.0)

    def _process_queue(self):
        doubled = True
        while self.running:
            with self.lock:
                if self.result_queue.empty() and doubled:
                    self.interval *= 2
                    doubled = False
                elif not self.result_queue.empty():
                    result = self.result_queue.get()
                    self.output_queue.put(result)
                    self.total_processed += 1
                    doubled = True
            time.sleep(self.interval)

    def __call__(self, func, *args, **kwargs):
        if not self.running:
            self.start()
        result = func(*args, **kwargs)
        with self.lock:
            self.result_queue.put(result)
        try:
            output = self.output_queue.get(timeout=5.0)
            return output
        except queue.Empty:
            return result

    def flush(self):
        start_time = time.time()
        timeout = 10.0
        while not self.result_queue.empty():
            if time.time() - start_time > timeout:
                break
            time.sleep(0.1)
        return self.total_processed
    

class HalvingBlackbox:
    def __init__(self, initial_q=0.1):
        self.q = initial_q
        self.initial_q = initial_q
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        self.running = False
        self.print_thread = None
        self.total_printed = 0
        self.expected_outputs = 0

    def start(self, expected_outputs=5):
        self.running = True
        self.expected_outputs = expected_outputs
        self.print_thread = threading.Thread(target=self._print_queue)
        self.print_thread.daemon = True
        self.print_thread.start()

    def stop(self):
        self.running = False
        if self.print_thread:
            self.print_thread.join(timeout=2.0)

    def flush(self):
        flush_array = bytearray(10 * 1024 * 1024)
        for i in range(len(flush_array)):
            flush_array[i] = i % 256
        _ = flush_array[0]

    def _print_queue(self):
        start_time = time.perf_counter()
        while self.running:
            with self.lock:
                if self.queue.empty():
                    self.q *= 2
                    print(f"Queue empty. q doubled to {self.q:.4f}")
                else:
                    result = self.queue.get()
                    current_time = time.perf_counter()
                    elapsed = current_time - start_time
                    print(f"Output: {result}")
                    print(f"Time spent: {elapsed:.4f} seconds")
                    self.total_printed += 1

                    if not self.queue.empty():
                        self.q /= 2
                        print(f"Queue not empty. q halved to {self.q:.4f}")
                    start_time = time.perf_counter()

            if self.total_printed >= self.expected_outputs:
                print("All expected outputs printed. Exiting print thread.")
                break

            time.sleep(self.q)

    def __call__(self, func, *args, **kwargs):
        self.flush()  # simulate pre-work
        result = func(*args, **kwargs)

        # Add to output queue for staggered timing
        with self.lock:
            self.queue.put(result)

        return result

# Dictionary mapping mitigation names to their functions
MITIGATION_SYSTEMS = {
    'none': lambda f, *args, **kwargs: f(*args, **kwargs),  # No mitigation
    'slow': SlowBlackbox(),  # slow
    'halving': HalvingBlackbox(),
}

# --------------- Password Storage & Verification ---------------

class UserStore:
    """Simulates a user database with password hashing and verification"""
    
    def __init__(self):
        self.users = {}

    def register_user(self, phone, email, username, first, last, password):
        """Register a new user with 5 password hashes"""
        if username in self.users:
            return False, "Username already exists"
        
        # Generate 5 password permutations and hash them
        password_hashes = [basic_fib_hash(email), basic_fib_hash(username), 
                           basic_fib_hash(first), basic_fib_hash(last),
                           basic_fib_hash(password)]
        # for i in range(5):
        #     # Create a slightly modified password for each hash
        #     if i == 0:
        #         # First hash is the actual password
        #         modified_password = password
        #     else:
        #         # Others are permutations
        #         salt = str(i)
        #         modified_password = password + salt
            
        #     # Hash the password
        #     password_hash = basic_fib_hash(modified_password)
        #     password_hashes.append(password_hash)
        
        # Store user data
        self.users[username] = {
            'email': email,
            'password_hashes': password_hashes
        }
        
        return True, "User registered successfully"
    
    def verify_password(self, username, password, mitigation_system='none'):
        """
        Verify password using the specified mitigation system
        
        Args:
            username: User's username
            password: Password to verify
            mitigation_system: Name of the mitigation system to use (from MITIGATION_SYSTEMS)
        """
        if username not in self.users or mitigation_system not in MITIGATION_SYSTEMS:
            return False
        
        user_data = self.users[username]
        
        # Get the mitigation system instance
        mitigator = MITIGATION_SYSTEMS[mitigation_system]
        
        # Check against all 5 password hashes
        password_match = False
        
        for i, stored_hash in enumerate(user_data['password_hashes']):
            # Create a function that checks one hash
            def check_hash(pwd):
                test_hash = basic_fib_hash(pwd)
                print(f"Checking hash #{i+1}", flush=True)
                return test_hash == stored_hash
            
            # Apply the mitigation system to the hash check
            is_match = mitigator(check_hash, password)
            
            if is_match:
                password_match = True
        
        return password_match

# --------------- Timing Analysis Framework ---------------

def time_function(func):
    """Decorator to time function execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        return result, execution_time
    return wrapper

class TimingAnalyzer:
    """Framework for analyzing timing vulnerabilities in password verification"""
    
    def __init__(self, user_store):
        self.user_store = user_store
    
    def generate_passwords(self, correct_password, count=10):
        """Generate a mix of correct and incorrect passwords"""
        passwords = []
        
        # Add the correct password
        passwords.append(correct_password)
        
        # Add some incorrect passwords of different lengths
        for _ in range(count - 1):
            length = secrets.randbelow(10) + 5  # 5-14 characters
            incorrect_pass = ''.join(secrets.choice(string.ascii_letters + string.digits) 
                                    for _ in range(length))
            passwords.append(incorrect_pass)
        
        return passwords
    
    def analyze_mitigation_system(self, mitigation_name, username, passwords, trials=10):
        """Analyze timing characteristics of a verification method with a specific mitigation system"""
        # Create a wrapper function that calls verify_password with the specific mitigation
        def verify_with_mitigation(username, password):
            return self.user_store.verify_password(username, password, mitigation_name)
        
        timed_verify = time_function(verify_with_mitigation)
        
        results = []
        
        for password in passwords:
            times = []
            correct = []
            
            for _ in range(trials):
                is_valid, execution_time = timed_verify(username, password)
                times.append(execution_time)
                correct.append(is_valid)
            
            avg_time = statistics.mean(times)
            std_dev = statistics.stdev(times) if len(times) > 1 else 0
            is_correct = any(correct)
            
            results.append({
                'password': password,
                'is_correct': is_correct,
                'avg_time': avg_time,
                'std_dev': std_dev,
                'times': times
            })
        
        # If using mitigation, make sure to flush the queue
        if mitigation_name != 'none':
          MITIGATION_SYSTEMS[mitigation_name].flush()
        
        return results
    
    # def compare_mitigation_systems(self, username, correct_password, password_count=10, trials=10):
    #     """Compare timing characteristics of different mitigation systems"""
    #     mitigation_systems = list(MITIGATION_SYSTEMS.keys())
        
    #     passwords = self.generate_passwords(correct_password, password_count)
    #     all_results = {}
        
    #     for mitigation in mitigation_systems:
    #         print(f"Testing mitigation system: {mitigation}")
            
    #         if mitigation != 'none':
    #           MITIGATION_SYSTEMS[mitigation].start()
                
    #         results = self.analyze_mitigation_system(mitigation, username, passwords, trials)
    #         all_results[mitigation] = results

    #         if mitigation != 'none':
    #           MITIGATION_SYSTEMS[mitigation].stop()
            
    #     return all_results
    
    # def plot_results(self, all_results):
    #     """Plot timing comparison results"""
    #     mitigation_systems = list(all_results.keys())
    #     fig, axes = plt.subplots(len(mitigation_systems), 1, figsize=(10, 12), sharex=True)
        
    #     # Handle case with only one mitigation system
    #     if len(mitigation_systems) == 1:
    #         axes = [axes]
        
    #     for i, mitigation in enumerate(mitigation_systems):
    #         results = all_results[mitigation]
    #         correct_times = [r['avg_time'] for r in results if r['is_correct']]
    #         incorrect_times = [r['avg_time'] for r in results if not r['is_correct']]
            
    #         # Calculate statistics
    #         correct_mean = statistics.mean(correct_times) if correct_times else 0
    #         incorrect_mean = statistics.mean(incorrect_times) if incorrect_times else 0
    #         time_diff = abs(correct_mean - incorrect_mean)
            
    #         # Plot data
    #         ax = axes[i]
    #         x_positions = range(len(results))
    #         colors = ['green' if r['is_correct'] else 'red' for r in results]
            
    #         # Bar plot with error bars
    #         bars = ax.bar(x_positions, [r['avg_time'] for r in results], 
    #                       yerr=[r['std_dev'] for r in results], 
    #                       color=colors, alpha=0.7)
            
    #         # Add labels and statistics
    #         ax.set_title(f"Mitigation: {mitigation} (Diff: {time_diff:.6f}s)")
    #         ax.set_ylabel("Time (seconds)")
    #         ax.grid(True, linestyle='--', alpha=0.7)
            
    #         # Add legend
    #         ax.axhline(y=correct_mean, color='green', linestyle='-', alpha=0.5, label=f"Correct Mean: {correct_mean:.6f}s")
    #         ax.axhline(y=incorrect_mean, color='red', linestyle='-', alpha=0.5, label=f"Incorrect Mean: {incorrect_mean:.6f}s")
    #         ax.legend()
        
    #     axes[-1].set_xlabel("Password Trials")
    #     plt.tight_layout()
    #     plt.savefig('mitigation_timing_analysis.png')
    #     plt.close()
        
    #     return 'mitigation_timing_analysis.png'
    
    def calculate_epoch_changes(self, all_results, q_precision=0.01):
      """
      Count epoch changes based on changes in timing quantum q.
      Each time timing crosses into a different bin (quantum), we register a change.
      
      Args:
          all_results: dict of mitigation -> list of result dicts
          q_precision: float, the width of each timing quantum (e.g., 0.01s)
      """
      epoch_changes = {}

      for mitigation, results in all_results.items():
          q_epochs = []
          for result in results:
              for t in result["times"]:
                  quantum = round(t / q_precision)
                  q_epochs.append(quantum)

          if not q_epochs:
              epoch_changes[mitigation] = "N/A - no timing data"
              continue

          # Count how many times the quantum changes (sequentially)
          changes = 0
          for i in range(1, len(q_epochs)):
              if q_epochs[i] != q_epochs[i - 1]:
                  changes += 1

          epoch_changes[mitigation] = changes

      return epoch_changes

# --------------- Demo Usage ---------------

def run_timing_analysis(username="myuser", password="secretpass"):
    """Run a complete timing analysis demonstration"""
    # Initialize the user store
    store = UserStore()
    
    # Register the test user
    store.register_user("5551234567", "me@email.com", "myuser", "John", "Doe", "secretpass")
    
    # Create the timing analyzer
    analyzer = TimingAnalyzer(store)
    
    # Run the comparison
    print("Running timing analysis...")
    results = analyzer.compare_mitigation_systems(username, password, password_count=5, trials=5)
    
    # Plot the results
    print("Generating plot...")
    plot_file = analyzer.plot_results(results)
    
    # Calculate epoch changes
    print("Calculating epoch changes...")
    epoch_changes = analyzer.calculate_epoch_changes(results)
    
    print("\nEpoch changes analysis (lower is better):")
    for mitigation, changes in epoch_changes.items():
        print(f"  {mitigation}: {changes}")
    
    print(f"\nPlot saved to {plot_file}")
    return results, epoch_changes, plot_file

if __name__ == "__main__":
    run_timing_analysis()