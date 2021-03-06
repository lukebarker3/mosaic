from io import BytesIO
from multiprocessing import Process, Queue, cpu_count
from PIL import Image
from utils import MosaicArgs
from pprint import pprint

import logging, os, requests, sys

# https://stackoverflow.com/questions/51152059/pillow-in-python-wont-let-me-open-image-exceeds-limit
Image.MAX_IMAGE_PIXELS = 933120000


class MosaicGenerator:
	mosaic_args: MosaicArgs = None
	TILE_SIZE      = 50
	TILE_MATCH_RES =  5
	ENLARGEMENT    =  8
	OUT_FILE = 'mosaic.png'
	EOQ_VALUE = None

	@staticmethod
	def tile_block_size():
		return MosaicGenerator.TILE_SIZE / max(min(MosaicGenerator.TILE_MATCH_RES, MosaicGenerator.TILE_SIZE), 1)

	@staticmethod
	def worker_count():
		return max(cpu_count() - 1, 1)

	class TileProcessor:
		def __init__(self, tiles_directory):
			self.tiles_directory = tiles_directory

		def __process_tile(self, tile_path):
			try:
				img = Image.open(tile_path)
				# tiles must be square, so get the largest square that fits inside the image
				w = img.size[0]
				h = img.size[1]
				min_dimension = min(w, h)
				w_crop = (w - min_dimension) / 2
				h_crop = (h - min_dimension) / 2
				img = img.crop((w_crop, h_crop, w - w_crop, h - h_crop))

				large_tile_img = img.resize((MosaicGenerator.TILE_SIZE, MosaicGenerator.TILE_SIZE), Image.ANTIALIAS)
				small_tile_img = img.resize((int(MosaicGenerator.TILE_SIZE/MosaicGenerator.tile_block_size()), int(MosaicGenerator.TILE_SIZE/MosaicGenerator.tile_block_size())), Image.ANTIALIAS)

				return (large_tile_img.convert('RGB'), small_tile_img.convert('RGB'))
			except Exception as e:
				logging.exception(f"Tile processing error: {str(e)}")
				return (None, None)

		def get_tiles(self):
			large_tiles = []
			small_tiles = []

			if self.tiles_directory:
				logging.info('Reading tiles from {}...'.format(self.tiles_directory))

				# search the tiles directory recursively
				for root, subFolders, files in os.walk(self.tiles_directory):
					for tile_name in files:
						logging.debug('Reading {:40.40}\r'.format(tile_name))
						tile_path = os.path.join(root, tile_name)
						large_tile, small_tile = self.__process_tile(tile_path)
						if large_tile:
							large_tiles.append(large_tile)
							small_tiles.append(small_tile)
			else:
				logging.info('Creating basic coloured tiles...')

				

			logging.info('Finished processing tiles.')

			return (large_tiles, small_tiles)

	class TargetImage:
		def __init__(self, image_path):
			self.image_path = image_path

		def get_data(self):
			if self.image_path.startswith('http'):
				logging.info("Downloading image from URL...")
				resp = requests.get(self.image_path)
				img = Image.open(BytesIO(resp.content))
			else:
				logging.info("Retrieving image from file system...")
				img = Image.open(self.image_path)

			logging.info('Processing retrieved main image...')

			w = img.size[0] * MosaicGenerator.ENLARGEMENT
			h = img.size[1]	* MosaicGenerator.ENLARGEMENT
			large_img = img.resize((w, h), Image.ANTIALIAS)
			w_diff = (w % MosaicGenerator.TILE_SIZE)/2
			h_diff = (h % MosaicGenerator.TILE_SIZE)/2
			
			# if necessary, crop the image slightly so we use a whole number of tiles horizontally and vertically
			if w_diff or h_diff:
				large_img = large_img.crop((w_diff, h_diff, w - w_diff, h - h_diff))

			small_img = large_img.resize((int(w/MosaicGenerator.tile_block_size()), int(h/MosaicGenerator.tile_block_size())), Image.ANTIALIAS)

			image_data = (large_img.convert('RGB'), small_img.convert('RGB'))

			logging.info('Main image processed.')

			return image_data

	class TileFitter:
		def __init__(self, tiles_data):
			self.tiles_data = tiles_data

		def __get_tile_diff(self, t1, t2, bail_out_value):
			diff = 0
			i = 0
			len_t1 = len(t1)
			while i < len_t1:
				#diff += (abs(t1[i][0] - t2[i][0]) + abs(t1[i][1] - t2[i][1]) + abs(t1[i][2] - t2[i][2]))
				diff += ((t1[i][0] - t2[i][0])**2 + (t1[i][1] - t2[i][1])**2 + (t1[i][2] - t2[i][2])**2)
				if diff > bail_out_value:
					# we know already that this isn't going to be the best fit, so no point continuing with this tile
					return diff
				i += 1
			return diff

		def get_best_fit_tile(self, img_data, good_enough_diff = 25000):
			best_fit_tile_index = None
			min_diff = sys.maxsize
			tile_index = 0

			# go through each tile in turn looking for the best match for the part of the image represented by 'img_data'
			for tile_data in self.tiles_data:
				diff = self.__get_tile_diff(img_data, tile_data, min_diff)
				if diff < min_diff:
					min_diff = diff
					best_fit_tile_index = tile_index
					# "optimisation vs quality" hack
					if min_diff <= good_enough_diff:
						return best_fit_tile_index
				tile_index += 1
			return best_fit_tile_index

	@staticmethod
	def fit_tiles(work_queue, result_queue, tiles_data):
		# this function gets run by the worker processes, one on each CPU core
		tile_fitter = MosaicGenerator.TileFitter(tiles_data)

		while True:
			try:
				img_data, img_coords = work_queue.get(True)
				if img_data == MosaicGenerator.EOQ_VALUE:
					break
				tile_index = tile_fitter.get_best_fit_tile(img_data)
				result_queue.put((img_coords, tile_index))
			except KeyboardInterrupt:
				pass

		# let the result handler know that this worker has finished everything
		result_queue.put((MosaicGenerator.EOQ_VALUE, MosaicGenerator.EOQ_VALUE))

	class ProgressCounter:
		def __init__(self, total):
			self.total = total
			self.counter = 0

		def update(self):
			self.counter += 1
			logging.debug("Progress: {:04.1f}%".format(100 * self.counter / self.total))

	class MosaicImage:
		def __init__(self, original_img):
			self.image = Image.new(original_img.mode, original_img.size)
			logging.info("original_img info:")
			pprint(original_img.__dict__)
			logging.info("self.image info:")
			pprint(self.image.__dict__)
			self.x_tile_count = int(original_img.size[0] / MosaicGenerator.TILE_SIZE)
			self.y_tile_count = int(original_img.size[1] / MosaicGenerator.TILE_SIZE)
			self.total_tiles  = self.x_tile_count * self.y_tile_count

		def add_tile(self, tile_data, coords):
			img = Image.new('RGB', (MosaicGenerator.TILE_SIZE, MosaicGenerator.TILE_SIZE))
			img.putdata(tile_data)
			logging.info("tile info:")
			pprint(img.__dict__)
			self.image.paste(img, coords)

		def save(self, path):
			self.image.save(path, format='png')

	@staticmethod
	def build_mosaic(result_queue, all_tile_data_large, original_img_large):
		mosaic = MosaicGenerator.MosaicImage(original_img_large)

		active_workers = MosaicGenerator.worker_count()
		while True:
			try:
				img_coords, best_fit_tile_index = result_queue.get()

				if img_coords == MosaicGenerator.EOQ_VALUE:
					active_workers -= 1
					if not active_workers:
						break
				else:
					tile_data = all_tile_data_large[best_fit_tile_index]
					mosaic.add_tile(tile_data, img_coords)

			except KeyboardInterrupt:
				pass

		mosaic.save(MosaicGenerator.OUT_FILE)
		logging.info('\nFinished, output is in', MosaicGenerator.OUT_FILE)

	def compose(self, original_img, tiles):
		logging.info('Building mosaic, press Ctrl-C to abort...')
		original_img_large, original_img_small = original_img
		tiles_large, tiles_small = tiles

		mosaic = MosaicGenerator.MosaicImage(original_img_large)

		all_tile_data_large = [list(tile.getdata()) for tile in tiles_large]
		all_tile_data_small = [list(tile.getdata()) for tile in tiles_small]

		work_queue   = Queue(MosaicGenerator.worker_count())	
		result_queue = Queue()

		try:
			# start the worker processes that will build the mosaic image
			Process(target=MosaicGenerator.build_mosaic, args=(result_queue, all_tile_data_large, original_img_large)).start()

			# start the worker processes that will perform the tile fitting
			for n in range(MosaicGenerator.worker_count()):
				Process(target=MosaicGenerator.fit_tiles, args=(work_queue, result_queue, all_tile_data_small)).start()

			progress = MosaicGenerator.ProgressCounter(mosaic.x_tile_count * mosaic.y_tile_count)
			for x in range(mosaic.x_tile_count):
				for y in range(mosaic.y_tile_count):
					large_box = (x * MosaicGenerator.TILE_SIZE, y * MosaicGenerator.TILE_SIZE, (x + 1) * MosaicGenerator.TILE_SIZE, (y + 1) * MosaicGenerator.TILE_SIZE)
					small_box = (x * MosaicGenerator.TILE_SIZE/MosaicGenerator.tile_block_size(), y * MosaicGenerator.TILE_SIZE/MosaicGenerator.tile_block_size(), (x + 1) * MosaicGenerator.TILE_SIZE/MosaicGenerator.tile_block_size(), (y + 1) * MosaicGenerator.TILE_SIZE/MosaicGenerator.tile_block_size())
					work_queue.put((list(original_img_small.crop(small_box).getdata()), large_box))
					progress.update()

		except KeyboardInterrupt:
			logging.info('\nHalting, saving partial image please wait...')

		finally:
			# put these special values onto the queue to let the workers know they can terminate
			for n in range(MosaicGenerator.worker_count()):
				work_queue.put((MosaicGenerator.EOQ_VALUE, MosaicGenerator.EOQ_VALUE))

	def __init__(self, mosaic_args):
		self.mosaic_args = mosaic_args

	def run(self):
		MosaicGenerator.TILE_SIZE = self.mosaic_args.pixels
		MosaicGenerator.TILE_MATCH_RES = self.mosaic_args.resolution
		MosaicGenerator.ENLARGEMENT = self.mosaic_args.enlargement
		MosaicGenerator.OUT_FILE = self.mosaic_args.out_file
		tiles_data = MosaicGenerator.TileProcessor(self.mosaic_args.directory).get_tiles()
		image_data = MosaicGenerator.TargetImage(self.mosaic_args.image).get_data()
		self.compose(image_data, tiles_data)
