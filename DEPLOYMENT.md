# 🔵 Azure Deployment Guide# 🚀 Cloud Deployment Guide



Your Crypto Investment Analyzer deployment guide for Microsoft Azure.Your Crypto Investment Analyzer is now ready for cloud deployment! Choose from multiple hosting options below.



## 📋 **Prerequisites**## 📋 **Quick Setup**



- Azure account ([Create free account](https://azure.microsoft.com/free/))### 1. Install Web Dependencies

- Azure CLI installed locally```bash

- Git repository with your codepip install flask gunicorn

```

### Install Azure CLI

```bash### 2. Test Locally

# macOS```bash

brew install azure-clipython web_app.py

# Visit: http://localhost:8080

# Windows (PowerShell)```

Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile .\AzureCLI.msi; Start-Process msiexec.exe -Wait -ArgumentList '/I AzureCLI.msi /quiet'

## ☁️ **Cloud Hosting Options**

# Ubuntu/Debian

curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash### 🔥 **Option 1: Heroku (Easiest)**

```

**Steps:**

## 🚀 **Deployment Options**1. Create Heroku account at [heroku.com](https://heroku.com)

2. Install Heroku CLI

### **Option 1: Azure App Service (Recommended)**3. Deploy:

Best for Python web applications with automatic scaling.```bash

# Login to Heroku

#### **Quick Deployment**heroku login

```bash

# 1. Login to Azure# Create app

az loginheroku create your-crypto-analyzer



# 2. Create resource group# Deploy

az group create --name crypto-analyzer-rg --location eastusgit add .

git commit -m "Deploy crypto analyzer"

# 3. Create App Service plangit push heroku main

az appservice plan create \

  --name crypto-analyzer-plan \# Open your app

  --resource-group crypto-analyzer-rg \heroku open

  --sku B1 \```

  --is-linux

**Files needed:** ✅ Already created

# 4. Create web app- `Procfile` - Heroku process configuration

az webapp create \- `requirements.txt` - Python dependencies

  --resource-group crypto-analyzer-rg \- `runtime.txt` - Python version

  --plan crypto-analyzer-plan \

  --name your-crypto-analyzer \---

  --runtime "PYTHON|3.9"

### 🐳 **Option 2: Docker + Any Cloud**

# 5. Configure startup command

az webapp config set \**Build and run locally:**

  --resource-group crypto-analyzer-rg \```bash

  --name your-crypto-analyzer \# Build image

  --startup-file "gunicorn --bind=0.0.0.0 --timeout 600 web_app:app"docker build -t crypto-analyzer .



# 6. Enable local Git deployment# Run container

az webapp deployment source config-local-git \docker run -p 8080:8080 crypto-analyzer

  --name your-crypto-analyzer \

  --resource-group crypto-analyzer-rg# Or use docker-compose

docker-compose up

# 7. Deploy your code```

git remote add azure <git-url-from-step-6>

git push azure development:master**Deploy to:**

```- **Google Cloud Run**

- **AWS ECS**

#### **Environment Variables (Optional)**- **Azure Container Instances**

```bash- **DigitalOcean Apps**

# Set environment variables if needed

az webapp config appsettings set \---

  --resource-group crypto-analyzer-rg \

  --name your-crypto-analyzer \### ⚡ **Option 3: Vercel (Serverless)**

  --settings FLASK_ENV=production

```**Steps:**

1. Install Vercel CLI: `npm i -g vercel`

---2. Deploy:

```bash

### **Option 2: Azure Container Instances**vercel --prod

Use Docker containers for more control over the environment.```



#### **Build and Deploy Container****Files needed:** ✅ Already created

```bash- `vercel.json` - Vercel configuration

# 1. Build Docker image locally

docker build -t crypto-analyzer .---



# 2. Create Azure Container Registry### 🌐 **Option 4: Google Cloud Platform**

az acr create \

  --resource-group crypto-analyzer-rg \**Deploy to App Engine:**

  --name cryptoanalyzeracr \```bash

  --sku Basic# Install gcloud CLI

gcloud app deploy

# 3. Login to registry

az acr login --name cryptoanalyzeracr# View app

gcloud app browse

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