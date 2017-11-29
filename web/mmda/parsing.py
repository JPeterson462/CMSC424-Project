import uuid
import mutagen
import zipfile, lxml.etree

from urllib import request
from django.db import connection
from PIL import Image
from .models import *
from html.parser import HTMLParser

def get_extension(file):
	parts = file.split('.')
	return parts[len(parts) - 1]

def parse_file(file, dagr_guid, storage_path, creator_name, creation_time, last_modified):
	extension = get_extension(file)
	# http://pillow.readthedocs.io/en/3.4.x/handbook/image-file-formats.html
	image_extensions = ["bmp", "eps", "gif", "icns", "im", "jpeg", "jpg",
						"msp", "pcx", "png", "ppm", "spider", "tiff",
						"webp", "xbm", "cur", "dcx", "dds", "fli", "flc",
						"fpx", "ftex", "gbr", "gd", "ico", "imt", "iptc",
						"naa", "mcidas", "mic", "mpo", "pcd", "pixar",
						"psd", "sgi", "tga", "wal", "xpm"]
	# https://mutagen.readthedocs.io/en/latest/
	video_extensions = ["mp4"]
	audio_extensions = ["asf", "flac", "mp4", "mp3", "ogg", "ogv", "wav", "aiff"]
	office_extensions = ["docx"]
	document_type = 0
	if extension in image_extensions:
		document_type = 2
	elif extension in video_extensions:
		document_type = 4
	elif extension in audio_extensions:
		document_type = 3
	elif extension in office_extensions:
		document_type = 1
	guid = str(uuid.uuid4())
	with connection.cursor() as cursor:
		cursor.execute("""
			INSERT INTO file_instance (
				file_guid, dagr_guid, storage_path, creator_name, creation_time,
				last_modified, document_type
			) VALUES (
				%s, %s, %s, %s, %s, %s, %s
			)
		""", [guid, dagr_guid, storage_path, creator_name, creation_time, last_modified, document_type])
	if extension in image_extensions:
		return parse_image(file, guid)
	elif extension in video_extensions:
		return parse_video(file, guid)
	elif extension in audio_extensions:
		return parse_audio(file, guid)
	elif extension in office_extensions:
		return parse_office(file, guid)
	if file.startswith("http") and "://" in file:
		return parse_html(file, guid)
	return False # No parser found

def parse_image(file, guid):
	image = Image.open(file)
	iwidth, iheight = image.size
	f_format = get_extension(file)
	with connection.cursor() as cursor:
		cursor.execute("""
			INSERT INTO image_metadata (
				file_guid, width, height, file_format
			) VALUES (
				%s, %s, %s, %s
			)
		""", [guid, iwidth, iheight, f_format])
	return True

def parse_audio(file, guid):
	t = mutagen.File(file)
	info = t.info
	data = info.split("'")[1].split(",")
	a_length = info[1].strip()
	b_rate = info[2].strip()
	f_format = get_extension(file)
	mono_or_stereo_value = 1 # TODO: determine mono vs stereo (1 = mono, 2 = stereo)
	with connection.cursor() as cursor:
		cursor.execute("""
			INSERT INTO audio_metadata (
				file_guid, length, bit_rate, mono_or_stereo, file_format
			) VALUES (
				%s, %s, %s, %s, %s
			)
		""", [guid, a_length, b_rate, mono_or_stereo_value, f_format])
	return True

def parse_office(file, guid):
	f_format = get_extension(file)
	zf = zipfile.ZipFile(file)
	doc = lxml.etree.fromstring(zf.read('docProps/core.xml'))
	ns = {'dc': 'http://purl.org/dc/elements/1.1'}
	creator = doc.xpath('//dc:creator', namespaces=ns)[0].text
	title = doc.xpath('//dc:title', namespaces=ns)[0].text
	with connection.cursor() as cursor:
		cursor.execute("""
			INSERT INTO document_metadata (
				file_guid, title, creator
			) VALUES (
				%s, %s
			)
		""", )
	return True

def parse_video(file, guid):
	pass # TODO

class ResourceHTMLParser(HTMLParser):
	IMAGE = 1
	AUDIO = 2
	VIDEO = 3

	def __init__(self, handler, guid):
		HTMLParser.__init__(self)
		self.handler = handler
		self.in_video = False
		self.in_audio = False
		self.guid = guid

	def read(self, data):
		self._lines = []
		self.reset()
		self.feed(data)
		return ''.join(self._lines)

	def handle_data(self, d):
		self._lines.append(d)

	def find_attr(attrs, attr):
		for (name, value) in attrs:
			if attr == name:
				return value
		return None

	def handle_startag(self, tag, attrs):
		if tag == 'img':
			handler.add_resource(IMAGE, guid, find_attr(attrs, 'src'))
		if tag == 'video':
			self.in_video = True
		if tag == 'audio':
			self.in_audio = True
		if tag == 'source':
			if self.in_video:
				handler.add_resource(VIDEO, guid, find_attr(attrs, 'src'))
			if self.in_audio:
				handler.add_resource(AUDIO, guid, find_attr(attrs, 'src'))


	def handle_endtag(self, tag):
		if tag == 'video':
			self.in_video = False
		if tag == 'audio':
			self.in_audio = False

	def handle_data(self, data):
		pass

def parse_html_resource(type, guid, file):
	if type == ResourceHTMLParser.IMAGE:
		parse_image(file, guid)
	if type == ResourceHTMLParser.AUDIO:
		parse_audio(file, guid)
	if type == ResourceHTMLParser.VIDEO:
		parse_video(file, guid)

def parse_html(file, guid):
	f = request.urlopen(file)
	lines = f.readlines()
	contents = ''
	for line in lines:
		line_utf8 = line.decode('utf8', 'ignore')
		print(line_utf8)
		contents += line_utf8
	print(contents)
	parser = ResourceHTMLParser(parse_html_resource)
	parser.feed(contents)