
# Go-Back-N Protocol | Python

## Overview
This project implements the **Go-Back-N** protocol, a sliding window-based reliable data transmission protocol. It simulates the **sender** and **receiver** interacting through queues, timeouts, packet acknowledgments, and retries. The protocol guarantees data delivery, handling dropped packets and out-of-order arrivals.

## Features
- **Sender**:
  - Divides an input file into **packets**.
  - Implements a **sliding window** for controlling the number of unacknowledged packets.
  - Handles **packet drops** and retransmission with **timeouts**.
  - Logs the status of each packet sent and dropped.

- **Receiver**:
  - Receives **packets**, processes them, and ensures they are in order.
  - Sends **acknowledgments** for each correctly received packet.
  - Reconstructs the original file from the received packets.

- **Multithreading**:
  - Sender and receiver work concurrently to handle packet transmission and reception.
  
- **File I/O**:
  - Sender reads the input file, converts data to **binary** for transmission.
  - Receiver reconstructs the data into the original file format.

## Requirements
- Python 3.x
- The `logging` library for logging events.

## Usage

### Sender
1. Provide the following arguments to initialize the sender:
   - `input_file`: Path to the file you want to send.
   - `window_size`: Size of the sliding window.
   - `packet_len`: Length of each packet.
   - `nth_packet`: Frequency of packet drops.
   - `timeout_interval`: Timeout duration in seconds.

2. The sender will divide the file into packets, send them through a queue, and handle timeouts and retransmissions.

### Receiver
1. The receiver listens for incoming packets and reconstructs the file.
2. After receiving all packets, the receiver writes the output to a file specified in the program.

## Example
Run the sender and receiver using separate terminal windows or processes.

1. **test_gbn.py**:
   Modify variables in test_gbn.py to your liking
   ```bash
    log_file = 'simulation.log'
    in_file = 'input_test.txt'
    out_file = 'output_test.txt'
    window_size = <integer>
    packet_len = <integer>
    nth_packet = <integer>
    timeout_interval = <integer>
   ```

## Logging
- Both sender and receiver log their actions using the `logging` library.
- Logs include information about **sent packets**, **acknowledgments**, **packet drops**, and **timeouts**.
