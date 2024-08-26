# Setting Up Auto VDBENCH in a Site without Internet Connection

To set up Auto VDBENCH in an isolated, dark site without an internet connection, follow the steps below.

You will need two hosts: one to download the modules, which has internet access, and the other to actually run Auto VDBENCH at the dark site. For this example, we will use Rocky Linux 9.4.

## Tasks on the Internet-Connected Host

First, on the host with internet access, download Auto VDBENCH and the necessary modules.

1. Install pip as root user
    ```
    dnf install git python3-pip
    ```

1. Download Auto VDBENCH
    ```
    git clone https://github.com/shuichi-taketani/auto_vdbench.git
    ```

1. Use venv to create a virtual environment for running Auto VDBENCH
    ```
    cd auto_vdbench/
    python -m venv ./python
    source ./python/bin/activate
    ```

1. Download the required modules
    ```
    pip install requests pandas matplotlib openpyxl pymsteams scipy plotly kaleido slack-sdk
    ```

1. Deactivate the virtual environment
    ```
    deactivate
    ```

1. Archive the virtual environment using zip or a similar tool
    ```
    cd ..
    zip -r auto_vdbench.zip auto_vdbench/
    ```

## Tasks on the Host without Internet Connection

Transfer the created archive to the dark site's host using a USB drive or similar means.

1. Extract the transferred zip file
    ```
    unzip auto_vdbench.zip
    ```

1. Activate the extracted virtual environment
    ```
    cd auto_vdbench/
    source ./python/bin/activate
    ```

1. Execute Auto VDBENCH
    ```
    python ./auto_vdbench.py init
    ```
