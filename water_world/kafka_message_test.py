#!/usr/bin/env python3
"""
Enhanced Kafka consumer for real-time message monitoring.

Usage examples:
  # Basic usage with default settings
  python kafka_realtime_test.py

  # Connect to specific broker and topic
  python kafka_realtime_test.py --broker 192.168.kafka.ip:9092 --topic people_count_results

  # Monitor multiple topics with JSON formatting
  python kafka_realtime_test.py --topic topic1 --topic topic2 --decode json

  # Start from beginning of topic
  python kafka_realtime_test.py --from-beginning

  # Pretty print with timestamps
  python kafka_realtime_test.py --pretty --show-timestamp
"""

import argparse
import json
import logging
import signal
import sys
import time
from datetime import datetime
from typing import List, Optional
from kafka import KafkaConsumer
from kafka.errors import KafkaError

# Color codes for pretty printing
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

LOG_LEVELS = {"debug": logging.DEBUG, "info": logging.INFO, "warning": logging.WARNING, "error": logging.ERROR}

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enhanced Kafka real-time message consumer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Connect to default broker and topic
  python kafka_realtime_test.py

  # Connect to specific broker
  python kafka_realtime_test.py --broker 192.168.1.100:9092

  # Monitor multiple topics
  python kafka_realtime_test.py --topic topic1 --topic topic2

  # Pretty JSON output with timestamps
  python kafka_realtime_test.py --decode json --pretty --show-timestamp
        """
    )
    
    # Connection settings
    parser.add_argument(
        "--broker", "--bootstrap-server",
        default="localhost:9092",
        help="Kafka bootstrap server (host:port). Multiple servers: host1:port1,host2:port2"
    )
    
    # Topic settings
    parser.add_argument(
        "--topic", "-t",
        action="append",
        help="Topic(s) to consume. Use multiple --topic flags for multiple topics. Default: people_count_results"
    )
    
    # Consumer settings
    parser.add_argument(
        "--group-id", "-g",
        default=f"realtime-test-consumer-{int(time.time())}",
        help="Consumer group ID. Default uses timestamp to avoid conflicts"
    )
    
    parser.add_argument(
        "--from-beginning", "-b",
        action="store_true",
        help="Start consuming from the beginning of the topic"
    )
    
    # Display settings
    parser.add_argument(
        "--decode", "-d",
        choices=["utf-8", "json", "raw"],
        default="utf-8",
        help="How to decode message values"
    )
    
    parser.add_argument(
        "--pretty", "-p",
        action="store_true",
        default=True,
        help="Enable pretty colored output"
    )
    
    parser.add_argument(
        "--show-timestamp", "-s",
        action="store_true",
        help="Show message timestamps"
    )
    
    parser.add_argument(
        "--show-headers", "-H",
        action="store_true",
        help="Show message headers"
    )
    
    parser.add_argument(
        "--max-messages", "-m",
        type=int,
        help="Maximum number of messages to consume (default: unlimited)"
    )
    
    # Logging
    parser.add_argument(
        "--log-level", "-l",
        choices=LOG_LEVELS.keys(),
        default="info",
        help="Logging verbosity"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress info logs, only show messages"
    )
    
    return parser.parse_args()

def decode_value(value: bytes | None, mode: str) -> str:
    """Decode message value based on specified mode."""
    if value is None:
        return "None"

    if mode == "raw":
        return repr(value)

    try:
        text = value.decode("utf-8")
    except UnicodeDecodeError as exc:
        return f"<decode error {exc!r}: {repr(value)}>"

    if mode == "json":
        try:
            parsed = json.loads(text)
            return json.dumps(parsed, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            return f"<invalid json> {text}"

    return text

def format_message(record, decode_mode: str, pretty: bool = False, show_timestamp: bool = False, show_headers: bool = False) -> str:
    """Format a Kafka message for display."""
    
    # Decode the message value
    value = decode_value(record.value, decode_mode)
    
    # Build the message info
    info_parts = []
    
    if pretty:
        info_parts.append(f"{Colors.CYAN}topic={Colors.END}{Colors.BOLD}{record.topic}{Colors.END}")
        info_parts.append(f"{Colors.BLUE}partition={Colors.END}{record.partition}")
        info_parts.append(f"{Colors.GREEN}offset={Colors.END}{record.offset}")
    else:
        info_parts.append(f"topic={record.topic}")
        info_parts.append(f"partition={record.partition}")
        info_parts.append(f"offset={record.offset}")
    
    if show_timestamp and record.timestamp:
        timestamp = datetime.fromtimestamp(record.timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        if pretty:
            info_parts.append(f"{Colors.WARNING}time={Colors.END}{timestamp}")
        else:
            info_parts.append(f"time={timestamp}")
    
    info_str = " ".join(info_parts)
    
    # Format headers if requested
    headers_str = ""
    if show_headers and record.headers:
        headers_dict = {k: v.decode('utf-8') if isinstance(v, bytes) else str(v) for k, v in record.headers}
        if pretty:
            headers_str = f"\n{Colors.HEADER}Headers:{Colors.END} {json.dumps(headers_dict, indent=2)}"
        else:
            headers_str = f"\nHeaders: {headers_dict}"
    
    # Format the final message
    if pretty:
        if decode_mode == "json":
            return f"[{info_str}]{headers_str}\n{Colors.BOLD}Message:{Colors.END}\n{value}\n"
        else:
            return f"[{info_str}]{headers_str} {Colors.BOLD}{value}{Colors.END}"
    else:
        if decode_mode == "json":
            return f"[{info_str}]{headers_str}\nMessage:\n{value}\n"
        else:
            return f"[{info_str}]{headers_str} {value}"

def main() -> int:
    args = parse_args()
    
    # Set up logging
    if args.quiet:
        logging.basicConfig(level=logging.ERROR, format="%(message)s")
    else:
        logging.basicConfig(
            level=LOG_LEVELS[args.log_level],
            format="%(asctime)s %(levelname)s: %(message)s"
        )
    
    logger = logging.getLogger("kafka-realtime-consumer")
    
    # Parse bootstrap servers
    bootstrap_servers = [server.strip() for server in args.broker.split(",") if server.strip()]
    
    # Set default topic if none provided
    topics = args.topic if args.topic else ["people_count_results"]
    
    # Consumer settings
    auto_offset = "earliest" if args.from_beginning else "latest"
    
    if not args.quiet:
        logger.info(f"Connecting to Kafka brokers: {bootstrap_servers}")
        logger.info(f"Topics: {topics}")
        logger.info(f"Consumer group: {args.group_id}")
        logger.info(f"Starting from: {auto_offset}")
        if args.max_messages:
            logger.info(f"Max messages: {args.max_messages}")
    
    try:
        consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=bootstrap_servers,
            group_id=args.group_id,
            auto_offset_reset=auto_offset,
            enable_auto_commit=True,
            consumer_timeout_ms=1000,  # Timeout for polling
            value_deserializer=None,  # Keep as bytes for flexible decoding
        )
    except KafkaError as error:
        logger.error(f"Failed to create consumer: {error}")
        return 1
    
    if not args.quiet:
        logger.info("Successfully connected! Waiting for messages... (Ctrl+C to stop)")
        if args.pretty:
            print(f"{Colors.BOLD}=== Kafka Real-time Message Monitor ==={Colors.END}")
    
    # Message counter
    message_count = 0
    running = True
    
    def handle_signal(signum, frame):
        nonlocal running
        if not args.quiet:
            logger.info(f"Signal {signum} received, shutting down...")
        running = False
    
    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_signal)
    
    try:
        while running:
            # Poll for messages
            message_batch = consumer.poll(timeout_ms=500)
            
            if not message_batch:
                continue
                
            for topic_partition, messages in message_batch.items():
                for record in messages:
                    message_count += 1
                    
                    # Format and print the message
                    formatted_message = format_message(
                        record, 
                        args.decode, 
                        args.pretty, 
                        args.show_timestamp, 
                        args.show_headers
                    )
                    print(formatted_message)
                    
                    # Check if we've reached the maximum message count
                    if args.max_messages and message_count >= args.max_messages:
                        if not args.quiet:
                            logger.info(f"Reached maximum message count ({args.max_messages})")
                        running = False
                        break
                
                if not running:
                    break
    
    except KafkaError as error:
        logger.error(f"Error while consuming: {error}")
        return 1
    except KeyboardInterrupt:
        if not args.quiet:
            logger.info("Interrupted by user")
    finally:
        consumer.close()
        if not args.quiet:
            logger.info(f"Consumer closed. Total messages processed: {message_count}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())