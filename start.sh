#!/bin/bash

# Start Train Traffic Control MVP

echo "🚂 Starting Enhanced Train Traffic Control MVP..."
echo ""
echo "Features:"
echo "  ✓ Control Panel with simulation controls"
echo "  ✓ Real-time Performance Metrics"
echo "  ✓ Live Event Log"
echo "  ✓ Collision Detection & Safety Validation"
echo "  ✓ Network Visualization"
echo "  ✓ Train Schedule Monitoring"
echo ""

# Navigate to project directory
cd ~/train_traffic_control_mvp

# Activate virtual environment
source venv/bin/activate

# Start Flask server
echo "Starting Flask server on http://127.0.0.1:5000"
echo ""
echo "📊 Open your browser and visit: http://127.0.0.1:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

flask --app src.web.enhanced_app run --port 5000
