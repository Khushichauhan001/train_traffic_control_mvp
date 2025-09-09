# 🚂 AI-Powered Train Traffic Control MVP

A proof-of-concept implementation for optimizing train traffic control using heuristic algorithms and real-time simulation. This MVP demonstrates intelligent decision-making for train precedence, crossings, and schedule optimization on a single railway section.

## 🎯 Problem Statement

This project addresses the **Ministry of Railways' challenge** (ID: 25022) to maximize section throughput using AI-powered precise train traffic control. It provides a decision-support system for section controllers to optimize train movements considering multiple constraints like safety, track resources, platform availability, and train priorities.

## ✨ Features

- **Priority-based Optimization**: Automatically determines train precedence based on configurable priorities
- **Real-time Simulation**: Time-stepped simulation engine to test optimization decisions
- **Space-Time Visualization**: Interactive Gantt chart showing train movements across blocks
- **KPI Dashboard**: Tracks average delays, throughput, and section utilization
- **AI Recommendations**: Provides actionable insights for improving traffic flow
- **Disruption Handling**: Supports re-optimization when delays or failures occur

## 🏗️ Architecture

```
train_traffic_control_mvp/
├── src/
│   ├── core/           # Domain models and optimization engine
│   │   ├── models.py    # Train, Section, Block data structures
│   │   └── optimizer.py # Heuristic scheduling algorithm
│   ├── sim/            # Simulation environment
│   │   └── simulator.py # Time-stepped train movement simulation
│   └── web/            # Flask web application
│       └── app.py       # REST API and web interface
├── templates/          # HTML templates
│   └── index.html      # Main UI
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

1. **Clone or navigate to the project directory:**
```bash
cd ~/train_traffic_control_mvp
```

2. **Create a virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

### Running the Application

1. **Start the Flask server:**
```bash
flask --app src.web.app run --port 5000
```

2. **Open your browser and visit:**
```
http://127.0.0.1:5000
```

3. **Click "Run Simulation" to see the system in action!**

## 📊 How It Works

### 1. **Optimization Engine**
- Uses priority-based heuristics to schedule trains
- Respects headway constraints (minimum time between trains)
- Handles bidirectional traffic with crossing decisions

### 2. **Simulation**
- Runs a discrete-time simulation (1-minute steps)
- Tracks train movements through blocks
- Calculates delays and performance metrics

### 3. **Visualization**
- Space-time diagram shows train trajectories
- Color-coded by train priority
- Interactive hover for details

### 4. **KPIs Tracked**
- **Average Delay**: Mean delay across all trains
- **Throughput**: Trains completed per hour
- **Section Utilization**: Percentage of time blocks are occupied
- **Completion Rate**: Ratio of finished to total trains

## 🎮 Demo Scenario

The default scenario includes:
- **5 blocks** (36 km total) with 3 stations
- **6 trains** of different types:
  - 2 Express trains (Priority 1, 120 km/h)
  - 2 Passenger trains (Priority 2, 80 km/h)
  - 1 Freight train (Priority 3, 60 km/h)
  - Mix of up and down directions

## 🔄 Extending the System

### Adding Custom Scenarios

Modify the `load_default_scenario()` function in `src/web/app.py` to add:
- New blocks with different characteristics
- More trains with varying priorities
- Different route patterns
- Disruption events

### Improving the Optimizer

Replace the heuristic algorithm with:
- Mixed Integer Programming (MIP)
- Constraint Programming (CP-SAT)
- Reinforcement Learning (RL)
- Genetic Algorithms

## 🚧 Limitations (MVP)

- Single section only (no network-level optimization)
- Simplified signaling model
- Basic heuristic algorithm (not globally optimal)
- No real-time data integration
- Limited to ~10 trains for good performance

## 🔮 Future Enhancements

1. **Advanced Optimization**
   - Implement CP-SAT solver for optimal solutions
   - Add machine learning for pattern recognition

2. **Network Expansion**
   - Multi-section coordination
   - Junction management
   - Complex interlocking rules

3. **Real-time Integration**
   - Connect to actual Train Management Systems
   - Live GPS tracking
   - Weather and incident feeds

4. **Enhanced UI**
   - 3D visualization
   - Mobile-responsive design
   - Operator override controls

## 📈 Performance Metrics

With the default scenario:
- Processes 6 trains over 8 hours
- Achieves <5 minute average delays
- Maintains ~40% section utilization
- Provides recommendations in <100ms

## 🤝 Contributing

This is an MVP demonstration. For production deployment:
1. Add comprehensive testing
2. Implement security measures
3. Add database persistence
4. Scale optimization algorithms
5. Integrate with railway systems

## 📄 License

This MVP is created for demonstration purposes as part of the Ministry of Railways innovation challenge.

---

**Built with ❤️ for Indian Railways**

*Making train traffic control smarter, one optimization at a time!*
