#!/bin/bash

# KrishnaAI Easy Setup and Run Script
# This script handles everything in one go!

echo "===== KrishnaAI Easy Setup and Run ====="
echo "This script will set up and run your KrishnaAI hybrid app with minimal effort."

# Check if we're already set up
if [ -d "krishna_ai_app" ]; then
    echo "KrishnaAI Flutter app already exists."
    
    # Ask if user wants to rebuild or just run
    read -p "Do you want to rebuild the app? (y/n): " rebuild
    if [[ $rebuild == "y" || $rebuild == "Y" ]]; then
        echo "Rebuilding app..."
        rm -rf krishna_ai_app
        ./setup_flutter.sh
        ./download_fonts.sh
    fi
else
    # First-time setup
    echo "First-time setup detected. Setting up KrishnaAI Flutter app..."
    
    # Make sure scripts are executable
    chmod +x setup_flutter.sh
    chmod +x download_fonts.sh
    
    # Run setup scripts
    ./setup_flutter.sh
    ./download_fonts.sh
fi

# Check if app.py is currently running
if pgrep -f "python app.py" > /dev/null; then
    echo "Flask backend is already running. Stopping it first..."
    pkill -f "python app.py"
    sleep 2
fi

# Run the app
echo "Starting KrishnaAI app!"
./run_app.sh 