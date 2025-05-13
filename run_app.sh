#!/bin/bash

# Kill any existing Flask server processes
pkill -f "python krishna_backend/main.py" || true

# Check for active port 5000
if lsof -i :5000 >/dev/null; then
  echo "Warning: Port 5000 is already in use. Trying to kill the process..."
  lsof -ti :5000 | xargs kill -9
  sleep 1
fi

# Start the Flask backend
echo "Starting Flask backend..."
python krishna_backend/main.py --debug &
FLASK_PID=$!

# Give Flask a moment to start up
sleep 2

# Start Flutter app if the directory exists
if [ -d "krishna_ai_app" ]; then
  echo "Starting Flutter app..."
  cd krishna_ai_app
  flutter run -d chrome --web-port=5000
  
  # When Flutter exits, also kill the Flask server
  kill $FLASK_PID
else
  echo "Flutter app directory not found. Only starting backend."
  # Wait for the Flask process to end
  wait $FLASK_PID
fi
