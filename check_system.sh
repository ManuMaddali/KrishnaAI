#!/bin/bash

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Print header
echo "=========================================="
echo "          KrishnaAI System Check          "
echo "=========================================="
echo

# Check Python installation
echo "Checking Python installation..."
if command_exists python3; then
    python_version=$(python3 --version)
    echo "✅ Python installed: $python_version"
else
    echo "❌ Python 3 not found. Please install Python 3.8 or higher."
fi
echo

# Check pip installation
echo "Checking pip installation..."
if command_exists pip3; then
    pip_version=$(pip3 --version | cut -d " " -f 2)
    echo "✅ pip installed: $pip_version"
else
    echo "❌ pip3 not found. Please install pip for Python 3."
fi
echo

# Check virtual environment
echo "Checking virtual environment..."
if [ -d ".venv" ]; then
    echo "✅ Virtual environment found: .venv/"
else
    echo "⚠️ Virtual environment not found. Recommend creating one with: python -m venv .venv"
fi
echo

# Check for .env file
echo "Checking .env configuration..."
if [ -f ".env" ]; then
    # Check for required keys without revealing contents
    if grep -q "OPENAI_API_KEY" .env; then
        echo "✅ OPENAI_API_KEY found in .env"
    else
        echo "❌ OPENAI_API_KEY not found in .env. Required for API calls."
    fi
else
    echo "❌ .env file not found. Please create one with your OPENAI_API_KEY."
fi
echo

# Check project structure
echo "Checking project structure..."
if [ -d "krishna_backend" ]; then
    echo "✅ Krishna backend package found"
else
    echo "❌ Krishna backend package not found. Directory structure may be incorrect."
fi

if [ -d "krishna_ai_app" ]; then
    echo "✅ Flutter app directory found"
else
    echo "⚠️ Flutter app directory not found. Mobile app will not be available."
fi

if [ -d "scriptures" ] || [ -d "krishna_backend/data/scriptures" ]; then
    echo "✅ Scriptures directory found"
else
    echo "❌ Scriptures directory not found. Please add scripture PDFs."
fi
echo

# Check for running processes
echo "Checking for running processes..."
if pgrep -f "python.*krishna_backend" > /dev/null; then
    echo "✅ Krishna backend is running"
else
    echo "⚠️ Krishna backend is not running. Start with: python main.py"
fi

# Check port 5000
echo "Checking port 5000..."
if command_exists lsof && lsof -i :5000 > /dev/null; then
    echo "✅ Port 5000 is in use (backend server is running)"
else
    echo "⚠️ Port 5000 is not in use. Backend server may not be running."
fi
echo

# Final summary
echo "=========================================="
echo "               Summary                    "
echo "=========================================="
echo "Run the application with: bash run_app.sh"
echo "Or start the backend only with: python main.py"
echo
echo "For more information, see the README.md file."
echo "==========================================" 