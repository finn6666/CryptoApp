# RHEL SSL Deployment Checklist

Before running the SSL setup script, make sure these are complete:

## ✅ Pre-Deployment Checklist

### 1. Domain Setup
- [ ] Domain purchased and DNS configured
- [ ] A record points to Azure VM public IP
- [ ] DNS propagated (test: `nslookup yourdomain.com`)

### 2. Azure VM Requirements
- [ ] VM running RHEL
- [ ] CryptoApp installed at `~/CryptoApp`
- [ ] App service (`cryptoapp`) running
- [ ] Nginx installed

### 3. Azure Network Security Group
- [ ] Port 22 (SSH) - Allow from your IP
- [ ] Port 80 (HTTP) - Allow from Any
- [ ] Port 443 (HTTPS) - Allow from Any

### 4. Test Current Setup
```bash
# Verify app is running
sudo systemctl status cryptoapp

# Verify nginx is installed
nginx -v

# Verify app responds
curl http://localhost:5001/health
```

---

## 🚀 Quick SSL Deployment

### Step 1: Upload Script to VM

**Option A: Git (Recommended)**
```bash
# On your local machine - commit the script
cd ~/Dev/CryptoApp
git add deploy/setup-ssl-rhel.sh
git commit -m "Add RHEL SSL setup script"
git push origin main

# On Azure VM
ssh your-username@your-vm-ip
cd ~/CryptoApp
git pull origin main
chmod +x deploy/setup-ssl-rhel.sh
```

**Option B: SCP (Direct Transfer)**
```bash
# From your local machine
scp deploy/setup-ssl-rhel.sh your-username@your-vm-ip:~/
```

### Step 2: Run Setup Script

```bash
# SSH to VM
ssh your-username@your-vm-ip

# Run script (replace with your domain and email)
cd ~/CryptoApp
sudo ./deploy/setup-ssl-rhel.sh crypto.example.com your-email@example.com

# Or if copied directly to home:
sudo ~/setup-ssl-rhel.sh crypto.example.com your-email@example.com
```

### Step 3: Verify

```bash
# Check HTTPS works
curl -I https://yourdomain.com

# Check HTTP redirects to HTTPS
curl -I http://yourdomain.com

# View logs
sudo journalctl -u cryptoapp -n 30
sudo tail -f /var/log/nginx/access.log
```

---

## 🔍 What the Script Does

1. **Installs Certbot** - Let's Encrypt client
2. **Stops nginx** - Required for standalone verification
3. **Requests SSL certificate** - Automated, free from Let's Encrypt
4. **Creates nginx config** - With HTTPS, redirects, security headers
5. **Configures SELinux** - Allows nginx to connect to backend
6. **Opens firewall ports** - HTTP (80) and HTTPS (443)
7. **Tests configuration** - Validates nginx config before starting
8. **Starts services** - nginx and cryptoapp
9. **Sets up auto-renewal** - Certificate renews automatically

---

## 🛡️ Security Features Enabled

✅ **TLS 1.2 & 1.3** - Modern encryption protocols  
✅ **HSTS** - Forces HTTPS for 1 year  
✅ **Security Headers** - X-Frame-Options, X-Content-Type, etc.  
✅ **HTTP → HTTPS Redirect** - All traffic encrypted  
✅ **Auto-renewal** - Certificate renews before expiration  
✅ **SELinux** - Configured correctly  
✅ **Firewall** - Only necessary ports open  

---

## 📊 Post-Deployment Verification

### Check SSL Grade
Visit: https://www.ssllabs.com/ssltest/
- Enter your domain
- Should get **A or A+** rating

### Test Security Headers
```bash
curl -I https://yourdomain.com
# Should see:
# - Strict-Transport-Security
# - X-Frame-Options
# - X-Content-Type-Options
# - X-XSS-Protection
```

### Verify Auto-Renewal
```bash
# Check renewal timer
sudo systemctl status certbot-renew.timer

# Test renewal (dry run)
sudo certbot renew --dry-run

# Check certificate expiration
sudo certbot certificates
```

---

## 🔧 Troubleshooting

### Certificate Request Failed

**DNS not propagated:**
```bash
# Check DNS
nslookup yourdomain.com

# Should return your VM's public IP
```

**Port 80 blocked:**
```bash
# Check firewall
sudo firewall-cmd --list-all

# Check Azure NSG in portal
```

**Domain not owned:**
- Verify you own the domain
- Check DNS configuration at your registrar

### Nginx Won't Start

**Test configuration:**
```bash
sudo nginx -t
```

**Check logs:**
```bash
sudo tail -f /var/log/nginx/error.log
```

**SELinux blocking:**
```bash
# Check denials
sudo ausearch -m avc -ts recent

# If needed, allow
sudo setsebool -P httpd_can_network_connect 1
```

### 502 Bad Gateway

**Backend not running:**
```bash
sudo systemctl status cryptoapp
sudo systemctl start cryptoapp
```

**Port mismatch:**
```bash
# Verify gunicorn is on port 5001
sudo netstat -tlnp | grep 5001
```

---

## 🔄 Manual Certificate Renewal

If auto-renewal fails:

```bash
# Renew certificate
sudo certbot renew

# Reload nginx
sudo systemctl reload nginx

# Check expiration
sudo certbot certificates
```

---

## 📝 Update After SSL Setup

Don't forget to update your app's configuration:

```bash
# Edit .env if needed
nano ~/CryptoApp/.env

# Add/update:
FLASK_ENV=production
FLASK_DEBUG=False

# Restart app
sudo systemctl restart cryptoapp
```

---

## ⏱️ Estimated Time

- **Script execution**: 2-5 minutes
- **DNS propagation**: 0-48 hours (if just configured)
- **Total setup**: 5-10 minutes (if DNS ready)

---

## 💰 Cost

- **SSL Certificate**: FREE (Let's Encrypt)
- **Maintenance**: Automated, no ongoing costs
- **Renewal**: Automatic, FREE

---

## 📞 Need Help?

**Check logs:**
```bash
# App logs
sudo journalctl -u cryptoapp -n 100

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/cryptoapp_error.log

# Certificate logs
sudo journalctl -u certbot -n 50
```

**Revert to HTTP only:**
```bash
sudo rm /etc/nginx/conf.d/cryptoapp.conf
sudo cp ~/CryptoApp/deploy/nginx-cryptoapp.conf /etc/nginx/conf.d/
sudo nginx -t && sudo systemctl restart nginx
```
