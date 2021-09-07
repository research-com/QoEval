from qoemu_pkg.configuration import *
from qoemu_pkg.coordinator import Coordinator


CONFIG_FILE = "qoemu_gui.conf"

config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), CONFIG_FILE)

parser = configparser.ConfigParser()
parser.read(config_path)
config = QoEmuConfiguration(parser)

coord = Coordinator()

for entry in config.coordinator_stimuli.get():
    coord.start([entry["type_id"]], [entry["table_id"]], [entry["entry_id"]],
                config.coordinator_generate_stimuli,
                config.coordinator_postprocessing,
                config.coordinator_overwrite)
