import uuid
import mutagen
import zipfile, lxml.etree
import requests
import httplib2

from mutagen.aiff import *
from mutagen.asf import *
from mutagen.flac import *
from mutagen.mp3 import *
from mutagen.mp3 import JOINTSTEREO
from mutagen.ogg import *
from mutagen.wavpack import WavPack

from urllib import request
from urllib.parse import urljoin
from django.db import connection
from PIL import Image
from io import BytesIO
from .models import *
from html.parser import HTMLParser
from bs4 import BeautifulSoup

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
	audio_extensions = ["asf", "mp3", "wav", "aiff", "mpeg"]
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
		return parse_html(file, file_guid, create_dagr, recursion_level)
	else:
		return

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
	f_format = get_extension(file).lower()
	if f_format == "asf":
		f = ASF(file)
		a_length =  str(f.info.length) + "s"
		bitrate = f.info.bitrate
		channels = self.info.channels
	elif f_format == "aiff":
		f = AIFF(file)
		a_length =  str(f.info.length) + "s"
		bitrate = f.info.bitrate
		channels = self.info.channels
	elif f_format == "mp3" or f_format == "mpeg":
		f = MP3(file)
		a_length = str(f.info.length) + "s"
		bitrate = f.info.bitrate
		if f.info.mode == JOINTSTEREO:
			channels = 2
		else:
			channels = 1
	elif f_format == "wav":
		f = WavPack(file)
		a_length = str(f.info.length) + "s"
		bitrate = f.info.sample_rate
		channels = f.info.channels
	with connection.cursor() as cursor:
		cursor.execute("""
			INSERT INTO audio_metadata (
				file_guid, length, bit_rate, mono_or_stereo, file_format
			) VALUES (
				%s, %s, %s, %s, %s
			)
		""", [guid, a_length, bitrate, channels, f_format])
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
	pass

def find_attr(attrs, attr):
	for (name, value) in attrs:
		if attr == name:
			return value
	return None

def parse_html_page(guid, url, r, recursion_level, create_dagr):
	soup = BeautifulSoup(r, 'html.parser')
	html_to_load = []
	images_to_load = []
	videos_to_load = []
	audio_to_load = []
	title = ""
	authors = ""
	keywords = []
	for link in soup.find_all('a'):
		href = link.get('href')
		if not href == None and not href in html_to_load and not href.startswith('mailto:') and not href.startswith('#'):
			html_to_load.append(href)
	for img in soup.find_all('img'):
		src = img.get('src')
		images_to_load.append(src)
	for video in soup.find_all('video'):
		children = video.findChildren()
		for child in children:
			if child.name == 'source':
				videos_to_load.append(child.get('src'))
	for audio in soup.find_all('audio'):
		children = audio.findChildren()
		for child in children:
			if child.name == 'source':
				audio_to_load.append(child.get('src'))
	for t in soup.find_all('title'):
		title = t.getText()
	for m in soup.find_all('meta'):
		if m.get('name') == 'author':
			authors = m.get('content')
		if m.get('name') == 'keywords':
			keywords = m.get('content').split(',')
	with connection.cursor() as cursor:
		cursor.execute("""
			INSERT INTO document_metadata (
				file_guid, title, authors
			) VALUES (
				%s, %s, %s
			)
		""", [guid, title, authors])
		for annotation in keywords:
			cursor.execute("""
				INSERT INTO annotation (
					dagr_guid, annotation
				) VALUES (
					%s, %s
				)
			""", [guid, annotation])
		for link in html_to_load:
			print(link)
			create_dagr(urljoin(url, link), guid, recursion_level + 1)
		for link in images_to_load:
			print(link)
			create_dagr(urljoin(url, link), guid, recursion_level + 1)
		for link in videos_to_load:
			print(link)
			create_dagr(urljoin(url, link), guid, recursion_level + 1)
		for link in audio_to_load:
			print(link)
			create_dagr(urljoin(url, link), guid, recursion_level + 1)

def parse_html(file, guid, create_dagr, recursion_level):
	print ("Parsing HTML")
	http = httplib2.Http()
	status, response = http.request(file)
	parse_html_page(guid, file, response, recursion_level, create_dagr)