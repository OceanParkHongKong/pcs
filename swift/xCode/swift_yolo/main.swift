import Foundation
import Vision
import CoreML
import AVFoundation

protocol PrintDelegate {
    func print(_ message: String)
}

class PrintManager: PrintDelegate {
    private var buffer: [String] = []
    private let bufferSize = 3
    
    func print(_ message: String) {
        if buffer.contains(message) {
            // The new message is already in the buffer, do not print
            return
        } else {
            // Print the current message
            Swift.print(message)
            buffer.append(message)
            if buffer.count > bufferSize {
                buffer.removeFirst()
            }
        }
    }
}

class VideoAnalyzer {
    private var request: VNCoreMLRequest?
    private var counter = 0
    private var inputPipe: FileHandle?
    private var outputPipe: FileHandle?
    private var yoloModel: String
    private var printDelegate: PrintDelegate
    
    init(inputPipePath: String, outputPipePath: String, yolo_model: String = "crocoland", printDelegate: PrintDelegate) {
        self.yoloModel = yolo_model
        self.printDelegate = printDelegate
        setupModel()
      
        openPipeForWriting(pipePath: "/tmp/" + outputPipePath)
        openPipeForReading(pipePath: "/tmp/" + inputPipePath)
        print ("pipe read write ready")
    }

    private func setupModel() {
        do {
            let model: VNCoreMLModel
            let thresholdProvider: ThresholdProvider
            switch yoloModel {
            case "cableCar":
                model = try VNCoreMLModel(for: yolov11n_cablecar_PP_28_february_2025_11_02(configuration: MLModelConfiguration()).model)
                thresholdProvider = ThresholdProvider(iouThreshold: 0.3, confidenceThreshold: 0.5)
//            case "meerkat":
//                model = try VNCoreMLModel(for: yolov8_blar_bar(configuration: MLModelConfiguration()).model)
            case "meerkat":
                model = try VNCoreMLModel(for: yolov8n_meerkat_8_august_2024_15_10(configuration: MLModelConfiguration()).model)
                thresholdProvider = ThresholdProvider(iouThreshold: 0.7, confidenceThreshold: 0.3)
            case "ww_pool":
                model = try VNCoreMLModel(for: yolo11n_640_hc_bwb_9_june_2025_12_41(configuration: MLModelConfiguration()).model)
                thresholdProvider = ThresholdProvider(iouThreshold: 0.7, confidenceThreshold: 0.3)
            case "ww_pool_1920":
                model = try VNCoreMLModel(for: yolov11_1920_hc_bwb_9_june_2025_12_41(configuration: MLModelConfiguration()).model)
                thresholdProvider = ThresholdProvider(iouThreshold: 0.7, confidenceThreshold: 0.3)
            case "ww_riptide":
                model = try VNCoreMLModel(for: yolov11n_LC_RP_BWB_WS_640_15_july_2025_13_41(configuration: MLModelConfiguration()).model)
                thresholdProvider = ThresholdProvider(iouThreshold: 0.7, confidenceThreshold: 0.3)
            case "ww_7in1":
                model = try VNCoreMLModel(for: yolov11n_640_7in1_27_august_2025_8_03(configuration: MLModelConfiguration()).model)
                thresholdProvider = ThresholdProvider(iouThreshold: 0.7, confidenceThreshold: 0.2)
            case "ww_9in1", "ww_9in1_slides":
                model = try VNCoreMLModel(for: yolov11n_ww_9in1_II_16_september_2025_13_36 (configuration: MLModelConfiguration()).model)
                thresholdProvider = ThresholdProvider(iouThreshold: 0.7, confidenceThreshold: 0.2)
            case "ww_riptide_1920":
                model = try VNCoreMLModel(for: yolov11n_LC_RP_BWB_WS_1920_15_july_2025_13_41_manual_convert(configuration: MLModelConfiguration()).model)
                thresholdProvider = ThresholdProvider(iouThreshold: 0.7, confidenceThreshold: 0.3)
            case "crocoland":
                fallthrough
            default:
                model = try VNCoreMLModel(for: yolov8_crocoland_24_june_2024_10_11(configuration: MLModelConfiguration()).model)
                thresholdProvider = ThresholdProvider(iouThreshold: 0.7, confidenceThreshold: 0.3)
            }
            // Create an instance of ThresholdProvider with custom thresholds
            
            model.featureProvider = thresholdProvider
            
            request = VNCoreMLRequest(model: model, completionHandler: { [weak self] request, error in
                guard let self = self else { return }
                if let error = error {
                    self.printDelegate.print("Error processing the request: \(error.localizedDescription)")
                    return
                }

                var detections: [String] = []
                guard let results = request.results as? [VNRecognizedObjectObservation] else {
                    self.printDelegate.print("No object detection results found.")
                    return
                }

                for result in results {
                    let objectBounds = result.boundingBox
                    if let topLabel = result.labels.first {
                        let detectionInfo = [
                            "bbox": "\(objectBounds)",
                            "label": "\(topLabel.identifier)",
                            "confidence": "\(result.confidence)"
                        ]
              
                        if let jsonData = try? JSONSerialization.data(withJSONObject: detectionInfo, options: []),
                           let jsonString = String(data: jsonData, encoding: .utf8) {
                            detections.append(jsonString)
                        }
                    }
                }


                self.writeToPipe(detections.joined(separator: " "))

                self.counter += 1
                if self.counter % 1000 == 0 {
                    self.printDelegate.print("Processed 1000 frames")
                }
            })
            request?.imageCropAndScaleOption = .scaleFit
        } catch {
            self.printDelegate.print("Failed to load the model: \(error)")
        }
    }

    func analyzeVideo() {
        autoreleasepool {
            
            guard let image = fetchImageFromPipe() else {
                self.printDelegate.print("Failed to fetch image.")
                return
            }
            
         
            guard let request = self.request else {
                self.printDelegate.print("Model not setup properly.")
                return
            }

            let handler = VNImageRequestHandler(cgImage: image, options: [:])
                                
            do {
                try handler.perform([request])
            } catch {
                self.printDelegate.print("Failed to perform Vision request: \(error.localizedDescription)")
            }
        }
    }

    func openPipeForReading(pipePath: String) {
        let pipeURL = URL(fileURLWithPath: pipePath)

        do {
            let pipe = try FileHandle(forReadingFrom: pipeURL)
            self.inputPipe = pipe
        } catch {
            self.printDelegate.print("Failed to open pipe for reading: \(error.localizedDescription)")
        }
    }

    func openPipeForWriting(pipePath: String) {
        let pipeURL = URL(fileURLWithPath: pipePath)

        do {
            let pipe = try FileHandle(forWritingTo: pipeURL)
            self.outputPipe = pipe
        } catch {
            self.printDelegate.print("Failed to open pipe for writing: \(error.localizedDescription)")
        }
    }

    func fetchImageFromPipe() -> CGImage? {
        guard let pipe = self.inputPipe else {
            self.printDelegate.print("Invalid pipe handle.")
            return nil
        }
        
        // Read width, height, and length (4 bytes each)
        guard let headerData = try? readFully(pipe: pipe, length: 12) else {
            self.printDelegate.print("Failed to read image header.")
            return nil
        }

        let width = headerData.withUnsafeBytes { $0.load(fromByteOffset: 0, as: UInt32.self) }.bigEndian
        let height = headerData.withUnsafeBytes { $0.load(fromByteOffset: 4, as: UInt32.self) }.bigEndian
        let length = headerData.withUnsafeBytes { $0.load(fromByteOffset: 8, as: UInt32.self) }.bigEndian

        // Print the width, height, and length for debugging
//        self.printDelegate.print("Width: \(width), Height: \(height), Length: \(length)")
        
        if length > 0 {
            guard let imageData = try? readFully(pipe: pipe, length: Int(length)) else {
                self.printDelegate.print("Failed to read full image data.")
                return nil
            }

            // Create CGImage using width and height
            let bytesPerPixel = 3
            let bitsPerComponent = 8
            let bytesPerRow = bytesPerPixel * Int(width)

            let colorSpace = CGColorSpaceCreateDeviceRGB()
            let bitmapInfo = CGBitmapInfo(rawValue: CGImageAlphaInfo.none.rawValue)

            guard let provider = CGDataProvider(data: imageData as CFData) else {
                self.printDelegate.print("Failed to create data provider.")
                return nil
            }

            if let image = CGImage(
                width: Int(width),
                height: Int(height),
                bitsPerComponent: bitsPerComponent,
                bitsPerPixel: bytesPerPixel * bitsPerComponent,
                bytesPerRow: bytesPerRow,
                space: colorSpace,
                bitmapInfo: bitmapInfo,
                provider: provider,
                decode: nil,
                shouldInterpolate: true,
                intent: .defaultIntent
            ) {
                self.printDelegate.print("Successfully created CGImage.")
                return image
            } else {
                self.printDelegate.print("Failed to create CGImage.")
                return nil
            }
        }

        return nil
    }

    func readFully(pipe: FileHandle, length: Int) throws -> Data {
        var data = Data(capacity: length)
        while data.count < length {
            let remainingLength = length - data.count
            let chunk = pipe.readData(ofLength: remainingLength)
            if chunk.isEmpty {
                throw NSError(domain: "com.example.ErrorDomain", code: 1001, userInfo: [NSLocalizedDescriptionKey: "EOF reached before expected length"])
            }
            data.append(chunk)
        }
        return data
    }

    func writeToPipe(_ message: String) {
        guard let pipe = self.outputPipe else {
            self.printDelegate.print("Pipe is not open for writing.")
            return
        }

        if let data = message.data(using: .utf8) {
            var length = UInt32(data.count)
            let lengthData = Data(bytes: &length, count: 4)
            
            do {
//                print (length)
                try pipe.write(contentsOf: lengthData)
                try pipe.write(contentsOf: data)
                pipe.synchronizeFile()
            } catch {
                self.printDelegate.print("Failed to write to pipe: \(error.localizedDescription)")
            }
        }
    }
}

// Main script to initialize and run the VideoAnalyzer
import Foundation

let inputPipePath = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "test1"
let outputPipePath = CommandLine.arguments.count > 2 ? CommandLine.arguments[2] : "test1_result"
let yoloModel = CommandLine.arguments.count > 3 ? CommandLine.arguments[3] : "crocoland"

let printManager = PrintManager()  // Initialize PrintManager

let analyzer = VideoAnalyzer(inputPipePath: inputPipePath, outputPipePath: outputPipePath, yolo_model: yoloModel, printDelegate: printManager)



print ("swift loop started")
 
while true {
    let startTime = Date()  // Capture the start time

    analyzer.analyzeVideo()
        
    let executionTime = Date().timeIntervalSince(startTime)  // Calculate execution time
    let executionTimeInMilliseconds = executionTime * 1000   // Convert to milliseconds
//    print("\(inputPipePath): \(String(format: "%.2f ms swift", executionTimeInMilliseconds))")

        // *** No need to sleep, pipe readFully already blocking if no data

}
