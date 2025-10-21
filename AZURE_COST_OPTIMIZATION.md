# Azure VM Cost Optimization Guide

## 🚨 Cost Control Strategies

### 1. Choose the Right VM Size
- **B1s** (~$3.80/month): 1 vCPU, 1GB RAM - Perfect for crypto analyzer
- **B1ms** (~$7.60/month): 1 vCPU, 2GB RAM - Better performance
- **B2s** (~$15.20/month): 2 vCPU, 4GB RAM - Overkill for this app

**Recommendation**: Use B1s or B1ms for your crypto analyzer

### 2. Set Up Billing Alerts & Budgets
```bash
# Azure CLI commands to set up cost alerts
az consumption budget create \
  --budget-name "CryptoApp-Monthly" \
  --amount 10 \
  --time-grain Monthly \
  --time-period-start-date 2025-10-01 \
  --time-period-end-date 2026-12-31
```

### 3. Auto-Shutdown Schedule
- **Portal**: VM → Auto-shutdown → Set daily shutdown at 11 PM
- **Cost Savings**: ~70% if you shutdown 16 hours daily
- **Weekend Shutdown**: Additional 30% savings

### 4. Use Spot Instances (Advanced)
- **Savings**: Up to 90% discount
- **Risk**: VM can be evicted with 30-second notice
- **Good for**: Development/testing environments

### 5. Storage Optimization
- **Standard HDD**: $0.045/GB/month (sufficient for crypto app)
- **Standard SSD**: $0.10/GB/month (unnecessary for this use case)
- **Size**: 30GB disk is enough for your app

## 💰 Cost Monitoring Commands

### Check Current Usage
```bash
# Get VM costs
az consumption usage list --start-date 2025-10-01 --end-date 2025-10-21

# Get resource group costs
az consumption usage list -g your-resource-group-name
```

### Set Up Cost Alerts
```bash
# Create action group for email alerts
az monitor action-group create \
  --name "cost-alerts" \
  --resource-group "your-rg" \
  --short-name "costalert" \
  --email "your-email@example.com"

# Create budget with alert
az consumption budget create \
  --budget-name "monthly-budget" \
  --amount 15 \
  --threshold 80 \
  --threshold-type Percentage \
  --contact-emails "your-email@example.com"
```

## 🔧 Application-Level Optimizations

### 1. Reduce API Calls
```python
# Current: Updates every 5 minutes = 288 calls/day
# Optimized: Updates every 15 minutes = 96 calls/day
FETCH_INTERVAL = 15 * 60  # 15 minutes instead of 5
```

### 2. Cache API Data
```python
# Implement local caching to reduce external calls
import time
CACHE_DURATION = 10 * 60  # 10 minutes cache

def fetch_with_cache():
    if time.time() - last_fetch > CACHE_DURATION:
        # Fetch new data
        pass
    else:
        # Use cached data
        pass
```

### 3. Optimize Memory Usage
```python
# Use generators instead of lists for large datasets
def process_coins():
    for coin in coins:
        yield process_coin(coin)
```

## 📊 Expected Monthly Costs

### Minimal Setup (B1s)
- VM: $3.80
- Storage (30GB HDD): $1.35
- Bandwidth: $0.50
- **Total: ~$5.65/month**

### Recommended Setup (B1ms)
- VM: $7.60
- Storage (30GB HDD): $1.35
- Bandwidth: $0.50
- **Total: ~$9.45/month**

### With Auto-Shutdown (12h/day)
- VM Cost: 50% reduction
- **B1s Total: ~$3.25/month**
- **B1ms Total: ~$5.25/month**

## 🚨 Emergency Cost Controls

### 1. Deallocate VM (Stop Billing)
```bash
# Stop VM to stop compute charges (keeps storage)
az vm deallocate --resource-group myResourceGroup --name myVM
```

### 2. Delete VM (Keep Storage)
```bash
# Delete VM but keep disk for later
az vm delete --resource-group myResourceGroup --name myVM --yes
```

### 3. Complete Cleanup
```bash
# Delete everything to stop all charges
az group delete --name myResourceGroup --yes
```

## ⚡ Quick Setup Commands

### 1. Create Cost-Optimized VM
```bash
az vm create \
  --resource-group myResourceGroup \
  --name crypto-analyzer \
  --image Ubuntu2204 \
  --size Standard_B1s \
  --storage-sku Standard_LRS \
  --os-disk-size-gb 30 \
  --admin-username azureuser \
  --generate-ssh-keys
```

### 2. Enable Auto-Shutdown
```bash
az vm auto-shutdown \
  --resource-group myResourceGroup \
  --name crypto-analyzer \
  --time 2300 \
  --email your-email@example.com
```

## 📱 Mobile Monitoring
- **Azure Mobile App**: Real-time cost tracking
- **SMS Alerts**: Set up for budget thresholds
- **Daily Email Reports**: Cost summaries

## 🎯 Best Practices Summary
1. **Use B1s VM size** for development
2. **Set up auto-shutdown** for 16+ hours daily
3. **Monitor costs weekly** via Azure portal
4. **Set budget alerts** at 50%, 80%, 100%
5. **Use Standard HDD storage**
6. **Optimize API call frequency**
7. **Keep resource group organized**
8. **Tag resources** for cost tracking

## 🔍 Cost Monitoring Tools
- Azure Cost Management + Billing
- Azure Advisor recommendations
- Third-party tools: CloudHealth, Cloudyn
- Azure mobile app for on-the-go monitoring