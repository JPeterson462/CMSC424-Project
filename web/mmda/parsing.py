import uuid
import mutagen

from PIL import Image

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
	if extension in image_extensions:
		return parse_image(file)
	if extension in audio_extensions:
		return parse_audio(file)
	return False # No parser found

def parse_image(file):
	image = Image.open(file)
	# guid = str(uuid.uuid4())
	iwidth, iheight = image.size
	f_format = get_extension(file)
	metadata = ImageMetadata(
			width = iwidth,
			height = iheight,
			file_format = f_format
		)
	metadata.save()
	return True

def parse_audio(file):
	t = mutagen.File(file)
	info = t.info
	data = info.split("'")[1].split(",")
	a_length = info[1].strip()
	b_rate = info[2].strip()
	f_format = get_extension(file)
	metadata = AudioMetadata(
			length = a_length,
			bit_rate = b_rate,
			mono_or_stereo = 1, # TODO: determine mono vs stereo (1 = mono, 2 = stereo)
			file_format = f_format
		)
	metadata.save()
	return True