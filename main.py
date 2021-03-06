import logging
import multiprocessing
import os
import requests
import utils

from cli.app import CommandLineApp

from mosaic import MosaicGenerator


class MosaicApp(CommandLineApp):
    mosaic_args: utils.MosaicArgs = None

    def _add_mosaic_params(self):
        """
        Generates expected parameters for the Mosaic CLI.
        """
        self.add_param('-i', '--image', required=True, action='store', help='File path / URL of the image to be re-created as a mosaic.', type=str)
        self.add_param('-d', '--directory', required=False, action='store', help='File path of the folder containing tiles to use for creating the mosaic.', type=str)
        self.add_param('-p', '--pixels', required=False, default=utils.MosaicArgs.pixels, action='store', help='Pixel dimensions of each tile. E.g. 32 will create 32x32 tiles.', type=int)
        self.add_param('-r', '--resolution', required=False, default=utils.MosaicArgs.resolution, action='store', help='Tile matching resolution - higher values give better fit but require more processing.', type=int)
        self.add_param('-e', '--enlargement', required=False, default=utils.MosaicArgs.enlargement, action='store', help='The mosaic image\'s dimensions will be this many times larger than the original.')
        self.add_param('-o', '--out-file', required=False, default=utils.MosaicArgs.out_file, action='store', help='Send mosaic image to a custom file name.', type=str)
        self.add_param('-v', '--verbose', default=utils.MosaicArgs.verbose, action='store_true', help='Verbose logging.')

    def _validate_mosaic_args(self):
        """
        Determines if given args are valid for Mosaic CLI.

        Raises:
            ValueError: If any user-provided arguments are determined to be invalid.
        """
        # set logging level
        logging.basicConfig(format='%(asctime)s %(message)s', level=utils.parse_log_level(self.mosaic_args.verbose))
        self._validate_image_path()
        self._validate_tiles_directory()

    def _validate_image_path(self):
        # if image path is URL - check image is available first
        if self.mosaic_args.image.startswith("http"):
            image_resp = requests.get(self.mosaic_args.image)
            if image_resp.ok is False:
                raise ValueError(f"Unable to download image from '{self.mosaic_args.image}'.")
        # if image path is local to machine
        elif os.path.exists(self.mosaic_args.image) is False:
            raise ValueError(f"Image file '{self.mosaic_args.image}' does not exist.")

    def _validate_tiles_directory(self):
        # check directory exists locally
        if self.mosaic_args.directory is True and os.path.exists(self.mosaic_args.directory) is False:
            raise ValueError(f"Tiles directory '{self.mosaic_args.directory}' does not exist.")

    def setup(self):
        """
        Performs setup for the Mosaic CLI.
        """
        super(MosaicApp, self).setup()
        self._add_mosaic_params()

    def main(self):
        """
        Runs the Mosaic CLI.
        """
        try:
            self.mosaic_args = utils.MosaicArgs.from_namespace(self.params)
            self._validate_mosaic_args()
        except ValueError as e:
            logging.exception("Invalid input to Mosaic CLI detected!", e)
            raise e

        # mosaic args should be valid at this point
        try:
            self.generator = MosaicGenerator(self.mosaic_args)
            self.generator.run()
        except Exception as e:
            logging.exception("Something went wrong whilst attempting to generate the mosaic.", e)
            raise e


if __name__ == "__main__":
    multiprocessing.set_start_method('spawn', True)
    app = MosaicApp()
    try:
        app.run()
    except Exception as e:
        logging.exception("Something went wrong!", e)
