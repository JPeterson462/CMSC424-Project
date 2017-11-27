-- Run this SQL script to set up the database.

-- Create the database named mmdadb
CREATE DATABASE mmdadb CHARACTER SET UTF8;

-- Create the user django_user that we will use to connect to the database
CREATE USER 'django_user'@'localhost' IDENTIFIED BY 'password';

-- Grant all user permissions to django_user on the database
GRANT ALL ON mmdadb.* TO 'django_user'@'localhost';

USE mmdadb;

-- Create the category and type tables
CREATE TABLE categories (
	category_id int,
	category_name varchar(200),
	parent_category int,
	PRIMARY KEY (category_id),
	FOREIGN KEY (parent_category) REFERENCES categories(category_id)
);
CREATE TABLE types (
	document_type_id int,
	document_type varchar(64),
	PRIMARY KEY (document_type_id)
);

-- Create the file and DAGR tables
CREATE TABLE files (
	file_guid varchar(64),
	file_name varchar(200),
	storage_path varchar(500),
	creator_name varchar(200),
	time_created datetime,
	last_modified datetime,
	document_type_id int,
	PRIMARY KEY (file_guid),
	FOREIGN KEY (document_type_id) REFERENCES types(document_type_id)
);
CREATE TABLE data_aggregates (
	dagr_guid varchar(64),
	name varchar(200),
	time_created datetime,
	parent_dagr varchar(64),
	PRIMARY KEY (dagr_guid),
	FOREIGN KEY (parent_dagr) REFERENCES data_aggregates(dagr_guid)
);

-- Create the metadata tables
CREATE TABLE images (
	file_guid varchar(64),
	width int unsigned,
	height int unsigned,
	file_format varchar(64),
	PRIMARY KEY (file_guid),
	FOREIGN KEY (file_guid) REFERENCES files(file_guid)
);
CREATE TABLE audio (
	file_guid varchar(64),
	length varchar(64),
	bit_rate varchar(64),
	mono_or_stereo int unsigned,
	file_format varchar(64),
	PRIMARY KEY (file_guid),
	FOREIGN KEY (file_guid) REFERENCES files(file_guid)
);
CREATE TABLE videos (
	file_guid varchar(64),
	length varchar(64),
	file_format varchar(64),
	PRIMARY KEY (file_guid),
	FOREIGN KEY (file_guid) REFERENCES files(file_guid)
);
CREATE TABLE documents (
	file_guid varchar(64),
	title varchar(200),
	authors varchar(500),
	PRIMARY KEY (file_guid),
	FOREIGN KEY (file_guid) REFERENCES files(file_guid)
);
CREATE TABLE annotations (
	dagr_guid varchar(64),
	annotation varchar(500)
);