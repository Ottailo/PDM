# PDM (Predictive Maintenance) System - Complete Technical Analysis

**Version:** 1.0  
**Date:** December 2025  
**System:** Advanced Predictive Maintenance Platform for Manufacturing

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Technology Stack](#technology-stack)
4. [Database Schema](#database-schema)
5. [Application Components](#application-components)
6. [Data Flow & Processing](#data-flow--processing)
7. [Machine Learning System](#machine-learning-system)
8. [User Interface & Frontend](#user-interface--frontend)
9. [API Endpoints](#api-endpoints)
10. [Visual Design System](#visual-design-system)
11. [Business Logic & Workflows](#business-logic--workflows)
12. [Configuration & Setup](#configuration--setup)

---

## Executive Summary

The PDM (Predictive Maintenance) Dashboard is a real-time web application designed for predictive maintenance in manufacturing environments. It monitors multiple types of industrial machines (FILLING, SHRINK, PILLOW, BOXING), collects sensor data, uses machine learning to predict failures, and provides an interactive dashboard for operators and administrators.

### Key Features

- **Real-time Sensor Monitoring**: Continuous collection and display of sensor data from multiple machine types
- **Predictive Analytics**: ML-based failure prediction with Remaining Useful Life (RUL) estimation
- **Specific Failure Detection**: Identifies exact failure modes (e.g., "Nozzle Clog", "Pump Wear", "Conveyor Belt Stretch")
- **Interactive Dashboard**: Live charts, machine cards, and visual alerts
- **Service Request System**: Part-specific maintenance scheduling with time estimates
- **Multi-tenant Support**: Company-based machine management
- **Authentication & Authorization**: Role-based access control (admin, operator, viewer)
- **Data Simulation**: Built-in simulator for testing and development

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT BROWSER                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Dashboard   │  │  Admin Panel │  │   Login/Auth     │  │
│  │   (React)    │  │   (HTML)     │  │    (HTML)        │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                  │                   │             │
│         └──────────────────┴───────────────────┘             │
│                           │                                   │
└───────────────────────────┼───────────────────────────────────┘
                            │ HTTP/WebSocket
┌───────────────────────────┼───────────────────────────────────┐
│                    FLASK APPLICATION                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                   Flask-SocketIO                        │ │
│  │              (Real-time Updates)                        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   API Routes │  │   Services   │  │    Models        │  │
│  │  (Blueprints)│  │  (Business   │  │  (Database ORM)  │  │
│  │              │  │   Logic)     │  │                  │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                  │                   │             │
│         └──────────────────┴───────────────────┘             │
│                           │                                   │
└───────────────────────────┼───────────────────────────────────┘
                            │
┌───────────────────────────┼───────────────────────────────────┐
│                      DATABASE LAYER                           │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              SQLAlchemy ORM                             │ │
│  │  SQLite (Development) / PostgreSQL (Production)        │ │
│  └─────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│                    MACHINE LEARNING LAYER                     │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │         TensorFlow 2.15 (Keras Models)                 │ │
│  │  - GRU Recurrent Neural Networks                       │ │
│  │  - Scikit-learn Scalers                                │ │
│  │  - Model Directory: /models/{MACHINE_TYPE}/            │ │
│  └─────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

### Component Architecture

**Frontend Layer:**
- Vanilla JavaScript (ES6+) with Chart.js for visualizations
- Tailwind CSS for styling
- Template engine: Jinja2
- Real-time updates via polling (2-second intervals)

**Backend Layer:**
- Flask 3.0 application factory pattern
- Flask-SocketIO for WebSocket support (currently used for future expansion)
- SQLAlchemy ORM for database operations
- Flask-Login for authentication

**Data Processing:**
- DataSimulator: Generates realistic sensor data with degradation patterns
- PredictiveService: ML-based predictions with heuristic fallback
- Background thread for continuous data generation

---

## Technology Stack

### Backend Technologies

- **Python 3.x**: Core programming language
- **Flask 3.0.0**: Web framework
- **Flask-SQLAlchemy 3.1.1**: Database ORM
- **Flask-Migrate 4.1.0**: Database migrations (Alembic)
- **Flask-Login 0.6.3**: User session management
- **Flask-SocketIO 5.3.6**: WebSocket support for real-time updates
- **SQLAlchemy 2.0.23**: Database toolkit

### Machine Learning

- **TensorFlow 2.15.0**: Deep learning framework
- **NumPy 1.25.2**: Numerical computing
- **Pandas 2.1.3**: Data manipulation
- **Scikit-learn 1.3.2**: Data preprocessing (scalers)

### Frontend Technologies

- **Vanilla JavaScript**: Core client-side logic
- **Chart.js**: Interactive charts and graphs
- **Tailwind CSS**: Utility-first CSS framework
- **Google Fonts**: Inter, JetBrains Mono, Space Grotesk
- **Font Awesome 6.4.0**: Icons

### Database

- **SQLite**: Default development database (instance/maintenance.db)
- **PostgreSQL**: Production-ready alternative (via docker-compose.yml)

### Deployment

- **Gunicorn 23.0.0**: WSGI HTTP server
- **Docker**: Containerization (docker-compose.yml provided)
- **Eventlet 0.33.3**: Async networking for SocketIO

---

## Database Schema

### Entity Relationship Overview

```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│   Company   │────────<│   Machine    │         │     User     │
│             │ 1    N  │              │         │              │
│ - id        │         │ - id         │         │ - id         │
│ - name      │         │ - machine_id │         │ - username   │
│ - industry  │         │ - name       │         │ - email      │
│ - email     │         │ - type       │         │ - password   │
│ - phone     │         │ - company_id │         │ - role       │
└─────────────┘         └──────┬───────┘         │ - company_id │
                               │                 └──────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
       ┌────────┴────────┐          ┌─────────┴─────────┐
       │   SensorData    │          │   MachineState    │
       │                 │          │                   │
       │ - id            │          │ - id              │
       │ - timestamp     │          │ - machine_id      │
       │ - sensor_id     │          │ - status          │
       │ - value         │          │ - health_factor   │
       └─────────────────┘          │ - active_failure  │
                                    │ - event_steps     │
                                    └─────────┬─────────┘
                                              │
                                    ┌─────────┴─────────┐
                                    │    EventLog       │
                                    │                   │
                                    │ - id              │
                                    │ - timestamp       │
                                    │ - machine_id      │
                                    │ - event_type      │
                                    │ - details         │
                                    └───────────────────┘
```

### Core Tables

#### 1. **companies**
Multi-tenant support for different manufacturing companies.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Primary key |
| name | VARCHAR(100) | Company name |
| industry | VARCHAR(50) | Industry type |
| contact_email | VARCHAR(120) | Contact email |
| contact_phone | VARCHAR(20) | Contact phone |
| address | TEXT | Physical address |
| created_at | DATETIME | Record creation timestamp |
| is_active | BOOLEAN | Active status flag |

#### 2. **machines**
Machine inventory and configuration.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Primary key |
| machine_id | VARCHAR(50) UNIQUE | Unique machine identifier (e.g., "FILLING_001") |
| name | VARCHAR(100) | Display name |
| machine_type | VARCHAR(50) | Type: FILLING, SHRINK, PILLOW, BOXING |
| manufacturer | VARCHAR(100) | Manufacturer name |
| model | VARCHAR(100) | Model number |
| serial_number | VARCHAR(100) | Serial number |
| installation_date | DATETIME | Installation date |
| location | VARCHAR(200) | Physical location |
| status | VARCHAR(20) | Status: Active, Inactive, etc. |
| company_id | INTEGER (FK) | Foreign key to companies |
| sensor_config | JSON | Custom sensor configuration |
| thresholds | JSON | Alert thresholds |
| maintenance_schedule | JSON | Maintenance schedule |
| created_at | DATETIME | Record creation timestamp |
| updated_at | DATETIME | Last update timestamp |
| created_by | VARCHAR(100) | Creator username |

#### 3. **users**
Authentication and authorization.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Primary key |
| username | VARCHAR(64) UNIQUE | Unique username |
| email | VARCHAR(120) UNIQUE | Unique email |
| password_hash | VARCHAR(128) | Bcrypt password hash |
| role | VARCHAR(20) | Role: admin, operator, viewer |
| company_id | INTEGER (FK) | Foreign key to companies (optional) |
| created_at | DATETIME | Account creation timestamp |
| last_login | DATETIME | Last login timestamp |

#### 4. **sensor_data**
Time-series sensor readings.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Primary key |
| timestamp | DATETIME | Reading timestamp (indexed) |
| sensor_id | VARCHAR(100) | Sensor identifier (e.g., "FILLING_001_Fill_Volume_Sensor") (indexed) |
| value | FLOAT | Sensor reading value |

**Indexes:**
- Composite index on (sensor_id, timestamp) for fast time-series queries
- Index on timestamp for time-range queries

#### 5. **machine_state**
Current operational state of each machine.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Primary key |
| machine_id | VARCHAR(100) UNIQUE | Unique machine identifier |
| status | VARCHAR(50) | Status: Normal, Degrading, Off, Maintenance, Scheduled Maintenance, Operator Error |
| health_factor | FLOAT | Health score (0.0 to 1.0) |
| active_failure | JSON | Active failure mode details: `{"type": "Nozzle Clog", "progress": 0.5}` |
| event_steps_left | INTEGER | Steps remaining for current event (e.g., maintenance duration) |
| last_updated | DATETIME | Last state update timestamp |

**Status Values:**
- `Normal`: Operating normally
- `Degrading`: ML prediction indicates degradation
- `Off`: Machine is powered off
- `Maintenance`: Currently under maintenance
- `Scheduled Maintenance`: Scheduled maintenance period
- `Operator Error`: Temporary operator-induced issue

#### 6. **event_log**
System events and state changes.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Primary key |
| timestamp | DATETIME | Event timestamp (indexed) |
| machine_id | VARCHAR(100) | Machine identifier (indexed) |
| event_type | VARCHAR(50) | Event type (indexed) |
| details | TEXT | Event description |

**Indexes:**
- Index on timestamp for chronological queries
- Composite index on (machine_id, event_type) for filtering

#### 7. **maintenance_records**
Historical maintenance activity.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Primary key |
| machine_id | VARCHAR(50) | Machine identifier |
| maintenance_type | VARCHAR(50) | Type: preventive, corrective, emergency |
| description | TEXT | Maintenance description |
| performed_by | VARCHAR(100) | Technician name |
| duration_hours | FLOAT | Maintenance duration |
| cost | FLOAT | Maintenance cost |
| parts_replaced | JSON | Array of replaced parts |
| notes | TEXT | Additional notes |
| scheduled_date | DATETIME | Scheduled date |
| completed_date | DATETIME | Completion date |
| created_at | DATETIME | Record creation timestamp |
| company_id | INTEGER (FK) | Foreign key to companies |

---

## Application Components

### Directory Structure

```
PDM/
├── app/                          # Main application package
│   ├── __init__.py              # Application factory
│   ├── packages.py              # Blueprint definitions
│   ├── api/                     # API endpoints
│   │   ├── routes.py           # Main API routes
│   │   ├── auth.py             # Authentication endpoints
│   │   ├── admin.py            # Admin panel endpoints
│   │   ├── ingest.py           # Data ingestion API
│   │   └── machine_management.py # Machine CRUD operations
│   ├── config/                  # Configuration
│   │   └── machine_config.py   # Machine types, sensors, failures
│   ├── models/                  # Database models
│   │   ├── sensor_data.py      # SensorData, EventLog, MachineState
│   │   ├── company.py          # Company, Machine, MaintenanceRecord
│   │   └── user.py             # User authentication model
│   ├── services/                # Business logic
│   │   ├── simulator.py        # Data simulation service
│   │   └── predictor.py        # ML prediction service
│   ├── static/                  # Static assets
│   │   ├── css/
│   │   │   └── style.css       # Custom styles
│   │   └── js/
│   │       ├── dashboard.js    # Dashboard logic
│   │       ├── admin.js        # Admin panel logic
│   │       └── machine_management.js # Machine management
│   └── templates/               # Jinja2 templates
│       ├── base.html           # Base template
│       ├── dashboard.html      # Main dashboard
│       ├── login.html          # Login page
│       ├── admin_dashboard.html # Admin panel
│       └── components/         # Reusable components
│           ├── header.html
│           ├── sidebar.html
│           ├── modals.html
│           └── machine_management_modal.html
├── models/                      # Trained ML models
│   ├── FILLING/
│   ├── SHRINK/
│   ├── PILLOW/
│   └── BOXING/
├── migrations/                  # Database migrations (Alembic)
├── scripts/                     # Utility scripts
│   ├── create_basic_models.py
│   ├── populate_machines.py
│   └── test_*.py
├── instance/                    # Instance-specific files
│   └── maintenance.db          # SQLite database
├── run.py                       # Application entry point
├── requirements.txt             # Python dependencies
├── docker-compose.yml           # Docker configuration
└── README.md                    # Project documentation
```

### Core Components

#### 1. Application Factory (`app/__init__.py`)

**Purpose:** Creates and configures the Flask application instance.

**Key Functions:**
- `create_app(config=None)`: Factory function that:
  - Initializes Flask app with configuration
  - Sets up SQLAlchemy, Flask-Migrate, SocketIO
  - Configures Flask-Login for authentication
  - Registers blueprints (API routes)
  - Creates database tables
  - Returns configured app instance

**Configuration:**
- `SECRET_KEY`: Session encryption key
- `SQLALCHEMY_DATABASE_URI`: Database connection string
- `MODEL_BASE_DIR`: Path to ML models directory
- `SIMULATOR_UPDATE_INTERVAL`: Seconds between sensor data generation (default: 1)
- `WINDOW_SIZE`: Number of data points for ML predictions (default: 24)
- `ANOMALY_Z_SCORE_THRESHOLD`: Z-score threshold for anomaly detection (default: 4.0)
- `ENABLE_SIMULATOR`: Enable/disable data simulator (default: True)

#### 2. Data Simulator (`app/services/simulator.py`)

**Purpose:** Generates realistic sensor data for testing and demonstration.

**Class: `DataSimulator`**

**Key Methods:**

1. **`ensure_initialized()`**: Ensures all machines have initial state records
2. **`initialize_states()`**: Creates MachineState records for all configured machines
3. **`is_operational(timestamp)`**: Checks if factory is operational (always returns True - 24/7 operation)
4. **`generate_sensor_data()`**: Main method that:
   - Updates all machine states (state transitions, degradation)
   - Generates sensor readings for all machines
   - Saves readings to database
   - Commits transaction

5. **`generate_sensor_reading(machine_id, sensor_name, mean_value, state)`**: 
   - Generates single sensor value based on:
     - Machine type configuration
     - Current machine state (Normal, Degrading, Off, etc.)
     - Active failure mode (if degrading)
     - Sensor drift over time

6. **`update_machine_state(state)`**: 
   - Handles state transitions:
     - Normal → Operator Error (probability: 0.0001/hour)
     - Normal → Scheduled Maintenance (probability: 0.000005/hour)
     - Normal → Degrading (probability: 0.00005/hour × health_factor)
     - Updates degradation progress for degrading machines
     - Counts down event duration (maintenance, operator errors)

7. **`start_degradation(state)`**: 
   - Selects random failure mode from FAILURE_MODES config
   - Sets machine status to "Degrading"
   - Initializes active_failure with type and progress=0.0

8. **`request_maintenance(machine_id)`**: 
   - Sets machine status to "Maintenance"
   - Sets event_steps_left to 180 (3 hours)
   - Clears active_failure
   - Logs event to EventLog

**Sensor Data Generation Logic:**

```
For each machine:
  1. Determine machine type (FILLING, SHRINK, etc.)
  2. For each sensor in SENSOR_CONFIG[machine_type]:
     a. Calculate base value: mean ± random(0, std_dev)
     b. Apply state-based modifications:
        - Maintenance/Off: value = 0
        - Operator Error: value = mean ± (std_dev × 5) [high variance]
        - Degrading: Apply failure-specific trends:
          * Increase trend: value *= (1 + progress²)
          * Decrease trend: value *= (1 - progress²)
     c. Apply drift: Small random drift over time (0.00005/3600 per second)
     d. Ensure value ≥ 0
  3. Save to SensorData table
```

**State Transition Probabilities:**
- Operator Error: 0.0001 per hour (average once every 10,000 hours)
- Scheduled Maintenance: 0.000005 per hour (average once every 200,000 hours)
- Degradation Start: 0.00005 per hour ÷ health_factor (healthier machines less likely to degrade)

#### 3. Predictive Service (`app/services/predictor.py`)

**Purpose:** Machine learning-based failure prediction with heuristic fallback.

**Class: `PredictiveService`**

**Model Loading:**
- Loads TensorFlow Keras models on first instantiation
- Caches models globally in `_MODEL_CACHE` to avoid reloading
- Supports multiple machine types (FILLING, SHRINK, PILLOW, BOXING)
- Each machine type requires:
  - `{machine_type}_recurrent_model.keras`: GRU neural network
  - `{machine_type}_scaler.joblib`: Feature scaler
  - `{machine_type}_rul_scaler.joblib`: RUL output scaler

**Prediction Methods:**

1. **`get_predictions()`**: 
   - Returns predictions for all configured machines
   - Retrieves latest sensor data (window_size × num_sensors)
   - Converts to DataFrame and pivots by sensor
   - Runs ML prediction or heuristic fallback
   - Returns dictionary of predictions

2. **`generate_prediction_for_machine(machine_id, sensor_data)`**: 
   - Generates prediction for single machine
   - Calculates health score
   - Detects anomalies
   - Predicts RUL (Remaining Useful Life)
   - Returns formatted prediction dictionary

3. **`_heuristic_prediction(machine_id, df_window)`**: 
   - Fallback when ML models unavailable
   - Uses statistical analysis:
     - Anomaly detection via Z-score
     - Trend analysis for failure type prediction
     - TTF (Time To Failure) estimation based on machine type

4. **`predict_failure_type(machine_type, df_window)`**: 
   - Analyzes sensor trends (slope analysis)
   - Matches trends to known failure modes from FAILURE_MODES config
   - Returns predicted failure name

5. **`check_anomalies(df_window)`**: 
   - Z-score analysis on each sensor
   - Threshold: ANOMALY_Z_SCORE_THRESHOLD (default: 4.0)
   - Returns (is_anomalous, details)

6. **`preprocess_input(df, machine_type)`**: 
   - Scales sensor data using fitted scaler
   - Handles missing values (forward fill, backward fill, zero fill)
   - Reshapes for neural network input (batch, timesteps, features)

**ML Model Architecture:**

- **Input**: Window of 24 sensor readings (each sensor is a feature)
- **Model Type**: GRU (Gated Recurrent Unit) - recurrent neural network
- **Outputs**:
  - Classification: Probability of degradation (0.0 to 1.0)
  - Regression: Normalized RUL value (inverse transformed using rul_scaler)

**Prediction Flow:**

```
1. Retrieve latest 24 sensor readings
2. Preprocess (scale, handle missing values)
3. If ML model available:
   a. Run inference: (prob_degrading, normalized_rul) = model.predict(window)
   b. Inverse transform RUL: rul = rul_scaler.inverse_transform(normalized_rul)
   c. If prob_degrading > 0.5: status = "Degrading"
4. Else (heuristic):
   a. Check anomalies
   b. Analyze trends
   c. Estimate TTF from base ranges
5. Predict failure type from sensor trends
6. Return prediction dictionary
```

#### 4. Machine Configuration (`app/config/machine_config.py`)

**Purpose:** Centralized configuration for machine types, sensors, and failure modes.

**Machine Types:** FILLING (3), SHRINK (2), PILLOW (4), BOXING (1)

**Sensors per Type:**
- FILLING: Fill_Volume_Sensor, Nozzle_Pressure, Vibration
- SHRINK: Tunnel_Temperature, Conveyor_Speed, Humidity
- PILLOW: Sealing_Jaw_Temperature, Sealing_Jaw_Pressure, Alignment_Error
- BOXING: Box_Pressure_Sensor, Conveyor_Speed_Sensor, Box_Count_Sensor

**Failure Modes:** Each machine type has 2-3 defined failure modes with sensor trend patterns.

---

## User Interface & Frontend

### Dashboard Layout (From Image)

**Header Section:**
- Title: "PDM DASHBOARD" in light blue
- Status indicator: Green dot + "Live data from simulation"
- Last updated timestamp
- KPI Summary: "ONLINE 10" (blue) / "ALERTS 10" (red)
- MANAGE button (admin only) and LOGOUT link

**Left Sidebar:**
- Tabs: Watchlist (active), Event Log
- Watchlist shows critical machines:
  - BOXING 001: 168h remaining, "Critical Failure Imminent", "Conveyor Belt Stretch"
  - FILLING 001: 168h remaining, "Critical Failure Imminent", "Pump Wear"
- Each alert card shows: Machine ID, Time Remaining, Status, Predicted Failure, Action Required
- Admin Dashboard button (shield icon) at bottom

**Main Content Area:**
- Grid of machine cards (responsive: 1 col mobile, 2 cols tablet, 3 cols desktop)
- Each machine card shows:
  - Header: Machine ID + "INIT" button
  - Sensor readings (latest values with units)
  - Line chart (Chart.js) showing sensor trends
  - Footer: History button, Request Service button
- Cards have visual indicators:
  - Normal: Green status badge
  - Degrading: Red border/background, blinking
  - Anomaly: Yellow/orange indicators

### Frontend Components (`app/static/js/dashboard.js`)

**Core Functions:**

1. **`fetchDashboardData()`**: 
   - Polls `/api/latest-states` every 2 seconds
   - Updates all dashboard components

2. **`updateDashboard(data)`**:
   - Updates KPIs (online machines, alerts)
   - Updates sidebar watchlist with critical machines
   - Updates event log
   - Creates/updates machine cards

3. **`createMachineCard(machineId)`**:
   - Creates HTML structure for machine card
   - Initializes Chart.js instance
   - Sets up predictive spotlight effect

4. **`performMaintenance(machineId)`**:
   - Shows part selection modal
   - Handles part selection and service request

5. **`getFailureType(machineData)`**:
   - Determines specific failure type based on:
     - Sensor threshold violations (immediate detection)
     - ML predictions (for degrading machines)
   - Returns specific names like "Nozzle Clog", "Pump Wear", etc.

**Chart.js Integration:**
- Line charts for each machine showing sensor trends
- Threshold lines (warn/crit) overlaid on charts
- Clickable charts for detailed history view

**Styling (`app/static/css/style.css`):**
- Dark theme: Deep navy (#0b1120) background
- Cyber-industrial design system
- Accent colors: Electric blue (#06b6d4), Success green, Warning amber, Critical red
- Glassmorphism effects for panels
- Responsive breakpoints for mobile/tablet/desktop

---

## API Endpoints

### Authentication (`/auth/*`)

- **`GET/POST /auth/login`**: Login page and authentication
- **`GET /auth/logout`**: Logout user
- **`GET/POST /auth/setup-admin`**: Create initial admin (development only)

### Dashboard API (`/api/*`)

- **`GET /api/latest-states`**: Get current machine states and predictions
  - Returns: predictions dict, KPIs, event_log, is_operational flag
  
- **`GET /api/history?machine_id={id}&range={1h|6h|24h}`**: Get historical sensor data
  - Returns: timestamps array, sensors dict with time-series data

- **`POST /api/request-maintenance`**: Request maintenance for machine
  - Body: `{machine_id, parts[], estimated_duration}`
  - Updates MachineState to "Maintenance"

- **`GET /api/health`**: Health check endpoint
  - Returns: status, timestamp, models_loaded flag

### Data Ingestion (`/api/ingest`)

- **`POST /api/ingest`**: External sensor data ingestion
  - Headers: `X-API-Key: {API_KEY}`
  - Body: `{machine_id, timestamp?, sensors: {name: value}}`
  - Validates machine type and sensor names
  - Creates SensorData records

### Machine Management (`/api/machine-mgmt/*`)

- **`GET /api/machine-mgmt/companies`**: List all companies
- **`POST /api/machine-mgmt/companies`**: Create company
- **`GET /api/machine-mgmt/companies/{id}/machines`**: Get company machines
- **`POST /api/machine-mgmt/machines`**: Create machine (admin)
- **`PUT /api/machine-mgmt/machines/{id}`**: Update machine
- **`DELETE /api/machine-mgmt/machines/{id}`**: Delete machine (admin)
- **`GET /api/machine-mgmt/machine-types`**: Get available machine types/configs

### Admin API (`/api/admin/*`)

- **`GET /api/admin/users`**: List users
- **`POST /api/admin/users`**: Create user (admin)
- **`DELETE /api/admin/users/{id}`**: Delete user (admin)
- **`GET /api/admin/system-stats`**: System statistics (CPU, memory, DB status)

---

## Visual Design System

### Color Palette

- **Background**: Deep Navy (#0b1120)
- **Cards**: Dark Blue-Gray (#151e32)
- **Accent Primary**: Electric Blue/Cyan (#06b6d4)
- **Success**: Emerald Green (#10b981)
- **Warning**: Amber (#f59e0b)
- **Critical**: Rose Red (#f43f5e)
- **Text Primary**: Light Gray (#f1f5f9)
- **Text Secondary**: Medium Gray (#94a3b8)

### Typography

- **Headers**: Space Grotesk (sans-serif, bold)
- **Body**: Inter (sans-serif)
- **Code/Mono**: JetBrains Mono (monospace)

### UI Elements

- **Status Badges**: Rounded pills with colored backgrounds
- **Cards**: Dark background, subtle borders, hover effects
- **Charts**: Chart.js with custom dark theme
- **Modals**: Glassmorphism with backdrop blur
- **Buttons**: Gradient backgrounds, hover states
- **Icons**: Font Awesome 6.4.0

### Responsive Design

- Mobile: Single column, dropdown sidebar
- Tablet: 2-column machine grid
- Desktop: 3-column machine grid, fixed sidebar

---

## Configuration & Setup

### Environment Variables

```bash
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///maintenance.db  # or postgresql://...
MODEL_BASE_DIR=./models
SIMULATOR_UPDATE_INTERVAL=1  # seconds
WINDOW_SIZE=24  # sensor readings for ML
ANOMALY_Z_SCORE_THRESHOLD=4.0
ENABLE_SIMULATOR=True
API_KEY=dev-api-key  # for /api/ingest
PORT=5000
```

### Initial Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Initialize database: `python -c "from app import create_app; app = create_app()"`
3. Create admin user: Visit `/auth/setup-admin` (or manually via database)
4. (Optional) Train ML models: `python scripts/create_basic_models.py`
5. Start application: `python run.py`

### Default Credentials

- Username: `admin`
- Password: `admin123`
- Change immediately in production!

---

## Summary

This PDM system provides comprehensive predictive maintenance capabilities through:
- Real-time sensor monitoring
- ML-based failure prediction
- Specific failure mode identification
- Interactive dashboard visualization
- Service request workflow
- Multi-tenant architecture
- Role-based access control

The system is designed for continuous 24/7 operation with a flexible configuration system that supports multiple machine types and sensors.

---

