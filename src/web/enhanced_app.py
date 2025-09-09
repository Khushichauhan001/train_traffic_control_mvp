from flask import Flask, render_template, request, jsonify, session
import json
import plotly.graph_objs as go
import plotly.utils
from datetime import datetime
from typing import Dict, List
import threading
import time
from ..core.models import Train, Section, Block
from ..core.optimizer import HeuristicOptimizer
from ..core.safety_validator import CollisionDetector
from ..sim.enhanced_simulator import EnhancedSimulator

app = Flask(__name__, 
            template_folder='../../templates',
            static_folder='../../static')
app.secret_key = 'train_control_mvp_2024'

# Global storage
current_simulation = None
simulation_thread = None
simulation_status = {"running": False, "progress": 0}
realtime_data = {
    "train_states": {},
    "events": [],
    "kpis": None,
    "block_status": {}
}

def load_enhanced_scenario():
    """Load enhanced scenario with train types"""
    blocks = [
        Block("B1", 5, 100, "bi", "STN-A", 2),
        Block("B2", 8, 120, "bi"),
        Block("B3", 6, 100, "bi", "STN-B", 2),
        Block("B4", 10, 120, "bi"),
        Block("B5", 7, 100, "bi", "STN-C", 2),
        Block("B6", 9, 110, "bi"),
        Block("B7", 6, 100, "bi", "STN-D", 3),
    ]
    
    section = Section("SEC-MAIN", blocks, headway_min=3.0)
    
    trains = [
        Train("EXP-001", 1, 120, 2, ["B1", "B2", "B3", "B4", "B5", "B6", "B7"], "up", 0, "EXPRESS"),
        Train("EXP-002", 1, 110, 2, ["B1", "B2", "B3", "B4", "B5"], "up", 20, "EXPRESS"),
        Train("PASS-001", 2, 80, 3, ["B1", "B2", "B3", "B4"], "up", 35, "PASSENGER"),
        Train("FREIGHT-001", 3, 60, 0, ["B1", "B2", "B3", "B4", "B5", "B6", "B7"], "up", 50, "FREIGHT"),
        Train("EXP-003", 1, 120, 2, ["B7", "B6", "B5", "B4", "B3", "B2", "B1"], "down", 65, "EXPRESS"),
        Train("PASS-002", 2, 80, 3, ["B7", "B6", "B5", "B4"], "down", 80, "PASSENGER"),
        Train("FREIGHT-002", 3, 50, 0, ["B7", "B6", "B5", "B4", "B3"], "down", 100, "FREIGHT"),
        Train("EXP-004", 1, 115, 2, ["B1", "B2", "B3", "B4", "B5", "B6"], "up", 120, "EXPRESS"),
    ]
    
    return section, trains

@app.route('/')
def index():
    return render_template('enhanced_dashboard.html')

@app.route('/api/control/start_simulation', methods=['POST'])
def start_simulation():
    global current_simulation, simulation_thread, simulation_status, realtime_data
    
    try:
        data = request.json
        
        # Load scenario
        section, trains = load_enhanced_scenario()
        
        # Add any custom disruptions
        disruptions = data.get('disruptions', [])
        
        # Reset status
        simulation_status = {"running": True, "progress": 0}
        realtime_data = {
            "train_states": {},
            "events": [],
            "kpis": None,
            "block_status": {b.id: "FREE" for b in section.blocks}
        }
        
        # Run simulation in background thread
        def run_sim():
            global current_simulation, realtime_data, simulation_status
            
            simulator = EnhancedSimulator(section)
            
            def realtime_callback(current_time, train_states, kpis, recent_events):
                # Update realtime data
                realtime_data["train_states"] = {
                    ts.train.id: {
                        "location": ts.location,
                        "finished": ts.finished,
                        "delay": round(ts.delay_min, 1),
                        "type": ts.train.train_type,
                        "priority": ts.train.priority
                    } for ts in train_states.values()
                }
                
                realtime_data["kpis"] = kpis
                realtime_data["events"] = [e.to_dict() for e in recent_events]
                
                # Update block status
                for block_id in realtime_data["block_status"]:
                    realtime_data["block_status"][block_id] = "FREE"
                for ts in train_states.values():
                    if ts.location:
                        realtime_data["block_status"][ts.location] = f"OCCUPIED-{ts.train.id}"
                
                simulation_status["progress"] = min(100, int((current_time / 300) * 100))
            
            train_states, kpis, events = simulator.simulate(
                trains, 
                max_time=300,  # 5 hours for demo
                disruptions=disruptions,
                realtime_callback=realtime_callback
            )
            
            # Store final results
            current_simulation = {
                'section': section,
                'trains': trains,
                'train_states': train_states,
                'kpis': kpis,
                'events': events
            }
            
            simulation_status["running"] = False
            simulation_status["progress"] = 100
        
        simulation_thread = threading.Thread(target=run_sim)
        simulation_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Simulation started'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/control/stop_simulation', methods=['POST'])
def stop_simulation():
    global simulation_status
    simulation_status["running"] = False
    return jsonify({'success': True})

@app.route('/api/control/emergency_stop', methods=['POST'])
def emergency_stop():
    """Emergency stop for a specific train"""
    train_id = request.json.get('train_id')
    # In production, this would send emergency stop signal
    return jsonify({
        'success': True,
        'message': f'Emergency stop initiated for {train_id}'
    })

@app.route('/api/control/manual_override', methods=['POST'])
def manual_override():
    """Manual override for train routing"""
    data = request.json
    train_id = data.get('train_id')
    action = data.get('action')
    
    # In production, this would allow manual control
    return jsonify({
        'success': True,
        'message': f'Manual override: {action} for {train_id}'
    })

@app.route('/api/realtime/status', methods=['GET'])
def get_realtime_status():
    """Get realtime simulation status"""
    global realtime_data, simulation_status
    
    return jsonify({
        'running': simulation_status["running"],
        'progress': simulation_status["progress"],
        'train_states': realtime_data["train_states"],
        'block_status': realtime_data["block_status"],
        'recent_events': realtime_data["events"][-20:] if realtime_data["events"] else [],
        'kpis': {
            'active_trains': realtime_data["kpis"].active_trains if realtime_data["kpis"] else 0,
            'completed_trains': realtime_data["kpis"].completed_trains if realtime_data["kpis"] else 0,
            'avg_delay': round(realtime_data["kpis"].avg_delay_min, 2) if realtime_data["kpis"] else 0,
            'safety_score': round(realtime_data["kpis"].safety_score, 1) if realtime_data["kpis"] else 100
        } if realtime_data["kpis"] else None
    })

@app.route('/api/performance/metrics', methods=['GET'])
def get_performance_metrics():
    """Get detailed performance metrics"""
    global current_simulation
    
    if not current_simulation:
        return jsonify({'error': 'No simulation data available'})
    
    kpis = current_simulation['kpis']
    
    metrics = {
        'efficiency': {
            'throughput': round(kpis.throughput, 2),
            'section_utilization': round(kpis.section_utilization, 2),
            'avg_speed': round(kpis.avg_speed_kmph, 1),
            'total_distance': round(kpis.total_distance_km, 1)
        },
        'punctuality': {
            'on_time_performance': round(kpis.on_time_performance, 1),
            'avg_delay': round(kpis.avg_delay_min, 2),
            'max_delay': round(kpis.max_delay_min, 2),
            'total_delays': round(kpis.total_delay_min, 1)
        },
        'safety': {
            'safety_score': round(kpis.safety_score, 1),
            'critical_events': sum(1 for e in current_simulation['events'] if e.severity == "CRITICAL"),
            'warnings': sum(1 for e in current_simulation['events'] if e.severity == "WARNING"),
            'collision_free': kpis.safety_score > 80
        },
        'operations': {
            'total_trains': kpis.total_trains,
            'completed_trains': kpis.completed_trains,
            'completion_rate': round((kpis.completed_trains / kpis.total_trains * 100), 1) if kpis.total_trains > 0 else 0
        }
    }
    
    return jsonify(metrics)

@app.route('/api/performance/train_schedules', methods=['GET'])
def get_train_schedules():
    """Get detailed train schedules"""
    global current_simulation
    
    if not current_simulation:
        return jsonify({'error': 'No simulation data available'})
    
    schedules = []
    for ts in current_simulation['train_states']:
        train = ts.train
        schedules.append({
            'train_id': train.id,
            'type': train.train_type,
            'priority': train.priority,
            'status': 'Completed' if ts.finished else 'Active',
            'departure': f"{int(train.dep_time_min//60):02d}:{int(train.dep_time_min%60):02d}",
            'delay': round(ts.delay_min, 1),
            'route': ' → '.join(train.route[:3]) + ('...' if len(train.route) > 3 else '')
        })
    
    return jsonify({'schedules': schedules})

@app.route('/api/events/log', methods=['GET'])
def get_event_log():
    """Get full event log"""
    global current_simulation
    
    if not current_simulation:
        return jsonify({'events': []})
    
    # Get last 100 events
    events = [e.to_dict() for e in current_simulation['events'][-100:]]
    return jsonify({'events': events})

@app.route('/api/safety/validate', methods=['POST'])
def validate_safety():
    """Validate safety for a proposed schedule change"""
    global current_simulation
    
    if not current_simulation:
        return jsonify({'error': 'No simulation running'})
    
    # Get proposed changes
    changes = request.json.get('changes', {})
    
    # Run collision detection
    detector = CollisionDetector(current_simulation['section'])
    optimizer = HeuristicOptimizer(current_simulation['section'])
    
    # Get current schedule
    schedule = optimizer.optimize(current_simulation['trains'])
    
    # Validate
    is_safe, violations = detector.validate_schedule(schedule, current_simulation['trains'])
    
    result = {
        'is_safe': is_safe,
        'violations': [
            {
                'type': v.violation_type,
                'severity': v.severity,
                'message': v.message,
                'trains': [v.train1_id, v.train2_id],
                'block': v.block_id
            } for v in violations
        ]
    }
    
    return jsonify(result)

@app.route('/api/visualization/network_graph', methods=['GET'])
def get_network_graph():
    """Get network visualization data"""
    global current_simulation, realtime_data
    
    if not current_simulation:
        section, _ = load_enhanced_scenario()
    else:
        section = current_simulation['section']
    
    # Create network graph data
    nodes = []
    edges = []
    
    for i, block in enumerate(section.blocks):
        status = realtime_data["block_status"].get(block.id, "FREE") if realtime_data["block_status"] else "FREE"
        nodes.append({
            'id': block.id,
            'label': f"{block.id}\n{block.station if block.station else ''}",
            'x': i * 150,
            'y': 100,
            'status': status,
            'station': block.station is not None
        })
        
        if i < len(section.blocks) - 1:
            edges.append({
                'from': block.id,
                'to': section.blocks[i + 1].id,
                'length': block.length_km
            })
    
    return jsonify({'nodes': nodes, 'edges': edges})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
