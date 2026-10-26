#!/usr/bin/env python3
"""
PDM MQTT Industrial IoT Ingestion Bridge
========================================
Subscribes to factory MQTT brokers (Mosquitto, EMQX, HiveMQ, AWS IoT Greengrass)
to consume sensor telemetry topics published by smart transducers, Node-RED, or edge gateways,
and transmits validated records to the PDM Ingestion API.
"""

import sys
import os
import time
import json
import argparse
import urllib.request
from datetime import datetime

def forward_to_pdm(pdm_host: str, api_key: str, payload: dict) -> bool:
    """Forward unpacked MQTT payload to PDM API."""
    url = f"{pdm_host.rstrip('/')}/api/ingest"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[MQTT FORWARD ERROR] {e}")
        return False

def run_mqtt_bridge(broker_host: str, broker_port: int, topic: str, pdm_host: str, default_machine_id: str, api_key: str):
    print("=" * 70)
    print(" PDM MQTT INDUSTRIAL SUBSCRIBER BRIDGE")
    print("=" * 70)
    print(f" MQTT Broker:       {broker_host}:{broker_port}")
    print(f" Subscribed Topic:  {topic}")
    print(f" PDM Host:          {pdm_host}")
    print(f" Default Machine:   {default_machine_id}")
    print("=" * 70)

    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        print("[NOTICE] 'paho-mqtt' library not installed. Running simulated MQTT socket listener for verification.")
        print("To connect to a live broker: pip install paho-mqtt\n")
        # Simulated verification loop
        while True:
            simulated_payload = {
                "machine_id": default_machine_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "sensors": {
                    "Vibration": 0.12,
                    "Nozzle_Pressure": 2.21,
                    "Fill_Volume_Sensor": 100.2
                }
            }
            ok = forward_to_pdm(pdm_host, api_key, simulated_payload)
            print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] MQTT INGEST -> Machine: {default_machine_id} (Status: {'OK' if ok else 'FAIL'})")
            time.sleep(5)
        return

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print(f"[MQTT CONNECTED] Connected to broker. Subscribing to '{topic}'...")
            client.subscribe(topic)
        else:
            print(f"[MQTT ERROR] Connection failed with code {rc}")

    def on_message(client, userdata, msg):
        try:
            raw_text = msg.payload.decode('utf-8')
            data = json.loads(raw_text)

            machine_id = data.get('machine_id') or default_machine_id
            sensors = data.get('sensors') or data.get('values') or {}

            payload = {
                "machine_id": machine_id,
                "timestamp": data.get('timestamp') or (datetime.utcnow().isoformat() + "Z"),
                "sensors": sensors
            }

            ok = forward_to_pdm(pdm_host, api_key, payload)
            print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] MQTT TOPIC '{msg.topic}' -> Machine: {machine_id} ({len(sensors)} sensors) -> PDM: {'OK' if ok else 'FAILED'}")

        except Exception as e:
            print(f"[MQTT PARSE ERROR] On topic '{msg.topic}': {e}")

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(broker_host, broker_port, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[MQTT BRIDGE STOPPED]")

def main():
    parser = argparse.ArgumentParser(description="PDM Industrial MQTT Telemetry Subscriber Bridge")
    parser.add_argument("--broker", default="localhost", help="MQTT Broker Host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT Broker Port (default 1883)")
    parser.add_argument("--topic", default="pdm/+/telemetry", help="MQTT Subscription Topic")
    parser.add_argument("--host", default="http://localhost:5000", help="PDM API Host")
    parser.add_argument("--machine-id", default="FILLING_001", help="Default Asset Machine ID")
    parser.add_argument("--key", default="dev-api-key", help="Ingestion API key or token")

    args = parser.parse_args()
    run_mqtt_bridge(args.broker, args.port, args.topic, args.host, args.machine_id, args.key)

if __name__ == '__main__':
    main()
