from flask import Flask, render_template_string, jsonify, send_from_directory, request, redirect, url_for, session
from flask_cors import CORS
import subprocess
import signal
import psutil
import os
import time
import logging
import csv
import json
import atexit
from functools import wraps

app = Flask(__name__, static_folder='build/web')
CORS(app)  # Enable CORS for all routes. 
app.secret_key = 'your_secret_key_here'  # Add this line for session management
processes = {}

# File to store process status
PROCESS_STATUS_FILE = 'process_status.json'

def load_scripts():
    with open('save_video_config.txt', 'r') as f:
        return [line.strip() for line in f if line.strip()]

def extract_camera_name_from_line(script):
    parts = script.split('--camera_name')
    if len(parts) > 1:
        return parts[1].split()[0].strip('"')
    return "Unknown"

def load_users():
    users = {}
    with open('users.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            users[row[0]] = row[1]
    return users

def save_process_status():
    """Save current process status to file"""
    status_data = {}
    for camera_name, process_info in processes.items():
        if process_info['process'].poll() is None:  # Process is still running
            status_data[camera_name] = {
                'pid': process_info['process'].pid,
                'start_time': process_info['start_time'],
                'script_command': process_info.get('script_command', '')
            }
    
    try:
        with open(PROCESS_STATUS_FILE, 'w') as f:
            json.dump(status_data, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to save process status: {e}")

def load_process_status():
    """Load process status from file and restart processes if needed"""
    if not os.path.exists(PROCESS_STATUS_FILE):
        return
    
    try:
        with open(PROCESS_STATUS_FILE, 'r') as f:
            status_data = json.load(f)
        
        scripts = load_scripts()
        script_map = {extract_camera_name_from_line(script): script for script in scripts}
        
        for camera_name, process_info in status_data.items():
            # Check if the process is still running by PID
            try:
                psutil.Process(process_info['pid'])
                # Process exists, but we need to recreate the subprocess object
                # Since we can't recreate the actual subprocess, we'll mark it as running
                # but the status check will show it's not managed by this server
                logging.info(f"Process {camera_name} (PID: {process_info['pid']}) is still running but not managed by this server")
            except psutil.NoSuchProcess:
                # Process is not running, restart it if we have the script command
                if camera_name in script_map:
                    logging.info(f"Restarting process for camera: {camera_name}")
                    script_command = script_map[camera_name]
                    process = subprocess.Popen(script_command, shell=True, executable='/bin/bash')
                    processes[camera_name] = {
                        'process': process, 
                        'start_time': time.time(),
                        'script_command': script_command
                    }
                    logging.info(f"Restarted process for {camera_name} with PID: {process.pid}")
                else:
                    logging.warning(f"No script found for camera: {camera_name}")
                    
    except Exception as e:
        logging.error(f"Failed to load process status: {e}")

def cleanup_on_exit():
    """Cleanup function to save status before exit"""
    save_process_status()

# Register cleanup function
atexit.register(cleanup_on_exit)

# Load process status on startup
load_process_status()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        if username in users and users[username] == password:
            session['logged_in'] = True
            return redirect(url_for('serve'))
        else:
            return render_template_string('''
                <div style="text-align: center; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);">
                    <h1>Invalid credentials</h1>
                    <a href="{{ url_for('login') }}">Try again</a>
                </div>
            ''')
    return render_template_string('''
        <div style="text-align: center; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);">
            <h1>Login</h1>
            <form method="post">
                <input type="text" name="username" placeholder="Username" required style="margin-bottom: 10px;"><br>
                <input type="password" name="password" placeholder="Password" required style="margin-bottom: 10px;"><br>
                <input type="submit" value="Login">
            </form>
        </div>
    ''')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/camera_names', methods=['GET'])
@login_required
def get_camera_names():
    scripts = load_scripts()
    camera_names = [extract_camera_name_from_line(script) for script in scripts]
    return jsonify(camera_names)
  
@app.route('/')
@login_required
def serve():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
@login_required
def static_proxy(path):
    # send_static_file will guess the correct MIME type
    return send_from_directory(app.static_folder, path)
  
@app.route('/start/<camera_name>', methods=['POST'])
@login_required
def start_script(camera_name):
    global processes
    scripts = load_scripts()
    script_command = next((script for script in scripts if extract_camera_name_from_line(script) == camera_name), None)

    if not script_command:
        return jsonify({"status": "error", "message": "Invalid camera name"})

    if camera_name not in processes or processes[camera_name]['process'].poll() is not None:
        process = subprocess.Popen(script_command, shell=True, executable='/bin/bash')
        processes[camera_name] = {
            'process': process, 
            'start_time': time.time(),
            'script_command': script_command
        }
        save_process_status()  # Save status after starting
        return jsonify({"status": "started", "pid": process.pid})
    else:
        return jsonify({"status": "already running", "pid": processes[camera_name]['process'].pid})

@app.route('/stop/<camera_name>', methods=['POST'])
@login_required
def stop_script(camera_name):
    global processes
    if camera_name in processes and processes[camera_name]['process'].poll() is None:
        try:
            parent_pid = processes[camera_name]['process'].pid
            parent = psutil.Process(parent_pid)
            
            for child in parent.children(recursive=True):
                child.kill()
            
            parent.kill()
            
            save_process_status()  # Save status after stopping
            return jsonify({"status": "forcefully stopped", "pid": parent_pid})
        except psutil.NoSuchProcess:
            return jsonify({"status": "error", "message": "Process does not exist"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})
    else:
        return jsonify({"status": "NOT running"})

@app.route('/status/<camera_name>', methods=['GET'])
@login_required
def status(camera_name):
    if camera_name in processes and processes[camera_name]['process'].poll() is None:
        log_file = f"{camera_name}.txt"
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as file:
                lines = file.readlines()
                last_ten_lines = lines[-10:] if len(lines) >= 10 else lines
                last_ten_text = ' '.join(last_ten_lines)
        else:
            last_ten_text = "No log file found."
        
        return jsonify({"status": "running", "pid": processes[camera_name]['process'].pid, "log": last_ten_text})
    else:
        return jsonify({"status": "NOT running"})

@app.route('/duration/<camera_name>', methods=['GET'])
@login_required
def duration(camera_name):
    if camera_name in processes and processes[camera_name]['process'].poll() is None:
        start_time = processes[camera_name]['start_time']
        running_duration = time.time() - start_time
        return jsonify({"status": "running", "duration": running_duration})
    else:
        return jsonify({"status": "NOT running", "duration": 0})

from flask import request, jsonify
from datetime import datetime
import os
from concurrent.futures import ThreadPoolExecutor
import logging
import fnmatch

#To test
#curl -X GET "http://192.168.dev.ip:8000/list_files?page=1&limit=20"
@app.route('/list_files', methods=['GET'])
@login_required
def list_files():
    directory = './video_records'
    filter_query = request.args.get('filter', '')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    start = (page - 1) * limit
    end = start + limit

    def get_file_info(filename):
        try:
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                file_stats = os.stat(file_path)
                return {
                    "name": filename,
                    "size": file_stats.st_size,
                    "created": datetime.fromtimestamp(file_stats.st_ctime).isoformat()
                }
        except OSError as e:
            logging.error(f"Error processing file {filename}: {str(e)}")
        return None

    try:
        with os.scandir(directory) as it:
            files = [entry.name for entry in it if entry.is_file()]
    except OSError as e:
        logging.error(f"Error scanning directory: {str(e)}")
        return jsonify({"error": "Unable to access directory"}), 500

    with ThreadPoolExecutor(max_workers=10) as executor:
        files_info = list(filter(None, executor.map(get_file_info, files)))

    # Use fnmatch to filter files
    if filter_query:
        filter_query = f'*{filter_query}*'  # Add wildcards to both sides of the query
        files_info = [info for info in files_info if fnmatch.fnmatch(info['name'].lower(), filter_query.lower())]
            
    files_info.sort(key=lambda x: x['created'], reverse=True)

    total_files = len(files_info)

    return jsonify({
        "files": files_info[start:end],
        "total_files": total_files
    })

@app.route('/download/<filename>', methods=['GET'])
@login_required
def download_file(filename):
    return send_from_directory('./video_records', filename, as_attachment=True)
  
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)