import smtplib
from django.conf import settings

def sendmail(to, mail):
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login(settings.GMAIL_USER, settings.GMAIL_PASS)
    s.sendmail(settings.GMAIL_USER, to, mail)
    s.close()
