#!/bin/bash
#-----------------------------------------------------------------------
#   全サーバに対しホスト名を設定
#-----------------------------------------------------------------------

source `dirname $0`/../autogen_conf/conf.sh

for SERVER in $SERVER_LIST
do
    echo ----- $SERVER --------------------------------------------------
    ssh root@$SERVER hostnamectl set-hostname $SERVER
done
