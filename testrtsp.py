import cv2
import threading
from queue import Queue
from ultralytics import YOLO

# Initialize the model
model = YOLO("yolov8n.pt")

# Frame queue
frame_queue = Queue()



def capture_frames():
    cap = cv2.VideoCapture('rtsp://admin:H!kvision@321@10.0.40.109:554/Streaming/Channels/102')
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if not frame_queue.full():
            frame_queue.put(frame)

        cv2.imshow('Camera', frame)

    cap.release()

def process_frames():
    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()
            results = model.predict(frame)
            # Process results and display or further processing
            # This is where you'd integrate your existing processing code

# Thread setup
thread_capture = threading.Thread(target=capture_frames)
thread_process = threading.Thread(target=process_frames)

thread_capture.start()
thread_process.start()

thread_capture.join()
thread_process.join()