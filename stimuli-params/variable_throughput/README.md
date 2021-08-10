# Variable Throughput - Parameter Files

These parameter files can be used for emulating a realistic throughput
variation over time. Each line in the parameter file specifies a delay
after which the connection parameters are applied. The negative value
"-1" indicates is used to indicate that the respective connection parameter
should be unchanged. 

The connection parameters are applied in a loop, i.e. when the end of
the parameter file is reached but the connection is still active, 
the time-variant throughput variation continues at the first line
of the parameter file. 

## Motivation

The throughput variations within the parameter files are based on 
real network measurements for situations where a rebuffering phase
was observed while playing a video stream on a smartphone. The naming of 
the parameter files is based on the average throughput, e.g.
the `A_10000.csv` parameter file describes a time-variant downlink
where the overall average on the time-variant downlink is 10000 kbit/s. 

## Variants A to C

The directory includes different variants of the parameter files:
* Variant A: connection parameters are updated every second
* Variant B: connection parameters are updated every two seconds
* Variant C: connection parameters are updated every three seconds

## Acknowledgements

Parameter values have been provided by Robert Müllner, Telefonica.
