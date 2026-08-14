#!/usr/bin/env bash
# =============================================================================
# Orion School Management System - Automated Hostinger VPS Deployment Script
# =============================================================================
# Usage:
#   chmod +x deploy.sh
#   sudo ./deploy.sh
# =============================================================================

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}   🚀 Orion Online School Management System Deployment     ${NC}"
echo -e "${BLUE}                 Hostinger VPS Setup                       ${NC}"
echo -e "${BLUE}============================================================${NC}\n"

# Check root privileges
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}❌ Please run this script with sudo or as root.${NC}"
  exit 1
fi

APP_DIR="/var/www/orion"
LOG_DIR="/var/log/orion"
CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${YELLOW}Step 1: Installing System Dependencies...${NC}"
apt-get update -y
apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    curl \
    git \
    nginx \
    certbot \
    python3-certbot-nginx

echo -e "${GREEN}✓ System dependencies installed.${NC}\n"

echo -e "${YELLOW}Step 2: Preparing Application Directories...${NC}"
mkdir -p "$APP_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$APP_DIR/data"
mkdir -p "$APP_DIR/web/uploads"

# If running from within the project directory, sync files to /var/www/orion if different
if [ "$CURRENT_DIR" != "$APP_DIR" ]; then
    echo "Syncing project files to $APP_DIR..."
    rsync -av --exclude 'venv' --exclude '__pycache__' --exclude '.git' "$CURRENT_DIR/" "$APP_DIR/"
fi

cd "$APP_DIR"

echo -e "${YELLOW}Step 3: Setting Up Python Virtual Environment...${NC}"
if [ ! -d "$APP_DIR/venv" ]; then
    python3 -m venv "$APP_DIR/venv"
fi

"$APP_DIR/venv/bin/pip" install --upgrade pip setuptools wheel
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo -e "${GREEN}✓ Python packages installed successfully.${NC}\n"

echo -e "${YELLOW}Step 4: Configuring Environment File (.env)...${NC}"
if [ ! -f "$APP_DIR/.env" ]; then
    if [ -f "$APP_DIR/.env.example" ]; then
        cp "$APP_DIR/.env.example" "$APP_DIR/.env"
        # Generate a unique JWT secret key
        RANDOM_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        sed -i "s/JWT_SECRET=.*/JWT_SECRET=$RANDOM_KEY/" "$APP_DIR/.env"
        echo -e "${GREEN}✓ Created new .env file with generated secure JWT key.${NC}"
    fi
else
    echo -e "${GREEN}✓ Existing .env preserved.${NC}"
fi

echo -e "${YELLOW}Step 5: Installing Systemd Service...${NC}"
if [ -f "$APP_DIR/orion.service" ]; then
    cp "$APP_DIR/orion.service" /etc/systemd/system/orion.service
    systemctl daemon-reload
    systemctl enable orion.service
fi

echo -e "${YELLOW}Step 6: Setting File Permissions...${NC}"
chown -R www-data:www-data "$APP_DIR"
chown -R www-data:www-data "$LOG_DIR"
chmod -R 775 "$APP_DIR/data"
chmod -R 775 "$APP_DIR/web/uploads"

echo -e "${YELLOW}Step 7: Starting / Restarting Orion Service...${NC}"
systemctl restart orion.service
sleep 2

# Verify health status
echo -e "${YELLOW}Step 8: Verifying Service Health...${NC}"
HEALTH_RESPONSE=$(curl -s http://127.0.0.1:8000/api/health || true)
if [[ $HEALTH_RESPONSE == *"\"status\":\"ok\""* ]]; then
    echo -e "${GREEN}✓ Orion Service is healthy and responding!${NC}"
    echo -e "Health response: $HEALTH_RESPONSE\n"
else
    echo -e "${RED}⚠️ Service started, but health response was unexpected:${NC}"
    echo "$HEALTH_RESPONSE"
    echo -e "Check logs with: journalctl -u orion.service -n 50 --no-pager"
fi

echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}🎉 Deployment to Hostinger VPS Completed Successfully!${NC}"
echo -e "${BLUE}============================================================${NC}"
echo -e "Next steps:"
echo -e "1. Configure your domain in Nginx: ${YELLOW}/etc/nginx/sites-available/orion${NC}"
echo -e "2. Enable Nginx site: ${YELLOW}sudo ln -s /etc/nginx/sites-available/orion /etc/nginx/sites-enabled/${NC}"
echo -e "3. Test and reload Nginx: ${YELLOW}sudo nginx -t && sudo systemctl reload nginx${NC}"
echo -e "4. Obtain Free SSL: ${YELLOW}sudo certbot --nginx -d your-school-domain.com${NC}"
echo -e "5. View real-time service logs: ${YELLOW}sudo journalctl -u orion.service -f${NC}\n"
