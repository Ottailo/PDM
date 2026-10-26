"""
Auto-Baseline Learner & Sensor Envelope Calibrator
==================================================
Calculates empirical baseline statistics (mean, variance, sigma thresholds)
from newly connected physical machines during real-world pilot onboarding.
Sets precision warning and critical envelopes to eliminate false positive alarms.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from app import db
from app.models.configuration import Asset, AssetSensor
from app.models.sensor_data import SensorData, EventLog

logger = logging.getLogger(__name__)

class BaselineCalibrator:
    """Calculates empirical statistical envelopes from operational telemetry."""

    @classmethod
    def calibrate_asset(cls, machine_id: str, sample_count: int = 200, sigma_warn: float = 2.5, sigma_crit: float = 3.5):
        """
        Calibrate sensor envelopes for a machine based on its most recent sensor history.
        """
        asset = Asset.query.filter_by(name=machine_id).first()
        if not asset:
            return False, {}, f"Asset '{machine_id}' not found in registry."

        if not asset.sensors:
            return False, {}, f"Asset '{machine_id}' has no registered sensor channels."

        channel_ids = [s.channel_id for s in asset.sensors if s and s.channel_id]
        search_ids = set(channel_ids)
        for cid in channel_ids:
            search_ids.add(f"{machine_id}_{cid}")
            parts = cid.split('_', 1)
            if len(parts) > 1:
                search_ids.add(f"{machine_id}_{parts[1]}")

        # Query recent readings
        records = (SensorData.query
                   .filter(SensorData.sensor_id.in_(list(search_ids)))
                   .order_by(SensorData.timestamp.desc())
                   .limit(sample_count * len(search_ids))
                   .all())

        if not records:
            return False, {}, f"Insufficient telemetry data for '{machine_id}'. Stream at least 20 readings first."

        # Aggregate values by channel
        channel_data = {}
        for r in records:
            if r is None or getattr(r, 'sensor_id', None) is None or getattr(r, 'value', None) is None:
                continue
            channel_data.setdefault(r.sensor_id, []).append(r.value)

        calibrated_results = {}

        for sensor in asset.sensors:
            vals = channel_data.get(sensor.channel_id) or []
            if not vals:
                s_name = sensor.sensor_template.name if sensor.sensor_template else sensor.channel_id
                for k, v in channel_data.items():
                    if k.endswith(s_name):
                        vals = v
                        break

            if len(vals) < 2:
                continue

            arr = np.array(vals)
            mean_val = float(np.mean(arr))
            std_val = float(np.std(arr))
            if std_val < 1e-4:
                std_val = max(0.01 * mean_val, 0.1)

            # Determine envelope bounds
            warn_high = round(mean_val + (sigma_warn * std_val), 2)
            crit_high = round(mean_val + (sigma_crit * std_val), 2)
            warn_low = round(max(0.0, mean_val - (sigma_warn * std_val)), 2)
            crit_low = round(max(0.0, mean_val - (sigma_crit * std_val)), 2)

            # Store in sensor config overrides
            overrides = sensor.config_overrides or {}
            overrides.update({
                "mean": round(mean_val, 2),
                "std": round(std_val, 3),
                "warn": warn_high,
                "crit": crit_high,
                "warn_low": warn_low,
                "crit_low": crit_low,
                "calibrated_samples": len(vals),
                "calibrated_at": datetime.utcnow().isoformat()
            })
            sensor.config_overrides = overrides

            s_name = sensor.sensor_template.name if sensor.sensor_template else sensor.channel_id
            calibrated_results[s_name] = {
                "mean": round(mean_val, 2),
                "std": round(std_val, 3),
                "warn": warn_high,
                "crit": crit_high,
                "samples": len(vals)
            }

        db.session.commit()

        # Log calibration event
        log = EventLog(
            timestamp=datetime.utcnow(),
            machine_id=machine_id,
            event_type='Calibration',
            details=f"Empirical baseline calibration completed for {machine_id} ({len(calibrated_results)} channels calibrated from {len(records)} readings)."
        )
        db.session.add(log)
        db.session.commit()

        logger.info(f"Calibrated asset {machine_id}: {calibrated_results}")
        return True, calibrated_results, f"Asset '{machine_id}' successfully calibrated across {len(calibrated_results)} channels."
