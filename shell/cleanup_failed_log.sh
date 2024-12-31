#!/bin/bash
#-----------------------------------------------------------------------
#   失敗したテスト結果をディレクトリごと削除
#-----------------------------------------------------------------------

# Checking parameter
DRY_RUN=0
if [ $# -eq 1 ]; then
    DIR=$1
elif [ $# -eq 2 ]; then
    if [ $1 == --dry-run ]; then
        DRY_RUN=1
    else
        echo "Unlown option."
        exit 1
    fi
    DIR=$2
else
    echo "Search and clean up failed logs."
    echo "  $0 [--dry-run] [Target Directory]"
    exit 1
fi

# Search and delete failed logs
RESULT_LIST=`find $DIR -name result.csv`
for FILE in $RESULT_LIST
do
    RESULT=`grep -e "^,\+$" $FILE > /dev/null ; echo $?`
    if [ $RESULT -eq 0 ]; then
        DIR=`dirname $FILE`
        if [ $DRY_RUN -eq 0 ]; then
            echo "Deleting $DIR"
            #rm -rf $DIR
        else
            echo "$DIR will be deleted."
        fi
    fi
done
 
