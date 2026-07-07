# AL-CLINICA Deployment & Security Guide

This guide details how to securely deploy the **AL-CLINICA Patient Website** to a production server, manage security variables, and select the optimal hosting environment for low-load setups.

---

## 1. Hosting Environment Recommendations

Since the clinic website is a low-traffic web application (serving static landing pages, loading doctor JSON data, and handling infrequent WhatsApp bookings), you do not need expensive hosting.

### Option A: Render (Recommended — Easiest & Safest)
* **What it is**: A managed Platform-as-a-Service (PaaS) similar to Heroku.
* **Cost**: ~$7/month (starter tier for web services).
* **Why it's great**:
  * **Automatic HTTPS**: Render handles SSL certificates automatically through Let's Encrypt and auto-renews them.
  * **Managed Security**: Built-in DDoS protection, firewalls, and security patching.
  * **Git-Ops Deployment**: Every time you push to your GitHub `main` branch, Render automatically redeploys.
  * **Zero Server Configuration**: You do not have to configure Linux, Nginx, or Docker manually.

### Option B: DigitalOcean Droplet (Self-Managed VPS)
* **What it is**: A Virtual Private Server (VPS).
* **Cost**: ~$4 to $6/month (basic droplet).
* **Why it's great**:
  * Complete control over configuration.
  * Extremely cost-effective for running multiple Dockerized apps.
  * Perfect if you already have custom docker setup.
  * **Caveat**: You must manually configure the Linux firewall, SSH access, Nginx reverse proxy, and Let's Encrypt SSL.

---

## 2. Pre-Deployment Configuration Checklist

We have modified the codebase to support secure environment variables and prevent arbitrary file execution. Perform the following steps before deploying:

### Step 1: Create your `.env` File
Create a `.env` file in the root directory (this file is excluded from Git to prevent exposing credentials). Copy variables from `.env.example`:

```bash
cp .env.example .env
```

Open the newly created `.env` file and set secure production values:

```ini
# Admin Login Credentials (DO NOT USE 'admin123' IN PRODUCTION)
ADMIN_USERNAME=your_secure_admin_username
ADMIN_PASSWORD=your_highly_secure_random_password

# Cookie Security Settings
# Must be set to true in production so cookies only travel over HTTPS.
SECURE_COOKIES=true
```

### Step 2: Ensure Data & Upload Directories Are Persisted
* When deploying via Docker, the `data.json` database and `uploads/` directory must be mapped to persistent volumes so doctor records and photo uploads aren't erased during container updates. We've configured this in `docker-compose.yml`.

---

## 3. Step-by-Step Deployment Options

### Option A: Deploying on Render (Platform as a Service)

1. Sign up on [Render](https://render.com) and connect your GitHub account.
2. Click **New +** and select **Web Service**.
3. Choose your repository `itsmethahseer/home-page--AL-Clinica`.
4. Configure the service:
   * **Runtime**: Docker (Render automatically detects your `Dockerfile`).
   * **Instance Type**: Starter or Free.
5. Expand the **Advanced** section:
   * Click **Add Environment Variable** and define:
     * `ADMIN_USERNAME` = `(your custom admin username)`
     * `ADMIN_PASSWORD` = `(your custom secure password)`
     * `SECURE_COOKIES` = `true`
   * Click **Add Disk** to mount persistent storage (so data survives restarts):
     * **Name**: `clinic_data`
     * **Mount Path**: `/app/data` (Ensure you update data loading paths in Python if moving database to a mounted volume, or simply rely on Render's disk mount mapping).
6. Click **Deploy Web Service**. Render will build the Docker container and provide a secure `https://...onrender.com` URL.

---

### Option B: Deploying on a DigitalOcean Droplet (VPS)

If you select a basic Droplet with Ubuntu 22.04 LTS:

#### 1. Server Hardening (Run on the VPS terminal)
* **Update the System**:
  ```bash
  sudo apt update && sudo apt upgrade -y
  ```
* **Configure Firewall (UFW)**: Block all incoming ports except SSH, HTTP, and HTTPS:
  ```bash
  sudo ufw default deny incoming
  sudo ufw default allow outgoing
  sudo ufw allow ssh
  sudo ufw allow http
  sudo ufw allow https
  sudo ufw enable
  ```
* **Install Docker & Docker Compose**:
  Follow official instructions or install via package manager:
  ```bash
  sudo apt install docker.io docker-compose-v2 -y
  ```

#### 2. Deploy your App
* Clone your git repository to `/var/www/al-clinica`:
  ```bash
  git clone git@github-itsmethahseer:itsmethahseer/home-page--AL-Clinica.git /var/www/al-clinica
  ```
* Copy `.env.example` to `.env` and fill in the values:
  ```bash
  cd /var/www/al-clinica
  cp .env.example .env
  nano .env
  ```
* Build and start the container in detached mode:
  ```bash
  docker compose up -d --build
  ```

#### 3. Setup SSL (Let's Encrypt HTTPS)
* Use **Nginx** as a reverse proxy to route traffic from port `80` (HTTP) and `443` (HTTPS) to the local container running on port `3000`.
* Install Certbot to generate and auto-renew Let's Encrypt certificates:
  ```bash
  sudo apt install nginx certbot python3-certbot-nginx -y
  ```
* Configure Nginx (`/etc/nginx/sites-available/default`) to proxy traffic:
  ```nginx
  server {
      server_name clinic.yourdomain.com;

      location / {
          proxy_pass http://127.0.0.1:3000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }
  }
  ```
* Enable SSL via Certbot:
  ```bash
  sudo certbot --nginx -d clinic.yourdomain.com
  ```
  Certbot will secure the Nginx connection and automatically redirect all HTTP requests to HTTPS!

---

## 4. Key Security Controls Implemented

1. **Environment Variables Configuration**: Admin username and passwords are no longer exposed in the raw source code.
2. **Secure Session Cookie**: Added `SameSite=lax` (prevents cross-site request forgery) and supports the `Secure` flag (cookies are never transmitted over unencrypted HTTP).
3. **Safe File Uploads**: Added strict extension matching to block executable scripts (`.php`, `.py`, `.html`, `.sh`) from being uploaded to the uploads directory.
