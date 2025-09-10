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
from ..core.delhi_data_service import DelhiStationDataService
from ..sim.enhanced_simulator import EnhancedSimulator

app = Flask(__name__, 
            template_folder='../../templates',
            static_folder='../../static')
app.secret_key = 'train_control_mvp_2024'

# Global storage
current_simulation = None
simulation_thread = None
simulation_status = {"running": False, "progress": 0, "stopped": False}
realtime_data = {
    "train_states": {},
    "events": [],
    "kpis": None,
    "block_status": {},
    "route_recommendations": [],
    "real_time_info": None
}
delhi_service = DelhiStationDataService()
stop_simulation_flag = threading.Event()

def load_enhanced_scenario():
    """Load enhanced scenario with real Delhi station data"""
    global delhi_service
    return delhi_service.create_enhanced_scenario()

@app.route('/')
def index():
    return render_template('enhanced_dashboard.html')

@app.route('/api/control/start_simulation', methods=['POST'])
def start_simulation():
    global current_simulation, simulation_thread, simulation_status, realtime_data, stop_simulation_flag
    
    try:
        data = request.json
        
        # Load scenario with Delhi data
        section, trains = load_enhanced_scenario()
        
        # Get real-time Delhi data
        real_time_info = delhi_service.get_real_time_data()
        
        # Add any custom disruptions
        disruptions = data.get('disruptions', [])
        
        # Reset status and flags
        stop_simulation_flag.clear()
        simulation_status = {"running": True, "progress": 0, "stopped": False}
        realtime_data = {
            "train_states": {},
            "events": [],
            "kpis": None,
            "block_status": {b.id: "FREE" for b in section.blocks},
            "route_recommendations": [],
            "real_time_info": real_time_info
        }
        
        # Run simulation in background thread
        def run_sim():
            global current_simulation, realtime_data, simulation_status, stop_simulation_flag
            
            simulator = EnhancedSimulator(section)
            
            def realtime_callback(current_time, train_states, kpis, recent_events):
                # Check for stop signal
                if stop_simulation_flag.is_set():
                    return False  # Signal to stop simulation
                
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
                
                # Update block status and generate route recommendations
                occupied_blocks = []
                for block_id in realtime_data["block_status"]:
                    realtime_data["block_status"][block_id] = "FREE"
                for ts in train_states.values():
                    if ts.location:
                        realtime_data["block_status"][ts.location] = f"OCCUPIED-{ts.train.id}"
                        occupied_blocks.append(ts.location)
                
                # Generate route recommendations if there are occupied blocks
                if occupied_blocks:
                    available_blocks = [block_id for block_id in realtime_data["block_status"].keys()]
                    recommendations = delhi_service.get_route_recommendations(
                        occupied_blocks, "ANVT", available_blocks)  # Pass available blocks
                    realtime_data["route_recommendations"] = recommendations
                
                simulation_status["progress"] = min(100, int((current_time / 300) * 100))
                return True  # Continue simulation
            
            try:
                train_states, kpis, events = simulator.simulate(
                    trains, 
                    max_time=300,  # 5 hours for demo
                    disruptions=disruptions,
                    realtime_callback=realtime_callback
                )
            except Exception as e:
                print(f"Simulation error: {e}")
                train_states, kpis, events = {}, None, []
            
            # Store final results
            current_simulation = {
                'section': section,
                'trains': trains,
                'train_states': train_states if isinstance(train_states, list) else list(train_states.values()) if train_states else [],
                'kpis': kpis,
                'events': events
            }
            
            simulation_status["running"] = False
            simulation_status["progress"] = 100
            print(f"Simulation completed with {len(current_simulation['train_states'])} train states")
        
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
    global simulation_status, stop_simulation_flag, simulation_thread
    
    try:
        # Signal the simulation to stop
        stop_simulation_flag.set()
        simulation_status["running"] = False
        simulation_status["stopped"] = True
        
        # Wait for thread to finish (with timeout)
        if simulation_thread and simulation_thread.is_alive():
            simulation_thread.join(timeout=2.0)
        
        return jsonify({
            'success': True,
            'message': 'Simulation stopped successfully',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e),
            'message': 'Failed to stop simulation'
        })

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
    """Get realtime simulation status with Delhi data"""
    global realtime_data, simulation_status
    
    return jsonify({
        'running': simulation_status["running"],
        'stopped': simulation_status.get("stopped", False),
        'progress': simulation_status["progress"],
        'train_states': realtime_data["train_states"],
        'block_status': realtime_data["block_status"],
        'recent_events': realtime_data["events"][-20:] if realtime_data["events"] else [],
        'route_recommendations': realtime_data.get("route_recommendations", [])[:3],
        'delhi_alerts': (realtime_data.get("real_time_info") or {}).get("system_alerts", [])[:5],
        'weather_conditions': (realtime_data.get("real_time_info") or {}).get("weather_conditions", {}),
        'kpis': {
            'active_trains': realtime_data["kpis"].active_trains if realtime_data["kpis"] else 0,
            'completed_trains': realtime_data["kpis"].completed_trains if realtime_data["kpis"] else 0,
            'avg_delay': round(realtime_data["kpis"].avg_delay_min, 2) if realtime_data["kpis"] else 0,
            'safety_score': round(realtime_data["kpis"].safety_score, 1) if realtime_data["kpis"] else 100,
            'throughput': round(realtime_data["kpis"].throughput, 2) if realtime_data["kpis"] else 0,
            'on_time_performance': round(realtime_data["kpis"].on_time_performance, 1) if realtime_data["kpis"] else 0
        } if realtime_data["kpis"] else None,
        'timestamp': datetime.now().strftime('%H:%M:%S')
    })

@app.route('/api/control/refresh_metrics', methods=['POST'])
def refresh_metrics():
    """Refresh all metrics and data with visual feedback"""
    global realtime_data, delhi_service
    
    try:
        # Simulate processing time for visual feedback
        time.sleep(0.5)
        
        # Refresh real-time Delhi data
        real_time_info = delhi_service.get_real_time_data()
        realtime_data["real_time_info"] = real_time_info
        
        # Update route recommendations if there are occupied blocks
        occupied_blocks = [block_id for block_id, status in realtime_data["block_status"].items() 
                          if status != "FREE"]
        
        if occupied_blocks:
            available_blocks = [block_id for block_id in realtime_data["block_status"].keys()]
            recommendations = delhi_service.get_route_recommendations(occupied_blocks, "ANVT", available_blocks)
            realtime_data["route_recommendations"] = recommendations
        
        return jsonify({
            'success': True,
            'message': 'Refresh metrics completed successfully',
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'updated_data': {
                'station_count': len(real_time_info['station_status']),
                'live_trains': len(real_time_info['live_trains']),
                'system_alerts': len(real_time_info['system_alerts']),
                'recommendations_count': len(realtime_data.get('route_recommendations', []))
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to refresh metrics'
        })

@app.route('/api/delhi/real_time_data', methods=['GET'])
def get_delhi_real_time_data():
    """Get current Delhi station real-time data"""
    global delhi_service, realtime_data
    
    # Get fresh data or return cached data
    if realtime_data.get('real_time_info') is None:
        real_time_info = delhi_service.get_real_time_data()
        realtime_data['real_time_info'] = real_time_info
    
    return jsonify({
        'success': True,
        'data': realtime_data['real_time_info'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/route/recommendations', methods=['GET'])
def get_route_recommendations():
    """Get intelligent route recommendations"""
    global realtime_data
    
    recommendations = realtime_data.get('route_recommendations', [])
    
    return jsonify({
        'success': True,
        'recommendations': recommendations,
        'count': len(recommendations),
        'timestamp': datetime.now().strftime('%H:%M:%S')
    })

@app.route('/api/visualization/network_graph', methods=['GET'])
def get_network_graph():
    """Get network visualization data"""
    global realtime_data, delhi_service
    
    # Get Delhi stations for network visualization
    section, _ = delhi_service.create_enhanced_scenario()
    
    nodes = []
    for block in section.blocks:
        status = realtime_data["block_status"].get(block.id, "FREE")
        
        nodes.append({
            "id": block.id,
            "label": f"{block.id}\n{block.station or 'Track'}",
            "station": block.station is not None,
            "status": status
        })
    
    return jsonify({"nodes": nodes})

@app.route('/api/performance/train_schedules', methods=['GET'])
def get_train_schedules():
    """Get train schedule information"""
    global realtime_data, current_simulation
    
    if not realtime_data["train_states"]:
        # Generate sample schedules from Delhi service
        section, trains = delhi_service.create_enhanced_scenario()
        schedules = []
        for train in trains:
            schedules.append({
                "train_id": train.id,
                "type": train.train_type,
                "priority": train.priority,
                "status": "SCHEDULED",
                "departure": f"{int(train.dep_time_min//60):02d}:{int(train.dep_time_min%60):02d}",
                "delay": "0 min"
            })
    else:
        schedules = []
        for train_id, state in realtime_data["train_states"].items():
            schedules.append({
                "train_id": train_id,
                "type": state.get("type", "UNKNOWN"),
                "priority": state.get("priority", 0),
                "status": "FINISHED" if state.get("finished") else "RUNNING",
                "departure": "--:--",
                "delay": f"{state.get('delay', 0)} min"
            })
    
    return jsonify({"schedules": schedules})

@app.route('/api/safety/validate', methods=['POST'])
def validate_safety():
    """Validate current schedule for safety violations"""
    global current_simulation
    
    try:
        section, trains = delhi_service.create_enhanced_scenario()
        optimizer = HeuristicOptimizer(section)
        collision_detector = CollisionDetector(section)
        
        # Get current schedule
        schedule = optimizer.optimize(trains)
        
        # Validate for safety
        is_safe, violations = collision_detector.validate_schedule(schedule, trains)
        
        return jsonify({
            "is_safe": is_safe,
            "violations": [{
                "severity": v.severity,
                "message": v.message,
                "train1_id": v.train1_id,
                "train2_id": v.train2_id,
                "block_id": v.block_id,
                "time": v.time
            } for v in violations]
        })
    except Exception as e:
        return jsonify({
            "is_safe": False,
            "error": str(e),
            "violations": []
        })

@app.route('/api/performance/metrics', methods=['GET'])
def get_performance_metrics():
    """Get detailed performance metrics"""
    global current_simulation, realtime_data
    
    if current_simulation and current_simulation.get('kpis'):
        kpis = current_simulation['kpis']
        
        return jsonify({
            "efficiency": {
                "throughput": round(kpis.throughput, 2),
                "section_utilization": round(kpis.section_utilization, 1)
            },
            "punctuality": {
                "avg_delay": round(kpis.avg_delay_min, 1),
                "on_time_performance": round(kpis.on_time_performance, 1)
            },
            "safety": {
                "safety_score": round(kpis.safety_score, 1)
            },
            "operational": {
                "active_trains": kpis.active_trains,
                "completed_trains": kpis.completed_trains
            }
        })
    else:
        return jsonify({
            "efficiency": {"throughput": "-", "section_utilization": "-"},
            "punctuality": {"avg_delay": "-", "on_time_performance": "-"},
            "safety": {"safety_score": "-"},
            "operational": {"active_trains": "-", "completed_trains": "-"}
        })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
