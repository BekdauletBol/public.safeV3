#!/bin/bash

# SafeGrid OS v2.0 Local Setup Script
# This script sets up a virtual environment and starts both backend and frontend.

echo "🚀 Starting SafeGrid OS Local Setup..."

# 1. Backend Setup
echo "📦 Setting up Backend..."
cd backend
python3 -m venv venv
# Ensure pip is installed if venv didn't include it
./venv/bin/python3 -m ensurepip
./venv/bin/python3 -m pip install --upgrade pip
./venv/bin/python3 -m pip install -r requirements.txt
export PYTHONPATH=$PYTHONPATH:.
./venv/bin/python3 main.py &
BACKEND_PID=$!
cd ..

# 2. Dashboard Setup
echo "🖥️ Setting up Dashboard..."
cd dashboard
npm install
npm run dev &
FRONTEND_PID=$!
cd ..

echo "✅ SafeGrid OS is running!"
echo "Dashboard: http://localhost:3000"
echo "Backend: http://localhost:8000"
echo "Edge Node: file://$(pwd)/edge/browser/index.html"
echo ""
echo "Press Ctrl+C to stop both servers."

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
