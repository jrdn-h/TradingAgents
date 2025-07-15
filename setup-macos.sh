#!/bin/bash
# =============================================================================
# TradingAgents macOS Setup Script
# =============================================================================
# This script helps set up TradingAgents on macOS systems

set -e  # Exit on any error

echo "🍎 TradingAgents macOS Setup Script"
echo "=================================="

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is designed for macOS only."
    echo "   For other platforms, see DEPENDENCIES.md"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check and install Xcode Command Line Tools
echo "🔧 Checking Xcode Command Line Tools..."
if ! command_exists xcode-select; then
    echo "   Installing Xcode Command Line Tools..."
    xcode-select --install
    echo "   ✅ Please complete the Xcode installation and re-run this script"
    exit 0
else
    echo "   ✅ Xcode Command Line Tools found"
fi

# Check and install Homebrew
echo "🍺 Checking Homebrew..."
if ! command_exists brew; then
    echo "   Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo "   ✅ Homebrew found"
fi

# Install Python
echo "🐍 Checking Python..."
if ! command_exists python3.12; then
    echo "   Installing Python 3.12..."
    brew install python@3.12
else
    echo "   ✅ Python 3.12 found"
fi

# Install Poetry
echo "📦 Checking Poetry..."
if ! command_exists poetry; then
    echo "   Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    
    # Add Poetry to PATH
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
    export PATH="$HOME/.local/bin:$PATH"
else
    echo "   ✅ Poetry found"
fi

# Install TradingAgents dependencies
echo "🤖 Installing TradingAgents..."
if [[ -f "pyproject.toml" ]]; then
    poetry install
    echo "   ✅ Dependencies installed successfully"
else
    echo "   ❌ pyproject.toml not found. Are you in the TradingAgents directory?"
    exit 1
fi

# Set up environment file
echo "⚙️  Setting up environment configuration..."
if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        cp .env.example .env
        echo "   ✅ Created .env file from .env.example"
        echo "   📝 Please edit .env with your API keys:"
        echo "      - OPENAI_API_KEY=your-openai-key"
        echo "      - TWIKIT_USERNAME=your-twitter-username"
        echo "      - TWIKIT_PASSWORD=your-twitter-password"
    else
        echo "   ❌ .env.example not found"
    fi
else
    echo "   ✅ .env file already exists"
fi

# Test installation
echo "🧪 Testing installation..."
if poetry run python -c "from tradingagents.config import settings; print('Configuration loaded successfully')" 2>/dev/null; then
    echo "   ✅ TradingAgents installation test passed"
else
    echo "   ⚠️  Installation test failed - check your configuration"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Run: poetry shell"
echo "3. Run: poetry run python -m tradingagents run-demo --symbol BTCUSD"
echo ""
echo "For more information, see README.md and DEPENDENCIES.md"
