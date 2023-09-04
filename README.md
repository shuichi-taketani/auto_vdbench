# Auto VDBENCH

[日本語版READMEはこちら](README-ja.md)

## Overview

Auto VDBENCH is a tool that measures the performance of storage under various conditions using VDBENCH and summarizes the results in interactive graphs, CSV files, Excel, and more.

![Auto VDBENCH Screenshot](docs/animated_slides.gif)

## Features

- Automatically measures various conditions such as deduplication ratio, compression ratio, sequential/random access, block size, read ratio, etc.
- Measures latency while varying the IOPS for a specific condition, allowing you to observe the latency changes according to the workload.
- Automatically determines the next measurement points based on the measured results, enabling efficient testing in a short time.
- Supports collecting storage-side statistics for NetApp ONTAP storage.
- Automatically aggregates test results and generates interactive graphs. Additionally, exports results in CSV and Excel formats.
- Automatically calculates cutoff (the value of IOPS at a certain latency) and displays a smooth approximation line using polynomial regression on the graph.
- Automatically summarizes IOPS, latency, storage CPU load, etc., and outputs them to CSV for multidimensional analysis using pivot tables in Excel.
- Supports suspending and resuming tests.
- Automatically creates checkpoints, allowing you to resume from a checkpoint even in case of errors.
- Posts test results with graphs to a Teams channel, Slack and LINE Notify, allowing you to monitor the progress of the test from anywhere.<br>
    (The inline graph is not displayed in the Teams iPhone app and requires tapping the link.)
- Easily creates graphs to compare results with different conditions.

## Setup

1. Download the Code

   Clone or download Auto VDBENCH from GitHub.
   ```
   git clone https://github.com/shuichi-taketani/auto_vdbench.git
   ```

2. Install Required Modules
   ```
   pip install requests, pandas, openpyxl, pymsteams, scipy, plotly, kaleido, slack-sdk
   ```

3. Download and Set Up VDBENCH

   Download VDBENCH from the following link.

   [https://www.oracle.com/downloads/server-storage/vdbench-downloads.html](https://www.oracle.com/downloads/server-storage/vdbench-downloads.html)

   Extract the downloaded zip file to a suitable location and add it to the system path.

4. Download and Set Up Perfstat (Optional)

   If you want to collect detailed statistical information from NetApp ONTAP storage using Perfstat, install Perfstat. Please note that downloading Perfstat requires a NetApp Support account.

   [https://mysupport.netapp.com/site/tools/tool-eula/perfstat-cdot](https://mysupport.netapp.com/site/tools/tool-eula/perfstat-cdot)

   Extract the downloaded zip file to a suitable location and add it to the system path.

For more detailed setup examples, refer to [here](docs/setup.md).

## Usage

### Terminology

- Scenario Name: 

  A combination of random access/sequential access, block size, and read ratio. For example, "rand-bs4k-read100".

- Cutoff:

  The value of IOPS at a certain latency.

### Measurement Modes

Auto VDBENCH has three measurement modes:

- Auto Mode:

  Measures the workload while considering the results and automatically determines the next measurement points (IOPS) to create smooth graphs with fewer measurements.

- Incremental Mode:

  Sets the starting IOPS and incremental IOPS values and performs tests by incrementally increasing the IOPS.

- File Mode:

  Performs tests only for the specified conditions in a CSV file. This mode is mainly used for redoing or adding additional measurements. The CSV file includes deduplication ratio, compression ratio, scenario name, and measurement IOPS. A sample is provided in [sample/auto_vdbench.csv](sample/auto_vdbench.csv).

### Measurement Process

1. Determine the test conditions, such as block size and read rate, and update the configuration file (conf/auto_vdbench.conf) accordingly.

1. Perform measurements in automatic mode:

    ```
    auto_vdbench.py start
    ```

1. Check the results in graphlist.html and identify areas that require retesting.

    The results are output to the report directory (report/). Open graphlist.html located in the deduplication and compression ratio directories to review the graphs.

    - If there are anomalies in certain graphs and you want to redo those tests:<br>
        → List the scenario name and target IOPS in a CSV file and perform retesting using file mode.

    - If you want to redo the specific scenario:<br>
        → Add the target scenario name to the scenario_list in the configuration file and perform retesting in automatic mode or incremental mode.<br>
        (Automatic mode is recommended for random access, and incremental mode is recommended for sequential access.)

1. Retest the measurements:

    For automatic mode:
    ```
    auto_vdbench.py start
    ```

    For incremental mode:
    ```
    auto_vdbench.py start --test-mode inc
    ```

    For file mode:
    ```
    auto_vdbench.py start --test-mode file --test-pattern-file retest.csv
    ```

1. If using file mode, recreate the report (reports are automatically recreated in automatic mode and incremental mode):

    ```
    auto_vdbench.py create-report
    ```

1. Review the graphs again and repeat the testing until satisfactory results are obtained.

NOTE: If the target IOPS is the same, the new measurement results will be utilized. Additionally, if a scenario directory with the same name exists, the old directory will be renamed. This behavior allows creating new graphs by simply rerunning the tests.  
Moreover, since directory names undergo exact matching, renaming a directory will exclude its results from the graphs.  
(Example: Changing "rand-bs4k-read100_iops1000_20230627-170500" to "rand-bs4k-read100_iops1000_20230627-170500.old" will prevent these results from being used.)

### Report Directory Structure and Contents

The test results are output to the report directory (by default, located below the directory of the script) following the directory structure described below.

- Report Directory (e.g., report/)
    - results_all.csv: Consolidated file containing result_dedupcomp.csv files from each deduplication and compression ratio directory.
    - Deduplication and Compression Ratio Directories (e.g., dedup1_comp1/)
        - graphlist.html: File that displays the graphs of each scenario.
        - result_dedupcomp.csv: Consolidated file containing the test results (result_scenario.csv) of each scenario.
        - Scenario Name Directory (e.g., rand-bs4k-read100/)
            - results.html: Interactive graph summarizing the test results.
            - results.png: Image file of the test result graph.
            - results.csv: CSV file containing the list of test results.
            - results.xlsx: Excel file containing the list of test results and graphs.
            - result_scenario.csv: CSV file that combines the test conditions, cutoff, maximum latency, latency at maximum IOPS, maximum IOPS at maximum latency, and QoS statistics latency show, sysstat -x, and other information in a single line.
            - Scenario Name + Measured IOPS + Measurement Date and Time Directory (e.g., rand-bs4k-read100_iops10000_20230624-232802)
                - All files output by VDBENCH.
                - For NetApp ONTAP
                    - sysstat -x 1
                    - sysstat -M 1
                    - qos statistics latench show
                    - Perfstat
                - result.csv: CSV file that consolidates VDBENCH results, QoS statistics latency show, and sysstat -x results (averages).

### Options

- `start` Subcommand

    Starts the measurement process. Measurements can be suspended using the `suspend` subcommand and checkpoints are saved at key points, allowing for resumption even in the event of unexpected errors.

    | Option | Description | Example |
    |----|----|----|
    | -m, --test-mode | Test mode. The default is automatic mode. <br> auto: Automatic mode. Performs tests while considering the results to determine the next measurement point (IOPS) for smooth graphs. <br> inc: Incremental mode. Starts from a specified initial IOPS and gradually increases the IOPS for testing. <br> file: File mode. Performs tests only for the conditions specified in a CSV file. Typically used for partial retesting or additional measurements. | --test-mode file |
    | -d, --dedup-ratio | List of deduplication ratios for testing. Specifies the extent to which the written data can be deduplicated. Specified in the format of n:1, where n=1 represents complete randomness and n=2 indicates the ability to deduplicate 2 blocks into 1 block. Combined with the -c, --compression-ratio, tests are conducted for all combinations. If this option is specified, it takes precedence over the configuration file. | --dedup-ratio 1 3 5 |
    | -c, --compression-ratio | List of compression ratios for testing. Specifies the extent to which the written data can be compressed. Specified in the format of n:1, where n=1 represents complete randomness and n=2 indicates the ability to compress into 1/2. If this option is specified, it takes precedence over the configuration file. | --compression-ratio 1 3 5 |
    | -f, --test-pattern-file | Specifies the CSV file that contains the conditions for performing tests in file mode. The CSV file should include columns for deduplication ratio, compression ratio, scenario name, and measured IOPS. A sample is provided in [sample/auto_vdbench.csv](sample/auto_vdbench.csv)` | --test-pattern-file auto_vdbench.csv |
    | -r, --report-dir      | Specifies the directory to output the test results. If this option is specified, it takes precedence over the configuration file. | --report-dir report/ |
    | --skip-creating-testfiles | Skips the creation of test files. Used when performing tests with the same deduplication and compression ratios as the previous test to omit the time required for test file creation. The default is False (creates test files). | --skip-creating-testfiles true |
    | --skip-creating-testfiles-at-first | Skips the creation of test files only for the first test. Used when performing multiple tests with different deduplication and compression ratios, but the first test has the same deduplication and compression ratios as the previous test. The default is False. | --skip-creating-testfiles-at-first true |
    | --skip-creating-conffiles | Skips the creation of automatically generated configuration files. Use this option if you want to directly edit the VDBENCH configuration file for testing. The default is False. | --skip-creating-conffiles true |
    | --graph-title | Specifies the title of the generated graph | --graph-title "A800 NFS" |
    | --debug-only | Returns debug measurement results without invoking VDBENCH or the test file creation script. | --debug-only true |

- `stop` Subcommand

    Stops the measurement process immediately. A stopped measurement cannot be resumed.

- `suspend` Subcommand

    Suspends the measurement process. The location where the measurement can be suspended depends on the measurement mode:
    - Automatic mode: By scenario
    - Incremental mode: By scenario
    - File mode: By test (row)

- `resume` Subcommand

    Resumes the measurement process from a suspended state or checkpoint.

- `create-report` Subcommand

    Re-creates the report. Used when partially retesting or excluding specific measurement points by renaming directories.
    
    | Option | Description | Example |
    |----|----|----|
    | -r, --report-dir | Specifies the directory where the test results were output. It can be the root report directory, deduplication and compression ratio directories, or scenario directories. | --report-dir report/dedup1_comp1/rand-bs4k-read100 |
    | --graph-title | Specifies the title of the generated graph list. | --graph-title "A800 NFS" |

- `create-comparison-report` Subcommand

    Creates a comparison graph that consolidates multiple test results into a single graph.
    
    | Option | Description | Example |
    |----|----|----|
    | -r, --report-dir | Specifies multiple directories where the test results were output. It can be the root report directory or deduplication and compression ratio directories. | --report-dir report/A800/dedup1_comp1/ report/C800/dedup1_comp1 |
    | -l, --label | Specifies multiple labels representing each test result. The order and number of labels should match the specified report directories. | --label A800 C800 |
    | -c, --color | Specifies the colors for each test result in the graph. Colors can be specified using CSS color names or in the #RRGGBB format. This option takes precedence over the configuration file. | --color blue red |
    | --graph-title | Specifies the title of the generated graph list. | --graph-title "A800 vs C800 NFS" |

- `init` Subcommand

    Generates configuration files in the `auto_genconf/` directory based on the contents of the configuration file (`conf/auto_vdbench.conf`). The automatically generated configuration files are created each time a test is performed, so this subcommand is usually not necessary. However, it can be used during setup when using helper scripts.

### Configuration File

The `conf/auto_vdbench.conf` file serves as the configuration file, where you can specify the test conditions such as the environment of the load server, deduplication and compression ratios. It is a commented JSON file, where lines starting with `#` are considered as comments. Some options, like deduplication and compression ratios, have the same specifications as command-line options, but the command-line options take precedence.  
(In each configuration value, `${AutoVDB_Home}` can be used to represent the directory where the script is located.)

| Setting Name | Description | Example |
|----|----|----|
| server_list | List of servers to apply the workload to | ["rocky1", "rocky2"] |
| server_threads | Number of load generation threads per server | 512 |
| storage_type | Storage type configuration for obtaining information from the storage side <br> "general": No additional retrieval <br> "NetApp_ONTAP": Retrieves sysstat -x, -M, qos statistics latency show, and perfstat | "NetApp_ONTAP" |
| ontap_cluster_name | Cluster name of ONTAP <br> (Required only when `storage_type` is "NetApp_ONTAP") | "sr-a800" |
| ontap_node_names | Node names of ONTAP <br> (Required only when `storage_type` is "NetApp_ONTAP") | ["sr-a800-01", "sr-a800-02"] |
| ontap_id | User name for logging in to ONTAP <br> (Required only when `storage_type` is "NetApp_ONTAP") | "admin" |
| ontap_passwd | Password for logging in to ONTAP <br> (Required only when `storage_type` is "NetApp_ONTAP") | "Password123" |
| ontap_perfstat_interval | Interval (in minutes) for obtaining Perfstat data. If a value less than 3 is specified, it defaults to 3 <br> (Required only when `storage_type` is "NetApp_ONTAP") | 3 |
| testfile_size | Size of the test files in GB. Specifies the value per server, and the total test file size is the value multiplied by the number of servers | 256 |
| testfile_dir | Directory to create the test files | "/mnt/test" |
| test_duration | Test duration in seconds | 300 |
| test_warmup | Warm-up time before starting the test in seconds | 30 |
| cooldown_wait | Wait time between tests in seconds. Also used as the wait time after creating the test files | 60 |
| max_retry | Maximum number of retries | 3 |
| inc_iops_start | Starting IOPS for incremental | 10000 |
| inc_iops_step | Incremental IOPS per test in incremental mode | 10000 |
| dedup_ratio | List of deduplication ratios to test. Specifies the extent to which the written data can be deduplicated. Specified in n:1 format, where n=1 indicates full randomness and n=2 indicates the ability to deduplicate 2 blocks into 1 block | [1, 3, 5] |
| compression_ratio | List of compression ratios to test. Specifies the extent to which the written data can be compressed. Specified in n:1 format, where n=1 indicates full randomness and n=2 indicates the ability to compress into 1/2. | [1, 3, 5] |
| read_ratio_list | List of read ratios to test. 100 represents 100% read, 0 represents 100% write | [100, 70, 50, 30, 0] |
| random_blocksize_list | List of block sizes (KB) for random access | [4, 8, 16, 32] |
| sequential_blocksize_list | List of block sizes (KB) for sequential access | [32, 64, 128] |
| scenario_list | List of scenarios to measure. If empty, all patterns will be measured | ["rand-bs4k-read100"] |
| scenario_test_result_merge_mode | Specifies whether to rename existing directories or merge the results into existing directories when performing scenario tests. This option is only valid for automatic and incremental modes.<br>"rename": Renames existing directories as `rand-bs4k-read100.001`.<br>"merge": Merges (appends) the test results to the existing directories. | "rename" |
| test_start_script | Path to the script executed at the start of each individual test (at the minimum (each IOPS test) level)<br>It receives the report directory, scenario name, IOPS, and timestamp as arguments | "${AutoVDB_Home}/test_start.sh" |
| test_end_script | Path to the script executed at the end of each individual test (at the minimum (each IOPS test) level)<br>It receives the report directory, scenario name, IOPS, and timestamp as arguments | "${AutoVDB_Home}/test_end.sh" |
| scenario_start_script | Path to the script executed at the start of each scenario test (e.g., rand-bs4k-read100)<br>It receives the report directory and scenario name as arguments | "${AutoVDB_Home}/scenario_test_start.sh" |
| scenario_end_script | Path to the script executed at the end of each scenario test (e.g., rand-bs4k-read100)<br>It receives the report directory and scenario name as arguments | "${AutoVDB_Home}/scenario_test_end.sh" |
| make_testfile_script | Path to the test file creation script. Usually does not require modification | "${AutoVDB_Home}/shell/make_testfile.sh" |
| stop_vdbench_script | Path to the script for stopping VDBENCH. Usually does not require modification | "${AutoVDB_Home}/shell/stop_vdbench.sh" |
| report_dir | Directory to output the reports | "${AutoVDB_Home}/report" |
| auto_min_test_count | Minimum number of tests per scenario when using automatic mode. Increasing this value allows smoother graphs even when latency changes are gradual | 10 |
| auto_max_test_count | Maximum number of tests per scenario when using automatic mode | 20 |
| auto_additional_percent_to_max | Percentage above the maximum value to measure when using automatic mode. (0 means no measurement). This option is used to verify that latency continues to increase even beyond the maximum IOPS. However, not measuring it tends to produce cleaner graphs | 5 |
| auto_min_iops | Lower limit for IOPS in automatic mode | 100 |
| auto_threshold_to_find_min_latency | Percentage of latency change from the previous measurement point below which the latency is considered the minimum when searching for the minimum latency in automatic mode | 5 |
| auto_latency_diff_threshold | If the difference in latency is smaller than this value and meets the minimum number of tests, the test will be terminated early | 20                                                    |
| polyfit_dimensions | Maximum dimensions for polynomial fitting | 10 |
| polyfit_err_threshold | Threshold for the error of polynomial fitting. If the squared error exceeds this value, the polynomial fitting curve will not be displayed in the graph | 100 |
| cutoff_latency | List of cutoff latencies (ms) which is IOPS values beyond these latencies. | [1, 2, 3, 4] |
| graph_default_colors | Default color list for the graphs. Color names can be any valid CSS color name or any value accepted by Plotly, such as #RRGGBB | ["blue", "red", "green", "gold", "purple"] |
| teams_send_message_type | The type of message for notifying Teams. Notifications will only be sent for messages of the specified type. <br> "START": Test start <br> "FINISH": Test finish <br> "SUSPEND": Test suspension <br> "REPORT": Report of test result <br> "INFO": Notifications about test accuracy degradation, etc. <br> "WARNING": Messages requiring attention, such as test failures in specific scenarios that can continue <br> "ERROR": Messages where test continuation is impossible and execution is aborted | ["START", "FINISH", "SUSPEND", "REPORT", "INFO", "WARNING", "ERROR"] |
| slack_send_message_type | The type of message for notifying Slack. Notifications will only be sent for messages of the specified type. <br> "START": Test start <br> "FINISH": Test finish <br> "SUSPEND": Test suspension <br> "REPORT": Report of test result <br> "INFO": Notifications about test accuracy degradation, etc. <br> "WARNING": Messages requiring attention, such as test failures in specific scenarios that can continue <br> "ERROR": Messages where test continuation is impossible and execution is aborted | ["START", "FINISH", "SUSPEND", "REPORT", "INFO", "WARNING", "ERROR"] |
| line_send_message_type | The type of message for notifying LINE. Notifications will only be sent for messages of the specified type. <br> "START": Test start <br> "FINISH": Test finish <br> "SUSPEND": Test suspension <br> "REPORT": Report of test result <br> "INFO": Notifications about test accuracy degradation, etc. <br> "WARNING": Messages requiring attention, such as test failures in specific scenarios that can continue <br> "ERROR": Messages where test continuation is impossible and execution is aborted | ["START", "FINISH", "SUSPEND", "REPORT", "INFO", "WARNING", "ERROR"] |
| teams_incoming_webhook | Teams Incoming Webhook address. When specified, notifications will be sent to the channel after each test scenario is completed. | "https://xxxx.webhook.office.com/webhookb2/" |
| slack_bot_token | Slack's Bot User Token. When specified, notifications will be sent to the channel after each test scenario is completed. | "xoxb-1234567890" |
| slack_channel | The channel for posting messages on Slack. | "#general" |
| line_notify_access_token | LINE Notify's access token. When specified, notifications will be sent to LINE after each test scenario is completed. | "abcdEFGHijklm" |
| uploader_url | When sending notifications to Teams, it is not possible to directly send image files to Teams, so an external uploader needs to be used. This is the URL of the uploader. An uploader that can accept files via POST is required. | "https://xxxx.xxxx/uploader.py" |
| uploader_reference_url | Reference URL for accessing the uploaded files | "https://xxxx.xxxx/" |
| upload_file_prefix | Prefix added to the file name when uploading files | "avdb_" |

## Helper Scripts

The following convenient scripts are provided for use with Auto VDBENCH either called from Auto VDBENCH or used independently.

| Script Name | Description |
|----|----|
| add_hosts.sh *file_name* | Adds the contents of the specified file to the /etc/hosts file on all servers except the server where the script was run. |
| cleanup_failed_log.sh [--dry-run] *target_directory* | Searches the target directory and deletes the directories containing failed test logs. If the --dry-run option is added, it displays the directories to be deleted without actually deleting them. |
| copy_all.sh *file_name* *directory_name* | Copies the specified file to all servers except the server where the script was run. |
| exec_all.sh *command* | Executes the specified command on all servers. |
| export_report.sh [-l summary\|log] *source_directory* *destination_directory* | Copies only specific files from the generated reports to the destination directory. The -l option allows specifying the target files, where "summary" copies HTML, PNG, CSV, and Excel files required for web access (graphlist.html), and "log" includes totals.html, qos statistics latency show, sysstat -x, and sysstat -M outputs in addition to the previous files. The default is "summary". If zip file is specified as the destination, a zip archive is created instead of copying the files. <br> Note that the specified source directory becomes the base. <br> Example: export_report.sh report/a800/ htdocs/ → htdocs/report/a800/dedup1_comp1/graphlist.html |
| make_testfile.sh | Script to create test files on all servers. Normally called from Auto VDBENCH. |
| ontapstats-start.sh | Script to start collecting statistics from ONTAP. Normally called from Auto VDBENCH. |
| ontapstats-stop.sh | Script to stop collecting statistics from ONTAP. Normally called from Auto VDBENCH. |
| set_hostnames.sh | Script to set hostnames on all servers. |
| stop_vdbench.sh | Script to stop (kill) VDBENCH. |

## FAQ

- The latency is too high at the high IOPS area (right side of the graph).

    The load is too heavy for the storage performance. Please decrease the number of threads (server_threads) in the configuration file.

- The latency is too low at the high IOPS area (right side of the graph), and the graph appears flat.

    The load may not be sufficient for the storage performance. Please increase the number of threads (server_threads) in the configuration file. If the latency still does not increase, reconsider the number of servers or the network configuration.

- I received the message "INFO: The lower range of IOPS could not be fully explored; increase auto_min_test_count or increase auto_threshold_to_find_min_latency."

    In automatic mode, the maximum IOPS is initially measured, and then the IOPS is gradually reduced by half until the latency change is below 5%. The above message indicates that the exploration of minimum IOPS ended prematurely due to exceeding the minimum test count. In the scenario where this message is displayed, the left side of the graph may not be sufficiently flat. Increasing the minimum test count (auto_min_test_count) or increasing the threshold to determine minimum latency (auto_threshold_to_find_min_latency) will resolve the issue.

- I received the message "INFO: IOPS changes could not be fully explored; increase auto_max_test_count may provide more details on IOPS changes."

    In automatic mode, measurements are conducted by dividing the section with the largest difference in latency into halves, and more measurements are performed in sections with significant latency changes. If the largest latency difference is within the default threshold of 20ms specified by auto_latency_diff_thresold and exceeds the minimum test count, the test will end there. However, if the largest latency difference still exceeds 20ms even after surpassing the maximum test count (auto_max_test_count), this message will be displayed. In the scenario where this message is displayed, the graph may appear jagged. Increasing the maximum test count (auto_max_test_count) or increasing the latency difference threshold (auto_latency_diff_thresold) will resolve the issue.

- How should I prepare the uploader?

    There is a Python module called [uploadserver](https://pypi.org/project/uploadserver/) that can be used for this purpose, making it the easiest option. You can set it up on a server accessible from the internet, such as a cloud-based server, by following these steps:

    ```
    # pip3 install uploadserver
    # python -m uploadserver --bind (server IP address) 8000
    ```

    In this case, you would configure the settings in the configuration file as follows:

    ```
    # File Uploader Script URL
    # If specified, upload the chart and attach it to the Teams message
    # これを指定するとTeamsへの通知の際にグラフが添付される
    "uploader_url": "http://(public IP of the upload server):8000/upload",

    # File Uploader Reference URL
    # ファイルアップロードサービスの参照URL
    "uploader_reference_url": "http://(public IP address of the upload server):8000/",
    ```

## Author

Shuichi Taketani

## License

The source code is licensed under the [MIT License](docs/LICENSE), and the documentation is licensed under the [CC BY 4.0 License](https://creativecommons.org/licenses/by/4.0/deed.en).
