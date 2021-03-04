import logging as log
import shlex
import subprocess
from time import sleep

interface = ""
interface_is_set = False
t_init = 0
rul = 50000
rdl = 50000
dul = 0
ddl = 0


def set_interface_name(interface_name):
    """
        Sets the global interface variable.

        To address the correct network interface, its name must be set with this function.

        Parameters
        ----------
        interface_name : str
            the name of the interface

        """

    global interface
    global interface_is_set
    interface = interface_name
    interface_is_set = True


def _init_ifb0():
    """Sets up the virtual network interface ifb0"""
    log.debug("Setting up ifb0")
    subprocess.run(shlex.split("modprobe ifb"))
    subprocess.run(shlex.split("ip link set dev ifb0 up"))


def _init_tc():
    """Sets up the tc rules to redirect incoming traffic to the virtual device ifb0"""
    log.debug("Initializing tc rules")
    subprocess.run(shlex.split(f"tc qdisc add dev {interface} ingress"))
    subprocess.run(shlex.split(f"tc filter add dev {interface} parent ffff: "
                               f"protocol all u32 match u32 0 0 flowid 1:1 action mirred egress redirect dev ifb0"))


def _init_netem_qdiscs():
    """Adds the netem qdiscs to both interfaces"""
    log.debug("Adding netem qdiscs")
    subprocess.run(shlex.split(f"tc qdisc add dev {interface} root netem"))
    subprocess.run(shlex.split(f"tc qdisc add dev ifb0 root netem"))


def init():
    if not interface_is_set:
        log.error("Interface is not defined")
        return
    """Executes all steps to initialize the module"""
    _init_ifb0()
    _init_tc()
    sleep(0.1)
    _init_netem_qdiscs()
    log.info("Netem initialized")


def _change_outgoing():
    """Changes the netem qdisc for outgoing traffic using the globally set parameters"""
    log.debug("Changing egress netem qdiscs")
    subprocess.run(shlex.split(f"tc qdisc change dev {interface} root netem rate {rul}kbit delay {dul}ms"))


def _change_incoming():
    """Changes the netem qdisc for incoming traffic using the globally set parameters"""
    log.debug("Changing ingress netem qdiscs")
    subprocess.run(shlex.split(f"tc qdisc change dev ifb0 root netem rate {rdl}kbit delay {ddl}ms"))


def change_parameters(t_init_new, rul_new, rdl_new, dul_new, ddl_new):
    """
        Changes the parameters globally and changes the netem qdiscs accordingly.

        Extended description of function.

        Parameters
        ----------
        t_init_new : int
            t_init in ms
        rul_new : int
            rul in kbit/s
        rdl_new : int
            rdl in kbit/s
        dul_new : int
            dul in ms
        ddl_new : int
            ddl in ms
        """
    global t_init
    global rul
    global rdl
    global dul
    global ddl
    t_init = t_init_new
    rul = rul_new
    rdl = rdl_new
    dul = dul_new
    ddl = ddl_new
    _change_incoming()
    _change_outgoing()


def simulate_t_init():
    """Simulates t_init by dropping all outgoing packets for the duration"""
    log.info(f"Simulating t_init, dropping all outgoing traffic for {t_init}ms")
    subprocess.run(shlex.split(f"tc qdisc change dev {interface} root netem loss random 100%"))
    sleep(float(t_init)/1000)
    enable()


def enable():
    """(Re)enables the netem qdiscs with the current global parameters."""
    log.debug("Enabling netem")
    _change_incoming()
    _change_outgoing()


def disable():
    """Disables the netem qdiscs."""
    log.debug("Disabling netem")
    subprocess.run(shlex.split(f"tc qdisc change dev {interface} root netem"))
    subprocess.run(shlex.split(f"tc qdisc change dev ifb0 root netem"))


def cleanup():
    """Removes all tc rules and virtual devices"""
    subprocess.run(shlex.split(f"tc qdisc del dev {interface} root"))
    subprocess.run(shlex.split(f"tc qdisc del dev {interface} ingress"))
    subprocess.run(shlex.split(f"modprobe -r ifb"))
    log.info("Cleaned up")
    return

