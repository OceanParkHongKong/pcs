# PeopleCount: Ocean Park Hong Kong People Count System, based on YOLOv11

<div align="center">
  <p>
    <img src="static/images/ScreenRecording2025-10-16.gif" width="600"/>
  </p>
</div>

## Introduction

Welcome to the repository that hosts a Python application designed to count people across various camera live feeds. This project leverages advanced object detection and tracking technologies to provide accurate, real-time people counting. It uses MySQL (or SQLite) for storing result data.

### Technologies Used

- **YOLOv11**: Our application indirectly uses [YOLOv11](https://github.com/ultralytics/ultralytics), a state-of-the-art object detection model known for its speed and accuracy.
- **BoxMOT**: The tracking functionality is built on top of [BoxMOT](https://github.com/mikel-brostrom/yolo_tracking), which integrates seamlessly with YOLO models to enhance tracking capabilities.
- **Flask**: For live video inspection.
- **Redis**: To share images between the YOLO process and the Flask process.

## Getting Started

### Prerequisites

Ensure you have the following installed:

- Python 3.8 or higher
>  ❗
> Should stick with Python 3.8 since 3.12 will be encountering dependency conficts.
- Dependencies as listed in `requirements.txt`
>  ❗
> Redis version redis-cli 7.4.0


### Installation

    Clone the repository:

```bash
   git clone https://www.github.com/oceanparkhk/people_count_op.git
   cd people_count_op
```

## Before you start the application

### Environment Setup

It is recommended to use Python Conda and set up an environment:

```bash
conda create -n pcs python=3.10
conda activate pcs
```

Install the required Python packages:

```bash
   pip install -r requirements.txt
```

Since it uses Apple CoreML by default, Docker is not currently supported for YOLO Apple processes.
There are two Dockerfiles:
Dockerfile.web_inspect to compose web REST APIs
Dockerfile.web_video_feed to compose web live video feed generators

If you are using VSCode, activate the Conda environment:
[How to activate conda environment in vs code](https://stackoverflow.com/questions/67750857/how-to-activate-conda-environment-in-vs-code)

- Press `apple + shift + p`
- Select interpreter
- Choose `pcs`

### Environment Variables Setup

Set up the following environment variables for Conda, which will be used in live camera URL authentication:

```bash
conda activate pcs
conda env config vars set PEOPLE_COUNT_CC_PASS="aUsername:thePassword"
conda env config vars set PEOPLE_COUNT_CROCO_PASS="Username2:Password2"
```

### Set Up Users and Passwords for Accessing Live Video

Modify `users.csv` to update user access credentials. It's straightforward.

### Configure Files 
in 'shared' folder
- `config_db.json`: Used for configuring MySQL database connections.
- `config_redis.json`: Used for configuring Redis connections.
>  ❗
> Change Redis connection ip and port if necessary
- `config_video_feed.json`: Used to specify the IP address for the video feed (IP address which running `python web_video_feed.py`).
>  ❗
> Change ip to 127.0.0.1

### To Initialize a Database table

The SQLite database will automatically initialize on the first run.

If you need to synchronize data from SQLite to MySQL, do the following. For the first time testing, you can ignore the following MySQL DB instructions:

The MySQL database needs to be manually initialized for now.

Call the following script once, you need to uncomment one line 'setup_or_clean_db(conn)' first, then:

```bash
python database_mysql.py
```

## Setup Options

### Option 1: One-command setup using Docker Compose

To set up all Docker containers at once, use the following command:

```bash
docker-compose -f docker-compose.host1.yaml up -d
```

This will create and start all the necessary containers as defined in the `docker-compose.host1.yml` file.

### Option 2: Manual setup

If you prefer to set up containers manually, follow these steps:

1. First, create a Docker network for the containers:

```bash
docker network create pcs_network
```

2. Then, install each container using the following commands:

- **For live video feed:**
  ```bash
  docker run -d --name pcs_web_video_feed --network pcs_network -p 5001:5001 pcs_web_video_feed:5
  ```
  Replace "5" with another version if needed.

- **For web inspection based on SQLite database:**
  ```bash
  docker run -d --name pcs_web_server_sqlite --network pcs_network -v ${PWD}/people_count_database.db:/app/people_count_database.db -p 5000:5000 pcs_web_server_sqlite:15
  ```

- **To install Redis database:**
  ```bash
  docker run --name my-redis --network pcs_network -p 6379:6379 -d redis
  ```

- **For synchronization between SQLite and MySQL databases:**
  *No specific commands provided.*

- **To install MySQL database:**
  *No specific commands provided.*

If you want to build the images, check the `Dockerfile.xxxx` files under the root folder.

In pcs_web_video_feed, pcs_web_server_sqlite, pcs_web_server_mysql, pcs_sync_mysql there are xxxx.json file(s) you need to config. You can change them with docker mount -v option, or modify them in the docker containers directly.

## Usage: Start the application

### To Start Single Video Source
- in project 'swfit' folder:
- Cable Car:
  ```bash
   python main_and_swift.py --video "http://$PEOPLE_COUNT_CC_PASS@192.168.camera.ip/mjpg/video.mjpg" --model cableCar --camera_name CC_Out_Cam2
  ```
- Pulbic Github:
For public users, since you cannot access Ocean Park's cameras, we have prepared a short demo Crocoland video. Video link here: xxxx 
You can start the testing script: 'python start_people_count_dev.py'.

### Start All Video Cameras YOLO Processes and Web Inspect Server

- In the project `swift` folder, run:

  ```bash
  ./start_people_count.sh
  ```
  Or, if you want to print logs directly in the console:
  ```bash
  ./python start_people_count.py
  ```
  This script will restart all processes if run more than once.

### Restart Daily

Current there is [memory leaks](https://github.com/ultralytics/ultralytics/issues/8441) when using Yolov8 with Apple mps, following script help to restart all Yolo process daily:

```bash
./start_people_count_loop.sh
```

### Check running logs, detect cameras network down

If camera network down, to restart the Yolo process automatically, you may need:

```bash
./start_people_count_monitor_log.sh
```

### Setup Regions to Count

If you check the script in start_people_count.py, you will find that each camera line has a parameter like [(x1,y1),(x2,y2),(x3,y3)...] after the camera name, which is used to specify counting regions. It consists of a series of points. You can use 'python image_point_positions_arguments_gen.py' to generate region points via the command line by using the mouse to point at an image.

### Different Counting Methods

There is a parameter called '-in-direction' in start_people_count.sh, which is used to set different methods for 'in_count' (and it implies that 'out_count' works reversely). x+ means increasing the x position results in in_count + 1, x- means decreasing the x position, and border means if an object enters the border, 'in_count' + 1 is added. Alternatively, you can check object_counter.py to see the source code.

## Dataset Processing

We train YOLOv11 models ourselves to achieve the best AI inference results. Using [CVAT](https://github.com/cvat-ai/cvat) (not included in this repo) to prepare images, since CVAT does not support YOLOv11 dataset export. Under the `dataset_process` folder, there are various standalone Python scripts; the file name generally describes what the script would do.

You can train with exported Yolov11 dataset with Google Colab in the link provided by [Ultralytics Hub](https://www.ultralytics.com/)

### Contributing & Support

We welcome contributions to this project! If you have suggestions or improvements, please fork the repo and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

For support, email larry.m.liu@oceanpark.com.hk or enterprise.team@oceanpark.com.hk.

### License

This project is licensed under the AGPL3.0 License - see the LICENSE file for details.

### Acknowledgments

Thanks to the creators of YOLOv11, BoxMOT, Flask, Redis etc for providing the tools that power our application.
