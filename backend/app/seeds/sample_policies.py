"""Seed sample policies and reports."""

from datetime import date

from app.constants import PolicyCategory
from app.database import SessionLocal
from app.models import Policy


SAMPLES = [
    {
        "title": "Khung chuẩn nghèo đa chiều 2026-2030",
        "category": PolicyCategory.DECREE,
        "summary": "Cập nhật chuẩn nghèo đa chiều giai đoạn 2026-2030 và hướng dẫn rà soát dữ liệu.",
        "description": "<p>Văn bản quy định khung tiêu chí và mức chuẩn nghèo đa chiều cho giai đoạn 2026-2030.</p><h3>1. Mục tiêu</h3><p>Thống nhất cách xác định chuẩn nghèo đa chiều và làm cơ sở phân bổ nguồn lực.</p><ul><li>Điều chỉnh ngưỡng thu nhập.</li><li>Bổ sung tiêu chí dịch vụ xã hội cơ bản.</li><li>Hướng dẫn quy trình rà soát hằng năm.</li></ul>",
        "effective_date": date(2026, 1, 5),
        "issued_by": "Vụ Giảm nghèo",
        "attachment_url": "",
        "tags": ["chuẩn nghèo", "hướng dẫn", "giai đoạn 2026-2030"],
        "is_public": True,
    },
    {
        "title": "Báo cáo rà soát hộ nghèo cấp huyện 2025",
        "category": PolicyCategory.REPORT,
        "summary": "Tổng hợp kết quả rà soát và đề xuất hỗ trợ bổ sung cho vùng khó khăn.",
        "description": "<p>Báo cáo tổng hợp kết quả rà soát cuối năm và so sánh biến động với năm trước.</p><h3>Nội dung chính</h3><ul><li>Biến động tỷ lệ hộ nghèo theo huyện.</li><li>Nguyên nhân biến động.</li><li>Đề xuất hỗ trợ bổ sung.</li></ul>",
        "effective_date": date(2025, 12, 22),
        "issued_by": "Sở LĐ-TB&XH Quảng Nam",
        "attachment_url": "",
        "tags": ["báo cáo", "rà soát", "2025"],
        "is_public": False,
    },
    {
        "title": "Checklist triển khai hỗ trợ sinh kế",
        "category": PolicyCategory.GUIDELINE,
        "summary": "Danh sách kiểm tra cho các bước triển khai hỗ trợ sinh kế.",
        "description": "<p>Checklist áp dụng cho các đơn vị triển khai hỗ trợ sinh kế hộ nghèo.</p><ul><li>Chuẩn bị dữ liệu hộ.</li><li>Phân nhóm đối tượng.</li><li>Thiết kế can thiệp.</li><li>Giám sát và đánh giá.</li></ul>",
        "effective_date": date(2025, 11, 10),
        "issued_by": "Ban QLDA tỉnh Đồng Tháp",
        "attachment_url": "",
        "tags": ["sinh kế", "checklist", "triển khai"],
        "is_public": True,
    },
    {
        "title": "Bản tin chương trình mục tiêu quốc gia Q4/2025",
        "category": PolicyCategory.GUIDELINE,
        "summary": "Tổng hợp tin nhanh về giải ngân, đào tạo và truyền thông quý IV/2025.",
        "description": "<p>Bản tin tổng hợp tiến độ giải ngân, đào tạo và truyền thông của chương trình mục tiêu quốc gia quý IV/2025.</p><h3>Điểm nổi bật</h3><ul><li>Tỷ lệ giải ngân đạt 92%.</li><li>Đào tạo cán bộ cấp xã tăng 18%.</li><li>Mô hình sinh kế mới tại 6 tỉnh.</li></ul>",
        "effective_date": date(2025, 10, 15),
        "issued_by": "Trung tâm thông tin",
        "attachment_url": "",
        "tags": ["bản tin", "chương trình mục tiêu", "2025"],
        "is_public": True,
    },
    {
        "title": "Thông tư hỗ trợ nhà ở vùng thiên tai",
        "category": PolicyCategory.CIRCULAR,
        "summary": "Hướng dẫn nguồn lực và thủ tục hỗ trợ nhà ở cho hộ nghèo vùng thiên tai.",
        "description": "<p>Thông tư quy định nguồn lực, đối tượng và thủ tục hỗ trợ nhà ở cho hộ nghèo chịu ảnh hưởng thiên tai.</p><h3>Phạm vi</h3><ul><li>Đối tượng thụ hưởng.</li><li>Mức hỗ trợ.</li><li>Thủ tục giải ngân.</li></ul>",
        "effective_date": date(2025, 2, 10),
        "issued_by": "Bộ Xây dựng",
        "attachment_url": "",
        "tags": ["nhà ở", "thiên tai", "thông tư"],
        "is_public": True,
    },
    {
        "title": "Đề án nâng cao năng lực cán bộ giảm nghèo 2026",
        "category": PolicyCategory.DECREE,
        "summary": "Đề án nâng cao năng lực cán bộ tuyến xã, huyện cho năm 2026.",
        "description": "<p>Đề án tập trung vào đào tạo, bồi dưỡng kỹ năng số và quản trị chương trình.</p><ul><li>Đào tạo kỹ năng số.</li><li>Quản lý dữ liệu hộ nghèo.</li><li>Giám sát kết quả.</li></ul>",
        "effective_date": date(2026, 3, 1),
        "issued_by": "Bộ LĐ-TB&XH",
        "attachment_url": "",
        "tags": ["đề án", "đào tạo", "năng lực"],
        "is_public": False,
    },
    {
        "title": "Báo cáo đánh giá mô hình sinh kế 2024-2025",
        "category": PolicyCategory.REPORT,
        "summary": "Đánh giá hiệu quả mô hình sinh kế tại 8 tỉnh giai đoạn 2024-2025.",
        "description": "<p>Báo cáo đánh giá hiệu quả các mô hình sinh kế và đề xuất nhân rộng.</p><h3>Kết quả</h3><ul><li>Tăng thu nhập bình quân 15%.</li><li>Tỷ lệ duy trì mô hình 82%.</li><li>Khuyến nghị mở rộng.</li></ul>",
        "effective_date": date(2025, 9, 30),
        "issued_by": "Văn phòng chương trình",
        "attachment_url": "",
        "tags": ["mô hình", "đánh giá", "sinh kế"],
        "is_public": False,
    },
    {
        "title": "Hướng dẫn cập nhật dữ liệu hộ nghèo 2025",
        "category": PolicyCategory.GUIDELINE,
        "summary": "Quy trình cập nhật dữ liệu hộ nghèo trên hệ thống năm 2025.",
        "description": "<p>Hướng dẫn chuẩn hóa dữ liệu và quy trình cập nhật trên hệ thống.</p><ul><li>Chuẩn hóa thông tin hộ.</li><li>Kiểm tra tính hợp lệ.</li><li>Phê duyệt cập nhật.</li></ul>",
        "effective_date": date(2025, 6, 15),
        "issued_by": "Trung tâm dữ liệu",
        "attachment_url": "",
        "tags": ["dữ liệu", "quy trình", "2025"],
        "is_public": True,
    },
    {
        "title": "Thông tư hướng dẫn hỗ trợ y tế hộ nghèo",
        "category": PolicyCategory.CIRCULAR,
        "summary": "Quy định mức hỗ trợ y tế và thủ tục áp dụng cho hộ nghèo.",
        "description": "<p>Thông tư quy định nguồn lực và thủ tục hỗ trợ y tế cho hộ nghèo.</p><ul><li>Đối tượng áp dụng.</li><li>Mức hỗ trợ.</li><li>Thủ tục thanh toán.</li></ul>",
        "effective_date": date(2025, 4, 20),
        "issued_by": "Bộ Y tế",
        "attachment_url": "",
        "tags": ["y tế", "hộ nghèo", "thông tư"],
        "is_public": True,
    },
    {
        "title": "Báo cáo tổng kết chương trình giảm nghèo 2025",
        "category": PolicyCategory.REPORT,
        "summary": "Tổng kết kết quả thực hiện chương trình giảm nghèo năm 2025.",
        "description": "<p>Báo cáo tổng kết kết quả thực hiện chương trình giảm nghèo năm 2025.</p><h3>Kết quả</h3><ul><li>Tỷ lệ giảm nghèo 1,2%.</li><li>Hỗ trợ sinh kế cho 12.000 hộ.</li><li>Giải ngân đạt 95%.</li></ul>",
        "effective_date": date(2025, 12, 31),
        "issued_by": "Bộ LĐ-TB&XH",
        "attachment_url": "",
        "tags": ["tổng kết", "giảm nghèo", "2025"],
        "is_public": True,
    },
    {
        "title": "Tin tức chương trình giảm nghèo tháng 12/2025",
        "category": PolicyCategory.NEWS,
        "summary": "Cập nhật nhanh hoạt động đào tạo, hỗ trợ sinh kế tại các địa phương.",
        "description": "<p>Bản tin tổng hợp hoạt động nổi bật tháng 12/2025.</p><ul><li>Đào tạo cán bộ cấp xã.</li><li>Mô hình sinh kế hiệu quả.</li><li>Truyền thông cộng đồng.</li></ul>",
        "effective_date": date(2025, 12, 5),
        "issued_by": "Trung tâm thông tin",
        "attachment_url": "",
        "tags": ["tin tức", "tháng 12", "2025"],
        "is_public": True,
    },
    {
        "title": "Thông báo lịch kiểm tra liên ngành quý I/2026",
        "category": PolicyCategory.ANNOUNCEMENT,
        "summary": "Lịch kiểm tra liên ngành về công tác giảm nghèo quý I/2026.",
        "description": "<p>Thông báo lịch kiểm tra liên ngành quý I/2026 tại các tỉnh trọng điểm.</p><ul><li>Thời gian: 10/01 - 25/01/2026.</li><li>Phạm vi: 12 tỉnh miền núi.</li><li>Đơn vị chủ trì: Bộ LĐ-TB&XH.</li></ul>",
        "effective_date": date(2026, 1, 8),
        "issued_by": "Văn phòng Bộ",
        "attachment_url": "",
        "tags": ["thông báo", "lịch kiểm tra", "2026"],
        "is_public": True,
    },
]


def seed_policies() -> None:
    db = SessionLocal()
    try:
        db.query(Policy).delete()
        for item in SAMPLES:
            db.add(Policy(**item))
        db.commit()
        print("Inserted sample policies.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_policies()
