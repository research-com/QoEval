# QoEval Parameter Files
This directory contains Comma-Separated-Value (CSV) files specifying the
parameters for generating the stimuli sets.

## Sub Folder *trigger*
This folder contains the trigger images used to detect start and end of 
a stimulus. Depending on the mobile application type, a start and/or an end
trigger image are required. These can easily be created via the QoEval 
GUI: Simply view a recorded stimulus video and capture the start and end
images.

## Sub Folder *variable_rate*
This folder contains CSV files which specify time-varant QoS parameters.
These are only used for stimuli which enable the time-variant QoS feature.

## TODO
The file format of the CSV files and the corresponding parser need to be
refactored: The current file format is historically based on an automated
export from an Excel file and therefore hard to read. Since we do not use
Excel for specifying parameter files anymore, we should refactor the parameter
file to use a more self-explaining and simpler-to-parse format.