#!/bin/bash
# run_demo.sh — one-command demo bootstrap for EduPredict AI
set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  EduPredict AI — Demo Bootstrap"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "→ Starting stack..."
docker compose up -d

echo "→ Waiting for API to be ready..."
until curl -sf http://localhost:8000/v1/health > /dev/null; do
  echo "  ... waiting"
  sleep 3
done

echo "→ Seeding demo API keys..."
docker compose exec -T api python scripts/seed_demo_key.py --key ep_demo_lender_2026
docker compose exec -T api python scripts/seed_demo_key.py --key ep_admin_2026 --tenant_id admin

echo "→ Seeding 50 assessments across 7 days..."
docker compose exec -T api python scripts/seed_demo_assessments.py \
  --count 50 --days 7 \
  --tenant_id demo_lender --api_key ep_demo_lender_2026

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Demo ready!"
echo ""
echo "  App:        http://localhost:8000"
echo "  Lender key: ep_demo_lender_2026"
echo "  Admin key:  ep_admin_2026"
echo "  Grafana:    http://localhost:3000"
echo "  Prometheus: http://localhost:9090"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
