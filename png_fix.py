#!/usr/bin/env python
import binascii
import enum
import itertools as it
import logging
import random
import struct
import zlib

from io import Reader, Writer
from argparse import ArgumentParser
from dataclasses import dataclass, field, asdict
from custom_formatter import CustomFormatter, TRACE

LOGGER = logging.getLogger(__name__)


class ColorType(enum.IntEnum):
    Greyscale = 0b000
    Truecolor = 0b010
    Indexed = 0b011
    GreyscaleAlpha = 0b100
    TruecolorAlpha = 0b110


@dataclass
class PngMetadata:
    width: int
    height: int
    bit_depth: int
    color_type: ColorType
    compression_method: int
    filter_method: int
    interlace_method: int

    def from_bytes(data: bytes):
        (
            width,
            height,
            bit_depth,
            color_type,
            compression_method,
            filter_method,
            interlace_method,
        ) = struct.unpack(">IIBBBBB", data)

        meta = PngMetadata(
            width=width,
            height=height,
            bit_depth=bit_depth,
            color_type=ColorType(color_type),
            compression_method=compression_method,
            filter_method=filter_method,
            interlace_method=interlace_method,
        )
        LOGGER.log(TRACE, "Parsed IHDR: %s", meta)

        return meta

    def __bytes__(self) -> bytes:
        return struct.pack(
            ">IIBBBBB",
            self.width,
            self.height,
            self.bit_depth,
            self.color_type,
            self.compression_method,
            self.filter_method,
            self.interlace_method,
        )


@dataclass
class Chunk:
    length: int
    type: str
    data: bytes
    crc: int = field(default=0)

    def __post_init__(self):
        if binascii.crc32(self.type.encode() + self.data) != self.crc:
            LOGGER.warning("CRC32 for %s chunk is incorrect", self.type)
            if self.type == "IHDR":
                LOGGER.warning(
                    "Metadata contents: %s", PngMetadata.from_bytes(self.data)
                )

    def __bytes__(self) -> bytes:
        return (
            struct.pack(">I", self.length)
            + self.type.encode("UTF-8")
            + self.data
            + struct.pack("!I", self.crc)
        )

    def recalc_crc(self):
        self.crc = binascii.crc32(self.type.encode() + self.data)

    def log(self, action: str):
        LOGGER.info("%s %s chunk", action, self.type)
        LOGGER.debug("\tlength = %d", self.length)
        LOGGER.log(TRACE, "\tdata = %s", self.data)
        LOGGER.debug("\tlength = %08x", self.crc)


def read_header(pngfile: Reader[bytes]) -> bytes:
    header = pngfile.read(8)
    LOGGER.log(TRACE, "Read header: %s", header)
    return header


def write_header(pngfile: Writer[bytes], header: bytes):
    pngfile.write(header)
    LOGGER.log(TRACE, "Wrote header: %s", header)


def read_chunk(pngfile: Reader[bytes]) -> Chunk | None:
    try:
        (length,) = struct.unpack(">I", pngfile.read(4))
        chunk_type = pngfile.read(4).decode()
        chunk_data = pngfile.read(length)
        (crc,) = struct.unpack("!I", pngfile.read(4))
    except struct.error:
        return None

    chunk = Chunk(length, chunk_type, chunk_data, crc)

    chunk.log(action="Read")
    return chunk


def write_chunk(pngfile: Writer[bytes], chunk: Chunk):
    pngfile.write(bytes(chunk))
    chunk.log(action="Wrote")


def set_metadata_property(chunk: Chunk, kv_pair: str) -> Chunk:
    meta = asdict(PngMetadata.from_bytes(chunk.data))

    key, _, value = kv_pair.partition("=")
    key = key.strip().lower()
    value = int(value.strip())

    if key not in meta:
        LOGGER.warning("Cannot set unknown metadata property %s", key)
        LOGGER.warning("Valid properties: %s", meta.keys())
        return chunk

    if key == "color_type":
        meta[key] = ColorType(value)
    else:
        meta[key] = value

    chunk = Chunk(chunk.length, chunk.type, bytes(PngMetadata(**meta)))
    chunk.recalc_crc()
    return chunk


def bruteforce_ihdr_dimensions(chunk: Chunk) -> Chunk:
    for width, height in it.product(range(1, 10000), range(1, 10000)):
        new_chunk = chunk
        new_chunk.data = struct.pack(">II", width, height) + chunk.data[8:]
        new_chunk.recalc_crc()

        LOGGER.log(TRACE, "trying: width = %d, height = %d", width, height)

        if new_chunk.crc == chunk.crc:
            LOGGER.info("found matching CRC, width = %d, height = %d", width, height)

            return new_chunk

    raise Exception(
        "Failed to find valid size by bruteforce between 1 and 10000 pixels"
    )


def randomise_plte(chunk):
    new_chunk = Chunk(
        length=chunk.length,
        type=chunk.type,
        data=random.randbytes(chunk.length),
    )
    new_chunk.recalc_crc()

    LOGGER.info("Generated random PLTE chunk.")
    LOGGER.log(TRACE, "\tdata = %s.", chunk.data)

    return new_chunk


def parse_file_chunks(input_file):
    chunks = []
    while (chunk := read_chunk(input_file)) is not None:
        chunks.append(chunk)

    return chunks


def parse_png(input_file: Reader[bytes]) -> tuple[bytes, list[Chunk]]:
    header = read_header(input_file)
    chunks = parse_file_chunks(input_file)
    return header, chunks


def save_png(output_file: Writer[bytes], header: bytes, chunks: list[Chunk]):
    write_header(output_file, header)
    for chunk in chunks:
        write_chunk(output_file, chunk)


def detect_excess_data(chunks: list[Chunk]):
    try:
        meta = PngMetadata.from_bytes(chunks[0].data)
    except Exception as e:
        LOGGER.exception("Invalid metadata chunk", exc_info=e)
        return

    try:
        compressed_data = b"".join(
            chunk.data for chunk in chunks if chunk.type == "IDAT"
        )
        data = zlib.decompress(compressed_data)
    except Exception as e:
        LOGGER.exception("Failed to decompress IDAT chunk data", exc_info=e)
        return

    # compute the size in bits of each pixel in the scanline
    match meta.bit_depth, meta.color_type:
        case (1 | 2 | 4 | 8 | 16, ColorType.Greyscale):
            pixel_size_bits = meta.bit_depth
        case (8 | 16, ColorType.Truecolor):
            pixel_size_bits = meta.bit_depth * 3
        case (1 | 2 | 4 | 8, ColorType.Indexed):
            pixel_size_bits = 8
        case (8 | 16, ColorType.GreyscaleAlpha):
            pixel_size_bits = meta.bit_depth * 2
        case (8 | 16, ColorType.TruecolorAlpha):
            pixel_size_bits = meta.bit_depth * 3
        case _:
            LOGGER.error(
                "Cannot check for excess data, header has illegal combination of bit_depth (%d) and color_type (%s)",
                meta.bit_depth,
                meta.color_type,
            )
            return

    # 1 for the filter byte
    scanline_size_bytes = 1 + (pixel_size_bits * meta.width + 7) // 8
    correct_data_size = scanline_size_bytes * meta.height

    if len(data) < correct_data_size:
        LOGGER.warning("There is less data in the IDAT chunks than expected")
    elif len(data) > correct_data_size:
        LOGGER.warning("There is more data in the IDAT chunks than expected")
    else:
        return

    LOGGER.warning(
        "len(data) = %d, correct_data_size = %d", len(data), correct_data_size
    )
    if len(data) % scanline_size_bytes != 0:
        LOGGER.warning("Scanline size does not divide data size, width probably wrong")
    else:
        LOGGER.warning(
            "Scanline size divides data size, correct height: %d",
            len(data) // scanline_size_bytes,
        )


def argument_parser() -> ArgumentParser:
    parser = ArgumentParser()

    parser.add_argument("--input-file")
    parser.add_argument("--output-file", required=False)
    parser.add_argument(
        "--fix-ihdr",
        action="store_true",
        help="Brute force values to find the right dimensions for the image, using the CRC to verify the chunk data.",
    )
    parser.add_argument(
        "--rand-plte",
        action="store_true",
        help="Insert random data into the PLTE chunk if one exists.",
    )
    parser.add_argument(
        "--fix-crc", action="store_true", help="Correct the CRC32 for every chunk"
    )
    parser.add_argument("--log-level", default="WARN", help="Set the log level")
    parser.add_argument(
        "--set",
        required=False,
        help="Change a PNG metadata property, e.g. --set height=1200",
    )

    return parser


def main():
    args = argument_parser().parse_args()
    level: int | str = (
        5 if args.log_level.upper() == "TRACE" else args.log_level.upper()
    )

    # create console handler with a higher log level
    LOGGER.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(CustomFormatter())
    LOGGER.addHandler(ch)

    input_file = open(args.input_file, "rb")
    header, chunks = parse_png(input_file)

    if args.set:
        chunks = [
            (set_metadata_property(chunk, args.set) if chunk.type == "IHDR" else chunk)
            for chunk in chunks
        ]

    if args.fix_ihdr:
        chunks = [
            (bruteforce_ihdr_dimensions(chunk) if chunk.type == "IHDR" else chunk)
            for chunk in chunks
        ]

    if args.rand_plte:
        chunks = [
            randomise_plte(chunk) if chunk.type == "PLTE" else chunk for chunk in chunks
        ]

    if args.fix_crc:
        for chunk in chunks:
            chunk.recalc_crc()

    detect_excess_data(chunks)

    if args.output_file:
        with open(args.output_file, "wb") as f:
            save_png(f, header, chunks)


if __name__ == "__main__":
    main()
