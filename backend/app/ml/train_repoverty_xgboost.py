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
STALE_HOURS = 6


def check_and_mark_stale_runs(session) -> None:
    if session is None:
        session = SessionLocal()
        should_close = True
    else:
        should_close = False
    
    try:
        from datetime import timedelta
        stale_threshold = datetime.utcnow() - timedelta(hours=STALE_HOURS)
        stale_runs = (
            session.query(MlTrainingRun)
            .filter(
                MlTrainingRun.status == "running",
                MlTrainingRun.started_at < stale_threshold,
            )
            .all()
        )
        for run in stale_runs:
            run.status = "failed"
            run.finished_at = datetime.utcnow()
            run.error_message = "stale training run - exceeded 6 hours without completion"
            session.add(run)
        if stale_runs:
            session.commit()
            print(f"marked {len(stale_runs)} stale runs as failed")
    finally:
        if should_close:
            session.close()


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


def build_training_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Build training frame and return latest survey year separately"""
    df = df.copy()
    df["is_escaped"] = df["poverty_status"].str.lower().isin(["escaped_poverty", "escaped"]).astype(int)
    df["is_poor_or_near"] = df["poverty_status"].str.lower().isin(["poor", "near_poor"]).astype(int)
    df["age"] = pd.to_datetime(df["birth_date"], errors="coerce")
    current_year = datetime.utcnow().year
    df["age"] = current_year - df["age"].dt.year

    df = df.sort_values(["household_id", "survey_year"])
    df["income_delta"] = df.groupby("household_id")["income_per_capita"].diff().fillna(0)
    df["b1_delta"] = df.groupby("household_id")["score_b1"].diff().fillna(0)
    df["b2_delta"] = df.groupby("household_id")["score_b2"].diff().fillna(0)
    df["next_status"] = df.groupby("household_id")["poverty_status"].shift(-1)
    df["label"] = df["next_status"].str.lower().isin(["poor", "near_poor"]).astype(int)

    # Get latest survey year BEFORE filtering
    latest_survey_year = int(df["survey_year"].max())
    
    train = df[df["next_status"].notna()].copy()
    train["predicted_for_year"] = train["survey_year"] + 1
    return train, latest_survey_year


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
    # ===== 1. INCOME / TREND =====
    ("income_drop", "Thu nhập bình quân giảm", scored["income_delta"] < 0),
    ("sharp_income_drop", "Thu nhập giảm mạnh", scored["income_delta"] < -500000),
    
    # ===== 2. MPI / SCORE =====
    ("high_b2", "Điểm B2 cao (thiếu hụt dịch vụ)", scored["score_b2"].fillna(0) >= 60),
    ("b2_increasing", "Thiếu hụt dịch vụ gia tăng", scored["b2_delta"] > 0),
    ("b1_increasing", "Điểm thu nhập xấu đi", scored["b1_delta"] > 0),

    # ===== 3. HOUSEHOLD CHARACTERISTICS =====
    ("large_household", "Số nhân khẩu lớn", scored["members_count"].fillna(0) >= 6),
    ("very_large_household", "Hộ rất đông người", scored["members_count"].fillna(0) >= 8),

    ("elderly_risk", "Chủ hộ cao tuổi", scored["age"].fillna(0) >= 65),
    ("young_dependency", "Hộ có nhiều người phụ thuộc trẻ", scored["age"].fillna(0) < 25),

    # ===== 4. POVERTY STATUS =====
    ("near_poor_base", "Trạng thái cận nghèo hiện tại", scored["poverty_status"] == "near_poor"),
    ("recently_escaped", "Mới thoát nghèo (rủi ro tái nghèo)", scored["poverty_status"] == "escaped"),

    # ===== 5. COMBINED RISK =====
    ("income_and_b2_risk", "Thu nhập giảm + thiếu hụt dịch vụ cao",
        (scored["income_delta"] < 0) & (scored["score_b2"].fillna(0) >= 50)
    ),

    ("multi_dimensional_risk", "Nhiều yếu tố rủi ro đồng thời",
        (scored["income_delta"] < 0) &
        (scored["members_count"].fillna(0) >= 5) &
        (scored["score_b2"].fillna(0) >= 40)
    ),
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


def save_predictions(train: pd.DataFrame, model: Pipeline, latest_survey_year: int) -> tuple[int, int]:
    """Save predictions for latest survey year + 1"""
    target_year = latest_survey_year + 1
    
    # Query latest year data directly
    pred_df = pd.read_sql(text("""
        SELECT
            hs.household_id,
            hs.survey_year,
            hs.income_per_capita,
            hs.members_count,
            hs.score_b1,
            hs.score_b2,
            h.province,
            h.district,
            h.commune,
            h.ethnicity,
            h.gender,
            h.birth_date,
            hs.poverty_status
        FROM household_surveys hs
        JOIN households h ON h.id = hs.household_id
        WHERE hs.survey_year = :year
    """).bindparams(year=latest_survey_year), engine)
    
    if pred_df.empty:
        raise RuntimeError("Khong co du lieu nam moi nhat de du bao")
    
    # Calculate deltas from previous year
    prev_df = pd.read_sql(text("""
        SELECT household_id, income_per_capita, score_b1, score_b2
        FROM household_surveys
        WHERE survey_year = :year
    """).bindparams(year=latest_survey_year-1), engine)
    
    if not prev_df.empty:
        prev_df = prev_df.add_suffix("_prev").rename(columns={"household_id_prev": "household_id"})
        pred_df = pred_df.merge(prev_df, on="household_id", how="left")
        pred_df["income_delta"] = pred_df["income_per_capita"] - pred_df["income_per_capita_prev"].fillna(pred_df["income_per_capita"])
        pred_df["b1_delta"] = pred_df["score_b1"] - pred_df["score_b1_prev"].fillna(pred_df["score_b1"])
        pred_df["b2_delta"] = pred_df["score_b2"] - pred_df["score_b2_prev"].fillna(pred_df["score_b2"])
        pred_df = pred_df[[c for c in pred_df.columns if not c.endswith("_prev")]]
    else:
        pred_df["income_delta"] = 0
        pred_df["b1_delta"] = 0
        pred_df["b2_delta"] = 0
    
    # Calculate age
    pred_df["age"] = datetime.utcnow().year - pd.to_datetime(pred_df["birth_date"], errors="coerce").dt.year.fillna(0)
    
    # Predict
    features = ["income_per_capita", "members_count", "score_b1", "score_b2", "income_delta", "b1_delta", "b2_delta", "age", "province", "district", "commune", "ethnicity", "gender", "poverty_status"]
    pred_df["risk_score"] = model.predict_proba(pred_df[features])[:, 1]
    pred_df["predicted_for_year"] = target_year
    pred_df["risk_band"] = np.where(
        pred_df["risk_score"] >= 0.65, "high",
        np.where(pred_df["risk_score"] >= 0.35, "medium", "low")
    )
    
    region_map = get_region_map()
    pred_df["region"] = pred_df["province"].map(region_map).fillna("Khac")

    # Save to database
    session = SessionLocal()
    try:
        session.query(HouseholdRiskScore).filter(HouseholdRiskScore.predicted_for_year == target_year).delete()
        session.query(RiskReasonAggregate).filter(RiskReasonAggregate.predicted_for_year == target_year).delete()

        risk_rows = [
            {
                "household_id": int(row.household_id),
                "survey_year": int(row.survey_year),
                "predicted_for_year": int(row.predicted_for_year),
                "scope_region": str(row.region),
                "scope_province": str(row.province),
                "risk_score": float(row.risk_score),
                "risk_band": str(row.risk_band),
                "model_name": MODEL_NAME,
                "model_version": MODEL_VERSION,
}
            for row in pred_df.itertuples(index=False)
        ]
        if risk_rows:
            session.execute(
                HouseholdRiskScore.__table__.insert(),
                risk_rows
            )

        reason_data = build_reason_rows(pred_df)
        if reason_data:
            session.execute(
                RiskReasonAggregate.__table__.insert(),
                reason_data
            )

        session.commit()
        print(f"saved_household_risk_scores={len(risk_rows)}")
        print(f"saved_risk_reason_aggregates={len(reason_data)}")
        return target_year, len(risk_rows)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    check_and_mark_stale_runs(None)
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
        train, latest_survey_year = build_training_frame(raw)
        model, pr_auc, train_rows = train_model(train)
        predicted_for_year, prediction_rows = save_predictions(train, model, latest_survey_year)
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
