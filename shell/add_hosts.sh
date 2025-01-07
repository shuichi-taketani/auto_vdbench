#!/bin/bash
#-----------------------------------------------------------------------
#   全サーバに対し指定されたファイルにあるhostsエントリを追加
#-----------------------------------------------------------------------

# 引数チェック
if [ $# != 1 ]; then
    echo "$0 [hosts entry file]"
    echo "指定されたファイルにあるhostsエントリを全サーバの/etc/hostsに追加します。"
    exit 1
fi

# /etc/hostsへ追加
source `dirname $0`/../autogen_conf/conf.sh
for SERVER in $SERVER_LIST
do
    if [ $SERVER != `hostname` ];
    then
        echo ----- $SERVER --------------------------------------------------
        ssh root@$SERVER "cat >> /etc/hosts" < $1
    fi
done
