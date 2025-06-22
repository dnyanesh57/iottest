
**7. startup.sh** (Boot Script)
```bash
#!/bin/bash
# Startup script for IoT Meter Server

cd /opt/iot-meter-server
source venv/bin/activate

# Start application service
sudo systemctl start iot-meter

# Start Nginx
sudo systemctl restart nginx

echo "IoT Meter Server started successfully"