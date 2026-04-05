"""Email service for notifications and digests."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from flask import current_app


def send_email(to_email: str, subject: str, html_body: str, text_body: str = ""):
    """Send an email."""
    try:
        config = current_app.config
        
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.get("EMAIL_FROM")
        msg["To"] = to_email
        
        # Add text and HTML parts
        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        
        # Send email
        with smtplib.SMTP(config.get("SMTP_HOST"), config.get("SMTP_PORT")) as server:
            if config.get("SMTP_USE_TLS"):
                server.starttls()
            
            server.login(config.get("SMTP_USER"), config.get("SMTP_PASSWORD"))
            server.sendmail(config.get("EMAIL_FROM"), to_email, msg.as_string())
        
        return {"ok": True}
    except Exception as e:
        print(f"Email send failed: {e}")
        return {"ok": False, "error": str(e)}


def send_welcome_email(to_email: str, user_name: str):
    """Send welcome email to new user."""
    subject = "Welcome to Assistly - Community Support Made Simple"
    
    html_body = f"""
    <html>
    <head></head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #14233b;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2>Welcome to Assistly, {user_name}!</h2>
            <p>We're excited to have you on board. Whether you're looking for help or want to make a difference in your community, you're in the right place.</p>
            
            <h3>Get Started:</h3>
            <ul>
                <li>Complete your profile</li>
                <li>Join your community</li>
                <li>Browse requests or post your own</li>
            </ul>
            
            <p>Questions? Check out our Help Center or contact support.</p>
            <p>Happy helping!</p>
            <p><strong>The Assistly Team</strong></p>
        </div>
    </body>
    </html>
    """
    
    return send_email(to_email, subject, html_body)


def send_request_accepted_email(to_email: str, volunteer_name: str, request_title: str):
    """Notify volunteer that their acceptance was registered."""
    subject = f"You've accepted: {request_title}"
    
    html_body = f"""
    <html>
    <head></head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #14233b;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2>Request Accepted, {volunteer_name}!</h2>
            <p>You've successfully accepted the request: <strong>{request_title}</strong></p>
            <p>Start connecting with the resident and get the details you need to help.</p>
            <p style="margin-top: 20px;"><a href="http://localhost:5000/dashboard" style="background: #245fcd; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px;">View Request</a></p>
        </div>
    </body>
    </html>
    """
    
    return send_email(to_email, subject, html_body)


def send_request_completed_email(to_email: str, resident_name: str, request_title: str):
    """Notify resident that volunteer marked request as completed."""
    subject = f"Request Complete: {request_title}"
    
    html_body = f"""
    <html>
    <head></head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #14233b;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2>Your Request is Complete!</h2>
            <p>Hi {resident_name},</p>
            <p>The volunteer has marked your request complete: <strong>{request_title}</strong></p>
            <p>Please confirm completion and rate their work to help build our community.</p>
            <p style="margin-top: 20px;"><a href="http://localhost:5000/dashboard" style="background: #245fcd; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px;">Rate Volunteer</a></p>
        </div>
    </body>
    </html>
    """
    
    return send_email(to_email, subject, html_body)


def send_weekly_digest_email(to_email: str, user_name: str, digest_data: dict):
    """Send weekly summary digest email."""
    subject = "Your Weekly Community Update"
    
    open_requests = digest_data.get("open_requests", 0)
    new_requests = digest_data.get("new_requests", 0)
    completed = digest_data.get("completed", 0)
    opportunities = digest_data.get("top_opportunities", [])
    
    opportunities_html = ""
    for opp in opportunities[:5]:
        opportunities_html += f"""
        <div style="background: #f8fafd; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #245fcd;">
            <h4 style="margin: 0 0 8px 0;">{opp.get('title', 'Untitled')}</h4>
            <p style="margin: 0; color: #637695; font-size: 14px;">{opp.get('description', '')[:100]}...</p>
        </div>
        """
    
    html_body = f"""
    <html>
    <head></head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #14233b;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2>Your Weekly Community Update</h2>
            <p>Hi {user_name},</p>
            
            <h3>This Week's Highlights:</h3>
            <div style="background: #f4f7fb; padding: 20px; border-radius: 10px; margin: 15px 0;">
                <p>📊 <strong>Community Activity:</strong></p>
                <ul style="list-style: none; padding-left: 0;">
                    <li>✓ {completed} requests completed</li>
                    <li>🆕 {new_requests} new requests</li>
                    <li>📋 {open_requests} open requests</li>
                </ul>
            </div>
            
            <h3>Top Opportunities This Week:</h3>
            {opportunities_html if opportunities_html else "<p>No new opportunities this week.</p>"}
            
            <p style="margin-top: 30px; text-align: center;">
                <a href="http://localhost:5000/dashboard" style="background: #245fcd; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px;">View Dashboard</a>
            </p>
            
            <p style="margin-top: 40px; font-size: 12px; color: #637695; border-top: 1px solid #d9e2f0; padding-top: 20px;">
                You're receiving this because you're part of our community. You can manage email preferences in your account settings.
            </p>
        </div>
    </body>
    </html>
    """
    
    return send_email(to_email, subject, html_body)


def send_notification_email(to_email: str, subject: str, title: str, message: str, action_url: str = "", action_text: str = "View"):
    """Send a general notification email."""
    action_button = ""
    if action_url:
        action_button = f"""
        <p style="margin-top: 20px; text-align: center;">
            <a href="{action_url}" style="background: #245fcd; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px;">{action_text}</a>
        </p>
        """
    
    html_body = f"""
    <html>
    <head></head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #14233b;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2>{title}</h2>
            <p>{message}</p>
            {action_button}
        </div>
    </body>
    </html>
    """
    
    return send_email(to_email, subject, html_body)
