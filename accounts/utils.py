# accounts/utils.py
from django.core.mail import send_mail
from django.conf import settings

def send_verification_email(email, code):
    """
    Send simple verification email
    """
    subject = 'Your Aqariiq Verification Code'
    
    message = f"""
    Welcome to Aqariiq!
    
    Your verification code is: {code}
    
    Enter this code in the app to verify your email address.
    
    This code will expire in 5 minutes.
    
    If you didn't create an account, please ignore this email.
    
    Best regards,
    Aqariiq Team
    """
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,  # Set to True in production
        )
        print(f"✅ Email sent to {email} with code: {code}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {email}: {e}")
        return False