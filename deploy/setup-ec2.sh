#!/usr/bin/env bash
# ==============================================================================
# QuantAI Trading Bot - Automated AWS EC2 Server Setup Script
# Supported OS: Ubuntu 22.04 LTS / Ubuntu 24.04 LTS / Debian 12
# ==============================================================================
set -e

echo "=========================================================="
echo " 🚀 Setting up QuantAI Trading Bot on AWS EC2 Instance"
echo "=========================================================="

# 1. Update OS and install essential packages
echo "📦 Updating packages..."
sudo apt-get update -y
sudo apt-get upgrade -y
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release git ufw fail2ban

# 2. Install Docker
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker Engine..."
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Enable Docker service
    sudo systemctl enable docker
    sudo systemctl start docker
    
    # Add current user to docker group to run docker without sudo
    sudo usermod -aG docker "$USER"
    echo "✅ Docker installed successfully."
else
    echo "✅ Docker is already installed."
fi

# 3. Configure Basic Firewall (UFW)
echo "🛡️ Configuring Firewall rules (Ports: 22, 80, 443, 8000)..."
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow 80/tcp comment 'HTTP'
sudo ufw allow 443/tcp comment 'HTTPS'
sudo ufw allow 8000/tcp comment 'QuantAI Dashboard & API'
sudo ufw --force enable

echo "=========================================================="
echo " 🎉 EC2 Environment Setup Complete!"
echo " If this is your first time adding the user to the docker group,"
echo " run: 'newgrp docker' or log out and log back in."
echo " Next step: Navigate to your repository and copy .env.example to .env"
echo "=========================================================="
