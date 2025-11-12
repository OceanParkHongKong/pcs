
from kafka import KafkaConsumer
import json

def consume_messages():
    consumer = KafkaConsumer(
        'data_diode_messages',
        bootstrap_servers=['localhost:9092'],
        value_deserializer=lambda x: json.loads(x.decode('utf-8')),
        auto_offset_reset='latest',  # Start from latest messages
        enable_auto_commit=True
    )
    
    print("🎯 Consuming messages from Kafka...")
    print("Press Ctrl+C to stop")
    
    try:
        for message in consumer:
            data = message.value
            print(f"📨 Received from Kafka:")
            print(f"   Partition: {message.partition}, Offset: {message.offset}")
            print(f"   Message ID: {data['data_diode_metadata']['message_id']}")
            print(f"   Original Sender: {data['data_diode_metadata']['sender']}")
            print(f"   Payload Type: {data['payload'].get('type', 'unknown')}")
            print(f"   Payload Source: {data['payload'].get('source', 'unknown')}")
            print("-" * 50)
    except KeyboardInterrupt:
        print("\n🛑 Consumer stopped")
    finally:
        consumer.close()

if __name__ == "__main__":
    consume_messages()
