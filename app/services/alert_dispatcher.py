"""
Industrial Incident & Webhook / Telegram Alert Dispatcher
=========================================================
Monitors machine state transitions and broadcasts actionable dispatch tickets
to plant reliability teams via Webhooks (Slack/Teams/MaintainX) and Telegram.
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from app import db
from app.models.sensor_data import EventLog

logger = logging.getLogger(__name__)

# Cache for alert throttling: { machine_id: last_alert_timestamp }
_ALERT_COOLDOWN = {}
COOLDOWN_MINUTES = 5

class IndustrialAlertDispatcher:
    """Dispatches real-time mechatronic incident tickets to external channels."""

    @classmethod
    def dispatch_incident(cls, machine_id: str, state: str, telemetry: dict, diagnosis: dict = None):
        """
        Evaluate and dispatch an incident alert if machine state warrants intervention.
        """
        if state not in ["Critical Failure Imminent", "Warning", "Degrading"]:
            return False

        # Throttling check
        now = datetime.utcnow()
        last_sent = _ALERT_COOLDOWN.get(machine_id)
        if last_sent and (now - last_sent) < timedelta(minutes=COOLDOWN_MINUTES):
            logger.debug(f"Alert throttled for {machine_id} (last sent {(now - last_sent).seconds}s ago)")
            return False

        _ALERT_COOLDOWN[machine_id] = now

        # Extract incident parameters
        machine_type = telemetry.get('machine_type', 'ASSET')
        location = telemetry.get('location', 'Factory Floor')
        rul = telemetry.get('rul_prediction') or telemetry.get('ttf_hours') or 'N/A'
        health = round(float(telemetry.get('health_score', 1.0)) * 100, 1)
        fault_mode = telemetry.get('predicted_failure') or (diagnosis.get('diagnosis_title') if diagnosis else 'Telemetry Drift')

        severity_emoji = "CRITICAL TRIP IMMINENT" if state == "Critical Failure Imminent" else "EARLY WARNING DEGRADATION"

        ticket = {
            "timestamp": now.isoformat(),
            "machine_id": machine_id,
            "machine_type": machine_type,
            "location": location,
            "state": state,
            "health_score": health,
            "rul_hours": rul,
            "fault_mode": fault_mode,
            "root_cause": diagnosis.get('physical_root_cause') if diagnosis else "Sensor envelope breach",
            "recommended_parts": diagnosis.get('required_spare_parts', []) if diagnosis else [],
            "action_items": diagnosis.get('immediate_actions', []) if diagnosis else [
                "Inspect mechanical assembly for friction or vibration",
                "Verify safety interlocks and transducer calibration"
            ]
        }

        # 1. Log to DB EventLog
        try:
            event = EventLog(
                timestamp=now,
                machine_id=machine_id,
                event_type='Alert',
                details=f"[{state.upper()}] {fault_mode} detected on {machine_id} (Health: {health}%, RUL: {rul}h)."
            )
            db.session.add(event)
            db.session.commit()
        except Exception as db_err:
            logger.error(f"Error logging alert to EventLog: {db_err}")

        # 2. Dispatch to Webhook (if configured)
        webhook_url = os.environ.get("ALERT_WEBHOOK_URL")
        if webhook_url:
            cls._send_webhook(webhook_url, ticket)

        # 3. Dispatch to Telegram (if configured)
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_ALERT_CHAT_ID")
        if bot_token and chat_id:
            cls._send_telegram(bot_token, chat_id, ticket)

        return True

    @classmethod
    def _send_webhook(cls, webhook_url: str, ticket: dict):
        try:
            payload = {
                "text": f"[{ticket['state']}] PDM Incident Alert: {ticket['machine_id']} ({ticket['fault_mode']})",
                "incident": ticket
            }
            requests.post(webhook_url, json=payload, timeout=4)
            logger.info(f"Dispatched webhook alert for {ticket['machine_id']}")
        except Exception as e:
            logger.warning(f"Failed to dispatch webhook alert: {e}")

    @classmethod
    def _send_telegram(cls, bot_token: str, chat_id: str, ticket: dict):
        try:
            msg = (
                f"🚨 *PDM INDUSTRIAL INCIDENT ALERT*\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"*Asset:* `{ticket['machine_id']}` ({ticket['machine_type']})\n"
                f"*Location:* {ticket['location']}\n"
                f"*Status:* `{ticket['state']}`\n"
                f"*Health:* {ticket['health_score']}%\n"
                f"*Est. RUL:* {ticket['rul_hours']} hours\n"
                f"*Fault Mode:* {ticket['fault_mode']}\n\n"
                f"*Physical Root Cause:*\n{ticket['root_cause']}\n\n"
                f"*Action Checklist:*\n" + "\n".join([f"• {a}" for a in ticket['action_items'][:3]]) + "\n\n"
                f"*Required Parts:* {', '.join(ticket['recommended_parts']) if ticket['recommended_parts'] else 'Standard Inspection Kit'}"
            )
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}, timeout=4)
            logger.info(f"Dispatched Telegram alert for {ticket['machine_id']}")
        except Exception as e:
            logger.warning(f"Failed to dispatch Telegram alert: {e}")
