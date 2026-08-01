# GCP Deployment Guide for Auto-Mail

This guide outlines the one-time manual steps required to set up your Google Cloud Platform (GCP) Compute Engine server for production. Once these steps are complete, GitHub Actions will automatically deploy future updates.

## 1. Provision the Target Server

1. Go to GCP Console → **Compute Engine** → **VM instances**.
2. Click **Create Instance**.
3. **Name:** `limitless-ai-v1-server`
4. **Region:** `asia-south2` (Delhi)
5. **Machine Configuration:** 
   - Choose `e2-standard-2` (2 vCPU, 8 GB RAM)
6. **Boot Disk:**
   - OS: **Ubuntu 22.04 LTS**
   - Size: **25 GB** Standard Persistent Disk
7. **Firewall:**
   - Check the boxes for **Allow HTTP traffic** and **Allow HTTPS traffic**
8. Click **Create**.

## 2. Reserve a Static IP

1. Go to GCP Console → **VPC Network** → **IP Addresses**.
2. Click **Reserve External Static IP Address**.
3. Name it `limitless-ai-ip`.
4. Attach it to your `limitless-ai-v1-server` instance.

## 3. Configure DNS (Hostinger)

1. Log into your Hostinger account.
2. Go to the DNS Zone Editor for `limitless-ai.in`.
3. Add two `A` records pointing to your new GCP Static IP:
   - Type: `A`, Name: `@` (or empty), Points to: `<GCP_STATIC_IP>`
   - Type: `A`, Name: `www`, Points to: `<GCP_STATIC_IP>`

## 4. Initial Server Setup (SSH into VM)

Click the **SSH** button next to your instance in the GCP Console, or use your local terminal if you have `gcloud` CLI set up. Run the following commands:

### Install Docker and Git
```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git certbot python3-certbot-nginx
sudo usermod -aG docker $USER
newgrp docker
```

### Clone the Repository
```bash
git clone https://github.com/rishabhJain1234/Auto-mail.git ~/auto-mail
cd ~/auto-mail
```

### Set up Secrets
Create the backend `.env` file manually. Your API keys are NEVER pushed to GitHub.
```bash
mkdir -p backend
nano backend/.env
```
*Paste your production `.env` contents here (Groq key, Fireworks key, Supabase URL, etc) and save.*

## 5. First Boot & SSL Certificate

### Boot the Stack
```bash
docker compose build
docker compose up -d
```
*Note: This starts the frontend (Nginx) on port 80.*

### Generate SSL Certificate
Run Certbot. It reads the Nginx configuration matching `limitless-ai.in` and provisions the Let's Encrypt certificates automatically.

```bash
sudo certbot --nginx -d limitless-ai.in -d www.limitless-ai.in
```
*Follow the prompts. Choose "Redirect" so HTTP traffic automatically goes to HTTPS.*

### Restart Nginx Template
Certbot automatically tweaks the Nginx config inside the file, but because Nginx is running in Docker, we need to pass the newly generated SSL certificates into the Docker volume mapping by restarting the frontend container:
```bash
docker compose down
docker compose up -d
```

## 6. Set up GitHub Actions CI/CD Secrets

On your local machine or via GCP Console, you need an SSH key that GitHub can use to deploy.
If you don't have one on the VM:
```bash
ssh-keygen -t rsa -b 4096 -C "github-actions"
# Press Enter for all prompts
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
cat ~/.ssh/id_rsa # Copy this private key!
```

Go to **GitHub** → **Settings** (for the repo) → **Secrets and variables** → **Actions** → **New repository secret**.

Add the following 3 secrets:
1. `GCP_SSH_PRIVATE_KEY` : *(The private key you just copied, starting with `-----BEGIN...`)*
2. `GCP_VM_IP` : *(Your GCP Static IP)*
3. `GCP_VM_USER` : *(Your GCP username, usually `ubuntu` or your Google login name)*

## Done! 🚀
Any subsequent push to the `main` branch will automatically deploy to `limitless-ai.in`.
