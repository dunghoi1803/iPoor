#!/usr/bin/env python3
"""Train FAQ data into Redis cache for chatbot"""
import sys
sys.path.insert(0, "/app")

import redis
import json
import hashlib
from datetime import datetime

FAQ_QUESTIONS = [
    {
        "q": "tiêu chí nghèo đa chiều là gì",
        "a": """**Tiêu chí nghèo đa chiều** (MITT120) bao gồm 5 tiêu chí:

1. **Thu nhập**: Thu nhập bình quân đầu người/tháng < 700.000 đồng (vùng nông thôn) hoặc < 900.000 đồng (vùng thành thị)
2. **Mức sống**: Chỉ số mức sống tối thiểu (MPI) dưới ngưỡng quy định
3. **Giáo dục**: Không có thành viên 15-24 tuổi hoàn thành THPT
4. **Y tế**: Không có thẻ BHYT hoặc chi phí y tế > 10% thu nhập
5. **Nhà ở**: Diện tích nhà ở < 15m²/người hoặc nhà tạm, dột nát

**Cận nghèo**: Thu nhập 700-1.000.000 đ (nông thôn) hoặc 900-1.300.000 đ (thành thị)."""
    },
    {
        "q": "chính sách giảm nghèo là gì",
        "a": """**Chính sách giảm nghèo** là các biện pháp của Nhà nước nhằm hỗ trợ hộ nghèo, cận nghèo vượt qua khó khăn:

**Chính sách chính:**
- Hỗ trợ tiền mặt (CHUO, bảo hiểm xã hội)
- Hỗ trợ y tế (thẻ BHYT miễn phí)
- Hỗ trợ giáo dục (học bổng, miễn phí học phí)
- Hỗ trợ nhà ở (xây dựng nhà cho hộ nghèo)
- Hỗ trợ tín dụng (vay vốn ưu đãi)
- Hỗ trợ sản xuất (con giống, phân bón, máy móc)

**Đối tượng**: Hộ nghèo, hộ cận nghèo theo chuẩn nghèo đa chiều quốc gia."""
    },
    {
        "q": "thoát nghèo là gì",
        "a": """**Thoát nghèo** là khi hộ đã thoát khỏi danh sách hộ nghèo theo tiêu chí nghèo đa chiều:

**Điều kiện thoát nghèo:**
- Thu nhập bình quân đầu người/tháng vượt ngưỡng nghèo (≥ 700.000đ vùng NT, ≥ 900.000đ vùng TT)
- Đạt đủ 4/5 tiêu chí về mức sống, y tế, giáo dục, nhà ở

**Chu kỳ kiểm tra:** Hàng năm qua khảo sát mục đích tiêu chí (MPI)

**Hỗ trợ sau thoát nghèo:**
- Tiếp tục hưởng một số chính sách trong 2-3 năm
- Được vay vốn tín dụng ưu đãi
- Được tư vấn hỗ trợ sinh kế."""
    },
    {
        "q": "hộ nghèo là gì",
        "a": """**Hộ nghèo** là hộ gia đình có mức sống dưới chuẩn nghèo đa chiều quốc gia:

**Xác định hộ nghèo:**
- Điều tra rà soát hàng năm theo phương pháp điểm chuẩn nghèo đa chiều (MPI)
- Đánh giá 5 tiêu chí: thu nhập, mức sống, y tế, giáo dục, nhà ở
- Hộ nghèo = thu nhập < ngưỡng VÀ đạt dưới 4/5 tiêu chí còn lại

**Thống kê hiện tại (2027):** Cả nước có khoảng 1,3 triệu hộ nghèo (tỷ lệ ~4,5%)."""
    },
    {
        "q": "cận nghèo là gì",
        "a": """**Hộ cận nghèo** (gần nghèo) là hộ có mức sống trên ngưỡng nghèo nhưng chưa đạt chuẩn bền vững:

**Đặc điểm:**
- Thu nhập: 700-1.000.000đ/tháng (nông thôn), 900-1.300.000đ/tháng (thành thị)
- Đạt 4/5 tiêu chí nghèo đa chiều hoặc thu nhập cao hơn ngưỡng nghèo nhưng các tiêu chí khác chưa bền vững

**Chính sách hỗ trợ:**
- Được vay v��n tín dụng ưu đãi
- Hỗ trợ y tế, giáo dục
- Hỗ trợ sinh kế, đào tạo nghề

**Thống kê hiện tại (2027):** Cả nước có khoảng 450.000 hộ cận nghèo."""
    },
    {
        "q": "tại sao phải giảm nghèo",
        "a": """**Giảm nghèo** vì:

1. **Nhân đạo**: Không ai phải sống trong thiếu thốn, đói kém
2. **Phát triển bền vững**: Nghèo đói là rào cản kinh tế - xã hội
3. **Bình đẳng xã hội**: Mọi người đều có cơ hội phát triển
4. **An ninh quốc gia**: Giảm nghèo giúp ổn định xã hội
5. **Cam kết quốc tế**: VN thực hiện Mục tiêu phát triển bền vững (SDGs)

**Mục tiêu đến 2030:** Không còn hộ nghèo theo chuẩn nghèo đa chiều (trừ hộ nghèo thuộc vùng đặc biệt khó khăn)."""
    },
    {
        "q": "cách xóa đói giảm nghèo",
        "a": """**Giải pháp xóa đói giảm nghèo:**

1. **Hỗ trợ thu nhập:**
   - Tạo việc làm, đào tạo nghề
   - Phát triển kinh tế hộ, kinh tế tập thể
   - Chuyển đổi cơ cấu cây trồng, vật nuôi

2. **Phát triển cơ sở hạ tầng:**
   - Giao thông, thủy lợi
   - Trường học, trạm y tế
   - Cấp điện, nước sạch

3. **Nâng cao chất lượng cuộc sống:**
   - Phát triển giáo dục, y tế
   - Bảo hiểm xã hội, y tế
   - Văn hóa, thông tin

4. ** Huy động nguồn lực:**
   - Ngân sách nhà nước
   - Doanh nghiệp, tổ chức xã hội
   - Hỗ trợ quốc tế"""
    },
    {
        "q": "điểm chuẩn nghèo đa chiều",
        "a": """**Điểm chuẩn nghèo đa chiều (MPI - Multidimensional Poverty Index):**

**5 tiêu chí & ngưỡng:**

| Tiêu chí | Nông thôn | Thành thị |
|---------|----------|-----------|
| Thu nhập | < 700.000đ/người/tháng | < 900.000đ/người/tháng |
| Mức sống | MPI < 0.03 | MPI < 0.02 |
| Giáo dục | Không có THPT 15-24t | Không có THPT 15-24t |
| Y tế | Không có BHYT | Không có BHYT |
| Nhà ở | < 15m²/người, tạm | < 15m²/người, tạm |

**Hộ nghèo**: Đạt dưới 4/5 tiêu chí còn lại (hoặc thu nhập < ngưỡng)"""
    },
    {
        "q": "chương trình mục tiêu quốc gia giảm nghèo bền vững",
        "a": """**Chương trình mục tiêu quốc gia giảm nghèo bền vững giai đoạn 2021-2025:**

**Mục tiêu:**
- Giảm tỷ lệ hộ nghèo xuống dưới 3% vào năm 2025
- Cập nhật danh sách hộ nghèo, cận nghèo chính xác
- Hỗ trợ đa chiều cho hộ nghèo

**Nội dung chính:**
1. Rà soát, đánh giá hộ nghèo hàng năm
2. Hỗ trợ tín dụng, tạo việc làm
3. Hỗ trợ giáo dục, y tế
4. Hỗ trợ nhà ở cho hộ nghèo
5. Phát triển hạ tầng vùng đặc biệt khó khăn

**Nguồn kinh phí:** Ngân sách TW + địa phương + huy động xã hội"""
    },
    {
        "q": "hỗ trợ hộ nghèo",
        "a": """**Các chính sách hỗ trợ hộ nghèo:**

1. **Tiền mặt:**
   - Chương trình hỗ trợ hộ thoát nghèo (CHUO)
   - Bảo hiểm xã hội tự nguyện
   - Trợ cấp xã hội định kỳ

2. **Y tế:**
   - Thẻ BHYT miễn phí
   - Miễn chi phí khám chữa bệnh
   - Hỗ trợ chi phí đi lại

3. **Giáo dục:**
   - Miễn học phí
   - Học bổng, sách vở, đồng phục
   - Hỗ trợ sinh viên nghèo

4. **Nhà ở:**
   - Hỗ trợ xây/sửa nhà
   - Chương trình nhà ở xã hội

5. **Tín dụng:**
   - Vay vốn ưu đãi
   - Không cần thế chấp"""
    },
    {
        "q": "khảo sát mục đích tiêu chí nghèo",
        "a": """**Khảo sát mục đích tiêu chí nghèo (MPI Survey):**

**Mục đích:**
- Đánh giá mức sống của hộ gia đình
- Xác định hộ nghề, cận nghèo
- Theo dõi tình trạng nghèo đa chiều
- Làm cơ sở cho chính sách hỗ trợ

**Nội dung khảo sát:**
1. Thông tin hộ: thành viên, thu nhập
2. Tiêu chí thu nhập: thu nhập bình quân
3. Tiêu chí mức sống: chi tiêu, tài sản
4. Tiêu chí y tế: BHYT, bệnh tật
5. Tiêu chí giáo dục: trình độ học vấn
6. Tiêu chí nhà ở: diện tích, chất lượng

**Tần suất:** Hàng năm (thường quý 4)"""
    },
    {
        "q": "quy trình rà soát hộ nghèo",
        "a": """**Quy trình rà soát hộ nghèo:**

1. **Chuẩn bị:**
   - Lập danh sách hộ cần rà soát
   - Tập huấn điều tra viên
   - Chuẩn bị phiếu điều tra

2. **Thu thập thông tin:**
   - Điều tra viên đến hộ
   - Thu thập 5 tiêu chí MPI
   - Ghi phiếu điều tra

3. **Tính điểm:**
   - Tính điểm thiếu hụt mỗi tiêu chí
   - Xác định hộ nghèo (điểm > ngưỡng)

4. **Xét duyệt:**
   - Họp thôn/xóm xét duyệt
   - Công khai danh sách
   - Tiếp nhận phản ánh

5. **Phê duyệt:**
   - UBND cấp xã phê duyệt
   - Niêm yết công khai
   - Nhập danh sách vào CSDL"""
    },
    {
        "q": "vay vốn giảm nghèo",
        "a": """**Vay vốn tín dụng ưu đãi cho hộ nghèo, cận nghèo:**

1. **Ngân hàng Chính sách xã hội (NHCSX):**
   - Cho vay theo các chương trình
   - Lãi suất ưu đãi (thấp hơn thị trường)
   - Không cần thế chấp tài sản
   - Hạn mức theo mục đích

2. **Các chương trình vay:**
   - Vay hộ nghèo, cận nghèo
   - Vay sinh viên nghèo
   - Vay nhà ở xã hội
   - Vay chăn nuôi, trồng trọt
   - Vay giải quyết việc làm

3. **Điều kiện:**
   - Thuộc diện hộ nghèo, cận nghèo
   - Có phương án sản xuất, kinh doanh
   - Tham gia bảo hiểm (một số chương trình)"""
    },
    {
        "q": "danh sách hộ nghèo",
        "a": """**Danh sách hộ nghèo:**

- Được lưu trữ tại **CSDL tập trung** của hệ thống iPOOR
- Cập nhật hàng năm sau khảo sát MPI
- Truy cập qua API `/households` với phân quyền
- Các trường: mã hộ, thông tin thành viên, địa bàn, trạng thái nghèo, năm khảo sát

**Tra cứu:**
- Qua dashboard theo địa bàn (tỉnh/huyện/xã)
- Qua chatbot hỏi: "Hà Nội có bao nhiêu hộ nghèo?"
- Qua API trực tiếp (cần đăng nhập)

**Lưu Ý:** Danh sách thay đổi theo năm khảo sát. Dữ liệu mới nhất 2027."""
    },
    {
        "q": "tỷ lệ nghèo việt nam",
        "a": """**Tỷ lệ nghèo tại Việt Nam (2027):**

| Khu vực | Tỷ lệ nghèo |
|---------|-------------|
| Cả nước | ~4,5% |
| Thành thị | ~1,5% |
| Nông thôn | ~6,8% |

**Theo vùng:**
- Đồng bằng sông Hồng: ~2,1%
- Đồng bằng sông Cửu Long: ~5,2%
- Tây Nguyên: ~8,5%
- Trung du & miền núi Bắc Bộ: ~10,2%

**Giảm nghèo:**
- 2010: 14,2%
- 2015: 7,8%
- 2020: 6,7%
- 2025: 5,2%
- 2027: ~4,5%

**Mục tiêu 2030:** < 3% (trừ vùng đặc biệt khó khăn)"""
    },
    {
        "q": "Ủy ban nhân dân cấp xã",
        "a": """**Ủy ban nhân dân (UBND) cấp xã** là cơ quan hành chính nhà nước ở cấp xã:

**Chức năng:**
- Quản lý hành chính tại địa phương
- Tổ chức thực thi pháp luật
- Thực hiện các nhiệm vụ kinh tế - xã hội

**Trong công tác giảm nghèo:**
- Rà soát hộ nghèo, cận nghèo
- Lập danh sách hộ nghèo
- Phối hợp hỗ trợ hộ nghèo
- Giám sát việc thực hiện chính sách

**Cơ cấu:**
- Chủ tịch UBND
- Phó Chủ tịch
- Các thành viên (CT phường, thủ trưởng các ban, ngành)"""
    },
    {
        "q": "huyện là gì",
        "a": """**Huyện** là đơn vị hành chính cấp quận/huyện/thị xã:

**Vị trí:**
- Cấp trên xã/phường/thị trấn
- Cấp dưới tỉnh/thành phố

**Trong iPOOR:**
- Đơn vị phân quyền: district_officer
- Lọc dữ liệu theo huyện
- Thống kê dashboard theo huyện
- Quản lý hộ nghèo theo địa bàn

**Tổ chức:**
- UBND huyện
- Các cơ quan chuyên môn
- Các đơn vị sự nghiệp"""
    },
    {
        "q": "xã là gì",
        "a": """**Xã** là đơn vị hành chính cấp cơ sở:

**Các loại xã:**
- Xã nông thôn
- Phường (khu vực thành thị)
- Thị trấn (trung tâm huyện)

**Trong iPOOR:**
- Cấp thấp nhất trong phân quyền
- Trực tiếp quản lý hộ nghèo
- commune_officer có quyền tại đây
- Cập nhật thông tin hộ

**Đặc điểm:**
- Gần với người dân nhất
- Nơi rà soát hộ nghèo
- Cung cấp dữ liệu ban đầu"""
    },
    {
        "q": "tỉnh là gì",
        "a": """**Tỉnh** là đơn vị hành chính cấp cao nhất trong iPOOR:

**Các tỉnh/thành phố:**
- 63 tỉnh/thành phố trực thuộc TW
- Bao gồm TP Hà Nội, TP Hồ Chí Minh

**Trong iPOOR:**
- Đơn vị phân quyền cao nhất: province_officer
- Lọc dashboard theo tỉnh
- Tra cứu số liệu: "Hà Nội có bao nhiêu hộ nghèo?"
- Quản lý toàn bộ địa bàn tỉnh

**Cơ cấu:**
- UBND tỉnh/thành phố
- Sở LĐ-TB&XH (quản lý giảm nghèo)
- Các sở, ban ngành khác"""
    },
    {
        "q": "ai là người dùng iPOOR",
        "a": """**Người dùng iPOOR:**

1. **Quản lý nhà nước:**
   - Cán bộ xã/phường (commune_officer)
   - Cán bộ huyện (district_officer)
   - Cán bộ tỉnh (province_officer)
   - Quản trị hệ thống (admin)

2. **Mục đích:**
   - Quản lý danh sách hộ nghèo
   - Thống kê, báo cáo
   - Quản lý chính sách
   - Theo dõi tiến độ giảm nghèo

3. **Quyền truy cập:**
   - Theo cấp hành chính
   - Admin: toàn bộ hệ thống
   - Province: toàn tỉnh
   - District: toàn huyện
   - Commune: chỉ xã"""
    },
]


def normalize_for_cache(msg: str) -> str:
    return msg.lower().strip()


def get_faq_key(message: str) -> str:
    normalized = normalize_for_cache(message)
    hash_key = hashlib.md5(normalized.encode()).hexdigest()[:16]
    return f"chatbot:faq:v1:q:{hash_key}"


def main():
    from app.config import get_settings
    settings = get_settings()
    
    redis_cli = None
    if settings.redis_host and settings.redis_port and settings.redis_password:
        try:
            redis_cli = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            redis_cli.ping()
            print("Redis connected")
        except Exception as e:
            print(f"✗ Redis connection failed: {e}")
            return
    else:
        print("✗ Redis not configured")
        return
    
    print(f"\nTraining {len(FAQ_QUESTIONS)} FAQ entries...")
    
    count = 0
    for faq in FAQ_QUESTIONS:
        key = get_faq_key(faq["q"])
        redis_cli.setex(key, 86400 * 30, faq["a"])  # 30 days
        count += 1
        
        # Also store an index for variations
        index_key = f"chatbot:faq:v1:index:{normalize_for_cache(faq['q'])[:50]}"
        redis_cli.setex(index_key, 86400 * 30, key)  # Point to main key
    
    # Store metadata
    meta = {
        "version": "v1",
        "count": count,
        "trained_at": datetime.now().isoformat(),
    }
    redis_cli.setex("chatbot:faq:v1:meta", 86400 * 30, json.dumps(meta))
    
    print(f"✓ Trained {count} FAQ entries")
    
    keys = redis_cli.dbsize()
    print(f"  Total Redis keys: {keys}")
    
    # Verify cache
    test_key, test_val = get_faq_key("tiêu chí nghèo đa chiều là gì"), None
    val = redis_cli.get(test_key)
    if val:
        print(f"✓ Cache verification passed (first 80 chars): {val[:80]}...")
    else:
        print("✗ Cache verification failed")


if __name__ == "__main__":
    main()