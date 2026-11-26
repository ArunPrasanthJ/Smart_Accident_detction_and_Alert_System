import os
import cv2
from flask import Flask, Response, render_template, request, send_file, session
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename, send_from_directory
from wtforms import FileField, SubmitField
from wtforms.validators import InputRequired
from YOLO_Video import process_image, video_detection
from mongo import get_dashboard_data
from notify import (
    reset_notifications,
    get_notifications
)

app = Flask(__name__)

BASE_DIR = app.root_path
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "files")
DETECTION_FOLDER = os.path.join(BASE_DIR, "runs", "detect")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

app.config.update(
    SECRET_KEY="roihansori",
    UPLOAD_FOLDER=UPLOAD_FOLDER,
)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/", methods=["GET", "POST"])
@app.route("/home", methods=["GET", "POST"])
def home():
    session.clear()

    try:
        dashboard_data = get_dashboard_data()
        dashboard_data["system_status"] = "ONLINE"

    except Exception as e:
        dashboard_data = {
            "total_detections": 0,
            "accidents_detected": 0,
            "low_severity": 0,
            "medium_severity": 0,
            "high_severity": 0,
            "system_status": "DATABASE ERROR",
            "error": str(e)
        }

    return render_template(
        "index.html",
        form=UploadFileForm(),
        dashboard_data=dashboard_data
    )

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def latest_detection_directory():
    """Return the most recently created YOLO output directory."""
    subfolders = [
        folder
        for folder in os.listdir(DETECTION_FOLDER)
        if os.path.isdir(os.path.join(DETECTION_FOLDER, folder))
    ]
    if not subfolders:
        raise FileNotFoundError("No YOLO detection output was generated")
    return max(
        subfolders,
        key=lambda folder: os.path.getctime(os.path.join(DETECTION_FOLDER, folder)),
    )


def uploaded_file_path(filename):
    """Return a safe absolute path inside the upload directory."""
    return os.path.join(UPLOAD_FOLDER, secure_filename(filename))

@app.route("/image_upload", methods=["GET"])
def image():
    session.clear()
    return render_template("image.html")

@app.route("/image_upload", methods=["POST"])
def predict_img():
    file = request.files.get("file")
    if not file or not file.filename or not allowed_file(file.filename):
        return render_template("invalid.html")

    filepath = uploaded_file_path(file.filename)
    file.save(filepath)
    image_path, detection_count = process_image(filepath)
    return render_template(
        "image.html",
        image_path=image_path,
        detection_count=detection_count,
    )


@app.route("/<path:filename>")
def display(filename):
    latest_folder = latest_detection_directory()
    directory = os.path.join(DETECTION_FOLDER, latest_folder)
    latest_file = next(iter(os.listdir(directory)), None)
    if not latest_file or not latest_file.lower().endswith((".jpg", ".jpeg", ".png")):
        return "Invalid file format", 404
    return send_from_directory(directory, latest_file, environ=request.environ)


@app.route("/download_image", defaults={"filename": None})
@app.route("/download_image/<path:filename>")
def download_image(filename):
    if filename:
        if not filename.startswith("files/processed/"):
            return "Not found", 404
        return send_from_directory(
            os.path.join(BASE_DIR, "static"),
            filename,
            as_attachment=True,
            environ=request.environ,
        )

    latest_folder = latest_detection_directory()
    directory = os.path.join(DETECTION_FOLDER, latest_folder)
    latest_file = next(iter(os.listdir(directory)), None)
    if not latest_file or not latest_file.lower().endswith((".jpg", ".jpeg", ".png")):
        return "Invalid file format", 404
    return send_file(os.path.join(directory, latest_file), as_attachment=True)
    
    

class UploadFileForm(FlaskForm):
    file = FileField("File", validators=[InputRequired()])
    submit = SubmitField("Run")


def generate_frames(path_x=""):
    for frame in video_detection(path_x):
        encoded, buffer = cv2.imencode(".jpg", frame)
        if not encoded:
            continue
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n\r\n"
        )


@app.route("/video_detection", methods=["GET", "POST"])
def front():

    form = UploadFileForm()
    video_ready = False

    if form.validate_on_submit():

        file = form.file.data

        video_path = uploaded_file_path(
            file.filename
        )

        file.save(video_path)

        # Clear ALL previous notifications
        reset_notifications()

        session["video_path"] = video_path

        video_ready = True

    return render_template(
        "video.html",
        form=form,
        video_ready=video_ready
    )


@app.route("/download_video")
def download_video():
    return send_file("output.mp4", as_attachment=True)


@app.route("/video")
def video():
    return Response(
        generate_frames(path_x=session.get("video_path", None)),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )

@app.route("/notifications")
def notifications():

    return {
        "notifications": get_notifications()
    }

if __name__ == "__main__":
    app.run(debug=True)