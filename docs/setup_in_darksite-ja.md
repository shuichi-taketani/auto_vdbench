# インターネット接続のないサイトでのAuto VDBENCHのセットアップ

インターネットに接続されていないダークサイトでAuto VDBENCHをセットアップするには以下のように行います。

モジュールをダウンロードするためのホストと実際に実行するダークサイトのホストの2台のホストが必要です。ここでは例としてRocky Linux 9.4を使用します。

## インターネットに接続されたホストでの作業

まず、インターネットに接続されたホストでAuto VDBENCHと必要なモジュールをダウンロードします。

1.  pipをインストールします(rootユーザ)
    ```
    dnf install git python3-pip
    ```

1. Auto VDBENCHをダウンロードします
    ```
    git clone https://github.com/shuichi-taketani/auto_vdbench.git
    ```

1. venvを使用し、Auto VDBENCHを動作させる仮想環境を作成します
    ```
    cd auto_vdbench/
    python -m venv ./python
    source ./python/bin/activate
    ```

1. 必要なモジュールをダウンロードします
    ```
    pip install requests pandas matplotlib openpyxl pymsteams scipy plotly kaleido slack-sdk
    ```

1. 仮想環境をdeactivateします
    ```
    deactivate
    ```

1. 仮想環境をzipなどでアーカイブします
    ```
    cd ..
    zip -r auto_vdbench.zip auto_vdbench/
    ```

## インターネットに接続されていないホストでの作業

作成したアーカイブをUSBメモリ等でダークサイトのホストへ転送します。

1. 転送したzipを展開します
    ```
    unzip auto_vdbench.zip
    ```

1. 展開した仮想環境をactivateします
    ```
    cd auto_vdbench/
    source ./python/bin/activate
    ```

1. Auto VDBENCHを実行します
    ```
    python ./auto_vdbench.py init
    ```