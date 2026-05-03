#!/bin/sh
set -eu

SCHEDULE_TYPE="${RISK_TRAIN_SCHEDULE:-monthly}"

docker exec ipoor_api sh -c "cd /app && RISK_TRAIN_SCHEDULE=${SCHEDULE_TYPE} python -m app.ml.train_repoverty_xgboost"
