# IoT Meter Server

Remote monitoring and configuration system for IoT temperature sensors.

## Features
- Remote device configuration
- Temperature data collection
- Web-based management interface
- OTA firmware updates
- AWS deployment

## Installation
```bash
git clone https://github.com/dnyanesh57/iottest.git
cd iot-meter-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python init_db.py