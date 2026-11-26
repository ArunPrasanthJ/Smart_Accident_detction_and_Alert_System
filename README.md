# Smart_Accident_detction_and_Alert_System
## Description
A real-time road accident detection and alert system developed using Python, YOLOv8, OpenCV, Flask, and MongoDB. Two integrated YOLOv8 models are used for accident detection and severity classification. The system monitors video streams, stores accident details, displays results through a web dashboard, and sends automated email alerts for high-severity accidents.

## Technology Stack
- Python
- YOLOv8
- OpenCV
- Flask
- MongoDB
- HTML
- CSS
- JavaScript
- SMTP

## Workflow
1. Capture video streams or upload recorded videos.
2. Extract video frames using OpenCV.
3. Preprocess frames for YOLOv8.
4. Detect accidents using the first YOLOv8 model.
5. Classify accident severity using the second YOLOv8 model.
6. Store accident details and results in MongoDB.
7. Display detection results through the Flask dashboard.
8. Send automated email alerts for high-severity accidents.

## Key Features
- Real-time accident monitoring.
- YOLOv8-based accident detection.
- Automated severity classification (Low, Medium, High).
- MongoDB database integration.
- Web-based monitoring dashboard.
- Automated emergency email notifications.

## Objective
To improve road safety through automated accident detection, severity assessment, and timely emergency notifications.
