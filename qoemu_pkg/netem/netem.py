import ipaddress
import logging as log
import shlex
import subprocess
import threading
import time
from typing import List

MAX_CONNECTIONS = 1

used_devices = []
ifb_is_initialized = False

class Connection:
    """
        The Connection object creates a controllable network connection.

        Parameters
        ----------
        name : str
            The name of the connection
        device_name : str
            The name of the actual network device to be used by the connection.
            Will be set to None if the connection could not be initialized.

        Attributes
        ----------
        name : str
            The name of the connection
        device : str
            The name of the actual device that the connection uses
        virtual_device_in : str
            The name of the virutal device that the connection uses
        t_init : float
            the initial delay in ms of the connection
        rul : float
            upload rate limit in kbps of the connection
        rdl : float
            download rate limit in kbps of the connection
        dul : float
            upload delay in ms of the connection
        ddl : float
            download delay in ms of the connection

        android_ip : ipaddress
            IP address of android device (emulator or real device). If specified, emulation is limited to this
            specific ip address (source and destination).
        exclude_ports : List[int]
            List of ports to be excluded from network emulation (e.g. for an ssh control connection)
        """

    __CMD_TC = "sudo tc"
    __CMD_IP = "sudo ip"
    __CMD_MODPROBE = "sudo modprobe"

    def __init__(self, name, device_name, t_init: float = None, rul: float = None, rdl:float = None, dul:float = None,
                 ddl:float = None, android_ip:ipaddress = None, exclude_ports: List[int] = None):
        global used_devices
        self.device = device_name
        self.name = name
        self.virtual_device_in = None
        self.virtual_device_out = None
        self.t_init = t_init
        self._t_init_active = False
        self.rul = rul
        self.rdl = rdl
        self.dul = dul
        self.ddl = ddl
        self.exclude_ports = exclude_ports
        self.android_ip = android_ip

        if(android_ip):
            log.debug(f"network emulation is applied only for IP address: {self.android_ip}")
        else:
            if self.exclude_ports and len(self.exclude_ports)>0:
                log.debug(f"network emulation is applied to all traffic except for traffic to/from ports: {self.exclude_ports}")
            else:
                log.debug(f"no android_ip specified, network emulation is applied to all traffic on {self.device}")

        log.debug(f"locating tc")
        output = subprocess.run(shlex.split(self.__CMD_TC), stderr=subprocess.PIPE,
                                universal_newlines=True)
        if output.returncode != 0:
            log.error(f"Cannot initialize connection: tc not found - please check if install.sh has modified sudoers correctly.")
            raise RuntimeError('External component not found.')

        log.debug(f"locating netem")
        output = subprocess.run(shlex.split("find /lib/modules/ -type f -name '*netem*'"),
                                stdout=subprocess.PIPE,
                                universal_newlines=True)
        if len(output.stdout) == 0:
            log.error(f"Cannot initialize connection: netem not found.")
            raise RuntimeError('External component not found.')

        # We should not execute the complete python script with superuser privileges
        # instead, the install.sh script modifies /etc/sudoers to allow us to
        # execute tc, ip, modprobe without asking for a password

        # log.debug(f"checking for sudo privileges")
        # if os.geteuid() != 0:
        #     log.error(f"Cannot initialize connection: No sudo privileges")
        #     self.device = None
        #     raise RuntimeError('Cannot setup network emulation - missing privileges.')

        self.reset_device()    # should not be necessary when implementation is completed

        output = subprocess.run(['ifconfig'], stdout=subprocess.PIPE,
                                universal_newlines=True)
        if device_name not in output.stdout:
            log.error(f"Cannot initialize connection: '{self.name}': Device does not exist")
            self.device = None
        elif device_name in used_devices:
            log.error(f"Cannot initialize connection: '{self.name}': Device already in use")
            self.device = None
        else:
            used_devices.append(device_name)
            self._init()

    def _get_ifb(self):
        """Tries to set up virtual devices for this connection

            Returns
            -------
            bool
                Returns True if ifb devices could be created False otherwise"""
        global ifb_is_initialized
        if not ifb_is_initialized:
            self._init_ifb(MAX_CONNECTIONS * 2)

        log.debug(f"Setting up virtual device for connection: '{self.name}'")
        output = subprocess.run(['ifconfig'], stdout=subprocess.PIPE,
                                universal_newlines=True)
        for i in range(MAX_CONNECTIONS * 2):
            if f"ifb{i}" not in output.stdout:
                if self.virtual_device_in is None:
                    self.virtual_device_in = f"ifb{i}"
                    log.debug(f"Initializing a new ifb device: ifb{i}")
                    self._init_ifb_device(i)
                    continue
                if self.virtual_device_out is None:
                    self.virtual_device_out = f"ifb{i}"
                    log.debug(f"Initializing a new ifb device: ifb{i}")
                    self._init_ifb_device(i)
                return True
        log.error("Not enough virtual devices available. Could not initialize connection")
        return False

    def _redirect_incoming(self):
        """Sets up the tc rules to redirect incoming traffic to the virtual_device_in"""
        log.debug(f"Initializing incoming tc redirection rules for connection: '{self.name}'")
        output = subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc add dev {self.device} ingress handle ffff:"))
        output.check_returncode()

        if self.android_ip:
            filter_match = f"match ip dst {self.android_ip}/32"
        else:
            filter_match = "match u32 0 0"

        # for each excluded port, we add a high(er) prio pass action
        remaining_prio = 1
        if self.exclude_ports:
            for p in self.exclude_ports:
                output = subprocess.run(shlex.split(f"{self.__CMD_TC} filter add dev {self.device} parent ffff: "
                                                    f"protocol all priority {remaining_prio} "
                                                    f"u32 match ip sport {p} 0xffff "
                                                    f"action pass"))
                output.check_returncode()
                output = subprocess.run(shlex.split(f"{self.__CMD_TC} filter add dev {self.device} parent ffff: "
                                                    f"protocol all priority {remaining_prio} "
                                                    f"u32 match ip dport {p} 0xffff "
                                                    f"action pass"))
                output.check_returncode()
                remaining_prio = remaining_prio + 1

        output = subprocess.run(shlex.split(f"{self.__CMD_TC} filter add dev {self.device} parent ffff: "
                                            f"protocol all priority {remaining_prio} u32 {filter_match} flowid 1:1 "
                                            f"action mirred egress redirect dev {self.virtual_device_in}"))
        output.check_returncode()

    def _redirect_outgoing(self):
        """Sets up the tc rules to redirect outgoing traffic to the virtual_device_out and after that the netem qdiscs"""
        log.debug(f"Initializing outgoing tc redirection rules for connection: '{self.name}'")
        # for each excluded port, we add a high(er) prio action to handle traffic in 1:1 (no netem)
        remaining_prio = 1
        if self.exclude_ports:
            for p in self.exclude_ports:
                output = subprocess.run(shlex.split(f"{self.__CMD_TC} filter add dev {self.device} parent 1: "
                                                    f"protocol all priority {remaining_prio} "
                                                    f"u32 match ip sport {p} 0xffff "
                                                    f"flowid 1:1"))
                output.check_returncode()
                output = subprocess.run(shlex.split(f"{self.__CMD_TC} filter add dev {self.device} parent 1: "
                                                    f"protocol all priority {remaining_prio} "
                                                    f"u32 match ip dport {p} 0xffff "
                                                    f"flowid 1:1"))
                output.check_returncode()
                remaining_prio = remaining_prio + 1

        if self.android_ip:
            # only traffic originating from emulator ip is handled by netem
             log.debug(f"Emulation enabled specifically for IP: {self.android_ip}")
             output = subprocess.run(shlex.split(f"{self.__CMD_TC} filter add dev {self.device} protocol ip "
                                                 f"priority {remaining_prio} parent 1: u32 "
                                                 f"match ip src {self.android_ip}/32 flowid 1:2 action mirred egress "
                                                 f" redirect dev {self.virtual_device_out}"))
             output.check_returncode()
        else:
            # all other traffic is handled in 1:2 by netem
            output = subprocess.run(shlex.split(
                f"{self.__CMD_TC} filter add dev {self.device} protocol all priority {remaining_prio} "
                f"parent 1: u32 match u32 0 0 flowid 1:2 action mirred egress redirect dev {self.virtual_device_out}"))
            output.check_returncode()

    def _add_netem_qdiscs(self):
        """Add the netem qdiscs to both the device and the virtual_device_in"""
        log.debug(f"Adding netem qdiscs to both devices for connection: '{self.name}'")

        # replace standard qdisc fq_codel (Fair Queueing with Controlled Delay) used by current Linux
        # versions with a simple prio queue
        # subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc replace dev {self.device} root pfifo")).check_returncode()

        # setup a simple priority queue - all traffic from emulator will be handled by 1:2 which has netem
        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc add dev {self.device} root handle 1: prio bands 2 priomap 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0")).check_returncode()
        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc add dev {self.device} parent 1:1 handle 10: prio")).check_returncode()
        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc add dev {self.device} parent 1:2 handle 20: netem")).check_returncode()

        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc add dev {self.virtual_device_in} root netem")).check_returncode()

    def _init(self):
        """Initiates the connection, so that it can be used"""
        if self._get_ifb():
            self._redirect_incoming()
            self._add_netem_qdiscs()
            self._redirect_outgoing()
            log.info(f"Connection: '{self.name}' initialized")
        else:
            raise RuntimeError('Uable to initialize device.')

    def _update_outgoing(self):
        """Updates the netem qdisc for outgoing traffic for this connection"""
        log.debug(f"Changing egress netem qdisc for connection: '{self.name}'")
        parent_id = "parent 1:2"
        if not self._t_init_active:
            subprocess.run(
                shlex.split(f"{self.__CMD_TC} qdisc change dev {self.device} "
                            f"{parent_id} netem rate {self.rul}kbit delay {self.dul}ms loss 0%")).check_returncode()
        else:
            # Variant 1: emulate T_init by packet loss during T_init
            # subprocess.run(
            #    shlex.split(f"{self.__CMD_TC} qdisc change dev {self.device} "
            #                f"{parent_id} netem loss 100%")).check_returncode()
            # Variant 2: emulate T_init by delaying packets (should be more realistic since T_init emulates connection setup)
            subprocess.run(
               shlex.split(f"{self.__CMD_TC} qdisc change dev {self.device} "
                           f"{parent_id} netem rate {self.rul}kbit delay {self.t_init}ms loss 0%")).check_returncode()

    def _update_incoming(self):
        """Updates the netem qdisc for incoming traffic for this connection"""
        log.debug(f"Changing ingress netem qdisc for connection: '{self.name}'")
        if not self._t_init_active:
            subprocess.run(shlex.split(
                f"{self.__CMD_TC} qdisc change dev {self.virtual_device_in} "
                f"root netem rate {self.rdl}kbit delay {self.ddl}ms loss 0%")).check_returncode()
        else:
            # Variant 1: emulate T_init by packet loss during T_init
            # subprocess.run(shlex.split(
            #     f"{self.__CMD_TC} qdisc change dev {self.virtual_device_in} "
            #     f"root netem loss 100%")).check_returncode()
            # Variant 2: emulate T_init by delaying packets (should be more realistic since T_init emulates connection setup)
            subprocess.run(shlex.split(
                f"{self.__CMD_TC} qdisc change dev {self.virtual_device_in} "
                f"root netem rate {self.rdl}kbit delay {self.t_init}ms loss 0%")).check_returncode()

    def change_parameters(self, t_init:float=None, rul:float=None, rdl:float=None, dul:float=None, ddl:float=None):
        """
                Sets the parameters for this connection and updates the netem qdiscs.


                Parameters
                ----------
                t_init : float
                    t_init in ms
                rul : float
                    rul in kbit/s
                rdl : float
                    rdl in kbit/s
                dul : float
                    dul in ms
                ddl : float
                    ddl in ms
                """
        if t_init:
            self.t_init = t_init
        if rul:
            self.rul = rul
        if rdl:
            self.rdl = rdl
        if dul:
            self.dul = dul
        if ddl:
            self.ddl = ddl
        self._update_outgoing()
        self._update_incoming()

    def enable_netem(self, consider_t_init: bool = True):
        """(Re)enables the netem qdiscs for this connection"""

        if self.device is None or self.virtual_device_in is None:
            log.error(f"Cannot enable netem for connection: '{self.name}': It is missing a device")
            return

        if None in [self.t_init, self.rul, self.rdl, self.dul, self.ddl]:
            log.error(f"Cannot enable netem for connection: '{self.name}':: Not all parameters are set")
            return

        log.debug(f"Enabling netem for connection: '{self.name}'")
        if(self.t_init > 0 and consider_t_init):
            self._t_init_thread = threading.Thread(target=self._emulate_t_init, args=())
            self._t_init_thread.start()
        else:
            self._update_incoming()
            self._update_outgoing()

    def disable_netem(self):
        """Disables the netem qdiscs for this connection."""

        if self.device is None or self.virtual_device_in is None:
            log.error(f"Cannot disable netem for connection: '{self.name}': It is missing a device")
            return

        log.debug(f"Disabling netem for connection: '{self.name}'")
        params = "rate 1000Gbit loss 0.0% delay 0ms duplicate 0% reorder 0% 0%"
        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc change dev {self.device} parent 1:2 netem {params}")).check_returncode()
        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc change dev {self.virtual_device_in} root netem {params}")).check_returncode()

    def cleanup(self):
        """Removes all tc rules and virtual devices for this connection"""

        if self.device is None:
            log.error(f"Cannot cleanup connection: '{self.name}': No device associated")
            return

        log.info(f"Cleaning up connection: '{self.name}'")
        log.debug(f"Removing tc rules for device: {self.device}")
        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc del dev {self.device} root"))
        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc del dev {self.device} ingress"))
        log.debug(f"Removing virtual device: {self.virtual_device_in}")
        subprocess.run(shlex.split(f"{self.__CMD_IP} link set dev {self.virtual_device_in} down"))
        used_devices.remove(self.device)

    def _init_ifb(self, numifbs):
        """
                Adds the ifb module to the kernel with numifbs devices available

                Parameters
                ----------
                numifbs : int
                    number of ifb's available

                """
        log.debug("Adding ifb module to kernel")
        subprocess.run(shlex.split(f"{self.__CMD_MODPROBE} ifb numifbs={numifbs}"))
        global ifb_is_initialized
        ifb_is_initialized = True

    def _init_ifb_device(self, ifb_id):
        """
                    Adds the ifb device with the specified id

                    Parameters
                    ----------
                    ifb_id : int
                        id of the ifb device to be added

                    """
        log.debug(f"Adding ifb{ifb_id}")
        subprocess.run(shlex.split(f"{self.__CMD_IP} link set dev ifb{ifb_id} up"))

    def _emulate_t_init(self):
        """Emulate T_init phase where data communication is not possible"""
        if self._t_init_active:
            raise RuntimeError('T_init emulation already active.')
        if self.t_init <= 0:
            return
        self._t_init_active = True
        log.debug("T_init active")
        self._update_incoming()
        self._update_outgoing()
        time.sleep(self.t_init/1000.0)
        self._t_init_active = False
        self._update_incoming()
        self._update_outgoing()
        log.debug("T_init done")

    def cleanup_ifb(self):
        """Removes the ifb module from kernel"""
        subprocess.run(shlex.split(f"{self.__CMD_MODPROBE} -r ifb"))
        log.debug("Removed ifb module from kernel")
        global ifb_is_initialized
        ifb_is_initialized = False

    def cleanup_actual_devices(self):
        """Removes tc rules from all actual devices"""
        for device in used_devices:
            log.debug(f"Removing tc rules for device: {device}")
            subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc del dev {device} root"))
            subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc del dev {device} ingress"))
            used_devices.remove(device)

    def cleanup(self):
        """Removes ifb module and all tc rules for actual devices"""
        self.cleanup_actual_devices()
        self.cleanup_ifb()
        log.info("Cleaned up all tc rules for actual devices and removed ifb module")

    def reset_device(self):
        """Resets all qdiscs and removes all virtual devices"""
        log.debug(f"Reset device: {self.device}")
        # delete possibly existing qdiscs but ignore errors - might simply not have qdiscs
        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc del dev {self.device} root"), stderr=subprocess.PIPE)
        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc del dev {self.device} ingress"), stderr=subprocess.PIPE)
        self.cleanup_ifb()
