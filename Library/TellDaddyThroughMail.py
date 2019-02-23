import smtplib
import getpass
import subprocess
import logging

try:
    import keyring
except ImportError:
    keyring = None

import email.mime.multipart
import email.mime.text
import email.utils

logger = logging.getLogger(__name__)


class Mailer(object):
    def send(self, msg):
        raise NotImplementedError

    def msg_plain(self, from_email, to_email, subject, body):
        msg = email.mime.text.MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Date'] = email.utils.formatdate()

        return msg

    def msg_html(self, from_email, to_email, subject, body_text, body_html):
        msg = email.mime.multipart.MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Date'] = email.utils.formatdate()

        msg.attach(email.mime.text.MIMEText(body_text, 'plain', 'utf-8'))
        msg.attach(email.mime.text.MIMEText(body_html, 'html', 'utf-8'))

        return msg


class SMTPMailer(Mailer):
    def __init__(self, smtp_user, smtp_server, smtp_port, tls, auth):
        self.smtp_server = smtp_server
        self.smtp_user = smtp_user
        self.smtp_port = smtp_port
        self.tls = tls
        self.auth = auth

    def send(self, msg):
        s = smtplib.SMTP(self.smtp_server, self.smtp_port)
        s.ehlo()

        if self.tls:
            s.starttls()

        if self.auth and keyring is not None:
            passwd = keyring.get_password(self.smtp_server, self.smtp_user)
            if passwd is None:
                raise ValueError('No password available in keyring for {}, {}'.format(self.smtp_server, self.smtp_user))
            s.login(self.smtp_user, passwd)

        s.sendmail(msg['From'], [msg['To']], msg.as_string())
        s.quit()


class SendmailMailer(Mailer):
    def __init__(self, sendmail_path):
        self.sendmail_path = sendmail_path

    def send(self, msg):
        p = subprocess.Popen([self.sendmail_path, '-t', '-oi'],
                             stdin=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             universal_newlines=True)
        result = p.communicate(msg.as_string())
        if p.returncode:
            logger.error('Sendmail failed with {result}'.format(result=result))


def have_password(smtp_server, from_email):
    return keyring.get_password(smtp_server, from_email) is not None


def set_password(smtp_server, from_email):
    ''' Set the keyring password for the mail connection. Interactive.'''
    if keyring is None:
        raise ImportError('keyring module missing - service unsupported')

    password = getpass.getpass(prompt='Enter password for {} using {}: '.format(from_email, smtp_server))
    keyring.set_password(smtp_server, from_email, password)
