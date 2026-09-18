-- MySQL dump 10.13  Distrib 9.7.1, for Win64 (x86_64)
--
-- Host: localhost    Database: sigito_db
-- ------------------------------------------------------
-- Server version	9.7.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;

SET NAMES utf8mb4;
/*!50503 SET NAMES utf8mb4 */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ 'bb2fd91c-7c9a-11f1-9cf6-0a0027000013:1-178';
--
-- Dumping data for table `articulos`
--

LOCK TABLES `articulos` WRITE;
/*!40000 ALTER TABLE `articulos` DISABLE KEYS */;
INSERT INTO `articulos` VALUES (1,'TEC-0001','Proyector Epson PowerLite X200',1,'Epson','PowerLite X200','EPX200-001',NULL,'bueno','disponible','2024-01-15','Bodega Central','2026-07-14 00:31:13'),(2,'TEC-0002','Laptop Dell Latitude 5420',1,'Dell','Latitude 5420','DL5420-002',NULL,'bueno','disponible','2023-08-10','Bodega Central','2026-07-14 00:31:13'),(3,'TEC-0003','Laptop HP ProBook 450',1,'HP','ProBook 450 G8','HP450-003',NULL,'regular','disponible','2022-03-05','Sala de Maestros','2026-07-14 00:31:13'),(4,'TEC-0004','Cámara Web Logitech C920',1,'Logitech','C920','LGC920-004',NULL,'bueno','disponible','2024-05-20','Bodega Central','2026-07-14 00:31:14'),(5,'TEC-0005','Tablet Samsung Galaxy Tab A8',1,'Samsung','Galaxy Tab A8','SGT8-005',NULL,'bueno','disponible','2024-02-14','Bodega Central','2026-07-14 00:31:14'),(6,'AUD-0001','Micrófono inalámbrico Shure',3,'Shure','BLX24','SHBLX24-006',NULL,'bueno','disponible','2023-11-01','Auditorio','2026-07-14 00:31:14'),(7,'AUD-0002','Bocina portátil JBL',3,'JBL','PartyBox 110','JBLPB110-007',NULL,'bueno','disponible','2023-09-12','Auditorio','2026-07-14 00:31:15'),(8,'AUD-0003','Cámara de video Canon',3,'Canon','VIXIA HF R800','CANR800-008',NULL,'regular','disponible','2021-06-18','Sala de Medios','2026-07-14 00:31:15'),(9,'OFI-0001','Escritorio de oficina',2,'Genérico','N/A','N/A',NULL,'bueno','disponible','2022-01-10','Dirección','2026-07-14 00:31:15'),(10,'OFI-0002','Silla ergonómica',2,'Genérico','N/A','N/A',NULL,'bueno','disponible','2022-01-10','Sala de Maestros','2026-07-14 00:31:15'),(11,'OFI-0003','Impresora HP LaserJet',2,'HP','LaserJet Pro M404','HPLJ404-009',NULL,'bueno','disponible','2023-04-22','Secretaría','2026-07-14 00:31:16'),(12,'TEC-0006','Router TP-Link',1,'TP-Link','Archer AX20','TPAX20-010',NULL,'dañado','disponible','2021-02-01','Bodega Central','2026-07-14 00:31:16');
/*!40000 ALTER TABLE `articulos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `asignaciones`
--

LOCK TABLES `asignaciones` WRITE;
/*!40000 ALTER TABLE `asignaciones` DISABLE KEYS */;
/*!40000 ALTER TABLE `asignaciones` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `categorias`
--

LOCK TABLES `categorias` WRITE;
/*!40000 ALTER TABLE `categorias` DISABLE KEYS */;
INSERT INTO `categorias` VALUES (1,'Cómputo','Equipo tecnológico: laptops, proyectores, PCs'),(2,'Ofimática','Mobiliario y artículos de oficina'),(3,'Audiovisual','Equipo de sonido, cámaras, micrófonos');
/*!40000 ALTER TABLE `categorias` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `historial_movimientos`
--

LOCK TABLES `historial_movimientos` WRITE;
/*!40000 ALTER TABLE `historial_movimientos` DISABLE KEYS */;
INSERT INTO `historial_movimientos` VALUES (1,1,NULL,'alta',NULL,'2026-07-14 00:31:13','Artículo agregado: TEC-0001 - Proyector Epson PowerLite X200'),(2,2,NULL,'alta',NULL,'2026-07-14 00:31:13','Artículo agregado: TEC-0002 - Laptop Dell Latitude 5420'),(3,3,NULL,'alta',NULL,'2026-07-14 00:31:14','Artículo agregado: TEC-0003 - Laptop HP ProBook 450'),(4,4,NULL,'alta',NULL,'2026-07-14 00:31:14','Artículo agregado: TEC-0004 - Cámara Web Logitech C920'),(5,5,NULL,'alta',NULL,'2026-07-14 00:31:14','Artículo agregado: TEC-0005 - Tablet Samsung Galaxy Tab A8'),(6,6,NULL,'alta',NULL,'2026-07-14 00:31:14','Artículo agregado: AUD-0001 - Micrófono inalámbrico Shure'),(7,7,NULL,'alta',NULL,'2026-07-14 00:31:15','Artículo agregado: AUD-0002 - Bocina portátil JBL'),(8,8,NULL,'alta',NULL,'2026-07-14 00:31:15','Artículo agregado: AUD-0003 - Cámara de video Canon'),(9,9,NULL,'alta',NULL,'2026-07-14 00:31:15','Artículo agregado: OFI-0001 - Escritorio de oficina'),(10,10,NULL,'alta',NULL,'2026-07-14 00:31:15','Artículo agregado: OFI-0002 - Silla ergonómica'),(11,11,NULL,'alta',NULL,'2026-07-14 00:31:16','Artículo agregado: OFI-0003 - Impresora HP LaserJet'),(12,12,NULL,'alta',NULL,'2026-07-14 00:31:16','Artículo agregado: TEC-0006 - Router TP-Link');
/*!40000 ALTER TABLE `historial_movimientos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `mantenimientos`
--

LOCK TABLES `mantenimientos` WRITE;
/*!40000 ALTER TABLE `mantenimientos` DISABLE KEYS */;
/*!40000 ALTER TABLE `mantenimientos` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `profesores_autorizados`
--

LOCK TABLES `profesores_autorizados` WRITE;
/*!40000 ALTER TABLE `profesores_autorizados` DISABLE KEYS */;
/*!40000 ALTER TABLE `profesores_autorizados` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
/*!40000 ALTER TABLE `usuarios` ENABLE KEYS */;
UNLOCK TABLES;
SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-07-13 18:39:50
