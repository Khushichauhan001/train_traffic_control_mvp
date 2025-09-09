from flask import Flask, render_template, request, jsonify
import json
import plotly.graph_objs as go
import plotly.utils
from ..core.models import Train, Section, Block
from ..core.optimizer import HeuristicOptimizer
from ..sim.simulator import Simulator

app = Flask(__name__, 
            template_folder='../../templates',
            static_folder='../../static')

# Global storage for simulation results
current_simulation = None

def load_default_scenario():
    """Load a default scenario for demo purposes"""
    blocks = [
        Block("B1", 5, 100, "bi", "STN-A", 2),
        Block("B2", 8, 120, "bi"),
        Block("B3", 6, 100, "bi", "STN-B", 2),
        Block("B4", 10, 120, "bi"),
        Block("B5", 7, 100, "bi", "STN-C", 2),
    ]
    
    section = Section("SEC-1", blocks, headway_min=3.0)
    
    trains = [
        Train("EXP-001", 1, 120, 2, ["B1", "B2", "B3", "B4", "B5"], "up", 0),
        Train("EXP-002", 1, 110, 2, ["B1", "B2", "B3", "B4", "B5"], "up", 15),
        Train("PASS-001", 2, 80, 3, ["B1", "B2", "B3"], "up", 30),
        Train("FREIGHT-001", 3, 60, 0, ["B1", "B2", "B3", "B4", "B5"], "up", 45),
        Train("EXP-003", 1, 120, 2, ["B5", "B4", "B3", "B2", "B1"], "down", 60),
        Train("PASS-002", 2, 80, 3, ["B5", "B4", "B3"], "down", 75),
    ]
    
    return section, trains

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/simulate', methods=['POST'])
def simulate():
    global current_simulation
    
    try:
        data = request.json
        
        # Use default scenario if not provided
        if not data or 'scenario' not in data:
            section, trains = load_default_scenario()
            disruptions = []
        else:
            # Parse custom scenario
            scenario = data['scenario']
            blocks = [Block(**b) for b in scenario['blocks']]
            section = Section(scenario['section_id'], blocks)
            trains = [Train(**t) for t in scenario['trains']]
            disruptions = scenario.get('disruptions', [])
        
        # Run simulation
        simulator = Simulator(section)
        train_states, kpis = simulator.simulate(trains, max_time=480, disruptions=disruptions)
        
        # Get optimized schedule
        optimizer = HeuristicOptimizer(section)
        schedule = optimizer.optimize(trains)
        
        # Store results
        current_simulation = {
            'section': section,
            'trains': trains,
            'train_states': train_states,
            'kpis': kpis,
            'schedule': schedule
        }
        
        # Prepare response
        result = {
            'success': True,
            'kpis': {
                'total_trains': kpis.total_trains,
                'completed_trains': kpis.completed_trains,
                'avg_delay_min': round(kpis.avg_delay_min, 2),
                'section_utilization': round(kpis.section_utilization, 2),
                'throughput': round(kpis.throughput, 2)
            },
            'train_states': [
                {
                    'train_id': ts.train.id,
                    'priority': ts.train.priority,
                    'finished': ts.finished,
                    'delay_min': round(ts.delay_min, 2),
                    'location': ts.location
                }
                for ts in train_states
            ]
        }
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/schedule_chart', methods=['GET'])
def schedule_chart():
    global current_simulation
    
    if not current_simulation:
        return jsonify({'error': 'No simulation available'})
    
    # Create Gantt chart for train schedules
    traces = []
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#F7DC6F', '#BB8FCE', '#85C1E2']
    
    for i, train in enumerate(current_simulation['trains']):
        schedule = current_simulation['schedule']
        
        for j, block_id in enumerate(train.route):
            entry_time = schedule.get_entry(train.id, block_id)
            if entry_time is not None:
                block = next(b for b in current_simulation['section'].blocks if b.id == block_id)
                travel_time = (block.length_km / min(train.max_speed_kmph, block.max_speed_kmph)) * 60
                dwell_time = train.dwell_min if block.station else 0
                exit_time = entry_time + travel_time + dwell_time
                
                trace = go.Scatter(
                    x=[entry_time, exit_time],
                    y=[f"{train.id} ({block_id})", f"{train.id} ({block_id})"],
                    mode='lines',
                    line=dict(color=colors[i % len(colors)], width=10),
                    name=train.id if j == 0 else "",
                    showlegend=(j == 0),
                    hovertemplate=f"Train: {train.id}<br>Block: {block_id}<br>Entry: %{{x:.1f}} min<br>Exit: %{{x:.1f}} min"
                )
                traces.append(trace)
    
    layout = go.Layout(
        title='Train Schedule - Space-Time Diagram',
        xaxis=dict(title='Time (minutes)', gridcolor='#e0e0e0'),
        yaxis=dict(title='Train-Block', gridcolor='#e0e0e0'),
        hovermode='closest',
        plot_bgcolor='#f8f9fa'
    )
    
    fig = go.Figure(data=traces, layout=layout)
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return jsonify({'chart': graphJSON})

@app.route('/api/optimization_recommendations', methods=['GET'])
def get_recommendations():
    global current_simulation
    
    if not current_simulation:
        return jsonify({'error': 'No simulation available'})
    
    recommendations = []
    
    # Analyze delays
    delayed_trains = [ts for ts in current_simulation['train_states'] if ts.delay_min > 5]
    if delayed_trains:
        for ts in delayed_trains:
            recommendations.append({
                'type': 'delay',
                'severity': 'high' if ts.delay_min > 15 else 'medium',
                'message': f"Train {ts.train.id} experienced {ts.delay_min:.1f} min delay. Consider adjusting schedule or priority."
            })
    
    # Check utilization
    kpis = current_simulation['kpis']
    if kpis.section_utilization > 80:
        recommendations.append({
            'type': 'capacity',
            'severity': 'high',
            'message': f"Section utilization at {kpis.section_utilization:.1f}%. Consider adding passing loops or reducing traffic."
        })
    elif kpis.section_utilization < 30:
        recommendations.append({
            'type': 'capacity',
            'severity': 'low',
            'message': f"Section underutilized at {kpis.section_utilization:.1f}%. Can accommodate more trains."
        })
    
    # Throughput analysis
    if kpis.throughput < 0.5:
        recommendations.append({
            'type': 'throughput',
            'severity': 'medium',
            'message': f"Low throughput of {kpis.throughput:.2f} trains/hour. Review scheduling strategy."
        })
    
    return jsonify({'recommendations': recommendations})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
