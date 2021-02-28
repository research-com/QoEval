#!/bin/sh
#
# script to setup all tc and modprobe devices

INTERFACE=$1

echo "Setting up ifb0"
modprobe ifb
ip link set dev ifb0 up

echo "Setting up ingress qdisc"
tc qdisc add dev $INTERFACE ingress

echo "Setting up redirect filter"
tc filter add dev $INTERFACE parent ffff: protocol all u32 match u32 0 0 flowid 1:1 action mirred egress redirect dev ifb0

echo "Setting up netem for $INTERFACE"
tc qdisc add dev $INTERFACE root handle 1: netem

echo "Setting up netem for ifb0"
tc qdisc add dev ifb0 root handle 1: netem

