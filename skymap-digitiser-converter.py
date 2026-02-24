#!/usr/bin/env python

import argparse

import skymapconv


parser = argparse.ArgumentParser(
    description = "Interactively extract data from a sky map and redraw it in a new projection or coordinate system")
parser.add_argument('file', type = str, nargs = 1,
    help = "raster image (PNG, JPEG, etc) of a sky map")
args = parser.parse_args()

iface = skymapconv.Interface(args.file[0])
iface.show()
