import uuid
import mutagen
import zipfile, lxml.etree
import requests

from urllib import request
from urllib.parse import urljoin
from django.db import connection
from PIL import Image
from io import BytesIO
from .models import *
from html.parser import HTMLParser

def get_extension(file):
	parts = file.split('.')
	return parts[len(parts) - 1]

def parse_file(file, dagr_guid, storage_path, creator_name, creation_time, last_modified, create_dagr, recursion_level):
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
	elif file.startswith("http") and "://" in file:
		document_type = 1
	file_guid = str(uuid.uuid4())
	print(dagr_guid)
	with connection.cursor() as cursor:
		cursor.execute("""
			INSERT INTO file_instance (
				file_guid, storage_path, creator_name, creation_time,
				last_modified, document_type
			) VALUES (
				%s, %s, %s, %s, %s, %s
			)
		""", [file_guid, storage_path, creator_name, creation_time, last_modified, document_type])
		cursor.execute("""
			INSERT INTO file_dagr_mapping (
				file_guid, dagr_guid
			) VALUES (
				%s, %s
			)
		""", [file_guid, dagr_guid])
	if extension in image_extensions:
		return parse_image(file, file_guid)
	elif extension in video_extensions:
		return parse_video(file, file_guid)
	elif extension in audio_extensions:
		return parse_audio(file, file_guid)
	elif extension in office_extensions:
		return parse_office(file, file_guid)
	elif file.startswith("http") and "://" in file:
		return parse_html(file, guid, create_dagr, recursion_level)
	return False # No parser found

def parse_image(file, guid):
	if file.startswith("http://") or file.startswith("https://"):
		response = requests.get(file)
		image = Image.open(BytesIO(response.content))
	else:
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
		""", [guid, title, creator])
	return True

def parse_video(file, guid):
	pass # TODO

def find_attr(attrs, attr):
	for (name, value) in attrs:
		if attr == name:
			return value
	return None

class ResourceHTMLParser(HTMLParser):
	IMAGE = 1
	AUDIO = 2
	VIDEO = 3
	LINK = 4

	def __init__(self, handler, guid, create_dagr, recursion_level, base_url):
		HTMLParser.__init__(self)
		self.handler = handler
		self.in_video = False
		self.in_audio = False
		self.in_title = False
		self.title = None
		self.author = None
		self.guid = guid
		self.create_dagr = create_dagr
		self.recursion_level = recursion_level
		self.data  = []
		self.base_url = base_url

	def handle_starttag(self, tag, attrs):
		print("start: " + tag)
		if tag == 'img':
			self.handler(self.IMAGE, self.guid, self.base_url, find_attr(attrs, 'src'), self.create_dagr, self.recursion_level)
		if tag == 'video':
			self.in_video = True
		if tag == 'audio':
			self.in_audio = True
		if tag == 'source':
			if self.in_video:
				self.handler(self.VIDEO, self.guid, self.base_url, find_attr(attrs, 'src'), self.create_dagr, self.recursion_level)
			if self.in_audio:
				self.handler(self.AUDIO, self.guid, self.base_url, find_attr(attrs, 'src'), self.create_dagr, self.recursion_level)
		if tag == 'a':
			self.handler(self.LINK, self.guid, self.base_url, find_attr(attrs, 'href'), self.create_dagr, self.recursion_level)
		if tag == 'meta':
			name = find_attr(attrs, 'name')
			content = find_attr(attrs, 'content')
			if name == 'author':
				self.author = content
		if tag == 'title':
			self.in_title = True


	def handle_endtag(self, tag):
		print("end: " + tag)
		if tag == 'video':
			self.in_video = False
		if tag == 'audio':
			self.in_audio = False
		if tag == 'html':
			with connection.cursor() as cursor:
				cursor.execute("""
					INSERT INTO document_metadata (
						file_guid, title, authors
					) VALUES (
						%s, %s, %s
					)
				""", [self.guid, self.title, self.author])
			self.author = None
		if tag == 'title':
			self.in_title = False


	def handle_data(self, data):
		if self.in_title:
			self.title = data

def parse_html_resource(type, guid, base_url, file, create_dagr, recursion_level):
	if file == None or file.startswith("#"):
		return False
	print ("Resource: " + file)
	file = urljoin(base_url, file)
	if type == ResourceHTMLParser.IMAGE:
		create_dagr(file, guid, recursion_level + 1)
	if type == ResourceHTMLParser.AUDIO:
		create_dagr(file, guid, recursion_level + 1)
	if type == ResourceHTMLParser.VIDEO:
		create_dagr(file, guid, recursion_level + 1)
	if type == ResourceHTMLParser.LINK and not file.startswith("#") and not file.startswith("mailto:"):
		create_dagr(file, guid, recursion_level + 1)
	return True

def parse_html(file, guid, create_dagr, recursion_level):
	try:
		print ("Parsing HTML")
		f = request.urlopen(file)
		lines = f.readlines()
		contents = ''
		for line in lines:
			line_utf8 = line.decode('utf8', 'ignore')
			contents += line_utf8
		parser = ResourceHTMLParser(parse_html_resource, guid, create_dagr, recursion_level, file)
		parser.feed(contents)
	except:
		pass