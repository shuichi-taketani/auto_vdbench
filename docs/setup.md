# Setup Example of Auto VDBENCH

Below is a step-by-step setup example for Rocky Linux 8.7 and NetApp ONTAP 9.13.1. In the following instructions, the server primarily used for operations will be referred to as the operation server.

## Storage Setup
-----

1. Set the time zone.

    ```
    sr-a800::> timezone -timezone Asia/Tokyo
    ```

1. Create an aggregate.

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

1. Create vserver

    ```
    sr-a800::> vserver create -vserver svm1_nfs -aggregate aggr1_01 -data-services data-nfs -rootvolume-security-style unix
    ```

1. Verify network ports

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

1. Configure MTU

    ```
    sr-a800::> broadcast-domain modify -broadcast-domain Default-1 -mtu 9000
      (network port broadcast-domain modify)

    Warning: Changing broadcast domain settings will cause a momentary data-serving
             interruption.
    Do you want to continue? {y|n}: y
    ```

1. Create LIFs

    ```
    sr-a800::> net int create -vserver svm1_nfs -lif svm1_nfs_lif01 -service-policy default-data-files -address 192.168.0.101 -netmask 255.255.255.0 -home-node sr-a800-01 -home-port e0e

    sr-a800::> net int create -vserver svm1_nfs -lif svm1_nfs_lif02 -service-policy default-data-files -address 192.168.0.102 -netmask 255.255.255.0 -home-node sr-a800-01 -home-port e0f

    sr-a800::> net int create -vserver svm1_nfs -lif svm1_nfs_lif03 -service-policy default-data-files -address 192.168.0.103 -netmask 255.255.255.0 -home-node sr-a800-01 -home-port e0g

    sr-a800::> net int create -vserver svm1_nfs -lif svm1_nfs_lif04 -service-policy default-data-files -address 192.168.0.104 -netmask 255.255.255.0 -home-node sr-a800-01 -home-port e0h
    ```

1. Create an export-policy

    ```
    sr-a800::> export-policy rule create -policyname default -clientmatch 0.0.0.0/0 -rorule any -rwrule any -allow-suid true -superuser any
    ```

1. Create volumes

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

1. Configure NFS service

    ```
    sr-a800::> nfs create -vserver svm1_nfs -v3 enabled -v4.0 disabled
    ```

1. Enable the diag user (used for perfstat) (optional)

    ```
    sr-a800::> security login password -username diag

    Enter a new password:
    Enter it again:

    sr-a800::> security login unlock -username diag
    ```

1. Increase the maximum number of SSH login sessions

    To collect ONTAP statistics, SSH sessions are used. However, sometimes SSH sessions may not close properly. To ensure uninterrupted collection of statistics, increase the maximum number of SSH connections.

    ```
    sr-a800::> security session limit modify -interface cli -max-active-limit 250 -category *
    3 entries were modified.
    ```

1. Disable RAID Scrub.

    By default, RAID Scrub runs at specific times to check for RAID errors. Although it has minimal impact on performance, disabling it prevents any unintended performance impact.
    
    ```
    sr-a800::> set diag
    sr-a800::*> storage raid-options modify -node * -name raid.scrub.enable -value off
    2 entries were modified.
    ```

## Server Setup
-----

1. Install Python

    ```
    # dnf install python39 python39-pip
    # alternatives --set python /usr/bin/python3.9
    ```

1. Install Auto VDBENCH

    ```
    # git clone https://github.com/shuichi-taketani/auto_vdbench.git
    # pip3 install requests, pandas, openpyxl, pymsteams, scipy, plotly, kaleido
    ```

   Set the PATH (optional)

    ```
    echo 'export PATH=$PATH:/root/auto_vdbench:/root/auto_vdbench/shell' >> /root/.bash_profile
    ```

1. Register the hostnames of the related servers and storage in the /etc/hosts file of the operation server (using rocky1 as an example)

   Write them in a separate file first to add them to other servers' /etc/hosts later.

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

1. Generate an SSH key pair on the operation server

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

1. Copy the public key to other servers for passwordless authentication (don't forget to copy it to the operation server itself as well)

    ```
    # ssh-copy-id -i ~/.ssh/id_rsa.pub root@rocky1
    # ssh-copy-id -i ~/.ssh/id_rsa.pub root@rocky2
    # ssh-copy-id -i ~/.ssh/id_rsa.pub root@rocky3
    …
    ```

1. Register the public key on ONTAP for SSH authentication

   Retrieve the contents of ~/.ssh/id_rsa.pub

    ```
    # cat ~/.ssh/id_rsa.pub 
    ssh-rsa AAAABBBBCCCCDDDDD....ZZZZ root@localhost.localdomain
    ```

   Register the above on ONTAP.

    ```
    sr-a800::> security login create -user-or-group-name admin -application ssh -authentication-method publickey -role admin
    Warning: To use public-key authentication, you must create a public key for user "admin".                                                                       
    ```
    ```
    sr-a800::> security login publickey create -username admin -index 0 -publickey "ssh-rsa AAAABBBBCCCCDDDDD....ZZZZ root@localhost.localdomain"    
    ```

1. List the servers in conf/auto_vdbench.conf as follows:

    ```
    "server_list": ["rocky1", "rocky2", "rocky3", "rocky4", "rocky5", "rocky6", "rocky7", "rocky8"],
    ```

    Run `auto_vdbench.py init` to enable helper scripts.

    ```
    # python auto_vdbench.py init
    ```

1. Set the hostname for all servers

    ```
    # set_hostnames.sh
    ```

1. Add the related hostnames to the /etc/hosts file of servers other than the operation server

    ```
    # add_hosts.sh add_hosts.txt
    ```

1. Set the timezone

    ```
    # exec_all.sh timedatectl set-timezone Asia/Tokyo
    ```
    (exec_all.sh is a helper script that executes the specified command on all servers)

1. Set the MTU of the test NIC to 9000

    ```
    # exec_all.sh "nmcli connection modify ens224 802-3.mtu 9000; systemctl restart NetworkManager"
    ```

1. Disable IPv6

    Disable IPv6 because IPv6 causes frequent error messages about duplicate IPv6 addresses.

    ```
    18:16:56.975 /var/log/messages: May  3 18:16:51 rocky5 kernel: IPv6: ens224: IPv6 duplicate address fe80::cb9e:5333:882d:7c8c used by 00:50:56:84:9f:a7 detected!
    18:16:55.676 /var/log/messages: May  3 18:16:53 rocky3 NetworkManager[1014]: <warn>  [1683105413.1879] ipv6ll[58e949cb1b94e943,ifindex=3]: changed: no IPv6 link local address to retry after Duplicate Address Detection failures (back off)
    ```

    ```
    # exec_all.sh nmcli device modify ens224 ipv6.method "disabled"
    ```
   (This change will revert when the server restarts, so the configuration needs to be reapplied after each restart.)

1. Stop the firewall

    ```
    # exec_all.sh systemctl stop firewalld
    # exec_all.sh systemctl disable firewalld
    ```

1. Mount the volumes

    Edit the /etc/fstab file on each server or create the following script that mounts the target storage volumes on each server.

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

    Create mount directories.

    ```
    # exec_all.sh mkdir -p /mnt/test
    ```

    Mount on all servers.

    ```
    # ./mount_nfs_all.sh
    ```

1. Install VDBENCH on all servers at /usr/local/vdbench
   
    Download VDBENCH from the following link and place it in /root on the operation server. From there, distribute it to /usr/local/vdbench on each server and set the PATH.

    https://www.oracle.com/downloads/server-storage/vdbench-downloads.html

    ```
    # exec_all.sh "dnf install java-1.8.0-openjdk"
    # copy_all.sh vdbench50407.zip /root
    # exec_all.sh "mkdir /usr/local/vdbench; cd /usr/local/vdbench; unzip /root/vdbench50407.zip; rm /root/vdbench50407.zip"
    # exec_all.sh "echo 'export PATH=$PATH:/usr/local/vdbench' >> /root/.bash_profile"
    # source /root/.bash_profile
    ```

1. Install perfstat (optional)
   
    Download Perfstat from the following link to /var/tmp
    https://mysupport.netapp.com/site/tools/tool-eula/5fca36ed72782835c55b81f8

    ```
    # cd /var/tmp
    # tar xfz Perfstat_8.4_Linux.tgz
    # mv /var/tmp/Perfstat_8.4_Linux/Perfstat_8.4_Linux/64-bit/perfstat8 /usr/local/bin
    ```

    To resolve the "libcrypto.so.10 not found" error, add the required OpenSSL-related libraries.

    ```
    # dnf install compat-openssl10-1:1.0.2o-4.el8_6.x86_64
    ```

1. Configure the NetApp ONTAP information in the configuration file

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

1. Configure the test file settings and test duration in the configuration file

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

1. Configure the deduplication and compression ratios

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

1. Define the test scenarios

    ```
    # vi conf/auto_vdbench.conf

    # Read Ratio List
    "read_ratio_list": [100, 70, 50, 30, 0],

    # Ranadom access block size List (KB)
    "random_blocksize_list": [4, 8, 16, 32],

    # Sequential access block size List (KB)
    "sequential_blocksize_list": [32, 64, 128],
    ```

1. Configure Teams integration (optional)
   
    If you want to send notifications to a Teams channel, specify the Incoming Webhook URL for the channel. Refer to the documentation for obtaining the Incoming Webhook URL.

    English: [Create Incoming Webhooks](https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook?tabs=dotnet#create-incoming-webhooks-1)
    Japanese: [受信 Webhook を作成する](https://learn.microsoft.com/ja-jp/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook?tabs=dotnet#create-incoming-webhooks-1)

    Additionally, set up an uploader accessible from the internet and provide its URL to enable attaching graphs to notifications. The [uploadserver](https://pypi.org/project/uploadserver/) can be used as the uploader. For more details, please refer to the FAQ section of README.

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
