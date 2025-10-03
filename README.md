# Advanced Predictive Maintenance Platform

A modern, intelligent web application for predictive maintenance in manufacturing environments. This system uses machine learning to predict equipment failures and provides real-time monitoring through an interactive dashboard with specific failure detection and immediate service request capabilities.

## 🚀 Key Features

- **🎯 Specific Failure Detection**: Shows exact issues like "Nozzle Clog", "Pump Wear", "Heater Element Degradation" instead of generic messages
- **⚡ Immediate Service Requests**: Click "Request Service" → Select specific parts → Get instant confirmation with time estimates
- **📊 Interactive Dashboard**: Real-time machine health monitoring with clickable sensor graphs
- **🤖 Intelligent ML System**: Supports different machine types with varying sensor configurations
- **📈 Predictive Analytics**: Failure prediction and remaining useful life estimation
- **🔄 Real-time Updates**: Live data streaming with WebSocket support
- **📱 Responsive Design**: Mobile-friendly sidebar with dropdown navigation
- **🚨 Anomaly Detection**: Statistical analysis with configurable thresholds
- **🔧 Maintenance Scheduling**: Professional service request workflow

## 🛠 Technology Stack

- **Backend**: Flask 3.0 with SQLAlchemy
- **Machine Learning**: TensorFlow 2.15 with dual-output GRU models
- **Frontend**: Modern JavaScript with Chart.js and Tailwind CSS
- **Real-time**: Flask-SocketIO for live updates
- **Database**: SQLite (PostgreSQL ready)
- **Architecture**: Centralized package management with clean structure

## ⚡ Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python -c "from app import create_app; app = create_app(); print('✅ Database initialized')"
```

### 3. Train Models (Optional - system works with intelligent fallback)
```bash
python scripts/create_basic_models.py
```

### 4. Run Application
```bash
python run.py
```

### 5. Access Dashboard
Open `http://localhost:5000` in your browser

## 🏗 Project Structure

```
PDM/
├── app/
│   ├── packages.py          # Centralized package definitions
│   ├── __init__.py         # Application factory
│   ├── api/                # API endpoints
│   │   ├── routes.py       # Main API routes
│   │   └── machine_management.py
│   ├── config/             # Configuration files
│   │   └── machine_config.py
│   ├── models/             # Database models
│   │   ├── company.py
│   │   └── sensor_data.py
│   ├── services/           # Business logic
│   │   ├── predictor.py    # ML prediction service
│   │   └── simulator.py    # Data simulation
│   └── templates/
│       └── dashboard.html  # Interactive dashboard
├── scripts/                # Utility scripts
├── models/                 # Trained ML models
├── .gitignore             # Git ignore rules
├── requirements.txt       # Python dependencies
└── run.py                # Application entry point
```

## 🎯 Specific Failure Detection

The system provides **exact failure information** instead of generic messages:

### Sensor-Based Failures (Immediate Detection)
- **FILLING**: "Nozzle Clog", "Pump Pressure Fault", "Bearing Wear"
- **SHRINK**: "Heater Failure", "Conveyor Jam", "Humidity Sensor Fault"
- **PILLOW**: "Seal Heater Failure", "Pressure Drop", "Alignment Error"
- **BOXING**: "Pneumatic Leak", "Box Jam", "Feed Mechanism Fault"

### ML-Based Predictions (For Degrading Machines)
- **FILLING**: "Nozzle Clog", "Pump Wear", "Seal Deterioration"
- **SHRINK**: "Heater Element Degradation", "Temperature Sensor Drift", "Insulation Failure"
- **PILLOW**: "Seal Heater Wear", "Pressure Regulator Drift", "Jaw Misalignment"
- **BOXING**: "Pneumatic Seal Wear", "Conveyor Belt Stretch", "Sensor Calibration Drift"

## ⚡ Immediate Service Request System

### Professional Workflow:
1. **Click "Request Service"** on any machine
2. **Select specific parts** from machine-specific list
3. **See time estimates** for each part (15-70 minutes)
4. **Get instant confirmation** with notification
5. **Track service progress** with real-time updates

### Serviceable Parts by Machine Type:

#### FILLING Machines
- Nozzle Assembly (30 min) - Clean/replace nozzles
- Pump System (45 min) - Service pump and seals
- Fill Volume Sensor (15 min) - Calibrate/clean sensor
- Vibration Sensor (10 min) - Check mounting and calibration
- General Maintenance (60 min) - Full system inspection

#### SHRINK Machines
- Heating Elements (40 min) - Replace/repair heating elements
- Conveyor Belt (35 min) - Adjust/replace belt
- Temperature Sensor (20 min) - Calibrate temperature sensor
- Humidity Control (25 min) - Service humidity system
- General Maintenance (70 min) - Full system inspection

#### PILLOW Machines
- Sealing Jaws (50 min) - Replace/align sealing jaws
- Pressure System (30 min) - Service pneumatic system
- Alignment Mechanism (40 min) - Calibrate alignment system
- Temperature Control (25 min) - Service heating system
- General Maintenance (65 min) - Full system inspection

#### BOXING Machines
- Pneumatic System (35 min) - Service air compressor and lines
- Conveyor Belt (30 min) - Adjust/replace conveyor
- Box Feed Mechanism (45 min) - Service box handling system
- Pressure Sensors (15 min) - Calibrate pressure sensors
- General Maintenance (60 min) - Full system inspection

## 📊 Interactive Dashboard Features

### Real-time Monitoring
- **Machine Cards**: Live sensor readings with color-coded status
- **Clickable Charts**: Interactive sensor graphs with threshold indicators
- **Status Badges**: Visual indicators for Normal/Degrading/Maintenance states
- **RUL Display**: Remaining Useful Life predictions in hours

### Responsive Sidebar
- **Desktop**: Traditional tabs (Watchlist, Event Log)
- **Mobile**: Dropdown menu with icons for better usability
- **Watchlist**: Critical failures with specific part information
- **Event Log**: Real-time system events and maintenance history

### Professional Notifications
- **Success Notifications**: Green notifications for completed actions
- **Error Notifications**: Red notifications for failed operations
- **Service Confirmations**: Detailed service request confirmations

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard |
| `/dashboard` | GET | Interactive dashboard |
| `/api/latest-states` | GET | Current machine states and predictions |
| `/api/history` | GET | Historical sensor data with charts |
| `/api/request-maintenance` | POST | Professional service request |
| `/api/machine-mgmt/*` | GET/POST | Machine management operations |

## ⚙️ Configuration

### Environment Variables (Optional - sensible defaults provided)
```bash
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///maintenance.db
MODEL_BASE_DIR=./models
SIMULATOR_UPDATE_INTERVAL=1
WINDOW_SIZE=24
ANOMALY_Z_SCORE_THRESHOLD=4.0
```

### Machine Configuration
Add new machine types in `app/config/machine_config.py`:
```python
MACHINES = {
    'YOUR_MACHINE': {
        'sensors': ['Sensor1', 'Sensor2', 'Sensor3'],
        'failures': ['Failure1', 'Failure2', 'Failure3']
    }
}
```

## 🧹 Project Cleanup

### Removing __pycache__ Directories
The project includes comprehensive cleanup tools:

```bash
# Remove all __pycache__ directories
Get-ChildItem -Path . -Recurse -Directory -Name "__pycache__" | ForEach-Object { Remove-Item -Path $_ -Recurse -Force }

# Or use Python
python -c "import os; [os.system(f'rm -rf {root}/{dir}') for root, dirs, files in os.walk('.') for dir in dirs if dir == '__pycache__']"
```

### .gitignore Configuration
The project includes a comprehensive `.gitignore` file that prevents:
- `__pycache__/` directories
- Python compiled files (`*.pyc`, `*.pyo`)
- Environment files (`.env`, `venv/`)
- IDE files (`.vscode/`, `.idea/`)
- OS files (`.DS_Store`, `Thumbs.db`)
- Database files (`*.db`, `*.sqlite`)
- ML model files (`*.h5`, `*.pkl`)

## 🚀 Production Deployment

### Docker Deployment
```bash
docker build -t maintenance-platform .
docker run -d -p 5000:5000 maintenance-platform
```

### Environment Setup
```bash
export FLASK_ENV=production
export DATABASE_URL=postgresql://user:pass@localhost/db
python run.py
```

### Performance Optimization
- **Debug Mode**: Disabled for production (`debug=False`)
- **Connection Pooling**: Configured for high-traffic environments
- **Model Caching**: ML models loaded once and cached
- **Database Indexing**: Optimized queries for sensor data

## 🔄 Continuous Learning

The system supports continuous learning from new data:
- **Automatic Model Updates**: Models retrain on new sensor data
- **Failure Pattern Learning**: System learns from new failure modes
- **Performance Adaptation**: Thresholds adjust based on historical data

## 🛡 Security Features

- **Input Validation**: All API inputs validated and sanitized
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection
- **CORS Configuration**: Properly configured for production
- **Error Handling**: Comprehensive error handling without information leakage

## 📈 Performance Metrics

- **Response Time**: < 100ms for dashboard updates
- **Memory Usage**: Optimized for 24/7 operation
- **Database Performance**: Indexed queries for fast sensor data retrieval
- **ML Inference**: < 50ms per prediction

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add comprehensive docstrings
- Include unit tests for new features
- Update documentation for API changes

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

**Server won't start:**
```bash
# Check if port 5000 is available
netstat -an | findstr :5000

# Kill existing Python processes
taskkill /f /im python.exe
```

**Database errors:**
```bash
# Recreate database
rm maintenance.db
python -c "from app import create_app; app = create_app()"
```

**ML model errors:**
```bash
# Recreate basic models
python scripts/create_basic_models.py
```

**__pycache__ cleanup:**
```bash
# Remove all cache directories
Get-ChildItem -Path . -Recurse -Directory -Name "__pycache__" | Remove-Item -Recurse -Force
```

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the API documentation
3. Check the console for error messages
4. Ensure all dependencies are installed correctly

---

**Built with ❤️ for modern manufacturing environments**