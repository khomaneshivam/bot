# 🚀 QuantAI — Autonomous Institutional Forex & Crypto Trading Bot

[![CI/CD Pipeline](https://github.com/khomaneshivam/bot/actions/workflows/deploy.yml/badge.svg)](https://github.com/khomaneshivam/bot/actions/workflows/deploy.yml)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://react.dev)

An institutional-grade autonomous trading terminal featuring neural-driven signal generation, continuous live retraining, negative experience shields, and real-time telemetry streaming via WebSockets.

---

## 🏗️ Architecture

- **Frontend**: React 18, Tailwind CSS, Lucide icons, Vite, Canvas-based live tick charts & telemetry dashboard.
- **Backend**: Python 3.11, FastAPI, Uvicorn, WebSockets, Pandas, Scikit-learn, SQLite trade ledger.
- **AI Engine**: Google Gemini (Google AI Studio) for macroeconomic reasoning, market catalysts, and trade veto safeguards.
- **Broker Bridge**: Native MetaTrader 5 execution (Windows) / Cross-platform Paper & Demo execution (Linux / Docker / EC2).

---

## 🚀 Quick Start (Local Run)

### Prerequisites
- Python 3.11+
- Node.js 20+ (for building frontend)

### 1. Setup Environment
```bash
# Clone the repository
git clone https://github.com/khomaneshivam/bot.git
cd bot

# Copy example environment configuration
cp .env.example forex-trading-bot/.env
```

Edit `forex-trading-bot/.env` and paste your Google Gemini API key:
```ini
GEMINI_API_KEY=your_actual_gemini_api_key
```

### 2. Run with Docker Compose
```bash
docker compose up -d --build
```
Access the dashboard at `http://localhost:8000`.

### 3. Run Directly with Python
```bash
cd forex-trading-bot
pip install -r requirements.txt
python run.py
```

---

## ☁️ AWS EC2 Deployment Guide

### 1. Launch an EC2 Instance
- **AMI**: Ubuntu 24.04 LTS or 22.04 LTS
- **Instance Type**: `t3.medium` or `t3.small` (min 2GB RAM recommended)
- **Security Group (Inbound Rules)**:
  - `SSH` (Port 22) from your IP or `0.0.0.0/0`
  - `Custom TCP` (Port 8000) from `0.0.0.0/0` (for Dashboard UI)
  - `HTTP` (Port 80) and `HTTPS` (Port 443) (optional if using reverse proxy)

### 2. Provision EC2 with One Command
SSH into your EC2 instance and run:
```bash
curl -fsSL https://raw.githubusercontent.com/khomaneshivam/bot/main/deploy/setup-ec2.sh | bash
```
This automatically updates packages, installs Docker, and configures the firewall.

### 3. Clone and Run
```bash
git clone https://github.com/khomaneshivam/bot.git ~/bot
cd ~/bot
cp .env.example forex-trading-bot/.env

# Add your Gemini API key:
nano forex-trading-bot/.env

# Start the bot:
docker compose up -d --build
```

---

## 🔄 CI/CD Pipeline (GitHub Actions)

This repository includes a production-ready CI/CD pipeline at `.github/workflows/deploy.yml`.

### How It Works:
1. **CI Quality Gate**: On every push or pull request to `main`, GitHub Actions:
   - Compiles and builds the React 18 frontend.
   - Installs Python dependencies and verifies server modules.
   - Validates multi-stage Docker build.
2. **Automated EC2 CD Deployment**: When code is pushed to `main`, GitHub Actions connects via SSH to your EC2 instance and runs `deploy/deploy.sh` to update containers with zero manual effort.

### Enabling Auto-Deployment:
In your GitHub repository, go to **Settings** ➔ **Secrets and variables** ➔ **Actions** and add:
- `EC2_HOST`: Your EC2 instance public IP (e.g., `54.210.xx.xx`)
- `EC2_USER`: SSH username (`ubuntu` for Ubuntu AMIs or `ec2-user` for Amazon Linux)
- `EC2_SSH_KEY`: Full contents of your private SSH key (`.pem` file)
- `EC2_PORT`: `22` (optional, default is 22)

---

## ⚙️ Environment Configuration Reference

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SERVER_HOST` | Host address to bind server (`0.0.0.0` for EC2 / Docker) | `0.0.0.0` |
| `SERVER_PORT` | HTTP port for API and Dashboard | `8000` |
| `ENVIRONMENT` | Running environment (`production` / `development`) | `production` |
| `GEMINI_API_KEY` | Google Gemini API key from AI Studio | Required for AI |
| `GEMINI_MODEL` | Model version | `gemini-2.5-flash` |
| `MT5_ACCOUNT` | MetaTrader 5 account ID | `0` |
| `MT5_PASSWORD` | MetaTrader 5 password | - |
| `MT5_SERVER` | MetaTrader 5 broker server | `MetaQuotes-Demo` |
| `BINANCE_API_KEY` | Binance Crypto API key (Optional) | - |
| `BINANCE_SECRET_KEY`| Binance Crypto Secret key (Optional) | - |
| `BINANCE_TESTNET` | Toggle Binance Testnet | `True` |

---

## 📜 License
MIT License. Created for quantitative and autonomous trading research.
