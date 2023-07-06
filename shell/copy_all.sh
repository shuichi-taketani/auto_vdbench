#!/bin/sh
#-----------------------------------------------------------------------
#   全サーバへファイルをコピー
#-----------------------------------------------------------------------
source `dirname $0`/../autogen_conf/conf.sh
for SERVER in $SERVER_LIST
do
    if [ $SERVER != `hostname` ];
    then
        echo ----- $SERVER --------------------------------------------------
        scp $1 root@$SERVER:$2
    fi
done
