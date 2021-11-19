# SPDX-License-Identifier: LGPL-3.0-or-later
#
# Authors:  Jan Andreas Krahl <krahl.jan@hm.edu>
#
# License:  LGPL 3.0 - see LICENSE file for details
from qoeval_pkg.configuration import *
from qoeval_pkg.coordinator import Coordinator


def main():
    """Loads the current GUI config and starts the coordinator with its options"""
    qoeval_config = QoEvalConfiguration()
    qoeval_config.read_from_file(qoeval_config.gui_current_config_file.get())
    coord = Coordinator(qoeval_config)

    if qoeval_config.coordinator_generate_stimuli.get():
        for entry in qoeval_config.gui_coordinator_stimuli.get():
            coord.start([entry["type_id"]], [entry["table_id"]], [entry["entry_id"]],
                        qoeval_config.coordinator_generate_stimuli,
                        False,
                        qoeval_config.coordinator_overwrite)

    if qoeval_config.coordinator_postprocessing.get():
        for entry in qoeval_config.gui_coordinator_stimuli.get():
            coord.start([entry["type_id"]], [entry["table_id"]], [entry["entry_id"]],
                        False,
                        qoeval_config.coordinator_postprocessing,
                        qoeval_config.coordinator_overwrite)


if __name__ == '__main__':
    main()
