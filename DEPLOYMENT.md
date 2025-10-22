# 🔵 Azure VM Deployment Guide# 🔵 Azure Deployment Guide# 🚀 Cloud Deployment Guide



Simple deployment guide for running your Crypto Investment Analyzer on an Azure Virtual Machine using Git and bash scripts.



## 📋 **Prerequisites**Your Crypto Investment Analyzer deployment guide for Microsoft Azure.Your Crypto Investment Analyzer is now ready for cloud deployment! Choose from multiple hosting options below.



- Azure VM with Ubuntu/Linux

- SSH access to your VM

- Git repository with your code## 📋 **Prerequisites**## 📋 **Quick Setup**

- Python 3.9+ installed on VM



## 🚀 **One-Time VM Setup**

- Azure account ([Create free account](https://azure.microsoft.com/free/))### 1. Install Web Dependencies

SSH into your Azure VM and run these commands:

- Azure CLI installed locally```bash

```bash

# Update system- Git repository with your codepip install flask gunicorn

sudo apt update && sudo apt upgrade -y

```

# Install Python and essential tools

sudo apt install python3 python3-pip python3-venv git nginx -y### Install Azure CLI



# Create application directory```bash### 2. Test Locally

sudo mkdir -p /var/www/crypto-analyzer

sudo chown $USER:$USER /var/www/crypto-analyzer# macOS```bash

```

brew install azure-clipython web_app.py

## 📥 **Deploy Your Application**

# Visit: http://localhost:8080

```bash

# Navigate to app directory# Windows (PowerShell)```

cd /var/www/crypto-analyzer

Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile .\AzureCLI.msi; Start-Process msiexec.exe -Wait -ArgumentList '/I AzureCLI.msi /quiet'

# Clone your repository

git clone https://github.com/your-username/your-repo.git .## ☁️ **Cloud Hosting Options**



# Create virtual environment# Ubuntu/Debian

python3 -m venv .venv

source .venv/bin/activatecurl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash### 🔥 **Option 1: Heroku (Easiest)**



# Install dependencies```

pip install -r requirements.txt

**Steps:**

# Test the application

python3 web_app.py## 🚀 **Deployment Options**1. Create Heroku account at [heroku.com](https://heroku.com)

```

2. Install Heroku CLI

## 🔧 **Production Setup with Systemd**

### **Option 1: Azure App Service (Recommended)**3. Deploy:

### 1. Install Gunicorn

```bashBest for Python web applications with automatic scaling.```bash

pip install gunicorn

```# Login to Heroku



### 2. Create Service File#### **Quick Deployment**heroku login

```bash

sudo nano /etc/systemd/system/crypto-analyzer.service```bash

```

# 1. Login to Azure# Create app

**Add this content:**

```iniaz loginheroku create your-crypto-analyzer

[Unit]

Description=Crypto Analyzer Flask App

After=network.target

# 2. Create resource group# Deploy

[Service]

User=azureuseraz group create --name crypto-analyzer-rg --location eastusgit add .

Group=www-data

WorkingDirectory=/var/www/crypto-analyzergit commit -m "Deploy crypto analyzer"

Environment="PATH=/var/www/crypto-analyzer/.venv/bin"

ExecStart=/var/www/crypto-analyzer/.venv/bin/gunicorn --bind 0.0.0.0:8080 web_app:app# 3. Create App Service plangit push heroku main

Restart=always

az appservice plan create \

[Install]

WantedBy=multi-user.target  --name crypto-analyzer-plan \# Open your app

```

  --resource-group crypto-analyzer-rg \heroku open

### 3. Enable and Start Service

```bash  --sku B1 \```

sudo systemctl daemon-reload

sudo systemctl enable crypto-analyzer  --is-linux

sudo systemctl start crypto-analyzer

sudo systemctl status crypto-analyzer**Files needed:** ✅ Already created

```

# 4. Create web app- `Procfile` - Heroku process configuration

## 🔄 **Easy Update Script**

az webapp create \- `requirements.txt` - Python dependencies

Create an update script for future deployments:

  --resource-group crypto-analyzer-rg \- `runtime.txt` - Python version

```bash

nano /var/www/crypto-analyzer/update_app.sh  --plan crypto-analyzer-plan \

```

  --name your-crypto-analyzer \---

**Script content:**

```bash  --runtime "PYTHON|3.9"

#!/bin/bash

echo "🔄 Updating Crypto Analyzer..."### 🐳 **Option 2: Docker + Any Cloud**



cd /var/www/crypto-analyzer# 5. Configure startup command



# Pull latest changesaz webapp config set \**Build and run locally:**

git pull origin main

  --resource-group crypto-analyzer-rg \```bash

# Activate virtual environment

source .venv/bin/activate  --name your-crypto-analyzer \# Build image



# Update dependencies if needed  --startup-file "gunicorn --bind=0.0.0.0 --timeout 600 web_app:app"docker build -t crypto-analyzer .

pip install -r requirements.txt



# Restart the service

sudo systemctl restart crypto-analyzer# 6. Enable local Git deployment# Run container



echo "✅ Update complete!"az webapp deployment source config-local-git \docker run -p 8080:8080 crypto-analyzer

```

  --name your-crypto-analyzer \

```bash

# Make executable  --resource-group crypto-analyzer-rg# Or use docker-compose

chmod +x update_app.sh

docker-compose up

# Usage: just run this for updates

./update_app.sh# 7. Deploy your code```

```

git remote add azure <git-url-from-step-6>

## 🔧 **Required Files (Minimal)**

git push azure development:master**Deploy to:**

Your repository only needs:

- ✅ `requirements.txt` - Python dependencies```- **Google Cloud Run**

- ✅ `web_app.py` - Flask app entry point

- ✅ Your Python source files (`crypto_analyzer.py`, etc.)- **AWS ECS**



**Not needed:**#### **Environment Variables (Optional)**- **Azure Container Instances**

- ❌ Docker files

- ❌ Platform-specific configs (Heroku, Vercel, etc.)```bash- **DigitalOcean Apps**



## 🌐 **Access Your App**# Set environment variables if needed



- **URL**: `http://your-vm-ip:8080`az webapp config appsettings set \---

- **Check Status**: `sudo systemctl status crypto-analyzer`

- **View Logs**: `sudo journalctl -u crypto-analyzer -f`  --resource-group crypto-analyzer-rg \



## 🛠️ **Management Commands**  --name your-crypto-analyzer \### ⚡ **Option 3: Vercel (Serverless)**



```bash  --settings FLASK_ENV=production

# Check app status

sudo systemctl status crypto-analyzer```**Steps:**



# Restart app1. Install Vercel CLI: `npm i -g vercel`

sudo systemctl restart crypto-analyzer

---2. Deploy:

# View real-time logs

sudo journalctl -u crypto-analyzer -f```bash



# Update app### **Option 2: Azure Container Instances**vercel --prod

cd /var/www/crypto-analyzer && ./update_app.sh

```Use Docker containers for more control over the environment.```



## 🆘 **Troubleshooting**



### App Won't Start#### **Build and Deploy Container****Files needed:** ✅ Already created

```bash

# Check logs```bash- `vercel.json` - Vercel configuration

sudo journalctl -u crypto-analyzer -f

# 1. Build Docker image locally

# Test manually

cd /var/www/crypto-analyzerdocker build -t crypto-analyzer .---

source .venv/bin/activate

python3 web_app.py

```

# 2. Create Azure Container Registry### 🌐 **Option 4: Google Cloud Platform**

### Permission Issues

```bashaz acr create \

sudo chown -R azureuser:www-data /var/www/crypto-analyzer

```  --resource-group crypto-analyzer-rg \**Deploy to App Engine:**



### Port Issues  --name cryptoanalyzeracr \```bash

```bash

# Check if port is in use  --sku Basic# Install gcloud CLI

sudo netstat -tlnp | grep :8080

gcloud app deploy

# Make sure Azure NSG allows port 8080

# Azure Portal → VM → Networking → Add inbound rule# 3. Login to registry

```

az acr login --name cryptoanalyzeracr# View app

---

gcloud app browse

**✅ That's it! Simple, direct Python deployment with no container overhead.**
# 4. Tag and push image```

docker tag crypto-analyzer cryptoanalyzeracr.azurecr.io/crypto-analyzer:latest

docker push cryptoanalyzeracr.azurecr.io/crypto-analyzer:latest**Files needed:** ✅ Already created

- `app.yaml` - GCP App Engine configuration

# 5. Deploy container

az container create \---

  --resource-group crypto-analyzer-rg \

  --name crypto-analyzer-container \### 🔧 **Option 5: Manual VPS Setup**

  --image cryptoanalyzeracr.azurecr.io/crypto-analyzer:latest \

  --dns-name-label crypto-analyzer-app \**For Ubuntu/Debian servers:**

  --ports 8080```bash

```# 1. Update system

sudo apt update && sudo apt upgrade -y

---

# 2. Install Python 3.9

## 🔧 **Configuration Files**sudo apt install python3.9 python3.9-venv python3-pip nginx -y



### **Required Files**# 3. Clone your repository

- ✅ `requirements.txt` - Python dependencies (auto-installed)git clone <your-repo-url>

- ✅ `web_app.py` - Flask application entry pointcd CryptoApp



### **Optional Files**# 4. Create virtual environment

- ✅ `Dockerfile` - For container deploymentpython3.9 -m venv venv

- ✅ `docker-compose.yml` - For local developmentsource venv/bin/activate



### **Not Needed for Azure**# 5. Install dependencies

- ❌ `Procfile` (Heroku-specific)pip install -r requirements.txt

- ❌ `runtime.txt` (Heroku-specific)  

- ❌ `vercel.json` (Vercel-specific)# 6. Run with Gunicorn

gunicorn --bind 0.0.0.0:8080 --workers 2 web_app:app

---

# 7. Setup Nginx reverse proxy (optional)

## 🌐 **Access Your App**sudo nano /etc/nginx/sites-available/crypto-analyzer

```

After successful deployment:

## 🔐 **Environment Variables**

### **App Service**

- URL: `https://your-crypto-analyzer.azurewebsites.net`For production, consider setting:

- Check logs: `az webapp log tail --name your-crypto-analyzer --resource-group crypto-analyzer-rg````bash

export FLASK_ENV=production

### **Container Instances**  export PYTHONPATH=/app

- URL: `http://crypto-analyzer-app.eastus.azurecontainer.io:8080````

- Check logs: `az container logs --resource-group crypto-analyzer-rg --name crypto-analyzer-container`

## 📊 **Features Available**

---

Your deployed app includes:

## 🛠️ **Local Development**

### **Web Dashboard:**

Test before deploying:- 📱 **Responsive Design** - Works on mobile & desktop

- 🔄 **Auto-refresh** - Updates every 5 minutes

### **Option 1: Direct Python**- 📊 **Live Statistics** - Portfolio overview

```bash- 💎 **Low Cap Focus** - Specialized for small market caps

# Install dependencies

pip install -r requirements.txt### **API Endpoints:**

- `GET /` - Main dashboard

# Run Flask app- `GET /api/coins` - Cryptocurrency data JSON

python web_app.py- `GET /api/stats` - Portfolio statistics

# Visit: http://localhost:8080- `GET /api/refresh` - Manual data refresh

```- `GET /health` - Health check for monitoring



### **Option 2: Docker**### **Real-time Features:**

```bash- ✅ Live CoinGecko API integration

# Build and run container- ✅ Background data updates

docker-compose up- ✅ Error handling and recovery

- ✅ Health monitoring

# Or manually:

docker build -t crypto-analyzer .## 🚀 **Performance Tips**

docker run -p 8080:8080 crypto-analyzer

```### **Optimization:**

1. **Caching** - Data updates every 5 minutes

---2. **Workers** - Multiple Gunicorn workers for scale

3. **Health Checks** - Built-in monitoring

## 🔍 **Monitoring & Management**4. **Error Handling** - Graceful failure recovery



### **View Application Logs**### **Scaling:**

```bash- **Horizontal:** Add more server instances

# App Service logs- **Vertical:** Increase CPU/memory per instance

az webapp log tail --name your-crypto-analyzer --resource-group crypto-analyzer-rg- **Database:** Consider Redis for caching (future)



# Container logs## 🔧 **Customization**

az container logs --resource-group crypto-analyzer-rg --name crypto-analyzer-container

```### **Change Update Frequency:**

Edit `web_app.py` line 20:

### **Scale Your Application**```python

```bashtime.sleep(300)  # 300 seconds = 5 minutes

# Scale App Service```

az appservice plan update --name crypto-analyzer-plan --resource-group crypto-analyzer-rg --number-of-workers 2

### **Modify UI:**

# Scale Container (recreate with more resources)Edit `templates/index.html` for styling changes

az container create --cpu 2 --memory 4 # ... other parameters

```### **Add Features:**

- Portfolio tracking

### **Update Your Application**- Price alerts

```bash- User accounts

# For App Service (Git deployment)- Advanced filtering

git push azure development:master

## 📱 **Mobile Support**

# For Container Instances

docker build -t crypto-analyzer .The web interface is fully responsive and works great on:

docker tag crypto-analyzer cryptoanalyzeracr.azurecr.io/crypto-analyzer:latest- 📱 **Mobile phones**

docker push cryptoanalyzeracr.azurecr.io/crypto-analyzer:latest- 📟 **Tablets** 

# Container will auto-update on restart- 💻 **Desktop browsers**

```- 🖥️ **Large screens**



---## 🔍 **Monitoring**



## 💰 **Cost Optimization**### **Health Check:**

```bash

- **Free Tier**: Use B1 Basic plan for development ($13.14/month)curl https://your-app.com/health

- **Production**: Scale to S1 Standard for better performance ($56.94/month)```

- **Containers**: Pay only for running time

- **Stop when not needed**: `az webapp stop` to save costs### **API Test:**

```bash

---curl https://your-app.com/api/coins

```

## 🆘 **Troubleshooting**

## 🆘 **Troubleshooting**

### **Common Issues**

### **Common Issues:**

1. **Deployment fails**

   ```bash1. **Port conflicts:** Change port in `web_app.py`

   # Check deployment logs2. **API limits:** CoinGecko has rate limits

   az webapp log tail --name your-crypto-analyzer --resource-group crypto-analyzer-rg3. **Memory usage:** Reduce update frequency

   ```4. **Dependencies:** Check `requirements.txt`



2. **App won't start**### **Logs:**

   ```bash```bash

   # Verify startup command# Heroku

   az webapp config show --name your-crypto-analyzer --resource-group crypto-analyzer-rgheroku logs --tail

   ```

# Docker

3. **Port issues**docker logs container_name

   - Azure App Service uses port 8000 by default

   - Ensure your Flask app binds to `0.0.0.0:8080` or use environment variable `PORT`# Systemd service

sudo journalctl -u your-service -f

### **Support Resources**```

- [Azure App Service Documentation](https://docs.microsoft.com/en-us/azure/app-service/)

- [Azure Container Instances Documentation](https://docs.microsoft.com/en-us/azure/container-instances/)---

- [Azure CLI Reference](https://docs.microsoft.com/en-us/cli/azure/)

## 🎉 **Success!**

---

Your crypto analyzer is now running in the cloud with:

*🎉 Your Crypto Investment Analyzer is now running on Azure!*- 🌐 **Public web interface**
- 📊 **Real-time data updates**
- 💎 **Low cap cryptocurrency focus**
- 📱 **Mobile-friendly design**
- ⚡ **High performance**

**Example URLs:**
- Dashboard: `https://your-app.com`
- API: `https://your-app.com/api/coins`
- Health: `https://your-app.com/health`

Happy crypto analyzing! 🚀💎