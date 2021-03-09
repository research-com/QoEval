"""

draft of the analysis module, using pyshark and matplotlib

for now it simply counts all packages traversing the interface
and displays a live graph

"""

import pyshark
import time
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
import threading
import time
import subprocess
import logging as log

# name of the network interface to be monitored
INTERFACE = "enx00e04c684348"

# update period in ms
RESOLUTION = 20

# global variable to count packets in one period
packet_count = 0

# check if interface exists
output = subprocess.run(['ifconfig'], stdout=subprocess.PIPE,
                        universal_newlines=True)
if INTERFACE not in output.stdout:
    log.error(f"Interface does not exist")
    exit(1)




# matplotlib animation
def animate(i):
    graph_data = open('data.txt', 'r').read()
    lines = graph_data.split('\n')
    xs = []
    ys = []
    for line in lines:
        if len(line) > 1:
            x, y = line.split(',')
            xs.append(float(x))
            ys.append(float(y))
    ax1.clear()
    ax1.plot(xs, ys)


def listen_on_interface(interface):
    """
    :param interface: The name of the interface on which to capture traffic
    :return: generator containing live packets
    """

    start = time.time()
    capture = pyshark.LiveCapture(interface=interface)
    global packet_count

    for item in capture.sniff_continuously():
        yield item


def counter():
    global packet_count
    for item in listen_on_interface(INTERFACE):
        #item.pretty_print()
        packet_count += 1


# writes data to file every period
def writer():
    start_time = time.time()
    global packet_count

    while True:
        fh = open('data.txt', 'a')
        time.sleep(float(RESOLUTION / 1000) - ((time.time() - start_time) % float(RESOLUTION / 1000)))
        fh.write(f"{time.time() - start_time},{packet_count}\n")
        packet_count = 0
        fh.close()


# clear the data file
open('data.txt', 'w').close()

# create daemons
counter = threading.Thread(target=counter, args=())
counter.setDaemon(True)

writer = threading.Thread(target=writer, args=())
writer.setDaemon(True)

counter.start()
writer.start()

# matplotlib
style.use('fivethirtyeight')
fig = plt.figure()
ax1 = fig.add_subplot(1, 1, 1)
ani = animation.FuncAnimation(fig, animate, interval=RESOLUTION)
plt.show()
