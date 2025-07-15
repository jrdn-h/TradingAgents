# TradingAgents Dependencies & Installation Guide

This document provides comprehensive installation instructions for TradingAgents, including platform-specific requirements and troubleshooting.

## Prerequisites

- **Python 3.11 or higher** (Python 3.12 recommended)
- **Poetry** (recommended) or **pip**
- **Git** for cloning the repository

## Installation Methods

### Method 1: Poetry (Recommended)

Poetry provides better dependency management and virtual environment handling.

#### Install Poetry
```bash
# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -

# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# Or via pip
pip install poetry
```

#### Basic Installation
```bash
# Clone the repository
git clone https://github.com/your-org/TradingAgents.git
cd TradingAgents

# Install core dependencies
poetry install

# Activate the virtual environment
poetry shell
```

#### Install with Optional Features
```bash
# Financial data and analysis
poetry install --extras finance

# Memory/vector storage features  
poetry install --extras memory

# Anthropic LLM support
poetry install --extras anthropic

# Google LLM support
poetry install --extras google

# Everything
poetry install --extras all
```

### Method 2: pip + Virtual Environment

If you prefer using pip directly:

```bash
# Clone the repository
git clone https://github.com/your-org/TradingAgents.git
cd TradingAgents

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Platform-Specific Requirements

### Windows

#### Visual Studio Build Tools (Required for chromadb)
ChromaDB requires C++ build tools for compilation. Install one of:

1. **Visual Studio Build Tools** (Recommended)
   - Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - Install "Desktop development with C++" workload
   - Includes MSVC compiler and Windows SDK

2. **Visual Studio Community** (Alternative)
   - Download from: https://visualstudio.microsoft.com/vs/community/
   - Select "Desktop development with C++" during installation

#### Common Windows Issues
- **Error: `Microsoft Visual C++ 14.0 is required`**
  - Install Visual Studio Build Tools as described above
- **Error: `float.h not found`**
  - Ensure Windows SDK is installed with Build Tools
- **Long path issues**
  - Enable long paths: `git config --system core.longpaths true`

### macOS

#### Prerequisites for macOS

**Xcode Command Line Tools** (Required for all installations)
```bash
# Install Xcode Command Line Tools
xcode-select --install

# Verify installation
xcode-select -p
# Should output: /Applications/Xcode.app/Contents/Developer
# or: /Library/Developer/CommandLineTools
```

#### Homebrew Installation (Recommended)

Install Homebrew for easy package management:
```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Add Homebrew to PATH (for Apple Silicon Macs)
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc

# For Intel Macs, Homebrew installs to /usr/local/bin (usually already in PATH)
```

#### Python Installation Options

**Option 1: Using Homebrew (Recommended)**
```bash
# Install Python 3.12 (latest stable)
brew install python@3.12

# Verify installation
python3.12 --version
# Should output: Python 3.12.x

# Create symlink for convenience (optional)
brew link python@3.12
```

**Option 2: Using pyenv (For multiple Python versions)**
```bash
# Install pyenv
brew install pyenv

# Add to shell configuration
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc

# Install Python 3.12
pyenv install 3.12.0
pyenv global 3.12.0

# Verify
python --version
```

**Option 3: Using python.org installer**
- Download from: https://www.python.org/downloads/macos/
- Install Python 3.12.x
- May require additional PATH configuration

#### Poetry Installation for macOS

```bash
# Method 1: Using the official installer (recommended)
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

# Method 2: Using Homebrew
brew install poetry

# Method 3: Using pip (if you prefer)
pip3 install poetry

# Verify installation
poetry --version
```

#### macOS-Specific Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-org/TradingAgents.git
cd TradingAgents

# 2. Create and activate virtual environment with Poetry
poetry install
poetry shell

# 3. Alternative: Using venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Install ChromaDB (may require additional steps)
# If you encounter issues, try:
pip install --upgrade pip setuptools wheel
pip install chromadb

# 5. Set up environment variables
cp .env.example .env
# Edit .env with your preferred editor:
nano .env
# or
code .env
# or
vim .env
```

#### Common macOS Issues and Solutions

**Issue: `command not found: python`**
```bash
# Solution: Use python3 or create alias
echo 'alias python=python3' >> ~/.zshrc
echo 'alias pip=pip3' >> ~/.zshrc
source ~/.zshrc
```

**Issue: Poetry not found after installation**
```bash
# Add Poetry to PATH
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Issue: ChromaDB compilation errors**
```bash
# Install additional build tools
brew install cmake
brew install sqlite3

# If using Apple Silicon Mac and encountering issues:
export ARCHFLAGS="-arch arm64"
pip install chromadb
```

**Issue: SSL certificate verification failed**
```bash
# Update certificates
brew install ca-certificates
# or
/Applications/Python\ 3.12/Install\ Certificates.command
```

**Issue: Permission denied errors**
```bash
# Don't use sudo with pip/poetry
# Instead, use virtual environments or user installs
pip install --user package_name
```

#### Apple Silicon (M1/M2/M3) Specific Notes

For Apple Silicon Macs, some packages might need special handling:

```bash
# Set architecture flags if needed
export ARCHFLAGS="-arch arm64"

# For packages that don't have ARM64 wheels:
pip install --no-binary=:all: package_name

# Use Rosetta 2 for Intel-only packages (last resort)
arch -x86_64 pip install package_name
```

#### macOS Environment Variables

Add these to your shell configuration (`~/.zshrc` or `~/.bash_profile`):

```bash
# Python and Poetry
export PATH="$HOME/.local/bin:$PATH"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Optional: Set default Python version
export PYTHON_VERSION=3.12

# For development
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
```

#### macOS Testing

Verify your installation works:

```bash
# Test Python
python3 --version

# Test Poetry
poetry --version

# Test virtual environment
poetry shell
python -c "import sys; print(sys.version)"

# Test TradingAgents
poetry run python -c "from tradingagents.config import settings; print('✅ Configuration loaded')"

# Run tests
poetry run pytest tests/ -v
```

### Linux (Ubuntu/Debian)

#### Build Dependencies
```bash
sudo apt update
sudo apt install build-essential python3-dev
```

#### For CentOS/RHEL
```bash
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel
```

## Dependency Matrix

| Feature | Required Package(s) | Poetry Extra | Commands/Functions Affected |
|---------|-------------------|--------------|---------------------------|
| **Yahoo Finance Data** | `yfinance` | `finance` | • `get_stock_data()`<br>• Historical price fetching<br>• Real-time quotes |
| **Technical Indicators** | `stockstats` | `finance` | • `calculate_indicators()`<br>• RSI, MACD, Bollinger Bands<br>• Technical analysis in backtests |
| **Memory Agents** | `chromadb` | `memory` | • `FinancialSituationMemory`<br>• Agent context persistence<br>• Semantic search over past decisions |
| **Anthropic LLMs** | `langchain-anthropic` | `anthropic` | • Claude model support<br>• Set `llm_provider: "anthropic"` in config |
| **Google LLMs** | `langchain-google-genai` | `google` | • Gemini model support<br>• Set `llm_provider: "google"` in config |

## Feature Availability by Installation Type

### Minimal Installation (no extras)
✅ Core trading logic  
✅ OpenAI LLM support  
✅ Twitter sentiment analysis (Twikit)  
✅ Redis/PostgreSQL integration  
✅ FastAPI endpoints  
✅ Prometheus metrics  
❌ Yahoo Finance data  
❌ Technical indicators  
❌ Memory persistence  
❌ Alternative LLMs (Anthropic/Google)  

### With `finance` Extra
✅ All minimal features  
✅ Historical price data from Yahoo Finance  
✅ Technical indicators (RSI, MACD, etc.)  
✅ Full backtesting capabilities  
❌ Memory persistence  
❌ Alternative LLMs  

### With `all` Extra
✅ Every feature available  
✅ All LLM providers  
✅ Full backtesting with technical analysis  
✅ Agent memory and context persistence  

## Docker Considerations

The current Dockerfile installs only base dependencies. To include extras in Docker:

```dockerfile
# Install with specific extras
RUN poetry install --no-interaction --no-ansi --no-root -E finance -E memory

# Or install everything
RUN poetry install --no-interaction --no-ansi --no-root -E all
```

## Troubleshooting

### Common Installation Issues

#### ChromaDB Installation Failures
**Problem**: `error: Microsoft Visual C++ 14.0 is required`
**Solution**: Install Visual Studio Build Tools (Windows) or build-essential (Linux)

**Problem**: `fatal error: 'float.h' file not found`
**Solution**: Ensure Windows SDK is installed with Visual Studio Build Tools

#### Poetry Issues
**Problem**: `poetry: command not found`
**Solution**: Add Poetry to PATH or reinstall:
```bash
# Windows
$env:PATH += ";$env:APPDATA\Python\Scripts"

# macOS/Linux
export PATH="$HOME/.local/bin:$PATH"
```

**Problem**: `Failed to create the collection`
**Solution**: Check if another process is using the database or clear cache:
```bash
rm -rf ./dataflows/data_cache/chroma.sqlite3
```

#### Network Issues
**Problem**: `SSL certificate verification failed`
**Solution**: Update certificates or use trusted hosts:
```bash
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt
```

### Testing Your Installation

After installation, verify everything works:

```bash
# Test basic functionality
poetry run python -c "from tradingagents.config import settings; print('✅ Configuration loaded')"

# Test LLM connection (requires API key)
poetry run python -c "from tradingagents.agents.analysts.sentiment_analyst import SentimentAnalyst; print('✅ Sentiment analyst imported')"

# Run the test suite
poetry run pytest tests/ -v
```

## Error Messages

When a feature requiring an optional dependency is used without the package installed, you'll see clear error messages:

- **yfinance**: `"yfinance is required to fetch stock data but is not installed. Install with: pip install yfinance"`
- **stockstats**: `"stockstats is required for technical indicators but is not installed. Install with: pip install stockstats"`
- **chromadb**: `"chromadb is required for FinancialSituationMemory but is not installed. Install with: pip install chromadb"`
- **langchain-anthropic**: `"langchain_anthropic is required for Anthropic LLMs. Install with: pip install langchain-anthropic"`
- **langchain-google-genai**: `"langchain_google_genai is required for Google LLMs. Install with: pip install langchain-google-genai"`

## Getting Help

If you encounter issues:

1. **Check the logs**: Set `LOG_LEVEL=DEBUG` in your `.env` file
2. **Search existing issues**: https://github.com/your-org/TradingAgents/issues
3. **Create a new issue**: Include your OS, Python version, and full error message
4. **Discord/Community**: Join our community for real-time help 