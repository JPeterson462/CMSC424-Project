USE mmdadb;

DROP TABLE IF EXISTS image_metadata;
DROP TABLE IF EXISTS audio_metadata;
DROP TABLE IF EXISTS document_metadata;
DROP TABLE IF EXISTS video_metadata;
DROP TABLE IF EXISTS file_instance;
DROP TABLE IF EXISTS document_type;
DROP TABLE IF EXISTS dagr;
DROP TABLE IF EXISTS category;
DROP TABLE IF EXISTS category_mapping;
DROP TABLE IF EXISTS annotation;

CREATE TABLE document_type (
	document_type_id int,
	document_type varchar(100),
	PRIMARY KEY (document_type_id)
);

INSERT INTO document_type (	document_type_id, document_type ) VALUES ( 0, "Unknown" );
INSERT INTO document_type (	document_type_id, document_type ) VALUES ( 1, "Document" );
INSERT INTO document_type (	document_type_id, document_type ) VALUES ( 2, "Image" );
INSERT INTO document_type (	document_type_id, document_type ) VALUES ( 3, "Audio" );
INSERT INTO document_type (	document_type_id, document_type ) VALUES ( 4, "Video" );

CREATE TABLE dagr (
	dagr_guid varchar(64),
	dagr_name varchar(200),
	time_created datetime,
	parent_dagr_guid varchar(64),
	PRIMARY KEY (dagr_guid)
);

CREATE TABLE file_instance (
	file_guid varchar(64),
	dagr_guid varchar(64),
	storage_path varchar(200),
	creator_name varchar(100),
	creation_time datetime,
	last_modified datetime,
	document_type int,
	PRIMARY KEY (file_guid),
	FOREIGN KEY (dagr_guid) REFERENCES dagr(dagr_guid),
	FOREIGN KEY (document_type) REFERENCES document_type(document_type_id)
);

CREATE TABLE image_metadata (
	file_guid varchar(64),
	width int,
	height int,
	file_format varchar(64),
	FOREIGN KEY (file_guid) REFERENCES file_instance(file_guid)
);

CREATE TABLE audio_metadata (
	file_guid varchar(64),
	length varchar(64),
	bit_rate int,
	mono_or_stereo int,
	file_format varchar(64),
	FOREIGN KEY (file_guid) REFERENCES file_instance(file_guid)
);

CREATE TABLE document_metadata (
	file_guid varchar(64),
	title varchar(200),
	authors varchar(500),
	FOREIGN KEY (file_guid) REFERENCES file_instance(file_guid)
);

CREATE TABLE video_metadata (
	file_guid varchar(64),
	file_format varchar(64),
	length varchar(64),
	FOREIGN KEY (file_guid) REFERENCES file_instance(file_guid)
);

CREATE TABLE category (
	category_id int NOT NULL AUTO_INCREMENT,
	category_name varchar(100),
	parent_category_id int,
	PRIMARY KEY (category_id)
);

CREATE TABLE category_mapping (
	dagr_guid varchar(64),
    category_id int,
    FOREIGN KEY (category_id) REFERENCES category(category_id)
);

CREATE TABLE annotation (
	dagr_guid varchar(64),
	annotation varchar(500),
	FOREIGN KEY (dagr_guid) REFERENCES dagr(dagr_guid)
);