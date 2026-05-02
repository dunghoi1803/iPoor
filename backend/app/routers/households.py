from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, extract, func
from sqlalchemy.orm import Session, joinedload

from .. import deps, models, schemas
from ..constants import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, PovertyStatus
from ..utils.activity_log import log_activity
from ..utils.household_code import generate_household_code

router = APIRouter(prefix="/households", tags=["households"])


@router.get("", response_model=schemas.HouseholdListResponse)
def list_households(
    province: str | None = None,
    district: str | None = None,
    commune: str | None = None,
    status_filter: PovertyStatus | None = None,
    skip: int = 0,
    limit: int = Query(DEFAULT_PAGE_LIMIT, le=MAX_PAGE_LIMIT),
    db: Session = Depends(deps.get_db),
) -> dict[str, object]:
    query = db.query(models.Household)
    if status_filter:
        latest_survey_subquery = (
            db.query(
                models.HouseholdSurvey.household_id.label("household_id"),
                models.HouseholdSurvey.poverty_status.label("poverty_status"),
                func.row_number()
                .over(
                    partition_by=models.HouseholdSurvey.household_id,
                    order_by=(
                        models.HouseholdSurvey.survey_year.desc(),
                        models.HouseholdSurvey.survey_date.desc(),
                        models.HouseholdSurvey.id.desc(),
                    ),
                )
                .label("rn"),
            )
            .subquery()
        )
        query = query.join(
            latest_survey_subquery,
            and_(
                models.Household.id == latest_survey_subquery.c.household_id,
                latest_survey_subquery.c.rn == 1,
            ),
        ).filter(latest_survey_subquery.c.poverty_status == status_filter)
    if province:
        query = query.filter(models.Household.province == province)
    if district:
        query = query.filter(models.Household.district == district)
    if commune:
        query = query.filter(models.Household.commune == commune)
    
    total = query.count()
    households = (
        query.order_by(models.Household.id.desc())
        .options(joinedload(models.Household.surveys))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {"items": households, "total": total}


@router.post("", response_model=schemas.HouseholdRead, status_code=status.HTTP_201_CREATED)
def create_household(
    payload: schemas.HouseholdCreate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    request: Request = None,
) -> models.Household:
    household_code = (payload.household_code or "").strip()
    if not household_code:
        household_code = generate_household_code(db)
    else:
        duplicate = (
            db.query(models.Household)
            .filter(models.Household.household_code == household_code)
            .first()
        )
        if duplicate:
            household_code = generate_household_code(db)
    payload_data = payload.model_dump(exclude={"survey"})
    payload_data["household_code"] = household_code
    household = models.Household(**payload_data)
    db.add(household)
    db.flush()
    if payload.survey:
        survey_data = payload.survey.model_dump()
        survey = models.HouseholdSurvey(household_id=household.id, **survey_data)
        db.add(survey)
    log_activity(
        db,
        user_id=current_user.id,
        action="create_household",
        entity_type="household",
        entity_id=household.id,
        household_id=household.id,
        detail="Household created",
        ip_address=request.client.host if request else None,
    )
    db.commit()
    db.refresh(household)
    return household


@router.get("/{household_id}", response_model=schemas.HouseholdRead)
def get_household(
    household_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
) -> models.Household:
    household = (
        db.query(models.Household)
        .options(joinedload(models.Household.surveys))
        .filter(models.Household.id == household_id)
        .first()
    )
    if not household:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Household not found")
    return household


@router.put("/{household_id}", response_model=schemas.HouseholdRead)
def update_household(
    household_id: int,
    payload: schemas.HouseholdUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    request: Request = None,
) -> models.Household:
    household = db.query(models.Household).filter(models.Household.id == household_id).first()
    if not household:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Household not found")
    for key, value in payload.model_dump(exclude_unset=True, exclude={"survey"}).items():
        setattr(household, key, value)
    
    survey_year = datetime.now().year
    if payload.survey:
        survey_data = payload.survey.model_dump(exclude_unset=True)
        # Derive year from survey_date; auto-set survey_year
        survey_year = survey_data.get("survey_date").year if survey_data.get("survey_date") else datetime.now().year
        # Auto-fill survey_year field
        survey_data["survey_year"] = survey_year

        existing_survey = db.query(models.HouseholdSurvey).filter(
            models.HouseholdSurvey.household_id == household_id,
            extract('year', models.HouseholdSurvey.survey_date) == survey_year
        ).first()

        if existing_survey:
            for k, v in survey_data.items():
                setattr(existing_survey, k, v)
        else:
            new_survey = models.HouseholdSurvey(household_id=household.id, **survey_data)
            db.add(new_survey)

    log_activity(
        db,
        user_id=current_user.id,
        action="update_household",
        entity_type="household",
        entity_id=household.id,
        household_id=household.id,
        detail=f"Household updated (Survey year: {survey_year})",
        ip_address=request.client.host if request else None,
    )
    db.commit()
    db.refresh(household)
    return household


@router.delete("/{household_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_household(
    household_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    request: Request = None,
) -> None:
    household = db.query(models.Household).filter(models.Household.id == household_id).first()
    if not household:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Household not found")
    db.query(models.ActivityLog).filter(models.ActivityLog.household_id == household_id).delete(
        synchronize_session=False
    )
    log_activity(
        db,
        user_id=current_user.id,
        action="delete_household",
        entity_type="household",
        entity_id=household.id,
        household_id=None,
        detail="Household removed",
        ip_address=request.client.host if request else None,
    )
    db.delete(household)
    db.commit()
