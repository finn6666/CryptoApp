#!/bin/bash

# Azure VM Cost Control Script
# Run this to set up cost monitoring and optimization

echo "🔧 Setting up Azure VM cost controls..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if Azure CLI is installed
check_azure_cli() {
    if ! command -v az &> /dev/null; then
        echo -e "${RED}❌ Azure CLI not found. Please install it first.${NC}"
        echo "Install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        exit 1
    fi
    echo -e "${GREEN}✅ Azure CLI found${NC}"
}

# Function to login to Azure
azure_login() {
    echo "🔐 Checking Azure login status..."
    if ! az account show &> /dev/null; then
        echo "🔑 Please login to Azure..."
        az login
    fi
    echo -e "${GREEN}✅ Azure login verified${NC}"
}

# Function to set up budget alerts
setup_budget() {
    read -p "Enter your monthly budget limit (USD): " budget_amount
    read -p "Enter your email for alerts: " email
    read -p "Enter your resource group name: " rg_name
    
    echo "📊 Creating budget with $budget_amount USD limit..."
    
    # Create action group for email notifications
    az monitor action-group create \
        --name "crypto-app-cost-alerts" \
        --resource-group "$rg_name" \
        --short-name "costAlert" \
        --email "$email" "CostAlert" \
        --output table
    
    # Create budget
    az consumption budget create \
        --budget-name "crypto-app-monthly-budget" \
        --amount "$budget_amount" \
        --time-grain Monthly \
        --time-period-start-date "$(date +%Y-%m-01)" \
        --time-period-end-date "2026-12-31" \
        --resource-group-filter "$rg_name" \
        --threshold 50 80 100 \
        --threshold-type Percentage \
        --contact-emails "$email" \
        --output table
    
    echo -e "${GREEN}✅ Budget and alerts configured${NC}"
}

# Function to configure auto-shutdown
setup_auto_shutdown() {
    read -p "Enter your VM name: " vm_name
    read -p "Enter your resource group name: " rg_name
    read -p "Enter shutdown time (24h format, e.g., 2300 for 11 PM): " shutdown_time
    read -p "Enter your email for shutdown notifications: " email
    
    echo "⏰ Setting up auto-shutdown for $shutdown_time..."
    
    az vm auto-shutdown \
        --resource-group "$rg_name" \
        --name "$vm_name" \
        --time "$shutdown_time" \
        --email "$email" \
        --output table
    
    echo -e "${GREEN}✅ Auto-shutdown configured for ${shutdown_time}${NC}"
}

# Function to show current costs
show_current_costs() {
    echo "💰 Fetching current month costs..."
    
    start_date=$(date +%Y-%m-01)
    end_date=$(date +%Y-%m-%d)
    
    echo "📅 Cost period: $start_date to $end_date"
    
    az consumption usage list \
        --start-date "$start_date" \
        --end-date "$end_date" \
        --output table
}

# Function to optimize VM settings
optimize_vm() {
    read -p "Enter your VM name: " vm_name
    read -p "Enter your resource group name: " rg_name
    
    echo "🔧 Checking current VM configuration..."
    
    # Show current VM size
    current_size=$(az vm show --resource-group "$rg_name" --name "$vm_name" --query "hardwareProfile.vmSize" --output tsv)
    echo "Current VM Size: $current_size"
    
    echo "💡 Recommended sizes for crypto analyzer:"
    echo "  - Standard_B1s  (~$3.80/month) - 1 vCPU, 1GB RAM"
    echo "  - Standard_B1ms (~$7.60/month) - 1 vCPU, 2GB RAM"
    
    read -p "Would you like to resize to B1s for cost savings? (y/N): " resize_choice
    
    if [[ $resize_choice =~ ^[Yy]$ ]]; then
        echo "⏸️  Deallocating VM for resize..."
        az vm deallocate --resource-group "$rg_name" --name "$vm_name"
        
        echo "📏 Resizing to Standard_B1s..."
        az vm resize --resource-group "$rg_name" --name "$vm_name" --size Standard_B1s
        
        echo "▶️  Starting VM..."
        az vm start --resource-group "$rg_name" --name "$vm_name"
        
        echo -e "${GREEN}✅ VM resized to cost-optimized B1s${NC}"
    fi
}

# Function to create monitoring dashboard
create_monitoring() {
    echo "📊 Setting up cost monitoring..."
    
    cat << 'EOF' > cost_monitor.py
#!/usr/bin/env python3
import subprocess
import json
from datetime import datetime, timedelta

def get_monthly_costs():
    """Get current month Azure costs"""
    start_date = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    try:
        result = subprocess.run([
            'az', 'consumption', 'usage', 'list',
            '--start-date', start_date,
            '--end-date', end_date,
            '--output', 'json'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            usage_data = json.loads(result.stdout)
            total_cost = sum(float(item.get('pretaxCost', 0)) for item in usage_data)
            print(f"💰 Current month cost: ${total_cost:.2f}")
            return total_cost
        else:
            print("❌ Failed to fetch cost data")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    get_monthly_costs()
EOF

    chmod +x cost_monitor.py
    echo -e "${GREEN}✅ Cost monitoring script created (cost_monitor.py)${NC}"
    echo "Run './cost_monitor.py' to check current costs"
}

# Main menu
main_menu() {
    echo "🔧 Azure VM Cost Control Setup"
    echo "=============================="
    echo "1. Set up budget alerts"
    echo "2. Configure auto-shutdown"
    echo "3. Show current costs"
    echo "4. Optimize VM size"
    echo "5. Create cost monitoring tools"
    echo "6. Exit"
    echo
    read -p "Choose an option (1-6): " choice
    
    case $choice in
        1) setup_budget ;;
        2) setup_auto_shutdown ;;
        3) show_current_costs ;;
        4) optimize_vm ;;
        5) create_monitoring ;;
        6) echo "👋 Goodbye!"; exit 0 ;;
        *) echo "❌ Invalid option"; main_menu ;;
    esac
}

# Main execution
echo "🚀 Azure VM Cost Control Assistant"
echo "=================================="

check_azure_cli
azure_login
main_menu

echo
echo -e "${GREEN}✅ Cost control setup complete!${NC}"
echo
echo "📋 Next steps:"
echo "1. Monitor costs weekly via Azure portal"
echo "2. Check budget alerts in your email"
echo "3. Use './cost_monitor.py' for quick cost checks"
echo "4. Review AZURE_COST_OPTIMIZATION.md for detailed tips"
echo
echo "💡 Pro tip: Set calendar reminders to check costs weekly!"