from pymongo import MongoClient
from datetime import datetime
from notify import add_notification

# MongoDB connection
MONGO_URI = "mongodb://localhost:27017/"

client = MongoClient(MONGO_URI)

# Database
db = client["Accident_DB"]

# Collection
accident_collection = db["Accidents"]


def save_accident(severity, confidence, location, image_path):
    """
    Save one accident incident into MongoDB.
    """

    accident_data = {
        "timestamp": datetime.now(),
        "result": "Accident Detected",
        "severity": severity,
        "confidence": round(float(confidence), 2),
        "location": location,
        "image": image_path
    }

    accident_collection.insert_one(accident_data)
    add_notification(
    "database",
    "Accident Saved",
    "Accident details saved successfully to MongoDB."
)

    print("Accident record saved to MongoDB")

def get_dashboard_data():

    total_accidents = accident_collection.count_documents({
        "result": "Accident Detected"
    })

    high_severity = accident_collection.count_documents({
        "severity": "High"
    })

    medium_severity = accident_collection.count_documents({
        "severity": "Medium"
    })

    low_severity = accident_collection.count_documents({
        "severity": "Low"
    })


    # Latest accident
    latest_record = accident_collection.find_one(
        {},
        sort=[("timestamp", -1)]
    )


    if latest_record:

        latest_data = {
            "result": latest_record.get(
                "result", "N/A"
            ),

            "severity": latest_record.get(
                "severity", "N/A"
            ),

            "confidence": latest_record.get(
                "confidence", 0
            ),

            "location": latest_record.get(
                "location", "N/A"
            ),

            "timestamp": str(
                latest_record.get("timestamp", "N/A")
            ),

            "image": latest_record.get(
                "image", ""
            )
        }

    else:

        latest_data = {
            "result": "No records",
            "severity": "None",
            "confidence": 0,
            "location": "N/A",
            "timestamp": "N/A",
            "image": ""
        }


    return {
        "total_detections": total_accidents,
        "accidents_detected": total_accidents,
        "low_severity": low_severity,
        "medium_severity": medium_severity,
        "high_severity": high_severity,
        "latest": latest_data
    }


