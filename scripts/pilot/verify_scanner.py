"""Read-only local ClamAV proof using clean and harmless EICAR test bytes."""
import socket
import struct


def scan(data: bytes) -> str:
    with socket.create_connection(('127.0.0.1', 13310), timeout=15) as client:
        client.sendall(b'zINSTREAM\0')
        client.sendall(struct.pack('!I', len(data)) + data + struct.pack('!I', 0))
        return client.recv(4096).decode().rstrip('\0')


def main() -> None:
    with socket.create_connection(('127.0.0.1', 13310), timeout=15) as client:
        client.sendall(b'zPING\0')
        response = client.recv(4096).decode().rstrip('\0')
        assert response == 'PONG', response
        print('ClamAV PING: PONG')
    clean = scan(b'%PDF-1.4\n% harmless local scanner connectivity test\n')
    print('Clean payload:', clean)
    assert clean.endswith('OK'), clean
    # Official harmless antivirus test signature, not executable malware.
    signature = b'X5O!P%@AP[4' + bytes([92]) + b'PZX54(P^)7CC)7}' + bytes([36]) + b'EICAR-STANDARD-ANTIVIRUS-TEST-FILE!' + bytes([36]) + b'H+H*'
    infected = scan(signature)
    print('EICAR negative control:', infected)
    assert infected.endswith('FOUND'), infected
    print('PASS: clean accepted and antivirus test signature detected')


if __name__ == '__main__':
    main()
