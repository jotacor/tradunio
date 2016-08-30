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

--
-- Table structure for table `clubs`
--

DROP TABLE IF EXISTS `clubs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `clubs` (
  `idcl` int(10) NOT NULL COMMENT 'Club id',
  `name` varchar(25) NOT NULL COMMENT 'Club name',
  PRIMARY KEY (`idcl`)
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
  CONSTRAINT `owners_fk_idu` FOREIGN KEY (`idu`) REFERENCES `users` (`idu`) ON DELETE CASCADE ON UPDATE CASCADE
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
  `position` varchar(25) NOT NULL COMMENT 'Demarcación del jugador',
  `idcl` int(10) DEFAULT NULL COMMENT 'ID del club',
  PRIMARY KEY (`idp`),
  KEY `idcl` (`idcl`),
  CONSTRAINT `players_fk_idcl` FOREIGN KEY (`idcl`) REFERENCES `clubs` (`idcl`) ON DELETE CASCADE ON UPDATE CASCADE
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
  `gameday` int(10) NOT NULL COMMENT 'ID jornada',
  `points` int(10) NOT NULL,
  PRIMARY KEY (`idp`,`gameday`),
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
  `date` date NOT NULL,
  `price` int(10) NOT NULL,
  PRIMARY KEY (`idp`,`date`),
  CONSTRAINT `prices_idp_fk` FOREIGN KEY (`idp`) REFERENCES `players` (`idp`) ON DELETE CASCADE ON UPDATE CASCADE
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
  `type` varchar(8) NOT NULL COMMENT 'Buy/Sell',
  `price` int(10) NOT NULL,
  `date` date NOT NULL,
  PRIMARY KEY (`idp`,`idu`,`date`),
  UNIQUE KEY `idp` (`idp`,`date`),
  KEY `idp_2` (`idp`),
  KEY `transactions_idu_fk` (`idu`),
  CONSTRAINT `transactions_idp_fk` FOREIGN KEY (`idp`) REFERENCES `players` (`idp`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `transactions_idu_fk` FOREIGN KEY (`idu`) REFERENCES `users` (`idu`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_data`
--

DROP TABLE IF EXISTS `user_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_data` (
  `idu` int(11) NOT NULL,
  `date` date NOT NULL,
  `points` int(11) NOT NULL,
  `money` int(11) NOT NULL,
  `teamvalue` int(11) NOT NULL,
  `maxbid` int(11) NOT NULL,
  PRIMARY KEY (`idu`,`date`),
  CONSTRAINT `idu_users` FOREIGN KEY (`idu`) REFERENCES `users` (`idu`) ON DELETE CASCADE ON UPDATE CASCADE
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
  `name` varchar(25) NOT NULL,
  PRIMARY KEY (`idu`,`name`),
  UNIQUE KEY `idu` (`idu`),
  KEY `idu_2` (`idu`)
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

-- Dump completed on 2016-02-01 11:37:54
