# mosaic

Fork of [codebox's](https://github.com/codebox) orgiinal mosaic program.

This utility can be used to generate [photo-mosaic](http://en.wikipedia.org/wiki/Photographic_mosaic) images, to use it you must have Python installed, along with the [Pillow](http://pillow.readthedocs.org/en/latest/) imaging library.

<pre>pip install pillow --user</pre>

Or for Windows users:
<pre>python -m pip install pillow user</pre>

As well as an image to use for the photo-mosaic ([most common image formats are supported](http://pillow.readthedocs.org/en/latest/handbook/image-file-formats.html)), you will need a large collection of different images to be used as tiles. The tile images can be any shape or size (the utility will automatically crop and resize them) but for good results you will need a lot of them - a few hundred at least. One convenient way of generating large numbers of tile images is to [extract screenshots from video files](https://trac.ffmpeg.org/wiki/Create%20a%20thumbnail%20image%20every%20X%20seconds%20of%20the%20video) using [ffmpeg](https://www.ffmpeg.org/).

Run the utility from the command line, as follows:

<pre>python main.py [-i] [--image] &lt;image&gt; [-d] [--directory] &lt;tiles directory&gt;
</pre>

*   The `image` argument should contain the local file path to the image for which you want to build as a mosaic
*   The `tiles directory` argument should contain the path to the directory containing the tile images (the directory will be searched recursively, so it doesn't matter if some of the images are contained in sub-directories)

For example:

<pre>python main.py -i some_image_to_mosaic.jpg -d /path/to/tiles/folder
</pre>

The images below show an example of how the mosaic tiles are matched to the details of the original image:

![Mosaic Image](https://codebox.net/assets/images/mosaic/mosaic_small.jpg)  
<span class="smallText">Original</span>

[![Mosaic Image Detail](https://codebox.net/assets/images/mosaic/mosaic_detail.jpg)](https://codebox.net/assets/images/mosaic/mosaic_large.jpg)  
<span class="smallText">Mosaic Detail (click through for [full mosaic](https://codebox.net/assets/images/mosaic/mosaic_large.jpg) ~15MB)</span>

Producing large, highly detailed mosaics can take some time - you should experiment with the various available optional parameters to find the right balance between image quality and render time.

*   `pixels` - Pixel dimensions of each tile. <pre>[-p] [--pixels] 32</pre>
*   `resolution` - Tile matching resolution - higher values give better fit but require more processing. <pre>[-r] [--resolution] 50</pre>
*   `enlargement` - The mosaic image's dimensions will be this many times larger than the original. <pre>[-e] [--enlargement] 8</pre>
*   `out-file` - Send mosaic image to a custom file name. <pre>[-o] [--out-file] my_mosaic.jpeg</pre>
*   `verbose` - Enables verbose output. <pre>[-v] [--verbose]</pre>

In particular the `resolution` parameter can have a big impact on both these factors - its value determines how closely the program examines each tile when trying to find the best fit for a particular segment of the image. Setting `resolution` to '1' simply finds the average colour of each tile, and picks the one that most closely matches the average colour of the image segment. As the value is increased, the tile is examined in more detail. Setting `resolution` to equal the `pixels` size will cause the utility to examine each pixel in the tile individually, producing the best possible match (during my testing I didn't find a very noticeable improvement beyond a value of 5, but YMMV).

By default the utility will configure itself to use all available CPUs/CPU-cores on the host system, if you want to leave some processing power spare for other tasks then adjust the [worker_count()](https://github.com/lukebarker3/mosaic/blob/master/mosaic.py#L20) function accordingly.
