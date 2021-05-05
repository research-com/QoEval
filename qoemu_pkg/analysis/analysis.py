"""

Analysis module, using tshark, pandas and matplotlib

This module can sniff and collect traffic data on two interfaces (one for outgoing and one for incoming traffic)
and plot it.

Example usage:

Counting packets/bytes on "ifb0" (outgoing) and "ifb1" (incoming) for 10s with a resolution interval of 20ms,
additionally sorting packets into bins for future histogram plots, with a BPF to filter packets from/to the ip address 8.8.8.8

    coll = analysis.DataCollector("ifb0", "ifb1", 10, 20, bin_sizes: [60, 120, 200, 500], bpf_filter="host 8.8.8.8")
    coll.start_threads()
    coll.start()

Showing a live plot of outgoing packet count during the collection of the data:

    live_plt = analysis.LivePlot(coll, value=analysis.PACKETS, direction=analysis.OUT)
    live_plt.show()

Plotting from the saved .csv file, second 2 to 5, packet count in and out separately as stacked bar plot,
packet protocol TCP, saving it as pdf with a resolution of 1600*600 pixels

    plt = analysis.Plot(coll.filename, start=2, end=5, value=analysis.PACKETS, directions=[analysis.IN, analysis.OUT],
                            protocols=[analysis.TCP], kind="bar", grid="both", stacked=True)

    plt.save_pdf(1600, 600)

"""
import io
import logging as log
import math
import re
import subprocess
import threading
import time
from datetime import datetime
import matplotlib.ticker as ticker
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PACKETS = "packets"
BYTES = "byte"
INOUT = "in/out"
OUT = "out"
IN = "in"
ALL = "all"
UDP = "UDP"
TCP = "TCP"
BIN = "bin"
TIME = "time"
SEP = ":"
VALUES = [PACKETS, BYTES]
DIRECTIONS = [INOUT, IN, OUT]
PROTOCOLS = [ALL, UDP, TCP]
BINS = []


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
        :param bin_sizes: list of integers representing the borders between bins for histogram creation
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
            TIME: np.arange(start=0,
                            stop=self.duration,
                            step=self.interval / 1000)
        }
        for protocol in PROTOCOLS:
            for direction in DIRECTIONS:
                for value in VALUES:
                    self.data[f"{SEP}{value}{SEP}{direction}{SEP}{protocol}{SEP}"] = np.zeros(self.data_array_size)

        if self.bin_sizes:
            for protocol in PROTOCOLS:
                for direction in DIRECTIONS:
                    for size in self.bin_sizes:
                        self.data[
                            f"{SEP}{PACKETS}{SEP}{direction}{SEP}{protocol}{SEP}{BIN}{SEP}<={size}{SEP}"] = np.zeros(
                            self.data_array_size)
                    self.data[
                        f"{SEP}{PACKETS}{SEP}{direction}{SEP}{protocol}{SEP}{BIN}{SEP}>{self.bin_sizes[len(self.bin_sizes) - 1]}{SEP}"] = np.zeros(
                        self.data_array_size)

    def _listen_on_interfaces(self):
        """
        This method will listen on both interfaces and yield the packets captured as lists of strings representing the
        properties of the packets.

        Due to python buffering, packets may be yielded out of order.
        """
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

    @staticmethod
    def _is_of_protocol(packet, protocol):
        if protocol == ALL:
            return True
        if protocol == packet[4]:
            return True
        return False

    def _get_direction(self, packet):
        if packet[3] == self.virtual_interface_out:
            return OUT
        return IN

    def _is_of_direction(self, packet, direction):
        if direction == INOUT:
            return True
        if direction == self._get_direction(packet):
            return True
        return False

    def _put_packet_in_bin(self, direction, protocol, length, packet_time_frame):
        if self.bin_sizes:
            for size in self.bin_sizes:
                if length <= size:
                    self.data[f"{SEP}{PACKETS}{SEP}{direction}{SEP}{protocol}{SEP}{BIN}{SEP}<={size}{SEP}"][
                        packet_time_frame] += 1
                    return
            self.data[
                f"{SEP}{PACKETS}{SEP}{direction}{SEP}{protocol}{SEP}{BIN}{SEP}>{self.bin_sizes[len(self.bin_sizes) - 1]}{SEP}"][
                packet_time_frame] += 1
            return

    def _count_thread(self):
        """
        This function is meant to runs as a thread and will sort packets yielded by the _listen_on_interface method
        into the data array.

        The method will return once it has counted all packets for the duration of the data collection.
        """

        for packet in self._listen_on_interfaces():

            if not self.capture_started:
                continue
            if float(packet[1]) < self.start_time:
                continue

            # packet_time_frame is the index of the packet time frame in the data arrays
            packet_time_frame = math.floor((float(packet[1]) - self.start_time) / (self.interval / 1000))

            # if the packet_time_frame is out of bounds we are not saving it to data:
            if packet_time_frame >= self.data_array_size:
                # packets can arrive out of order so we continue to look for packets for a few secs
                if float(packet[1]) >= self.start_time + self.duration + 2:
                    log.info(
                        f"Finished listening on interfaces: {self.virtual_interface_out}, {self.virtual_interface_in}")
                    self.stop_listening_flag = True
                    self._write_to_file()
                    return
                continue

            length = int(packet[2])

            for protocol in PROTOCOLS:
                for direction in DIRECTIONS:
                    if self._is_of_direction(packet, direction):
                        if self._is_of_protocol(packet, protocol):
                            self.data[f"{SEP}{PACKETS}{SEP}{direction}{SEP}{protocol}{SEP}"][packet_time_frame] += 1
                            self.data[f"{SEP}{BYTES}{SEP}{direction}{SEP}{protocol}{SEP}"][packet_time_frame] += length
                            self._put_packet_in_bin(direction, protocol, length, packet_time_frame)

    def _write_to_file(self):
        df = pd.DataFrame.from_dict(self.data)
        if self.filename is None:
            self.filename = "QoEmu-Data " + str(datetime.fromtimestamp(self.start_time))

        df.to_csv(f"{self.filename}.csv", index=False)
        log.info("Finished writing to file")

    def start_threads(self):
        """
        Starts thread counting packets. Sleeps for 3 seconds afterwards to ensure they are active.
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
    """Offers methods to create a plots based on existing .csv data files, created by the DataCollector object
        For now, one should create a new Plot object for every plot.
        """
    def __init__(self,
                 filename: str,
                 start: int,
                 end: int,
                 packets_bytes: str,
                 directions=None,
                 protocols=None,
                 kind=None,
                 grid=None,
                 stacked=False,
                 tick_interval: int = 100,
                 label_interval: int = 1000,
                 resolution_mult: int = 1,
                 x_size=1400,
                 y_size=600):
        """
        Creating this object will create a plot with the given parameters

        :param filename: Name of the file containing the data
        :param start: time in seconds from which point on the data should be plotted
        :param end: time in seconds to which point the data should be plotted
        :param packets_bytes: PACKETS or BYTES constant, value to be plotted over time
        :param directions: list of directions to be plotted (use IN, OUT and INOUT constants)
        :param protocols: list of packet protocols to be plotted (ALL, TCP, UDP)
        :param kind: "bar", "line" or "hist", type of the plot
        :param grid: None, "major", "both" or "minor" (not recommended), grid settings
        :param stacked: boolean, whether the bar plot should be stacked
        :param tick_interval: Interval in ms between x_ticks
        :param label_interval: Interval in ms between major x_ticks with labels
        :param resolution_mult: multiplier by which the plot will decrease the resolution of the data
        :param x_size: the default x size of plot in pixels
        :param y_size: the default y size of plot in pixels
        """
        if directions is None:
            directions = [INOUT]
        if protocols is None:
            protocols = [ALL]

        self.filename = filename
        self.start = start
        self.end = end
        self.kind = kind
        self.grid = grid
        self.stacked = stacked
        self.packets_bytes = packets_bytes
        self.directions = directions
        self.tick_interval = tick_interval
        self.label_interval = label_interval
        self.resolution_mult = resolution_mult
        self.x_size = x_size
        self.y_size = y_size
        self.protocols = protocols
        self.dataframe = None

        self.fig = plt.figure()

        self._parse_data()
        if self.kind == "bar":
            self._create_bar_plot(self.fig)
        if self.kind == "line":
            self._create_line_plot(self.fig)
        if self.kind == "hist":
            self._create_histogram(self.fig)

        self._set_size(self.x_size, self.y_size)

        self._label_axes(self.kind)


    def _parse_data(self):
        """
        Reads .csv file and creates a pandas dataframe
        """

        df = pd.read_csv(self.filename)

        self.interval = df[TIME][1] * 1000

        # find indices on both ends of time frame
        start_index = df.index[df[TIME] >= self.start][0]
        end_index = df.index[df[TIME] >= self.end][0]

        # make sure count of rows is divisible by resolution mult:
        end_index += (end_index - start_index + 1) % self.resolution_mult
        # make sure we're not out of bounds
        if end_index > df.tail(1).index.item():
            end_index -= self.resolution_mult

        # reduce dataframe to specified time frame
        df = df[df.index >= start_index]
        df = df[df.index <= end_index]

        if self.resolution_mult != 1:
            # if we combine rows using resolution_mult, we need to pick the correct rows from the "time" column
            times = df.iloc[::self.resolution_mult, :][TIME]
            times.reset_index(drop=True, inplace=True)
            # and sum up the of rows of the data
            df = df.drop(TIME, axis=1).groupby(np.arange(len(df)) // self.resolution_mult).sum()
            # reassemble time column and data
            self.dataframe = pd.concat([times, df], axis=1)
        else:
            self.dataframe = df

    def _create_line_plot(self, figure):
        """ Creates a line plot with the parsed x and y values"""
        # parse columns to be used
        columns = [TIME]
        for col in self.dataframe.columns:
            if (any(f"{SEP}{s}{SEP}" in col for s in self.directions)
                    and (any(f"{SEP}{s}{SEP}" in col for s in self.protocols))
                    and (f"{SEP}{self.packets_bytes}{SEP}" in col)
                    and not (f"{SEP}{BIN}{SEP}" in col)):
                columns.append(col)

        # reduce dataframe to used columns
        df = self.dataframe[columns]

        # plot with index set to time
        df.set_index(TIME).plot(kind="line", ax=figure.gca())

        # set major and minor tick position
        self.fig.gca().xaxis.set_minor_locator(plt.FixedLocator(df[TIME][::round(self.tick_interval/self.interval/self.resolution_mult)]))
        self.fig.gca().xaxis.set_major_locator(plt.FixedLocator(df[TIME][::round(self.label_interval/self.interval/self.resolution_mult)]))

        # format the ticks
        self.fig.gca().tick_params(which='major', length=5, labelrotation=0)
        self.fig.gca().tick_params(which='minor', length=2)

        # set grid
        if self.grid:
            plt.grid(True, which=self.grid)

        # create labels for  major ticks
        major_tick_labels = ["{:.2f}".format(item) for item in self.dataframe[TIME][::round(self.label_interval/self.interval/self.resolution_mult)]]

        # assign labels to major ticks
        self.fig.gca().xaxis.set_major_formatter(ticker.FixedFormatter(major_tick_labels))

    def _create_bar_plot(self, figure):
        """ Creates a bar plot with the parsed x and y values"""
        # parse columns to be used
        columns = [TIME]
        for col in self.dataframe.columns:
            if (any(f"{SEP}{s}{SEP}" in col for s in self.directions)
                    and (any(f"{SEP}{s}{SEP}" in col for s in self.protocols))
                    and (f"{SEP}{self.packets_bytes}{SEP}" in col)
                    and not (f"{SEP}{BIN}{SEP}" in col)):
                columns.append(col)

        # reduce dataframe to used columns
        df = self.dataframe[columns]
        df.set_index(TIME, inplace=True)

        # plot using pandas
        df.plot(kind="bar", stacked=self.stacked, align="edge", width=0.8, ax=figure.gca())

        # set grid
        if self.grid:
            plt.grid(True, which=self.grid)

        # set major and minor tick position
        self.fig.gca().xaxis.set_minor_locator(plt.FixedLocator(range(0, len(self.dataframe), round(self.tick_interval/self.interval/self.resolution_mult))))
        self.fig.gca().xaxis.set_major_locator(plt.FixedLocator(range(0, len(self.dataframe), round(self.label_interval/self.interval/self.resolution_mult))))

        # format the ticks
        self.fig.gca().tick_params(which='major', length=5, labelrotation=0)
        self.fig.gca().tick_params(which='minor', length=2)

        # create labels for  major ticks
        major_tick_labels = ["{:.2f}".format(item) for item in self.dataframe[TIME][::round(self.label_interval/self.interval / self.resolution_mult)]]

        # assign labels to major ticks
        self.fig.gca().xaxis.set_major_formatter(ticker.FixedFormatter(major_tick_labels))

    def _create_histogram(self, figure):

        data = {BIN: []}

        # regex for parsing bin sizes
        p = f"(?<={SEP}{PACKETS}{SEP}{IN}{SEP}{ALL}{SEP}{BIN}{SEP})\S+(?={SEP})"
        for col in self.dataframe.columns:
            # parse bins:
            if f"{SEP}{IN}{SEP}{ALL}{SEP}{BIN}{SEP}" in col:
                data[BIN].append(re.search(p, col)[0])

        # parse bin data
        for protocol in self.protocols:
            for direction in self.directions:
                data[f"{SEP}{PACKETS}{SEP}{direction}{SEP}{protocol}{SEP}"] = []
                for bin in data[BIN]:
                    data[f"{SEP}{PACKETS}{SEP}{direction}{SEP}{protocol}{SEP}"].append(
                        self.dataframe[f"{SEP}{PACKETS}{SEP}{direction}{SEP}{protocol}{SEP}{BIN}{SEP}{bin}{SEP}"].sum()
                    )
        # as dataframe
        df = pd.DataFrame(data)
        df.set_index(BIN, inplace=True)

        # plot using pandas
        df.plot(kind="bar", stacked=self.stacked, align="center", width=0.8, ax=figure.gca())

        # format labels
        self.fig.gca().tick_params(which='major', length=5, labelrotation=0)
        self.fig.gca().tick_params(which='minor', length=2)

    def _label_axes(self, type):
        """ Labels the axes of the plot"""
        if type in ["bar", "line"]:
            self.fig.gca().set_xlabel("Time in seconds")
            if self.packets_bytes == PACKETS:
                self.fig.gca().set_ylabel(PACKETS)
            if self.packets_bytes == BYTES:
                self.fig.gca().set_ylabel(BYTES)
        if type == "hist":
            self.fig.gca().set_xlabel("Packet size (byte)")
            self.fig.gca().set_ylabel(PACKETS)

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

    @staticmethod
    def show():
        """Shows the plot"""
        plt.show()


class LivePlot:
    """Plots the data of a given DataCollector live. Plot may behave unexpectedly because of buffering, which can lead
    to packets being processed much later than they arrive"""

    def __init__(self,
                 data_collector: DataCollector,
                 value: str,
                 direction: str,
                 y_lim=None,
                 has_dynamic_x=False):

        """
        Initializes the Plot

        :param data_collector: The DataCollector collecting the data to be plotted
        :param value: PACKETS or BYTES to plot packet count/byte count respectively
        :param direction: IN, OUT or INOUT to plot incoming, outgoing or both
        :param y_lim: limit of the y axis range. The default "None" will lead to a dynamic y axis range
        :param has_dynamic_x: Decides if x axis range is static or dynamic
        """
        self.data_collector = data_collector
        self.value = value
        self.direction = direction
        self.y_lim = 12
        self.has_dynamic_x = has_dynamic_x

        self.bar_count = self.data_collector.duration * 1000 // self.data_collector.interval
        self.x = []

        for i in range(self.bar_count):
            self.x.append(i * self.data_collector.interval / 1000)
        self.y = [0] * self.bar_count

        self.fig = plt.figure()

        # list of bars of plot
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
        for index, timestamp in enumerate(self.data_collector.data[TIME]):

            if self.direction == IN or self.direction == OUT:
                value = self.data_collector.data[f"{SEP}{self.value}{SEP}{self.direction}{SEP}{ALL}{SEP}"][
                    index]
            else:
                value = self.data_collector.data[f"{SEP}{self.value}{SEP}{IN}{SEP}{ALL}{SEP}"][index] \
                        + self.data_collector.data[f"{SEP}{self.value}{SEP}{OUT}{SEP}{ALL}{SEP}"][index]

            self.bar_collection[index].set_height(value)
            if self.has_dynamic_y:
                if self.bar_collection[index].get_height() > self.y_lim:
                    self.y_lim = self.bar_collection[index].get_height()
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

        # label axes
        self.fig.gca().set_xlabel("Time in seconds")
        if self.value == PACKETS:
            self.fig.gca().set_ylabel(PACKETS)
        if self.value == BYTES:
            self.fig.gca().set_ylabel(BYTES)

        # set xticks
        plt.xticks(np.arange(min(self.x), max(self.x) + 1, 0.2))

        xticks_pos, xticks_labels = plt.xticks()
        for i, l in enumerate(xticks_labels):
            if i % 5 != 0:  # only label every 5th tick
                l.set_visible(False)

        g = plt.gcf()
        dpi = g.get_dpi()
        g.set_size_inches(x_size / float(dpi), y_size / float(dpi))

        plt.show()
