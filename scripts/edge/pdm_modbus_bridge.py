#!/usr/bin/env python3
"""
PDM Modbus TCP Industrial PLC Ingestion Bridge
==============================================
Connects directly to factory PLCs (Siemens S7, Schneider Modicon, Allen-Bradley, Beckhoff, Omron)
over Modbus TCP (Port 502) to read input/holding registers, unpack multi-byte floats/integers,
and stream structured telemetry packets to the PDM Ingestion API.
"""

import sys
import os
import time
import json
import socket
import struct
import argparse
import urllib.request
from datetime import datetime

# Default Modbus Register Mapping Specification
# Structure: { SensorName: { register: int, type: 'uint16'|'int16'|'float32', scale: float, offset: float } }
DEFAULT_REGISTER_MAP = {
    "Vibration": {"register": 40001, "type": "float32", "scale": 1.0, "offset": 0.0},
    "Nozzle_Pressure": {"register": 40003, "type": "float32", "scale": 0.01, "offset": 0.0},
    "Fill_Volume_Sensor": {"register": 40005, "type": "float32", "scale": 1.0, "offset": 0.0}
}

class PdmModbusTcpClient:
    """Lightweight pure-python Modbus TCP client without heavy dependencies."""
    def __init__(self, host: str, port: int = 502, unit_id: int = 1, timeout: float = 3.0):
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.timeout = timeout
        self.transaction_id = 0

    def read_holding_registers(self, start_address: int, count: int) -> list:
        """Read holding registers using Modbus Function Code 0x03."""
        self.transaction_id = (self.transaction_id + 1) % 65535
        # Modbus TCP Header: Transaction ID (2B), Protocol ID (2B = 0), Length (2B), Unit ID (1B)
        # PDU: Function Code (1B = 0x03), Start Addr (2B), Register Count (2B)
        mbap = struct.pack(">HHHB", self.transaction_id, 0, 6, self.unit_id)
        # Normalize zero-indexed address
        addr = start_address - 40001 if start_address >= 40001 else start_address
        pdu = struct.pack(">BHH", 3, addr, count)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(self.timeout)
            s.connect((self.host, self.port))
            s.sendall(mbap + pdu)
            response = s.recv(256)

        if len(response) < 9:
            raise ValueError(f"Incomplete Modbus response ({len(response)} bytes)")

        # Verify function code
        fn = response[7]
        if fn & 0x80:
            err_code = response[8]
            raise RuntimeError(f"Modbus Exception 0x{err_code:02X} returned by PLC")

        byte_count = response[8]
        register_bytes = response[9:9+byte_count]
        registers = struct.unpack(f">{len(register_bytes)//2}H", register_bytes)
        return list(registers)


def poll_modbus_and_forward(plc_host: str, plc_port: int, pdm_host: str, machine_id: str, api_key: str, interval: float, config_file: str = None):
    register_map = DEFAULT_REGISTER_MAP
    if config_file and os.path.exists(config_file):
        with open(config_file, 'r') as f:
            register_map = json.load(f)

    print("=" * 70)
    print(" PDM MODBUS TCP PLC TELEMETRY BRIDGE")
    print("=" * 70)
    print(f" PLC Target:        {plc_host}:{plc_port}")
    print(f" Target Machine:    {machine_id}")
    print(f" Ingestion Host:    {pdm_host}")
    print(f" Sampling Interval: {interval}s")
    print(f" Mapped Channels:   {len(register_map)} registers")
    for s_name, spec in register_map.items():
        print(f"  -> {s_name:<20} Reg: {spec.get('register')} ({spec.get('type')}) Scale: {spec.get('scale')}")
    print("=" * 70)

    client = PdmModbusTcpClient(plc_host, plc_port)
    ingest_url = f"{pdm_host.rstrip('/')}/api/ingest"

    while True:
        readings = {}
        try:
            for s_name, spec in register_map.items():
                reg = spec.get('register', 40001)
                r_type = spec.get('type', 'uint16')
                scale = spec.get('scale', 1.0)
                offset = spec.get('offset', 0.0)

                if r_type == 'float32':
                    raw_regs = client.read_holding_registers(reg, 2)
                    raw_bytes = struct.pack(">HH", raw_regs[0], raw_regs[1])
                    val = struct.unpack(">f", raw_bytes)[0]
                elif r_type == 'int16':
                    raw_regs = client.read_holding_registers(reg, 1)
                    val = struct.unpack(">h", struct.pack(">H", raw_regs[0]))[0]
                else:
                    raw_regs = client.read_holding_registers(reg, 1)
                    val = raw_regs[0]

                readings[s_name] = round(float(val) * scale + offset, 3)

            # Transmit to PDM
            payload = {
                "machine_id": machine_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "sensors": readings
            }
            req = urllib.request.Request(
                ingest_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={"Content-Type": "application/json", "X-API-Key": api_key},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] MODBUS POLL OK -> {readings}")

        except socket.error as se:
            print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] [PLC OFFLINE] Could not connect to Modbus PLC at {plc_host}:{plc_port} ({se})")
        except Exception as e:
            print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] [BRIDGE ERROR] {e}")

        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="PDM Industrial Modbus TCP Gateway Bridge")
    parser.add_argument("--plc-host", default="192.168.1.100", help="Modbus PLC IP Address")
    parser.add_argument("--plc-port", type=int, default=502, help="Modbus TCP Port (default 502)")
    parser.add_argument("--host", default="http://localhost:5000", help="PDM API Host")
    parser.add_argument("--machine-id", default="FILLING_001", help="Target Asset Machine ID")
    parser.add_argument("--key", default="dev-api-key", help="Ingestion API key or token")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling cycle in seconds")
    parser.add_argument("--config", default=None, help="JSON configuration file for register map")

    args = parser.parse_args()
    poll_modbus_and_forward(args.plc_host, args.plc_port, args.host, args.machine_id, args.key, args.interval, args.config)

if __name__ == '__main__':
    main()
