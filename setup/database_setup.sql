-- Run this SQL script to set up the database.

-- Create the database named mmdadb
CREATE DATABASE mmdadb CHARACTER SET UTF8;

-- Create the user django_user that we will use to connect to the database
CREATE USER 'django_user'@'localhost' IDENTIFIED BY 'password';

-- Grant all user permissions to django_user on the database
GRANT ALL ON mmdadb.* TO 'django_user'@'localhost';