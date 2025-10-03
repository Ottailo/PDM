"""
Configuration constants for machines, sensors, and failure modes.
This file defines the flexible machine configuration system.
"""

# Machine definitions - easily extensible for new machine types
MACHINES = {
    "FILLING": [f"FILLING_{i+1:03d}" for i in range(3)],
    "SHRINK": [f"SHRINK_{i+1:03d}" for i in range(2)],
    "PILLOW": [f"PILLOW_{i+1:03d}" for i in range(4)],
    "BOXING": [f"BOXING_{i+1:03d}" for i in range(1)]
}

# Sensor configurations - defines sensors for each machine type
SENSOR_CONFIG = {
    "FILLING": {
        "Fill_Volume_Sensor": {
            "mean": 100.0,
            "std_dev": 0.2,
            "unit": "mL",
            "warn_threshold": 99.5,
            "crit_threshold": 99.0
        },
        "Nozzle_Pressure": {
            "mean": 2.0,
            "std_dev": 0.1,
            "unit": "bar",
            "warn_threshold": 2.2,
            "crit_threshold": 2.5
        },
        "Vibration": {
            "mean": 0.5,
            "std_dev": 0.05,
            "unit": "mm/s",
            "warn_threshold": 0.7,
            "crit_threshold": 0.9
        }
    },
    "SHRINK": {
        "Tunnel_Temperature": {
            "mean": 180.0,
            "std_dev": 2.0,
            "unit": "°C",
            "warn_threshold": 175.0,
            "crit_threshold": 170.0
        },
        "Conveyor_Speed": {
            "mean": 15.0,
            "std_dev": 0.1,
            "unit": "m/min",
            "warn_threshold": 14.8,
            "crit_threshold": 14.5
        },
        "Humidity": {
            "mean": 40.0,
            "std_dev": 1.0,
            "unit": "%",
            "warn_threshold": 45.0,
            "crit_threshold": 50.0
        }
    },
    "PILLOW": {
        "Sealing_Jaw_Temperature": {
            "mean": 160.0,
            "std_dev": 1.5,
            "unit": "°C",
            "warn_threshold": 157.0,
            "crit_threshold": 155.0
        },
        "Sealing_Jaw_Pressure": {
            "mean": 5.0,
            "std_dev": 0.2,
            "unit": "bar",
            "warn_threshold": 4.8,
            "crit_threshold": 4.5
        },
        "Alignment_Error": {
            "mean": 0.1,
            "std_dev": 0.02,
            "unit": "mm",
            "warn_threshold": 0.15,
            "crit_threshold": 0.2
        }
    },
    "BOXING": {
        "Box_Pressure_Sensor": {
            "mean": 5.0,
            "std_dev": 0.3,
            "unit": "bar",
            "warn_threshold": 7.0,
            "crit_threshold": 7.5
        },
        "Conveyor_Speed_Sensor": {
            "mean": 17.5,
            "std_dev": 0.5,
            "unit": "m/min",
            "warn_threshold": 22.0,
            "crit_threshold": 23.0
        },
        "Box_Count_Sensor": {
            "mean": 125.0,
            "std_dev": 5.0,
            "unit": "boxes/min",
            "warn_threshold": 170.0,
            "crit_threshold": 180.0
        }
    }
}

# Failure modes with degradation effects and RCA steps
FAILURE_MODES = {
    "FILLING": {
        "Nozzle Clog": {
            "trends": {
                "Nozzle_Pressure": "increase",
                "Fill_Volume_Sensor": "decrease"
            },
            "recommendation": "Schedule nozzle cleaning procedure (Ref: Manual 7B).",
            "rca_steps": [
                "Check for residue at nozzle tip.",
                "Verify fluid viscosity.",
                "Inspect filter for blockages."
            ]
        },
        "Pump Failure": {
            "trends": {
                "Fill_Volume_Sensor": "decrease",
                "Vibration": "increase"
            },
            "recommendation": "Inspect pump motor and seals for wear.",
            "rca_steps": [
                "Listen for unusual bearing noise.",
                "Check motor temperature.",
                "Verify input power supply."
            ]
        }
    },
    "SHRINK": {
        "Heater Failure": {
            "trends": {
                "Tunnel_Temperature": "decrease"
            },
            "recommendation": "Inspect heating element and thermostat connections.",
            "rca_steps": [
                "Verify power to heating element.",
                "Check thermostat calibration."
            ]
        },
        "Conveyor Jam": {
            "trends": {
                "Conveyor_Speed": "decrease"
            },
            "recommendation": "Clear conveyor path of obstructions. Check motor for strain.",
            "rca_steps": [
                "Visually inspect for physical blockages.",
                "Check conveyor belt tension.",
                "Monitor motor amperage for spikes."
            ]
        }
    },
    "PILLOW": {
        "Seal Heater Failure": {
            "trends": {
                "Sealing_Jaw_Temperature": "decrease"
            },
            "recommendation": "Inspect sealing jaw heating element.",
            "rca_steps": [
                "Check for continuity on heating element.",
                "Verify wiring integrity."
            ]
        },
        "Pressure Drop": {
            "trends": {
                "Sealing_Jaw_Pressure": "decrease",
                "Alignment_Error": "increase"
            },
            "recommendation": "Check pneumatic lines for leaks.",
            "rca_steps": [
                "Perform leak test using soapy water.",
                "Verify compressor output pressure."
            ]
        }
    },
    "BOXING": {
        "Box Jam": {
            "trends": {
                "Conveyor_Speed_Sensor": "decrease",
                "Box_Count_Sensor": "decrease"
            },
            "recommendation": "Clear conveyor path and check for box accumulation.",
            "rca_steps": [
                "Visually inspect conveyor for jammed boxes.",
                "Check box dimensions against specifications.",
                "Verify conveyor alignment."
            ]
        },
        "Pressure System Failure": {
            "trends": {
                "Box_Pressure_Sensor": "decrease"
            },
            "recommendation": "Inspect pneumatic system and compressor.",
            "rca_steps": [
                "Check air compressor operation.",
                "Inspect pneumatic lines for leaks.",
                "Verify pressure regulator settings."
            ]
        }
    }
}

# Operational schedule
OPERATIONAL_DAYS = [0, 1, 2, 3, 4]  # Monday to Friday
OPERATIONAL_HOURS = (8, 17)  # 8 AM to 5 PM

# Event probabilities (per hour)
PROB_DEGRADE_START = 0.00005  # Probability of starting degradation per hour
PROB_OPERATOR_ERROR = 0.0001  # Probability of operator error per hour
PROB_SCHED_MAINTENANCE = 0.000005  # Probability of scheduled maintenance per hour

# State constants
DEGRADING_STATE_KEYWORD = "Degrading"

# Model configuration
MODEL_CONFIG = {
    "WINDOW_SIZE": 24,
    "MAX_RUL": 300,
    "EPOCHS": 100,
    "BATCH_SIZE": 64,
    "LEARNING_RATE": 0.001,
    "L2_REG_FACTOR": 0.001
}
