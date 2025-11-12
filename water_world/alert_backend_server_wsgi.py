#!/usr/bin/env python3

import os
import sys
import threading
from alert_backend_server import app, socketio, logger, alert_monitor, kafka_consumer, check_send_alerts
from kafka_consumer import AlertKafkaConsumer

# Initialize alert monitoring
logger.info("WW backend started")
alert_monitor.create_location_alerts_table_if_not_exist()

# Start alert monitoring thread
threading.Thread(target=check_send_alerts, daemon=True).start()

# Initialize and start Kafka consumer
try:
    kafka_consumer = AlertKafkaConsumer(socketio)
    kafka_consumer.start()
    logger.info("✅ Kafka consumer initialized and started")
except Exception as e:
    logger.error(f"❌ Failed to initialize Kafka consumer: {e}")
    kafka_consumer = None

# Export the app for Gunicorn
application = app
