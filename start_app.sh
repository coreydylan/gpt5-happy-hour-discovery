#!/bin/bash

echo "🚀 Starting GPT-5 Happy Hour Discovery System"
echo "=============================================="

# Start backend in the background
echo "Starting backend API..."
source venv/bin/activate
python3 happy_hour_backend.py &
BACKEND_PID=$!

echo "Backend started with PID: $BACKEND_PID"
echo "API available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"

# Wait a moment for backend to start
sleep 3

# Start frontend
echo ""
echo "Starting React frontend..."
cd happy-hour-frontend
npm start &
FRONTEND_PID=$!

echo "Frontend started with PID: $FRONTEND_PID"
echo "Frontend available at: http://localhost:3000"

echo ""
echo "🎉 Both servers are running!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Function to cleanup processes
cleanup() {
    echo ""
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "Servers stopped."
    exit 0
}

# Set trap to cleanup on Ctrl+C
trap cleanup SIGINT

# Wait for user to interrupt
wait