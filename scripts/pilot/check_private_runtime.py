"""Check required local infrastructure/config without printing secrets."""
from pathlib import Path
import socket
from urllib.request import urlopen
from urllib.parse import urlsplit

from dotenv import dotenv_values
import psycopg

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    config = dotenv_values(ROOT / '.env.pilot')
    required = ['SECRET_KEY', 'DATABASE_URL', 'MFA_ENCRYPTION_KEY', 'PRIVATE_STORAGE_DIR', 'SMTP_HOST', 'SMTP_PORT', 'CLAMAV_HOST', 'CLAMAV_PORT']
    assert all(config.get(key) for key in required), 'Missing required local pilot configuration'
    assert len(config['SECRET_KEY']) >= 32, 'Secret key too short'
    uri = config['DATABASE_URL'].replace('postgresql+psycopg://', 'postgresql://')
    assert urlsplit(uri).path == '/machivital_pilot', 'Refuse unexpected database target'
    with psycopg.connect(uri) as connection:
        result = connection.execute('SELECT 1').fetchone()
        assert result == (1,)
    with socket.create_connection((config['CLAMAV_HOST'], int(config['CLAMAV_PORT'])), timeout=10) as scanner:
        scanner.sendall(b'zPING\0')
        assert scanner.recv(128).startswith(b'PONG')
    with socket.create_connection((config['SMTP_HOST'], int(config['SMTP_PORT'])), timeout=10) as smtp:
        assert smtp.recv(128).startswith(b'220')
    with urlopen('http://127.0.0.1:8026/api/v1/messages', timeout=10) as inbox:
        assert inbox.status == 200
    print('PASS: explicit private config, isolated PostgreSQL, actual SMTP and ClamAV reachable')
    print('No credentials, personal data or production service tested or printed')


if __name__ == '__main__':
    main()
