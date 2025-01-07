#!/bin/bash
#-----------------------------------------------------------------------
#   VDBENCHの停止
#-----------------------------------------------------------------------

RETRY_CNT=5

# Kill vdbench
for CNT in `seq $RETRY_CNT -1 1`
do
  PID=`ps -e -o pid,cmd | grep Vdb.Vdbmain | grep -v grep | awk '{print $1}'`
  if [ "$PID" == "" ]; then
    break
  fi
  kill -TERM $PID
  sleep 5
done
