#!/usr/bin/env bash
# Deploy MHFA agent on the site server (run as root or with sudo).
set -euo pipefail

SITE_SLUG="${1:-saroshan}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

install -d -m 0755 /opt/mhfa /etc/mhfa-agent
install -m 0755 "${REPO_ROOT}/scripts/mhfa_agent.py" /opt/mhfa/mhfa_agent.py
install -m 0640 "${REPO_ROOT}/scripts/mhfa-agent.env.example" "/etc/mhfa-agent/${SITE_SLUG}.env.example"

if command -v pip3 >/dev/null 2>&1; then
  pip3 install -r "${REPO_ROOT}/requirements-agent.txt"
fi

install -m 0644 "${REPO_ROOT}/scripts/systemd/mhfa-agent@.service" /etc/systemd/system/mhfa-agent@.service
systemctl daemon-reload

echo "Edit /etc/mhfa-agent/${SITE_SLUG}.env with MHFA_AGENT_TOKEN from live panel, then:"
echo "  cp /etc/mhfa-agent/${SITE_SLUG}.env.example /etc/mhfa-agent/${SITE_SLUG}.env"
echo "  systemctl enable --now mhfa-agent@${SITE_SLUG}"
