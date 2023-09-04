# Auto VDBENCHのセットアップ例

Rocky Linux 8.7とNetApp ONTAP 9.13.1でのステップバイステップのセットアップは以下の通り。尚、以下では主に操作を行うサーバをオペレーションサーバと呼称する。

## ストレージ側のセットアップ
-----

1. タイムゾーンの設定

    ```
    sr-a800::> timezone -timezone Asia/Tokyo
    ```

1. Aggregateの作成

    ```
    sr-a800::> aggr create -aggregate aggr1_01 -node sr-a800-01 -diskcount 23

    Info: The layout for aggregate "aggr1_01" on node "sr-a800-01" would be:

          First Plex

            RAID Group rg0, 23 disks (block checksum, raid_dp)
                                                                Usable Physical
              Position   Disk                      Type           Size     Size
              ---------- ------------------------- ---------- -------- --------
              shared     1.0.24                    SSD-NVM           -        -
              shared     1.0.25                    SSD-NVM           -        -
              shared     1.0.26                    SSD-NVM     882.4GB  882.4GB
              shared     1.0.30                    SSD-NVM     882.4GB  882.4GB
              shared     1.0.31                    SSD-NVM     882.4GB  882.4GB
              shared     1.0.32                    SSD-NVM     882.4GB  882.4GB
              shared     1.0.36                    SSD-NVM     882.4GB  882.4GB
              shared     1.0.37                    SSD-NVM     882.4GB  882.4GB
              shared     1.0.38                    SSD-NVM     882.4GB  882.4GB
              shared     1.0.42                    SSD-NVM     882.4GB  882.4GB
              shared     1.0.0                     SSD-NVM     882.4GB  882.4GB
              shared     1.0.2                     SSD-NVM     882.4GB  882.4GB
              shared     1.0.5                     SSD-NVM     882.4GB  882.4GB
              shared     1.0.6                     SSD-NVM     882.4GB  882.4GB
              shared     1.0.7                     SSD-NVM     882.4GB  882.4GB
              shared     1.0.8                     SSD-NVM     882.4GB  882.4GB
              shared     1.0.12                    SSD-NVM     882.4GB  882.4GB
              shared     1.0.13                    SSD-NVM     882.4GB  882.4GB
              shared     1.0.14                    SSD-NVM     882.4GB  882.4GB
              shared     1.0.18                    SSD-NVM     882.4GB  882.4GB
              shared     1.0.19                    SSD-NVM     882.4GB  882.4GB
              shared     1.0.20                    SSD-NVM     882.4GB  882.4GB
              shared     1.0.43                    SSD-NVM     882.4GB  882.4GB

          Aggregate capacity available for volume use would be 16.29TB.

    Do you want to continue? {y|n}: y
    [Job 40] Job succeeded: DONE
    ```

1. vserverの作成

    ```
    sr-a800::> vserver create -vserver svm1_nfs -aggregate aggr1_01 -data-services data-nfs -rootvolume-security-style unix
    ```

1. network portの確認

    ```
    sr-a800::> net port show
      (network port show)

    Node: sr-a800-01
                                                      Speed(Mbps) Health
    Port      IPspace      Broadcast Domain Link MTU  Admin/Oper  Status
    --------- ------------ ---------------- ---- ---- ----------- --------
    e0M       Default      Default          up   1500  auto/1000  healthy
    e0e       Default      Default-1        up   9000  auto/25000 healthy
    e0f       Default      Default-1        up   9000  auto/25000 healthy
    e0g       Default      Default-1        up   9000  auto/25000 healthy
    e0h       Default      Default-1        up   9000  auto/25000 healthy
    e3a       Cluster      Cluster          up   9000  auto/100000
                                                                  healthy
    e3b       Cluster      Cluster          up   9000  auto/100000
                                                                  healthy

    Node: sr-a800-02
                                                      Speed(Mbps) Health
    Port      IPspace      Broadcast Domain Link MTU  Admin/Oper  Status
    --------- ------------ ---------------- ---- ---- ----------- --------
    e0M       Default      Default          up   1500  auto/1000  healthy
    e0e       Default      Default-1        up   9000  auto/25000 healthy
    e0f       Default      Default-1        up   9000  auto/25000 healthy
    e0g       Default      Default-1        up   9000  auto/25000 healthy
    e0h       Default      Default-1        up   9000  auto/25000 healthy
    e3a       Cluster      Cluster          up   9000  auto/100000
                                                                  healthy
    e3b       Cluster      Cluster          up   9000  auto/100000
                                                                  healthy
    14 entries were displayed.
    ```

1. MTUの設定

    ```
    sr-a800::> broadcast-domain modify -broadcast-domain Default-1 -mtu 9000
      (network port broadcast-domain modify)

    Warning: Changing broadcast domain settings will cause a momentary data-serving
             interruption.
    Do you want to continue? {y|n}: y
    ```

1. LIFの作成

    ```
    sr-a800::> net int create -vserver svm1_nfs -lif svm1_nfs_lif01 -service-policy default-data-files -address 192.168.0.101 -netmask 255.255.255.0 -home-node sr-a800-01 -home-port e0e

    sr-a800::> net int create -vserver svm1_nfs -lif svm1_nfs_lif02 -service-policy default-data-files -address 192.168.0.102 -netmask 255.255.255.0 -home-node sr-a800-01 -home-port e0f

    sr-a800::> net int create -vserver svm1_nfs -lif svm1_nfs_lif03 -service-policy default-data-files -address 192.168.0.103 -netmask 255.255.255.0 -home-node sr-a800-01 -home-port e0g

    sr-a800::> net int create -vserver svm1_nfs -lif svm1_nfs_lif04 -service-policy default-data-files -address 192.168.0.104 -netmask 255.255.255.0 -home-node sr-a800-01 -home-port e0h
    ```

1. export-policyの作成

    ```
    sr-a800::> export-policy rule create -policyname default -clientmatch 0.0.0.0/0 -rorule any -rwrule any -allow-suid true -superuser any
    ```

1. volumeの作成

    ```
    sr-a800::> vol create -vserver svm1_nfs -size 568g -aggregate aggr1_01 -snapshot-policy none -percent-snapshot-space 0 -security-style unix -unix-permissions 777 -volume vol1 -junction-path /vol1

    sr-a800::> vol create -vserver svm1_nfs -size 568g -aggregate aggr1_01 -snapshot-policy none -percent-snapshot-space 0 -security-style unix -unix-permissions 777 -volume vol2 -junction-path /vol2

    sr-a800::> vol create -vserver svm1_nfs -size 568g -aggregate aggr1_01 -snapshot-policy none -percent-snapshot-space 0 -security-style unix -unix-permissions 777 -volume vol3 -junction-path /vol3

    sr-a800::> vol create -vserver svm1_nfs -size 568g -aggregate aggr1_01 -snapshot-policy none -percent-snapshot-space 0 -security-style unix -unix-permissions 777 -volume vol4 -junction-path /vol4

    sr-a800::> vol create -vserver svm1_nfs -size 568g -aggregate aggr1_01 -snapshot-policy none -percent-snapshot-space 0 -security-style unix -unix-permissions 777 -volume vol5 -junction-path /vol5

    sr-a800::> vol create -vserver svm1_nfs -size 568g -aggregate aggr1_01 -snapshot-policy none -percent-snapshot-space 0 -security-style unix -unix-permissions 777 -volume vol6 -junction-path /vol6

    sr-a800::> vol create -vserver svm1_nfs -size 568g -aggregate aggr1_01 -snapshot-policy none -percent-snapshot-space 0 -security-style unix -unix-permissions 777 -volume vol7 -junction-path /vol7

    sr-a800::> vol create -vserver svm1_nfs -size 568g -aggregate aggr1_01 -snapshot-policy none -percent-snapshot-space 0 -security-style unix -unix-permissions 777 -volume vol8 -junction-path /vol8
    ```

1. NFSサービスの作成

    ```
    sr-a800::> nfs create -vserver svm1_nfs -v3 enabled -v4.0 disabled
    ```

1. ONTAPに公開鍵認証でログインできるよう公開鍵を登録

    ~/.ssh/id_rsa.pubの内容を取得。
    (上記のファイルが存在しない場合は、「サーバ側のセットアップ」にあるssh-keygenの手順を参照して作成すること)

    ```
    # cat ~/.ssh/id_rsa.pub 
    ssh-rsa AAAABBBBCCCCDDDDD....ZZZZ root@localhost.localdomain
    ```

    上記をONTAPへ登録。

    ```
    sr-a800::> security login create -user-or-group-name admin -application ssh -authentication-method publickey -role admin
    Warning: To use public-key authentication, you must create a public key for user "admin".                                                                       
    ```
    ```
    sr-a800::> security login publickey create -username admin -index 0 -publickey "ssh-rsa AAAABBBBCCCCDDDDD....ZZZZ root@localhost.localdomain"    
    ```

1. diagユーザの有効化 (perfstatで使用) (オプション)

    ```
    sr-a800::> security login password -username diag

    Enter a new password:
    Enter it again:

    sr-a800::> security login unlock -username diag
    ```

1. SSHログインセッション数を最大まで増加

    ONTAPの統計情報を取得するためにsshセッションを使用するが、sshセッションがうまくクローズできないことがある。このようなケースでもできるだけ統計情報の取得が続けられるようsshコネクション数を最大まで増やしておく。

    ```
    sr-a800::> security session limit modify -interface cli -max-active-limit 250 -category *
    3 entries were modified.
    ```

1. RAID Scrubの無効化

    デフォルトでは特定の時刻にRAIDのエラーをチェックするRAID Scrubが走るようになっている。パフォーマンスへの影響は小さいが、意図しないパフォーマンスへの影響を防ぐためこれをオフにする。

    ```
    sr-a800::> set diag
    sr-a800::*> storage raid-options modify -node * -name raid.scrub.enable -value off
    2 entries were modified.
    ```

## サーバ側のセットアップ
-----

1. pythonのインストール

    ```
    # dnf install python39 python39-pip
    # alternatives --set python /usr/bin/python3.9
    ```

1. Auto VDBENCHのインストール

    ```
    # git clone https://github.com/shuichi-taketani/auto_vdbench.git
    # pip3 install requests, pandas, openpyxl, pymsteams, scipy, plotly, kaleido, slack-sdk
    ```

    パスを通す(オプション)

    ```
    echo 'export PATH=$PATH:/root/auto_vdbench:/root/auto_vdbench/shell' >> /root/.bash_profile
    ```

1. オペレーションサーバ(ここでは例としてrocky1を使用)の/etc/hostsに関連するサーバとストレージのホスト名を登録

    後で他のサーバの/etc/hostsに追加するため、一度別ファイルに記載してから追加する。

    ```
    # vi add_hosts.txt
    192.168.0.11 rocky1
    192.168.0.12 rocky2
    192.168.0.13 rocky3
    192.168.0.14 rocky4
    192.168.0.15 rocky5
    192.168.0.16 rocky6
    192.168.0.17 rocky7
    192.168.0.18 rocky8
    192.168.0.20 sr-a800
    192.168.0.101 sr-a800-svm1_nfs-01
    192.168.0.102 sr-a800-svm1_nfs-02
    192.168.0.103 sr-a800-svm1_nfs-03
    192.168.0.104 sr-a800-svm1_nfs-04

    # cat add_hosts.txt >> /etc/hosts
    ```

1. オペレーションサーバでssh公開鍵を作成

    ```
    # ssh-keygen
    Generating public/private rsa key pair.
    Enter file in which to save the key (/root/.ssh/id_rsa):
    Enter passphrase (empty for no passphrase):
    Enter same passphrase again:
    Your identification has been saved in /root/.ssh/id_rsa.
    Your public key has been saved in /root/.ssh/id_rsa.pub.
    The key fingerprint is:
    SHA256:fkmk8mWjRCQBZmuclAgjd6V9BQOAQCCqk2nOClxb+z0 root@localhost.localdomain
    The key's randomart image is:
    +---[RSA 3072]----+
    |X+.oB==o+..      |
    |+oo*.= o o       |
    |.   * . o .      |
    |.o .   o o       |
    |=. . .. S =      |
    |=.. o .= = o     |
    |.+ . .  + o      |
    |o     . .E       |
    |.      . ..      |
    +----[SHA256]-----+
    ```

1. 他のサーバへ公開鍵認証でログインできるよう公開鍵をコピー(自分自身へのコピーも忘れないこと)

    ```
    # ssh-copy-id -i ~/.ssh/id_rsa.pub root@rocky1
    # ssh-copy-id -i ~/.ssh/id_rsa.pub root@rocky2
    # ssh-copy-id -i ~/.ssh/id_rsa.pub root@rocky3
    …
    ```

1. 以下のようにconf/auto_vdbench.confにサーバの一覧を記載

    ```
    "server_list": ["rocky1", "rocky2", "rocky3", "rocky4", "rocky5", "rocky6", "rocky7", "rocky8"],
    ```

    ヘルパースクリプトが使えるよう、`auto_vdbench.py init`を実行

    ```
    # python auto_vdbench.py init
    ```

1. 全てのサーバに対してホスト名を設定

    ```
    # set_hostnames.sh
    ```

1. オペレーションサーバ以外のサーバの/etc/hostsに関連するホスト名を追加

    ```
    # add_hosts.sh add_hosts.txt
    ```

1. timezoneを設定

    ```
    # exec_all.sh timedatectl set-timezone Asia/Tokyo
    ```
    (exec_all.shは指定されたコマンドを全サーバで実行するヘルパースクリプト)

1. テスト用NICのMTUを9000に設定

    ```
    # exec_all.sh "nmcli connection modify ens224 802-3.mtu 9000; systemctl restart NetworkManager"
    ```

1. IPv6を無効化

    IPv6が有効になっていると、IPv6アドレスがduplicateしているというエラーメッセージ(以下)が頻繁に出るためIPv6を無効にする

    ```
    18:16:56.975 /var/log/messages: May  3 18:16:51 rocky5 kernel: IPv6: ens224: IPv6 duplicate address fe80::cb9e:5333:882d:7c8c used by 00:50:56:84:9f:a7 detected!
    18:16:55.676 /var/log/messages: May  3 18:16:53 rocky3 NetworkManager[1014]: <warn>  [1683105413.1879] ipv6ll[58e949cb1b94e943,ifindex=3]: changed: no IPv6 link local address to retry after Duplicate Address Detection failures (back off)
    ```

    ```
    # exec_all.sh nmcli device modify ens224 ipv6.method "disabled"
    ```
    (この変更はサーバを再起動すると元に戻るため、再起動の度に再設定が必要)

1. firewallを停止

    ```
    # exec_all.sh systemctl stop firewalld
    # exec_all.sh systemctl disable firewalld
    ```

1. マウント

    各サーバの/etc/fstabを編集あるいは以下のようなスクリプトを作成し、各サーバで対象ストレージのボリュームをマウントするよう設定する。

    ```
    # vi mount_all.sh
    MOUNT_OPT="-t nfs -o rsize=1048576,wsize=1048576,timeo=600,retrans=2"

    ssh root@rocky1 "mount $MOUNT_OPT sr-a800-svm1_nfs-01:/vol1 /mnt/test"
    ssh root@rocky2 "mount $MOUNT_OPT sr-a800-svm1_nfs-02:/vol2 /mnt/test"
    ssh root@rocky3 "mount $MOUNT_OPT sr-a800-svm1_nfs-03:/vol3 /mnt/test"
    ssh root@rocky4 "mount $MOUNT_OPT sr-a800-svm1_nfs-04:/vol4 /mnt/test"
    ssh root@rocky5 "mount $MOUNT_OPT sr-a800-svm1_nfs-01:/vol5 /mnt/test"
    ssh root@rocky6 "mount $MOUNT_OPT sr-a800-svm1_nfs-02:/vol6 /mnt/test"
    ssh root@rocky7 "mount $MOUNT_OPT sr-a800-svm1_nfs-03:/vol7 /mnt/test"
    ssh root@rocky8 "mount $MOUNT_OPT sr-a800-svm1_nfs-04:/vol8 /mnt/test"
    ```

    マウントディレクトリを作成

    ```
    # exec_all.sh mkdir -p /mnt/test
    ```

    全サーバでマウント

    ```
    # ./mount_nfs_all.sh
    ```

1. VDBENCHを全サーバの/usr/local/vdbenchへインストール

    VDBENCHを以下からダウンロードし、オペレーションサーバの/rootへ配置。そこから各サーバの/usr/local/vdbenchへ配置し、パスを通す。
    https://www.oracle.com/downloads/server-storage/vdbench-downloads.html

    ```
    # exec_all.sh "dnf install java-1.8.0-openjdk"
    # copy_all.sh vdbench50407.zip /root
    # exec_all.sh "mkdir /usr/local/vdbench; cd /usr/local/vdbench; unzip /root/vdbench50407.zip; rm /root/vdbench50407.zip"
    # exec_all.sh "echo 'export PATH=$PATH:/usr/local/vdbench' >> /root/.bash_profile"
    # source /root/.bash_profile
    ```

1. perfstatのインストール (オプション)

    Perfstatを以下からダウンロードし、/var/tmpへ配置。
    
    https://mysupport.netapp.com/site/tools/tool-eula/5fca36ed72782835c55b81f8

    ```
    # cd /var/tmp
    # tar xfz Perfstat_8.4_Linux.tgz
    # mv /var/tmp/Perfstat_8.4_Linux/Perfstat_8.4_Linux/64-bit/perfstat8 /usr/local/bin
    ```

    そのままでは、「libcrypto.so.10がない」というエラーが出るため、OpenSSL関連のライブラリを追加する。

    ```
    # dnf install compat-openssl10-1:1.0.2o-4.el8_6.x86_64
    ```

1. NetApp ONTAPの情報を設定ファイルに記載

    ```
    # vi conf/auto_vdbench.conf

    # Storage Type
    # For getting additional statistics on the storage side
    # ("general": no additionaal statistics,
    #  "NetApp_ONTAP": sysstat -x, -M, qos statistics latency show, perfstat)
    # ストレージ側の情報を取得するためのストレージタイプの設定
    # ("general": 追加取得なし
    #  "NetApp_ONTAP": sysstat -x, -M, qos statistics latency show, perfstatを取得)
    "storage_type": "NetApp_ONTAP",

    # ONTAP Cluster Name
    "ontap_cluster_name": "sr-a800",

    # ONTAP Node Names
    "ontap_node_names": ["sr-a800-01", "sr-a800-02"],

    # ONTAP Login ID
    "ontap_id": "admin",

    # ONTAP Login Password
    "ontap_passwd": "Password123",

    # ONTAP Perfstat Interval (min)
    "ontap_perfstat_interval": 1,
    ```

1. テストファイルの設定やテスト時間を設定ファイルに記載

    ```
    # vi conf/auto_vdbench.conf

    # Test file size (GB)
    "testfile_size": 256,

    # Test file directory,
    "testfile_dir": "/mnt/test",

    # Test duration (sec)
    # テスト時間(秒)
    "test_duration": 300,
    ```

1. 重複排除可能率と圧縮可能率の設定

    ```
    # vi conf/auto_vdbench.conf

    # Dedup Ratio (N:1)
    # "1" means that dedup is not possible
    # "1"は重複排除ができない(ランダム)であることを意味します
    "dedup_ratio": [1, 3, 5],

    # Compressiom Ratio (N:1)
    # "1" means that compression is not possible
    # "1"は圧縮ができない(ランダム)であることを意味します
    "compression_ratio": [1, 3, 5],
    ```

1. テストシナリオの定義

    ```
    # vi conf/auto_vdbench.conf

    # Read Ratio List
    "read_ratio_list": [100, 70, 50, 30, 0],

    # Ranadom access block size List (KB)
    "random_blocksize_list": [4, 8, 16, 32],

    # Sequential access block size List (KB)
    "sequential_blocksize_list": [32, 64, 128],
    ```

1. Teams関連の設定 (オプション)

    Teamsのチャネルへ通知を行う場合、チャネルのIncoming Webhook URLを指定する。Incoming Webhook URLの取得の方法は以下を参照。

    英語: [Create Incoming Webhooks](https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook?tabs=dotnet#create-incoming-webhooks-1)
    日本語: [受信 Webhook を作成する](https://learn.microsoft.com/ja-jp/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook?tabs=dotnet#create-incoming-webhooks-1)

    また、アップローダをインターネットからアクセス可能な場所に設置し、そのURLを記載することで、通知にグラフを添付することが可能。アップローダは[uploadserver](https://pypi.org/project/uploadserver/)を使用可能。詳しくはREADMEのFAQを参照。

    ```
    # vi conf/auto_vdbench.conf

    # Teams Incoming Webhook URL
    # If specified, you will be notified when each test scenario is completed.
    # これを指定すると1つのテストシナリオが終了するごとに通知が行われる
    "teams_incoming_webhook": "https://xxxx.webhook.office.com/webhookb2/xxxx",

    # File Uploader Script URL
    # If specified, upload the chart and attach it to Teams message
    # これを指定するとTeamsへの通知の際にグラフが添付される
    "uploader_url": "https://xxxx.xxxx/uploader/uploader.py",

    # File Uploader Reference URL
    # ファイルアップロードサービスの参照URL
    "uploader_reference_url": "https://xxxx.xxxx/uploader/",
    ```

1. Slack関連の設定 (オプション)

    Slackのチャネルへ通知を行う場合、以下の手順でSlackでトークンを発行する。

    1. 以下のURLをクリックし、対象のワークスペースを選択して新しいアプリ(App Manifest)を作成する<br>
    [Slackで新しいアプリを作成](https://api.slack.com/apps?new_app=1&manifest_yaml=_metadata%3A%0A++major_version%3A+1%0A++minor_version%3A+1%0Adisplay_information%3A%0D%0A++name%3A+Auto_VDBENCH%0D%0Afeatures%3A%0D%0A++app_home%3A%0D%0A++++home_tab_enabled%3A+false%0D%0A++++messages_tab_enabled%3A+true%0D%0A++++messages_tab_read_only_enabled%3A+false%0D%0A++bot_user%3A%0D%0A++++display_name%3A+Auto+VDBENCH+Bot%0D%0A++++always_online%3A+true%0D%0Aoauth_config%3A%0D%0A++scopes%3A%0D%0A++++bot%3A%0D%0A++++++-+chat%3Awrite%0D%0A++++++-+chat%3Awrite.customize%0D%0A++++++-+chat%3Awrite.public%0D%0A++++++-+files%3Awrite%0D%0A++++++-+files%3Aread%0D%0Asettings%3A%0D%0A++org_deploy_enabled%3A+false%0D%0A++socket_mode_enabled%3A+false%0D%0A++token_rotation_enabled%3A+false%0D%0A)
    1. 「Install to Workspace」ボタンを押し、Slackワークスペースにインストールする
    1. 権限を確認する画面が出るので、「許可する」をクリック
    1. 左側のメニューから「OAuth & Permissions」を選び、「Bot User OAuth Token」に表示されているxoxb-で始まるトークンをコピーする
    1. コピーしたトークンを設定ファイルの`slack_bot_token`に指定
    1. 投稿するチャネル名を設定ファイルの`slack_channel`に指定

    <br>

1. LINE Notify関連の設定 (オプション)

    LINEへ通知を行う場合、以下のマイページから開発者向けLINE Notifyのアクセストークンを発行しそれを指定する。

    英語: [LINE Notify](https://notify-bot.line.me/en/)
    日本語: [LINE Notify](https://notify-bot.line.me/ja/)

    LINE Notifyの場合、テスト結果のグラフ(画像)が添付される。アップローダーを設定した場合、HTMLへのリンクがメッセージに付加される。
