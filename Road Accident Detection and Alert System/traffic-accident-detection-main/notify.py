from datetime import datetime

current_notifications = []


def reset_notifications():
    global current_notifications
    current_notifications = []


def add_notification(notification_type, title, message):
    global current_notifications

    current_notifications.append({
        "type": notification_type,
        "title": title,
        "message": message,
        "time": datetime.now().strftime("%H:%M:%S")
    })


def get_notifications():
    return current_notifications.copy()