from qoemu_pkg.coordinator import Coordinator

import argparse

def main():
    print("QoE Command Line Coordinator")

    parser = argparse.ArgumentParser()
    parser.add_argument('type', help='Specifies parameter stimuli type id, e.g. \"VS\"')
    parser.add_argument('table', help='Specifies parameter stimuli table id, e.g. \"A\"')
    parser.add_argument('entry', help='Specifies parameter stimuli enty id, e.g. \"1\" or ALL (default)',
                        nargs='?', default="ALL")
    args = parser.parse_args()

    stimuli_type = args.type
    stimuli_table = args.table
    stimuli_entry = args.entry

    print (f"Starting to process type:{stimuli_type}; table: {stimuli_table}; entry:{stimuli_entry}")

    if stimuli_entry == "ALL":
        stimuli_entry_list = []
    else:
        stimuli_entry_list = [stimuli_entry]

    coordinator = Coordinator()
    coordinator.start([stimuli_type], [stimuli_table], stimuli_entry_list, generate_stimuli=True, postprocessing=True)

    print("Done.")