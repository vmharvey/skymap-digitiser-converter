# Sky map digitiser and converter

Python tool for interactively digitising an astrophysical sky map and converting it to a different projection or coordinate system.

By default, supports the Equatorial (icrs) and Galactic coordinate systems and the Hammer, Aitoff, and Sinusoidal projections.

| Example image (see [credit](#image-credit)) | ![](/samples/apjad843bf1_lr.jpg) |
| :---: | :---: |
| **Input pane**   | ![](/samples/Input.png) |
| **Control pane** | ![](/samples/Control_window.png) |
| **Output pane**  | ![](/samples/Output.png) |

## Usage

```bash
conda env create -f environment.yaml
conda activate skymapconv
python skymap-digitiser-converter.py samples/apjad843bf1_lr.jpg
```
alternatively, for a Jupyter experience:
```bash
jupyter lab demo.ipynb
```

1. Use the alignment sliders to centre the overlaid axes over the correct part of your image.
2. Use the toggles and sliders on the left to configure the overlaid axes until they match the format of the input image. Note that the "Hammer" and "Aitoff" projections are hard to distinguish unless there are gridlines in the input image.
3. When you are satisfied with the alignment of the axes and the choice of projection, coordinate system, and central longitude, click "Extract data with current alignment".
4. Use the toggles and sliders on the right to configure the output image to your liking. The "Smoothing" slider changes the radius of the circles imitating each pixel in the output image. If the output image looks jagged, then set this slider to a lower value.

## How does it work?

We take advantage of Matplotlib's transformations system. In essence, this lets us convert the position of each pixel into a SkyCoord which we associate with the colour of that pixel. Then, we can draw those SkyCoords on a new projection. We draw each coordinate as a circle with the colour of the pixel from the original image.

This could all be made much more clever, but it also works surprisingly well considering the simplicity of it.

## Image credit

The demo image "apjad843bf1_lr.jpg" is used under a [Creative Commons Attribution 4.0 license](http://creativecommons.org/licenses/by/4.0/) from Pierre Auger Collaboration (2024) "Large-scale Cosmic-ray Anisotropies with 19 yr of Data from the Pierre Auger Observatory", The Astrophysical Journal, Volume 976, Number 1. DOI: [10.3847/1538-4357/ad843b](https://dx.doi.org/10.3847/1538-4357/ad843b).
