from threading import Thread
import time


class GBN_sender:
    def __init__(self, input_file, window_size, packet_len, nth_packet, send_queue, ack_queue, timeout_interval,
                 logger):
        self.input_file = input_file
        self.window_size = window_size
        self.packet_len = packet_len
        self.nth_packet = nth_packet

        self.send_queue = send_queue
        self.ack_queue = ack_queue

        self.timeout_interval = timeout_interval
        self.logger = logger

        self.base = 0
        self.packets = self.prepare_packets()
        self.acks_list = []
        self.packet_timers = []

        self.packet_count = 0

        for _ in self.packets:
            self.acks_list.append(False)
            self.packet_timers.append(0)

        self.dropped_list = []
        self.in_queue = []

    def prepare_packets(self):
        packets = []
        try:
            with open(self.input_file, 'r') as file:
                content = file.read()
                # Generate ASCII string containing all binary data for the file
                ascii_String = ""
                for char in content:
                    character = format(ord(char), '08b')
                    ascii_String += character

                data_len = self.packet_len - 16
                count = 0
                packet_num = 0

                # Generate packets using ASCII string
                while count < len(ascii_String):
                    if len(ascii_String[data_len * packet_num:data_len * packet_num + 1]) > 0:
                        # Increase count by data end range of packet
                        count += data_len

                        # Generate packet ranging from data length, packet length - 16 (sequence number).
                        packet = "" + ascii_String[data_len * packet_num:data_len * (packet_num + 1)] + format(
                            packet_num, '016b')

                        # Add packet to packets list
                        packets.append(packet)

                        # Increment packet number to obtain
                        packet_num += 1
                    else:
                        break
            return packets

        except FileNotFoundError:
            print(f"File \"{self.input_file}\" not found")
        except Exception as e:
            print(f"prepare_packets exception: {e}")

    def send_packets(self):
        try:
            for packet_num in range(self.base, min(self.base + self.window_size, len(self.packets))):
                self.packet_count += 1
                packet = self.packets[packet_num]
                sequence_number = packet[-16:]

                # Check if the packet has been queued, or if it's supposed to be dropped due to it being nth packet
                if sequence_number not in self.dropped_list and self.packet_count % self.nth_packet == 0 and packet not in self.in_queue:
                    self.dropped_list.append(sequence_number)
                    self.logger.info(f"Sender: packet {packet_num} dropped")
                else:
                    # Otherwise, log the packet being sent, queue it and add time to packet timers list
                    self.logger.info(f"Sender: sending packet {packet_num}")
                    self.send_queue.put(packet)
                    self.in_queue.append(packet)
                    self.packet_timers.insert(packet_num, time.time())
        except Exception as e:
            print(f"send_packets exception: {e}")

    def send_next_packet(self):
        try:
            # Move base to most recently acknowledged packet
            while self.base < len(self.packets) and self.acks_list[self.base]:
                self.base += 1
            # Once it finds most recently acknowledged packet, check if base has reached the end of the queue,
            # or if the sliding window is about to reach the end
            if self.base < len(self.packets) and self.base + self.window_size <= len(self.packets):
                # And send the next batch of packets, starting from the last most recently acknowledged packet
                last_packet_index = self.base + self.window_size - 1
                packet = self.packets[last_packet_index]
                self.packet_count += 1
                packet_num = int(packet[-16:], 2)
                if packet not in self.dropped_list and self.packet_count % self.nth_packet == 0 and packet not in self.in_queue:
                    self.dropped_list.append(packet_num)
                    self.logger.info(f"Sender: packet {packet_num} dropped")
                else:
                    # Otherwise, log the packet being sent, queue it and add time to packet timers list
                    self.logger.info(f"Sender: sending packet {packet_num}")
                    self.send_queue.put(packet)
                    self.in_queue.append(packet)
                    self.packet_timers.insert(packet_num, time.time())
        except Exception as e:
            print(f"send_next_packet exception: {e}")

    def check_timers(self):
        try:
            current_time = time.time()
            # Initialize the current time
            for packet_num in range(self.base, min(self.base + self.window_size, len(self.packets))):
                # For each packet, check if any of the packets have exceeded their timeout limit
                if current_time - self.packet_timers[packet_num] > self.timeout_interval and not self.acks_list[
                    packet_num] and self.send_queue.empty() and self.ack_queue.empty():
                    self.logger.info(f"Sender: packet {packet_num} timed out")
                    return True
            return False
        except Exception as e:
            print(f"check_timer exception: {e}")

    def receive_acks(self):
        # While the base hasn't reached the end of the packets list, continually check for acknowledgements
        while self.base < len(self.packets):
            try:
                if not self.ack_queue.empty():
                    ack = self.ack_queue.get()
                    if not self.acks_list[ack]:
                        self.acks_list[ack] = True
                        self.logger.info(f"Sender: ack {ack} received")
                        self.send_next_packet()
                    else:
                        self.logger.info(f"Sender: ack {ack} received, ignoring")
            except Exception as e:
                print(f"receive_acks exception: {e}")

    def run(self):
        # Start the program by sending the first initial packets within the sliding window
        self.send_packets()
        # Start acknowledgement thread
        ack_thread = Thread(target=self.receive_acks)
        ack_thread.start()

        # Continually check for timeouts
        while self.base < len(self.packets):
            if self.check_timers():
                # If there is a timeout, send the same packets,
                # otherwise the acknowledgement thread will send the next batch
                self.send_packets()
        self.send_queue.put(None)
        ack_thread.join()


class GBN_receiver:
    def __init__(self, output_file, send_queue, ack_queue, logger):
        self.output_file = output_file
        self.send_queue = send_queue
        self.ack_queue = ack_queue
        self.logger = logger

        self.packet_list = []
        self.expected_seq_num = 0

    def process_packet(self, packet):
        # Find packet number through string
        packet_num = int(packet[-16:], 2)
        if self.expected_seq_num == packet_num:
            # Add full packet to list
            self.packet_list.append(packet)
            self.logger.info(f"Receiver: packet {packet_num} received")
            # Send acknowledgement to sender
            self.ack_queue.put(packet_num)
            self.expected_seq_num += 1
            return True
        else:
            self.logger.info(f"Receiver: packet {packet_num} received out of order")
            # Send acknowledgement of last acknowledged packet to sender
            self.ack_queue.put(self.expected_seq_num - 1)
            return False

    def write_to_file(self):
        # Create one big string full of all packet data
        binary_string = ""
        with open(self.output_file, "w") as file:
            for packet in self.packet_list:
                packet = packet[:-16]
                if len(packet) > 8:
                    # Rebuild packet data if the length is longer than 8 bits
                    for num in range(0, len(packet), 8):
                        if not num + 8 > len(packet):
                            packet_string = packet[num:num + 8]
                            binary_string += packet_string
                        else:
                            packet_string = packet[num:len(packet)]
                            binary_string += packet_string
                else:
                    binary_string += packet

            # Converts binary string into ASCII
            count = 0
            while count < len(binary_string):
                if not count + 8 > len(binary_string):
                    character = chr(int(binary_string[count:count + 8], 2))
                else:
                    character = chr(int(binary_string[count:len(binary_string)], 2))
                file.write(character)
                count += 8
            file.close()

    def run(self):
        while True:
            if not self.send_queue.empty():
                packet = self.send_queue.get()
                if packet is None:
                    break
                else:
                    self.process_packet(packet)
        self.write_to_file()
