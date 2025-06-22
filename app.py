import os
import sqlite3
import datetime
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)
DATABASE = '/opt/iot-meter-server/meters.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS meters
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  meter_id TEXT UNIQUE,
                  ssid TEXT,
                  password TEXT,
                  server_url TEXT,
                  sample_interval INTEGER,
                  last_seen TIMESTAMP)''')
    conn.commit()
    conn.close()

@app.route('/configure', methods=['POST'])
def configure_meter():
    data = request.json
    required = ['meter_id', 'ssid', 'password', 'server_url', 'sample_interval']
    
    if not all(field in data for field in required):
        return jsonify({"error": "Missing parameters"}), 400
        
    if data['sample_interval'] < 10:
        return jsonify({"error": "Interval must be >= 10 seconds"}), 400
        
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('''INSERT OR REPLACE INTO meters 
                     (meter_id, ssid, password, server_url, sample_interval, last_seen)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (data['meter_id'],
                   data['ssid'],
                   data['password'],
                   data['server_url'],
                   data['sample_interval'],
                   datetime.datetime.now()))
        
        conn.commit()
        return jsonify({
            "status": "success",
            "message": "Configuration updated",
            "meter_id": data['meter_id']
        })
    
    except sqlite3.Error as e:
        return jsonify({"error": str(e)}), 500
    
    finally:
        conn.close()

@app.route('/get_config/<meter_id>', methods=['GET'])
def get_config(meter_id):
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM meters WHERE meter_id = ?", (meter_id,))
        config = c.fetchone()
        
        if config:
            return jsonify({
                "ssid": config['ssid'],
                "password": config['password'],
                "server_url": config['server_url'],
                "sample_interval": config['sample_interval']
            })
        else:
            return jsonify({"error": "Meter not configured"}), 404
    
    finally:
        conn.close()

@app.route('/upload', methods=['POST'])
def upload_data():
    data = request.json
    required = ['meter_id', 'sensor_id', 'data']
    
    if not all(field in data for field in required):
        return jsonify({"error": "Missing parameters"}), 400
        
    # Check if meter is configured
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT 1 FROM meters WHERE meter_id = ?", (data['meter_id'],))
        
        if not c.fetchone():
            return jsonify({"status": "config_required"}), 400
        
        # Save data to file
        save_data(data)
        
        # Update last seen timestamp
        c.execute("UPDATE meters SET last_seen = ? WHERE meter_id = ?", 
                  (datetime.datetime.now(), data['meter_id']))
        conn.commit()
        
        return jsonify({"status": "success"})
    
    finally:
        conn.close()

def save_data(data):
    # Create directory if not exists
    os.makedirs('meter_data', exist_ok=True)
    
    # Generate filename
    filename = f"meter_data/{data['meter_id']}_{data['sensor_id']}.csv"
    
    # Write header if file doesn't exist
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            f.write("timestamp,serial_number,datetime,status,temperature,battery_adc\n")
    
    # Write data to file
    with open(filename, 'a') as f:
        parts = data['data'].split()
        if len(parts) >= 5:
            f.write(f"{datetime.datetime.now().isoformat()},")
            f.write(f"{parts[0]},{parts[1]} {parts[2]},")
            f.write(f"{parts[3]},{parts[4]},{parts[5]}\n")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/meters')
def list_meters():
    conn = get_db_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM meters ORDER BY last_seen DESC")
        meters = c.fetchall()
        return render_template('meters.html', meters=meters)
    finally:
        conn.close()

@app.route('/configure_meter', methods=['GET', 'POST'])
def configure_meter_ui():
    if request.method == 'POST':
        data = {
            'meter_id': request.form['meter_id'],
            'ssid': request.form['ssid'],
            'password': request.form['password'],
            'server_url': request.form['server_url'],
            'sample_interval': int(request.form['sample_interval'])
        }
        response = configure_meter().get_json()
        return render_template('configure.html', result=response)
    
    meter_id = request.args.get('meter_id', '')
    return render_template('configure.html', meter_id=meter_id)

@app.route('/meter_data/<meter_id>')
def view_meter_data(meter_id):
    data_files = []
    for file in os.listdir('meter_data'):
        if file.startswith(meter_id) and file.endswith('.csv'):
            file_path = os.path.join('meter_data', file)
            data_files.append({
                'filename': file,
                'size': os.path.getsize(file_path),
                'modified': datetime.datetime.fromtimestamp(
                    os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
            })
    
    return render_template('meter_data.html', 
                          meter_id=meter_id, 
                          data_files=data_files)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory('meter_data', filename, as_attachment=True)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000)