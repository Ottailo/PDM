#!/usr/bin/env python3
"""
PDM Real-World Factory Floor Edge Feeder
========================================

Simulates multiple independent industrial edge PLC transmitters connected
to factory machinery. Transmits genuine edge telemetry bursts to PDM /api/ingest
over HTTP, proving that PDM runs 100% on passive real-world telemetry without
any internal synthetic backend simulator thread.

Supported Capabilities:
- Multi-Asset Multi-Line Ingestion (FILLING, PACKAGING, CAPPING)
- Real-World Sensor Physics & Thermal Inertia
- Induced Edge Disconnects (to trigger and test the Watchdog Signal Dropped state)
- Induced Mechanical Degradation (to test mechatronic alerts & OmniRoute diagnostics)
"""

import os
import sys
import time
import math
import random
import argparse
import json
import logging
from datetime import datetime

try:
    import urllib.request
    import urllib.error
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [EDGE-FEEDER] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("FactoryFloorFeeder")

# Industrial Machine Profiles
MACHINERY_SPECS = {
    "FILLING_001": {
        "type": "FILLING",
        "line": "Line 1 - Bottling",
        "base_sensors": {
            "Speed": {"mean": 1450.0, "noise": 12.0, "unit": "RPM"},
            "Temperature": {"mean": 62.5, "noise": 0.8, "unit": "°C"},
            "Pressure": {"mean": 4.2, "noise": 0.15, "unit": "bar"},
            "Vibration": {"mean": 0.38, "noise": 0.04, "unit": "mm/s"}
        }
    },
    "PACKAGING_001": {
        "type": "PACKAGING",
        "line": "Line 2 - End of Line",
        "base_sensors": {
            "Speed": {"mean": 820.0, "noise": 8.0, "unit": "RPM"},
            "Temperature": {"mean": 48.0, "noise": 0.5, "unit": "°C"},
            "Pressure": {"mean": 3.8, "noise": 0.1, "unit": "bar"},
            "Vibration": {"mean": 0.22, "noise": 0.03, "unit": "mm/s"}
        }
    },
    "CAPPING_001": {
        "type": "CAPPING",
        "line": "Line 1 - Bottling",
        "base_sensors": {
            "Speed": {"mean": 1200.0, "noise": 10.0, "unit": "RPM"},
            "Temperature": {"mean": 55.0, "noise": 0.6, "unit": "°C"},
            "Pressure": {"mean": 5.1, "noise": 0.2, "unit": "bar"},
            "Vibration": {"mean": 0.29, "noise": 0.03, "unit": "mm/s"}
        }
    }
}

class EdgeTransmitter:
    def __init__(self, target_url: str, api_key: str):
        self.target_url = target_url
        self.api_key = api_key
        self.cycle_count = 0
        self.temperature_states = {mid: spec["base_sensors"]["Temperature"]["mean"] for mid, spec in MACHINERY_SPECS.items()}
        self.vibration_drifts = {mid: 0.0 for mid in MACHINERY_SPECS}

    def generate_packet(self, machine_id: str, induce_anomaly: bool = False) -> dict:
        spec = MACHINERY_SPECS[machine_id]
        readings = {}

        if induce_anomaly:
            # Mechanical Bearing Degradation Signature:
            # Exponentially increasing vibration + rising bearing friction thermal dissipation
            self.vibration_drifts[machine_id] += 0.08
            thermal_load = self.vibration_drifts[machine_id] * 4.5
        else:
            self.vibration_drifts[machine_id] = max(0.0, self.vibration_drifts[machine_id] - 0.02)
            thermal_load = 0.0

        for sensor_name, cfg in spec["base_sensors"].items():
            noise = random.gauss(0, cfg["noise"])
            if sensor_name == "Temperature":
                # Thermal inertia smoothing: dT = (target - current) * alpha
                target_temp = cfg["mean"] + thermal_load + noise
                self.temperature_states[machine_id] += (target_temp - self.temperature_states[machine_id]) * 0.15
                readings[sensor_name] = round(self.temperature_states[machine_id], 2)
            elif sensor_name == "Vibration":
                readings[sensor_name] = round(cfg["mean"] + self.vibration_drifts[machine_id] + abs(noise), 3)
            elif sensor_name == "Speed":
                readings[sensor_name] = round(cfg["mean"] + noise, 1)
            elif sensor_name == "Pressure":
                readings[sensor_name] = round(cfg["mean"] + noise, 2)
            else:
                readings[sensor_name] = round(cfg["mean"] + noise, 2)

        return {
            "machine_id": machine_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "readings": readings,
            "edge_gateway_id": f"GW_LINE_{spec['line'][:6].replace(' ', '_')}"
        }

    def transmit(self, payload: dict) -> bool:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            self.target_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-API-Key": self.api_key,
                "User-Agent": "PDM-FactoryFloorFeeder/2.0"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return resp.status in (200, 201)
        except Exception as e:
            logger.warning(f"Transmission failed for {payload.get('machine_id')}: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="PDM Factory Floor Edge Feeder")
    parser.add_argument("--target-url", default="http://localhost:5000/api/ingest", help="PDM API ingest endpoint")
    parser.add_argument("--api-key", default="dev-api-key", help="API Key for ingestion")
    parser.add_argument("--interval", type=float, default=2.0, help="Burst interval in seconds")
    parser.add_argument("--bursts", type=int, default=0, help="Total burst cycles (0 for continuous)")
    parser.add_argument("--drop-machine", default="", help="Machine ID to drop after 5 cycles (to test watchdog)")
    parser.add_argument("--anomaly-machine", default="", help="Machine ID to induce mechanical bearing wear on")
    args = parser.parse_args()

    transmitter = EdgeTransmitter(args.target_url, args.api_key)
    logger.info(f"Targeting PDM Ingest: {args.target_url}")
    logger.info(f"Active Factory Machines: {list(MACHINERY_SPECS.keys())}")
    if args.drop_machine:
        logger.info(f"Configured Drop Test: {args.drop_machine} will halt transmission after cycle 5")
    if args.anomaly_machine:
        logger.info(f"Configured Anomaly Test: Inducing bearing wear on {args.anomaly_machine}")

    cycle = 0
    try:
        while True:
            cycle += 1
            logger.info(f"--- Cycle #{cycle} Ingestion Burst ---")
            
            for machine_id in MACHINERY_SPECS:
                # Watchdog Drop Test Simulation
                if args.drop_machine == machine_id and cycle > 5:
                    logger.warning(f"[{machine_id}] SIMULATING CUT CABLE / PLC HALT. Transmission withheld.")
                    continue

                induce = (args.anomaly_machine == machine_id and cycle > 3)
                packet = transmitter.generate_packet(machine_id, induce_anomaly=induce)
                success = transmitter.transmit(packet)
                
                status_str = "ACK 200" if success else "ERR"
                vib = packet["readings"].get("Vibration", 0.0)
                temp = packet["readings"].get("Temperature", 0.0)
                logger.info(f"  [{machine_id}] {status_str} | Vib: {vib} mm/s | Temp: {temp} °C")

            if args.bursts > 0 and cycle >= args.bursts:
                logger.info(f"Completed {args.bursts} burst cycles. Feeder terminating.")
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        logger.info("Feeder stopped by operator.")

if __name__ == "__main__":
    main()
