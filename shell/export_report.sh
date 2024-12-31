#!/bin/bash
#-----------------------------------------------------------------------
#   テスト結果のうち必要なもののみコピーまたはzip
#-----------------------------------------------------------------------

# Checking parameter
if [ $# -eq 2 ]; then
    SRC=$1
    DEST=$2
elif [ $# -eq 4 ]; then
    if [ $1 == -l ]; then
        LEVEL=$2
    else
        echo "Unlown option."
        exit 1
    fi
    SRC=$3
    DEST=$4
else
    echo "Copy or zip summarys in report directory."
    echo "  $0 [-l {summary|log}] [Source Directory] [Target Directory/zip]"
    exit 1
fi
EXT=`basename $DEST | sed 's/^.*\.\([^\.]*\)$/\1/'`

# ファイルコピー/ZIP
if [ "$EXT" == "zip" ]; then
    # 既存ファイルがあれば削除
    if [ -e $DEST ]; then
        rm -f $DEST
    fi
    # ZIP
    find $SRC -name "graphlist.html" -exec zip $DEST {} \;
    find $SRC -name "results.html" -exec zip $DEST {} \;
    find $SRC -name "results_dedupcomp.csv" -exec zip $DEST {} \;
    find $SRC -name "result_scenario.csv" -exec zip $DEST {} \;
    find $SRC -name "results.csv" -exec zip $DEST {} \;
    find $SRC -name "*.xlsx" -exec zip $DEST {} \;
    find $SRC -name "*.png" -exec zip $DEST {} \;
    if [ "$LEVEL" == "log" ]; then
        find $SRC -name "totals.html" -exec zip $DEST {} \;
        find $SRC -name "result.csv" -exec zip $DEST {} \;
        find $SRC -name "*sysstat*.log" -exec zip $DEST {} \;
        find $SRC -name "qos_statistics_latency_show.log" -exec zip $DEST {} \;
    fi
else
    # ファイルコピー
    echo "Searching/copying files..."
    find $SRC -name "graphlist.html" -exec cp --parent {} $DEST \;
    find $SRC -name "results.html" -exec cp --parent {} $DEST \;
    find $SRC -name "results_dedupcomp.csv" -exec cp --parent {} $DEST \;
    find $SRC -name "result_scenario.csv" -exec cp --parent {} $DEST \;
    find $SRC -name "results.csv" -exec cp --parent {} $DEST \;
    find $SRC -name "*.xlsx" -exec cp --parent {} $DEST \;
    find $SRC -name "*.png" -exec cp --parent {} $DEST \;
    if [ "$LEVEL" == "log" ]; then
        find $SRC -name "totals.html" -exec cp --parent {} $DEST \;
        find $SRC -name "result.csv" -exec cp --parent {} $DEST \;
        find $SRC -name "*sysstat*.log" -exec cp --parent {} $DEST \;
        find $SRC -name "qos_statistics_latency_show.log" -exec cp --parent {} $DEST \;
    fi
fi
