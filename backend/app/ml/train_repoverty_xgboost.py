from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sqlalchemy import text
from xgboost import XGBClassifier

from app.database import SessionLocal, engine
from app.models import HouseholdRiskScore, MlTrainingRun, RiskReasonAggregate
from app.routers.dashboard import SCOPE_ALL, SCOPE_COUNTRY, SCOPE_PROVINCE, SCOPE_REGION, get_region_map

MODEL_VERSION = datetime.utcnow().strftime("%Y%m%d%H%M%S")
MODEL_NAME = "xgboost"
ARTIFACT_DIR = Path("/app/uploads/ml")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
LOCK_FILE = Path("/tmp/ipoor_risk_train.lock")
SCHEDULE_TYPE = os.getenv("RISK_TRAIN_SCHEDULE", "manual")


def load_dataset() -> pd.DataFrame:
    sql = text(
        """
        SELECT
            hs.household_id,
            hs.survey_year,
            hs.poverty_status,
            hs.income_per_capita,
            hs.members_count,
            hs.score_b1,
            hs.score_b2,
            h.province,
            h.district,
            h.commune,
            h.ethnicity,
            h.gender,
            h.birth_date
        FROM household_surveys hs
        JOIN households h ON h.id = hs.household_id
        ORDER BY hs.household_id, hs.survey_year
        """
    )
    return pd.read_sql(sql, engine)


def build_training_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["is_escaped"] = (df["poverty_status"] == "escaped_poverty").astype(int)
    df["is_poor_or_near"] = df["poverty_status"].isin(["poor", "near_poor"]).astype(int)
    df["age"] = pd.to_datetime(df["birth_date"], errors="coerce")
    current_year = datetime.utcnow().year
    df["age"] = current_year - df["age"].dt.year

    grouped = []
    for _, g in df.groupby("household_id", sort=False):
        g = g.sort_values("survey_year").copy()
        g["income_delta"] = g["income_per_capita"].diff().fillna(0)
        g["b1_delta"] = g["score_b1"].diff().fillna(0)
        g["b2_delta"] = g["score_b2"].diff().fillna(0)
        g["next_status"] = g["poverty_status"].shift(-1)
        g["label"] = ((g["poverty_status"] == "escaped_poverty") & g["next_status"].isin(["poor", "near_poor"])).astype(int)
        grouped.append(g)

    train = pd.concat(grouped, ignore_index=True)
    train = train[train["next_status"].notna()].copy()
    train["predicted_for_year"] = train["survey_year"] + 1
    return train


def train_model(train: pd.DataFrame):
    feature_cols_num = ["income_per_capita", "members_count", "score_b1", "score_b2", "income_delta", "b1_delta", "b2_delta", "age"]
    feature_cols_cat = ["province", "district", "commune", "ethnicity", "gender", "poverty_status"]
    X = train[feature_cols_num + feature_cols_cat]
    y = train["label"].astype(int)

    if y.nunique() < 2:
        raise RuntimeError("Dataset khong du nhan class de train model")

    latest_year = int(train["survey_year"].max())
    split_year = max(int(train["survey_year"].min()) + 1, latest_year - 1)
    train_mask = train["survey_year"] < split_year
    X_train, y_train = X[train_mask], y[train_mask]
    X_val, y_val = X[~train_mask], y[~train_mask]
    if len(X_val) == 0:
        X_train, y_train = X, y
        X_val, y_val = X, y

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), feature_cols_num),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("ohe", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                feature_cols_cat,
            ),
        ]
    )
    neg = max((y_train == 0).sum(), 1)
    pos = max((y_train == 1).sum(), 1)
    clf = XGBClassifier(
        n_estimators=260,
        learning_rate=0.05,
        max_depth=5,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=42,
        scale_pos_weight=float(neg / pos),
    )
    pipe = Pipeline([("prep", preprocessor), ("model", clf)])
    pipe.fit(X_train, y_train)
    preds = pipe.predict_proba(X_val)[:, 1]
    ap = average_precision_score(y_val, preds)
    print(f"validation_pr_auc={ap:.4f}")
    joblib.dump(pipe, ARTIFACT_DIR / f"repoverty_xgb_{MODEL_VERSION}.joblib")
    return pipe, float(ap), int(len(X_train))


def build_reason_rows(scored: pd.DataFrame) -> list[dict]:
    rules = [
        ("income_drop", "Thu nhap binh quan giam", scored["income_delta"] < 0),
        ("high_b2", "Diem B2 cao", scored["score_b2"].fillna(0) >= 60),
        ("large_household", "So nhan khau lon", scored["members_count"].fillna(0) >= 6),
        ("near_poor_base", "Trang thai can ngheo hien tai", scored["poverty_status"] == "near_poor"),
    ]
    rows: list[dict] = []
    latest_target = int(scored["predicted_for_year"].max())

    def append_scope(scope_type: str, scope_name: str, frame: pd.DataFrame):
        for key, label, mask in rules:
            sub = frame[mask.loc[frame.index]]
            if len(sub) == 0:
                continue
            rows.append(
                {
                    "scope_type": scope_type,
                    "scope_name": scope_name,
                    "predicted_for_year": latest_target,
                    "reason_key": key,
                    "reason_label": label,
                    "importance": float(sub["risk_score"].mean()),
                    "affected_households": int(len(sub)),
                }
            )

    append_scope(SCOPE_COUNTRY, SCOPE_ALL, scored)
    for province, g in scored.groupby("province"):
        append_scope(SCOPE_PROVINCE, str(province), g)
    for region, g in scored.groupby("region"):
        append_scope(SCOPE_REGION, str(region), g)
    return rows


def save_predictions(train: pd.DataFrame, model: Pipeline) -> tuple[int, int]:
    latest_year = int(train["survey_year"].max())
    prediction_input = train[train["survey_year"] == latest_year].copy()
    if prediction_input.empty:
        raise RuntimeError("Khong co du lieu nam moi nhat de du bao")

    features = ["income_per_capita", "members_count", "score_b1", "score_b2", "income_delta", "b1_delta", "b2_delta", "age", "province", "district", "commune", "ethnicity", "gender", "poverty_status"]
    prediction_input["risk_score"] = model.predict_proba(prediction_input[features])[:, 1]
    prediction_input["predicted_for_year"] = latest_year + 1
    prediction_input["risk_band"] = np.where(
        prediction_input["risk_score"] >= 0.65,
        "high",
        np.where(prediction_input["risk_score"] >= 0.35, "medium", "low"),
    )
    region_map = get_region_map()
    prediction_input["region"] = prediction_input["province"].map(region_map).fillna("Khac")

    session = SessionLocal()
    try:
        target_year = latest_year + 1
        session.query(HouseholdRiskScore).filter(HouseholdRiskScore.predicted_for_year == target_year).delete()
        session.query(RiskReasonAggregate).filter(RiskReasonAggregate.predicted_for_year == target_year).delete()

        objects = [
            HouseholdRiskScore(
                household_id=int(row.household_id),
                survey_year=int(row.survey_year),
                predicted_for_year=int(row.predicted_for_year),
                scope_region=str(row.region),
                scope_province=str(row.province),
                risk_score=float(row.risk_score),
                risk_band=str(row.risk_band),
                model_name=MODEL_NAME,
                model_version=MODEL_VERSION,
            )
            for row in prediction_input.itertuples(index=False)
        ]
        if objects:
            session.bulk_save_objects(objects)

        reason_objects = [
            RiskReasonAggregate(
                scope_type=item["scope_type"],
                scope_name=item["scope_name"],
                predicted_for_year=item["predicted_for_year"],
                reason_key=item["reason_key"],
                reason_label=item["reason_label"],
                importance=item["importance"],
                affected_households=item["affected_households"],
            )
            for item in build_reason_rows(prediction_input)
        ]
        if reason_objects:
            session.bulk_save_objects(reason_objects)

        session.commit()
        print(f"saved_household_risk_scores={len(objects)}")
        print(f"saved_risk_reason_aggregates={len(reason_objects)}")
        return target_year, len(objects)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    if LOCK_FILE.exists():
        raise RuntimeError("Training job dang chay, bo qua lan goi nay")
    LOCK_FILE.write_text(datetime.utcnow().isoformat())
    session = SessionLocal()
    run = MlTrainingRun(
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        schedule_type=SCHEDULE_TYPE,
        status="running",
        started_at=datetime.utcnow(),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    try:
        raw = load_dataset()
        train = build_training_frame(raw)
        model, pr_auc, train_rows = train_model(train)
        predicted_for_year, prediction_rows = save_predictions(train, model)
        run.status = "success"
        run.finished_at = datetime.utcnow()
        run.predicted_for_year = predicted_for_year
        run.pr_auc = pr_auc
        run.train_rows = train_rows
        run.prediction_rows = prediction_rows
        session.add(run)
        session.commit()
    except Exception as exc:
        session.rollback()
        run.status = "failed"
        run.finished_at = datetime.utcnow()
        run.error_message = str(exc)[:4000]
        session.add(run)
        session.commit()
        raise
    finally:
        session.close()
        if LOCK_FILE.exists():
            LOCK_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
