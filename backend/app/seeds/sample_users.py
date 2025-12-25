"""Seed sample users into the database."""

from app.database import SessionLocal
from app.models import User
from app.utils.security import get_password_hash
from app.constants import Roles


SAMPLES = [
    {
        "email": "admin@ipoor.local",
        "full_name": "Nguyễn Việt Hùng",
        "role": Roles.ADMIN,
        "org_level": "tw",
        "org_name": "Bộ Lao động - Thương binh và Xã hội",
        "position": "Quản trị hệ thống",
        "cccd": "011234567890",
        "province": "Hà Nội",
        "district": "Ba Đình",
        "commune": "Phường Ngọc Hà",
    },
    {
        "email": "canbo.tinh@ipoor.local",
        "full_name": "Trần Thị Thanh",
        "role": Roles.PROVINCE_OFFICER,
        "org_level": "tinh",
        "org_name": "Sở LĐ-TB&XH Quảng Nam",
        "position": "Cán bộ tỉnh",
        "cccd": "022345678901",
        "province": "Quảng Nam",
        "district": "Tam Kỳ",
        "commune": "Phường An Mỹ",
    },
    {
        "email": "canbo.huyen@ipoor.local",
        "full_name": "Lê Văn Khôi",
        "role": Roles.DISTRICT_OFFICER,
        "org_level": "huyen",
        "org_name": "UBND huyện Quỳnh Lưu",
        "position": "Cán bộ huyện",
        "cccd": "033456789012",
        "province": "Nghệ An",
        "district": "Quỳnh Lưu",
        "commune": "Xã Quỳnh Hồng",
    },
    {
        "email": "canbo.xa@ipoor.local",
        "full_name": "Hoàng Thị Dung",
        "role": Roles.COMMUNE_OFFICER,
        "org_level": "xa",
        "org_name": "UBND xã Nghĩa Phương",
        "position": "Cán bộ xã",
        "cccd": "044567890123",
        "province": "Quảng Ngãi",
        "district": "Tư Nghĩa",
        "commune": "Xã Nghĩa Phương",
    },
]


def seed_users(password: str = "18032002") -> None:
    db = SessionLocal()
    try:
        db.query(User).delete()
        hashed_password = get_password_hash(password)
        for item in SAMPLES:
            db.add(User(**item, hashed_password=hashed_password))
        db.commit()
        print("Inserted sample users.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_users()
