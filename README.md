# legome

Legome is a python script that uses [OpenCV](https://opencv.org/) to apply Lego colour palette into the input picture.
The idea is to convert images and then use the image to sort of convert images into a 'lego painting'! :)

## Install

```bash
$ pip3 install numpy
...
$ pip3 install opencv-python
...
```
[pip](https://pypi.org/project/pip/) is the python package manager, usually it is called pip or pip3 depending on the python version you are using

## Usage

```bash
LegoMe (c) 2021 Geraldo Netto
Usage: python3 legome.py <input-image.jpg> <output-image.jpg>
```

The original image  
![Original image](example/input.jpg)

Will be transformed into this, now it's your turn to order some bricks and build up the image! :)  
![Transformed image](example/output.jpg)

## TODO

* refactoring
* add an option to hide/show recoloured image. currently, it is always shown
* allow the colour palette to be dynamically loaded (json), once it could be useful for other scenarios (recolouring old pictures)
* allow to upscale/downscale image (e.g.: allow to resize to A1, A2, A3, A4, ...)

## License

* [BSD 3-Clause](LICENSE)
* This project is just for fun and has no relation with [Lego](https://www.lego.com)

## References

[Learn OpenCV](https://github.com/spmallick/learnopencv/blob/master/Colormap/custom_colormap.py)
[OpenCV LUT function](https://docs.opencv.org/2.4/modules/core/doc/operations_on_arrays.html#lut)
[(unofficial) Lego colour palette](http://ryanhowerter.net/colors.php)
[OpenCV: Detect whether a window is closed or close by press “x” button](https://medium.com/@mh_yip/opencv-detect-whether-a-window-is-closed-or-close-by-press-x-button-ee51616f7088)
