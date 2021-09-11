from qoemu_pkg.configuration import *
from qoemu_pkg.coordinator import Coordinator
import qoemu_pkg.configuration


CONFIG_FILE = "qoemu_gui.conf"

config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), CONFIG_FILE)
print(config_path)

parser = configparser.ConfigParser()
parser.read(config_path)
config.configparser = parser


coord = Coordinator()

if config.coordinator_generate_stimuli.get():
    for entry in config.gui_coordinator_stimuli.get():
        coord.start([entry["type_id"]], [entry["table_id"]], [entry["entry_id"]],
                    config.coordinator_generate_stimuli,
                    False,
                    config.coordinator_overwrite)

if config.coordinator_postprocessing.get():
    for entry in config.gui_coordinator_stimuli.get():
        coord.start([entry["type_id"]], [entry["table_id"]], [entry["entry_id"]],
                    False,
                    config.coordinator_postprocessing,
                    config.coordinator_overwrite)

