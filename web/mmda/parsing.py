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

def parse_file(file):
	extension = get_extension(file)
	# http://pillow.readthedocs.io/en/3.4.x/handbook/image-file-formats.html
	image_extensions = ["bmp", "eps", "gif", "icns", "im", "jpeg", "jpg",
						"msp", "pcx", "png", "ppm", "spider", "tiff",
						"webp", "xbm", "cur", "dcx", "dds", "fli", "flc",
						"fpx", "ftex", "gbr", "gd", "ico", "imt", "iptc",
						"naa", "mcidas", "mic", "mpo", "pcd", "pixar",
						"psd", "sgi", "tga", "wal", "xpm"]
	# https://mutagen.readthedocs.io/en/latest/
	audio_extensions = ["asf", "flac", "mp4", "mp3", "ogg", "ogv", "wav", "aiff"]
	office_extensions = ["docx"]
	if extension in image_extensions:
		return parse_image(file)
	if extension in audio_extensions:
		return parse_audio(file)
	if extension in office_extensions:
		return parse_office(file)
	if file.startswith("http") and "://" in file:
		return parse_html(file)
	return False # No parser found

def parse_image(file):
	image = Image.open(file)
	# guid = str(uuid.uuid4())
	iwidth, iheight = image.size
	f_format = get_extension(file)
	with connection.cursor() as cursor:
		cursor.execute("""
			INSERT INTO mmda_imagemetadata (
				width, height, file_format
			) VALUES (
				%s, %s, %s
			)
		""", [str(iwidth), str(iheight), f_format])
	return True

def parse_audio(file):
	t = mutagen.File(file)
	info = t.info
	data = info.split("'")[1].split(",")
	a_length = info[1].strip()
	b_rate = info[2].strip()
	f_format = get_extension(file)
	mono_or_stereo_value = 1 # TODO: determine mono vs stereo (1 = mono, 2 = stereo)
	with connection.cursor() as cursor:
		cursor.execute("""
			INSERT INTO mmda_audiometadata (
				length, bit_rate, mono_or_stereo, file_format
			) VALUES (
				%s, %s, %s, %s
			)
		""", [str(a_length), str(b_rate), str(mono_or_stereo_value), f_format])
	return True

def parse_office(file):
	f_format = get_extension(file)
	zf = zipfile.ZipFile(file)
	doc = lxml.etree.fromstring(zf.read('docProps/core.xml'))
	ns = {'dc': 'http://purl.org/dc/elements/1.1'}
	creator = doc.xpath('//dc:creator', namespaces=ns)[0].text
	title = doc.xpath('//dc:title', namespaces=ns)[0].text
	with connection.cursor() as cursor:
		cursor.execute("""
			INSERT INTO mmda_documentmetadata (
				title, creator
			) VALUES (
				%s, %s
			)
		""", )
	return True

def parse_video(file):
	pass # TODO

class ResourceHTMLParser(HTMLParser):
	IMAGE = 1
	AUDIO = 2
	VIDEO = 3

	def __init__(self, handler):
		HTMLParser.__init__(self)
		self.handler = handler
		self.in_video = False
		self.in_audio = False

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
			handler.add_resource(IMAGE, find_attr(attrs, 'src'))
		if tag == 'video':
			self.in_video = True
		if tag == 'audio':
			self.in_audio = True
		if tag == 'source':
			if self.in_video:
				handler.add_resource(VIDEO, find_attr(attrs, 'src'))
			if self.in_audio:
				handler.add_resource(AUDIO, find_attr(attrs, 'src'))


	def handle_endtag(self, tag):
		if tag == 'video':
			self.in_video = False
		if tag == 'audio':
			self.in_audio = False

	def handle_data(self, data):
		pass

def parse_html_resource(type, file):
	if type == ResourceHTMLParser.IMAGE:
		parse_image(file)
	if type == ResourceHTMLParser.AUDIO:
		parse_audio(file)
	if type == ResourceHTMLParser.VIDEO:
		parse_video(file)

def parse_html(file):
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