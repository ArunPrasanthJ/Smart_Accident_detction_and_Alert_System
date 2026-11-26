import os
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart


alert_sent = False


def SendMail(ImgFileName):
    global alert_sent

    # Do not send again
    if alert_sent:
        return False

    img_data = open(ImgFileName, "rb").read()

    msg = MIMEMultipart()
    msg["Subject"] = "Crash Alert"
    msg["From"] = "ACCIDENT DETECTION SYSTEM"
    msg["To"] = "HOSPITAL EMERGENCY TEAM"

    text = MIMEText("Vehicle Crash Detected. High Severity. Send HELP")
    msg.attach(text)

    image = MIMEImage(
        img_data,
        name=os.path.basename(ImgFileName)
    )
    msg.attach(image)

    try:
        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.ehlo()
        s.starttls()
        s.ehlo()

        s.login(
            "arunprasanthj777@gmail.com",
            "npav rkls xkok vvfx"
        )

        s.sendmail(
            "arunprasanthj777@gmail.com",
            "arunthemaster2.o@gmail.com",
            msg.as_string()
        )

        s.quit()

        # Mark alert as sent only after successful email
        alert_sent = True

        print("High severity alert email sent.")
        return True

    except Exception as e:
        print("Email failed:", e)
        return False
def reset_alert():
    global alert_sent
    alert_sent = False