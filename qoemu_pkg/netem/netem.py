import dataclasses
from dataclasses import dataclass, field
import ipaddress
import logging as log
import shlex
import subprocess
import threading
import time
import math
from typing import List
import csv
from timeit import default_timer as timer

MAX_CONNECTIONS = 1

USED_DEVICES = []
IFB_IS_INITIALIZED = False
CMD_MODPROBE = "sudo modprobe"
CMD_TC = "sudo tc"
CMD_IP = "sudo ip"


@dataclass
class ParameterSet:
    """Parameters and timeframe determining for how long the parameters shall be applied for dynamic emulation

    Except for the timeframe, a value of -1 will leave the parameter as it was

    Attributes:
        timeframe: the time in ms for which this set of parameters shall be active, set to -1 for an infinite timeframe
        rul: upload rate in kbit/s
        rdl: download rate in kbit/s
        dul: upload delay in ms
        ddl: download delay in ms
    """
    timeframe: float
    rul: float
    rdl: float
    dul: float = field(default=-1)
    ddl: float = field(default=-1)


@dataclass
class DynamicParametersSetup:
    """Contains ParameterSet objects for emulation with dynamic parameters

    Dynamic emulation can loop over these parameter sets and apply their parameters for the given timeframe

    Attributes:
        parameter_sets: the parameters sets to be looped over by dynamic emulation
        verbose: decides whether netem changes are being logged

    Example Usage:

        A_5000 = DynamicParametersSetup.from_csv("../../stimuli-params/variable_throughput/A_5000.csv")

        connection = Connection("enp51s0", "enp51s0", rul=50000, rdl=10000, dul=50, ddl=50, t_init=100,
                      dynamic_parameters_setup=A_5000)
        connection.enable_netem(consider_t_init=True, consider_dynamic_parameters=True)


    """
    parameter_sets: List[ParameterSet] = field(default_factory=list, init=False)
    verbose: bool = field(default=False)

    @staticmethod
    def from_nested_lists(parameter_sets: List[List[int]], verbose: bool = False):
        '''Creates a DynamicParamterSetup from nested lists, each list representing a ParameterSet'''
        result = DynamicParametersSetup(verbose=verbose)
        result._append_parameter_sets_from_nested_lists(parameter_sets)
        return result

    @staticmethod
    def from_csv(filename: str, verbose: bool = False):
        '''Loads a DynamicParamterSetup from a .csv file'''
        result = DynamicParametersSetup(verbose=verbose)
        result._append_from_csv(filename)
        return result

    def _append_parameter_set(self, parameter_set: ParameterSet):
        self.parameter_sets.append(parameter_set)

    def _append_parameter_sets(self, parameter_sets: List[ParameterSet]):
        for parameter in parameter_sets:
            self.parameter_sets.append(parameter)

    def _append_parameter_set_from_list(self, *args):
        self.parameter_sets.append(ParameterSet(*args))

    def _append_parameter_sets_from_nested_lists(self, parameter_sets: List[List[int]]):
        for parameter_set in parameter_sets:
            if len(parameter_set) == 0:
                continue
            self.parameter_sets.append(ParameterSet(*parameter_set))

    def save_to_csv(self, filename: str):
        ''' Saves the ParameterSetup as .csv file'''
        with open(filename, 'w') as file:
            data = [dataclasses.astuple(parameter_set) for parameter_set in self.parameter_sets]

            writer = csv.writer(file)
            writer.writerow(data_field.name for data_field in dataclasses.fields(ParameterSet))
            writer.writerows(data)

    def _append_from_csv(self, filename: str):
        ''' Append ParamterSets to the list of ParamtersSets from a .csv file'''
        with open(filename, newline='') as file:
            reader = csv.reader(file)
            raw_data = list(reader)
            data = [list(map(int, parameter_set)) for parameter_set in raw_data[1:]]
            self._append_parameter_sets_from_nested_lists(data)



class Connection:
    """
        The Connection object creates a controllable network connection.

        Attributes
        ----------
        name : str
            The name of the connection
        device_name : str
            The name of the actual network device to be used by the connection.
            Will be set to None if the connection could not be initialized.
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
        dynamic_parameters_setup: DynamicParametersSetup
            To emulate dynamic parameters
        """

    __CMD_TC = CMD_TC
    __CMD_IP = CMD_IP
    __CMD_MODPROBE = CMD_MODPROBE

    def __init__(self, name, device_name, t_init: float = None, rul: float = None, rdl:float = None, dul:float = None,
                 ddl:float = None, android_ip:ipaddress = None, exclude_ports: List[int] = None,
                 dynamic_parameters_setup: DynamicParametersSetup = None):
        global USED_DEVICES
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
        self.dynamic_parameters_setup = dynamic_parameters_setup
        if self.dynamic_parameters_setup and len(self.dynamic_parameters_setup.parameter_sets) == 0:
            log.warning(f"DynamicParametersSetup for connection {self.name} is empty")
        self.android_ip = android_ip
        self._dynamic_emulation_thread = None
        self.emulation_is_active = False

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
        elif device_name in USED_DEVICES:
            log.error(f"Cannot initialize connection: '{self.name}': Device already in use")
            self.device = None
        else:
            USED_DEVICES.append(device_name)
            self._init()

    def _get_ifb(self):
        """Tries to set up virtual devices for this connection

            Returns
            -------
            bool
                Returns True if ifb devices could be created False otherwise"""
        global IFB_IS_INITIALIZED
        if not IFB_IS_INITIALIZED:
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

    def _update_outgoing(self, verbose=True):
        """Updates the netem qdisc for outgoing traffic for this connection"""

        parent_id = "parent 1:2"

        start = timer()

        if not self._t_init_active:
            subprocess.run(
                shlex.split(f"{self.__CMD_TC} qdisc change dev {self.device} "
                            f"{parent_id} netem limit {Connection.calculate_netem_limit(self.dul, self.rul)} rate {self.rul}kbit delay {self.dul}ms loss 0%")).check_returncode()
        else:
            # Variant 1: emulate T_init by packet loss during T_init
            # subprocess.run(
            #    shlex.split(f"{self.__CMD_TC} qdisc change dev {self.device} "
            #                f"{parent_id} netem loss 100%")).check_returncode()
            # Variant 2: emulate T_init by delaying packets (should be more realistic since T_init emulates connection setup)
            subprocess.run(
               shlex.split(f"{self.__CMD_TC} qdisc change dev {self.device} "
                           f"{parent_id} netem rate {self.rul}kbit delay {self.t_init}ms loss 0%")).check_returncode()

        end = timer()

        if verbose:
            delay = (end - start) * 1000.0
            log.debug(f"Changed egress netem qdisc for connection: '{self.name}'. It took {delay:.2f} ms.")

    def _update_incoming(self, verbose=True):
        """Updates the netem qdisc for incoming traffic for this connection"""

        start = timer()

        if not self._t_init_active:
            subprocess.run(shlex.split(
                f"{self.__CMD_TC} qdisc change dev {self.virtual_device_in} "
                f"root netem limit {Connection.calculate_netem_limit(self.ddl, self.rdl)} rate {self.rdl}kbit delay {self.ddl}ms loss 0%")).check_returncode()
        else:
            # Variant 1: emulate T_init by packet loss during T_init
            # subprocess.run(shlex.split(
            #     f"{self.__CMD_TC} qdisc change dev {self.virtual_device_in} "
            #     f"root netem loss 100%")).check_returncode()
            # Variant 2: emulate T_init by delaying packets (should be more realistic since T_init emulates connection setup)
            subprocess.run(shlex.split(
                f"{self.__CMD_TC} qdisc change dev {self.virtual_device_in} "
                f"root netem rate {self.rdl}kbit delay {self.t_init}ms loss 0%")).check_returncode()

        end = timer()

        if verbose:
            delay = (end - start) * 1000.0
            log.debug(f"Changed egress netem qdisc for connection: '{self.name}'. It took {delay:.2f} ms.")

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

    @staticmethod
    def calculate_netem_limit(delay: float, rate: float) -> int:
        """
                Calculate the limit parameter for a netem queuing discipline.


                Parameters
                ----------
                :param delay: delay [ms]
                :param rate: data rate [kbit/s]
                :return limit parameter as integer value [packets]
        """
        # Prevent a limit of 0 when delay is 0
        if delay == 0:
            delay = 1
        # Note: assumed average packet size (use a rather small size since a large limit does not hurt much)
        return math.ceil(((delay*rate)/128)*1.5)


    def enable_netem(self, consider_t_init: bool = True, consider_dynamic_parameters: bool = True):
        """(Re)enables the netem qdiscs for this connection"""

        if self.device is None or self.virtual_device_in is None:
            log.error(f"Cannot enable netem for connection: '{self.name}': It is missing a device")
            return

        if None in [self.t_init, self.rul, self.rdl, self.dul, self.ddl]:
            log.error(f"Cannot enable netem for connection: '{self.name}':: Not all parameters are set")
            return

        log.debug(f"Enabling netem for connection: '{self.name}'")
        self.emulation_is_active = True
        emulate_t_init = self.t_init > 0 and consider_t_init
        emulate_dynamic_parameters = consider_dynamic_parameters \
                                     and self.dynamic_parameters_setup is not None \
                                     and len(self.dynamic_parameters_setup.parameter_sets) > 0
        if consider_dynamic_parameters and not emulate_dynamic_parameters:
            log.warning(f"Dynamic parameters cannot be considered - dynamic parameter setup is not available.")

        emulate_dynamically = emulate_t_init or emulate_dynamic_parameters
        if emulate_dynamically:
            self._dynamic_emulation_thread = threading.Thread(target=self._emulate_dynamically,
                                                              args=(emulate_t_init, emulate_dynamic_parameters),
                                                              daemon=True)
            self._dynamic_emulation_thread.start()
        else:
            self._update_incoming()
            self._update_outgoing()

    def disable_netem(self):
        """Disables the netem qdiscs for this connection."""

        if self.device is None or self.virtual_device_in is None:
            log.error(f"Cannot disable netem for connection: '{self.name}': It is missing a device")
            return

        log.debug(f"Disabling netem for connection: '{self.name}'")
        self.emulation_is_active = False
        params = "rate 1000Gbit loss 0.0% delay 0ms duplicate 0% reorder 0% 0%"
        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc change dev {self.device} parent 1:2 netem {params}")).check_returncode()
        subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc change dev {self.virtual_device_in} root netem {params}")).check_returncode()


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
        global IFB_IS_INITIALIZED
        IFB_IS_INITIALIZED = True

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

    def _emulate_dynamic_parameters(self):
        """Emulate dynamic change of netem parameters"""
        next_change = timer()

        while self.emulation_is_active:
            for parameter_set in self.dynamic_parameters_setup.parameter_sets:
                if self.emulation_is_active:
                    if parameter_set.rul >= 0:
                        self.rul = parameter_set.rul
                    if parameter_set.rdl >= 0:
                        self.rdl = parameter_set.rdl
                    if parameter_set.dul >= 0:
                        self.dul = parameter_set.dul
                    if parameter_set.ddl >= 0:
                        self.ddl = parameter_set.ddl
                    self._update_incoming(self.dynamic_parameters_setup.verbose)
                    self._update_outgoing(self.dynamic_parameters_setup.verbose)

                    if parameter_set.timeframe >= 0:
                        timeframe_in_seconds = parameter_set.timeframe/1000.0
                        next_change += timeframe_in_seconds
                        if self.dynamic_parameters_setup.verbose:
                            log.debug(f"[{timer()}] Updated all dynamic connection parameters - next change will occur at {next_change} in {int((next_change-timer())*1000)} ms")
                        time.sleep(next_change-timer())
                    else:
                        return

    def _emulate_dynamically(self, emulate_t_init: bool = True, emulate_dynamic_parameters: bool = True):
        """Emulate the dynamic conditions of a cellular network"""
        if emulate_t_init:
            self._emulate_t_init()
        if emulate_dynamic_parameters:
            self._emulate_dynamic_parameters()


    def cleanup_ifb(self):
        """Removes the ifb module from kernel"""
        subprocess.run(shlex.split(f"{self.__CMD_MODPROBE} -r ifb"))
        log.debug("Removed ifb module from kernel")
        global IFB_IS_INITIALIZED
        IFB_IS_INITIALIZED = False

    def cleanup_actual_devices(self):
        """Removes tc rules from all actual devices"""
        for device in USED_DEVICES:
            log.debug(f"Removing tc rules for device: {device}")
            subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc del dev {device} root"))
            subprocess.run(shlex.split(f"{self.__CMD_TC} qdisc del dev {device} ingress"))
            USED_DEVICES.remove(device)

    def cleanup(self):
        """Removes ifb module and all tc rules for actual devices"""
        self.emulation_is_active = False
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


def reset_device_and_ifb(net_device: str):
    log.debug(f"Reset device: {net_device}")
    subprocess.run(shlex.split(f"{CMD_TC} qdisc del dev {net_device} root"), stderr=subprocess.PIPE)
    subprocess.run(shlex.split(f"{CMD_TC} qdisc del dev {net_device} ingress"), stderr=subprocess.PIPE)
    subprocess.run(shlex.split(f"{CMD_MODPROBE} -r ifb"))
    log.debug("Removed ifb module from kernel")
    global IFB_IS_INITIALIZED
    IFB_IS_INITIALIZED = False
