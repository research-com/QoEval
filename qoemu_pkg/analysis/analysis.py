"""

Analysis module, using pyshark and matplotlib

This module can sniff and collect traffic data on two interfaces (one for outgoing and one for incoming traffic)
and plot it.

Example usage:

Counting packets/bytes on "ifb0" (outgoing) and "ifb1" (incoming) for 10s with a resolution interval of 20ms
with a BPF to filter packets from/to the ip address 8.8.8.8

    coll = analysis.DataCollector("ifb0", "ifb1", 10, 20, bpf_filter="host 8.8.8.8")
    coll.init()
    coll.start()

Showing a live plot of incoming packet count during the collection of the data:

    live_plt = analysis.LivePlot(coll, "p", "in")
    live_plt.show()

Plotting data from .csv file, second 2 to 5, packet count in/out, saving it as pdf with a resolution of 1600*600 pixels

    plt = analysis.Plot(coll.filename, 2, 5, "p")
    plt.save_pdf(1600, 600)

"""
import logging as log
import subprocess
import threading
import time
from datetime import datetime

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyshark


class Interface:
    """This class represents an interface and contains its name and MAC address"""

    def __init__(self, name: str):
        """
        Creates an Interface object if an interface with the given name exists and finds it's MAC address.

        If no interface with the given name is found, the name will be set to None.

        :param name: The name of the interface
        """
        self.name = name
        # check if interface exists and if so find mac address
        output = subprocess.run(['ifconfig'], stdout=subprocess.PIPE,
                                universal_newlines=True)
        if self.name not in output.stdout:
            log.error(f"Interface {self.name} does not exist")
            self.name = None
        if self.name is not None:
            # get MAC addresses of interface
            found = False
            for line in output.stdout.split("\n"):
                if self.name in line:
                    found = True
                if found:
                    if "ether" in line:
                        self.mac = line.split()[1]
                        break


class Counter:
    """A container for the data collected on an interface during an interval.

     Attributes:

        packets: Count of total packets
        packets_in: Count of incoming packets
        packets_out: Count of outgoing packets
        bytes: Count of total bytes
        bytes_in: Count of incoming bytes
        bytes_out: Count of outgoing bytes
    """

    def __init__(self):
        self.packets = 0
        self.packets_out = 0
        self.packets_in = 0
        self.bytes = 0
        self.bytes_out = 0
        self.bytes_in = 0


class DataCollector:
    """This class listens on and collects data from two interfaces, one for outgoing and one for incoming traffic."""

    def __init__(self,
                 virtual_interface_out: str,
                 virtual_interface_in: str,
                 phsical_interface_mac_address : str,
                 duration: int,
                 interval: int = 10,
                 filename: str = None,
                 bpf_filter: str = "",
                 display_filter: str = ""):
        """
        Creates the object and sets all attributes.

        :param virtual_interface_out: The name of the interface on which outgoing traffic is sniffed
        :param virtual_interface_in: The name of the interface on which incoming traffic is sniffed
        :param interval: The interval in ms for which packet/byte counts
        :param duration: The duration in seconds for which data will be collected
        :param filename: The filename under which the data will be saved, if None a default will be used
        :param bpf_filter: A bpf_filter (Berkeley Packet Filter) applied to the packets
        :param display_filter: A display_filter (wireshark display filter) applied to the packets
        """
        self.virtual_interface_out = Interface(virtual_interface_out)
        self.virtual_interface_in = Interface(virtual_interface_in)
        self.physical_interface_mac_address = phsical_interface_mac_address
        self.duration = duration
        self.interval = interval
        self.filename = filename
        self.bpf_filter = bpf_filter
        self.display_filter = display_filter
        self.start_time = None
        self.is_initialized = False
        self.has_started = False
        self.counter_out = Counter()
        self.counter_in = Counter()
        self.data = {
            "time": [],
            "p_out": [],
            "p_in": [],
            "b_out": [],
            "b_in": [],

        }

    def _listen_on_interface(self, interface: Interface):
        """
        This function listens to an interface and yields traversing packets (matching the bpf_filter and display_filter)

            :param interface: The interface object representing the interface to listen on
        """

        log.info(f"Listening on interface: {interface.name}")
        capture = pyshark.LiveCapture(interface=interface.name,
                                      bpf_filter=self.bpf_filter,
                                      display_filter=self.display_filter)
        for item in capture.sniff_continuously():
            yield item

    def _count_thread(self, interface: Interface, counter: Counter):
        """
        This function is meant to runs as a thread and counts packets using the _listen_on_interface function.


        :param interface: The interface object representing the interface to listen on
        :param counter: The CountContainer used to temporarily store data in
        """

        for item in self._listen_on_interface(interface):

            counter.packets += 1
            length = int(item.length)
            counter.bytes += length

            if item.eth.src == self.physical_interface_mac_address:
                counter.packets_out += 1
                counter.bytes_out += length
            elif item.eth.dst == self.physical_interface_mac_address:
                counter.packets_in += 1
                counter.bytes_in += length
            if self.has_started:
                if time.time() - self.start_time > self.duration:
                    log.info(f"Finished listening on interface: {interface.name}")
                    return

    def _reset_counters(self):
        """
        resets all packet and byte counts in the Counter objects to 0
        """
        self.counter_out.packets = 0
        self.counter_out.packets_out = 0
        self.counter_out.packets_in = 0
        self.counter_out.bytes = 0
        self.counter_out.bytes_out = 0
        self.counter_out.bytes_in = 0
        if self.virtual_interface_in is not None:
            self.counter_in.packets = 0
            self.counter_in.packets_out = 0
            self.counter_in.packets_in = 0
            self.counter_in.bytes = 0
            self.counter_in.bytes_out = 0
            self.counter_in.bytes_in = 0

    def _write_to_data(self):
        """
        appends the current relevant packet and byte counts to the data object
        """
        self.data["time"].append(time.time() - self.start_time)
        self.data["p_out"].append(self.counter_out.packets_out)
        self.data["b_out"].append(self.counter_out.bytes_out)
        self.data["p_in"].append(self.counter_in.packets_in)
        self.data["b_in"].append(self.counter_in.bytes_in)

    # writes data to file every period
    def _write_thread(self):
        """
        Meant to run as a thread. Writes the collected data to the data object in intervals.
        """
        self._reset_counters()
        self.start_time = time.time()
        self.has_started = True

        while time.time() - self.start_time < self.duration:
            time.sleep(float(self.interval / 1000) - ((time.time() - self.start_time) % float(self.interval / 1000)))
            self._write_to_data()
            self._reset_counters()

        df = pd.DataFrame.from_dict(self.data)
        if self.filename is None:
            self.filename = "QoEmu-Data " + str(datetime.fromtimestamp(self.start_time))

        df.to_csv(f"{self.filename}.csv")
        log.info("Finished writing to file")

        return

    def activate_capture(self):
        """
        Starts threads counting packets/bytes. Sleeps for 1 seconds afterwards to ensure they are active.
        """
        # create daemons
        count_thread_out = threading.Thread(target=self._count_thread,
                                            args=([self.virtual_interface_out, self.counter_out]))
        count_thread_out.setDaemon(True)
        count_thread_out.start()

        count_thread_in = threading.Thread(target=self._count_thread,
                                           args=([self.virtual_interface_in, self.counter_in]))
        count_thread_in.setDaemon(True)
        count_thread_in.start()

        time.sleep(1)
        self.is_initialized = True

    def start(self):
        """
        Starts collection of data. "activate_capture" needs to be called first.
        """
        if not self.is_initialized:
            log.error("Packet capture not yet activated.")

        write_thread = threading.Thread(target=self._write_thread, args=())
        write_thread.setDaemon(True)

        write_thread.start()


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

        df = df[df["time"] >= self.start]
        df = df[df["time"] <= self.end]

        t_sum = 0  # used when summing up multiple rows of data

        for index, row in df.iterrows():

            if self.packets_bytes == "p":
                if self.direction == "in":
                    t = row["p_in"]
                elif self.direction == "out":
                    t = row["p_out"]
                else:
                    t = row["p_in"] + row["p_out"]
            else:
                if self.direction == "in":
                    t = row["b_in"]
                elif self.direction == "out":
                    t = row["b_out"]
                else:
                    t = row["b_in"] + row["b_out"]

            if (index + 1) % self.resolution_mult == 0:
                self.x_values.append(row["time"])
                t_sum += t
                self.y_values.append(t_sum)
                t_sum = 0

            else:
                t_sum += t

    def _create_bar_plot(self):
        """ Creates a bar plot with the parsed x and y values"""
        axes = self.fig.gca()

        axes.bar(self.x_values, self.y_values, align='edge',
                 width=self.tick_interval / 1000 * 0.5 * self.resolution_mult)

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
        for i, timestamp in enumerate(self.data_collector.data["time"][self.line_counter:]):

            if self.packets_bytes == "p":
                if self.direction == "in":
                    t = self.data_collector.data["p_in"][self.line_counter]
                if self.direction == "out":
                    t = self.data_collector.data["p_out"][self.line_counter]
                else:
                    t = self.data_collector.data["p_in"][self.line_counter] + self.data_collector.data["p_out"][
                        self.line_counter]
            else:
                if self.direction == "in":
                    t = self.data_collector.data["b_in"][self.line_counter]
                if self.direction == "out":
                    t = self.data_collector.data["b_out"][self.line_counter]
                else:
                    t = self.data_collector.data["b_in"][self.line_counter] + self.data_collector.data["b_out"][
                        self.line_counter]
            self.bar_collection[self.bar_counter].set_height(t)
            if self.has_dynamic_y:
                if self.bar_collection[self.bar_counter].get_height() > self.y_lim:
                    self.y_lim = self.bar_collection[self.bar_counter].get_height()
                    plt.ylim(0, self.y_lim)
            self.line_counter += 1
            self.bar_counter += 1

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
