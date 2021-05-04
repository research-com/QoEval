"""

Analysis module, using pyshark and matplotlib

This module can sniff and collect traffic data on two interfaces (one for outgoing and one for incoming traffic)
and plot it.

Example usage:

Counting packets/bytes on "ifb0" (outgoing) and "ifb1" (incoming) for 10s with a resolution interval of 20ms
with a BPF to filter packets from/to the ip address 8.8.8.8

    coll = analysis.DataCollector("ifb0", "ifb1", 10, 20, bpf_filter="host 8.8.8.8")
    coll.start_threads()
    coll.start()

Showing a live plot of incoming packet count during the collection of the data:

    live_plt = analysis.LivePlot(coll, "p", "in")
    live_plt.show()

Plotting data from .csv file, second 2 to 5, packet count in/out, saving it as pdf with a resolution of 1600*600 pixels

    plt = analysis.Plot(coll.filename, 2, 5, "p")
    plt.save_pdf(1600, 600)

"""
import io
import logging as log
import math
import subprocess
import threading
import time
from datetime import datetime

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

TIME_FIELD = "time"
FIELDS = ["p", "b"]
DIRECTIONS = ["out", "in"]
PROTOCOLS = ["all", "udp", "tcp"]


class DataCollector:
    """This class listens on and collects data from two interfaces, one for outgoing and one for incoming traffic."""

    def __init__(self,
                 virtual_interface_out: str,
                 virtual_interface_in: str,
                 duration: int,
                 interval: int = 10,
                 filename: str = None,
                 bin_sizes: [] = None,
                 bpf_filter: str = ""):
        """
        Creates the object and sets all attributes.

        :param virtual_interface_out: The name of the interface on which outgoing traffic is sniffed
        :param virtual_interface_in: The name of the interface on which incoming traffic is sniffed
        :param interval: The interval in ms for which packet/byte counts
        :param duration: The duration in seconds for which data will be collected
        :param filename: The filename under which the data will be saved, if None a default will be used
        :param bpf_filter: A bpf_filter (Berkeley Packet Filter) applied to the packets
        """
        self.virtual_interface_out = virtual_interface_out
        self.virtual_interface_in = virtual_interface_in
        self.duration = duration
        self.interval = interval
        self.filename = filename
        self.bpf_filter = bpf_filter
        self.start_time = None
        self.is_initialized = False
        self.capture_started = False
        self.stop_listening_flag = False
        self.bin_sizes = bin_sizes
        self.data_array_size = math.ceil(self.duration / self.interval * 1000)
        self.data = {
            TIME_FIELD: np.arange(start=self.interval/1000,
                              stop=self.duration + self.interval/1000,
                              step=self.interval/1000)
        }
        for protocol in PROTOCOLS:
            for direction in DIRECTIONS:
                for field in FIELDS:
                    self.data[f"{field}_{direction}_{protocol}"] = np.zeros(self.data_array_size)


        if self.bin_sizes:
            for protocol in PROTOCOLS:
                for direction in DIRECTIONS:
                    for size in self.bin_sizes:
                        self.data[f"p_{direction}_{protocol}_<={size}"] = np.zeros(self.data_array_size)
                    self.data[f"p_{direction}_{protocol}_>{self.bin_sizes[len(self.bin_sizes) - 1]}"] = np.zeros(self.data_array_size)

    def _listen_on_interfaces(self):
        cmd = f"tshark -i {self.virtual_interface_in} -i {self.virtual_interface_out} " \
              f"-Tfields -e frame.number -e frame.time_epoch " \
              f"-e frame.cap_len -e frame.interface_name -e _ws.col.Protocol " \
              f"-f {self.bpf_filter}"  # -e eth.src -e eth.dst"
        proc = subprocess.Popen(cmd.split(" "), stdout=subprocess.PIPE)
        for line in io.TextIOWrapper(proc.stdout, encoding="utf-8"):
            yield line.rstrip().split("\t")
            if self.stop_listening_flag:
                break

        proc.terminate()
        self.stop_listening_flag = False

    def _is_out(self, packet):
        return packet[3] == self.virtual_interface_out

    def _is_in(self, packet):
        return packet[3] == self.virtual_interface_out

    @staticmethod
    def _is_udp(packet):
        return packet[4] == "UDP"

    @staticmethod
    def _is_tcp(packet):
        return packet[4] == "TCP"

    def _get_bin(self, packet):
        for size in self.bin_sizes:
            if int(packet[2]) <= size:
                return size
        return -1

    def _put_packet_in_bin(self, direction, protocol, length, packet_time_frame):
        if self.bin_sizes:
            for size in self.bin_sizes:
                if length <= size:
                    self.data[f"p_{direction}_{protocol}_<={size}"][packet_time_frame] += 1
                    return
            self.data[f"p_{direction}_{protocol}_>={self.bin_sizes[len(self.bin_sizes) - 1]}"][packet_time_frame] += 1
            return

    def _count_thread(self):
        """
        This function is meant to runs as a thread and counts packets using the _listen_on_interface function.
        """

        for packet in self._listen_on_interfaces():

            if not self.capture_started:
                continue
            if float(packet[1]) < self.start_time:
                continue

            packet_time_frame = math.floor((float(packet[1]) - self.start_time) / (self.interval/1000))

            # if the packet_time_frame is out of bounds we are finished writing data:
            if packet_time_frame >= self.data_array_size:
                log.info(f"Finished listening on interfaces: {self.virtual_interface_out}, {self.virtual_interface_in}")
                self.stop_listening_flag = True
                self._write_to_file()
                return

            length = int(packet[2])

            if self._is_out(packet):
                self.data["p_out_all"][packet_time_frame] += 1
                self.data["b_out_all"][packet_time_frame] += length
                self._put_packet_in_bin("out", "all", length, packet_time_frame)

                if self._is_tcp(packet):
                    self.data["p_out_tcp"][packet_time_frame] += 1
                    self.data["b_out_tcp"][packet_time_frame] += length
                    self._put_packet_in_bin("out", "tcp", length, packet_time_frame)

                if self._is_udp(packet):
                    self.data["p_out_udp"][packet_time_frame] += 1
                    self.data["b_out_udp"][packet_time_frame] += length
                    self._put_packet_in_bin("out", "udp", length, packet_time_frame)

            elif self._is_in(packet):
                self.data["p_in_all"][packet_time_frame] += 1
                self.data["b_in_all"][packet_time_frame] += length
                self._put_packet_in_bin("in", "all", length, packet_time_frame)

                if self._is_tcp(packet):
                    self.data["p_in_tcp"][packet_time_frame] += 1
                    self.data["b_in_tcp"][packet_time_frame] += length
                    self._put_packet_in_bin("in", "tcp", length, packet_time_frame)

                if self._is_udp(packet):
                    self.data["p_in_udp"][packet_time_frame] += 1
                    self.data["b_in_udp"][packet_time_frame] += length
                    self._put_packet_in_bin("in", "udp", length, packet_time_frame)



    def _write_to_file(self):
        df = pd.DataFrame.from_dict(self.data)
        if self.filename is None:
            self.filename = "QoEmu-Data " + str(datetime.fromtimestamp(self.start_time))

        df.to_csv(f"{self.filename}.csv", index=False)
        log.info("Finished writing to file")

    def start_threads(self):
        """
        Starts thread counting packets/bytes. Sleeps for 3 seconds afterwards to ensure they are active.
        """
        # create daemon
        count_thread = threading.Thread(target=self._count_thread)
        count_thread.setDaemon(True)
        count_thread.start()


        time.sleep(3)
        self.is_initialized = True

    def start(self):
        """
        Starts collection of data. "activate_capture" needs to be called first.
        """
        if not self.is_initialized:
            log.error("Packet capture not yet activated.")
            return
        self.start_time = time.time()
        self.capture_started = True


class Plot:
    """Offers methods to create a plots based on existing .csv data files."""

    def __init__(self,
                 filename: str,
                 start: int,
                 end: int,
                 packets_bytes: str,
                 direction: str = "in/out",
                 tick_interval: int = 10,
                 label_frequency: int = 10,
                 resolution_mult: int = 1,
                 x_size=1400,
                 y_size=600):
        """
        Creating this object will create a plot with the given parameters

        :param filename: Name of the file containing the data
        :param start: time in seconds from which point on the data should be plotted
        :param end: time in seconds to which point the data should be plotted
        :param packets_bytes: "p" or "b" to plot packets or bytes respectively
        :param direction: "in", "out" or any other string to plot incoming, outgoing or both
        :param tick_interval: Interval in ms between x ticks
        :param label_frequency: Frequency of labelled x ticks (i.e. every n-th tick will be labeled)
        :param resolution_mult: multiplier by which the plot will decrease the resolution of the data
        :param x_size: the default x size of plot in pixels
        :param y_size: the default y size of plot in pixels
        """
        self.filename = filename
        self.start = start
        self.end = end
        self.packets_bytes = packets_bytes
        self.direction = direction
        self.tick_interval = tick_interval
        self.label_frequency = label_frequency
        self.resolution_mult = resolution_mult
        self.x_size = x_size
        self.y_size = y_size

        self.x_values = []
        self.y_values = []
        self.fig = plt.figure()

        self._parse_data()
        self._create_bar_plot()
        self._arrange_xticks()
        self._label_axes()

    def _parse_data(self):
        """
        Reads .csv file and saves relevant data to self.x_values and self.y_values
        """

        df = pd.read_csv(self.filename)

        df = df[df[TIME_FIELD] >= self.start]
        df = df[df[TIME_FIELD] <= self.end]

        t_sum = 0  # used when summing up multiple rows of data

        for index, row in df.iterrows():

            if self.packets_bytes == "p":
                if self.direction == "in":
                    t = row["p_in_all"]
                elif self.direction == "out":
                    t = row["p_out_all"]
                else:
                    t = row["p_in_all"] + row["p_out_all"]
            else:
                if self.direction == "in":
                    t = row["b_in_all"]
                elif self.direction == "out":
                    t = row["b_out_all"]
                else:
                    t = row["b_in_all"] + row["b_out_all"]

            if (index + 1) % self.resolution_mult == 0:
                self.x_values.append(row[TIME_FIELD])
                t_sum += t
                self.y_values.append(t_sum)
                t_sum = 0

            else:
                t_sum += t

    def _create_bar_plot(self):
        """ Creates a bar plot with the parsed x and y values"""
        axes = self.fig.gca()

        axes.bar(self.x_values, self.y_values, align='edge',
                 width=(self.x_values[1]-self.x_values[0]) * 0.8 * self.resolution_mult)

    def _arrange_xticks(self):
        """ Arranges the x-ticks of the plot"""
        axes = self.fig.gca()
        axes.set_xticks(np.arange(self.start, self.end + self.tick_interval / 1000,
                                  float(self.tick_interval / 1000)))

        axes.xaxis.set_major_locator(plt.MultipleLocator(self.tick_interval * self.label_frequency / 1000))
        axes.xaxis.set_minor_locator(plt.MultipleLocator(self.tick_interval / 1000))
        axes.tick_params(which='major', length=5, labelsize="large")
        axes.tick_params(which='minor', length=2)

    def _label_axes(self):
        """ Labels the axes of the plot"""
        self.fig.gca().set_xlabel("Time in seconds")
        if self.packets_bytes == "p":
            s1 = "Packets "
        else:
            s1 = "Bytes "
        if self.direction == "in":
            s2 = "in"
        elif self.direction == "out":
            s2 = "out"
        else:
            s2 = "in/out"
        self.fig.gca().set_ylabel(f"{s1}{s2}")

    def _set_size(self, x, y):
        """Sets the size of the plot"""
        dpi = self.fig.get_dpi()
        self.fig.set_size_inches(x / float(dpi), y / float(dpi))

    def save_pdf(self, x_size=None, y_size=None):
        """Saves the plot as a pdf file in the given resolution or the default resolution"""
        if x_size is None:
            x_size = self.x_size
        if y_size is None:
            y_size = self.y_size
        self._set_size(x_size, y_size)

        self.fig.savefig(f'{self.filename}.pdf')

    def save_png(self, x_size=None, y_size=None):
        """Saves the plot as a png file in the given resolution or the default resolution"""
        if x_size is None:
            x_size = self.x_size
        if y_size is None:
            y_size = self.y_size
        self._set_size(x_size, y_size)

        self.fig.savefig(f'{self.filename}.png')


class LivePlot:
    """Plots the data of a given DataCollector live"""

    def __init__(self,
                 data_collector: DataCollector,
                 packets_bytes: str,
                 direction: str,
                 y_lim=None,
                 has_dynamic_x=False):

        """
        Initializes the Plot

        :param data_collector: The DataCollector collecting the data to be plotted
        :param packets_bytes: "p" or "b" to plot packet count/byte count respectively
        :param direction: "in", "out" or ""(both) to plot incoming, outgoing or both
        :param y_lim: limit of the y axis range. The default "None" will lead to a dynamic y axis range
        :param has_dynamic_x: Decides if x axis range is static or dynamic
        """
        self.data_collector = data_collector
        self.packets_bytes = packets_bytes
        self.direction = direction
        self.y_lim = 12
        self.has_dynamic_x = has_dynamic_x

        self.bar_count = self.data_collector.duration * 1000 // self.data_collector.interval
        self.x = []

        for i in range(self.bar_count):
            self.x.append(i * self.data_collector.interval / 1000)
        self.y = [0] * self.bar_count

        self.fig = plt.figure()

        self.bar_collection = plt.bar(self.x, self.y, align='edge', width=data_collector.interval / 1000 * 0.8)

        self.y_lim = y_lim
        if self.y_lim is None:
            self.has_dynamic_y = True
            self.y_lim = 1
        else:
            self.has_dynamic_y = False

        self.line_counter = 0
        self.bar_counter = 0
        self.draw_interval = 1000  # in ms

    def _animate(self, i):
        """The animate function called by animation.FuncAnimation()"""
        for i, timestamp in enumerate(self.data_collector.data[TIME_FIELD]):

            if self.packets_bytes == "p":
                if self.direction == "in":
                    t = self.data_collector.data["p_in_all"][i]
                elif self.direction == "out":
                    t = self.data_collector.data["p_out_all"][i]
                else:
                    t = self.data_collector.data["p_in_all"][i] + self.data_collector.data["p_out_all"][i]
            else:
                if self.direction == "in":
                    t = self.data_collector.data["b_in_all"][i]
                elif self.direction == "out":
                    t = self.data_collector.data["b_out_all"][i]
                else:
                    t = self.data_collector.data["b_in_all"][i] + self.data_collector.data["b_out_all"][i]
            self.bar_collection[i].set_height(t)
            if self.has_dynamic_y:
                if self.bar_collection[i].get_height() > self.y_lim:
                    self.y_lim = self.bar_collection[i].get_height()
                    plt.ylim(0, self.y_lim)

            if self.has_dynamic_x:
                plt.xlim(0, timestamp + 5 * self.data_collector.interval / 1000)

    def show(self, x_size=1400, y_size=600):
        """Shows the Live Plot with the given size in pixels
        :param x_size: x size of plot in pixels
        :param y_size: y size of plot in pixels
        """

        anim = animation.FuncAnimation(self.fig, self._animate,
                                       interval=self.draw_interval)

        plt.ylim(0, self.y_lim)
        plt.xlabel("Time in seconds")

        plt.xlabel("Time in seconds")
        if self.packets_bytes == "p":
            s1 = "Packets "
        else:
            s1 = "Bytes "
        if self.direction == "in":
            s2 = "in"
        elif self.direction == "out":
            s2 = "out"
        else:
            s2 = "in/out"
        plt.ylabel(f"{s1}{s2}")

        plt.xticks(np.arange(min(self.x), max(self.x) + 1, 0.2))

        xticks_pos, xticks_labels = plt.xticks()
        for i, l in enumerate(xticks_labels):
            if i % 5 != 0:  # only label every 5th tick
                l.set_visible(False)

        g = plt.gcf()
        dpi = g.get_dpi()
        g.set_size_inches(x_size / float(dpi), y_size / float(dpi))

        plt.show()
