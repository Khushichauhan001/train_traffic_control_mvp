# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is an AI-powered Train Traffic Control MVP that demonstrates intelligent decision-making for train precedence, crossings, and schedule optimization on a single railway section. It's built for the Ministry of Railways' challenge to maximize section throughput using AI-powered precise train traffic control.

## Development Commands

### Virtual Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Start the basic Flask application
flask --app src.web.app run --port 5000

# Start the enhanced version with real-time features
flask --app src.web.enhanced_app run --port 5000

# Use the provided start script (runs enhanced version)
bash start.sh
```

### Development Testing
```bash
# Install additional development dependencies if needed
pip install pytest pytest-cov

# Run basic functionality tests (create tests manually if needed)
python -m pytest tests/ -v

# Run specific module tests
python -c "from src.core.optimizer import HeuristicOptimizer; from src.core.models import *; print('Basic imports working')"
```

### Single Module Testing
```bash
# Test the simulator module
python -c "
from src.core.models import Train, Section, Block
from src.sim.simulator import Simulator
section = Section('test', [Block('B1', 10, 100)])
sim = Simulator(section)
print('Simulator module working')
"

# Test optimization engine
python -c "
from src.core.optimizer import HeuristicOptimizer
from src.core.models import Train, Section, Block
section = Section('test', [Block('B1', 10, 100)])
opt = HeuristicOptimizer(section)
print('Optimizer module working')
"
```

## Architecture Overview

### Core Design Pattern
The system follows a **layered architecture** with clear separation of concerns:

- **Models Layer** (`src/core/models.py`): Domain objects (Train, Section, Block, TrainState)
- **Optimization Layer** (`src/core/optimizer.py`): Heuristic scheduling algorithms
- **Safety Layer** (`src/core/safety_validator.py`): Collision detection and safety validation
- **Simulation Layer** (`src/sim/`): Time-stepped simulation engines
- **Web Layer** (`src/web/`): Flask APIs and user interfaces

### Key Architectural Components

#### 1. Domain Models (`src/core/models.py`)
- `Train`: Represents a train with priority, speed, route, and type
- `Section`: A railway section containing multiple blocks
- `Block`: Individual track segments with length, speed limits, and station info
- `TrainState`: Runtime state of a train during simulation
- `ScheduleDecision`: Container for optimized train scheduling results

#### 2. Optimization Engine (`src/core/optimizer.py`)
- **HeuristicOptimizer**: Priority-based scheduling with headway constraints
- Uses greedy algorithm: sorts trains by priority then departure time
- Handles block occupancy conflicts and crossing decisions
- **Key method**: `optimize()` returns complete schedule for all trains

#### 3. Safety System (`src/core/safety_validator.py`)
- **CollisionDetector**: Validates schedules for safety violations
- Detects same-block conflicts, insufficient headway, head-on collisions
- **Real-time verification**: `verify_block_clearance()` for live safety checks
- Returns detailed violation reports with severity levels

#### 4. Simulation Engines (`src/sim/`)

##### Basic Simulator (`simulator.py`)
- Time-stepped discrete simulation
- Tracks KPIs: delays, throughput, utilization
- Supports disruption handling and re-optimization

##### Enhanced Simulator (`enhanced_simulator.py`)  
- Extended with real-time event logging
- **Event system**: Comprehensive logging of departures, arrivals, crossings, warnings
- **Enhanced KPIs**: Safety scores, on-time performance, distance tracking
- **Real-time callbacks**: Supports live dashboard updates

#### 5. Web Applications (`src/web/`)

##### Basic App (`app.py`)
- Simple Flask API with visualization
- Gantt chart generation using Plotly
- Basic KPI reporting and optimization recommendations

##### Enhanced App (`enhanced_app.py`)
- **Real-time dashboard** with live updates
- **Control panel**: Start/stop simulation, emergency stops, manual overrides
- **Threading**: Background simulation with progress tracking
- **Event streaming**: Live event log with severity filtering

### Data Flow Architecture

```
[User Input] → [Flask API] → [Optimizer] → [Safety Validator] → [Simulator] 
     ↑                                                              ↓
[Dashboard] ← [Real-time Updates] ← [Event Logger] ← [Train State Manager]
```

### Critical Design Decisions

#### Time-Based Simulation
- **Discrete time steps**: 0.5-1 minute intervals for accuracy vs performance
- **Schedule-driven**: Pre-calculated optimal schedule guides simulation
- **Dynamic re-optimization**: Schedule recalculated after disruptions

#### Safety-First Architecture  
- **Pre-validation**: All schedules validated before execution
- **Runtime verification**: Double-checking before every train movement
- **Multi-layer safety**: Block occupancy + headway + collision detection

#### Event-Driven Updates
- **Observer pattern**: Real-time callbacks for dashboard updates  
- **Comprehensive logging**: Every significant action generates timestamped events
- **Severity classification**: INFO/WARNING/ERROR/CRITICAL for filtering

### Extension Points

#### Adding New Optimization Algorithms
1. Inherit from base optimizer interface
2. Implement `optimize(trains, current_time)` method
3. Return `ScheduleDecision` object
4. Ensure safety validator compatibility

#### Adding New Safety Checks
1. Extend `SafetyViolation` dataclass for new violation types
2. Add validation logic to `CollisionDetector`
3. Define severity levels and error messages
4. Update event logging in simulators

#### Scaling to Network-Level
- **Current**: Single section with bidirectional blocks
- **Future**: Multi-section coordination requires:
  - Junction management in models
  - Network-wide optimization algorithms
  - Distributed safety validation
  - Cross-section event coordination

### Performance Characteristics
- **Optimization**: <100ms for 8 trains, O(n²) time complexity
- **Safety validation**: <50ms response time  
- **Simulation**: 5 hours simulated in ~10 seconds (real-time ratio: 1800:1)
- **Memory**: Stores complete event history and state transitions

### Testing Strategy
- **Unit tests**: Individual components (models, optimizer, safety)
- **Integration tests**: Full simulation scenarios with known outcomes  
- **Safety tests**: Violation detection with adversarial schedules
- **Performance tests**: Large train sets and long simulation periods

### Known Limitations
- Single section only (no network optimization)
- Heuristic optimization (not globally optimal) 
- No real-time data integration
- Limited to ~10 trains for responsive performance
- Simplified signaling model compared to real railway systems
