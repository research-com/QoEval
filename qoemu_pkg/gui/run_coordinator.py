from qoemu_pkg.configuration import *
from qoemu_pkg.coordinator import Coordinator


def main():
    """Loads the current GUI config and starts the coordinator with its options"""
    qoemu_config = QoEmuConfiguration()
    qoemu_config.read_from_file(qoemu_config.gui_current_config_file.get())
    coord = Coordinator(qoemu_config)

    if qoemu_config.coordinator_generate_stimuli.get():
        for entry in qoemu_config.gui_coordinator_stimuli.get():
            coord.start([entry["type_id"]], [entry["table_id"]], [entry["entry_id"]],
                        qoemu_config.coordinator_generate_stimuli,
                        False,
                        qoemu_config.coordinator_overwrite)

    if qoemu_config.coordinator_postprocessing.get():
        for entry in qoemu_config.gui_coordinator_stimuli.get():
            coord.start([entry["type_id"]], [entry["table_id"]], [entry["entry_id"]],
                        False,
                        qoemu_config.coordinator_postprocessing,
                        qoemu_config.coordinator_overwrite)


if __name__ == '__main__':
    main()
