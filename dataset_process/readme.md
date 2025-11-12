# YOLO Dataset Preparation Guide

This guide outlines the steps to prepare a YOLO dataset using various scripts and configurations.

We need to convert from Yolo 1.0 format to Yolo v11 format. The final Yolo v8 dataset file structure is like this:

```
yolo_dataset/
    data.yaml
    train/
        images/
            frame_001.jpg
            frame_002.jpg
        labels/
            frame_001.txt
            frame_002.txt
        ...
    val/
        images/
            frame_001.jpg
            frame_002.jpg  
        labels/
            frame_001.txt
            frame_002.txt
        ...
    test/
        images/
            frame_001.jpg
            frame_002.jpg
        labels/
            frame_001.txt
            frame_002.txt
        ...
```

## Steps to Prepare the Dataset

1. **Download Dataset from CVAT in YOLO 1.0 Format**

   - Export your annotated dataset from CVAT in the YOLO 1.0 format.
2. **Merge Different Datasets into One Folder**

   - Use the `copy_files_keep_both.py` script to merge different datasets into a single folder.
   - This script ensures that all files from different datasets are copied while keeping both versions if there are duplicates.
   - Or you can export whole projects data (including all taskes within) directly from CVAT (but you may still need merge manually)
   - "ls -d */" command to list only the directories in the current folder
3. **Remove Empty Text and JPEG Files**

   - Run the `remove_empty_txt_jpgs.py` script to clean up the dataset by removing any empty text and JPEG files.
4. **Split Dataset into Train, Validation, and Test Folders**

   - Use the `split_to_3_folders.py` script to split your dataset into three folders: `train`, `val`, and `test`.
5. **Separate Labels and Images into Two Folders**

   - Execute the `split_labels_images_to_2_folder.py` script to separate the label files and image files into two different folders within each of the train, val, and test directories.
6. **Need call yolov8_to_v11.py to convert to v11 format**
7. **Copy a Valid YOLOv11 `data.yaml` into the Prepared Folder**

   - Copy the following `data.yaml` file into the root folder of your prepared dataset:

```yaml
train: images/train
val: images/val
test: images/test

names:
  0: panda
```

8. **`data.yaml` for POSE dataset:**

```yaml
train: images/train
val: images/val
test: images/test

kpt_shape: [17, 3]
flip_idx: [1, 0, 2, 3, 4, 8, 9, 10, 5, 6, 7, 14, 15, 16, 11, 12, 13]

names:
  0: panda
```

9. **To zip a folder using terminal, since the GUI menu's compress option doubles the file size:**

First, change current directory to target folder (otherwise, unexpected folder paths would be included in result zip). Then:
zip -r ../archive_name.zip .