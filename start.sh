#!/bin/bash

# Start Train Traffic Control MVP

echo "🚂 Starting Train Traffic Control MVP..."
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

flask --app src.web.app run --port 5000
