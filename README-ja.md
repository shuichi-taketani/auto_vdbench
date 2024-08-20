# Auto VDBENCH

[English README is here](README.md)

## 概要

VDBENCHを使用して、様々な条件でストレージのパフォーマンスを測定し、結果をインタラクティブなグラフやCSV, Excelなどに纏めます。

![Auto VDBENCHのスクリーンショット](docs/animated_slides.gif)

## 特長

- 重複排除率、圧縮率、シーケンシャルアクセス/ランダムアクセス、ブロックサイズ、リード比率など様々な条件について自動的に測定が可能
- 1つの条件についてIOPSを変化させながらレイテンシを測定するため、負荷に応じたレイテンシの変化を確認することができる
- 測定結果を考慮しながら次に測定するポイントを自動的に決定するため、短い時間で効率的なテストが可能
- NetApp ONTAPストレージではストレージ側の統計情報も取得可能
- テスト結果を自動集計し、インタラクティブなグラフを生成。さらに、CSVやExcelで出力。
- カットオフ(あるレイテンシに達するIOPSの値)を自動計算、また多項式近似によるスムースな近似線をグラフに自動表示
- IOPSやレイテンシ、ストレージのCPU負荷などを自動的にサマリしCSVに出力するため、Excel上でピポッドテーブルによる多角的な分析が可能
- テストの途中停止(サスペンド)と再開(レジューム)が可能
- チェックポイントが自動作成され、エラーで終了した場合でもチェックポイントから再開可能
- テストの結果をグラフつきでTeamsチャネル、Slack、LINE Notifyへ投稿。テストの経過をどこでも確認可能。<br>
    (iPhoneアプリのTeamsではインラインでグラフは表示されず、リンクをタップする必要があります)
- 条件の異なる結果を比較するグラフを簡単に作成可能

## セットアップ

1. コードのダウンロード

    GitHubからAuto VDBENCHをcloneまたはダウンロードします。
    ```
    git clone https://github.com/shuichi-taketani/auto_vdbench.git
    ```

1. 必要なモジュールのインストール
    ```
    pip install requests pandas matplotlib openpyxl pymsteams scipy plotly kaleido slack-sdk
    ```

1. VDBENCHのダウンロードとセットアップ

    以下からVDBENCHをダウンロードします。

    [https://www.oracle.com/downloads/server-storage/vdbench-downloads.html](https://www.oracle.com/downloads/server-storage/vdbench-downloads.html)

    ダウンロードしたzipを適当な場所へ展開し、パスを通します。

1. Perfstatのダウンロードとセットアップ(オプション)

    NetApp ONTAPストレージでPerfstatを使って詳細な統計情報を取得する場合、Perfstatをインストールします。尚、PerfstatのダウンロードにはNetApp Supportのアカウントが必要です。

    [https://mysupport.netapp.com/site/tools/tool-eula/perfstat-cdot](https://mysupport.netapp.com/site/tools/tool-eula/perfstat-cdot)

    ダウンロードしたzipを適当な場所へ展開し、パスを通します。

より詳しいセットアップ例は[こちら](docs/setup-ja.md)。

## 使い方

### 用語

- シナリオ名<br>
    ランダムアクセス/シーケンシャルアクセス、ブロックサイズ、リード率を纏めたもので、rand-bs4k-read100のように記載されます

- カットオフ<br>
    あるレイテンシに達するIOPSの値

### 測定モード

Auto VDBENCHには以下3つの測定モードがあります。
- 自動モード

    測定結果を随時考慮しながら、より少ない測定でなめらかなグラフとなるよう次の測定点(IOPS)を自動で決めてテストを行うモード
- 増分モード

    開始IOPSと増分IOPSを決め、開始IOPSから順次IOPSを増やしながらテストを行うモード

- ファイルモード

    CSVで指定した条件のみテストを行うモード。主に測定の一部やり直しや追加測定に使用する。<br>
    CSVは重複排除率、圧縮率、シナリオ名、測定IOPSを並べたもの。[sample/auto_vdbench.csv](sample/auto_vdbench.csv)にサンプルがある。

### 測定の流れ

1. ブロックサイズやリード率などのテスト条件を決め、設定ファイル(conf/auto_vdbench.conf)へ反映

1. 自動モードで測定

    ```
    auto_vdbench.py start
    ```

1. graphlist.htmlで結果を確認し、再取得が必要な部分を判断

    結果はレポートディレクトリ(report/)に出力される。重複排除率・圧縮率ディレクトリ以下にあるgraphlist.htmlを開き、グラフを確認する。

    - グラフの一部に異常値があり取り直したい<br>
        → 取り直したい部分のシナリオ名とTarget IOPSをCSVに記載し、ファイルモードで再テストを行う。

    - 特定のシナリオを取り直したい<br>
        → 設定ファイルのscenario_listに対象のシナリオ名を記載し、自動モードまたは増分モードで再テスト<br>
        (ランダムアクセスでは自動モード、シーケンシャルアクセスでは増分モードがお勧め)

1. 再テスト

    自動モードの場合:
    ```
    auto_vdbench.py start
    ```

    増分モードの場合:
    ```
    auto_vdbench.py start --test-mode inc
    ```

    ファイルモードの場合:
    ```
    auto_vdbench.py start --test-mode file --test-pattern-file retest.csv
    ```

1. ファイルモードの場合、レポートを再作成する(自動モードと増分モードでは自動的にレポートが再作成される)

    ```
    auto_vdbench.py create-report
    ```

1. グラフを再確認し、満足のいく結果が出るまでテストを繰り返す

※ Target IOPSが同一の場合、新しい測定結果が利用されます。また、同名のシナリオディレクトリがある場合、古いものはリネームされます。これらの仕様により、テストを再実行するだけで新しい結果からグラフが作成されます。  
また、ディレクトリ名は厳密なマッチが行われるため、リネームを行うだけでその結果をグラフから外すことができます。  
(例. rand-bs4k-read100_iops1000_20230627-170500 → rand-bs4k-read100_iops1000_20230627-170500.oldとすることで、この結果は使用されなくなります)

### レポートディレクトリの構成とレポート内容

テスト結果は以下のようなディレクトリ構成でレポートディレクトリ(デフォルトはスクリプトのあるディレクトリ以下のreport)に出力されます。

- レポートディレクトリ (例. report/)
    - results_all.csv : 各重複排除率・圧縮率ディレクトリにあるresult_dedupcomp.csvを纏めたファイル
    - 重複排除率・圧縮率ディレクトリ (例. dedup1_comp1/)
        - graphlist.html : 各シナリオのグラフを一覧表示するためのファイル
        - result_dedupcomp.csv : 各シナリオのテスト結果(result_scenario.csv)を纏めたファイル
        - シナリオ名ディレクトリ (例. rand-bs4k-read100/)
            - results.html : テスト結果をインタラクティブなグラフに纏めたもの
            - results.png : テスト結果のグラフの画像ファイル
            - results.csv : テスト結果の一覧CSV
            - results.xlsx : テスト結果の一覧とグラフのExcel
            - result_scenario.csv : テスト条件とカットオフ、最大レイテンシ、最大IOPS時のレイテンシ、最大レイテンシ時のIOPS、最大IOPS時のqos statistics latency show、sysstat -xなどを1行にまとめたCSV
            - シナリオ名+測定IOPSと測定日時のディレクトリ (例. rand-bs4k-read100_iops10000_20230624-232802)
                - VDBENCHが出力する全てのファイル
                - NetApp ONTAPの場合以下も出力される
                    - sysstat -x 1
                    - sysstat -M 1
                    - qos statistics latench show
                    - Perfstat
                - result.csv : VDBENCHの結果やqos statistics latency show、sysstat -xの結果(平均)をCSVに纏めたもの

### オプション

- startサブコマンド

    測定を開始します。測定はsuspendサブコマンドで中断することができる他、要所要所でチェックポイントが保存されており、想定しないエラーで終了したとしても再開することが可能です。

    | オプション | 説明 | 使用例 |
    |----|----|----|
    | -m, --test-mode | テストモード。デフォルトは自動モード。 <br> auto: 自動モード。測定結果を随時考慮しながら、より少ない測定でなめらかなグラフとなるよう次の測定点(IOPS)を自動で決めてテストを行うモード。 <br> inc: 増分モード。開始IOPSと増分IOPSを決め、開始IOPSから順次IOPSを増やしながらテストを行うモード <br> file: ファイルモード。CSVで指定した条件のみテストを行うモード。主に測定の一部やり直しや追加測定に使用する。 | --test-mode file |
    | -d, --dedup-ratio | テストを行う重複排除可能率のリスト。書き込むデータをどの程度重複排除可能なものにするのか指定する。n:1形式で指定し、n=1であれば完全なランダム、n=2であれば2ブロックを1ブロックに重複排除可能であることを示す。後術の-c, --compression-ratioと合わせ、すべての組み合わせのテストが行われる。このオプションを指定した場合、設定ファイルよりこのオプションが優先される。 | --dedup-ratio 1 3 5 |
    | -c, --compression-ratio | テストを行う圧縮可能率のリスト。書き込むデータをどの程度圧縮可能なものにするのか指定する。n:1形式で指定し、n=1であれば完全なランダム、n=2であれば1/2に圧縮可能であることを示す。このオプションを指定した場合、設定ファイルよりこのオプションが優先される。 | --compression-ratio 1 3 5 |
    | -f, --test-pattern-file | ファイルモードでテストを行う条件を記載したCSVを指定する。CSVは重複排除率、圧縮率、シナリオ名、測定IOPSを並べたもの。[sample/auto_vdbench.csv](sample/auto_vdbench.csv)にサンプルがある。 | --test-pattern-file auto_vdbench.csv |
    | -r, --report-dir | テスト結果を出力するディレクトリ。このオプションを指定した場合、設定ファイルよりこのオプションが優先される。 | --report-dir report/ |
    | --skip-creating-testfiles | テストファイルの作成をスキップする。前回のテストと同じ重複排除率・圧縮率のテストを行う場合、テストファイルの作成時間を省略するために使用する。デフォルトはFalse (テストファイルを作成する) | --skip-creating-testfiles true |
    | --skip-creating-testfiles-at-first | 初回のみテストファイルの作成をスキップする。複数の重複排除率・圧縮率のテストを行うが、初めのテストは前回と同じ重複排除率・圧縮率の場合に使用する。デフォルトはFalse。 | --skip-creating-testfiles-at-first true |
    | --skip-creating-conffiles | 自動生成設定ファイルの作成をスキップする。VDBENCHの設定ファイルを直接編集してテストを行いたい場合に指定する。デフォルトはFalse。 | --skip-creating-conffiles true |
    | --graph-title | 生成されるグラフリストのタイトルを指定する | --graph-title "A800 NFS" |
    | --debug-only | VDBENCHやテストファイル作成スクリプトを呼び出さず、デバッグ用の測定結果を返す | --debug-only true |

- stopサブコマンド

    測定を直ちに中止します。中止した測定は再開できません。

- suspendサブコマンド

    測定を中断します。測定モードによって中断できる場所に違いがあります。
    - 自動モード : シナリオ単位
    - 増分モード : シナリオ単位
    - ファイルモード : テスト(行)単位

- resumeサブコマンド

    中断した測定またはチェックポイントから再開します。

- create-reportサブコマンド

    レポートを再作成します。一部を再測定したり、ディレクトリをリネームして測定点を外した場合に使用します。
    | オプション | 説明 | 使用例 |
    |----|----|----|
    | -r, --report-dir | テスト結果が出力されたディレクトリを指定する。レポートディレクトリのルートの他、重複排除率・圧縮率ディレクトリ、シナリオディレクトリも指定可能。 | --report-dir report/dedup1_comp1/rand-bs4k-read100 |
    | --graph-title | 生成されるグラフリストのタイトルを指定する | --graph-title "A800 NFS" |

- create-comparison-reportサブコマンド

    複数の測定結果を1つのグラフにまとめた比較グラフを作成します。
    | オプション | 説明 | 使用例 |
    |----|----|----|
    | -r, --report-dir | テスト結果が出力されたディレクトリを複数指定する。レポートディレクトリのルートの他、重複排除率・圧縮率ディレクトリも指定可能。 | --report-dir report/A800/dedup1_comp1/ report/C800/dedup1_comp1 |
    | -l, --label | 各テスト結果を表す名称(ラベル)を複数指定する。レポートディレクトリの指定と順序を合わせること。 | --label A800 C800 |
    | -c, --color | 各テスト結果をグラフに描画する際の色を指定する。色名はCSSできるものの他、#RRGGBBでの指定も可能。このオプションを指定した場合、設定ファイルよりこのオプションが優先される。 | --color blue red |
    | -o, --output-dir | グラフを出力するディレクトリを指定する | --output-dir comparison/ |
    | --graph-title | 生成されるグラフリストのタイトルを指定する | --graph-title "A800 vs C800 NFS" |

- initサブコマンド

    設定ファイル(conf/auto_vdbeench.conf)の内容を元に、VDBENCHやヘルパースクリプトで使用する設定ファイルを(auto_genconf/に)生成します。自動生成設定ファイルはテストの度に生成されるされるため、通常はこのサブコマンドを使用する必要がありませんが、セットアップ時にヘルパースクリプト使用する場合に使用します。

### 設定ファイル

conf/auto_vdbench.confが設定ファイルになっており、このファイルで負荷サーバなどの環境、重複排除率・圧縮率などのテスト条件などを指定します。コメントつきJSONになており、#で始まる行はコメントと見なされます。重複排除率・圧縮率などいくつかコマンドラインオプションと同じ指定がありますが、コマンドラインオプションが優先されます。  
(各設定値では、${AutoVDB_Home}でスクリプトのあるディレクトリを示すことができます。)


| 項目名 | 説明 | 設定例 |
|----|----|----|
| server_list | 負荷をかけるサーバの一覧 | ["rocky1", "rocky2"] |
| server_threads | サーバ1台あたりの負荷生成スレッド数 | 512 |
| storage_type | ストレージ側の情報を取得するためのストレージタイプの設定 <br> "general": 追加取得なし <br> "NetApp_ONTAP": sysstat -x, -M, qos statistics latency show, perfstatを取得 | "NetApp_ONTAP" |
| ontap_cluster_name | ONTAPのクラスタ名 <br> (storage_typeがNetApp_ONTAPの場合のみ必要) | "sr-a800" |
| ontap_node_names | ONTAPのノード名 <br> (storage_typeがNetApp_ONTAPの場合のみ必要) | ["sr-a800-01", "sr-a800-02"] |
| ontap_id | ONTAPにログインする際のユーザ名 <br> (storage_typeがNetApp_ONTAPの場合のみ必要) | "admin" |
| ontap_passwd | ONTAPにログインする際のパスワード <br> (storage_typeがNetApp_ONTAPの場合のみ必要) | "Password123" |
| ontap_perfstat_interval | Perfstatを取得する際のインターバル(分)。3分以下を指定した場合は3分になる。 <br> (storage_typeがNetApp_ONTAPの場合のみ必要) | 3 |
| testfile_size | テストファイルのサイズ(GB)。サーバ1台に対する指定のため、この値xサーバ台数がトータルのテストファイルサイズとなる。 | 256 |
| testfile_dir | テストファイルを作成するディレクトリ | "/mnt/test" |
| test_duration | テスト時間(秒) | 300 |
| test_warmup | テスト開始までのウォームアップ(秒) | 30 |
| cooldown_wait | テスト間のウェイト(秒)。テストファイルを作成した後のウェイトとしても使われる。 | 60 |
| max_retry | 最大リトライ回数 | 3 |
| inc_iops_start | 増分モードでの開始IOPS | 10000 |
| inc_iops_step | 増分モードでのテストごとのIOPSの増分 | 10000 |
| dedup_ratio | テストを行う重複排除可能率のリスト。書き込むデータをどの程度重複排除可能なものにするのか指定する。n:1形式で指定し、n=1であれば完全なランダム、n=2であれば2ブロックを1ブロックに重複排除可能であることを示す。後術のcompression_ratioと合わせ、すべての組み合わせのテストが行われる。 | [1, 3, 5] |
| compression_ratio | テストを行う圧縮可能率のリスト。書き込むデータをどの程度圧縮可能なものにするのか指定する。n:1形式で指定し、n=1であれば完全なランダム、n=2であれば1/2に圧縮可能であることを示す。 | [1, 3, 5] |
| read_ratio_list | テストを行うリード率のリスト。100で100%リード、0で100%ライトを示す。 | [100, 70, 50, 30, 0] |
| random_blocksize_list | ランダムアクセスの際のブロックサイズのリスト(KB) | [4, 8, 16, 32] |
| sequential_blocksize_list | シーケンシャルアクセスの際のブロックサイズのリスト(KB) | [32, 64, 128] |
| scenario_list | 測定するシナリオのリスト。空の場合は全パターンを測定。 | ["rand-bs4k-read100"] |
| scenario_test_result_merge_mode | シナリオテストを行う際、既にディレクトリが存在した場合、既存ディレクトリをリーネームするのか、既存ディレクトリに結果をマージするのかを指定。特定のシナリオのみ再テストを行う場合、前回のテスト結果を利用しない場合は"rename"を選択する。自動モードと増分モードのみ有効。 <br> "rename": 既存ディレクトリをrand-bs4k-read100.001のようにリネーム <br> "merge": 既存ディレクトリにあるテスト結果にマージ(追加) | "rename" |
| test_start_script | 個別の(最小単位であるIOPSごとの)テスト開始時に実行されるスクリプトのパス <br> (引数にレポートディレクトリ、シナリオ名、IOPS、タイムスタンプが渡される) | "${AutoVDB_Home}/test_start.sh" |
| test_end_script | 個別の(最小単位であるIOPSごとの)テスト終了時に実行されるスクリプトのパス <br> (引数にレポートディレクトリ、シナリオ名、IOPS、タイムスタンプが渡される) | "${AutoVDB_Home}/test_end.sh" |
| scenario_start_script | シナリオテスト(例. rand-bs4k-read100)開始時に実行されるスクリプトのパス <br> (引数にレポートディレクトリ、シナリオ名が渡される) | "${AutoVDB_Home}/scenario_test_start.sh" |
| scenario_end_script | シナリオテスト(例. rand-bs4k-read100)終了時に実行されるスクリプトのパス <br> (引数にレポートディレクトリ、シナリオ名が渡される) | "${AutoVDB_Home}/scenario_test_end.sh" |
| make_testfile_script | テストファイル作成スクリプトのパス。通常は変更不要。 | "${AutoVDB_Home}/shell/make_testfile.sh" |
| stop_vdbench_script | VDBENCH停止スクリプトのパス。通常は変更不要。 | "${AutoVDB_Home}/shell/stop_vdbench.sh" |
| report_dir | レポートを出力するディレクトリ | "${AutoVDB_Home}/report" |
| auto_min_test_count | 自動モード使用時のシナリオあたりの最小テスト回数。この値を増やすことで、レイテンシの変化が緩やかな場合でもなめらかなグラフを得ることができます。 | 10 |
| auto_max_test_count | 自動モード使用時のシナリオあたりの最大テスト回数 | 20 |
| auto_additional_percent_to_max | 自動モードで最大値よりどの程度高いIOPSを計測するか(パーセント)(0指定で計測しない)。最大IOPSよりも高いIOPSでも継続してレイテンシが増加することを確認するためのオプションですが、計測しない方が綺麗なグラフを得られるようです。 | 5 |
| auto_min_iops | 自動モードで下限となるIOPS | 100 |
| auto_threshold_to_find_min_latency | 自動モードで最小レイテンシを探す際、前回計測点からどの程度レイテンシが変わらなければ最小レイテンシであると判断するか(パーセント) | 5 |
| auto_latency_diff_thresold | この値よりレイテンシの差分が小さく、かつ最小テスト回数以上であれば早期にテストを終了する | 20 |
| polyfit_dimensions | 多項式近似を行う際の最大次数 | 10 |
| polyfit_err_threshold | 多項式近似の誤差の閾値。2乗誤差がこの値より大きくなる場合、グラフに多項式近似曲線を表示しない。 | 100 |
| cutoff_latency | カットオフ(特定のレイテンシを超えるIOPSの値)(ms)のリスト | [1, 2, 3, 4] |
| graph_default_colors | グラフのデフォルトカラーリスト。色名はCSSで利用可能な色名または#RRGGBBなどPlotlyで使用できるものであれば使用可能。 | ["blue", "red", "green", "gold", "purple"] |
| teams_send_message_type | Teamsへ通知を行うメッセージのタイプ。ここで指定したタイプのメッセージのみ通知が行われる。 <br> "START":テスト開始 <br> "FINISH": テスト終了  <br>  "SUSPEND": テストサスペンド  <br>  "REPORT": テスト結果のレポート <br> "INFO": テスト精度低下などのお知らせ <br>  "WARNING": 特定シナリオのテスト失敗など継続可能だが対応が必要なもの  <br>  "ERROR": テスト継続が不可能で実行を中止したもの | ["START", "FINISH", "SUSPEND", "REPORT", "INFO", "WARNING", "ERROR"] |
| slack_send_message_type | Slackへ通知を行うメッセージのタイプ。ここで指定したタイプのメッセージのみ通知が行われる。 <br> "START":テスト開始 <br> "FINISH": テスト終了  <br>  "SUSPEND": テストサスペンド  <br>  "REPORT": テスト結果のレポート <br> "INFO": テスト精度低下などのお知らせ <br>  "WARNING": 特定シナリオのテスト失敗など継続可能だが対応が必要なもの  <br>  "ERROR": テスト継続が不可能で実行を中止したもの | ["START", "FINISH", "SUSPEND", "REPORT", "INFO", "WARNING", "ERROR"] |
| line_send_message_type | LINEへ通知を行うメッセージのタイプ。ここで指定したタイプのメッセージのみ通知が行われる。 <br> "START":テスト開始 <br> "FINISH": テスト終了  <br>  "SUSPEND": テストサスペンド  <br>  "REPORT": テスト結果のレポート <br> "INFO": テスト精度低下などのお知らせ <br>  "WARNING": 特定シナリオのテスト失敗など継続可能だが対応が必要なもの  <br>  "ERROR": テスト継続が不可能で実行を中止したもの | ["START", "FINISH", "SUSPEND", "REPORT", "INFO", "WARNING", "ERROR"] |
teams_incoming_webhook | TeamsのIncoming Webhookのアドレス。これを指定すると1つのテストシナリオが終了するごとにチャネルに通知が行われる。 | "https://xxxx.webhook.office.com/webhookb2/" |
| slack_bot_token | SlackのBot User Token。これを指定すると1つのテストシナリオが終了するごとに指定されたチャネルに通知が行われる。 | "xoxb-1234567890" |
| slack_channel | Slackに投稿を行うチャネル | "#general" |
| line_notify_access_token | LINE Notifyのアクセストークン。これを指定すると1つのテストシナリオが終了するごとにLINEに通知が行われる。 | "abcdEFGHijklm" |
| uploader_url | Teamsへ通知を行う際、Teamsに直接画像ファイルを送信することはできないため、外部のアップローダを使用する必要がある。そのアップローダのURL。postでファイルを受け付けられるアップローダが必要。 | "https://xxxx.xxxx/uploader.py" |
| uploader_reference_url | アップロードしたファイルを参照するための参照URL | "https://xxxx.xxxx/" |
| upload_file_prefix | ファイルをアップロードする際、ファイル名の先頭に付加する文字列 | "avdb_" |

## ヘルパースクリプト

Auto VDBENCHから呼び出されるあるいは単独で使用するための便利なスクリプトとして以下が用意されています。

| シェルスクリプト名 | 説明 |
|----|----|
| add_hosts.sh *ファイル名* | 引数に指定したファイルの内容を(自分自身を除く)全サーバの/etc/hostsに追加 |
| cleanup_failed_log.sh [--dry-run] *対象ディレクトリ* | 対象ディレクトリ以下を検索し、テストに失敗したログのディレクトリを削除する。--dry-runオプションを付加すると実際の削除は行わず、削除対象ディレクトリを表示。 |
| copy_all.sh *ファイル名* *ディレクトリ名* | 引数に指定したファイルを(自分自身を除く)全サーバへコピー |
| exec_all.sh *コマンド* | 引数に指定されたコマンドを全サーバで実行 |
| export_report.sh [-l summary\|log] *転送元ディレクトリ* *転送先ディレクトリ* | 出力されたレポートのうち、特定のファイルのみを転送先ディレクトリへコピー。-lオプションで対象ファイルを指定することができ、summaryではWebアクセス(graphlist.html)に必要なHTML、PNG、CSV、Excelのみをコピー。logでは先述のものに加えてVDBENCHのtotals.htmlやqos statistics latency show、sysstat -x、sysstat -Mの出力もコピー。デフォルトはsummary。尚、転送先としてzipを指定するとファイルをコピーする代わりにzipアーカイブが作成される。 <br> 転送元として指定されたディレクトリがベースとなることに注意。<br> 例. export_report.sh report/a800/ htdocs/ → htdocs/report/a800/dedup1_comp1/graphlist.html |
| make_testfile.sh | 全サーバでテストファイルを作成するスクリプト。通常はAuto VDBENCHから呼び出される。 |
| ontapstats-start.sh | ONTAPの統計情報の取得を開始するスクリプト。通常はAuto VDBENCHから呼び出される。 |
| ontapstats-stop.sh | ONTAPの統計情報の取得を停止するスクリプト。通常はAuto VDBENCHから呼び出される。 |
| set_hostnames.sh | 全サーバでホスト名を設定するスクリプト |
| stop_vdbench.sh | VDBENCHを停止(kill)するスクリプト |

## FAQ

- IOPSを増やしていった際のレイテンシ(グラフ右側)が大きすぎます

    ストレージの性能に対して負荷が大きすぎます。設定ファイルのスレッド数(server_threads)を減らしてください。

- IOPSを増やしていった際のレイテンシ(グラフ右側)が小さすぎ、グラフがフラットになってしまいます

    ストレージの性能に対して負荷が十分でない可能性があります。設定ファイルのスレッド数(server_threads)を増やしてください。それでもレイテンシが上がらない場合はサーバ台数やネットワーク構成を見直してください。

- "INFO: The lower range of IOPS could not be fully explored; increase auto_min_test_count or increase auto_threshold_to_find_min_latency." といメッセージが出力されました。

    自動モードではまず最大IOPSを計測し、そこからIOPSを1/2ずつに減らしていき、レイテンシの変化が5%以下になったところを最小レイテンシとしています。上記のメッセージは最小IOPSの探索中に最小テスト回数を超えてしまい、最小レイテンシの探索が途中で終了したことを示します。このメッセージが出力されたシナリオでは、グラフ左側が十分にフラットになっていない可能性があります。最小テスト回数(auto_min_test_count)を増やすか、最小レイテンシの探索を終了する変化量(auto_threshold_to_find_min_latency)を増やすと解消します。

- "INFO: IOPS changes could not be fully explored; increase auto_max_test_count may provide more details on IOPS changes." といメッセージが出力されました。

    自動モードでは、レイテンシの差が最も大きい部分を二分割するように測定を行い、レイテンシの変化が大きい部分ではより沢山測定を行うようになっています。最も大きなレイテンシの差分がauto_latency_diff_thresoldで規定されるデフォルト20ms以下でかつ最小テスト回数を超えていればテストはそこで終了しますが、最大テスト回数(auto_max_test_count)を超えてもなお最も大きなレイテンシの差分が20ms以上ある場合はこのメッセージが出力されます。このメッセージが出力されたシナリオでは、グラフがガタガタになっている可能性があります。最大テスト回数(auto_max_test_count)を増やすかレイテンシ差分(auto_latency_diff_thresold)を増やすと解消します。

- アップローダはどのように準備すればいいですか

    Pythonに[uploadserver](https://pypi.org/project/uploadserver/)というモジュールがありますので、これを利用して頂くのが最も簡単です。クラウド上のサーバなどインターネットからアクセス可能なサーバで以下のようにすることでセットアップが可能です。

    ```
    # pip3 install uploadserver
    # python -m uploadserver --bind (サーバのIPアドレス) 8000
    ```

    この場合、設定ファイルには以下のように記載します。

    ```
    # File Uploader Script URL
    # If specified, upload the chart and attach it to Teams message
    # これを指定するとTeamsへの通知の際にグラフが添付される
    "uploader_url": "http://(uploadserverのPublic IP):8000/upload",

    # File Uploader Reference URL
    # ファイルアップロードサービスの参照URL
    "uploader_reference_url": "http://(uploadserverのPublic IPアドレス):8000/",
    ```

## Author

Shuichi Taketani

## Licence

ソースコードは[MITライセンス](docs/LICENSE)、ドキュメントは[CC BY 4.0ライセンス](https://creativecommons.org/licenses/by/4.0/deed.en)です。
