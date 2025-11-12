from flask import Flask, jsonify
import subprocess
import re
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # This line will enable CORS for all routes

# Compile the regular expressions once to avoid recompilation on each request
gpu_hw_active_frequency_re = re.compile(r'GPU HW active frequency: (\d+) MHz')
gpu_hw_active_residency_re = re.compile(r'GPU HW active residency:\s+(\d+\.\d+)%')
gpu_idle_residency_re = re.compile(r'GPU idle residency:\s+(\d+\.\d+)%')
gpu_power_re = re.compile(r'GPU Power: (\d+) mW')

@app.route('/gpu-usage')
def get_gpu_usage():
    try:
        # Execute the powermetrics command to get GPU usage data
        process = subprocess.Popen(
            ['sudo', 'powermetrics', '--samplers', 'gpu_power', '-i500', '-n1'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()

        # Check if the command executed successfully
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, stderr)

        # Parse the GPU usage details from the command output
        gpu_usage_data = {
            'gpu_hw_active_frequency': None,
            'gpu_hw_active_residency': None,
            'gpu_sw_requested_state': None,
            'gpu_sw_state': None,
            'gpu_idle_residency': None,
            'gpu_power': None
        }

        # Use the precompiled regular expressions to extract the relevant information
        gpu_hw_active_frequency_match = gpu_hw_active_frequency_re.search(stdout)
        gpu_hw_active_residency_match = gpu_hw_active_residency_re.search(stdout)
        gpu_idle_residency_match = gpu_idle_residency_re.search(stdout)
        gpu_power_match = gpu_power_re.search(stdout)

        # Assign the extracted values to the dictionary if matches are found
        if gpu_hw_active_frequency_match:
            gpu_usage_data['gpu_hw_active_frequency'] = int(gpu_hw_active_frequency_match.group(1))
        if gpu_hw_active_residency_match:
            gpu_usage_data['gpu_hw_active_residency'] = float(gpu_hw_active_residency_match.group(1))
        if gpu_idle_residency_match:
            gpu_usage_data['gpu_idle_residency'] = float(gpu_idle_residency_match.group(1))
        if gpu_power_match:
            gpu_usage_data['gpu_power'] = int(gpu_power_match.group(1))

        return jsonify(gpu_usage_data)
    
    except subprocess.CalledProcessError as e:
        return jsonify({'error': 'Failed to retrieve GPU usage data', 'details': str(e)}), 500
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred', 'details': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=4999, host="0.0.0.0")