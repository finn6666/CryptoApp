#!/bin/bash

# 🚀 CryptoApp Development Workflow Script
# This script helps you make changes safely with confidence

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    print_error "Please run this script from the CryptoApp directory"
    exit 1
fi

# Main menu function
show_menu() {
    echo ""
    echo "🚀 CryptoApp Development Workflow"
    echo "================================"
    echo "1. 🧪 Run Tests (check stability)"
    echo "2. 💾 Create Backup Branch"
    echo "3. 🔄 Quick App Test"
    echo "4. 📊 Run Full Analysis"
    echo "5. 🌐 Test Web Interface"
    echo "6. 🔍 Check for Common Issues"
    echo "7. 📋 Git Status & Changes"
    echo "8. 🔙 Rollback Changes (if needed)"
    echo "9. 🎯 Exit"
    echo ""
    read -p "Choose an option (1-9): " choice
}

# Function to run tests
run_tests() {
    print_status "Running basic functionality tests..."
    if python3 test_basic_functionality.py | grep -q "All tests passed"; then
        print_success "All tests passed! Your code is stable."
        return 0
    else
        print_error "Some tests failed. Check the output above."
        return 1
    fi
}

# Function to create backup branch
create_backup() {
    timestamp=$(date +"%Y%m%d_%H%M%S")
    branch_name="backup_${timestamp}"
    git checkout -b "$branch_name" 2>/dev/null
    git checkout - 2>/dev/null
    print_success "Created backup branch: $branch_name"
}

# Function to test the CLI app
test_cli_app() {
    print_status "Testing CLI application..."
    if python3 main.py --help > /dev/null 2>&1; then
        print_success "CLI app loads successfully"
        python3 main.py --help
    else
        print_error "CLI app has issues"
        return 1
    fi
}

# Function to run full analysis
run_analysis() {
    print_status "Running full crypto analysis..."
    python3 main.py --mode analysis --top 3
}

# Function to test web interface
test_web() {
    print_status "Starting web interface test (will run for 10 seconds)..."
    python3 -c "
from web_app import app
import threading
import time
import requests

def run_server():
    app.run(debug=False, port=5001)

# Start server in background
server_thread = threading.Thread(target=run_server)
server_thread.daemon = True
server_thread.start()

# Wait for server to start
time.sleep(2)

try:
    response = requests.get('http://localhost:5001/', timeout=5)
    if response.status_code == 200:
        print('✅ Web interface is working!')
    else:
        print(f'⚠️  Web interface returned status: {response.status_code}')
except Exception as e:
    print(f'❌ Web interface test failed: {e}')
" 2>/dev/null || print_warning "Web interface test encountered issues"
}

# Function to check for common issues
check_issues() {
    print_status "Checking for common issues..."
    
    # Check for missing imports
    echo "📋 Checking imports..."
    if python3 -c "
import sys
sys.path.insert(0, '.')
try:
    import main, crypto_analyzer, crypto_display, web_app
    print('✅ All main modules import successfully')
except ImportError as e:
    print(f'❌ Import error: {e}')
"; then
        print_success "Import check passed"
    fi
    
    # Check for syntax errors
    echo "📋 Checking syntax..."
    if python3 -m py_compile *.py 2>/dev/null; then
        print_success "No syntax errors found"
    else
        print_warning "Syntax errors detected in some files"
    fi
    
    # Check data files
    echo "📋 Checking data files..."
    if [ -f "api.json" ]; then
        print_success "api.json exists"
    else
        print_warning "api.json missing - may need to fetch data first"
    fi
}

# Function to show git status
show_git_status() {
    print_status "Git repository status:"
    git status --porcelain
    echo ""
    print_status "Recent commits:"
    git log --oneline -5
    echo ""
    print_status "Current branch:"
    git branch --show-current
}

# Function to rollback changes
rollback_changes() {
    print_warning "This will discard all uncommitted changes!"
    read -p "Are you sure? (y/N): " confirm
    if [[ $confirm =~ ^[Yy]$ ]]; then
        git checkout -- .
        git clean -fd
        print_success "All changes rolled back"
    else
        print_status "Rollback cancelled"
    fi
}

# Main loop
while true; do
    show_menu
    
    case $choice in
        1)
            run_tests
            ;;
        2)
            create_backup
            ;;
        3)
            test_cli_app
            ;;
        4)
            run_analysis
            ;;
        5)
            test_web
            ;;
        6)
            check_issues
            ;;
        7)
            show_git_status
            ;;
        8)
            rollback_changes
            ;;
        9)
            print_success "Happy coding! 🎉"
            exit 0
            ;;
        *)
            print_error "Invalid option. Please choose 1-9."
            ;;
    esac
    
    # Wait for user to press enter before showing menu again
    echo ""
    read -p "Press Enter to continue..."
done