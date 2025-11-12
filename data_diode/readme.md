# Data Diode

This data_diode folder contains the data diode implementation for sending PCS real-time results from the CCTV network to the IT network.

## Setup

First, you need to link the PCS SQLite database file to the current folder:

```bash
ln -s ../swift/people_count_database.db .
```

## Usage

CCTV Network
In the CCTV network, use the following commands to start sending data to the IT network:

```bash
python sender_http_server.py
python database_sender.py -batch-size 40
```

IT Network
In the IT network, use the following command to start receiving data from the CCTV network:

```bash
python kafka_consumer_example.py
```

Or for production, sending Kafka real time data to PCS API:

```bash
python receiver.py --interface en7
python kafka_batch_consumer_api.py

```

## Overview

The data diode ensures secure one-way data transmission of people counting results from the CCTV surveillance network to the IT infrastructure network.
