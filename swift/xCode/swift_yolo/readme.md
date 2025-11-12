# Swift YOLO - Xcode Project

This is an Xcode project where `main.swift` receives pipe inputs from Python (the `main.py` under the swift folder), then returns YOLO results through another pipe which is read by the Python process.

**Benefits:**
- Utilizes Apple Neural Engine (ANE) for hardware acceleration
- Can run approximately 2x more YOLO processes compared to pure Python implementation
- Significantly improves inference performance on Apple Silicon

## Build Output Location

The generated macOS executable is located in Xcode's DerivedData folder. The path typically looks like:

```
/Users/username/Library/Developer/Xcode/DerivedData/<ProjectName>-<UniqueID>/Build/Products/Debug
/Users/username/Library/Developer/Xcode/DerivedData/<ProjectName>-<UniqueID>/Build/Products/Release
```

### How to Find Build Folder

In Xcode:
1. Menu Bar → **Product** → **Show Build Folder in Finder**

## Example Paths

Debug build:
```
/Users/username/Library/Developer/Xcode/DerivedData/test_swfit_ANE_2-cegmmbrsqckhwxgicibycuozveeb/Build/Products/Debug
```

Release build:
```
/Users/username/Library/Developer/Xcode/DerivedData/test_swfit_ANE_2-eqhnjqfponxgtddswukmtqorpagb/Build/Products/Release
```

Current project build:
```
/Users/username/Library/Developer/Xcode/DerivedData/swfit_yolo-gqqhyrfffctjifenpuypbuxoxzkh/Build
```

## Copy Build Scripts (Optional)

If you need to copy batch scripts to the build directory:

```bash
cp /path/to/your/scripts/start_batch_10.sh .
cp /path/to/your/scripts/stop_batch.sh .
```
