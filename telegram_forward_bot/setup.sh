#!/bin/bash

echo "🤖 PLATINUM Telegram Forward Bot - Setup Script"
echo "================================================"
echo ""

# Check Python version
echo "📋 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

# Check if pip is installed
echo "📋 Checking pip..."
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 not found. Please install pip first."
    exit 1
fi
echo "✅ pip3 found"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully!"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Check if .env exists
echo ""
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "✅ .env file created. Please edit it with your bot token."
else
    echo "✅ .env file already exists"
fi

echo ""
echo "================================================"
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your BOT_TOKEN"
echo "2. Add your ADMIN_IDS (your Telegram user ID)"
echo "3. Run: python3 main.py"
echo ""
echo "Get your bot token from @BotFather"
echo "Get your user ID from @userinfobot"
echo "================================================"
