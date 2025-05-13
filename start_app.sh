#!/bin/bash

# ---------------------------------
# Krishna AI Application Launcher
# ---------------------------------

# Set environment to development
export ENVIRONMENT=development

# Colors for better feedback
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}  Krishna AI Application Launcher   ${NC}"
echo -e "${BLUE}     (DEVELOPMENT ENVIRONMENT)      ${NC}"
echo -e "${BLUE}====================================${NC}"

# Safely terminate processes
cleanup() {
  echo -e "\n${YELLOW}Cleaning up processes...${NC}"
  
  # Kill any running backend processes
  if [ ! -z "$BACKEND_PID" ]; then
    echo -e "Terminating backend (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null || true
  fi
  
  # Kill any remaining python process using port 5000
  lsof -ti :5000 | xargs kill -9 2>/dev/null || true
  
  # Kill any remaining flutter process on port 8000
  lsof -ti :8000 | xargs kill -9 2>/dev/null || true
  
  echo -e "${GREEN}Cleanup complete.${NC}"
  exit 0
}

# Register cleanup function for exit
trap cleanup SIGINT SIGTERM EXIT

# Check if ports are in use
echo -e "${BLUE}Checking for existing processes...${NC}"
if lsof -ti :5000 >/dev/null 2>&1; then
  echo -e "${YELLOW}Port 5000 is already in use. Terminating...${NC}"
  lsof -ti :5000 | xargs kill -9
  sleep 2
  if lsof -ti :5000 >/dev/null 2>&1; then
    echo -e "${RED}Failed to terminate process on port 5000.${NC}"
    exit 1
  fi
fi

if lsof -ti :8000 >/dev/null 2>&1; then
  echo -e "${YELLOW}Port 8000 is already in use. Terminating...${NC}"
  lsof -ti :8000 | xargs kill -9
  sleep 2
  if lsof -ti :8000 >/dev/null 2>&1; then
    echo -e "${RED}Failed to terminate process on port 8000.${NC}"
    exit 1
  fi
fi

# Kill any existing Python processes that might be running our app
pkill -f "python app.py" >/dev/null 2>&1 || true
pkill -f "python main.py" >/dev/null 2>&1 || true
pkill -f "python -m krishna_backend.main" >/dev/null 2>&1 || true
sleep 1

# Setup Python path for module imports
export PYTHONPATH=$(pwd):$PYTHONPATH

# Start the backend server with the new module structure
echo -e "${BLUE}Starting Krishna AI backend on port 5000...${NC}"
python -m krishna_backend.main --debug &
BACKEND_PID=$!

# Give backend time to start
echo -e "${YELLOW}Waiting for backend to initialize...${NC}"
echo -e "${YELLOW}This may take up to 30 seconds while loading scripture files...${NC}"
for i in {1..30}; do
  echo -n "."
  if lsof -ti :5000 >/dev/null 2>&1; then
    echo -e "\n${GREEN}Backend detected on port 5000!${NC}"
    break
  fi
  sleep 1
done

# Check if backend started successfully
if ! lsof -ti :5000 >/dev/null 2>&1; then
  echo -e "\n${RED}Error: Backend failed to start on port 5000 after 30 seconds.${NC}"
  echo -e "${YELLOW}Showing recent backend logs:${NC}"
  tail -n 20 app.log 2>/dev/null || echo "No log file found"
  cleanup
  exit 1
fi

echo -e "${GREEN}Backend started successfully (PID: $BACKEND_PID)${NC}"

# Start the Flutter frontend
echo -e "${BLUE}Starting Flutter frontend on port 8000...${NC}"
(cd krishna_ai_app && flutter run -d chrome --web-port=8000) &
FRONTEND_PID=$!

echo -e "${GREEN}Frontend starting...${NC}"
echo -e "${YELLOW}You can access the application at: http://localhost:8000${NC}"
echo -e "${YELLOW}Backend API is running at: http://localhost:5000${NC}"
echo -e "${BLUE}====================================${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"

# Wait for user interrupt
wait 