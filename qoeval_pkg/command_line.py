# SPDX-License-Identifier: LGPL-3.0-or-later
#
# Authors:  Lars Wischhof, <wischhof@ieee.org>
#
# License:  LGPL 3.0 - see LICENSE file for details
import argparse

from qoeval_pkg.configuration import QoEvalConfiguration
from qoeval_pkg.coordinator import Coordinator
from qoeval_pkg.parser.parser import load_parameter_file, is_correct_parameter_file


def main():
    print("QoEval Command Line Coordinator")

    parser = argparse.ArgumentParser()
    parser.add_argument('type', help='Specifies parameter stimuli type id, e.g. \"VS\"')
    parser.add_argument('table', help='Specifies parameter stimuli table id, e.g. \"A\"')
    parser.add_argument('entry', help='Specifies parameter stimuli enty id, e.g. \"1\" or ALL (default)',
                        nargs='?', default="ALL")
    parser.add_argument('--overwrite', help="Overwrite existing stimuli files", action='store_true')
    parser.add_argument('--skipgenerate', help="Skip generating stimuli files", action='store_true')
    parser.add_argument('--skippostprocessing', help="Skip postprocessing stimuli files", action='store_true')
    parser.add_argument('--parameterfile', dest='parameter_file', help='Path to parameter file',
                        action='store', nargs='?', default='', type=str)
    parser.add_argument('--check-params', dest='check_params',
                        help='Perform additional check of parameter-file before running the coordinator',
                        action='store_true')

    args = parser.parse_args()

    stimuli_type = args.type
    stimuli_table = args.table
    stimuli_entry = args.entry

    if stimuli_entry == "ALL":
        stimuli_entry_list = None
    else:
        stimuli_entry_list = [stimuli_entry]

    qoeval_config = QoEvalConfiguration()

    # modify qoeval default configuration according to supplied parameter values
    if args.parameter_file and len(args.parameter_file) > 0:
        qoeval_config.parameter_file.set(args.parameter_file)

    if args.check_params:
        load_parameter_file(qoeval_config.parameter_file.get())
        if not is_correct_parameter_file():
            raise RuntimeError(f"Check of parameter file {qoeval_config.parameter_file.get()} failed.")
        print(f"Checking parameter file {qoeval_config.parameter_file.get()}...   ok.")

    print(f"Starting to process type:{stimuli_type}; table: {stimuli_table}; entry:{stimuli_entry}")

    coordinator = Coordinator(qoeval_config)
    coordinator.start([stimuli_type], [stimuli_table], stimuli_entry_list, generate_stimuli=not args.skipgenerate,
                      postprocessing=not args.skippostprocessing, overwrite=args.overwrite)

    print("Done.")
