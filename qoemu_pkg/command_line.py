from qoemu_pkg.coordinator import Coordinator

import argparse

def main():
    print("QoE Command Line Coordinator")

    parser = argparse.ArgumentParser()
    parser.add_argument('type', help='Specifies parameter stimuli type id, e.g. \"VS\"')
    parser.add_argument('table', help='Specifies parameter stimuli table id, e.g. \"A\"')
    parser.add_argument('entry', help='Specifies parameter stimuli enty id, e.g. \"1\" or ALL (default)',
                        nargs='?', default="ALL")
    parser.add_argument('--overwrite', help="Overwrite existing stimuli files", action='store_true')
    parser.add_argument('--skipgenerate', help="Skip generating stimuli files", action='store_true')
    parser.add_argument('--skippostprocessing', help="Skip postprocessing stimuli files", action='store_true')
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
    coordinator.start([stimuli_type], [stimuli_table], stimuli_entry_list, generate_stimuli=not args.skipgenerate,
                      postprocessing= not args.skippostprocessing, overwrite=args.overwrite)

    print("Done.")