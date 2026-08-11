#!/usr/bin/env bash
# One-shot installer for Ubuntu VPS (Cloud Himalaya etc.)
# Usage: sudo bash deploy/install.sh yourdomain.com.np
set -euo pipefail

DOMAIN="${1:-}"
APP_DIR=/opt/nepal-call-agent

echo "==> Installing system packages"
apt-get update -qq
apt-get install -y -qq python3-venv python3-pip nginx certbot python3-certbot-nginx

echo "==> Copying app to $APP_DIR"
mkdir -p "$APP_DIR"
cp -r "$(dirname "$0")/.." "$APP_DIR" 2>/dev/null || true
cd "$APP_DIR"

echo "==> Python environment"
python3 -m venv venv
./venv/bin/pip install -q fastapi "uvicorn[standard]" python-multipart \
  anthropic python-dotenv websockets httpx pydantic twilio

if [ ! -f .env ]; then
  cp .env.example .env
  # generate a strong admin key automatically
  ADMIN_KEY=$(python3 -c "import secrets;print(secrets.token_urlsafe(32))")
  sed -i "s|ADMIN_API_KEY=.*|ADMIN_API_KEY=$ADMIN_KEY|" .env
  echo "!!  Edit $APP_DIR/.env — add your ANTHROPIC_API_KEY. Admin key generated."
fi

chown -R www-data:www-data "$APP_DIR"

echo "==> systemd service"
cp deploy/callagent.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now callagent

echo "==> nginx"
sed "s/calls.yourdomain.com.np/${DOMAIN:-_}/" deploy/nginx.conf \
  > /etc/nginx/sites-available/callagent
ln -sf /etc/nginx/sites-available/callagent /etc/nginx/sites-enabled/callagent
nginx -t && systemctl reload nginx

if [ -n "$DOMAIN" ]; then
  echo "==> HTTPS certificate"
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
    -m admin@"$DOMAIN" || echo "(run certbot manually if DNS isn't ready yet)"
fi

echo ""
echo "Done. Next steps:"
echo "  1. nano $APP_DIR/.env   → set ANTHROPIC_API_KEY"
echo "  2. systemctl restart callagent"
echo "  3. Open https://${DOMAIN:-<your-ip>}/admin  (key is in .env)"
echo "  4. Create your first tenant, then open /portal on your phone."
