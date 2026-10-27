# utils/email_utils.py
# Sends the booking confirmation email through Gmail SMTP.
# If anything goes wrong it only prints a "[EMAIL] ..." message and returns False,
# so the booking itself (already saved in MongoDB) is never lost.

import os
import smtplib
import ssl
from html import escape
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()


def build_email_html(b):
    """The HTML body of the confirmation email."""
    rows = [
        ("Booking ID", b["booking_id"]),
        ("Movie", b["movie_title"]),
        ("Date", b["show_date_display"]),
        ("Show time", b["show_time"]),
        ("Seats", b.get("seats_text", ", ".join(b["seats"]))),
        ("Tickets", str(b["seat_count"])),
        ("Price per ticket", "Rs. " + str(b["ticket_price"])),
        ("Total amount", "Rs. " + str(b["total_amount"])),
    ]
    table_rows = "".join(
        '<tr><td style="padding:8px 0;color:#6F6D66;border-bottom:1px solid #EFEDE8;">'
        + escape(label) +
        '</td><td style="padding:8px 0;text-align:right;font-weight:600;border-bottom:1px solid #EFEDE8;">'
        + escape(str(value)) + '</td></tr>'
        for label, value in rows
    )
    return (
        '<div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;color:#2A2924;">'
        '<h2 style="text-align:center;">MOVIE MAX</h2>'
        '<p>Hello ' + escape(b["customer_name"]) + ',</p>'
        '<p>Your booking is <strong>confirmed</strong>. Here are your ticket details:</p>'
        '<table style="width:100%;border-collapse:collapse;font-size:14px;">' + table_rows + '</table>'
        '<p style="margin-top:20px;">Enjoy the movie!</p>'
        '</div>'
    )


def send_booking_email(booking):
    """Returns True if the email was sent, otherwise False."""
    sender = os.getenv("EMAIL_ADDRESS", "").strip()
    password = os.getenv("EMAIL_PASSWORD", "").replace(" ", "")

    if not sender or not password or "yourgmail" in sender or "16letter" in password:
        print("[EMAIL] Not sent: set EMAIL_ADDRESS and EMAIL_PASSWORD (Gmail App Password) in the .env file.")
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = "Movie Max - Booking Confirmed (" + booking["booking_id"] + ")"
    message["From"] = "Movie Max <" + sender + ">"
    message["To"] = booking["customer_email"]
    message.attach(MIMEText(build_email_html(booking), "html"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=15) as server:
            server.login(sender, password)
            server.sendmail(sender, booking["customer_email"], message.as_string())
        return True
    except smtplib.SMTPAuthenticationError:
        print("[EMAIL] Gmail login failed. Use a 16-letter App Password (not your normal password).")
    except Exception as error:
        print("[EMAIL] Could not send the email:", error)
    return False
