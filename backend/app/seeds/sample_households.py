"""Seed sample households and historical surveys with dynamic status calculation."""

import random
from datetime import date, timedelta

from app.constants import PovertyStatus, Roles, PolicyCategory
from sqlalchemy import text
from app.database import SessionLocal, engine, Base
from app.models import Household, HouseholdSurvey, PovertyThreshold, ActivityLog, DataCollection, User, Policy
from app.utils.security import get_password_hash


def get_poverty_status(area_type: str, b1: int, b2: int, threshold_b1: int) -> PovertyStatus:
    """Calculate poverty status based on B1, B2 and area standards."""
    if b1 <= threshold_b1:
        if b2 >= 30:
            return PovertyStatus.POOR
        else:
            return PovertyStatus.NEAR_POOR
    else:
        # If above income threshold, then escaped
        return PovertyStatus.ESCAPED


LOCATIONS = [
    ("TP. Hà Nội", "Ba Đình", "Phường Ngọc Hà", "Thành thị"),
    ("TP. Hải Phòng", "Lê Chân", "Phường An Biên", "Thành thị"),
    ("TP. Đà Nẵng", "Hải Châu", "Phường Thạch Thang", "Thành thị"),
    ("Nghệ An", "Quỳnh Lưu", "Xã Quỳnh Hồng", "Nông thôn"),
    ("Lâm Đồng", "Di Linh", "Xã Đinh Lạc", "Nông thôn"),
    ("TP. Hồ Chí Minh", "Bình Thạnh", "Phường 14", "Thành thị"),
    ("TP. Cần Thơ", "Ninh Kiều", "Phường An Khánh", "Thành thị"),
    ("Thanh Hóa", "Triệu Sơn", "Xã Dân Lý", "Nông thôn"),
    ("Quảng Nam", "Thăng Bình", "Xã Bình Dương", "Nông thôn"),
    ("Khánh Hòa", "Nha Trang", "Phường Vĩnh Hòa", "Thành thị"),
    ("Bắc Ninh", "Yên Phong", "Xã Đông Phong", "Nông thôn"),
    ("Đắk Lắk", "Buôn Ma Thuột", "Phường Tân An", "Thành thị"),
    ("Lào Cai", "Sa Pa", "Xã Tả Van", "Nông thôn"),
    ("Quảng Ngãi", "Tư Nghĩa", "Xã Nghĩa Phương", "Nông thôn"),
    ("Phú Thọ", "Việt Trì", "Phường Vân Cơ", "Thành thị"),
    ("An Giang", "Châu Phú", "Xã Bình Mỹ", "Nông thôn"),
    ("Đồng Nai", "Biên Hòa", "Phường Tân Biên", "Thành thị"),
    ("Ninh Bình", "Hoa Lư", "Xã Ninh Vân", "Nông thôn"),
    ("Quảng Trị", "Cam Lộ", "Xã Cam Tuyền", "Nông thôn"),
    ("Bình Định", "Phù Cát", "Xã Cát Hanh", "Nông thôn"),
]

OFFICERS = [
    "Nguyễn Văn An", "Trần Thị Bình", "Lê Văn Cường", "Phạm Thị Dung", 
    "Hoàng Văn Em", "Ngô Thị Phương", "Đỗ Văn Giang", "Bùi Thị Hạnh"
]

SURNAMES = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Phan", "Vũ", "Đặng", "Bùi", "Đỗ"]
MIDDLE_NAMES = ["Văn", "Thị", "Hữu", "Minh", "Đức", "Ngọc", "Hoàng", "Kim"]
FIRST_NAMES = ["Hùng", "Lan", "Tuấn", "Mai", "Cường", "Hoa", "Dũng", "Huệ", "Sơn", "Linh"]


def generate_name():
    return f"{random.choice(SURNAMES)} {random.choice(MIDDLE_NAMES)} {random.choice(FIRST_NAMES)}"


def seed_households() -> None:
    # Ensure all tables defined in models exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Clear existing data with FK checks disabled for a clean sweep
        db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        db.execute(text("TRUNCATE TABLE activity_logs;"))
        db.execute(text("TRUNCATE TABLE data_collections;"))
        db.execute(text("TRUNCATE TABLE household_surveys;"))
        db.execute(text("TRUNCATE TABLE households;"))
        db.execute(text("TRUNCATE TABLE poverty_thresholds;"))
        db.execute(text("TRUNCATE TABLE policies;"))
        db.execute(text("TRUNCATE TABLE policy_drafts;"))
        db.execute(text("TRUNCATE TABLE users;"))
        db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        db.commit()

        # 2. Seed Users
        hashed_pwd = get_password_hash("18032002")
        users_data = [
            User(email="admin@ipoor.local", full_name="Nguyễn Việt Hùng", hashed_password=hashed_pwd, role=Roles.ADMIN, org_level="tw", org_name="Bộ Lao động - Thương binh và Xã hội", position="Quản trị hệ thống", cccd="011234567890", province="Hà Nội", district="Ba Đình", commune="Phường Ngọc Hà"),
            User(email="canbo.tinh@ipoor.local", full_name="Trần Thị Thanh", hashed_password=hashed_pwd, role=Roles.PROVINCE_OFFICER, org_level="tinh", org_name="Sở LĐ-TB&XH Quảng Nam", position="Cán bộ tỉnh", cccd="022345678901", province="Quảng Nam", district="Tam Kỳ", commune="Phường An Mỹ"),
            User(email="canbo.huyen@ipoor.local", full_name="Lê Văn Khôi", hashed_password=hashed_pwd, role=Roles.DISTRICT_OFFICER, org_level="huyen", org_name="UBND huyện Quỳnh Lưu", position="Cán bộ huyện", cccd="033456789012", province="Nghệ An", district="Quỳnh Lưu", commune="Xã Quỳnh Hồng"),
            User(email="canbo.xa@ipoor.local", full_name="Hoàng Thị Dung", hashed_password=hashed_pwd, role=Roles.COMMUNE_OFFICER, org_level="xa", org_name="UBND xã Nghĩa Phương", position="Cán bộ xã", cccd="044567890123", province="Quảng Ngãi", district="Tư Nghĩa", commune="Xã Nghĩa Phương"),
        ]
        for u in users_data:
            db.add(u)
        db.flush()

        # 3. Seed Policies
        policies_data = [
            Policy(title="Khung chuẩn nghèo đa chiều 2026-2030", category=PolicyCategory.DECREE, summary="Cập nhật chuẩn nghèo đa chiều giai đoạn 2026-2030 và hướng dẫn rà soát dữ liệu.", description="<p>Văn bản quy định khung tiêu chí và mức chuẩn nghèo đa chiều cho giai đoạn 2026-2030.</p><h3>1. Mục tiêu</h3><p>Thống nhất cách xác định chuẩn nghèo đa chiều và làm cơ sở phân bổ nguồn lực.</p><ul><li>Điều chỉnh ngưỡng thu nhập.</li><li>Bổ sung tiêu chí dịch vụ xã hội cơ bản.</li><li>Hướng dẫn quy trình rà soát hằng năm.</li></ul>", effective_date=date(2026, 1, 5), issued_by="Vụ Giảm nghèo", tags=["chuẩn nghèo", "hướng dẫn", "giai đoạn 2026-2030"], is_public=True),
            Policy(title="Báo cáo rà soát hộ nghèo cấp huyện 2025", category=PolicyCategory.REPORT, summary="Tổng hợp kết quả rà soát và đề xuất hỗ trợ bổ sung cho vùng khó khăn.", description="<p>Báo cáo tổng hợp kết quả rà soát cuối năm và so sánh biến động với năm trước.</p><h3>Nội dung chính</h3><ul><li>Biến động tỷ lệ hộ nghèo theo huyện.</li><li>Nguyên nhân biến động.</li><li>Đề xuất hỗ trợ bổ sung.</li></ul>", effective_date=date(2025, 12, 22), issued_by="Sở LĐ-TB&XH Quảng Nam", tags=["báo cáo", "rà soát", "2025"], is_public=False),
            Policy(title="Checklist triển khai hỗ trợ sinh kế", category=PolicyCategory.GUIDELINE, summary="Danh sách kiểm tra cho các bước triển khai hỗ trợ sinh kế.", description="<p>Checklist áp dụng cho các đơn vị triển khai hỗ trợ sinh kế hộ nghèo.</p><ul><li>Chuẩn bị dữ liệu hộ.</li><li>Phân nhóm đối tượng.</li><li>Thiết kế can thiệp.</li><li>Giám sát và đánh giá.</li></ul>", effective_date=date(2025, 11, 10), issued_by="Ban QLDA tỉnh Đồng Tháp", tags=["sinh kế", "checklist", "triển khai"], is_public=True),
        ]
        for p in policies_data:
            db.add(p)
        db.flush()

        # 4. Seed Standards (Poverty Thresholds)
        thresholds_data = [
            # Nông thôn: B1 <= 150
            PovertyThreshold(year=2024, area_type="Nông thôn", b1_threshold=150, b2_deprived_min=30),
            PovertyThreshold(year=2025, area_type="Nông thôn", b1_threshold=155, b2_deprived_min=30),
            PovertyThreshold(year=2026, area_type="Nông thôn", b1_threshold=160, b2_deprived_min=30),
            # Thành thị: B1 <= 175
            PovertyThreshold(year=2024, area_type="Thành thị", b1_threshold=175, b2_deprived_min=30),
            PovertyThreshold(year=2025, area_type="Thành thị", b1_threshold=180, b2_deprived_min=30),
            PovertyThreshold(year=2026, area_type="Thành thị", b1_threshold=185, b2_deprived_min=30),
        ]
        for t in thresholds_data:
            db.add(t)
        db.flush()

        # Mapping for lookup
        standards = {}
        for t in thresholds_data:
            standards[(t.year, t.area_type)] = t.b1_threshold

        # 3. Generate 50 sample households
        for i in range(1, 51):
            province, district, commune, area_type = random.choice(LOCATIONS)
            
            household = Household(
                household_code=f"HH-{i:04d}",
                head_name=generate_name(),
                birth_date=date(random.randint(1960, 1995), random.randint(1, 12), random.randint(1, 28)),
                gender=random.choice(["Nam", "Nữ"]),
                id_card=f"0{random.randint(10000000000, 99999999999)}",
                province=province,
                district=district,
                commune=commune,
                ethnicity="Kinh",
                area=area_type,
                village=f"Tổ {random.randint(1, 15)}"
            )
            db.add(household)
            db.flush()

            # 4. Generate surveys for 2024, 2025, 2026
            for year in [2024, 2025, 2026]:
                # Trend: slightly improving scores/income over years
                b1 = random.randint(80, 220) + (year - 2024) * 10
                b2 = random.randint(10, 60) - (year - 2024) * 5
                
                threshold_b1 = standards.get((year, area_type), 150)
                status = get_poverty_status(area_type, b1, b2, threshold_b1)
                
                survey = HouseholdSurvey(
                    household_id=household.id,
                    survey_year=year,
                    survey_date=date(year, random.randint(1, 12), random.randint(1, 28)),
                    poverty_status=status,
                    members_count=random.randint(2, 7),
                    income_per_capita=b1 * 10000, # Mock income scale
                    score_b1=b1,
                    score_b2=max(0, b2),
                    note=f"Khảo sát định kỳ năm {year}",
                    officer=random.choice(OFFICERS),
                    remark="Dữ liệu đã rà soát" if random.random() > 0.2 else "Cần kiểm tra lại"
                )
                db.add(survey)

        db.commit()
        print("Successfully seeded 50 households with historical surveys (2024-2026).")
    except Exception as e:
        print(f"Error seeding: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_households()
