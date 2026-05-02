
import random
from datetime import date, datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import Policy
from app.constants import PolicyCategory

POLICIES_DATA = [
    {
        "title": "Nghị định 07/2021/NĐ-CP quy định chuẩn nghèo đa chiều giai đoạn 2021-2025",
        "category": PolicyCategory.DECREE,
        "summary": "Quy định các tiêu chí đo lường nghèo đa chiều, chuẩn hộ nghèo, hộ cận nghèo áp dụng cho giai đoạn 2021-2025.",
        "description": "Nghị định này quy định các tiêu chí đo lường nghèo đa chiều; chuẩn hộ nghèo, hộ cận nghèo, hộ có mức sống trung bình và quy trình rà soát, phân loại hộ nghèo, hộ cận nghèo hàng năm.",
        "issued_by": "Chính phủ",
        "is_public": True,
        "tags": ["chuẩn nghèo", "2021-2025", "đa chiều"]
    },
    {
        "title": "Thông tư 07/2021/TT-BLĐTBXH hướng dẫn rà soát hộ nghèo, hộ cận nghèo hàng năm",
        "category": PolicyCategory.CIRCULAR,
        "summary": "Hướng dẫn phương pháp rà soát, phân loại hộ nghèo, hộ cận nghèo và xác định hộ làm nông nghiệp, lâm nghiệp có mức sống trung bình.",
        "description": "Thông tư hướng dẫn chi tiết về quy trình rà soát tại cấp xã, phương pháp chấm điểm B1 và B2 để phân loại hộ gia đình.",
        "issued_by": "Bộ Lao động - Thương binh và Xã hội",
        "is_public": True,
        "tags": ["hướng dẫn", "rà soát", "BLĐTBXH"]
    },
    {
        "title": "Báo cáo tổng kết công tác giảm nghèo bền vững năm 2023",
        "category": PolicyCategory.REPORT,
        "summary": "Đánh giá kết quả thực hiện chương trình mục tiêu quốc gia giảm nghèo bền vững trong năm 2023.",
        "description": "Báo cáo nêu rõ tỷ lệ giảm nghèo trên cả nước, các khó khăn vướng mắc và kế hoạch triển khai cho năm 2024.",
        "issued_by": "Văn phòng Quốc gia về Giảm nghèo",
        "is_public": True,
        "tags": ["báo cáo", "tổng kết", "2023"]
    },
    {
        "title": "Hướng dẫn sử dụng phần mềm iPOOR cho cán bộ cấp xã",
        "category": PolicyCategory.GUIDELINE,
        "summary": "Tài liệu hướng dẫn các thao tác nhập liệu, cập nhật thông tin hộ gia đình trên hệ thống iPOOR.",
        "description": "Tài liệu bao gồm các bước từ đăng nhập, tra cứu hộ, nhập phiếu khảo sát đến xuất báo cáo thống kê.",
        "issued_by": "Ban quản lý dự án iPOOR",
        "is_public": True,
        "tags": ["iPOOR", "hướng dẫn", "phần mềm"]
    },
    {
        "title": "Tin tức: Khởi động chương trình hỗ trợ sinh kế cho hộ nghèo vùng sâu vùng xa",
        "category": PolicyCategory.NEWS,
        "summary": "Chương trình cung cấp giống cây trồng, vật nuôi và kỹ thuật canh tác cho 1000 hộ nghèo tại các tỉnh miền núi phía Bắc.",
        "description": "Chương trình có tổng kinh phí 50 tỷ đồng từ nguồn ngân sách nhà nước và đóng góp của các doanh nghiệp.",
        "issued_by": "Ban Thời sự",
        "is_public": True,
        "tags": ["tin tức", "hỗ trợ", "sinh kế"]
    },
    {
        "title": "Thông báo về việc triển khai rà soát hộ nghèo định kỳ năm 2024",
        "category": PolicyCategory.ANNOUNCEMENT,
        "summary": "Yêu cầu các địa phương thực hiện rà soát hộ nghèo, hộ cận nghèo bắt đầu từ ngày 01/09/2024.",
        "description": "Thời gian hoàn thành rà soát và báo cáo kết quả sơ bộ trước ngày 15/11/2024.",
        "issued_by": "Sở Lao động - Thương binh và Xã hội",
        "is_public": True,
        "tags": ["thông báo", "rà soát", "2024"]
    }
]

def seed_policies():
    print("Seeding sample policies and reports...")
    db = SessionLocal()
    try:
        # Clear existing policies (optional, but good for clean seed)
        # db.query(Policy).delete()
        
        for data in POLICIES_DATA:
            policy = Policy(
                title=data["title"],
                category=data["category"],
                summary=data["summary"],
                description=data["description"],
                issued_by=data["issued_by"],
                effective_date=date.today(),
                is_public=data["is_public"],
                tags=data["tags"],
                content_blocks=[
                    {"type": "paragraph", "content": data["description"]},
                    {"type": "heading", "content": "Nội dung chính"},
                    {"type": "list", "items": ["Mục tiêu của chính sách", "Đối tượng áp dụng", "Quy trình thực hiện"]}
                ],
                attachment_files=[
                    {"name": "File_dinh_kem.pdf", "url": "/app/FE/data/FileExcelDataCollection.xlsx"} # Placeholder
                ]
            )
            db.add(policy)
        
        db.commit()
        print(f"Successfully seeded {len(POLICIES_DATA)} policies.")
    except Exception as e:
        print(f"Error seeding policies: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_policies()
