"""
OmniRoute LLM Cognitive Advisory & Diagnostic Service.
Analyzes physical machine telemetry, sensor deviations, and failure modes
to provide precision mechatronic root-cause analysis and repair guidance.
"""
import os
import json
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

OMNIROUTE_URL = os.environ.get("OMNIROUTE_URL", "http://127.0.0.1:20129/v1/chat/completions")
OMNIROUTE_API_KEY = os.environ.get("OMNIROUTE_API_KEY", "sk-9ebfedc343ccc674-f1fdcc-800831f5")
PREFERRED_MODELS = [
    "auto/best-fast",
    "agy/gemini-2.5-flash",
    "groq/llama-3.3-70b-versatile",
    "infron/deepseek-v4.1-flash"
]

class LLMDiagnosticAdvisor:
    """Provides LLM-driven mechatronic diagnostics and action planning via OmniRoute."""

    @classmethod
    def generate_diagnosis(cls, machine_id, telemetry_context):
        """
        Generate diagnostic advisory for a specific asset given its telemetry state.
        
        telemetry_context dictionary schema:
        {
            'machine_type': str,
            'state': str,
            'predicted_failure': str,
            'rul_prediction': float/int/str,
            'health_score': float,
            'sensor_readings': dict,
            'thresholds': dict,
            'recent_events': list
        }
        """
        machine_type = telemetry_context.get('machine_type', 'PACKAGING_ASSET')
        state = telemetry_context.get('state', 'Normal')
        failure = telemetry_context.get('predicted_failure') or 'Sensor Variance / Component Wear'
        rul = telemetry_context.get('rul_prediction') or telemetry_context.get('ttf_hours') or 'Normal'
        health = round(float(telemetry_context.get('health_score', 1.0)) * 100, 1)
        sensor_readings = telemetry_context.get('sensor_readings', {})
        thresholds = telemetry_context.get('thresholds', {})
        recent_events = telemetry_context.get('recent_events', [])

        # Try OmniRoute LLM first
        llm_response = cls._query_omniroute(
            machine_id=machine_id,
            machine_type=machine_type,
            state=state,
            failure=failure,
            rul=rul,
            health=health,
            sensor_readings=sensor_readings,
            thresholds=thresholds,
            recent_events=recent_events
        )

        if llm_response:
            return llm_response

        # Grounded fallback if OmniRoute is offline
        logger.info(f"Using deterministic engineering fallback for {machine_id} diagnostics")
        return cls._deterministic_fallback(
            machine_id=machine_id,
            machine_type=machine_type,
            state=state,
            failure=failure,
            rul=rul,
            sensor_readings=sensor_readings,
            thresholds=thresholds
        )

    @classmethod
    def _query_omniroute(cls, machine_id, machine_type, state, failure, rul, health, sensor_readings, thresholds, recent_events):
        prompt = f"""
You are the Chief Mechatronics & Plant Reliability Engineer for a high-speed discrete packaging plant.
Analyze the live sensor telemetry and predictive neural network outputs for physical asset `{machine_id}` ({machine_type}).

CURRENT ASSET STATUS:
- Operational State: {state}
- Health Score: {health}%
- Remaining Useful Life (RUL): {rul} hours
- Neural Fault Signature: {failure}

LIVE SENSOR READINGS:
{json.dumps(sensor_readings, indent=2)}

CALIBRATED THRESHOLDS:
{json.dumps(thresholds, indent=2)}

RECENT EVENT LOGS:
{json.dumps(recent_events[:4], indent=2)}

TASK:
Produce a deterministic, highly technical engineering diagnosis. Pinpoint the mechanical or electrical failure mechanism, cite the exact sensor readings exceeding nominal thresholds, list the immediate physical safety/inspection steps, required replacement parts, and estimated repair duration.

Respond with pure JSON only in the following schema (no markdown wrappers, no raw text outside JSON):
{{
    "diagnosis_title": "Concise technical diagnosis title (e.g. Orifice Cavitation & Nozzle Restriction)",
    "severity": "CRITICAL" | "WARNING" | "NOMINAL",
    "physical_root_cause": "Detailed mechatronic explanation of what is degrading and why based on the numbers.",
    "evidence": [
        "Sensor Channel X reading Y exceeds threshold Z"
    ],
    "immediate_actions": [
        "Step 1: Immediate safety or isolation action",
        "Step 2: Physical inspection step",
        "Step 3: Verification or calibration step"
    ],
    "required_spare_parts": [
        "Part name with specification"
    ],
    "estimated_downtime_minutes": 35,
    "operational_risk": "Specific risk if operation continues (e.g. motor winding burnout, seal blowout)"
}}
"""
        headers = {
            "Authorization": f"Bearer {OMNIROUTE_API_KEY}",
            "Content-Type": "application/json"
        }

        # Try available models in sequence
        for model in PREFERRED_MODELS:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a plant mechatronics reliability AI that outputs strictly valid JSON without markdown formatting."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,
                "max_tokens": 1000
            }

            try:
                resp = requests.post(OMNIROUTE_URL, headers=headers, json=payload, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data['choices'][0]['message']['content'].strip()
                    # Strip any markdown code fences if present
                    if content.startswith("```"):
                        content = content.strip("`")
                        if content.startswith("json"):
                            content = content[4:].strip()
                    result = json.loads(content)
                    result["advisor_provider"] = f"OmniRoute LLM ({model})"
                    result["timestamp"] = datetime.utcnow().isoformat()
                    return result
            except Exception as e:
                logger.debug(f"OmniRoute model {model} attempt failed: {e}")
                continue

        return None

    @classmethod
    def _deterministic_fallback(cls, machine_id, machine_type, state, failure, rul, sensor_readings, thresholds):
        """Grounded domain expert rules if LLM endpoint is unavailable."""
        evidence = []
        for s_name, s_val in sensor_readings.items():
            thresh = thresholds.get(s_name, {})
            crit = thresh.get('crit')
            warn = thresh.get('warn')
            if crit is not None and s_val > crit:
                evidence.append(f"{s_name} reading {s_val:.2f} breaches CRITICAL boundary ({crit})")
            elif warn is not None and s_val > warn:
                evidence.append(f"{s_name} reading {s_val:.2f} breaches WARNING envelope ({warn})")

        if not evidence:
            evidence.append(f"Model sequence tracking detected anomalous trajectory matching `{failure}` signature.")

        # Domain specific presets
        actions_map = {
            "Nozzle Clog": [
                "De-energize pneumatic manifold and depressurize liquid supply line.",
                "Inspect rotary nozzle orifices for particulate crystallization or particulate buildup.",
                "Execute CIP (Clean-in-Place) hot caustic flush cycle and verify flow transducer response."
            ],
            "Pump Wear": [
                "Isolate positive displacement pump motor drive at local disconnect.",
                "Measure radial and axial bearing play using dial indicator on drive shaft.",
                "Inspect mechanical shaft seals for weeping fluid and repack seal housing."
            ],
            "Conveyor Belt Stretch": [
                "Check belt tensioner take-up screw elongation and calibrate tracking guide rollers.",
                "Inspect drive motor gearbox for thermal degradation and lubrication loss.",
                "Verify optical encoder pulse synchronization with line tachometer."
            ],
            "Heater Element Degradation": [
                "Lock out main 480V circuit breaker to thermal tunnel heating banks.",
                "Perform resistance measurement (ohms) across each heating element ceramic core.",
                "Inspect thermocouple probe tip for physical oxidation or thermal boundary drift."
            ]
        }

        parts_map = {
            "Nozzle Clog": ["Nozzle Tip Assembly (Part #NZL-316L)", "PTFE O-Ring Kit", "Orifice Ultrasonic Cleaning Solvent"],
            "Pump Wear": ["Positive Displacement Pump Impeller", "Silicon Carbide Mechanical Seal", "SKF 6205 Deep Groove Ball Bearing"],
            "Conveyor Belt Stretch": ["Modular Link Belt Section (2m)", "Idler Sprocket Set", "Self-Aligning Take-Up Bearing Units"],
            "Heater Element Degradation": ["Ceramic Incoloy 800 Heating Element (3.5kW)", "Type K Mineral Insulated Thermocouple", "Solid State Relay 40A"]
        }

        actions = actions_map.get(failure, [
            "Initiate physical diagnostic lockout and verify line safety interlocks.",
            "Inspect mechanical assemblies and drive couplings for abnormal friction or play.",
            "Recalibrate analog sensor loop transmitters and verify 4-20mA calibration curves."
        ])

        parts = parts_map.get(failure, [
            f"{machine_type} Standard Mechanical Service Kit",
            "Vibration Isolator Damper Mounts",
            "Transducer Calibration Harness"
        ])

        severity = "CRITICAL" if state in ["Critical Failure Imminent", "Critical"] else ("WARNING" if state in ["Warning", "Degrading"] else "NOMINAL")

        return {
            "diagnosis_title": f"{failure} Diagnostic Analysis ({machine_id})",
            "severity": severity,
            "physical_root_cause": f"Observed sensor variance on {machine_id} indicates progressive mechanical wear and anomalous hydraulic/pneumatic impedance characteristic of {failure}.",
            "evidence": evidence,
            "immediate_actions": actions,
            "required_spare_parts": parts,
            "estimated_downtime_minutes": 30 if severity == "WARNING" else 50,
            "operational_risk": f"Continued operation under {state} condition risks unrecoverable line jam, actuator seizure, and cascade product contamination.",
            "advisor_provider": "PDM Embedded Physics Engine (Grounded Offline Rules)",
            "timestamp": datetime.utcnow().isoformat()
        }
