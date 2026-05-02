
import csv
import json
import random
import time
from datetime import date, datetime
from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import Household, HouseholdSurvey, PovertyThreshold, User, Policy, DashboardAggregate
from app.constants import PovertyStatus, Roles, PolicyCategory
from app.utils.security import get_password_hash
from app.routers.dashboard import ensure_dashboard_aggregates

# Constants for realistic data generation
SURNAMES = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Phan", "Vũ", "Đặng", "Bùi", "Đỗ"]
MIDDLE_NAMES = ["Văn", "Thị", "Hữu", "Minh", "Đức", "Ngọc", "Hoàng", "Kim"]
FIRST_NAMES = ["Hùng", "Lan", "Tuấn", "Mai", "Cường", "Hoa", "Dũng", "Huệ", "Sơn", "Linh"]
OFFICERS = ["Nguyễn Văn An", "Trần Thị Bình", "Lê Văn Cường", "Phạm Thị Dung", "Hoàng Văn Em"]
ETHNICITIES = ["Kinh"] * 85 + ["Tày", "Thái", "Mường", "Khơ Me", "Nùng", "H'Mông", "Dao", "Gia Rai", "Ê Đê"]

def generate_name():
    return f"{random.choice(SURNAMES)} {random.choice(MIDDLE_NAMES)} {random.choice(FIRST_NAMES)}"

def parse_stats(csv_path):
    stats = defaultdict(lambda: defaultdict(dict))
    with open(csv_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            indicator = row['indicator_code']
            geo_name = row['geo_name']
            year = row['year']
            value = row['value']
            try:
                val = float(value)
            except:
                val = 0.0
            if indicator == '1.1':
                stats[geo_name][year]['poor_rate'] = val
            elif indicator == '1.4':
                stats[geo_name][year]['near_poor_rate'] = val
            elif indicator == '1.3':
                stats[geo_name][year]['poor_count'] = val
            elif indicator == '1.5':
                stats[geo_name][year]['near_poor_count'] = val
    return stats

def seed_bulk_data(total_households=500000, batch_size=5000):
    print(f"Starting bulk seeding of {total_households} households with optimized distribution...")
    start_time = time.time()
    
    # 1. Initialize DB and Truncate
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Truncating existing data...")
        db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        tables = ["activity_logs", "data_collections", "dashboard_aggregates", "household_surveys", "households", "poverty_thresholds", "policies", "policy_drafts", "users"]
        for table in tables:
            db.execute(text(f"TRUNCATE TABLE {table};"))
        db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        db.commit()

        # 2. Seed Base Data
        print("Seeding base data...")
        hashed_pwd = get_password_hash("18032002")
        admin = User(email="admin@ipoor.local", full_name="Admin System", hashed_password=hashed_pwd, role=Roles.ADMIN, org_level="tw", province="Hà Nội")
        db.add(admin)
        
        # Extended thresholds
        thresholds = [
            PovertyThreshold(year=2022, area_type="Nông thôn", b1_threshold=140, b2_deprived_min=30),
            PovertyThreshold(year=2023, area_type="Nông thôn", b1_threshold=145, b2_deprived_min=30),
            PovertyThreshold(year=2024, area_type="Nông thôn", b1_threshold=150, b2_deprived_min=30),
            PovertyThreshold(year=2025, area_type="Nông thôn", b1_threshold=155, b2_deprived_min=30),
            PovertyThreshold(year=2026, area_type="Nông thôn", b1_threshold=160, b2_deprived_min=30),
            PovertyThreshold(year=2022, area_type="Thành thị", b1_threshold=165, b2_deprived_min=30),
            PovertyThreshold(year=2023, area_type="Thành thị", b1_threshold=170, b2_deprived_min=30),
            PovertyThreshold(year=2024, area_type="Thành thị", b1_threshold=175, b2_deprived_min=30),
            PovertyThreshold(year=2025, area_type="Thành thị", b1_threshold=180, b2_deprived_min=30),
            PovertyThreshold(year=2026, area_type="Thành thị", b1_threshold=185, b2_deprived_min=30),
        ]
        for t in thresholds:
            db.add(t)
        db.commit()

        # 3. Prepare Province Distributions
        with open("/app/FE/data/processed/region_map.json", "r") as f:
            region_map = json.load(f)
        
        provinces = list(region_map["province_to_region"].keys())
        stats = parse_stats("/app/FE/data/processed/group1_values.csv")
        
        prov_weights = {}
        total_weight = 0
        for p in provinces:
            p_stats = stats.get(p, {})
            # Use 2021 as a baseline for province weight
            s = p_stats.get("2021") or p_stats.get("2022") or p_stats.get("2023") or {}
            count = s.get("poor_count", 1000)
            rate = s.get("poor_rate", 1.0)
            if rate == 0: rate = 0.1
            weight = count / (rate / 100)
            prov_weights[p] = weight
            total_weight += weight
            
        # 4. Generate Households in Batches
        hh_counter = 0
        current_id = 1
        
        for p in provinces:
            p_target = int((prov_weights[p] / total_weight) * total_households)
            if p_target == 0: p_target = 1
            
            print(f"Generating {p_target} households for {p}...")
            districts = [f"Huyện {d}" for d in ["A", "B", "C", "D", "E"]]
            communes = [f"Xã {c}" for c in range(1, 11)]
            
            # Distribution parameters for each year
            p_stats_years = {
                2022: stats.get(p, {}).get("2021", {}), 
                2023: stats.get(p, {}).get("2022", {}),
                2024: stats.get(p, {}).get("2023", {}),
                2025: stats.get(p, {}).get("2024", {}),
                2026: stats.get(p, {}).get("2024", {}) # Fallback to 2024
            }

            p_batches = (p_target // batch_size) + 1
            for b in range(p_batches):
                b_size = min(batch_size, p_target - (b * batch_size))
                if b_size <= 0: break
                
                households_batch = []
                surveys_batch = []
                
                for _ in range(b_size):
                    hh_id = current_id
                    hh_code = f"HH-{hh_id:07d}"
                    area_type = random.choice(["Thành thị", "Nông thôn"])
                    
                    hh_dict = {
                        "id": hh_id,
                        "household_code": hh_code,
                        "head_name": generate_name(),
                        "gender": random.choice(["Nam", "Nữ"]),
                        "ethnicity": random.choice(ETHNICITIES),
                        "province": p,
                        "district": random.choice(districts),
                        "commune": random.choice(communes),
                        "area": area_type,
                        "created_at": datetime.utcnow()
                    }
                    households_batch.append(hh_dict)
                    
                    # Generate surveys
                    for year in [2022, 2023, 2024, 2025, 2026]:
                        s_stats = p_stats_years[year]
                        poor_rate = s_stats.get("poor_rate", 5.0)
                        near_poor_rate = s_stats.get("near_poor_rate", 3.0)
                        
                        # Heuristic for Escaped: those who escaped poverty in the last year
                        # We'll set it as a fraction of the poor population to keep it realistic
                        escaped_rate = poor_rate * random.uniform(0.15, 0.35)
                        
                        # Normalize these 3 categories to 100% within our tracked sample
                        total_tracked = poor_rate + near_poor_rate + escaped_rate
                        if total_tracked == 0: total_tracked = 0.1
                        
                        rand = random.random() * total_tracked
                        
                        if rand < poor_rate:
                            status = PovertyStatus.POOR
                            income = random.randint(50, 140)
                        elif rand < (poor_rate + near_poor_rate):
                            status = PovertyStatus.NEAR_POOR
                            income = random.randint(141, 170)
                        else:
                            status = PovertyStatus.ESCAPED
                            income = random.randint(171, 300)
                            
                        survey_dict = {
                            "household_id": hh_id,
                            "survey_year": year,
                            "survey_date": date(year, random.randint(1, 12), random.randint(1, 28)),
                            "poverty_status": status,
                            "income_per_capita": income * 10000,
                            "members_count": random.randint(1, 7),
                            "score_b1": income,
                            "score_b2": random.randint(10, 50),
                            "officer": random.choice(OFFICERS),
                            "created_at": datetime.utcnow()
                        }
                        surveys_batch.append(survey_dict)
                    
                    current_id += 1
                    hh_counter += 1
                
                db.bulk_insert_mappings(Household, households_batch)
                db.bulk_insert_mappings(HouseholdSurvey, surveys_batch)
                db.commit()
                
            print(f"Progress: {hh_counter}/{total_households} households seeded.")

        print("Recalculating dashboard aggregates...")
        ensure_dashboard_aggregates(db)
        
        end_time = time.time()
        print(f"Finished! Total households: {hh_counter}. Time taken: {end_time - start_time:.2f}s")

    except Exception as e:
        print(f"Error seeding: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_bulk_data(500000, 5000)
