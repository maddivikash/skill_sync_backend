#!/usr/bin/env bash
# Deploy a branch to the single EC2 box WITHOUT SSH (run as root via SSM).
#
#   bash deploy/ec2-deploy-branch.sh [branch]      # default: master
#
# Why this exists: the box is not a git checkout (code is synced in), and SSH
# is often blocked because the home IP rotates. The repo is public, so the box
# can fetch the branch tarball from GitHub itself. The server .env is NEVER
# touched by the sync (it holds SECRET_KEY, GROQ keys, SMTP creds).
set -euo pipefail
BRANCH="${1:-master}"
APP=/home/ec2-user/skillsync
SRC=/home/ec2-user/deploy_src

rm -rf "$SRC" && mkdir -p "$SRC"
curl -sL "https://codeload.github.com/maddivikash/skill_sync_backend/tar.gz/refs/heads/${BRANCH}" \
  | tar xz -C "$SRC" --strip-components=1

rsync -a --exclude '.env' --exclude 'node_modules' --exclude 'dist' --exclude '__pycache__' "$SRC/" "$APP/"
chown -R ec2-user:ec2-user "$APP"
cd "$APP"

# Admins may generate/publish the daily AI digest from the app.
if ! grep -q '^ADMIN_EMAILS=' .env; then
  [ -n "$(tail -c1 .env)" ] && echo >> .env
  echo 'ADMIN_EMAILS=vikashmaddi1@gmail.com,vickyvikashmaddi@gmail.com' >> .env
fi

# Daily digest AUTO-PUBLISH at 01:00 UTC (06:30 IST); same pattern as the reminders cron.
cat > /etc/cron.d/ascend-digest <<'CRON'
0 1 * * * root cd /home/ec2-user/skillsync && /usr/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api python -m app.services.digest_service --publish >> /var/log/ascend-digest.log 2>&1
0 2 * * 0 root cd /home/ec2-user/skillsync && /usr/bin/docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T api python -m app.services.digest_service --weekly --publish >> /var/log/ascend-digest.log 2>&1
CRON
chmod 644 /etc/cron.d/ascend-digest

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build 2>&1 | tail -5
sleep 8
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs api --tail 20 2>&1 \
  | grep -i -E "alembic|entrypoint|error|e5posts" || true
docker ps --format '{{.Names}} {{.Status}}'
