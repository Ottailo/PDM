"""Production SMTP must authenticate the TLS server certificate."""
import ssl
from unittest.mock import patch
from app.pilot.auth import encrypt
from app.pilot.worker import send_mail


def test_smtp_tls_verifies_certificate_and_hostname(app):
    app.config.update(TEST_MAIL_ADAPTER=None, SMTP_STARTTLS=True, SMTP_HOST='smtp.example.test', SMTP_PORT=587, SMTP_FROM='accounts@example.test')
    with app.app_context(), patch('app.pilot.worker.smtplib.SMTP') as smtp:
        smtp.return_value.__enter__.return_value.send_message.return_value = {}
        send_mail({'to': 'recipient@example.test', 'subject': 'Synthetic fixture', 'body_encrypted': encrypt('Synthetic fixture')}, 'tls-test-1')
        context = smtp.return_value.__enter__.return_value.starttls.call_args.kwargs['context']
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname is True
