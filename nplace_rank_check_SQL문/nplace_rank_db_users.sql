CREATE DATABASE  IF NOT EXISTS `nplace_rank_db` /*!40100 DEFAULT CHARACTER SET utf8mb3 */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `nplace_rank_db`;
-- MySQL dump 10.13  Distrib 8.0.38, for Win64 (x86_64)
--
-- Host: 192.168.0.26    Database: nplace_rank_db
-- ------------------------------------------------------
-- Server version	8.0.39

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `user_num` int NOT NULL AUTO_INCREMENT,
  `id` varchar(100) NOT NULL,
  `password` varchar(100) NOT NULL,
  `username` varchar(50) NOT NULL,
  `place_id` varchar(50) NOT NULL,
  `vip_day` date DEFAULT NULL,
  PRIMARY KEY (`user_num`),
  UNIQUE KEY `id_UNIQUE` (`id`),
  UNIQUE KEY `place_id_UNIQUE` (`place_id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'테스트','test','웨이양','1027695353','2025-08-05'),(2,'맹구포차','aodrnvhck','맹구포차','1824150629','2025-09-05'),(3,'광안리송원','thddnjs','광안리 송원','16681733','2022-01-01'),(5,'의정부피쏘','vlTh','의정부 피쏘','1241503073','2024-09-05'),(6,'감탄계불당점','qnfekdwja','감탄계 불당점','1890638017','2024-09-05'),(7,'양재역탐라순대국','didwodurxkafktnseornr','양재역 탐라순대국','1113983640','2024-09-05'),(8,'명품김보살','rlaqhtkf','천상장군 명품 김보살 신점','1918659828','2024-09-05'),(9,'잠실본디','wkatlfqhsel','잠실 본디','1197609869','2024-09-05'),(10,'전포세번째','wjsvhtpqjsWo','전포 세번째','1378868399','2024-09-05'),(11,'사상조돼리','tktkdwhehofl','사상 조돼리','1220246922','2024-09-05'),(12,'해운대리본','godnseoflqhs','해운대 리본','1615812977','2024-09-05');
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

-- Dump completed on 2024-11-11 20:29:11
