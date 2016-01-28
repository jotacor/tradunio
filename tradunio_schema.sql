-- MySQL dump 10.13  Distrib 5.5.46, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: tradunio
-- ------------------------------------------------------
-- Server version       5.5.46-0ubuntu0.14.04.2

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

CREATE DATABASE `tradunio` /*!40100 COLLATE 'utf8_general_ci' */

--
-- Table structure for table `clubs`
--

DROP TABLE IF EXISTS `clubs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `clubs` (
  `idcl` int(10) NOT NULL COMMENT 'ID del club',
  `name` varchar(25) NOT NULL COMMENT 'Nombre del club',
  PRIMARY KEY (`idcl`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `communities`
--

DROP TABLE IF EXISTS `communities`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `communities` (
  `idc` int(10) NOT NULL,
  `name` varchar(25) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
  `idl` int(10) NOT NULL COMMENT 'ID domain',
  PRIMARY KEY (`idc`,`name`),
  KEY `idl` (`idl`),
  CONSTRAINT `communities_ibfk_1` FOREIGN KEY (`idl`) REFERENCES `leagues` (`idl`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `gamedays`
--

DROP TABLE IF EXISTS `gamedays`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `gamedays` (
  `idg` int(11) NOT NULL AUTO_INCREMENT COMMENT 'Index',
  `gameday` varchar(2) NOT NULL COMMENT 'Jornada',
  `season` varchar(9) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL COMMENT 'YYYY/yyyy',
  PRIMARY KEY (`idg`,`gameday`,`season`)
) ENGINE=InnoDB AUTO_INCREMENT=901 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `indicators`
--

DROP TABLE IF EXISTS `indicators`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `indicators` (
  `idi` int(10) NOT NULL AUTO_INCREMENT,
  `date` varchar(8) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
  `av_points` decimal(5,2) NOT NULL COMMENT 'Total avg.',
  `av_price` decimal(5,2) NOT NULL COMMENT 'Precio medio',
  `strength` decimal(5,2) NOT NULL COMMENT '%: >6 points played',
  `performance` decimal(5,2) NOT NULL COMMENT '%: >6 points all gamedays',
  `streak` decimal(5,2) NOT NULL COMMENT '%: >6 points last gamedays',
  `profit` int(10) NOT NULL COMMENT 'Value / total points',
  PRIMARY KEY (`idi`,`date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `leagues`
--

DROP TABLE IF EXISTS `leagues`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `leagues` (
  `idl` int(10) NOT NULL AUTO_INCREMENT,
  `name` varchar(25) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
  `domain` varchar(25) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
  PRIMARY KEY (`idl`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `matches`
--

DROP TABLE IF EXISTS `matches`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `matches` (
  `idclh` int(10) NOT NULL COMMENT 'Casa',
  `idcla` int(10) NOT NULL COMMENT 'Fuera',
  `idg` int(10) NOT NULL COMMENT 'ID jornada',
  `date` varchar(8) NOT NULL,
  `time` varchar(4) NOT NULL,
  PRIMARY KEY (`idclh`,`idcla`,`idg`),
  KEY `matches_fk_idcla` (`idcla`),
  KEY `matches_fk_idg` (`idg`),
  CONSTRAINT `matches_fk_idcla` FOREIGN KEY (`idcla`) REFERENCES `clubs` (`idcl`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `matches_fk_idclh` FOREIGN KEY (`idclh`) REFERENCES `clubs` (`idcl`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `matches_fk_idg` FOREIGN KEY (`idg`) REFERENCES `gamedays` (`idg`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='Partidos de la jornada';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `money`
--

DROP TABLE IF EXISTS `money`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `money` (
  `idu` int(10) NOT NULL COMMENT 'Identificador del usuario',
  `date` varchar(8) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL COMMENT 'Fecha',
  `money` int(10) NOT NULL,
  PRIMARY KEY (`idu`,`date`),
  UNIQUE KEY `idu` (`idu`),
  CONSTRAINT `money_ibfk_1` FOREIGN KEY (`idu`) REFERENCES `users` (`idu`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `owners`
--

DROP TABLE IF EXISTS `owners`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `owners` (
  `idp` int(10) NOT NULL,
  `idu` int(10) NOT NULL,
  PRIMARY KEY (`idp`,`idu`),
  KEY `owners_fk_idu` (`idu`),
  CONSTRAINT `owners_fk_idp` FOREIGN KEY (`idp`) REFERENCES `players` (`idp`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `owners_fk_idu` FOREIGN KEY (`idu`) REFERENCES `users` (`idu`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `player_indicator`
--

DROP TABLE IF EXISTS `player_indicator`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `player_indicator` (
  `idp` int(10) NOT NULL,
  `idi` int(10) NOT NULL,
  PRIMARY KEY (`idp`,`idi`),
  KEY `player_indicator_fk_idi` (`idi`),
  CONSTRAINT `player_indicator_fk_idi` FOREIGN KEY (`idi`) REFERENCES `indicators` (`idi`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `player_indicator_fk_idp` FOREIGN KEY (`idp`) REFERENCES `players` (`idp`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `players`
--

DROP TABLE IF EXISTS `players`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `players` (
  `idp` int(10) NOT NULL COMMENT 'ID del jugador',
  `name` varchar(25) NOT NULL COMMENT 'Nombre',
  `position` int(10) NOT NULL COMMENT 'Demarcación del jugador',
  `idcl` int(10) DEFAULT NULL COMMENT 'ID del club',
  PRIMARY KEY (`idp`),
  KEY `idcl` (`idcl`),
  CONSTRAINT `players_fk_idcl` FOREIGN KEY (`idcl`) REFERENCES `clubs` (`idcl`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `points`
--

DROP TABLE IF EXISTS `points`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `points` (
  `idp` int(10) NOT NULL,
  `idg` int(10) NOT NULL COMMENT 'ID jornada',
  `points` int(10) NOT NULL,
  PRIMARY KEY (`idp`,`idg`),
  KEY `points_fk_idg` (`idg`),
  CONSTRAINT `points_fk_idg` FOREIGN KEY (`idg`) REFERENCES `gamedays` (`idg`),
  CONSTRAINT `points_fk_idp` FOREIGN KEY (`idp`) REFERENCES `players` (`idp`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `prices`
--

DROP TABLE IF EXISTS `prices`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `prices` (
  `idp` int(10) NOT NULL,
  `date` varchar(8) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
  `price` int(10) NOT NULL,
  PRIMARY KEY (`idp`,`date`),
  CONSTRAINT `prices_idp_fk` FOREIGN KEY (`idp`) REFERENCES `players` (`idp`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `teamvalue`
--

DROP TABLE IF EXISTS `teamvalue`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `teamvalue` (
  `idu` int(10) NOT NULL,
  `date` varchar(8) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
  `value` int(10) NOT NULL,
  PRIMARY KEY (`idu`,`date`),
  CONSTRAINT `teamvalue_idu_fk` FOREIGN KEY (`idu`) REFERENCES `users` (`idu`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `transactions`
--

DROP TABLE IF EXISTS `transactions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `transactions` (
  `idp` int(10) NOT NULL,
  `idu` int(10) NOT NULL,
  `type` varchar(8) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
  `price` int(10) NOT NULL,
  `date` varchar(8) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
  PRIMARY KEY (`idp`,`idu`,`date`),
  UNIQUE KEY `idp` (`idp`,`date`),
  KEY `idp_2` (`idp`),
  KEY `transactions_idu_fk` (`idu`),
  CONSTRAINT `transactions_idp_fk` FOREIGN KEY (`idp`) REFERENCES `players` (`idp`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `transactions_idu_fk` FOREIGN KEY (`idu`) REFERENCES `users` (`idu`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `users` (
  `idu` int(10) NOT NULL,
  `name` varchar(25) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
  `idc` int(10) NOT NULL,
  PRIMARY KEY (`idu`,`name`),
  UNIQUE KEY `idu` (`idu`),
  KEY `idu_2` (`idu`),
  KEY `idc` (`idc`),
  CONSTRAINT `users_ibfk_1` FOREIGN KEY (`idc`) REFERENCES `communities` (`idc`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2016-01-22 17:11:40
