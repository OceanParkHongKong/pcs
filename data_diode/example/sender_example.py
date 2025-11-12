import requests
import json

def send_data(data, message_type="general", source="python_client", priority="normal"):
    payload = {
        "data": data,
        "type": message_type,
        "source": source,
        "priority": priority
    }
    
    response = requests.post(
        "http://localhost:8008/send",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    return response.json()

# Send some data
result = send_data(
    {"user_id": 123, "action": "login", "timestamp": "2024-01-15T10:30:00Z"},
    message_type="user_activity",
    source="auth_service"
)
print(result)