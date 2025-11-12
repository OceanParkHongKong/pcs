# Project Name

## Introduction

The goal of this project is to leverage Apple's Neural Engine to run 2-3 times more YOLO-based Python people counting programs on a single Mac Studio Ultra. While the speed testing results are promising, showing significant improvements, there is a noted drop in accuracy by approximately 3-5%.

## Speed and Accuracy Comparison

### Speed Comparison

| Video | Resolution | pure Python FPS20  | this python with Swift FPS20 |
|-------|------------|------------|-----------|
| Crocoland | 1280x720 | 20 videos in parallel | 35 videos in parallel|
| Cable Car | 640x480  | 15 videos in parallel | 50 videos in parallel|


### Accuracy

The results of the Swift version and the pure Python version differ by approximately ±3%. 

## How to Start

### Prerequisites

- **Xcode**: Version 15.2 (15C500b) on MacOS 14.2.1 Sonoma
- **Python Environment**: Same as the `pcs` environment used in the `people_count_crocoland` project.

### Setup

1. **Start Swift Executables**:
    - Before running the Python code, you need to start the Swift executables. These executables receive images from Python via a Unix pipe and send back AI detection results to another pipe.

2. **Run Python Programs**:
    - Use the `start_batch_x.sh` script to start the Python programs. This script sends data to Swift via a Unix pipe and uses the AI detection results obtained from another pipe.
    - The `object_counter.py` and `ByteTrack` scripts are the same as those used in the `people_count_crocoland` project.

## Additional Information

- This project aims to enhance the performance of people counting applications by utilizing Apple's Neural Engine.
- Despite the improvements in speed, the slight drop in accuracy is a known issue and is being actively investigated.

## Contributing

If you wish to contribute to this project, please fork the repository and submit a pull request. For major changes, please open an issue to discuss what you would like to change.

---

Your contributions and feedback are welcome to help improve the accuracy and performance of this project.