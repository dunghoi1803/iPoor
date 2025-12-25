-- MySQL dump 10.13  Distrib 8.0.44, for Linux (x86_64)
--
-- Host: 127.0.0.1    Database: iPoor
-- ------------------------------------------------------
-- Server version	8.0.44

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `activity_logs`
--

DROP TABLE IF EXISTS `activity_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `activity_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `household_id` int DEFAULT NULL,
  `action` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `entity_type` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `entity_id` int DEFAULT NULL,
  `detail` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL,
  `ip_address` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `household_id` (`household_id`),
  CONSTRAINT `activity_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `activity_logs_ibfk_2` FOREIGN KEY (`household_id`) REFERENCES `households` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `activity_logs`
--

LOCK TABLES `activity_logs` WRITE;
/*!40000 ALTER TABLE `activity_logs` DISABLE KEYS */;
INSERT INTO `activity_logs` VALUES (1,2,1,'create_household','household',1,'Seeded activity','2025-12-24 08:24:38','127.0.0.1'),(2,2,2,'update_household','household',2,'Seeded activity','2025-12-23 08:24:38','10.20.30.40'),(3,2,3,'delete_household','household',3,'Seeded activity','2025-12-22 08:24:38','127.0.0.1'),(4,3,NULL,'create_policy','policy',4,'Seeded activity','2025-12-24 08:24:38','10.20.30.40'),(5,3,NULL,'update_policy','policy',5,'Seeded activity','2025-12-23 08:24:38','127.0.0.1'),(6,3,NULL,'upload_policy_attachment','policy',6,'Seeded activity','2025-12-23 08:24:38','10.20.30.40'),(7,4,7,'create_household','household',7,'Seeded activity','2025-12-21 08:24:38','127.0.0.1'),(8,4,8,'view_household','household',8,'Seeded activity','2025-12-21 08:24:38','10.20.30.40'),(9,4,9,'update_household','household',9,'Seeded activity','2025-12-20 08:24:38','127.0.0.1'),(10,5,10,'update_household','household',10,'Seeded activity','2025-12-19 08:24:38','10.20.30.40'),(11,5,11,'view_household','household',11,'Seeded activity','2025-12-19 08:24:38','127.0.0.1'),(12,2,NULL,'update_policy','policy',12,'Seeded activity','2025-12-21 08:24:38','10.20.30.40'),(13,2,NULL,'delete_policy','policy',12,'Seeded activity','2025-12-20 08:24:38','127.0.0.1'),(14,3,NULL,'create_policy','policy',12,'Seeded activity','2025-12-19 08:24:38','10.20.30.40'),(15,3,NULL,'upload_policy_attachment','policy',12,'Seeded activity','2025-12-18 08:24:38','127.0.0.1'),(16,4,16,'create_household','household',16,'Seeded activity','2025-12-18 08:24:38','10.20.30.40'),(17,4,17,'update_household','household',17,'Seeded activity','2025-12-17 08:24:38','127.0.0.1'),(18,5,18,'create_household','household',18,'Seeded activity','2025-12-16 08:24:38','10.20.30.40'),(19,5,19,'view_household','household',19,'Seeded activity','2025-12-16 08:24:38','127.0.0.1'),(20,2,NULL,'update_policy','policy',12,'Seeded activity','2025-12-15 08:24:38','10.20.30.40');
/*!40000 ALTER TABLE `activity_logs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `alembic_version`
--

DROP TABLE IF EXISTS `alembic_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alembic_version`
--

LOCK TABLES `alembic_version` WRITE;
/*!40000 ALTER TABLE `alembic_version` DISABLE KEYS */;
INSERT INTO `alembic_version` VALUES ('20251225_1024');
/*!40000 ALTER TABLE `alembic_version` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `data_collections`
--

DROP TABLE IF EXISTS `data_collections`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `data_collections` (
  `id` int NOT NULL AUTO_INCREMENT,
  `household_id` int NOT NULL,
  `collector_id` int DEFAULT NULL,
  `status` enum('DRAFT','IN_PROGRESS','VERIFIED','SUBMITTED') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'DRAFT',
  `notes` text COLLATE utf8mb4_unicode_ci,
  `collected_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `household_id` (`household_id`),
  KEY `collector_id` (`collector_id`),
  CONSTRAINT `data_collections_ibfk_1` FOREIGN KEY (`household_id`) REFERENCES `households` (`id`),
  CONSTRAINT `data_collections_ibfk_2` FOREIGN KEY (`collector_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `data_collections`
--

LOCK TABLES `data_collections` WRITE;
/*!40000 ALTER TABLE `data_collections` DISABLE KEYS */;
/*!40000 ALTER TABLE `data_collections` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `households`
--

DROP TABLE IF EXISTS `households`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `households` (
  `id` int NOT NULL AUTO_INCREMENT,
  `household_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `head_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `address_line` text COLLATE utf8mb4_unicode_ci,
  `province` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `district` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `commune` varchar(120) COLLATE utf8mb4_unicode_ci NOT NULL,
  `poverty_status` enum('POOR','NEAR_POOR','ESCAPED','AT_RISK') COLLATE utf8mb4_unicode_ci NOT NULL,
  `ethnicity` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `members_count` int DEFAULT NULL,
  `income_per_capita` float DEFAULT NULL,
  `last_surveyed_at` date DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  `birth_date` date DEFAULT NULL,
  `gender` varchar(16) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_card` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `score_b1` int DEFAULT NULL,
  `score_b2` int DEFAULT NULL,
  `note` text COLLATE utf8mb4_unicode_ci,
  `area` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `village` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `officer` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remark` text COLLATE utf8mb4_unicode_ci,
  `attachment_url` varchar(1024) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `household_code` (`household_code`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `households`
--

LOCK TABLES `households` WRITE;
/*!40000 ALTER TABLE `households` DISABLE KEYS */;
INSERT INTO `households` VALUES (1,'HH-0001','Nguyễn Thị Hoa',NULL,'TP. Hà Nội','Ba Đình','Phường Ngọc Hà','POOR','Kinh',4,1200000,'2024-12-01','2025-12-25 08:24:38','2025-12-25 08:24:38','1985-03-12','Nữ','031234567890',68,74,'Thiếu điều kiện tiếp cận giáo dục và y tế.','Thành thị','Tổ 5','Trần Văn Minh','Đã khảo sát thực địa.',''),(2,'HH-0002','Phạm Văn Long',NULL,'TP. Hải Phòng','Lê Chân','Phường An Biên','NEAR_POOR','Kinh',5,1500000,'2024-11-15','2025-12-25 08:24:38','2025-12-25 08:24:38','1979-07-24','Nam','038765432109',55,61,'Thu nhập sát chuẩn, thiếu việc làm ổn định.','Thành thị','Tổ 9','Nguyễn Thị Ngọc','Cần hỗ trợ vay vốn.',''),(3,'HH-0003','Lê Văn Nam',NULL,'TP. Đà Nẵng','Hải Châu','Phường Thạch Thang','AT_RISK','Kinh',3,1800000,'2024-10-20','2025-12-25 08:24:38','2025-12-25 08:24:38','1990-05-02','Nam','012345678901',42,49,'Nguy cơ tái nghèo do việc làm không ổn định.','Thành thị','Khu phố 2','Lê Thị Hạnh','Theo dõi biến động thu nhập.',''),(4,'HH-0004','Hoàng Thị Lan',NULL,'Nghệ An','Quỳnh Lưu','Xã Quỳnh Hồng','POOR','Thái',6,900000,'2024-09-30','2025-12-25 08:24:38','2025-12-25 08:24:38','1982-09-19','Nữ','024681357913',77,80,'Thiếu đất sản xuất, nhiều người phụ thuộc.','Nông thôn','Xóm 7','Phan Văn Dũng','Ưu tiên hỗ trợ sinh kế.',''),(5,'HH-0005','Trần Văn Minh',NULL,'Lâm Đồng','Di Linh','Xã Đinh Lạc','ESCAPED','K\'Ho',4,2300000,'2024-08-25','2025-12-25 08:24:38','2025-12-25 08:24:38','1975-01-08','Nam','099887766554',35,40,'Đã thoát nghèo, cần theo dõi ổn định.','Nông thôn','Thôn 3','Võ Thị Liên','Theo dõi định kỳ.',''),(6,'HH-0006','Đặng Văn Khánh',NULL,'TP. Hồ Chí Minh','Bình Thạnh','Phường 14','NEAR_POOR','Kinh',3,1700000,'2024-12-12','2025-12-25 08:24:38','2025-12-25 08:24:38','1988-02-14','Nam','078901234567',50,58,'Việc làm thời vụ, thu nhập không ổn định.','Thành thị','Khu phố 6','Phạm Thị Mai','Khuyến nghị hỗ trợ nghề.',''),(7,'HH-0007','Võ Thị Hạnh',NULL,'TP. Cần Thơ','Ninh Kiều','Phường An Khánh','POOR','Kinh',5,980000,'2024-11-03','2025-12-25 08:24:38','2025-12-25 08:24:38','1992-11-05','Nữ','066778899001',72,78,'Thiếu điều kiện học tập cho con.','Thành thị','Tổ 12','Lê Văn Hòa','Cần hỗ trợ học phí.',''),(8,'HH-0008','Ngô Văn Tuấn',NULL,'Thanh Hóa','Triệu Sơn','Xã Dân Lý','AT_RISK','Kinh',6,1300000,'2024-10-05','2025-12-25 08:24:38','2025-12-25 08:24:38','1980-04-21','Nam','055443322110',48,52,'Nguy cơ tái nghèo do thiên tai.','Nông thôn','Thôn 2','Đỗ Thị Hằng','Theo dõi mùa vụ.',''),(9,'HH-0009','Phan Văn Dũng',NULL,'Quảng Nam','Thăng Bình','Xã Bình Dương','POOR','Cơ Tu',7,850000,'2024-09-18','2025-12-25 08:24:38','2025-12-25 08:24:38','1972-06-30','Nam','044556677889',81,86,'Thiếu sinh kế ổn định.','Nông thôn','Thôn 4','Nguyễn Văn Quang','Ưu tiên hỗ trợ sinh kế.',''),(10,'HH-0010','Bùi Thị Thu',NULL,'Khánh Hòa','Nha Trang','Phường Vĩnh Hòa','NEAR_POOR','Kinh',4,1600000,'2024-08-10','2025-12-25 08:24:38','2025-12-25 08:24:38','1987-08-09','Nữ','033221100998',53,57,'Thu nhập thấp, thiếu bảo hiểm y tế.','Thành thị','Tổ 3','Phạm Văn Đức','Hỗ trợ BHYT.',''),(11,'HH-0011','Trịnh Văn Hậu',NULL,'Bắc Ninh','Yên Phong','Xã Đông Phong','ESCAPED','Kinh',3,2100000,'2024-07-22','2025-12-25 08:24:38','2025-12-25 08:24:38','1995-12-01','Nam','022334455667',30,38,'Đã thoát nghèo nhờ việc làm ổn định.','Nông thôn','Thôn Lý','Nguyễn Thị Lan','Theo dõi 2 năm.',''),(12,'HH-0012','Lưu Thị Bình',NULL,'Đắk Lắk','Buôn Ma Thuột','Phường Tân An','POOR','Ê Đê',6,920000,'2024-06-12','2025-12-25 08:24:38','2025-12-25 08:24:38','1983-03-03','Nữ','088776655443',79,83,'Thiếu nước sạch và nhà ở kiên cố.','Nông thôn','Buôn 1','Y Bích','Ưu tiên hỗ trợ nước sạch.',''),(13,'HH-0013','Hoàng Văn Sơn',NULL,'Lào Cai','Sa Pa','Xã Tả Van','AT_RISK','H\'Mông',5,1400000,'2024-05-20','2025-12-25 08:24:38','2025-12-25 08:24:38','1978-01-17','Nam','077665544332',49,55,'Thu nhập bấp bênh do du lịch mùa vụ.','Nông thôn','Thôn Suối Hồ','Sùng A Lử','Hỗ trợ đào tạo nghề.',''),(14,'HH-0014','Đinh Thị Hường',NULL,'Quảng Ngãi','Tư Nghĩa','Xã Nghĩa Phương','NEAR_POOR','Kinh',4,1650000,'2024-04-02','2025-12-25 08:24:38','2025-12-25 08:24:38','1991-09-29','Nữ','011223344556',54,60,'Thiếu việc làm ổn định, cần hỗ trợ vay vốn.','Nông thôn','Thôn Trung','Trần Văn Khoa','Theo dõi sử dụng vốn.',''),(15,'HH-0015','Nguyễn Văn Phúc',NULL,'Phú Thọ','Việt Trì','Phường Vân Cơ','ESCAPED','Kinh',3,2400000,'2024-03-18','2025-12-25 08:24:38','2025-12-25 08:24:38','1984-12-25','Nam','099001122334',28,35,'Ổn định thu nhập, duy trì thoát nghèo.','Thành thị','Tổ 1','Phan Thị Dung','Theo dõi định kỳ.',''),(16,'HH-0016','Lâm Văn Hòa',NULL,'An Giang','Châu Phú','Xã Bình Mỹ','POOR','Kinh',6,870000,'2024-02-11','2025-12-25 08:24:38','2025-12-25 08:24:38','1986-06-07','Nam','066112233445',82,88,'Thiếu điều kiện nhà ở.','Nông thôn','Ấp 3','Huỳnh Thị Hòa','Đề xuất hỗ trợ nhà ở.',''),(17,'HH-0017','Phạm Thị Ánh',NULL,'Đồng Nai','Biên Hòa','Phường Tân Biên','NEAR_POOR','Kinh',4,1550000,'2024-01-14','2025-12-25 08:24:38','2025-12-25 08:24:38','1993-10-10','Nữ','055667788990',57,62,'Thiếu điều kiện y tế.','Thành thị','Khu phố 8','Trương Văn Tín','Hỗ trợ khám chữa bệnh.',''),(18,'HH-0018','Dương Văn Thái',NULL,'Ninh Bình','Hoa Lư','Xã Ninh Vân','AT_RISK','Kinh',5,1350000,'2023-12-28','2025-12-25 08:24:38','2025-12-25 08:24:38','1970-04-04','Nam','044332211000',46,51,'Nguy cơ tái nghèo do bệnh tật.','Nông thôn','Thôn Đồng','Nguyễn Văn Huy','Theo dõi sức khỏe.',''),(19,'HH-0019','Mai Thị Yến',NULL,'Quảng Trị','Cam Lộ','Xã Cam Tuyền','POOR','Vân Kiều',6,910000,'2023-11-30','2025-12-25 08:24:38','2025-12-25 08:24:38','1989-05-15','Nữ','077889900112',76,81,'Thiếu điều kiện nước sạch.','Nông thôn','Thôn 6','Hồ Văn Nam','Ưu tiên dự án nước sạch.',''),(20,'HH-0020','Trần Văn Hùng',NULL,'Bình Định','Phù Cát','Xã Cát Hanh','ESCAPED','Kinh',4,2200000,'2023-10-12','2025-12-25 08:24:38','2025-12-25 08:24:38','1981-02-28','Nam','066554433221',32,39,'Thoát nghèo ổn định, cần theo dõi.','Nông thôn','Thôn Đông','Đặng Thị Lan','Theo dõi 1 năm.','');
/*!40000 ALTER TABLE `households` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `policies`
--

DROP TABLE IF EXISTS `policies`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `policies` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `category` enum('decree','circular','report','guideline','news','announcement') COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `effective_date` date DEFAULT NULL,
  `issued_by` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attachment_url` varchar(1024) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  `summary` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tags` json DEFAULT NULL,
  `is_public` tinyint(1) DEFAULT NULL,
  `content_blocks` json DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `policies`
--

LOCK TABLES `policies` WRITE;
/*!40000 ALTER TABLE `policies` DISABLE KEYS */;
INSERT INTO `policies` VALUES (1,'Khung chuẩn nghèo đa chiều 2026-2030','decree','<p>Văn bản quy định khung tiêu chí và mức chuẩn nghèo đa chiều cho giai đoạn 2026-2030.</p><h3>1. Mục tiêu</h3><p>Thống nhất cách xác định chuẩn nghèo đa chiều và làm cơ sở phân bổ nguồn lực.</p><ul><li>Điều chỉnh ngưỡng thu nhập.</li><li>Bổ sung tiêu chí dịch vụ xã hội cơ bản.</li><li>Hướng dẫn quy trình rà soát hằng năm.</li></ul>','2026-01-05','Vụ Giảm nghèo','','2025-12-25 08:24:38','2025-12-25 08:24:38','Cập nhật chuẩn nghèo đa chiều giai đoạn 2026-2030 và hướng dẫn rà soát dữ liệu.','[\"chuẩn nghèo\", \"hướng dẫn\", \"giai đoạn 2026-2030\"]',1,NULL),(2,'Báo cáo rà soát hộ nghèo cấp huyện 2025','report','<p>Báo cáo tổng hợp kết quả rà soát cuối năm và so sánh biến động với năm trước.</p><h3>Nội dung chính</h3><ul><li>Biến động tỷ lệ hộ nghèo theo huyện.</li><li>Nguyên nhân biến động.</li><li>Đề xuất hỗ trợ bổ sung.</li></ul>','2025-12-22','Sở LĐ-TB&XH Quảng Nam','','2025-12-25 08:24:38','2025-12-25 08:24:38','Tổng hợp kết quả rà soát và đề xuất hỗ trợ bổ sung cho vùng khó khăn.','[\"báo cáo\", \"rà soát\", \"2025\"]',0,NULL),(3,'Checklist triển khai hỗ trợ sinh kế','guideline','<p>Checklist áp dụng cho các đơn vị triển khai hỗ trợ sinh kế hộ nghèo.</p><ul><li>Chuẩn bị dữ liệu hộ.</li><li>Phân nhóm đối tượng.</li><li>Thiết kế can thiệp.</li><li>Giám sát và đánh giá.</li></ul>','2025-11-10','Ban QLDA tỉnh Đồng Tháp','','2025-12-25 08:24:38','2025-12-25 08:24:38','Danh sách kiểm tra cho các bước triển khai hỗ trợ sinh kế.','[\"sinh kế\", \"checklist\", \"triển khai\"]',1,NULL),(4,'Bản tin chương trình mục tiêu quốc gia Q4/2025','guideline','<p>Bản tin tổng hợp tiến độ giải ngân, đào tạo và truyền thông của chương trình mục tiêu quốc gia quý IV/2025.</p><h3>Điểm nổi bật</h3><ul><li>Tỷ lệ giải ngân đạt 92%.</li><li>Đào tạo cán bộ cấp xã tăng 18%.</li><li>Mô hình sinh kế mới tại 6 tỉnh.</li></ul>','2025-10-15','Trung tâm thông tin','','2025-12-25 08:24:38','2025-12-25 08:24:38','Tổng hợp tin nhanh về giải ngân, đào tạo và truyền thông quý IV/2025.','[\"bản tin\", \"chương trình mục tiêu\", \"2025\"]',1,NULL),(5,'Thông tư hỗ trợ nhà ở vùng thiên tai','circular','<p>Thông tư quy định nguồn lực, đối tượng và thủ tục hỗ trợ nhà ở cho hộ nghèo chịu ảnh hưởng thiên tai.</p><h3>Phạm vi</h3><ul><li>Đối tượng thụ hưởng.</li><li>Mức hỗ trợ.</li><li>Thủ tục giải ngân.</li></ul>','2025-02-10','Bộ Xây dựng','','2025-12-25 08:24:38','2025-12-25 08:24:38','Hướng dẫn nguồn lực và thủ tục hỗ trợ nhà ở cho hộ nghèo vùng thiên tai.','[\"nhà ở\", \"thiên tai\", \"thông tư\"]',1,NULL),(6,'Đề án nâng cao năng lực cán bộ giảm nghèo 2026','decree','<p>Đề án tập trung vào đào tạo, bồi dưỡng kỹ năng số và quản trị chương trình.</p><ul><li>Đào tạo kỹ năng số.</li><li>Quản lý dữ liệu hộ nghèo.</li><li>Giám sát kết quả.</li></ul>','2026-03-01','Bộ LĐ-TB&XH','','2025-12-25 08:24:38','2025-12-25 08:24:38','Đề án nâng cao năng lực cán bộ tuyến xã, huyện cho năm 2026.','[\"đề án\", \"đào tạo\", \"năng lực\"]',0,NULL),(7,'Báo cáo đánh giá mô hình sinh kế 2024-2025','report','<p>Báo cáo đánh giá hiệu quả các mô hình sinh kế và đề xuất nhân rộng.</p><h3>Kết quả</h3><ul><li>Tăng thu nhập bình quân 15%.</li><li>Tỷ lệ duy trì mô hình 82%.</li><li>Khuyến nghị mở rộng.</li></ul>','2025-09-30','Văn phòng chương trình','','2025-12-25 08:24:38','2025-12-25 08:24:38','Đánh giá hiệu quả mô hình sinh kế tại 8 tỉnh giai đoạn 2024-2025.','[\"mô hình\", \"đánh giá\", \"sinh kế\"]',0,NULL),(8,'Hướng dẫn cập nhật dữ liệu hộ nghèo 2025','guideline','<p>Hướng dẫn chuẩn hóa dữ liệu và quy trình cập nhật trên hệ thống.</p><ul><li>Chuẩn hóa thông tin hộ.</li><li>Kiểm tra tính hợp lệ.</li><li>Phê duyệt cập nhật.</li></ul>','2025-06-15','Trung tâm dữ liệu','','2025-12-25 08:24:38','2025-12-25 08:24:38','Quy trình cập nhật dữ liệu hộ nghèo trên hệ thống năm 2025.','[\"dữ liệu\", \"quy trình\", \"2025\"]',1,NULL),(9,'Thông tư hướng dẫn hỗ trợ y tế hộ nghèo','circular','<p>Thông tư quy định nguồn lực và thủ tục hỗ trợ y tế cho hộ nghèo.</p><ul><li>Đối tượng áp dụng.</li><li>Mức hỗ trợ.</li><li>Thủ tục thanh toán.</li></ul>','2025-04-20','Bộ Y tế','','2025-12-25 08:24:38','2025-12-25 08:24:38','Quy định mức hỗ trợ y tế và thủ tục áp dụng cho hộ nghèo.','[\"y tế\", \"hộ nghèo\", \"thông tư\"]',1,NULL),(10,'Báo cáo tổng kết chương trình giảm nghèo 2025','report','<p>Báo cáo tổng kết kết quả thực hiện chương trình giảm nghèo năm 2025.</p><h3>Kết quả</h3><ul><li>Tỷ lệ giảm nghèo 1,2%.</li><li>Hỗ trợ sinh kế cho 12.000 hộ.</li><li>Giải ngân đạt 95%.</li></ul>','2025-12-31','Bộ LĐ-TB&XH','','2025-12-25 08:24:38','2025-12-25 08:24:38','Tổng kết kết quả thực hiện chương trình giảm nghèo năm 2025.','[\"tổng kết\", \"giảm nghèo\", \"2025\"]',1,NULL),(11,'Tin tức chương trình giảm nghèo tháng 12/2025','news','<p>Bản tin tổng hợp hoạt động nổi bật tháng 12/2025.</p><ul><li>Đào tạo cán bộ cấp xã.</li><li>Mô hình sinh kế hiệu quả.</li><li>Truyền thông cộng đồng.</li></ul>','2025-12-05','Trung tâm thông tin','','2025-12-25 08:24:38','2025-12-25 08:24:38','Cập nhật nhanh hoạt động đào tạo, hỗ trợ sinh kế tại các địa phương.','[\"tin tức\", \"tháng 12\", \"2025\"]',1,NULL),(12,'Thông báo lịch kiểm tra liên ngành quý I/2026','announcement','<p>Thông báo lịch kiểm tra liên ngành quý I/2026 tại các tỉnh trọng điểm.</p><ul><li>Thời gian: 10/01 - 25/01/2026.</li><li>Phạm vi: 12 tỉnh miền núi.</li><li>Đơn vị chủ trì: Bộ LĐ-TB&XH.</li></ul>','2026-01-08','Văn phòng Bộ','','2025-12-25 08:24:38','2025-12-25 08:24:38','Lịch kiểm tra liên ngành về công tác giảm nghèo quý I/2026.','[\"thông báo\", \"lịch kiểm tra\", \"2026\"]',1,NULL);
/*!40000 ALTER TABLE `policies` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `policy_drafts`
--

DROP TABLE IF EXISTS `policy_drafts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `policy_drafts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `policy_id` int DEFAULT NULL,
  `title` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `category` enum('decree','circular','report','guideline','news','announcement') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `summary` varchar(300) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `content_blocks` json DEFAULT NULL,
  `effective_date` date DEFAULT NULL,
  `issued_by` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attachment_url` varchar(1024) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tags` json DEFAULT NULL,
  `is_public` tinyint(1) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_policy_drafts_id` (`id`),
  KEY `ix_policy_drafts_policy_id` (`policy_id`),
  KEY `ix_policy_drafts_user_id` (`user_id`),
  CONSTRAINT `policy_drafts_ibfk_1` FOREIGN KEY (`policy_id`) REFERENCES `policies` (`id`),
  CONSTRAINT `policy_drafts_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `policy_drafts`
--

LOCK TABLES `policy_drafts` WRITE;
/*!40000 ALTER TABLE `policy_drafts` DISABLE KEYS */;
/*!40000 ALTER TABLE `policy_drafts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `full_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `hashed_password` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` enum('ADMIN','PROVINCE_OFFICER','DISTRICT_OFFICER','COMMUNE_OFFICER') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'PROVINCE_OFFICER',
  `province` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `district` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `commune` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL,
  `org_level` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `org_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `position` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cccd` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cccd_image_url` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  KEY `ix_users_cccd` (`cccd`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (2,'admin@ipoor.local','Nguyễn Việt Hùng','$2b$12$K5ZpSICsBqPIaReDQt2YNe8RXfI3YXN8efbgo69SYRDxjAvkPOVxO','ADMIN','Hà Nội','Ba Đình','Phường Ngọc Hà',1,'2025-12-25 08:24:38','tw','Bộ Lao động - Thương binh và Xã hội','Quản trị hệ thống','011234567890',NULL),(3,'canbo.tinh@ipoor.local','Trần Thị Thanh','$2b$12$K5ZpSICsBqPIaReDQt2YNe8RXfI3YXN8efbgo69SYRDxjAvkPOVxO','PROVINCE_OFFICER','Quảng Nam','Tam Kỳ','Phường An Mỹ',1,'2025-12-25 08:24:38','tinh','Sở LĐ-TB&XH Quảng Nam','Cán bộ tỉnh','022345678901',NULL),(4,'canbo.huyen@ipoor.local','Lê Văn Khôi','$2b$12$K5ZpSICsBqPIaReDQt2YNe8RXfI3YXN8efbgo69SYRDxjAvkPOVxO','DISTRICT_OFFICER','Nghệ An','Quỳnh Lưu','Xã Quỳnh Hồng',1,'2025-12-25 08:24:38','huyen','UBND huyện Quỳnh Lưu','Cán bộ huyện','033456789012',NULL),(5,'canbo.xa@ipoor.local','Hoàng Thị Dung','$2b$12$K5ZpSICsBqPIaReDQt2YNe8RXfI3YXN8efbgo69SYRDxjAvkPOVxO','COMMUNE_OFFICER','Quảng Ngãi','Tư Nghĩa','Xã Nghĩa Phương',1,'2025-12-25 08:24:38','xa','UBND xã Nghĩa Phương','Cán bộ xã','044567890123',NULL);
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-25  8:26:05
