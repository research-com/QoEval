import os
import subprocess
from time import sleep

INTERFACE = 'enx00e04c684348'
CSV_FILENAME = '../../stimuli-params/VS.csv'


fileDir = os.path.dirname(os.path.realpath('__file__'))
filename = os.path.join(fileDir, CSV_FILENAME)

print(f"Opening {filename}")
fh = open(filename)

stimulus_id = ""
t_init = int
rul = int
rdl = int
dul = int
ddl = int
line_count = 0

subprocess.run(["sudo", "./init.sh", INTERFACE])

for line in fh:
    line_count += 1
    if line.startswith("VS-"):

        args = line.split(";")

        stimulus_id = args[0]
        t_init = args[2]
        rul = args[3]
        rdl = args[4]
        dul = args[5]
        ddl = args[6]

        print(f"line: {line_count}, stimulus_id:{stimulus_id}, t_init:{t_init}ms, rul:{rul}kbit/s, rdl:{rdl}kbit/s, dul:{dul}ms, ddl:{ddl}ms")
        print(f"Dropping all outgoing traffic for {float(t_init) / 1000}s")

        bashCommand = f"sudo tc qdisc change dev {INTERFACE} root netem loss random 100%"
        subprocess.run(bashCommand.split())

        # initiate video capture here
        print(f"Initiate video capture here")

        sleep(float(t_init)/1000)

        print(f"Slept for <{float(t_init) / 1000}s> (t_init)")
        print("Setting rates")

        bashCommand = f"sudo tc qdisc change dev {INTERFACE} root netem rate {rul}kbit delay {dul}ms"
        subprocess.run(bashCommand.split())

        bashCommand = f"sudo tc qdisc change dev ifb0 root netem rate {rdl}kbit delay {ddl}ms"
        subprocess.run(bashCommand.split())

        print("Rates set")

        if input('Enter for next line, "x" to exit') == "x":
            break


fh.close()

subprocess.run(["sudo", "./cleanup.sh", INTERFACE, ])
