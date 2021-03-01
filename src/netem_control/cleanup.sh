#!/bin/sh
#
# script to cleanup all tc and modprobe devices

INTERFACE=$1

echo "Removing ingress qdisc for $INTERFACE"
tc qdisc del dev $INTERFACE ingress

echo "Removing root qdisc for $INTERFACE"
tc qdisc del dev $INTERFACE root

echo "Removing ifb0"
modprobe -r ifb

