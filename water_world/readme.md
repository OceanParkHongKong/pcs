# Water World People Counting System

The Water World system is an enhanced version of the original Ocean Park People Counting System (PCS), specifically designed for Water World attractions with additional alert mechanisms and occupancy calculations.

## Overview

The Water World system extends the original PCS with:

- **Real-time alerts** for capacity management and safety monitoring
- **Occupancy calculations** for water attractions
- **Enhanced monitoring** with Kafka-based event streaming
- **Web-based dashboard** for real-time monitoring and management
- **Flutter mobile frontend** for on-the-go monitoring

## Architecture

### System Dependencies

- **Base System**: Built on top of the original PCS system (must be running)
- **Alert Backend**: Flask-based server with WebSocket support
- **Kafka Integration**: Event streaming for real-time alerts
- **Database**: SQLite for alert storage, inherits people count data from main PCS
- **Frontend**: Flutter-based mobile app and web interface

### Key Components

1. **Alert Backend Server** (`alert_backend_server.py`)

   - Flask API with real-time WebSocket communication
   - JWT-based authentication
   - Alert management and monitoring
2. **Alert Monitor** (`alert_monitor.py`)

   - Continuous monitoring of people count data
   - Capacity threshold management
   - Automated alert generation
3. **Kafka Consumer** (`kafka_consumer.py`)

   - Real-time event processing
   - Integration with external systems
4. **SAHI Integration** (`main_sahi.py`)

   - Enhanced object detection using SAHI (Slicing Aided Hyper Inference)
   - Improved accuracy for crowded scenes

## Prerequisites

- Original PCS system running (see main [README.md](../README.md))
- Docker and Docker Compose
- Python 3.8+ with conda environment
- Kafka cluster (handled by docker-compose)

## Quick Start

### 1. Environment Setup

```bash
# Navigate to water_world directory
cd water_world

# Ensure original PCS system is running
# (Follow instructions in main README.md)

# Set required environment variables
export PASSO="your_camera_password"
```

### 2. Start Infrastructure (Kafka & Zookeeper)

```bash
# Start Kafka infrastructure
docker-compose up -d zookeeper kafka
```

### 3. Start Alert Backend Server

```bash
# Using Docker (recommended)
docker run -d --name pcs-ww-alert-backend-server \
    -p 8002:8002 \
    --network people_count_op_pcs_network_host1 \
    -v $(pwd)/../swift/people_count_database.db:/app/people_count_database.db \
    -v $(pwd)/config.json:/app/config.json \
    -v $(pwd)/../shared/config_kafka.json:/app/config_kafka.json \
    -v $(pwd)/logs:/app/logs \
    -v $(pwd)/alerts.db:/app/alerts.db \
    -v $(pwd)/location_settings.json:/app/location_settings.json \
    -v $(pwd)/users.json:/app/users.json \
    -v $(pwd)/user_preferences.json:/app/user_preferences.json \
    --restart=unless-stopped \
    pcs_ww_alert_backend_server:7

# Or run locally for development
python alert_backend_server.py
```

### 4. Start Web Frontend

```bash
# Start web frontend container
docker run -d \
    -p 8080:80 \
    -v $(pwd)/config_frontend.json:/usr/share/nginx/html/assets/config.json \
    --name pcs-ww-alert-web-frontend \
    --restart=unless-stopped \
    pcs_ww_alert_web_frontend:15
```

### 5. Start People Counting with SAHI (Optional)

```bash
# For enhanced detection accuracy in crowded scenes
python start_people_count_sahi.py
```

## Configuration

### Core Configuration Files

- **`config.json`**: API endpoints and JWT settings
- **`location_settings.json`**: Water World specific location configurations
- **`users.json`**: User management for web interface
- **`user_preferences.json`**: User-specific alert preferences

### Camera Configuration

Water World cameras are configured in `start_people_count_sahi.py`:

```python
cameras_config = [
    "rtsp://username1:${PASSO}@192.168.camera.ip1:554/axis-media/media.amp ww_pool C-2001 '[(10,1072),...'",
    "rtsp://username2:${PASSO}@192.168.camera.ip2:554/axis-media/media.amp ww_pool C-2004 '[(36,590),...'",
    # ... additional cameras
]
```

## API Endpoints

The alert backend server provides REST APIs:

- **`POST /api/login`**: User authentication
- **`GET /api/alerts`**: Retrieve active alerts
- **`POST /api/alerts`**: Create new alerts
- **`PUT /api/alerts/{id}`**: Update alert status
- **`GET /api/occupancy`**: Real-time occupancy data
- **`WebSocket /socket.io`**: Real-time updates

## Development & Testing

### Demo Mode

For testing without live cameras:

```bash
# Start demo with recorded videos
./start_demo.sh

# Stop demo
./stop_demo.sh
```

### Performance Monitoring

```bash
# Enable profiling (development only)
./run_profiling.sh

# View profiling dashboard
python profiling_dashboard.py
```

## Monitoring & Alerts

### Alert Types

- **Capacity Alerts**: When area occupancy exceeds thresholds
- **System Alerts**: Camera failures, processing errors
- **Safety Alerts**: Emergency situations requiring immediate attention

### Log Files

- **Application logs**: `logs/alert_backend_server.log`
- **Alert database**: `alerts.db`
- **Performance logs**: `logs/profiling/`

## Troubleshooting

### Common Issues

1. **Backend server not starting**

   ```bash
   # Check if original PCS is running
   curl http://localhost:5000/health

   # Check database permissions
   ls -la people_count_database.db
   ```
2. **Kafka connection issues**

   ```bash
   # Restart Kafka services
   docker-compose restart kafka zookeeper
   ```
3. **Camera connection problems**

   ```bash
   # Test camera connectivity
   python test_rtsp.py
   ```

## Dependencies

See `requirements.txt` for Python dependencies:

- Flask ecosystem (Flask, SocketIO, CORS)
- Kafka integration
- Redis for caching
- JWT for authentication
- SAHI for enhanced detection

## Related Documentation

- [Main PCS System](../README.md)
- [How to Add New Camera](../doc/how%20to%20add%20a%20new%20camera.md)
- [Backup Plan](../doc/backup_plan.md)

## Support

For issues related to:

- **Water World specific features**: Check `logs/` directory
- **Base PCS functionality**: Refer to main system documentation
- **Camera configuration**: See camera setup guides in `../doc/`
