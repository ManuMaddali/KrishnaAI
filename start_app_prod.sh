#!/bin/bash

# ---------------------------------
# Krishna AI Production Launcher
# ---------------------------------

# Set environment to production
export ENVIRONMENT=production

# Colors for better feedback
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}  Krishna AI Application Launcher   ${NC}"
echo -e "${RED}     (PRODUCTION ENVIRONMENT)      ${NC}"
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
  
  echo -e "${GREEN}Cleanup complete.${NC}"
  exit 0
}

# Register cleanup function for exit
trap cleanup SIGINT SIGTERM EXIT

# Check if production .env file exists
if [ ! -f ".env.production" ]; then
    echo -e "${RED}Error: .env.production file not found.${NC}"
    echo -e "${YELLOW}Please create a .env.production file with your production settings.${NC}"
    exit 1
fi

# Check if database URL is configured
if ! grep -q "DATABASE_URL" .env.production; then
    echo -e "${YELLOW}Warning: DATABASE_URL not found in .env.production.${NC}"
    echo -e "${YELLOW}Will use SQLite as fallback. This is not recommended for production.${NC}"
fi

# Check if required dependencies are installed
if ! python -c "import psycopg2" 2>/dev/null; then
    echo -e "${YELLOW}Warning: psycopg2 not installed. PostgreSQL support unavailable.${NC}"
    echo -e "${YELLOW}Install with: pip install psycopg2-binary${NC}"
fi

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

# Kill any existing Python processes that might be running our app
pkill -f "python app.py" >/dev/null 2>&1 || true
pkill -f "python main.py" >/dev/null 2>&1 || true
pkill -f "python -m krishna_backend.main" >/dev/null 2>&1 || true
sleep 1

# Setup Python path for module imports
export PYTHONPATH=$(pwd):$PYTHONPATH

# Start the backend server with production settings
echo -e "${BLUE}Starting Krishna AI backend on port 5000...${NC}"
python -m krishna_backend.main --host 0.0.0.0 --port 5000 &
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
echo -e "${GREEN}Production server is running at: http://0.0.0.0:5000${NC}"
echo -e "${BLUE}====================================${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo -e "${RED}Note: This script doesn't start the frontend in production.${NC}"
echo -e "${RED}For mobile apps, make sure to configure the correct API URL in the app settings.${NC}"

# Wait for user interrupt
wait 