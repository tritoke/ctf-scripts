#!/usr/bin/env python

import struct
import argparse


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("image", help="The image to change the dimensions of.")
    parser.add_argument("changed_image", help="The file name to save the new image to.")
    parser.add_argument("--width", required=True, help="The new width of the image.", type=int)
    parser.add_argument("--height", required=True, help="The new height of the image.", type=int)

    args = parser.parse_args()

    with open(args.image, "rb") as f:
        imdata = f.read()

    new_shape = struct.pack(">HH", args.height, args.width)

    # start of frame marker (yes there are others, I'm lazy)
    if (sof := imdata.find(bytes([0xFF, 0xC0]))) is not None:
        imdata = imdata[:sof+5] + new_shape + imdata[sof+9:]

        with open(args.changed_image, "wb") as f:
            f.write(imdata)
    else:
        print("Couldn't find Start of frame marker.")


if __name__ == "__main__":
    main()
