#!/bin/bash

# Setup script for Happy Hour Discovery System

echo "🍻 Happy Hour Discovery System Setup"
echo "===================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q pandas pydantic aiohttp python-dotenv openai

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "Please edit .env and add your OpenAI API key"
fi

# Check for CSV file
if [ ! -f "food_permits_restaurants.csv" ]; then
    echo "⚠️  Warning: food_permits_restaurants.csv not found"
    echo "Please ensure the CSV file is in this directory"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the system:"
echo "  1. Edit .env file with your OpenAI API key"
echo "  2. Run: source venv/bin/activate"
echo "  3. Run: python3 run_happy_hour_discovery.py --restaurant 'RESTAURANT_NAME'"
echo ""
echo "Example:"
echo "  python3 run_happy_hour_discovery.py --restaurant 'BARBARELLA'"