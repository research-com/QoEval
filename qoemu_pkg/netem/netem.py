import logging as log
import shlex
import subprocess

MAX_CONNECTIONS = 3

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
            The name of the actual network device to be used by the connection

        Attributes
        ----------
        name : str
            The name of the connection
        device : str
            The name of the actual device that the connection uses
        virtual_device : str
            The name of the virutal device that the connection uses
        t_init : int
            the initial delay in ms of the connection
        rul : int
            upload rate limit in kbps of the connection
        rdl : int
            download rate limit in kbps of the connection
        dul : int
            upload delay in ms of the connection
        ddl : int
            download delay in ms of the connection
        """

    def __init__(self, name, device_name, t_init=None, rul=None, rdl=None, dul=None, ddl=None):
        global used_devices
        self.device = device_name
        self.name = name
        self.virtual_device = None
        self.t_init = t_init
        self.rul = rul
        self.rdl = rdl
        self.dul = dul
        self.ddl = ddl
        output = subprocess.run(['ifconfig'], stdout=subprocess.PIPE,
                                universal_newlines=True)
        if device_name not in output.stdout:
            log.error(f"Cannot initialize connection: {self.name}: Device does not exist")
            self.device = None
        elif device_name in used_devices:
            log.error(f"Cannot initialize connection: {self.name}: Device already in use")
            self.device = None
        else:
            used_devices.append(device_name)
            self._init()

    def _get_ifb(self):
        """Tries to set up a virtual device for this connection"""
        global ifb_is_initialized
        if not ifb_is_initialized:
            _init_ifb(MAX_CONNECTIONS)

        log.debug(f"Setting up virtual device for connection: {self.name}")
        output = subprocess.run(['ifconfig'], stdout=subprocess.PIPE,
                                universal_newlines=True)
        for i in range(MAX_CONNECTIONS):
            if f"ifb{i}" not in output.stdout:
                self.virtual_device = f"ifb{i}"
                _init_ifb_device(i)
                break
            log.error("No virtual device available. Could not initialize connection")
            return

    def _redirect(self):
        """Sets up the tc rules to redirect incoming traffic to the virtual device"""
        log.debug(f"Initializing tc redirection rules for connection: {self.name}")
        subprocess.run(shlex.split(f"tc qdisc add dev {self.device} ingress"))
        subprocess.run(shlex.split(f"tc filter add dev {self.device} parent ffff: "
                                   f"protocol all u32 match u32 0 0 flowid 1:1 "
                                   f"action mirred egress redirect dev {self.virtual_device}"))

    def _add_netem_qdiscs(self):
        """Add the netem qdiscs to both devices"""
        log.debug(f"Adding netem qdiscs to both devices for connection: {self.name}")
        subprocess.run(shlex.split(f"tc qdisc add dev {self.device} root netem"))
        subprocess.run(shlex.split(f"tc qdisc add dev {self.virtual_device} root netem"))

    def _init(self):
        """Initiates the connection, so that it can be used"""
        self._get_ifb()
        self._redirect()
        self._add_netem_qdiscs()

    def _update_outgoing(self):
        """Updates the netem qdisc for outgoing traffic for this connection"""
        log.debug(f"Changing egress netem qdisc for connection: {self.name}")
        subprocess.run(
            shlex.split(f"tc qdisc change dev {self.device} root netem rate {self.rul}kbit delay {self.dul}ms"))

    def _update_incoming(self):
        """Updates the netem qdisc for incoming traffic for this connection"""
        log.debug(f"Changing ingress netem qdisc for connection: {self.name}")
        subprocess.run(shlex.split(
            f"tc qdisc change dev {self.virtual_device} root netem rate {self.rdl}kbit delay {self.ddl}ms"))

    def change_parameters(self, t_init, rul, rdl, dul, ddl):
        """
                Sets the parameters for this connection and updates the netem qdiscs.


                Parameters
                ----------
                t_init : int
                    t_init in ms
                rul : int
                    rul in kbit/s
                rdl : int
                    rdl in kbit/s
                dul : int
                    dul in ms
                ddl : int
                    ddl in ms
                """
        self.t_init = t_init
        self.rul = rul
        self.rdl = rdl
        self.dul = dul
        self.ddl = ddl
        self._update_outgoing()
        self._update_incoming()

    def enable_netem(self):
        """(Re)enables the netem qdiscs for this connection"""

        if self.device is None or self.virtual_device is None:
            log.error(f"Cannot enable netem for connection: {self.name}: It is missing a device")
            return

        if None in [self.t_init, self.rul, self.rdl, self.dul, self.ddl]:
            log.error(f"Cannot enable netem for connection: {self.name}:: Not all parameters are set")
            return

        log.debug(f"Enabling netem for connection: {self.name}")
        self._update_incoming()
        self._update_outgoing()

    def disable_netem(self):
        """Disables the netem qdiscs for this connection."""

        if self.device is None or self.virtual_device is None:
            log.error(f"Cannot disable netem for connection: {self.name}: It is missing a device")
            return

        log.debug(f"Disabling netem for connection: {self.name}")
        subprocess.run(shlex.split(f"tc qdisc change dev {self.device} root netem"))
        subprocess.run(shlex.split(f"tc qdisc change dev {self.virtual_device} root netem"))

    def cleanup(self):
        """Removes all tc rules and virtual devices for this connection"""

        if self.device is None:
            log.error(f"Cannot cleanup connection: {self.name}: No device associated")
            return

        log.info(f"Cleaning up connection: {self.name}")
        log.debug(f"Removing tc rules for device: {self.device}")
        subprocess.run(shlex.split(f"tc qdisc del dev {self.device} root"))
        subprocess.run(shlex.split(f"tc qdisc del dev {self.device} ingress"))
        log.debug(f"Removing virtual device: {self.virtual_device}")
        subprocess.run(shlex.split(f"ip link set dev {self.virtual_device} down"))
        used_devices.remove(self.device)


def _init_ifb(numifbs):
    """
            Adds the ifb module to the kernel with numifbs devices available

            Parameters
            ----------
            numifbs : int
                number of ifb's available

            """
    log.debug("Adding ifb module to kernel")
    subprocess.run(shlex.split(f"modprobe ifb numifbs={numifbs}"))
    global ifb_is_initialized
    ifb_is_initialized = True


def _init_ifb_device(ifb_id):
    """
                Adds the ifb device with the specified id

                Parameters
                ----------
                ifb_id : int
                    id of the ifb device to be added

                """
    log.debug(f"Adding ifb{ifb_id}")
    subprocess.run(shlex.split(f"ip link set dev ifb{ifb_id} up"))


def cleanup_ifb():
    """Removes the ifb module from kernel"""
    subprocess.run(shlex.split(f"modprobe -r ifb"))
    log.info("Removed ifb module from kernel")
    global ifb_is_initialized
    ifb_is_initialized = False


def cleanup_actual_devices():
    """Removes tc rules from all actual devices"""
    for device in used_devices:
        log.debug(f"Removing tc rules for device: {device}")
        subprocess.run(shlex.split(f"tc qdisc del dev {device} root"))
        subprocess.run(shlex.split(f"tc qdisc del dev {device} ingress"))
        used_devices.remove(device)


def cleanup():
    """Removes ifb module and all tc rules for actual devices"""
    cleanup_actual_devices()
    cleanup_ifb()


