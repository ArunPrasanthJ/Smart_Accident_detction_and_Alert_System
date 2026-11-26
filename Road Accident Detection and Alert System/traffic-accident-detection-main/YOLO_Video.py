from ultralytics import YOLO
import cv2
import torch
import time
import uuid
from pathlib import Path
from image_email import SendMail, reset_alert
from mongo import save_accident
from notify import add_notification


# ============================================================
# MODEL PATHS
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent
ACCIDENT_MODEL_PATH = PROJECT_DIR / "YOLO-Weights" / "yolov8m-dataset-7000-300.pt"
SEVERITY_MODEL_PATH = PROJECT_DIR / "YOLO-Weights" / "epoch90.pt"
IMAGE_OUTPUT_DIR = PROJECT_DIR / "static" / "files" / "processed"


# ============================================================
# SETTINGS
# ============================================================

ACCIDENT_CONFIDENCE = 0.50
IMAGE_CONFIDENCE = 0.10
SEVERITY_CONFIDENCE = 0.25

ACCIDENT_IMGSZ = 640
SEVERITY_IMGSZ = 320

# Run accident detection every N frames
FRAME_SKIP = 2

# Run severity detection every N processed frames
SEVERITY_INTERVAL = 5


# ============================================================
# DEVICE
# ============================================================

if torch.cuda.is_available():
    DEVICE = 0
    print("GPU:", torch.cuda.get_device_name(0))
else:
    DEVICE = "cpu"
    print("Running on CPU")


# ============================================================
# LOAD MODELS ONCE
# ============================================================

accident_model = YOLO(ACCIDENT_MODEL_PATH)
severity_model = YOLO(SEVERITY_MODEL_PATH)

print("Accident model loaded")
print("Severity model loaded")
print("Severity classes:", severity_model.names)


# ============================================================
# IMAGE DETECTION
# ============================================================

def process_image(file_path):
    source_path = Path(file_path).expanduser().resolve()
    image = cv2.imread(str(source_path))
    if image is None:
        raise ValueError(f"Could not read uploaded image: {source_path}")

    results = accident_model.predict(
        image,
        imgsz=ACCIDENT_IMGSZ,
        conf=IMAGE_CONFIDENCE,
        device=DEVICE,
        verbose=False
    )

    if not results:
        raise RuntimeError(f"YOLO did not return a result for {source_path.name}")

    result = results[0]
    detection_count = len(result.boxes) if result.boxes is not None else 0

    IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = IMAGE_OUTPUT_DIR / f"{uuid.uuid4().hex}.jpg"
    if not cv2.imwrite(str(output_path), result.plot()):
        raise OSError(f"Could not save annotated image to {output_path}")

    return output_path.relative_to(PROJECT_DIR / "static").as_posix(), detection_count


# ============================================================
# REAL-TIME VIDEO DETECTION
# ============================================================

def video_detection(path_x):

    cap = cv2.VideoCapture(path_x)

    if not cap.isOpened():
        print("Error: Could not open video")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)

    if fps <= 0:
        fps = 25

    # ==========================================================
    # FRAME VARIABLES
    # ==========================================================

    frame_count = 0
    processed_count = 0

    last_box = None
    last_accident_confidence = 0.0

    last_severity = "Unknown"
    last_severity_confidence = 0.0

    last_severity_time = 0

    # ==========================================================
    # INCIDENT VARIABLES
    # ==========================================================

    incident_active = False

    incident_max_severity = "Unknown"
    incident_max_confidence = 0.0
    incident_image_path = None

    missed_accident_frames = 0

    # Accident must be absent for this many
    # processed frames before incident ends
    INCIDENT_END_FRAMES = 5

    # ==========================================================
    # SEVERITY PRIORITY
    # ==========================================================

    severity_rank = {
        "unknown": 0,
        "low": 1,
        "medium": 2,
        "high": 3
    }

    try:

        while True:

            success, frame = cap.read()

            if not success:
                break

            frame_count += 1

            # ==================================================
            # FRAME SKIPPING
            # ==================================================

            if frame_count % FRAME_SKIP != 0:

                # ----------------------------------------------
                # Draw previous detection
                # ----------------------------------------------

                if last_box is not None:

                    x1, y1, x2, y2 = last_box

                    cv2.rectangle(
                        frame,
                        (x1, y1),
                        (x2, y2),
                        (0, 255, 0),
                        2
                    )

                    cv2.putText(
                        frame,
                        f"Accident: "
                        f"{last_accident_confidence:.2f}",
                        (x1, max(y1 - 10, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2
                    )

                    if last_severity != "Unknown":

                        cv2.putText(
                            frame,
                            f"Severity: {last_severity}",
                            (x1, y2 + 25),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 255),
                            2
                        )

                # IMPORTANT:
                # Return the actual OpenCV frame.
                # Flask will encode it later.
                yield frame

                continue

            # ==================================================
            # PROCESS FRAME
            # ==================================================

            processed_count += 1

            accident_found = False
            roi = None

            # ==================================================
            # ACCIDENT DETECTION
            # ==================================================

            accident_results = accident_model.predict(
                frame,
                imgsz=ACCIDENT_IMGSZ,
                conf=ACCIDENT_CONFIDENCE,
                device=DEVICE,
                verbose=False
            )

            accident_result = accident_results[0]

            # ==================================================
            # CHECK ACCIDENT DETECTION
            # ==================================================

            if (
                accident_result.boxes is not None
                and len(accident_result.boxes) > 0
            ):

                # ----------------------------------------------
                # Highest confidence accident
                # ----------------------------------------------

                best_index = torch.argmax(
                    accident_result.boxes.conf
                ).item()

                box = (
                    accident_result
                    .boxes
                    .xyxy[best_index]
                    .cpu()
                    .numpy()
                )

                accident_confidence = float(
                    accident_result
                    .boxes
                    .conf[best_index]
                    .item()
                )

                x1, y1, x2, y2 = map(
                    int,
                    box
                )

                # ----------------------------------------------
                # Keep coordinates inside frame
                # ----------------------------------------------

                h, w = frame.shape[:2]

                x1 = max(0, min(x1, w - 1))
                y1 = max(0, min(y1, h - 1))

                x2 = max(0, min(x2, w - 1))
                y2 = max(0, min(y2, h - 1))

                if x2 > x1 and y2 > y1:

                    accident_found = True

                    last_box = (
                        x1,
                        y1,
                        x2,
                        y2
                    )

                    last_accident_confidence = (
                        accident_confidence
                    )

                    # ------------------------------------------
                    # Accident ROI
                    # ------------------------------------------

                    roi = frame[
                        y1:y2,
                        x1:x2
                    ]

            # ==================================================
            # ACCIDENT FOUND
            # ==================================================

            if accident_found:

                # Reset missed frame counter
                missed_accident_frames = 0

                # ==================================================
                # START NEW INCIDENT
                # ==================================================

                if not incident_active:

                    incident_active = True

                    incident_max_severity = "Unknown"

                    incident_max_confidence = 0.0

                    incident_image_path = None

                    print(
                        "================================"
                    )
                    print(
                        "NEW ACCIDENT INCIDENT STARTED"
                    )
                    print(
                        "================================"
                    )

                # ==================================================
                # SEVERITY DETECTION
                # ==================================================

                if (
                    processed_count
                    - last_severity_time
                    >= SEVERITY_INTERVAL
                ):

                    if roi is not None and roi.size > 0:

                        severity_results = (
                            severity_model.predict(
                                roi,
                                imgsz=SEVERITY_IMGSZ,
                                conf=SEVERITY_CONFIDENCE,
                                device=DEVICE,
                                verbose=False
                            )
                        )

                        severity_result = (
                            severity_results[0]
                        )

                        current_severity = "Unknown"

                        current_severity_confidence = 0.0

                        # ==================================================
                        # CHECK SEVERITY MODEL
                        # ==================================================

                        if (
                            severity_result.boxes
                            is not None
                            and len(
                                severity_result.boxes
                            ) > 0
                        ):

                            # ------------------------------------------
                            # Highest confidence severity
                            # ------------------------------------------

                            best_severity_index = (
                                torch.argmax(
                                    severity_result
                                    .boxes
                                    .conf
                                ).item()
                            )

                            current_severity_confidence = (
                                float(
                                    severity_result
                                    .boxes
                                    .conf[
                                        best_severity_index
                                    ].item()
                                )
                            )

                            # ------------------------------------------
                            # Class ID
                            # ------------------------------------------

                            class_id = int(
                                severity_result
                                .boxes
                                .cls[
                                    best_severity_index
                                ].item()
                            )

                            # ------------------------------------------
                            # Class name
                            # ------------------------------------------

                            predicted_class = (
                                severity_model
                                .names[class_id]
                                .lower()
                            )

                            print(
                                "Severity model detected:",
                                predicted_class
                            )

                            # ==================================================
                            # VALID SEVERITY CLASSES ONLY
                            # ==================================================

                            if predicted_class in (
                                "low",
                                "medium",
                                "high"
                            ):

                                current_severity = (
                                    predicted_class
                                    .capitalize()
                                )

                            else:

                                # Ignore:
                                # detected-injury
                                # fire
                                # smoke

                                current_severity = "Unknown"

                                current_severity_confidence = 0.0

                                print(
                                    "Ignoring class:",
                                    predicted_class
                                )

                        # ==================================================
                        # VALID SEVERITY FOUND
                        # ==================================================

                        if current_severity != "Unknown":

                            # ------------------------------------------
                            # Latest severity
                            # ------------------------------------------

                            last_severity = (
                                current_severity
                            )

                            last_severity_confidence = (
                                current_severity_confidence
                            )

                            print(
                                "Current severity:",
                                current_severity
                            )

                            # ==================================================
                            # UPDATE MAXIMUM SEVERITY
                            # ==================================================

                            if (
                                severity_rank[
                                    current_severity.lower()
                                ]
                                >
                                severity_rank[
                                    incident_max_severity.lower()
                                ]
                            ):

                                incident_max_severity = (
                                    current_severity
                                )

                                incident_max_confidence = (
                                    current_severity_confidence
                                )

                                # ------------------------------------------
                                # Save representative image
                                # ------------------------------------------

                                incident_image_path = (
                                    "accident_incident.jpg"
                                )

                                cv2.imwrite(
                                    incident_image_path,
                                    roi
                                )

                                print(
                                    "Incident maximum severity:",
                                    incident_max_severity
                                )

                            # ==================================================
                            # HIGH SEVERITY EMAIL
                            # ==================================================

                            if current_severity == "High":

                                print(
                                    "HIGH SEVERITY DETECTED!"
                                )

                                high_image_path = (
                                    "high_severity_accident.jpg"
                                )

                                cv2.imwrite(
                                    high_image_path,
                                    roi
                                )

                                print(
                                    "Calling SendMail..."
                                )

                                if SendMail(high_image_path):
                                    add_notification(
                                        "email",
                                        "Alert Email Sent",
                                        "High severity accident alert email sent successfully."
                                    )

                        # Update severity check time
                        last_severity_time = (
                            processed_count
                        )

            # ==================================================
            # NO ACCIDENT FOUND
            # ==================================================

            else:

                if incident_active:

                    missed_accident_frames += 1

                    print(
                        "Accident not detected."
                    )

                    print(
                        "Missed frames:",
                        missed_accident_frames
                    )

                    # ==================================================
                    # END INCIDENT
                    # ==================================================

                    if (
                        missed_accident_frames
                        >= INCIDENT_END_FRAMES
                    ):

                        print(
                            "================================"
                        )

                        print(
                            "ACCIDENT INCIDENT ENDED"
                        )

                        print(
                            "Final severity:",
                            incident_max_severity
                        )

                        print(
                            "================================"
                        )

                        # ==================================================
                        # SAVE ONE MONGODB RECORD
                        # ==================================================

                        if (
                            incident_max_severity
                            != "Unknown"
                        ):

                            save_accident(
                                severity=(
                                    incident_max_severity
                                ),
                                confidence=(
                                    incident_max_confidence
                                ),
                                location="Chennai",
                                image_path=(
                                    incident_image_path
                                )
                            )

                            print(
                                "Accident record saved "
                                "to MongoDB."
                            )

                        # ==================================================
                        # RESET INCIDENT
                        # ==================================================

                        incident_active = False

                        incident_max_severity = (
                            "Unknown"
                        )

                        incident_max_confidence = 0.0

                        incident_image_path = None

                        missed_accident_frames = 0

                        last_box = None

                        last_accident_confidence = 0.0

                        last_severity = "Unknown"

                        last_severity_confidence = 0.0

                        last_severity_time = 0

                        # Allow a new High alert
                        reset_alert()

            # ==================================================
            # DRAW ACCIDENT BOX
            # ==================================================

            if last_box is not None:

                x1, y1, x2, y2 = last_box

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2
                )

                cv2.putText(
                    frame,
                    f"Accident: "
                    f"{last_accident_confidence:.2f}",
                    (x1, max(y1 - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

                # ==================================================
                # DRAW SEVERITY
                # ==================================================

                if last_severity != "Unknown":

                    cv2.putText(
                        frame,
                        f"Severity: {last_severity}",
                        (x1, y2 + 25),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 255),
                        2
                    )

            # ==================================================
            # DISPLAY PROCESSED FRAME COUNT
            # ==================================================

            cv2.putText(
                frame,
                f"Processed Frames: "
                f"{processed_count}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2
            )

            # ==================================================
            # IMPORTANT
            # ==================================================
            # Do NOT use cv2.imencode() here.
            #
            # Flask generate_frames() will encode this frame.
            # ==================================================

            yield frame

    finally:

        # ======================================================
        # VIDEO ENDED WHILE INCIDENT IS ACTIVE
        # ======================================================

        if incident_active:

            if (
                incident_max_severity
                != "Unknown"
            ):

                print(
                    "Video ended during active incident."
                )

                print(
                    "Saving final severity:",
                    incident_max_severity
                )

                save_accident(
                    severity=(
                        incident_max_severity
                    ),
                    confidence=(
                        incident_max_confidence
                    ),
                    location="Chennai",
                    image_path=(
                        incident_image_path
                    )
                )

        # ======================================================
        # RELEASE VIDEO
        # ======================================================

        cap.release()

        print(
            "Video processing completed."
        )