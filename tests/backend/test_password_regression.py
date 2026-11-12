"""Regression: identity passwords are opaque, not trimmed form labels."""
from conftest import api, mail_token


def test_password_whitespace_is_preserved(app, client):
    password = '  Unique long password with spaces 73!  '
    result = api(client, '/auth/signup', {'name': 'Password test', 'email': 'spaces@example.test', 'password': password, 'company_name': 'Password fixture'})
    assert result.status_code == 201
    assert api(client, '/auth/verify-email', {'token': mail_token(app, 'verify')}).status_code == 200
    assert api(client, '/auth/login', {'email': 'spaces@example.test', 'password': password}).status_code == 200
    assert api(client, '/auth/mfa/setup', {'password': password}).status_code == 200
