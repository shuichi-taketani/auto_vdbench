#!/bin/sh
#---------------------------------------
# Stop getting ONTAP Statistics
#---------------------------------------

# Paramters
source `dirname $0`/../autogen_conf/conf.sh

# sysstat
kill -INT `ps aw | grep sysstat | awk '{ print $1 }'` > /dev/null 2>&1
sleep 1
kill `ps aw | grep sysstat | awk '{ print $1 }'` > /dev/null 2>&1

# qos latency show
kill -INT `ps aw | grep "qos latency show" | awk '{ print $1 }'` > /dev/null 2>&1
sleep 1
kill `ps aw | grep "qos latency show" | awk '{ print $1 }'` > /dev/null 2>&1

# perfstat
killall -SIGINT perfstat8 > /dev/null
sleep 10
killall perfstat8 > /dev/null
