# TradingAgents macOS Setup Guide 🍎

This guide provides macOS-specific instructions for setting up TradingAgents on your Mac.

## Quick Setup (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/TradingAgents.git
cd TradingAgents

# 2. Run the automated setup script
chmod +x setup-macos.sh
./setup-macos.sh

# 3. Edit your API keys
nano .env

# 4. Test the installation
poetry run python -m tradingagents run-demo --symbol BTCUSD
```

## Prerequisites

### System Requirements
- **macOS 10.15** (Catalina) or later
- **Xcode Command Line Tools**
- **8GB RAM** minimum (16GB recommended)
- **5GB free disk space**

### Architecture Support
- ✅ **Intel Macs** (x86_64) - Fully supported
- ✅ **Apple Silicon** (M1/M2/M3) - Fully supported with native performance

## Step-by-Step Installation

### 1. Install Xcode Command Line Tools

```bash
# Install Xcode Command Line Tools
xcode-select --install

# Verify installation
xcode-select -p
# Should output: /Applications/Xcode.app/Contents/Developer
```

### 2. Install Homebrew

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Add to PATH (Apple Silicon)
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc

# Add to PATH (Intel)
echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc
```

### 3. Install Python

```bash
# Install Python 3.12
brew install python@3.12

# Verify installation
python3.12 --version

# Create convenient aliases
echo 'alias python=python3' >> ~/.zshrc
echo 'alias pip=pip3' >> ~/.zshrc
source ~/.zshrc
```

### 4. Install Poetry

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Verify installation
poetry --version
```

### 5. Install TradingAgents

```bash
# Clone the repository
git clone https://github.com/your-org/TradingAgents.git
cd TradingAgents

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

### 6. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your preferred editor
nano .env    # Simple editor
code .env    # VS Code
vim .env     # Vim
```

## Environment Configuration

### Required API Keys

Add these to your `.env` file:

```bash
# OpenAI API Key (required)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Twitter credentials (required for sentiment analysis)
TWIKIT_USERNAME=your-twitter-username
TWIKIT_PASSWORD=your-twitter-password

# Optional: Financial data
FINNHUB_API_KEY=your-finnhub-api-key-here
```

### Shell Configuration

Add these to your `~/.zshrc` (or `~/.bash_profile` for bash):

```bash
# Python and Poetry
export PATH="$HOME/.local/bin:$PATH"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Optional: Development settings
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

# Aliases for convenience
alias python=python3
alias pip=pip3
```

## Testing Your Installation

### Basic Tests

```bash
# Test Python
python --version

# Test Poetry
poetry --version

# Test virtual environment
poetry shell
python -c "import sys; print(f'Python: {sys.version}')"

# Test TradingAgents
python -c "from tradingagents.config import settings; print('✅ Configuration loaded')"
```

### Run Demo

```bash
# Activate environment
poetry shell

# Run basic demo
poetry run python -m tradingagents run-demo --symbol BTCUSD

# Run with live data
poetry run python -m tradingagents run-demo --symbol BTCUSD --live
```

### Run Tests

```bash
# Run all tests
poetry run pytest tests/ -v

# Run specific tests
poetry run pytest tests/test_agents.py -v
```

## Common Issues and Solutions

### Python Command Not Found

```bash
# Problem: python command not found
# Solution: Create alias or use python3
echo 'alias python=python3' >> ~/.zshrc
echo 'alias pip=pip3' >> ~/.zshrc
source ~/.zshrc
```

### Poetry Not Found

```bash
# Problem: poetry command not found
# Solution: Add to PATH
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### ChromaDB Installation Issues

```bash
# Problem: ChromaDB compilation errors
# Solution: Install build tools
brew install cmake sqlite3

# For Apple Silicon:
export ARCHFLAGS="-arch arm64"
pip install chromadb
```

### SSL Certificate Errors

```bash
# Problem: SSL certificate verification failed
# Solution: Update certificates
brew install ca-certificates

# Or run Python's certificate installer
/Applications/Python\ 3.12/Install\ Certificates.command
```

### Permission Errors

```bash
# Problem: Permission denied
# Solution: Never use sudo with pip/poetry
# Use virtual environments instead

# Wrong:
sudo pip install package

# Right:
poetry add package
# or
pip install --user package
```

## Apple Silicon Specific

### Native Performance

Apple Silicon Macs get native performance with most packages. For packages without ARM64 wheels:

```bash
# Set architecture flags
export ARCHFLAGS="-arch arm64"

# Install from source
pip install --no-binary=:all: package_name
```

### Rosetta 2 Fallback

For Intel-only packages (rare):

```bash
# Install Rosetta 2 (if not already installed)
softwareupdate --install-rosetta

# Run with Rosetta 2
arch -x86_64 pip install package_name
```

## Performance Optimization

### Memory Settings

```bash
# Increase memory limits for large datasets
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
```

### Parallel Processing

```bash
# Use all CPU cores
export OMP_NUM_THREADS=$(sysctl -n hw.ncpu)
```

## Development Setup

### VS Code Integration

```bash
# Install VS Code
brew install --cask visual-studio-code

# Install Python extension
code --install-extension ms-python.python

# Open project
code .
```

### Jupyter Notebook

```bash
# Install Jupyter
poetry add jupyter

# Start Jupyter
poetry run jupyter notebook
```

## Uninstalling

To completely remove TradingAgents:

```bash
# Remove virtual environment
poetry env remove python

# Remove project directory
rm -rf TradingAgents

# Optional: Remove Poetry
curl -sSL https://install.python-poetry.org | python3 - --uninstall

# Optional: Remove Python (if installed via Homebrew)
brew uninstall python@3.12
```

## Getting Help

### Log Files

Check these locations for logs:
- `~/Library/Logs/TradingAgents/`
- `./logs/`
- `./results/`

### System Information

```bash
# System info
system_profiler SPSoftwareDataType

# Python info
python -c "import sys; print(sys.version)"
python -c "import platform; print(platform.platform())"

# Poetry info
poetry --version
poetry env info
```

### Support Channels

- **GitHub Issues**: [Report bugs](https://github.com/your-org/TradingAgents/issues)
- **Discussions**: [Ask questions](https://github.com/your-org/TradingAgents/discussions)
- **Documentation**: [Full docs](README.md)

---

**Happy Trading on macOS!** 🍎🚀 