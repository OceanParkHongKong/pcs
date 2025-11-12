from ultralytics import YOLO

model=YOLO('/Users/username/Downloads/yolov8n-AF_in_-3-october-2024-14_57.pt')

model.export(format='coreml',nms=True)

