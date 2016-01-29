-- --------------------------------------------------------
-- Host:                         localhost
-- Server version:               10.1.10-MariaDB - mariadb.org binary distribution
-- Server OS:                    Win64
-- HeidiSQL Version:             9.3.0.4984
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8mb4 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;

-- Dumping database structure for tradunio
DROP DATABASE IF EXISTS `tradunio`;
CREATE DATABASE IF NOT EXISTS `tradunio` /*!40100 DEFAULT CHARACTER SET utf8 */;
USE `tradunio`;


-- Dumping structure for table tradunio.clubs
DROP TABLE IF EXISTS `clubs`;
CREATE TABLE IF NOT EXISTS `clubs` (
  `idcl` int(10) NOT NULL COMMENT 'Club id',
  `name` varchar(25) NOT NULL COMMENT 'Club name',
  PRIMARY KEY (`idcl`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Data exporting was unselected.


-- Dumping structure for table tradunio.money
DROP TABLE IF EXISTS `money`;
CREATE TABLE IF NOT EXISTS `money` (
  `idu` int(10) NOT NULL COMMENT 'Identificador del usuario',
  `date` date NOT NULL COMMENT 'Fecha',
  `money` int(10) NOT NULL,
  PRIMARY KEY (`idu`,`date`),
  UNIQUE KEY `idu` (`idu`),
  CONSTRAINT `money_ibfk_1` FOREIGN KEY (`idu`) REFERENCES `users` (`idu`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Data exporting was unselected.


-- Dumping structure for table tradunio.owners
DROP TABLE IF EXISTS `owners`;
CREATE TABLE IF NOT EXISTS `owners` (
  `idp` int(10) NOT NULL,
  `idu` int(10) NOT NULL,
  PRIMARY KEY (`idp`,`idu`),
  KEY `owners_fk_idu` (`idu`),
  CONSTRAINT `owners_fk_idp` FOREIGN KEY (`idp`) REFERENCES `players` (`idp`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `owners_fk_idu` FOREIGN KEY (`idu`) REFERENCES `users` (`idu`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Data exporting was unselected.


-- Dumping structure for table tradunio.players
DROP TABLE IF EXISTS `players`;
CREATE TABLE IF NOT EXISTS `players` (
  `idp` int(10) NOT NULL COMMENT 'ID del jugador',
  `name` varchar(25) NOT NULL COMMENT 'Nombre',
  `position` int(10) NOT NULL COMMENT 'Demarcación del jugador',
  `idcl` int(10) DEFAULT NULL COMMENT 'ID del club',
  PRIMARY KEY (`idp`),
  KEY `idcl` (`idcl`),
  CONSTRAINT `players_fk_idcl` FOREIGN KEY (`idcl`) REFERENCES `clubs` (`idcl`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Data exporting was unselected.


-- Dumping structure for table tradunio.points
DROP TABLE IF EXISTS `points`;
CREATE TABLE IF NOT EXISTS `points` (
  `idp` int(10) NOT NULL,
  `gameday` int(10) NOT NULL COMMENT 'ID jornada',
  `points` int(10) NOT NULL,
  PRIMARY KEY (`idp`,`gameday`),
  CONSTRAINT `points_fk_idp` FOREIGN KEY (`idp`) REFERENCES `players` (`idp`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Data exporting was unselected.


-- Dumping structure for table tradunio.prices
DROP TABLE IF EXISTS `prices`;
CREATE TABLE IF NOT EXISTS `prices` (
  `idp` int(10) NOT NULL,
  `date` date NOT NULL,
  `price` int(10) NOT NULL,
  PRIMARY KEY (`idp`,`date`),
  CONSTRAINT `prices_idp_fk` FOREIGN KEY (`idp`) REFERENCES `players` (`idp`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Data exporting was unselected.


-- Dumping structure for table tradunio.teamvalue
DROP TABLE IF EXISTS `teamvalue`;
CREATE TABLE IF NOT EXISTS `teamvalue` (
  `idu` int(10) NOT NULL,
  `date` date NOT NULL,
  `value` int(10) NOT NULL,
  PRIMARY KEY (`idu`,`date`),
  CONSTRAINT `teamvalue_idu_fk` FOREIGN KEY (`idu`) REFERENCES `users` (`idu`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Data exporting was unselected.


-- Dumping structure for table tradunio.transactions
DROP TABLE IF EXISTS `transactions`;
CREATE TABLE IF NOT EXISTS `transactions` (
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
  CONSTRAINT `transactions_idu_fk` FOREIGN KEY (`idu`) REFERENCES `users` (`idu`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Data exporting was unselected.


-- Dumping structure for table tradunio.users
DROP TABLE IF EXISTS `users`;
CREATE TABLE IF NOT EXISTS `users` (
  `idu` int(10) NOT NULL,
  `name` varchar(25) NOT NULL,
  `idc` int(10) NOT NULL,
  PRIMARY KEY (`idu`,`name`),
  UNIQUE KEY `idu` (`idu`),
  KEY `idu_2` (`idu`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Data exporting was unselected.
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IF(@OLD_FOREIGN_KEY_CHECKS IS NULL, 1, @OLD_FOREIGN_KEY_CHECKS) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
