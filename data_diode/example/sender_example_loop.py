import requests
import json
import time
import random
from datetime import datetime, timezone

def send_data(data, message_type="general", source="python_client", priority="normal"):
    payload = {
        "data": data,
        "type": message_type,
        "source": source,
        "priority": priority
    }
    
    try:
        response = requests.post(
            "http://localhost:8008/send",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=5  # 5 second timeout
        )
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
            
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {str(e)}"

def generate_sensor_data():
    """Generate realistic sensor data"""
    return {
        "sensor_id": f"TEMP_{random.randint(1, 10):02d}",
        "temperature": round(random.uniform(18.0, 35.0), 2),
        "humidity": round(random.uniform(30.0, 80.0), 2),
        "pressure": round(random.uniform(990.0, 1030.0), 2),
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "location": random.choice(["Room_A", "Room_B", "Room_C", "Outdoor"])
    }

def generate_user_activity():
    """Generate user activity data"""
    actions = ["login", "logout", "view_page", "download", "upload", "search"]
    return {
        "user_id": random.randint(100, 999),
        "action": random.choice(actions),
        "ip_address": f"192.168.1.{random.randint(10, 254)}",
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "session_id": f"sess_{random.randint(10000, 99999)}"
    }

def generate_system_metrics():
    """Generate system performance metrics"""
    return {
        "cpu_usage": round(random.uniform(10.0, 95.0), 2),
        "memory_usage": round(random.uniform(40.0, 90.0), 2),
        "disk_usage": round(random.uniform(20.0, 85.0), 2),
        "network_in": random.randint(1000, 50000),
        "network_out": random.randint(800, 40000),
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "hostname": f"server-{random.randint(1, 5):02d}"
    }

def generate_alert():
    """Generate alert messages (high priority)"""
    alert_types = ["temperature_critical", "disk_full", "high_cpu", "memory_leak", "network_down"]
    severity_levels = ["warning", "critical", "error"]
    
    return {
        "alert_type": random.choice(alert_types),
        "severity": random.choice(severity_levels),
        "message": f"Alert triggered at {datetime.now().strftime('%H:%M:%S')}",
        "affected_system": f"system-{random.randint(1, 10)}",
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "alert_id": f"ALT_{random.randint(10000, 99999)}"
    }

def main():
    print("🚀 Starting continuous data sender...")
    print("📡 Sending data to http://localhost:8008")
    print("Press Ctrl+C to stop\n")
    
    message_count = 0
    success_count = 0
    error_count = 0
    
    # Data generators with their weights (probability of being selected)
    data_generators = [
        (generate_sensor_data, "sensor_data", "sensor_network", "normal", 40),      # 40% probability
        (generate_user_activity, "user_activity", "auth_service", "normal", 30),    # 30% probability  
        (generate_system_metrics, "system_metrics", "monitoring", "normal", 25),    # 25% probability
        (generate_alert, "alert", "alert_system", "high", 5)                       # 5% probability (high priority)
    ]
    
    try:
        while True:
            message_count += 1
            
            # Weighted random selection of data type
            weights = [item[4] for item in data_generators]
            selected = random.choices(data_generators, weights=weights, k=1)[0]
            
            generator_func, msg_type, source, priority, _ = selected
            
            # Generate data
            data = generator_func()
            
            # Send data
            success, result = send_data(data, msg_type, source, priority)
            
            if success:
                success_count += 1
                queue_size = result.get('queue_size', 'unknown')
                priority_indicator = "🔴" if priority == "high" else "🟢"
                print(f"{priority_indicator} Message #{message_count} sent successfully [Type: {msg_type}] [Queue: {queue_size}]")
            else:
                error_count += 1
                print(f"❌ Message #{message_count} failed: {result}")
            
            # Print statistics every 50 messages
            if message_count % 50 == 0:
                success_rate = (success_count / message_count) * 100
                print(f"\n📊 Statistics after {message_count} messages:")
                print(f"   ✅ Success: {success_count} ({success_rate:.1f}%)")
                print(f"   ❌ Errors: {error_count}")
                print("=" * 50)
                
                # Check sender status
                try:
                    status_response = requests.get("http://localhost:8008/status", timeout=2)
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        sender_stats = status_data.get('sender_stats', {})
                        queue_stats = status_data.get('queue_stats', {})
                        
                        print(f"📡 Sender status:")
                        print(f"   Messages sent: {sender_stats.get('messages_sent', 'unknown')}")
                        print(f"   Bytes sent: {sender_stats.get('bytes_sent', 'unknown')}")
                        print(f"   Queue drops: {queue_stats.get('queue_full_drops', 0)}")
                        print("=" * 50 + "\n")
                except:
                    print("⚠️  Could not get sender status\n")
            
            # Variable delay based on message type
            if priority == "high":
                time.sleep(random.uniform(0.01, 0.03))  # Alerts send faster
            else:
                time.sleep(random.uniform(0.05, 1.0))   # Regular messages
            
    except KeyboardInterrupt:
        print(f"\n🛑 Stopping sender...")
        print(f"📊 Final Statistics:")
        print(f"   Total messages: {message_count}")
        print(f"   Successful: {success_count}")
        print(f"   Errors: {error_count}")
        if message_count > 0:
            success_rate = (success_count / message_count) * 100
            print(f"   Success rate: {success_rate:.1f}%")
        print("👋 Goodbye!")

if __name__ == "__main__":
    main()