import logging as log
import shlex
import subprocess
import os

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
            The name of the actual network device to be used by the connection.
            Will be set to None if the connection could not be initialized.

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

    __CMD_TC = "sudo tc"
    __CMD_IP = "sudo ip"
    __CMD_MODPROBE = "sudo modprobe"

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
        # instead, the install.sh script modofies /etc/sudoers to allow us to
        # execute tc, ip, modprobe without asking for a password

        # log.debug(f"checking for sudo privileges")
        # if os.geteuid() != 0:
        #     log.error(f"Cannot initialize connection: No sudo privileges")
        #     self.device = None
        #     raise RuntimeError('Cannot setup network emulation - missing privileges.')

        self.reset_device()    # FIXME: should not be necessary when implementation is completed

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
        """Tries to set up a virtual device for this connection

            Returns
            -------
            bool
                Returns True if ifb device could be created False otherwise"""
        global ifb_is_initialized
        if not ifb_is_initialized:
            self._init_ifb(MAX_CONNECTIONS)

        log.debug(f"Setting up virtual device for connection: '{self.name}'")
        output = subprocess.run(['ifconfig'], stdout=subprocess.PIPE,
                                universal_newlines=True)
        for i in range(MAX_CONNECTIONS):
            if f"ifb{i}" not in output.stdout:
                self.virtual_device = f"ifb{i}"
                log.debug(f"Initializing a new ifb device: ifb{i}")
                self._init_ifb_device(i)
                return True
        log.error("No virtual device available. Could not initialize connection")
        return False

    def _redirect(self):
        """Sets up the tc rules to redirect incoming traffic to the virtual device"""
        log.debug(f"Initializing tc redirection rules for connection: '{self.name}'")
        output = subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc add dev {self.device} ingress"))
        output.check_returncode()
        output = subprocess.run(shlex.split(f"{self.__CMD_TC} filter add dev {self.device} parent ffff: "
                                   f"protocol all u32 match u32 0 0 flowid 1:1 "
                                   f"action mirred egress redirect dev {self.virtual_device}"))
        output.check_returncode()

    def _add_netem_qdiscs(self):
        """Add the netem qdiscs to both devices"""
        log.debug(f"Adding netem qdiscs to both devices for connection: '{self.name}'")
        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc add dev {self.device} root netem"))
        output = subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc add dev {self.virtual_device} root netem"))
        output.check_returncode()

    def _init(self):
        """Initiates the connection, so that it can be used"""
        if self._get_ifb():
            self._redirect()
            self._add_netem_qdiscs()
            log.info(f"Connection: '{self.name}' initialized")
        else:
            raise RuntimeError('Uable to initialize device.')

    def _update_outgoing(self):
        """Updates the netem qdisc for outgoing traffic for this connection"""
        log.debug(f"Changing egress netem qdisc for connection: '{self.name}'")
        subprocess.run(
            shlex.split(f"{self.__CMD_TC} qdisc change dev {self.device} root netem rate {self.rul}kbit delay {self.dul}ms"))

    def _update_incoming(self):
        """Updates the netem qdisc for incoming traffic for this connection"""
        log.debug(f"Changing ingress netem qdisc for connection: '{self.name}'")
        subprocess.run(shlex.split(
            f"{self.__CMD_TC} qdisc change dev {self.virtual_device} root netem rate {self.rdl}kbit delay {self.ddl}ms"))

    def change_parameters(self, t_init=None, rul=None, rdl=None, dul=None, ddl=None):
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

    def enable_netem(self):
        """(Re)enables the netem qdiscs for this connection"""

        if self.device is None or self.virtual_device is None:
            log.error(f"Cannot enable netem for connection: '{self.name}': It is missing a device")
            return

        if None in [self.t_init, self.rul, self.rdl, self.dul, self.ddl]:
            log.error(f"Cannot enable netem for connection: '{self.name}':: Not all parameters are set")
            return

        log.debug(f"Enabling netem for connection: '{self.name}'")
        self._update_incoming()
        self._update_outgoing()

    def disable_netem(self):
        """Disables the netem qdiscs for this connection."""

        if self.device is None or self.virtual_device is None:
            log.error(f"Cannot disable netem for connection: '{self.name}': It is missing a device")
            return

        log.debug(f"Disabling netem for connection: '{self.name}'")
        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc change dev {self.device} root netem"))
        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc change dev {self.virtual_device} root netem"))

    def cleanup(self):
        """Removes all tc rules and virtual devices for this connection"""

        if self.device is None:
            log.error(f"Cannot cleanup connection: '{self.name}': No device associated")
            return

        log.info(f"Cleaning up connection: '{self.name}'")
        log.debug(f"Removing tc rules for device: {self.device}")
        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc del dev {self.device} root"))
        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc del dev {self.device} ingress"))
        log.debug(f"Removing virtual device: {self.virtual_device}")
        subprocess.run(shlex.split(f"{self.__CMD_IP} link set dev {self.virtual_device} down"))
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
