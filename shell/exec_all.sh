#!/bin/bash
#-----------------------------------------------------------------------
#   全サーバで同一コマンドを実行
#-----------------------------------------------------------------------
source `dirname $0`/../autogen_conf/conf.sh
for SERVER in $SERVER_LIST
do
    echo ----- $SERVER --------------------------------------------------
    ssh root@$SERVER $@
done
