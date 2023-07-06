#!/usr/bin/python
#---------------------------------------------------------------------
#   auto_vdbench - Automatic VDBENCH Script - Version.1.0.0
#                         Copyright(c) 2023 Shuichi Taketani (NetApp)
#
#   This software is released under the MIT license, see docs/LICENSE. 
#---------------------------------------------------------------------

#---- モジュール定義 --------------------------------------------------
# pip install requests, pandas, openpyxl, pymsteams, scipy, plotly, kaleido
import os
import sys
import shutil
import subprocess
import glob
import re
import pandas as pd
import numpy as np
import time
import string
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.chart import ScatterChart, Reference, Series
from argparse import ArgumentParser
import pymsteams
import requests
import json
from scipy import interpolate
import warnings

#---- 定数 -----------------------------------------------------------
# 設定ファイルディレクトリ名(スクリプトがあるディレクトリからの相対指定)
CONFIG_DIR_NAME = "conf"
# 設定ファイル名
CONFIG_FILE_NAME = "auto_vdbench.conf"
# 自動生成設定ファイルディレクトリ名
AUTOGEN_CONFIG_DIR_NAME = "autogen_conf"
# テンポラリディレクトリ
TEMP_DIR = "/var/tmp"
# チェックポイントファイル名(レジューム用)
CHECKPOINT_FILE = TEMP_DIR + "/auto_vdbench.resume"
# サスペンド要求ファイル名
SUSPEND_FILE = TEMP_DIR + "/auto_vdbench.suspend"
# PIDファイル名
PID_FILE = TEMP_DIR + "/auto_vdbench.pid"
# テンポラリファイル
TEMP_FILE = TEMP_DIR + "/auto_vdbench.tmp"
# コマンドラインオプション(デバッグ用)
# (None指定で本来のコマンドライン参照)
#DEBUG_CLI_ARGS = ['start', '-m', 'inc', '--debug-only', 'true', '--skip-creating-testfiles', 'true']
DEBUG_CLI_ARGS = None
# デバッグ実行時VDBENCH実行の代わりとなるWAIT
DEBUG_VDBENCH_WAIT = 3

#---- グローバル変数 --------------------------------------------------
# 設定ファイル・コマンドラインオプション
Config = {}
# Auto VDBENCHディレクトリ(スクリプトと同一)
AutoVDB_Home = ""
# 設定ファイルディレクトリ
Config_Dir = ""

#---------------------------------------------------------------------
#   メイン
#---------------------------------------------------------------------
def main() -> None:
    """
    Main routine

    Invoke other function by arguments
    """

    # バナー表示
    print("auto_vdbench Version 1.0.0 - Copyright(c) 2023 Shuichi Taketani (NetApp)\n", flush=True)
    # モードに併せて実行
    if Config['mode'] == "start":
        # 初期設定ファイルを作成
        if not Config['skip_creating_conffiles']:
            init_conffile()
        # シナリオ名のリストが空の場合はリストを作成
        if len(Config['scenario_list']) == 0:
            Config['scenario_list'], _ = create_scenario_name_and_definitions()
        # モードに応じて実行
        if Config['test_mode'] == 'auto':
            # 自動モードでテスト開始
            start_test_in_auto_mode()
        elif Config['test_mode'] == 'inc':
            # 増加モードでテスト開始
            start_test_in_incremental_mode()
        elif Config['test_mode'] == 'file':
            # ファイルモードでテスト開始
            if not Config['test_pattern_file']:
                print("Please specify a test pattern file with CSV format like --test-pattern-file <file>", file=sys.stderr, flush=True)
            else:
                start_test_in_file_mode()
    elif Config['mode'] == "stop":
        # テスト終了(中止)
        stop()
    elif Config['mode'] == "suspend":
        # テストを中断(再開できるよう保存)
        suspend()
    elif Config['mode'] == "resume":
        # テストを再開
        resume()
    elif Config['mode'] == "create-report":
        # レポートを作成
        create_report()
    elif Config['mode'] == "create-comparison-report":
        # 比較レポートを作成
        if len(Config['report_dir']) != len(Config['label']):
            print("The number of label and report_dir doesn't match.", file=sys.stderr, flush=True)
        else:
            create_comparison_report()
    elif Config['mode'] == "init":
        # 初期設定ファイル作成
        init_conffile()
        print("Auto-generating conf files are created.", flush=True)

#---------------------------------------------------------------------
#   増加モードでのテストを開始
#
# 概要:
#   指定された全パターンのテストを開始します。最大IOPSを計測後、設定
#   ファイルで指定されたIOPS(inc_iops_start)から指定された
#   IOPS(inc_iops_step)ごとに、最大IOPSを少し超えるところまで計測します。
# 引数:
#   なし
# 戻り値:
#   なし
#---------------------------------------------------------------------
def start_test_in_incremental_mode() -> None:
    """
    Start tests in incremental mode

    Start testd all patterns specified. After measuring the maximum IOPS, 
    measure from specified IOPS (inc_iops_start) to max IOPS with specified
    IOPS (inc_iops_step) in the configuration file.
    """
    # テスト開始/再開メッセージを送信
    if Config['mode'] == "start":
        send_to_teams(Config['teams_incoming_webhook'], "Test Start", "Tests are started.", [])
    else:
        send_to_teams(Config['teams_incoming_webhook'], "Test Resume", "Tests are resumed.", [])

    # 重複排除率でループ
    save_pid()
    resume_skip = Config['mode'] == "resume"
    testfile_skip_first = Config['skip_creating_testfiles_at_first'] == True
    for dedup in Config['dedup_ratio']:
        # 圧縮率でループ
        for comp in Config['compression_ratio']:
            # レジューム開始位置までスキップ
            if resume_skip and (Config['resume_dedup_ratio'] != dedup
                                 or Config['resume_compression_ratio'] != comp):
                continue
            # シナリオでループ
            print("==================================================")
            print("  Dedup: {}  Compression: {}".format(dedup, comp))
            print("==================================================")
            sys.stdout.flush()
            # 重複排除と圧縮の設定をファイルへ書き込み
            os.makedirs(Autogen_Config_Dir, exist_ok=True)
            make_file_from_template(Config_Dir + "dedup.template", Autogen_Config_Dir + "dedup",
                                    {"dedup": dedup, "comp": comp})
            # テストファイル作成
            if (not testfile_skip_first) and (Config['mode'] != "resume"):
                make_test_files()
            testfile_skip_first = False
            for scenario in Config['scenario_list']:
                # レジューム開始位置までスキップ
                if resume_skip:
                    if Config['resume_scenario'] == scenario:
                        resume_skip = False
                    continue

                results = pd.DataFrame()
                # レポートディレクトリ作成
                report_basedir = Config['report_dir'] + "/dedup{}_comp{}/{}".format(dedup, comp, scenario)
                if Config['scenario_test_result_merge_mode'] == 'rename':
                    makedir_with_rename(report_basedir)

                # シナリオテスト開始時のスクリプトを実行
                if Config['scenario_start_script']:
                    subprocess.run(Config['scenario_start_script'] + ' ' + report_basedir + ' ' +
                                   scenario, shell=True)

                # 最大性能を調べる
                result = run_test_with_retry(dedup, comp, scenario, 0, report_basedir)
                results = pd.concat([results, result], axis=0)
                max_iops = (int(result["iops"][0] / Config['inc_iops_step']) + 2) * Config['inc_iops_step']

                # IOPSを変化させながら調べる
                for iops in range(Config['inc_iops_start'], max_iops + 1, Config['inc_iops_step']):
                    result = run_test_with_retry(dedup, comp, scenario, iops, report_basedir)
                    results = pd.concat([results, result], axis=0)

                # シナリオごとの結果をファイルへ保存
                create_report_scenario(report_basedir + '/')
                send_to_teams(Config['teams_incoming_webhook'], scenario + " result",
                              "dedup: {}\r\ncomp: {}\r\n".format(dedup, comp),
                              [report_basedir + "/results.png", report_basedir + "/results.html"])

                # シナリオテスト終了時のスクリプトを実行
                if Config['scenario_end_script']:
                    subprocess.run(Config['scenario_end_script'] + ' ' + report_basedir + ' ' +
                                   scenario, shell=True)

                # レジューム用にチェックポイント作成
                save_checkpoint(dedup, comp, scenario, 0)
                if check_suspend():
                    print("Tests is suspended by user.", flush=True)
                    send_to_teams(Config['teams_incoming_webhook'], "Test Suspend", "Test was suspended by user. It can be resumed by resume command.", [])
                    return

    # テスト終了
    cleanup_checkpoint()
    create_report()
    cleanup_pid()
    print("All tests have been complated.", flush=True)
    send_to_teams(Config['teams_incoming_webhook'], "Test Complete", "All tests have been completed.", [])

#---------------------------------------------------------------------
#   自動モードのテストを開始
#
# 概要:
#   指定された全パターンのテストを開始します。IOPSの測定点はLatencyを元に
#   自動で決定します。
# 引数:
#   なし
# 戻り値:
#   なし
#---------------------------------------------------------------------
def start_test_in_auto_mode() -> None:
    """
    Start tests in auto mode
    
    Start tests all specified patterns; the IOPS measurement point is
    automatically determined based on latency.
    """
    # テスト開始/再開メッセージを送信
    if Config['mode'] == "start":
        send_to_teams(Config['teams_incoming_webhook'], "Test Start", "Tests are started.", [])
    else:
        send_to_teams(Config['teams_incoming_webhook'], "Test Resume", "Tests are resumed.", [])

    # 重複排除率でループ
    save_pid()
    resume_skip = Config['mode'] == "resume"
    testfile_skip_first = Config['skip_creating_testfiles_at_first'] == True
    for dedup in Config['dedup_ratio']:
        # 圧縮率でループ
        for comp in Config['compression_ratio']:
            # レジューム開始位置までスキップ
            if resume_skip and (Config['resume_dedup_ratio'] != dedup
                                 or Config['resume_compression_ratio'] != comp):
                continue
            # シナリオでループ
            print("==================================================")
            print("  Dedup: {}  Compression: {}".format(dedup, comp))
            print("==================================================")
            sys.stdout.flush()
            # 重複排除と圧縮の設定をファイルへ書き込み
            os.makedirs(Autogen_Config_Dir, exist_ok=True)
            make_file_from_template(Config_Dir + "/dedup.template", Autogen_Config_Dir + "/dedup",
                                    {"dedup": dedup, "comp": comp})
            # テストファイル作成
            if (not testfile_skip_first) and (Config['mode'] != "resume"):
                make_test_files()
            testfile_skip_first = False
            for scenario in Config['scenario_list']:
                # レジューム開始位置までスキップ
                if resume_skip:
                    if Config['resume_scenario'] == scenario:
                        resume_skip = False
                    continue
                
                results = pd.DataFrame()
                test_cnt = 0
                # レポートディレクトリ作成
                report_basedir = Config['report_dir'] + "/dedup{}_comp{}/{}".format(dedup, comp, scenario)
                if Config['scenario_test_result_merge_mode'] == 'rename':
                    makedir_with_rename(report_basedir)

                # シナリオテスト開始時のスクリプトを実行
                if Config['scenario_start_script']:
                    subprocess.run(Config['scenario_start_script'] + ' ' + scenario, shell=True)

                # 最大性能を調べる
                result = run_test_with_retry(dedup, comp, scenario, 0, report_basedir)
                if not result["iops"].values[0] > 0:
                    err = "Can't get maximum performance."
                    print("ERROR: " + err, file=sys.stderr, flush=True)
                    send_to_teams(Config['teams_incoming_webhook'], "Error", err, [])
                    sys.exit(1)
                results = pd.concat([results, result], axis=0)
                max_iops = round_iops(result["iops"][0])
                test_cnt += 1
                # 最大性能と丸めた同値を計測(最大性能ではレイテンシが大きくでるため)
                result = run_test_with_retry(dedup, comp, scenario, max_iops, report_basedir)
                results = pd.concat([results, result], axis=0)
                prev_resp_time = result['resp_time'].values[0]
                test_cnt += 1
                # 最大性能+5%を計測
                if Config['auto_additional_percent_to_max'] != 0:
                    iops = round_iops(max_iops * (1 + Config['auto_additional_percent_to_max'] / 100))
                    result = run_test_with_retry(dedup, comp, scenario, iops, report_basedir)
                    results = pd.concat([results, result], axis=0)
                    test_cnt += 1

                # IOPSの下限(レイテンシが十分小さくなるIOPS)を探す
                iops = max_iops
                while test_cnt < Config['auto_min_test_count']:
                    iops = round_iops(iops / 2)
                    if iops < Config['auto_min_iops']:
                        iops = Config['auto_min_iops']
                    # IOPSが既に計測済みであれば終了
                    if iops in results['target_iops']:
                        break
                    # テスト開始
                    result = run_test_with_retry(dedup, comp, scenario, iops, report_basedir)
                    results = pd.concat([results, result], axis=0)
                    test_cnt += 1
                    # 前回レイテンシと比較し、5%以下または増加であれば終了
                    diff_percent = (prev_resp_time - result['resp_time'].values[0]) / prev_resp_time * 100
                    if diff_percent > Config['auto_threshold_to_find_min_latency']:
                        prev_resp_time = result['resp_time'].values[0]
                    else:
                        break
                # エラーチェック
                if test_cnt >= Config['auto_min_test_count']:
                    err = "The lower range of IOPS could not be fully explored; increase auto_min_test_count or increase auto_threshold_to_find_min_latency."
                    print("INFO: " + err, file=sys.stderr, flush=True)
                    send_to_teams(Config['teams_incoming_webhook'], "Information", err, [])

                # IOPSのレンジ内でLatencyの差分が大きい部分を計測
                while test_cnt < Config['auto_max_test_count']:
                    # Latency差分の最も大きなIOPS範囲を特定
                    df = results.sort_values('iops')
                    df.reset_index(drop=True, inplace=True)
                    df['diff_resp_time'] = df['resp_time'].diff().abs()
                    df['diff_iops'] = df['iops'].diff()
                    to_iops = df.loc[df['diff_resp_time'].idxmax(), 'iops']
                    from_iops = df.loc[df['diff_resp_time'].idxmax()-1, 'iops']
                    iops = round_iops((to_iops - from_iops) / 2 + from_iops)
                    # 最小テスト回数を超えており、Latency差分が規定より小さければ終了
                    if test_cnt > Config['auto_min_test_count'] and df['diff_resp_time'].max() < Config['auto_latency_diff_thresold']:
                        break
                    # IOPSが既に計測済みであれば終了
                    if str(iops) in results['target_iops'].values:
                        break
                    # テスト実行
                    result = run_test_with_retry(dedup, comp, scenario, iops, report_basedir)
                    results = pd.concat([results, result], axis=0)
                    test_cnt += 1
                # エラーチェック
                if test_cnt >= Config['auto_max_test_count']:
                    err = "IOPS changes could not be fully explored; increase auto_max_test_count may provide more details on IOPS changes."
                    print("INFO: " + err, file=sys.stderr, flush=True)
                    send_to_teams(Config['teams_incoming_webhook'], "Information", err, [])

                # 最低テスト回数に満たない場合は、IOPSの差が大きい部分を計測
                while test_cnt < Config['auto_min_test_count']:
                    # IOPS差分が最も大きい範囲を特定
                    df = results.sort_values('iops')
                    df.reset_index(drop=True, inplace=True)
                    df['diff_iops'] = df['iops'].diff()
                    to_iops = df.loc[df['diff_iops'].idxmax(), 'iops']
                    from_iops = df.loc[df['diff_iops'].idxmax()-1, 'iops']
                    iops = round_iops((to_iops - from_iops) / 2 + from_iops)
                    # IOPSが既に計測済みであれば終了
                    if str(iops) in results['target_iops'].values:
                        break
                    # テスト実行
                    result = run_test_with_retry(dedup, comp, scenario, iops, report_basedir)
                    results = pd.concat([results, result], axis=0)
                    test_cnt += 1

                # シナリオごとの結果をファイルへ保存
                create_report_scenario(report_basedir + '/')
                send_to_teams(Config['teams_incoming_webhook'], scenario + " result",
                              "dedup: {}\r\ncomp: {}\r\n".format(dedup, comp),
                              [report_basedir + "/results.png", report_basedir + "/results.html"])

                # シナリオテスト終了時のスクリプトを実行
                if Config['scenario_end_script']:
                    subprocess.run(Config['scenario_end_script'] + ' ' + scenario, shell=True)

                # レジューム用にチェックポイント作成
                save_checkpoint(dedup, comp, scenario, 0)
                if check_suspend():
                    print("Tests is suspended by user.", flush=True)
                    send_to_teams(Config['teams_incoming_webhook'], "Test Suspend", "Test was suspended by user. It can be resumed by resume command.", [])
                    return

    # テスト終了
    cleanup_checkpoint()
    create_report()
    cleanup_pid()
    print("All tests have been complated.", flush=True)
    send_to_teams(Config['teams_incoming_webhook'], "Test Complete", "All tests have been completed.", [])

#---------------------------------------------------------------------
#   ファイルモードのテストを開始
#
# 概要:
#   CSVファイルで指定されたパターンのテストを開始します。
# 引数:
#   なし
# 戻り値:
#   なし
#---------------------------------------------------------------------
def start_test_in_file_mode() -> None:
    """
    Start test in file mode
    
    Start tests the pattern specified in the CSV file.
    """
    # テストパターンのCSVファイルを読み込み
    test_pattern = pd.read_csv(Config['test_pattern_file'], encoding='utf-8')

    # テスト開始/再開メッセージを送信
    if Config['mode'] == "start":
        send_to_teams(Config['teams_incoming_webhook'], "Test Start", "Tests are started.", [])
    else:
        send_to_teams(Config['teams_incoming_webhook'], "Test Resume", "Tests are resumed.", [])

    # テストパターンでループ
    save_pid()
    prev_dedup_ratio = 0
    prev_compression_ratio = 0
    resume_skip = Config['mode'] == "resume"
    testfile_skip_first = Config['skip_creating_testfiles_at_first'] == True
    for index, pattern in test_pattern.iterrows():
        # レジューム開始位置までスキップ
        if resume_skip:
            if (Config['resume_dedup_ratio'] == pattern['dedup_ratio']
                and Config['resume_compression_ratio'] == pattern['compression_ratio']
                and Config['resume_scenario'] == pattern['scenario']
                and Config['resume_iops'] == pattern['iops']):
                prev_dedup_ratio = Config['resume_dedup_ratio']
                prev_compression_ratio = Config['resume_compression_ratio']
                resume_skip = False
            continue

        # テストファイル作成
        if prev_dedup_ratio != pattern['dedup_ratio'] or prev_compression_ratio != pattern['compression_ratio']:
            if not testfile_skip_first:
                make_test_files()
            testfile_skip_first = False
            prev_dedup_ratio = pattern['dedup_ratio']
            prev_compression_ratio = pattern['compression_ratio']

        # テストの実行
        report_basedir = Config['report_dir'] + "/dedup{}_comp{}/{}".format(
            pattern['dedup_ratio'], pattern['compression_ratio'], pattern['scenario'])
        result = run_test_with_retry(pattern['dedup_ratio'], pattern['compression_ratio'],
                                     pattern['scenario'], pattern['iops'], report_basedir)

        # レジューム用にチェックポイント作成
        save_checkpoint(pattern['dedup_ratio'], pattern['compression_ratio'], pattern['scenario'], pattern['iops'])
        if check_suspend():
            print("Tests is suspended by user.", flush=True)
            send_to_teams(Config['teams_incoming_webhook'], "Test Suspend", "Test was suspended by user. It can be resumed by resume command.", [])
            break

    # テスト終了
    cleanup_checkpoint()
    cleanup_pid()
    print("All tests have been complated.", flush=True)
    send_to_teams(Config['teams_incoming_webhook'], "Test Complete", "All tests have been completed.", [])

#---------------------------------------------------------------------
#   テストの中止(再開不可能)
#
# 概要:
#   テストを中止します。
# 引数:
#   なし
# 戻り値:
#   なし
#---------------------------------------------------------------------
def stop() -> None:
    # PIDファイルの存在チェック
    if not os.path.isfile(PID_FILE):
        print("No PID file.", file=sys.stderr, flush=True)
        return
    # PIDファイルの読み込みとKill
    print("Stop auto_vdbench", flush=True)
    with open(PID_FILE, 'r') as f:
        pid = f.read()
    subprocess.run(['kill', pid], shell=False)
    # VDBENCHを停止
    subprocess.run(Config['stop_vdbench_script'], shell=True)
    # PIDとSuspendをクリア
    cleanup_checkpoint()
    cleanup_pid()

#---------------------------------------------------------------------
#   PIDの保存
#
# 概要:
#   テストを中止する際に使うPIDをファイルへ保存します。
# 引数:
#   なし
# 戻り値:
#   なし
#---------------------------------------------------------------------
def save_pid() -> None:
    """
    Save PID

    Save PID to stop tests.
    """
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

#---------------------------------------------------------------------
#   PIDの削除
#
# 概要:
#   PIDファイルを削除します。
# 引数:
#   なし
# 戻り値:
#   なし
#---------------------------------------------------------------------
def cleanup_pid() -> None:
    """
    Clean up PID

    Delete PID file.
    """
    if os.path.isfile(PID_FILE):
        os.remove(PID_FILE)

#---------------------------------------------------------------------
#   テストの中断(再開可能)
#
# 概要:
#   テストを中断するよう目印となるファイルを作成します。
# 引数:
#   なし
# 戻り値:
#   なし
#---------------------------------------------------------------------
def suspend() -> None:
    """
    Suspend tests (can be resumed)

    Create a file to mark the test to be suspended.
    """
    # サスペンドを要求するファイルを作成
    with open(SUSPEND_FILE, 'w') as f:
        f.write("Suspend")
    print("Suspend is resuested.", flush=True)

#---------------------------------------------------------------------
#   テストの再開
#
# 概要:
#   チェックポイントファイルを読み込み、テストを再開します。
# 引数:
#   なし
# 戻り値:
#   なし
#---------------------------------------------------------------------
def resume() -> None:
    """
    Resume tests

    Load the checkpoint file and resume tests.
    """

    # チェックポイントファイルの存在チェック
    if not os.path.isfile(CHECKPOINT_FILE):
        print("No checkpoint file.", file=sys.stderr, flush=True)
        return
    # チェックポイントファイル読み込み
    global Config
    with open(CHECKPOINT_FILE, 'r') as f:
        Config = json.load(f)
    Config['mode'] = "resume"
    # 中断時のテストルーチンに戻す
    if Config['test_mode'] == 'auto':
        # 自動モードでテスト再開
        start_test_in_auto_mode()
    elif Config['test_mode'] == 'inc':
        # 増加モードでテスト再開
        start_test_in_incremental_mode()
    elif Config['test_mode'] == 'file':
        # ファイルモードでテスト再開
        if not Config['test_pattern_file']:
            print("Please specify a test pattern file with --test-pattern-file", file=sys.stderr, flush=True)
        else:
            start_test_in_file_mode()

#---------------------------------------------------------------------
#   レポートの作成
#
# 概要:
#   既に終了したテスト結果(result.csv)から以下のようなグラフやCSV,Excelを作成する
#   - シナリオごと
#     - IOPSごとの結果を1つのファイルにまとめたCSV, Excel
#     - IOPSとLatencyのグラフ(1-4msのcutoffを含む)
#   - dedup/compごと
#     - 各シナリオのグラフを一覧表示するためのHTML
#   - すべて
#     - シナリオを1行とし、すべての結果をまとめたCSV, Excel
# 引数:
#   なし
# 戻り値:
#   なし
#---------------------------------------------------------------------
def create_report() -> None:
    """ Create report

    Create the following graphs, CSV and Excel from the already completed
    test results (result.csv)
    - Per scenario
      - CSV and Excel with all IOPS results
      - Graph with IOPS and latency including 1-4ms cutoff
    - Per dedup/comp
      - HTML file for listing graphs for each scenario
    - All
      - CSV and Excel with one row for each scenario and all result summarized
    """
    # 重複排除・圧縮ごとのディレクトリを処理
    results = pd.DataFrame()
    for dedup_dir in glob.glob(Config['report_dir'] + "/dedup[0-9]*_comp[0-9]*/"):
        results = pd.concat([results, create_report_dedupcomp(dedup_dir)])
    if len(results.index):
        results.to_csv(Config['report_dir'] + "/results_all.csv", index=False)
    # 重複排除・圧縮ディレクトリが直接指定された場合、これを処理
    dir = Config['report_dir']
    if not dir.endswith('/'):
        dir += '/'
    create_report_dedupcomp(dir)
    # シナリオディレクトリが直接指定された場合、これを処理
    create_report_scenario(dir)

#---------------------------------------------------------------------
#   重複排除・圧縮ごとのレポートの作成
#
# 概要:
#   既に終了したテスト結果(result.csv)から以下のようなグラフやCSV,Excelを作成する
#   - 各シナリオのグラフを一覧表示するためのHTML
# 引数:
#   dedup_dir  重複排除・圧縮のディレクトリ(/で終わること)
# 戻り値:
#   1行レポートをまとめたDataFrame
#---------------------------------------------------------------------
def create_report_dedupcomp(dedup_dir):
    """ Create report for dedup/comp

    Create the following graphs, CSV and Excel from the already completed
    test results (result.csv)
    - HTML for listing graphs for each scenario

    Parameters
    ----------
    scenario_dir: str
        Directory of dedup/comp (must end with /)

    Returns
    -------
    DataFrame
        DataFrame summarizing a one-line report 
    """
    results = None
    dedup_comp = re.findall(r'dedup([0-9]+)_comp([0-9]+)/$', dedup_dir)
    if dedup_comp:
        print("Processing: " + dedup_dir, flush=True)
        # シナリオディレクトリのリストアップ
        results = pd.DataFrame()
        for scenario_dir in glob.glob(dedup_dir + "*/"):
            results = pd.concat([results, create_report_scenario(scenario_dir)])
        # 結果をソートして保存
        results.insert(0, 'compression_ratio', dedup_comp[0][1])
        results.insert(0, 'dedup_ratio', dedup_comp[0][0])
        results.sort_values(['random_sequential', 'block_size_kb', 'read_ratio'], ascending=[True, True, False],inplace=True)
        results.to_csv(dedup_dir + "/result_dedupcomp.csv", index=False)
        # グラフを一覧表示するためのHTMLを作成
        create_graph_list(results, dedup_dir + '/graphlist.html', 'single')
    return results

#---------------------------------------------------------------------
#   シナリオごとのレポートの作成
#
# 概要:
#   既に終了したテスト結果(result.csv)から以下のようなグラフやCSV,Excelを作成する
#   - IOPSごとの結果を1つのファイルにまとめたCSV, Excel
#   - IOPSとLatencyのグラフ(1-4msのcutoffを含む)
#   - シナリオの結果を1行としたCSV(result_scenario.csv)
# 引数:
#   scenario_dir  シナリオのディレクトリ(/で終わること)
# 戻り値:
#   result_scenario.csvと同じ内容のDataFrame
#---------------------------------------------------------------------
def create_report_scenario(scenario_dir: str) -> pd.DataFrame:
    """
    Create report for scenario

    Create the following graphs, CSV and Excel from the already completed
    test results (result.csv)
    - CSV and Excel with all IOPS results
    - Graph with IOPS and latency including 1-4ms cutoff
    - 1 row summary with CSV (result_scenario.csv)

    Parameters
    ----------
    scenario_dir: str
        Directory of scenario (must end with /)

    Returns
    -------
    DataFrame
        Same contents with result_scenaario.csv
    """
    results = pd.DataFrame(columns=['target_iops','timestamp'])
    result_scenario = None
    scenario_param = re.findall(r'((rand|seq)-bs([0-9]+)k-read([0-9]+))/$', scenario_dir)
    if scenario_param:
        scenario_param = scenario_param[0]
        print("Creating report: " + scenario_param[0], flush=True)
        # IOPSディレクトリをリストアップして結果を読み込み
        for iops_dir in glob.glob(scenario_dir + "/" + scenario_param[0] + "-iops*/"):
            iops_param = re.findall(scenario_param[0] + r'-iops([0-9]+|max)_([0-9]+\-[0-9]+)/$', iops_dir)
            if iops_param:
                iops_param = iops_param[0]
                result = load_csv_report(iops_dir)
                if result is not None:
                    result['target_iops'] = iops_param[0]
                    result['timestamp'] = iops_param[1]
                    results = pd.concat([results, result], axis=0)
        # Indexを振り直す
        results.reset_index(drop=True, inplace=True)
        # IOPSがNaNのものを削除
        results.dropna(subset=['iops'], inplace=True)
        # IOPSがmaxになっているものはLatencyが飛び抜けて大きい傾向があるため削除
        results = results[results['target_iops'] != 'max']
        # IOPSが重複している場合、新しいものを残す
        results = results.sort_values('timestamp', ascending=True).drop_duplicates('target_iops', keep='last')
        # レポートを保存
        results.to_csv(scenario_dir + "/results.csv", index=False)
        make_iops_latency_excel(scenario_param[0], results, scenario_dir + "/results.xlsx")
        cutoff = plot_iops_latency(scenario_param[0], [results], scenario_dir + "/results.png", scenario_dir + "/results.html")[0]
        # 1行レポートの作成
        result_scenario = {
            'scenario_name': scenario_param[0],
            'random_sequential': scenario_param[1],
            'block_size_kb': int(scenario_param[2]),
            'read_ratio': int(scenario_param[3])
        }
        result_scenario.update({"{}ms_cutoff".format(key): value for key, value in zip(Config['cutoff_latency'], cutoff)})
        # 最大IOPSとその時のLatencyを追加
        result_scenario['max_iops'] = results['iops'].max()
        result_scenario['latency_at_max_iops'] = results.loc[results['iops'].idxmax(), 'resp_time']
        # 最大Latencyとその時のIOPSを追加
        result_scenario['max_latency'] = results['resp_time'].max()
        result_scenario['iops_at_max_latency'] = results.loc[results['resp_time'].idxmax(), 'iops']
        # 最大IOPS時の結果を連結
        result_scenario = pd.DataFrame([result_scenario])
        result_max = results[results['iops'] == results['iops'].max()].head(1)
        result_max.index = result_scenario.index
        result_scenario = pd.concat([result_scenario, result_max], axis=1)
        # 1行レポートをCSVとして保存
        result_scenario.to_csv(scenario_dir + "/result_scenario.csv", index=False)
    return result_scenario

#---------------------------------------------------------------------
#   比較レポートの作成
#
# 概要:
#   複数のディレクトリにある集計済みテスト結果(results.csv)からシナリオごとに
#   IOPS-Latencyのグラフを作成する
# 引数:
#   なし
# 戻り値:
#   なし
#---------------------------------------------------------------------
def create_comparison_report() -> None:
    """
    Create comparison report

    Create IOPS-Latency graphs for each scenario from aggregated test
    results (results.csv) in multiple directories.
    """
    # 重複排除・圧縮ごとのディレクトリを処理
    for dedup_dir in glob.glob(Config['report_dir'][0] + "/dedup[0-9]*_comp[0-9]*/"):
        dedup_comp = re.findall(r'(dedup([0-9]+)_comp([0-9]+))/$', dedup_dir)
        if dedup_comp:
            dedup_comp = dedup_comp[0]
            # ディレクトリ存在チェック
            dir_exists = True
            for dir in Config['report_dir']:
                if not os.path.isdir(dir + '/' + dedup_comp[0]):
                    dir_exists = False
            # 重複排除・圧縮ごとの比較レポートの作成
            if dir_exists:
                dirs = [ s + '/' + dedup_comp[0] + '/' for s in Config['report_dir']]
                print("Processing: " + dirs[0], flush=True)
                create_comparison_report_dedupcomp(dirs, Config['output_dir'] + '/' + dedup_comp[0])
    # 重複排除・圧縮ディレクトリが直接指定された場合の処理
    dirs = [s + '/' if not s.endswith('/') else s for s in Config['report_dir']]
    create_comparison_report_dedupcomp(dirs, Config['output_dir'])

#---------------------------------------------------------------------
#   重複排除・圧縮ごとの比較レポートの作成
#
# 概要:
#   複数のディレクトリにある集計済みテスト結果(results.csv)からシナリオごとに
#   IOPS-Latencyのグラフを作成する
# 引数:
#   dedup_dirs  シナリオディレクトリがあるディレクトリのリスト(/で終わること)
#   output_dir  出力ディレクトリ
#   なし
# 戻り値:
#   なし
#---------------------------------------------------------------------
def create_comparison_report_dedupcomp(dedup_dirs: list, output_dir: str) -> None:
    """
    Create comparison report for dedup

    Create IOPS-Latency graphs for each scenario from aggregated test
    results (results.csv) in multiple directories.

    Parameters
    ----------
    dedup_dirs: list
        List of directories with scenario directories (must end with /)
    output_dir: str
        Output directory
    """
    # シナリオディレクトリのリストアップ
    scenario_list = pd.DataFrame(columns=[])
    for scenario_dir in glob.glob(dedup_dirs[0] + "*/"):
        scenario_param = re.findall(r'((rand|seq)-bs([0-9]+)k-read([0-9]+))/$', scenario_dir)
        if scenario_param:
            scenario_param = scenario_param[0]
            # 他の結果にも当該シナリオの結果があるかチェック
            file_exists = True
            for dir in dedup_dirs:
                if not os.path.isfile(dir + scenario_param[0] + '/results.csv'):
                    file_exists = False
            # シナリオごとの比較レポート作成
            if file_exists:
                scenario_dirs = [s + scenario_param[0] for s in dedup_dirs]
                create_comparison_report_scenario(scenario_param[0], scenario_dirs, 
                                                  output_dir + '/' + scenario_param[0])
                # 一覧表示用にシナリオ情報を記録
                scenario_list = pd.concat([scenario_list, pd.DataFrame({
                    'scenario_name': [scenario_param[0]], 'random_sequential': [scenario_param[1]],
                    'block_size_kb': [int(scenario_param[2])], 'read_ratio': [int(scenario_param[3])]})])
    # グラフを一覧表示するためのHTMLを作成
    create_graph_list(scenario_list, output_dir + '/graphlist.html', 'comparison')

#---------------------------------------------------------------------
#   シナリオごとの比較レポートの作成
#
# 概要:
#   複数のディレクトリにある集計済みテスト結果(results.csv)から1つの
#   IOPS-Latencyのグラフを作成する
# 引数:
#   scenario_name  シナリオ名
#   scenario_dir   シナリオのディレクトリのリスト
#   output_dir     出力先のディレクトリ
# 戻り値:
#   なし
#---------------------------------------------------------------------
def create_comparison_report_scenario(scenario_name: str, scenario_dir: list, output_dir: str) -> None:
    """ Create comparison report for scenario

    Create a single IOPS-Latency graph from aggregated test results
    (results.csv) in multiple directories

    Parameters
    ----------
    scenario_name: str
        Scenario name
    scenario_dir: list of str
        List of directory of scenario
    output_dir: str
        Output directory
    """
    # 処理中のシナリオ名を表示
    print("Creating comparison report: " + scenario_name)
    # CSVを読み込み
    results = []
    for dir in scenario_dir:
        result = pd.read_csv(dir + '/results.csv', encoding='utf-8')
        results.append(result)
    # 出力ディレクトリ作成
    os.makedirs(output_dir, exist_ok=True)
    # グラフ作成
    plot_iops_latency(scenario_name, results, output_dir + "/results.png", output_dir + "/results.html")

#---------------------------------------------------------------------
#   グラフリストファイルの作成
#
# 概要:
#   グラフを一覧表示するためのHTMLファイルを作成します。
# 引数:
#   scenario_list  シナリオ名、random/sequential, blocksize, read ratioを
#                  まとめたDataFrame
#   htmlfile       出力するHTMLファイル名
#   graphtype      グラフタイプ('single'で単一グラフ、'comparison'で比較後ラフ)
# 戻り値:
#   なし
#---------------------------------------------------------------------
def create_graph_list(scenario_list: pd.DataFrame, htmlfile: str, graphtype: str) -> None:
    """
    Creating a graph list file

    Create an HTML file to list the graphs.

    Parameters
    ----------
    scenario_list: DataFrame
        DataFrame including scenario name, random/sequential, block size, read ratio
    htmlfile: str
        Output HTML filename
    graphtype: str
        Type of graphs ('single' or 'comparison')
    """
    if len(scenario_list.index):
        # グラフをソート
        scenarios = scenario_list.sort_values(['random_sequential', 'block_size_kb', 'read_ratio'], ascending=[True, True, False])
        with open(htmlfile, 'w') as f:
            # ヘッダ
            f.write("<html>\n")
            if Config['graph_title']:
                f.write("  <head><title>{} - Graph List</title></head>\n".format(Config['graph_title']))
            else:
                f.write("  <head><title>Graph List</title></head>\n")
            f.write("<body>\n")
            if Config['graph_title']:
                f.write("  <div style='padding-left: 10px;'><h2>{}</h2></div>\n".format(Config['graph_title']))
            f.write("  <table border='0'>\n")
            # 表形式で並べる
            prev_rs = ""
            prev_bs = 0
            for index, row in scenarios.iterrows():
                if prev_rs != row['random_sequential'] or prev_bs != row['block_size_kb']:
                    f.write("  <tr>\n")
                    prev_rs = row['random_sequential']
                    prev_bs = row['block_size_kb']
                f.write("    <td align='center'>")
                f.write("        <iframe src='{}/results.html' width='700' height='500' frameborder='0'></iframe><br>\n".format(row['scenario_name']))
                f.write("        <a href='{}/results.html' target='_blank'>Open in new window</a><br>\n".format(row['scenario_name']))
                if graphtype == 'single':
                    f.write("        <a href='{}/results.xlsx'>Download Excel</a><br>\n".format(row['scenario_name']))
                    f.write("        <a href='{}/results.csv'>Download CSV</a>\n".format(row['scenario_name']))
            # フッタ
            f.write("  </table>\n")
            f.write("</body></html>\n")

#---------------------------------------------------------------------
#   設定ファイルの読み込み
#
# 概要:
#   設定ファイルを読み込み、DICT型として返します。
#   設定ファイルは # によるコメントが使用可能です。
# 引数:
#   configfile  設定ファイル名
# 戻り値:
#   設定値のDICT
#---------------------------------------------------------------------
def load_config(configfile: str) -> dict:
    """
    Load configuration file

    Load a configuration file and returns it as type DICT.
    Configuration file can be commented with #.

    Parameters
    ----------
    configfile: str
        Configuration filename
    
    Returns
    -------
    Dict
        Dict of configurations
    """
    # ファイルを読み込み
    with open(configfile, 'r', encoding='utf-8') as f:
        text = f.read()
    # コメントを削除
    text = re.sub(r'#.*', '', text)
    # 設定をJsonとしてパース
    config = json.loads(text, strict=False)
    # AutoVDB_Homeをテンプレートとして置き換え
    for key in config:
        if type(config[key]) is str:
            template = string.Template(config[key])
            config[key] = template.safe_substitute({'AutoVDB_Home': AutoVDB_Home})
    return config

#---------------------------------------------------------------------
#   コマンドラインオプションの取得
#
# 概要:
#   コマンドラインオプションを取得し、DICT型として返します
# 引数:
#   なし
# 戻り値:
#   引数のDICT
#---------------------------------------------------------------------
def get_args() -> dict:
    """
    Get command line options

    Get command line options and return them as DICT type

    Returns
    -------
    dict
        dict of arguments
    """
    parser = ArgumentParser(
        description='Conduct storage performance tests and make reports and graphs with VDBENCH'
    )
    subparsers = parser.add_subparsers(dest='mode')

    # initコマンドオプション
    parser_init = subparsers.add_parser('init', help='generate paramter files from config file for helper scripts')
    # startコマンドオプション
    parser_start = subparsers.add_parser('start', help='start tests')
    parser_start.add_argument('-m', '--test-mode', choices=['auto', 'inc', 'file'], default='auto',
                            help='auto: automatically determines the IOPS measurement points, \
                            inc: increments IOPS in specified steps from min IOPS to max IOPS, \
                            file: perform tests in the specified file')
    parser_start.add_argument('-d', '--dedup-ratio', type=int, nargs='+', default=Config['dedup_ratio'],
                            help='dedup ratios (auto and inc mode only)')
    parser_start.add_argument('-c', '--compression-ratio', type=int, nargs='+', default=Config['compression_ratio'],
                            help='compression ratios (auto and inc mode only)')
    parser_start.add_argument('-f', '--test-pattern-file',
                            help='test pattern file with CSV format (file mode only)', metavar='CSVFILE')
    parser_start.add_argument('-r', '--report-dir', default=Config['report_dir'],
                            help='directory to output reports')
    parser_start.add_argument('--skip-creating-testfiles', type=bool, default=False,
                            help='skip creating test files', metavar='True/False')
    parser_start.add_argument('--skip-creating-testfiles-at-first', type=bool, default=False,
                            help='skip creating test files at first', metavar='True/False')
    parser_start.add_argument('--skip-creating-conffiles', type=bool, default=False,
                            help='skip creating auto genegrating conf files', metavar='True/False')
    parser_start.add_argument('--graph-title',
                           help='title of graph list (e.g. A400 NFS Perf Test)')
    parser_start.add_argument('--debug-only', type=bool, default=False,
                            help='skip creating test files and tests', metavar='True/False')
    # stopコマンドオプション
    parser_stop = subparsers.add_parser('stop', help='abort tests')
    # suspendコマンドオプション
    parser_suspend = subparsers.add_parser('suspend', help='save checkpoint and exit')
    # resumeコマンドオプション
    parser_resume = subparsers.add_parser('resume', help='resume test from saved checkpoint')
    # create-reportコマンドオプション
    parser_create_report = subparsers.add_parser('create-report', help='creating report files from results')
    parser_create_report.add_argument('-r', '--report-dir', default=Config['report_dir'],
                            help='directory to load results and save reports')
    parser_create_report.add_argument('--graph-title',
                            help='title of graph list (e.g. A400 NFS Perf Test)')
    # create-comparison-reportコマンドオプション
    parser_create_comparison_report = subparsers.add_parser('create-comparison-report',
                                        help='creating comparison report from multiple results')
    parser_create_comparison_report.add_argument('-r', '--report-dir', nargs='+',
                                    help='directory to load results')
    parser_create_comparison_report.add_argument('-l', '--label', nargs='+', required=True,
                                    help='label for each results (e.g. A400, C400)')
    parser_create_comparison_report.add_argument('-c', '--color', nargs='+', default=Config['graph_default_colors'],
                                    help='Color in graph for each results (e.g. blue, red)')
    parser_create_comparison_report.add_argument('-o', '--output-dir', required=True,
                                    help='directory to save report')
    parser_create_comparison_report.add_argument('--graph-title',
                                    help='title of graph list (e.g. A400 NFS Perf Test)')

    args = vars(parser.parse_args(DEBUG_CLI_ARGS))
    return args

#---------------------------------------------------------------------
#   チェックポイントをファイルに保存
#
# 概要:
#   resumeで再開できるよう、チェックポイントをファイルへ保存します。
# 引数:
#   dedup     完了した重複排除率
#   comp      完了した圧縮率
#   scenario  完了したシナリオ
#   iops      完了したIOPS
# 戻り値:
#   なし
#---------------------------------------------------------------------
def save_checkpoint(dedup, comp, scenario, iops) -> None:
    """
    Save a checkpoint to file

    Save a checkpoint to a file so they can be resumed with resume.

    Parameters
    ----------
    dedup: float or str
        Completed dedup ratio
    comp: float or str
        Completed compression ratio
    scenario: str
        Completed scenario
    iops: int or float
        Completed IOPS
    """
    Config['resume_dedup_ratio'] = dedup
    Config['resume_compression_ratio'] = comp
    Config['resume_scenario'] = scenario
    Config['resume_iops'] = iops
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(Config, f, indent=4)

#---------------------------------------------------------------------
#   チェックポイントをクリア
#
# 概要:
#   チェックポイントをクリアします。
# 引数:
#   なし
# 戻り値:
#   なし
#---------------------------------------------------------------------
def cleanup_checkpoint() -> None:
    """
    Cleanup checkpoint
    """
    if os.path.isfile(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

#---------------------------------------------------------------------
#   サスペンド要求のチェック
#
# 概要:
#   サスペンド要求のファイルがあるか確認し、ある場合はファイルを削除した上で
#   Trueを返す。
# 引数:
#   なし
# 戻り値:
#   True   サスペンド要求あり
#   False  サスペンド要求なし
#---------------------------------------------------------------------
def check_suspend() -> None:
    """
    Check suspend request

    Checks to see if there is a file for the suspend request, and if so,
    returns True after deleting the file.

    Returns
    -------
    Bool
        True   Suspend request exists
        False  No suspend request
    """
    if os.path.isfile(SUSPEND_FILE):
        os.remove(SUSPEND_FILE)
        return True
    else:
        return False

#---------------------------------------------------------------------
#   設定ファイルの初期化
#
# 概要:
#   auto_vdbench.confに設定された内容をもとにVDBENCHの設定ファイルを
#   作成します。
# 引数:
#   なし
# 戻り値:
#   なし
#---------------------------------------------------------------------
def init_conffile() -> None:
    os.makedirs(Autogen_Config_Dir, exist_ok=True)
    # Host Definitionsの作成
    shutil.copy(Config_Dir + 'hosts.template', Autogen_Config_Dir + 'hosts')
    with open(Autogen_Config_Dir + 'hosts', 'a') as f:
        for i, str in enumerate(Config['server_list']):
            f.write('hd=hd{},system={},user=root\n'.format(i+1, str))
    # Initilization & Finalizationの作成
    shutil.copy(Config_Dir + 'init.template', Autogen_Config_Dir + 'init')
    if Config['storage_type'].lower() == 'netapp_ontap':
        # NetApp ONTAPの場合
        with open(Autogen_Config_Dir + 'init', 'a') as f:
            f.write('* Initialization\n')
            f.write('startcmd="{}/shell/ontapstats-start.sh $OUTPUT_DIR"\n\n'.format(AutoVDB_Home))
            f.write('* Finalization\n')
            f.write('endcmd="{}/shell/ontapstats-stop.sh"\n\n'.format(AutoVDB_Home))
    # Run Defaultsの作成
    make_file_from_template(Config_Dir + '/run_defaults.template',
                            Autogen_Config_Dir + '/run_defaults', 
                            {'warmup': Config['test_warmup'], 'elapsed': Config['test_duration'],
                             'threads': Config['server_threads']})
    # Storage Definitionsの作成
    make_file_from_template(Config_Dir + '/storages.template',
                            Autogen_Config_Dir + '/storages', 
                            {'size': Config['testfile_size']})
    with open(Autogen_Config_Dir + '/storages', 'a') as f:
        for i in range(1, len(Config['server_list'])+1):
            f.write('sd=sd{0}-1,host=hd{0},lun={1}/file1\n'.format(i, Config['testfile_dir']))
    # Workload Definitionsの作成
    shutil.copy(Config_Dir + 'workloads.template', Autogen_Config_Dir + 'workloads')
    with open(Autogen_Config_Dir + 'workloads', 'a') as f:
        scenario_name, line = create_scenario_name_and_definitions()
        f.write(line)
    # シェルスクリプト用設定ファイルの作成
    with open(Autogen_Config_Dir + 'conf.sh', 'w') as f:
        f.write('SERVER_LIST="' + " ".join(Config['server_list']) + '"\n')
        f.write('TESTFILE_PATH="{}/file1"\n'.format(Config['testfile_dir']))
        f.write('TESTFILE_SIZE_GB={}\n'.format(Config['testfile_size']))
        f.write('TESTFILE_VDBENCH_SCENARIO="{}/scenario-init"\n'.format(Autogen_Config_Dir))
        f.write('ONTAP_CLUSTER="{}"\n'.format(Config['ontap_cluster_name']))
        f.write('ONTAP_ID="{}"\n'.format(Config['ontap_id']))
        f.write('ONTAP_PASSWD="{}"\n'.format(Config['ontap_passwd']))
        f.write('ONTAP_NODES="' + " ".join(Config['ontap_node_names']) + '"\n')
        f.write('STAT_DURATION={}\n'.format(Config['test_duration'] + Config['test_warmup']))
        # Perfstatの間隔と回数を計算
        f.write('ONTAP_PERFSTAT_TIME={}\n'.format(Config['ontap_perfstat_interval']))
        n = Config['ontap_perfstat_interval'] if Config['ontap_perfstat_interval'] > 3 else 3
        n = int(Config['test_duration'] / 60 / n)
        n = n if n > 1 else 1
        f.write('ONTAP_PERFSTAT_ITER={}\n'.format(n))
    # テストファイル作成用Storage Definitionsの作成
    make_file_from_template(Config_Dir + '/scenario-init.template',
                            Autogen_Config_Dir + '/scenario-init', 
                            {'scenario': "seq-bs{}k-read0".format(max(Config['sequential_blocksize_list'])),
                             'AutoVDB_Home': AutoVDB_Home})

#---------------------------------------------------------------------
#   シナリオ名リストの作成
#
# 概要:
#   設定ファイルの内容をもとにシナリオ名とWorkload Definitionsの内容を
#   作成します
# 引数:
#   なし
# 戻り値:
#   シナリオ名のリスト
#   Storage Definitionの内容
#---------------------------------------------------------------------
def create_scenario_name_and_definitions() -> list:
    """
    Create scenario name list

    Create the scenario names and workload definitions based on the configuration file

    Returns
    -------
    List of scenario name
    Content of storage definitions
    """
    scenario_name = []
    line = ""
    # ランダムアクセスの定義を作成
    for blocksize in Config['random_blocksize_list']:
        line += "* random {}k\n".format(blocksize)
        for readratio in Config['read_ratio_list']:
            name = "rand-bs{}k-read{}".format(blocksize, readratio)
            line += "wd={},sd=*,seekpct=100,xfersize={}k,rdpct={}\n".format(name, blocksize, readratio)
            scenario_name.append(name)
        line += '\n'
    # シーケンシャルアクセスの定義を作成
    for blocksize in Config['sequential_blocksize_list']:
        line += "* sequential {}k\n".format(blocksize)
        for readratio in Config['read_ratio_list']:
            name = "seq-bs{}k-read{}".format(blocksize, readratio)
            line += "wd={},sd=*,seekpct=.0,xfersize={}k,rdpct={}\n".format(name, blocksize, readratio)
            scenario_name.append(name)
        line += '\n'
    return scenario_name, line

#---------------------------------------------------------------------
#   テストファイルを作成
#
# 概要:
#   スクリプトを呼び出すことでテストファイルを作成します。
# 引数:
#   なし
# 戻り値:
#   なし
#---------------------------------------------------------------------
def make_test_files() -> None:
    """
    Make test file

    Create a test file by calling the helper script.
    """
    if (not Config['debug_only']) and (not Config['skip_creating_testfiles']):
        subprocess.run(Config['make_testfile_script'], shell=True)
        time.sleep(Config['cooldown_wait'])
    else:
        print("Skip test file creation.", flush=True)

#---------------------------------------------------------------------
#   テストを実行(リトライつき)
#
# 概要:
#   vdbenchを実行し、テストを行います。テストが失敗した場合は、MAX_RETRYに
#   定義された回数までリトライを行います。
# 引数:
#   dedup_ratio        重複排除率
#   compression_ratio  圧縮率
#   scenario           シナリオ名(例: rand-bs4k-read100)
#   iops               IOPS(0でmax)
#   report_basedir     レポートを保存するディレクトリ(ex. dedup1_comp1/
#                      rand-bs4k-read100)
# 戻り値:
#   テスト結果のDataFrame
#---------------------------------------------------------------------
def run_test_with_retry(dedup_ratio, compression_ratio, scenario, iops, report_basedir):
    """
    Run test with retry

    Run vdbench and perform the test. If the test fails, retry up to the
    number of times defined in MAX_RETRY.

    Parameters
    ----------
    dedup_ratio: float
        Deduplication ratio
    compression_ratio: float
        Compression ratio
    scenario: str
        Scenario name (ex. rand-bs4k-read100)
    iops: int
        IOPS (0 means max)
    report_basedir: str
        Directory to save report (ex. dedup1_comp1/rand-bs4k-read100)

    Returns
    -------
    DataFrame
        Results of test
    """
    # テスト実行
    if iops == 0:
        striops = "max"
    else:
        striops = str(iops)
    # テスト実行
    retry = Config['max_retry']
    while retry > 0:
        print("----------------------------------------")
        print("  Dedup: {}  Compression: {}".format(dedup_ratio, compression_ratio))
        print("  Scenario: {} IOPS: {}".format(scenario, striops))
        print("----------------------------------------")
        sys.stdout.flush()
        # テスト実行
        result = run_test(scenario, iops, report_basedir)
        # エラーチェック
        if result["iops"].values[0] > 0:
            break
        retry = retry -1
    # リトライエラーチェック
    if retry == 0:
        err = "Max retry exceeded in " + scenario + "-iops" + striops
        print("WARNING: " + err, file=sys.stderr, flush=True)
        send_to_teams(Config['teams_incoming_webhook'], "Warning", err, [])
    return result

#---------------------------------------------------------------------
#   テストを実行
#
# 概要:
#   vdbenchを実行し、テストを行います。
# 引数:
#   scenario   シナリオ名(例: rand-bs4k-read100)
#   iops       IOPS(0でmax)
#   reportdir  結果を出力するベースディレクトリ(例: ./report)
# 戻り値:
#   テスト結果のDataFrame
#---------------------------------------------------------------------
def run_test(scenario: str, iops: int, reportdir: str) -> pd.DataFrame:
    """
    Run a test

    Run VDBENCH for test.

    Parameters
    ----------
    scenario: str
        scenario name (e.g. rand-bs4k-read100)
    iops: int
        IOPS (0 means max)
    reportdir: str
        Base directory to output results (e.g. . /report)

    Returns
    -------
    DataFrame
        DataFrame of test result
    """
    # ディレクトリ作成
    iops = str(iops) if iops != 0 else "max"
    scenario_iops = scenario + "-iops" + iops
    timestamp = time.strftime('%Y%m%d-%H%M%S', time.localtime())
    reportdir = reportdir + "/" + scenario_iops + "_" + timestamp
    os.makedirs(reportdir, exist_ok=True)
    # テスト開始時のスクリプトを実行
    if Config['test_start_script']:
        subprocess.run(Config['test_start_script'] + ' ' + reportdir + ' ' + scenario + ' '
                       + iops + ' ' + timestamp, shell=True)
    # シナリオの作成と実行、レポート作成
    if not Config['debug_only']:
        # テンプレートからシナリオ作成
        scenario_file = reportdir + "/" + scenario_iops + ".scenario"
        make_file_from_template(Config_Dir + "/scenario.template", scenario_file, 
                                {'iops': iops, 'scenario': scenario, 'AutoVDB_Home': AutoVDB_Home})
        # VDBENCH実行
        subprocess.run("export OUTPUT_DIR=\"{1}\"; vdbench -f {0} -o {1}".format(scenario_file, reportdir), shell=True)
        print("Waiting for cool down", flush=True)
        time.sleep(Config['cooldown_wait'])
        # CSVレポート作成
        result = make_csv_report(iops, timestamp, reportdir)
    else:
        # デバッグモードの場合は適当なデータを返す
        result = run_test_dummy(scenario, iops, reportdir)
    # テスト終了時のスクリプトを実行
    if Config['test_end_script']:
        subprocess.run(Config['test_end_script'] + ' ' + reportdir + ' ' + scenario + ' '
                       + iops + ' ' + timestamp, shell=True)
    return result

#---------------------------------------------------------------------
#   テストを実行(ダミー)
#
# 概要:
#   デバッグのためIOPSに見合うLatencyを含む適当なデータを返します
# 引数:
#   scenario     シナリオ名(例: rand-bs4k-read100)
#   target_iops  IOPS(0でmax)
#   reportdir    結果を出力するディレクトリ(run_testとは指定が異なるため注意)
#                (例: ./report/rand-bs4k-read100-20230517_103800)
# 戻り値:
#   テスト結果のDataFrame
#---------------------------------------------------------------------
def run_test_dummy(scenario: str, target_iops: str, reportdir: str) -> pd.DataFrame:
    """
    Run a test (Dummy)

    Returns appropriate data for debugging, including latency for IOPS

    Parameters
    ----------
    scenario: str
        scenario name (e.g. rand-bs4k-read100)
    target_iops: int
        IOPS (0 means max)
    report_dir: str
        Directory to output the results (note that the specification is
        different from run_test)
        (e.g. ./report/rand-bs4k-read100-20230517_103800)
    
    Returns
    -------
    DataFrame
        Test result
    """
    # IOPSに見合うLatencyを計算(多項式近似式からダミーデータを生成)
    iops = 250000 if target_iops == "max" else int(target_iops)
    coe = [1.42977323e-49, -1.66623627e-43, 8.32486951e-38, -2.33125165e-32,
           4.01683643e-27, -4.40255367e-22, 3.06815109e-17, -1.32103848e-12,
           3.29621659e-08, -4.17197769e-04, 2.56949405e+00]
    latency = 0
    for a in coe:
        latency = latency * iops + a
    # 必要な結果のみをデータとして返す
    timestamp = time.strftime('%Y%m%d-%H%M%S', time.localtime())
    result = pd.DataFrame({'target_iops': [target_iops], 'timestamp': [timestamp],
                           'iops': [iops], 'throughput': [iops * 4 / 1024], 'blocksize': [4096],
                           'read_pct': 100, 'resp_time': [latency]})
    # CSVとして保存
    result.to_csv(reportdir + '/result.csv', index=False)
    # ウェイト
    time.sleep(DEBUG_VDBENCH_WAIT)
    return result

#---------------------------------------------------------------------
#   テンプレートを使用してファイルを作成
#
# 概要:
#   指定されたテンプレートファイルの変数を指定された値に置き換え新しいファ
#   イルを作成する。
# 引数:
#   tempfile  テンプレートファイル
#   newfile   作成されるファイル
#   keywords  置き換える値(dic形式)
# 戻り値:
#   なし
#---------------------------------------------------------------------
def make_file_from_template(tempfile: str, newfile: str, keywords: dict) -> None:
    """
    Create a new file using a template

    Creates a new file replacing the variables in the specified template
    file with the specified values.

    Parameters
    ----------
    tempfile: str
        Template file
    newfile: str
        File to be created
    keywords: dict
        Value to replace (dic format)
    """
    with open(tempfile, 'r', encoding='UTF-8') as f:
        template = string.Template(f.read())
        text = template.safe_substitute(keywords)
    with open(newfile, 'w', encoding='UTF-8') as f:
        f.write(text)

#---------------------------------------------------------------------
#   CSVレポート作成
#
# 概要:
#   IOPS, resp_timeなどVDBENCHの結果(totals.html)やsysstatの結果を纏めた
#   CSVファイルを作成
# 引数:
#   target_iops  Target IOPS (VDBENCHに指定されたIOPS)
#   timestamp    実施日時(YYYYMMDD-HHMMSS形式)
#   reportdir    結果が出力されたディレクトリ
# 戻り値:
#   テスト結果のDataFrame
#---------------------------------------------------------------------
def make_csv_report(target_iops: str, timestamp: str, reportdir: str) -> pd.DataFrame:
    """
    Make CSV Report

    Make CSV report from VDBENCH result file (totals.html) and sysstat 
    such as IOPS, resp_time

    Parameters
    ----------
    target_iops: str
        Target IOPS (IOPS specified to VDBENCH)
    timestamp: str
        Test date and time (YYYYMMDD-HHMMSS format)
    reportdir: str
        where results are output

    Returns
    -------
    DataFarame
        Test result
    """
    # Target IOPSと日時を設定
    csv_report = pd.DataFrame({'target_iops': [target_iops], 'timestamp': [timestamp]})
    # VDBENCHのレポートを取得
    vdbench_report = get_vdbench_report(reportdir)
    csv_report = pd.concat([csv_report, vdbench_report], axis=1)
    # qos statistics latency showを取得
    if Config['storage_type'].lower() == 'netapp_ontap':
        latency_report = pd.DataFrame(get_qos_latency_report(reportdir))
        csv_report = pd.concat([csv_report, latency_report.T], axis=1)
    # sysstat -x を読み込み
    if Config['storage_type'].lower() == 'netapp_ontap':
        files = glob.glob(reportdir + "/*_sysstat-x.log")
        for file in files:
            match = re.match(r'(.+?)-([0-9]+)_sysstat-x.log$', file)
            if match:
                nodenum = match.group(2)
                sysstat_report = get_sysstat_x_report(file)
                # 列名にノード番号を付加
                sysstat_report = sysstat_report.add_prefix(nodenum + "_")
                csv_report = pd.concat([csv_report, pd.DataFrame(sysstat_report).T], axis=1)
    # 不要な列を削除
    csv_report.drop(columns=["time", "interval"], inplace=True)
    # ファイルへ書き出し
    csv_report.to_csv(reportdir + "/result.csv", index=False)
    return csv_report

#---------------------------------------------------------------------
#   CSVレポート読み込み
#
# 概要:
#   テストごとに作成されるCSVレポートを読み込み
# 引数:
#   reportdir  CSVレポートがあるディレクトリ
# 戻り値:
#   テスト結果のDataFrame
#---------------------------------------------------------------------
def load_csv_report(reportdir: str) -> pd.DataFrame:
    """
    Load CSV report
    
    Load CSV report which is made by each test and return DataFrame

    Paramters
    ---------
    reportdir: str
        Directory with CSV report
    
    Returns
    -------
    pd.DataFrame
        DataFrame of test result
    """
    if os.path.isfile(reportdir + "/result.csv"):
        return pd.read_csv(reportdir + "/result.csv")
    else:
        return None

#---------------------------------------------------------------------
#   既存ディレクトリをリネームして新しいディレクトリを作成
#
# 概要:
#   指定されたディレクトリを作成します。ただし、同名のディレクトリが既に
#   存在する場合は、既存ディレクトリをXXX.001のようにリネームしてから新規
#   ディレクトリを作成します。リネーム先が既に存在する場合は.002, .003と
#   順次接尾辞の数字が増えていきます。新しいものが.001となり、古いものが
#   .002となるわけではありません。
#   例) DIRを作成する場合
#     DIR (既存)
#     DIR.001 (既存)
#     DIR → DIR.002とリネームして、DIRを新規作成
# 引数:
#   dir  作成するディレクトリ名
# 戻り値:
#   なし
#---------------------------------------------------------------------
def makedir_with_rename(dir: str) -> None:
    """
    Create a directory with renaming the existing directory

    Creates the specified directory. However, if a directory with the
    same name already exists, the existing directory is renamed to
    XXX.001, and then a new directory is created. If the renamed
    directory already exists, the suffix number is increased sequentially
    to .002, .003, and so on. The new one does not become .001 and the
    old one .002.

    Ex) When creating a DIR
      DIR (existing)
      DIR.001 (existing)
      Rename DIR to DIR.002 and create a new DIR

    Parameters
    ----------
    dir: str
        Name of the directory to be created
    """
    if os.path.isdir(dir):
        # 既存ディレクトリを衝突しないディレクトリ名にリネーム
        for n in range(1, 1000):
            target_dir = dir + '.{:03}'.format(n)
            if not os.path.isdir(target_dir):
                break
        os.rename(dir, target_dir)
    os.makedirs(dir)

#---------------------------------------------------------------------
#   VDBENCHのレポート取得
#
# 概要:
#   IOPS, Latencyなどを纏めたDataFrameを取得
# 引数:
#   reportdir  結果が出力されたディレクトリ
# 戻り値:
#   DataFrame
#---------------------------------------------------------------------
def get_vdbench_report(reportdir: str) -> pd.DataFrame:
    """
    Get report of VDBENCH

    Obtain a DataFrame that summarizes IOPS, latency, etc.

    Parameters
    ----------
    reportdir: str
        Directory where results outputs

    Returns
    -------
    DataFrame
    """
    # vdbenchのtotals.htmlを読み込み
    VDB_TOTAL_HEADER = ["time", "interval", "iops", "throughput", "blocksize", "read_pct",
                        "resp_time", "read_resp", "write_resp", "read_max", "write_max",
                        "resp_stddev", "queue_depth", "cpu_sys+u", "cpu_sys"]
    subprocess.run("tail -1 " + reportdir + "/totals.html > " + TEMP_FILE + " 2> /dev/null", shell=True)
    vdbench_report = pd.read_csv(TEMP_FILE, sep="\s+", names=VDB_TOTAL_HEADER)
    os.remove(TEMP_FILE)
    return vdbench_report

#---------------------------------------------------------------------
#   sysstat -xのCSVレポート取得
#
# 概要:
#   CPU%, Disk Utilなどの平均を纏めたDataFrameを取得
# 引数:
#   reportfile  結果が出力されたファイル
# 戻り値:
#   DataFrame
#---------------------------------------------------------------------
def get_sysstat_x_report(reportfile: str) -> pd.DataFrame:
    """
    Get report of sysstat -x

    Obtain a DataFrame that summarizes averages of CPU%, Disk Util, etc.

    Parameters
    ----------
    reportfile: str
        File with results output

    Returns
    -------
    DataFrame
    """
    # sysstat -x を読み込み
    SYSSTAT_X_HEADER = ["CPU", "NFS", "CIFS", "HTTP", "storage_iops", "net_in", "net_out",
                        "disk_read", "disk_write", "tape_read", "tape_write", "cache_age",
                        "cache_hit", "cp_time", "cp_type", "cp_ph", "disk_util", "other",
                        "FCP", "iSCSI", "FCP_in", "FCP_out", "iSCSI_in", "iSCSI_out",
                        "NVMeF", "NVMeF_in", "NVMeF_out", "NVMeT", "NVMeT_in", "NVMeT_out"]
    subprocess.run("grep % " + reportfile + " > " + TEMP_FILE + " 2> /dev/null", shell=True)
    sysstat_report = pd.read_csv(TEMP_FILE, sep="\s+", names=SYSSTAT_X_HEADER)
    os.remove(TEMP_FILE)
    # 単位の%やsを削除
    for col in ["CPU", "cache_hit", "cp_time", "disk_util"]:
        sysstat_report[col] = pd.to_numeric(sysstat_report[col].str.replace('%', ''), errors='coerce')
    # ゼロ以外の行で平均を求める
    sysstat_report.drop(columns=["cp_type", "cp_ph", "cache_age"], inplace=True)
    sysstat_report_avg = sysstat_report[sysstat_report["storage_iops"] != 0].mean()
    return sysstat_report_avg

#---------------------------------------------------------------------
#   qos statistics latency showのレポート取得
#
# 概要:
#   Total Latency, NVRAM Latencyなどの平均を纏めたDataFrameを取得
# 引数:
#   reportdir  結果が出力されたディレクトリ
# 戻り値:
#   DataFrame
#---------------------------------------------------------------------
def get_qos_latency_report(reportdir: str) -> pd.DataFrame:
    """
    Get report of qos statistics latency show

    Obtain a DataFrame that summarizes the average of Total Latency, 
    NVRAM Latency, etc.

    Parameters
    ----------
    reportdir: str
        Directory where results outputs
    
    Returns
    -------
    DataFrame
    """
    # qos latency show を読み込み
    TMPFILE = "/var/tmp/run_all.tmp"
    QOS_LATENCY_HEADER = ["qos_policy", "storage_latency", "network_latency", "cluster_latency",
                          "data_latency", "disk_latency", "qos_max", "qos_min", "nvram_latency",
                          "cloud_latency", "flexcache_latency", "SM_sync_latency", "VA_latency",
                          "AV_scan_latency"]
    subprocess.run("grep 'total-' " + reportdir + "/qos_statistics_latency_show.log > " + TMPFILE +
                   " 2> /dev/null", shell=True)
    qos_latency = pd.read_csv(TMPFILE, sep="\s+", names=QOS_LATENCY_HEADER)
    os.remove(TMPFILE)
    # 単位(us,ms)を削除し、ミリ秒に統一
    for col in qos_latency.columns[1:]:
        tmp = qos_latency[col].str.extract(r'([0-9\.]+)(us|ms)')
        qos_latency[col] = tmp[0].astype('float').div(tmp[1].map({'us': 1000, 'ms': 1}))
    # ゼロ以外の行で平均を求める
    qos_latency.drop(columns="qos_policy", inplace=True)
    qos_latency_avg = qos_latency[qos_latency["storage_latency"] != 0].mean()
    return qos_latency_avg

#---------------------------------------------------------------------
#   テスト結果からカットオフ値を計算し、折れ線グラフを作成
#
# 概要:
#   テスト結果のDataFrameからIOPSとLatencyの折れ線グラフを作成します。
#   さらに多項式近似とカットオフ値(特定のレイテンシの時のIOPS値)も計算し、
#   グラフに書き入れます。グラフはファイルに保存します。
# 引数:
#   title    グラフのタイトル
#   results  テスト結果のDataFrameのリスト
#   file     保存先のファイル名
# 戻り値:
#   カットオフの値(IOPS)のリストのリスト
#   例) [[1, 2, 3], [4, 5, 6]]
#---------------------------------------------------------------------
def plot_iops_latency(title: str, results: list, img_file: str, html_file: str) -> list:
    """
    Calculate polyfit and cutoff, and plot iops-latency graph
      
    Create a line graph of IOPS and Latency from the test result DataFrame.
    In addition, calculate the polynomial fitting and the cutoff value
    (IOPS value at a specific latency), The graph is saved to a file.

    Patameters
    ----------
    title: str
        Title of graph
    results: List of DataFrame
        DataFrame of test results
    file: str
        Filename to save the graph

    Returns
    -------
    List
        List of list of cutoff values (IOPS)
        ex) [[1, 2, 3], [4, 5, 6]]
    """
    # テスト結果ごとに近似計算やカットオフ計算、グラフ描画を行う
    fig = go.Figure()
    cutoff_iops_list = []
    index = 0
    for result in results:
        # テスト結果をソート
        result = result.sort_values('iops')

        # 多項式近似とカットオフを計算
        cutoff_iops = []
        for cutoff in Config['cutoff_latency']:
            x_cutoff = calc_cutoff(result['iops'], result['resp_time'], cutoff)
            # カットオフをグラフに描画
            if x_cutoff:
                fig.add_shape(type='line', xref='x', yref='y', x0=0, y0=cutoff,
                            x1=x_cutoff, y1=cutoff, line=dict(dash='dash', color='gray', width=1))
                fig.add_shape(type='line', xref='x', yref='y', x0=x_cutoff, y0=0,
                            x1=x_cutoff, y1=cutoff, line=dict(dash='dash', color='gray', width=1))
            else:
                fig.add_shape(type='line', xref='x', yref='y', x0=0, y0=cutoff,
                          x1=result['iops'].max(), y1=cutoff, line=dict(dash='dash', color='gray', width=1))
            cutoff_iops.append(x_cutoff)
        cutoff_iops_list.append(cutoff_iops)
        # カットオフ点をグラフに描画
        if Config.get('label'):
            name = Config['label'][index] + " cutoff"
        else:
            name = "cutoff"
        fig.add_trace(
            go.Scatter(x=cutoff_iops, y=Config['cutoff_latency'], name=name, mode='markers',
                       marker=dict(color='gray'), showlegend=False,
                       hovertemplate=('IOPS: %{x}<br>Latency: %{y} ms'))
        )
        # 多項式近似のグラフを描画(単一グラフの場合のみ)
        if len(results) == 1:
            coe, err = polyfit(result['iops'], result["resp_time"])
            if err < Config['polyfit_err_threshold']:
                x_polyfit = np.linspace(result['iops'].min(), result['iops'].max(), 100)
                y_polyfit = np.polyval(coe, x_polyfit)
                fig.add_trace(
                    go.Scatter(x=x_polyfit, y=y_polyfit, name='polyfit', mode='lines', line=dict(color='skyblue'))
                )
        # 実IOPSのグラフを描画
        if Config.get('label'):
            fig.add_trace(
                go.Scatter(x=result['iops'], y=result['resp_time'], customdata=result[['target_iops', 'timestamp']],
                           name=Config['label'][index], mode='markers+lines', line=dict(
                           color=Config['graph_default_colors'][index % len(Config['graph_default_colors'])]),
                           hovertemplate=('IOPS: %{x}<br>Latency: %{y} ms'))
            )
        else:
            fig.add_trace(
                go.Scatter(x=result['iops'], y=result['resp_time'], customdata=result[['target_iops', 'timestamp']],
                       name='actual', mode='markers+lines', line=dict(
                       color=Config['graph_default_colors'][index % len(Config['graph_default_colors'])]),
                       hovertemplate=('IOPS: %{x}<br>Latency: %{y} ms<br><br>' +\
                                      'Target IOPS: %{customdata[0]}<br>Timestamp: %{customdata[1]}'))
            )
        index += 1

    # タイトルと軸の設定
    fig.update_layout(title_text='<b>'+title+'</b>', title_x=0.5)
    fig.update_layout(showlegend=(len(results) != 1))
    fig.update_xaxes(title='IOPS', showline=True, linewidth=1, linecolor='lightgray')
    fig.update_yaxes(title='Latency (ms)', showline=True, linewidth=1, linecolor='lightgray', rangemode='tozero')
    # 保存
    fig.write_image(img_file)
    fig.write_html(html_file)
    return cutoff_iops_list

#---------------------------------------------------------------------
#   多項式近似
#
# 概要:
#   与えられたX,Yのリストを元に多項式近似を行い、パラメータを返します。
#   次数は線形補間との誤差が少なくなるよう自動的に決定します。
# 引数:
#   x  Xの値
#   y  yの値
# 戻り値:
#   coe  近似式の派多メータ
#   err  2乗誤差  
#---------------------------------------------------------------------
def polyfit(x, y):
    """
    Polynomical fitting

    Performs a polynomial fitting based on the given list of X and Y
    and returns an fitting of the parameters.
    The dimension is automatically determined to minimize the error from
    linear interpolation.

    Paramters
    ---------
    x: float
      X values
    y: float
      Y values
    
    Returns
    -------
    List of float
      Parameters of polynomical fitting
    float
      Squared error
    """
    # 誤差が大きい場合のWarningを抑止
    warnings.simplefilter('ignore', np.RankWarning)
    # 線形補間
    x_linear = np.linspace(min(x), max(x), 100)
    linear = interpolate.interp1d(x, y)
    y_linear = linear(x_linear)
    # 多項式近似
    min_err = np.finfo(np.float64).max
    for n in range(2, Config['polyfit_dimensions']+1):
        coe = np.polyfit(x, y, n)
        # 近似したYを計算
        y_polyfit = np.polyval(coe, x_linear)
        err = sum((y_linear - y_polyfit) ** 2)
        if err < min_err:
            min_err = err
            best_coe = coe
    return (best_coe, min_err)

#---------------------------------------------------------------------
#   カットオフ値の計算
#
# 概要:
#   X, Yのリストから線形補間でカットオフ値(指定されたレイテンシを超えるIOPSの値)を
#   計算します。
# 引数:
#   x       Xの値のリスト
#   y       yの値のリスト
#   cutoff  カットオフ値(ms)
# 戻り値:
#   カットオフ値を迎えるx
#---------------------------------------------------------------------
def calc_cutoff(x, y, cutoff):
    """
    Calculate cutoff value
    
    Calculates the cutoff value (the value of IOPS above a specified latency)
    by linear interpolation from the X, Y list.

    Parameters
    ----------
    x: list
        List of X (IOPS)
    y: list
        List of Y (Latency)
    cutoff: float
        Cutoff value (ms)

    Returns
    -------
    float
        X approaching cutoff value
    """
    # 線形補間によりカットオフ値を求める
    x = np.array(x)
    y = np.array(y)
    y2 = np.repeat(cutoff, len(x))
    xc, yc = interpolated_intercept(x, y, y2)
    if xc.size != 0:
        return xc.min()
    else:
        return None

#---------------------------------------------------------------------
#   交点の計算
#
# 概要:
#   X, Y1, Y2のリストから線形補間で2つの曲線の交点を求めます。
# 引数:
#   x   Xの値のリスト
#   y1  y1の値のリスト(曲線1)
#   y2  y2の値のリスト(曲線2)
# 戻り値:
#   交点のx
#---------------------------------------------------------------------
def interpolated_intercept(x, y1, y2):
    """
    Find the intercept of two curves

    Find the intercept of two curves, given by the same x data
    
    Parameters
    ----------
    x: List
        List of X (same X)
    y1: List
        List of Y1 (Curve1)
    y2: List
        List of Y2 (Curve2)

    Returns
    -------
    float
        X of intercept
    """

    def intercept(point1, point2, point3, point4):
        """
        find the intersection between two lines
        
        the first line is defined by the line between point1 and point2
        the first line is defined by the line between point3 and point4
        each point is an (x,y) tuple.

        So, for example, you can find the intersection between
        intercept((0,0), (1,1), (0,1), (1,0)) = (0.5, 0.5)

        Parameters
        ----------
        point1: List
            List of x and y at point1
        point2: List
            List of x and y at point2
        point3: List
            List of x and y at point3
        point4: List
            List of x and y at point4
        Returns
        -------
        List
            the intercept, in (x,y) format
        """    

        def line(p1, p2):
            A = (p1[1] - p2[1])
            B = (p2[0] - p1[0])
            C = (p1[0]*p2[1] - p2[0]*p1[1])
            return A, B, -C

        def intersection(L1, L2):
            D  = L1[0] * L2[1] - L1[1] * L2[0]
            Dx = L1[2] * L2[1] - L1[1] * L2[2]
            Dy = L1[0] * L2[2] - L1[2] * L2[0]

            x = Dx / D
            y = Dy / D
            return x,y

        L1 = line([point1[0],point1[1]], [point2[0],point2[1]])
        L2 = line([point3[0],point3[1]], [point4[0],point4[1]])

        R = intersection(L1, L2)

        return R

    idx = np.argwhere(np.diff(np.sign(y1 - y2)) != 0)
    if idx.size != 0:
        xc, yc = intercept((x[idx], y1[idx]),((x[idx+1], y1[idx+1])), ((x[idx], y2[idx])), ((x[idx+1], y2[idx+1])))
        return xc, yc
    else:
        return np.empty(0), np.empty(0)

#---------------------------------------------------------------------
#   IOPSを丸める
#
# 概要:
#   後の追加テストでユーザ指定がしやすいよう、指定された値が有効桁数2桁に
#   なるよう丸める。
# 引数:
#   val  対象の数
# 戻り値:
#   丸められた数
#---------------------------------------------------------------------
def round_iops(val):
    """
    Round IOPS

    Round the specified value to 2 significant digits for ease of user
    specification in later additional tests.

    Parameters
    ----------
    val: int or float
        target number

    Returns
    -------
    int
        Rounded number
    """
    # 桁数を求める
    num = len(str(int(val)))
    # 10万以上は有効桁数3桁、10万以下は2桁になるよう丸める
    if num >= 6:
        return int(round(val, 3 - num))
    else:
        return int(round(val, 2 - num))

#---------------------------------------------------------------------
#   テスト結果をExcel形式で保存
#
# 概要:
#   テスト結果のDataFrameからデータとグラフをExcelとして保存します
# 引数:
#   title    Excelのタイトル(シナリオ名)
#   results  テスト結果のDataFrame
#   file     保存先のファイル名
# 戻り値:
#   なし
#---------------------------------------------------------------------
def make_iops_latency_excel(title: str, results: pd.DataFrame, file: str) -> None:
    """
    Save IOPS-Latency results with Excel format

    Save the data and graphs from the test results DataFrame with Excel format.

    Parameters
    ----------
    title: str
        Title of Excel (scenario name)
    results: DataFrame
        DataFrame of test results
    file: str
        Filename to save
    """

    # ワークブックとシートを作成
    workbook = openpyxl.Workbook()
    sheet = workbook.create_sheet(index=0)
    # データ書き込み
    sheet["A1"] = title
    sheet["A2"] = ""
    for row in dataframe_to_rows(results.sort_values('iops'), index=False, header=True):
        sheet.append(row)
    # グラフ作成
    chart = ScatterChart(scatterStyle='smoothMarker')
    chart.title = title
    chart.x_axis.title = "IOPS"
    chart.y_axis.title = "Latency (ms)"
    chart.legend = None
    x_values = Reference(sheet, min_col=3, max_col=3, min_row=4, max_row=4+len(results)-1)
    y_values = Reference(sheet, min_col=7, max_col=7, min_row=4, max_row=4+len(results)-1)
    series = Series(y_values, x_values)
    series.marker.symbol = "circle"
    chart.series.append(series)
    sheet.add_chart(chart)
    # 保存
    workbook.save(file)

#---------------------------------------------------------------------
#   Teamsでメッセージを送信
#
# 概要:
#   Teamsのチャネルにメッセージを送信します。添付ファイルの指定がある場合、
#   アップローダーの指定があれば、そのファイルをアップロードした上で
#   リンクを添付して送信します。
# 引数:
#   url    Incoming Web HookのURL
#   title  タイトル(省略可)
#   text   メッセージ本分
#   files  添付ファイルのリスト
# 戻り値:
#   なし
#---------------------------------------------------------------------
def send_to_teams(url: str, title: str, text: str, files: list) -> None:
    """
    Send a message via Teams

    Send a message to the Teams channel. If an attachment is specified and
    an uploader is specified, upload the file and then sends the message
    with a link attached.

    Parameters
    ----------
    url: str
        Incoming Web Hook URL
    title: str
        Title (optional)
    test: str
        Message body
    files: List
        List of attached files
    """

    # Incoming Web Hookの指定がなければすぐに戻す
    if not url:
        return
    # メッセージ送信用オブジェクト作成
    teams = pymsteams.connectorcard(url)
    # タイトル
    if title != "":
        teams.title(title)
    # 本文と添付ファイル
    link = ""
    if Config['uploader_url']:
        for file in files:
            # ファイルをアップロード
            timestamp = time.strftime('%Y%m%d-%H%M%S', time.localtime())
            (filename, ext) = os.path.splitext(os.path.basename(file))
            filename = Config['upload_file_prefix'] + filename + "_" + timestamp + ext
            upload_file(Config['uploader_url'], file, filename)
            # ファイルへのリンクを生成
            if ext == ".png":
                link = link + "<img src=\"{0}\">\r\n<a href=\"{0}\">View Image</a><br>\r\n".format(Config['uploader_reference_url'] + filename)
            elif ext == ".xlsx":
                link = link + "<a href=\"{}\">Download Excel</a><br>\r\n".format(Config['uploader_reference_url'] + filename)
            elif ext == ".html":
                link = link + "<a href=\"{}\">View Page</a><br>\r\n".format(Config['uploader_reference_url'] + filename)
    teams.text(text + "\r\n" + link)
    # 送信
    teams.send()

#---------------------------------------------------------------------
#   ファイルをアップロード
#
# 概要:
#   ファイルをPOST形式でアップロードします
# 引数:
#   url       URL
#   file      アップロードするファイル
#   filename  アップロード先のファイル名
# 戻り値:
#   なし
#---------------------------------------------------------------------
def upload_file(url: str, file: str, filename: str) -> None:
    """
    Upload file

    Upload aa file via POST method

    Parameters
    ----------
    url: str
        URL to upload
    file: str
        file path to upload
    filename: str
        filename in destination
    """
    data = open(file, 'rb').read()
    file_data = {'files': (filename, data)}
    response = requests.post(url, files=file_data)
    if response.status_code != 200 and response.status_code != 204:
        print("Can't upload file: " + file, file=sys.stderr, flush=True)

if __name__ == '__main__':
    # ディレクトリ名の設定
    AutoVDB_Home = os.path.dirname(__file__)
    if AutoVDB_Home == '':
        AutoVDB_Home = os.getcwd()
    Config_Dir = AutoVDB_Home + '/' + CONFIG_DIR_NAME + '/'
    Autogen_Config_Dir = AutoVDB_Home + '/' + AUTOGEN_CONFIG_DIR_NAME + '/'
    # 設定ファイルと引数の取得
    Config = load_config(Config_Dir + CONFIG_FILE_NAME)
    args = get_args()
    Config.update(args)
    # メイン呼び出し
    main()
