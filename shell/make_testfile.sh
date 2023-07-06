#!/bin/sh
#-----------------------------------------------------------------------
#   テストファイルの作成
#-----------------------------------------------------------------------

source `dirname $0`/../autogen_conf/conf.sh

VDBENCH=`which vdbench 2> /dev/null`
TMPDIR="/var/tmp/vdbench_tmp"
WAIT_OTHER_SERVERS=10

# VDBENCH existance check
if [ "$VDBENCH" == "" ]; then
    echo "Can't find VDBENCH in path"
    exit 1
fi

# Delete existing test files
echo "Deleting existing test files"
`dirname $0`/exec_all.sh rm -f $TESTFILE_PATH > /dev/null

# Start creating test files
echo "Starting vdbench to create test files"
mkdir -p $TMPDIR
$VDBENCH -f $TESTFILE_VDBENCH_SCENARIO -o $TMPDIR > $TMPDIR/vdbench.log &

# Check filesize
FILESIZE=`expr $TESTFILE_SIZE_GB \* 1024 \* 1024 \* 1024`
SIZE=0
while [ $SIZE -lt $FILESIZE ]
do
    # Get filesize
    if [ -e $TESTFILE_PATH ];
    then
        SIZE=`stat -c %s $TESTFILE_PATH`
    else
        SIZE=0
    fi
    PERCENT=`expr $SIZE \* 100 / $FILESIZE`
    echo "Writing test file ($SIZE/$FILESIZE = $PERCENT%)"
    sleep 1
done

# Check filesize in other servers
SIZE=0
while [ $SIZE -lt $FILESIZE ]
do
    SIZE=`\`dirname $0\`/exec_all.sh stat -c %s $TESTFILE_PATH | grep -v "\----" | sort -n | head -1`
    PERCENT=`expr $SIZE \* 100 / $FILESIZE`
    echo "Waiting for other servers ($SIZE/$FILESIZE = $PERCENT%)"
    sleep $WAIT_OTHER_SERVERS
done

# Kill vdbench
while true
do
  PID=`ps -e -o pid,cmd | grep Vdb.Vdbmain | grep -v grep | awk '{print $1}'`
  if [ "$PID" == "" ]; then
    break
  fi
  kill -TERM $PID
  sleep 5
done

# Delete temporary directory
rm -rf $TMPDIR

echo "Complated."
