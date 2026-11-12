"""Message date regression with no database, SMTP or application factory."""
from datetime import datetime, timezone
from types import SimpleNamespace
from pathlib import Path
import sys

from cryptography.fernet import Fernet
from flask import Flask

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from app.pilot.scheduling import mail_payload
from app.pilot.auth import decrypt


def test_updated_due_date_has_matching_plant_local_date():
    app=Flask('email-date-test')
    app.config.update(MFA_ENCRYPTION_KEY=Fernet.generate_key().decode(),APP_BASE_URL='http://localhost:5174')
    context=(SimpleNamespace(stage='due'),SimpleNamespace(number='WO-TEST',title='Synthetic message',due_at=datetime(2026,1,2,8,tzinfo=timezone.utc)),SimpleNamespace(scheduled_local='2026-01-01T09:00',timezone='Africa/Lagos'),SimpleNamespace(id=1),SimpleNamespace(email='test@example.test'))
    with app.app_context():
        message=decrypt(mail_payload(context)['body_encrypted'])
    assert 'Scheduled: 2026-01-02T08:00:00Z (UTC)' in message
    assert 'Plant schedule: 2026-01-02T09:00 Africa/Lagos' in message
