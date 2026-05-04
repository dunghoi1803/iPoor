#!/bin/bash
# Refresh dashboard aggregates
docker exec ipoor_api python /app/scripts/refresh_dashboard_aggregates.py >> /var/log/ipoor_refresh.log 2>&1