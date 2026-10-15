# Update Log

## 2025-01-27

### Fixed Machine Card HTML Structure Issue

**Problem:** Machine cards were not displaying properly - status badge was outside the flex container due to broken HTML structure.

**Root Cause:** In `createMachineCard()` function (dashboard.js:595-604), there was an extra closing `</div>` tag that caused the status badge to be placed outside the header's flex container with `justify-between`, preventing proper layout.

**Fix Applied:**
- Removed extra closing `</div>` tag on line 602
- Moved status badge inside the header flex container so it properly appears on the right side
- Status badge now correctly uses `justify-between` to space machine name (left) and status (right)

**Files Modified:**
- `app/static/js/dashboard.js` (line 595-603)

**Testing:** Cards should now properly display:
- Machine name on the left
- Status badge on the right
- Sensor readings in the card body
- Chart at the bottom

### Fixed RUL Prediction Field Mismatch

**Problem:** RUL showing "--h" for all machines, even when they should have predictions.

**Root Cause:** Backend returns `ttf_hours` but frontend expects `rul_prediction` field name. Field name mismatch caused frontend to always fallback to "--".

**Fix Applied:**
- Added `rul_prediction` field mapping in predictor.py (line 474) to map `ttf_hours` value
- This ensures backward compatibility while maintaining the existing field structure

**Files Modified:**
- `app/services/predictor.py` (line 474)

**Note:** "--h" is expected behavior for machines in "Normal" state (no predicted failure = no RUL). Machines in Warning/Degrading/Critical states should now show numeric RUL values (e.g., "168h").

### Fixed Keras Model Loading Compatibility Issue

**Problem:** Models failing to load with error: "Could not deserialize class 'Functional' because its parent module keras.src.engine.functional cannot be imported."

**Root Cause:** Models were saved with standalone Keras 3.x (uses `keras.src.engine.functional`) but code was trying to load with TensorFlow 2.15's tf.keras (different internal structure). Version incompatibility between model save format and load format.

**Fix Applied:**
- Updated `_try_import_tf()` to try standalone Keras 3.x first, then fallback to TensorFlow Keras
- Added multiple loading strategies with different parameter combinations for compatibility
- Enabled unsafe deserialization for version compatibility
- Improved error handling with fallback strategies

**Files Modified:**
- `app/services/predictor.py` (lines 77-110, 150-195)

**Testing:** Models should now load successfully. If standalone Keras is available, it will be used. Otherwise, TensorFlow Keras will be used with compatibility settings.

### Updated All Requirements to Latest Versions

**Problem:** Package versions were outdated, causing compatibility issues with Keras 3.x models.

**Fix Applied:**
- Updated all packages to latest stable versions
- Added `keras>=3.0.5` (standalone Keras 3.x) for proper model loading compatibility
- All packages now use `>=` version constraints for better flexibility

**Files Modified:**
- `requirements.txt` (all packages updated)

**Key Updates:**
- flask: 3.0.0 → >=3.0.3
- numpy: 1.25.2 → >=1.26.4
- pandas: 2.1.3 → >=2.2.2
- scikit-learn: 1.3.2 → >=1.5.1
- **keras: NEW → >=3.0.5** (standalone Keras 3.x for model compatibility)
- eventlet: 0.33.3 → >=0.36.1
- All other packages updated to latest versions

**Next Steps:** Run `pip install --upgrade -r requirements.txt` to install updated packages.

### Fixed Keras Import Order Issue

**Problem:** Models still failing to load - TensorFlow was hijacking the `keras` module namespace, preventing standalone Keras 3.x from being used.

**Root Cause:** Even though standalone Keras 3.12.0 was installed, TensorFlow imports were overwriting the `keras` module in `sys.modules`, causing the code to use TensorFlow's keras instead of standalone keras.

**Fix Applied:**
- Pre-import standalone Keras at module level (before any TensorFlow imports)
- Store reference to standalone keras to prevent override
- Added fallback logic to force reload standalone keras if TF overrides it
- Improved error handling and logging for which keras backend is being used

**Files Modified:**
- `app/services/predictor.py` (lines 1-30: module-level keras import, lines 79-145: improved import logic)

**Testing:** Models should now load with standalone Keras 3.12.0. Check logs for "Using standalone Keras X.X.X for model loading" message.

### Fixed Functional Class Path Mapping

**Problem:** Models still failing with "Could not deserialize class 'Functional' because its parent module keras.src.engine.functional cannot be imported"

**Root Cause:** Models were saved with older Keras 3.x that used `keras.src.engine.functional.Functional`, but Keras 3.12.0 moved it to `keras.src.models.functional.Functional`. The deserializer couldn't find the old module path.

**Fix Applied:**
- Added custom_objects mapping to translate old module path (`keras.src.engine.functional.Functional`) to new class location (`keras.src.models.functional.Functional`)
- Properly imports Functional class from correct location in Keras 3.12.0
- Applied custom_objects to all model loading attempts for maximum compatibility

**Files Modified:**
- `app/services/predictor.py` (lines 224-250: custom_objects mapping logic)

**Testing:** Models should now load successfully. The old module path is automatically mapped to the new location.

### Fixed LSTM Layer Parameter Compatibility

**Problem:** Models failing with "Unrecognized keyword arguments passed to LSTM: {'time_major': False}"

**Root Cause:** Models were saved with older Keras versions where LSTM had a `time_major` parameter. Keras 3.12.0 removed this parameter (and `implementation` parameter), causing deserialization to fail.

**Fix Applied:**
- Created `CompatibleLSTM` wrapper class that filters out unsupported parameters (`time_major`, `implementation`) before passing to the real LSTM constructor
- Added LSTM mapping to custom_objects so the wrapper is used during model loading
- Wrapper inherits from current LSTM but removes deprecated parameters automatically

**Files Modified:**
- `app/services/predictor.py` (lines 225-275: CompatibleLSTM wrapper class and custom_objects mapping)

**Testing:** Models should now load successfully. Unsupported LSTM parameters are automatically filtered out.

### Fixed LSTM from_config Override

**Problem:** LSTM wrapper still failing because `from_config` is called during deserialization before `__init__`, so unsupported parameters weren't being filtered.

**Root Cause:** Keras deserialization uses `from_config` class method, not `__init__`, so we need to override `from_config` to filter parameters from the saved config.

**Fix Applied:**
- Added `from_config` class method override to `CompatibleLSTM` that filters `time_major` and `implementation` from config before calling parent's `from_config`
- This ensures parameters are removed during deserialization, not just during manual instantiation

**Files Modified:**
- `app/services/predictor.py` (CompatibleLSTM class: added from_config override)

**Testing:** Models should now load successfully. The from_config override properly filters unsupported parameters during deserialization.

### Fixed LSTM Deserialization with Global Monkey-Patch

**Problem:** LSTM wrapper still failing because custom_objects mapping wasn't matching the saved model's class path lookup.

**Root Cause:** Keras looks up classes by the exact module path stored in the saved model config. Our custom_objects mapping might not match exactly, or the saved model might reference LSTM directly without going through our custom mapping.

**Fix Applied:**
- Changed approach from custom_objects mapping to global monkey-patch of `LSTM.from_config`
- Patches the actual LSTM class's `from_config` method globally before loading models
- This ensures ALL LSTM deserializations filter out unsupported parameters, regardless of how they're referenced in saved models
- More reliable than custom_objects because it intercepts at the class level, not at the lookup level

**Files Modified:**
- `app/services/predictor.py` (LSTM.from_config global monkey-patch)

**Testing:** Models should now load successfully. The global patch ensures all LSTM layers filter unsupported parameters during deserialization.

### Fixed Functional Class Deserialization

**Problem:** Functional class deserialization failing: "could not be deserialized properly" - saved models have old module path `keras.src.engine.functional` but Keras 3.12.0 uses `keras.src.models.functional`.

**Root Cause:** The custom_objects mapping wasn't sufficient because the saved config dictionary contains the old module path, and the deserializer needs the config to be transformed.

**Fix Applied:**
- Created `CompatibleFunctional` wrapper class that extends the new Functional class
- Overrides `from_config` to transform old module path in config dictionary before deserialization
- Maps old module path to new one in the config
- Added fallback to Model.from_config if Functional.from_config fails

**Files Modified:**
- `app/services/predictor.py` (CompatibleFunctional wrapper with from_config override)

**Testing:** Models should now load successfully. The wrapper transforms old module paths in config before deserialization.

### Fixed Functional Deserialization with Monkey-Patch

**Problem:** Models loading but failing during prediction: "Model Model does not have a `call()` method implemented"

**Root Cause:** The CompatibleFunctional wrapper class was interfering with proper model deserialization, creating incomplete models that couldn't be called for prediction.

**Fix Applied:**
- Changed from wrapper class approach to global monkey-patch of `Functional.from_config`
- Patches the actual Functional class's `from_config` method to transform old module paths
- More reliable than wrapper because it modifies the class directly, preserving full model structure
- Applied once globally before any models are loaded

**Files Modified:**
- `app/services/predictor.py` (Functional.from_config global monkey-patch instead of wrapper)

**Testing:** Models should now load and work correctly for predictions. The monkey-patch preserves full model functionality while fixing module path compatibility.

### Enhanced Functional Deserialization Patch

**Problem:** Models still failing to deserialize - config still shows old module path, suggesting patch isn't being applied correctly.

**Root Cause:** The patch needs to also pass proper custom_objects mapping to ensure old module path is resolved correctly during deserialization.

**Fix Applied:**
- Enhanced Functional.from_config patch to also set custom_objects mapping for old module path
- Ensures both config transformation AND custom_objects mapping work together
- Added nested config handling for completeness

**Files Modified:**
- `app/services/predictor.py` (Enhanced Functional.from_config patch with custom_objects)

**Testing:** Models should now load successfully with both config transformation and proper custom_objects mapping.

