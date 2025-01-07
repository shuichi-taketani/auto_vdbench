#!/bin/bash
#---------------------------------------
#  Start to Get ONTAP Statistics
#---------------------------------------

# Parameters
source `dirname $0`/../autogen_conf/conf.sh

OUTPUT_DIR=$1
PERFSTAT=`which perfstat8 2> /dev/null`
TMPDIR=/var/tmp

# Complement parameters
if [ "$OUTPUT_DIR" = "" ]; then
    OUTPUT_DIR=`pwd`
fi

# sysstat -x
for NODE in $ONTAP_NODES; do
    ssh $ONTAP_ID@$ONTAP_CLUSTER "node run -node $NODE sysstat -c $STAT_DURATION -x 1" > $OUTPUT_DIR/${NODE}_sysstat-x.log &
done

# sysstat -M
for NODE in $ONTAP_NODES; do
    ssh $ONTAP_ID@$ONTAP_CLUSTER "node run -node $NODE \"priv set diag;sysstat -c $STAT_DURATION -M 1\"" > $OUTPUT_DIR/${NODE}_sysstat-M.log &
done

# qos statistics latency show
ssh $ONTAP_ID@$ONTAP_CLUSTER "qos statistics latency show -iterations $STAT_DURATION" > $OUTPUT_DIR/qos_statistics_latency_show.log &

# perfstat
if [ "$PERFSTAT" != "" ]; then
    cd $OUTPUT_DIR
    # SSH Public Keyによるログインがエラーになるため、パスワードによるログインに変更
    #$PERFSTAT $CDOT_CLUSTER -t $PERFSTAT_TIME -i $PERFSTAT_ITER --sshprivatekey-file=/root/.ssh/id_rsa --mode="c" &
    echo -e "\n\n$CDOT_ID\n$CDOT_PASSWD\n\n" > $TMPDIR/perfstat_passwd.tmp
    $PERFSTAT $ONTAP_CLUSTER -z -t $ONTAP_PERFSTAT_TIME -i $ONTAP_PERFSTAT_ITER --mode="c" < $TMPDIR/perfstat_passwd.tmp &
    sleep 30 # Waiting for accepting passwd before deleting
    rm -f $TMPDIR/perfstat_passwd.tmp
    cd -
fi

