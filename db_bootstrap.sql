CREATE DATABASE `test_db` /*!40100 DEFAULT CHARACTER SET utf8 */;
CREATE USER 'app'@'%'
  IDENTIFIED BY 't3stpassw0rd';

GRANT ALL ON `test_db`.* TO 'app'@'%';