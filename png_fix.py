#!/usr/bin/env python
import click
import struct
import binascii
import random
import itertools as it
from dataclasses import dataclass, field
from io import BytesIO

VERB = 0


@dataclass
class Chunk:
    length: int
    type: str
    data: bytes
    crc: int = field(default=0)

    def pack(self) -> bytes:
        return struct.pack(">I", self.length) + self.type.encode("UTF-8") + self.data + struct.pack("!I", self.crc)

    def recalc_crc(self):
        self.crc = binascii.crc32(self.type.encode() + self.data)

    def log(self, action: str):
        if VERB > 0:
            print(f"{action} {self.type} chunk")

        if VERB > 1:
            print(f"\tlength = {self.length}")

        if VERB > 2:
            print(f"\tdata = {self.data}")

        if VERB > 1:
            print(f"\tcrc = {self.crc:08X}")


@dataclass
class PngMetadata:
    width: int
    height: int
    bit_depth: int
    color_type: int
    compression_method: int
    filter_method: int
    interlace_method: int

    def __init__(self, data: bytes):
        (
            self.width,
            self.height,
            self.bit_depth,
            self.color_type,
            self.compression_method,
            self.filter_method,
            self.interlace_method,
        ) = struct.unpack(">IIBBBBB", data)

        if VERB > 2:
            print(f"Parsed IHDR: {self}")

    def pack(self) -> bytes:
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


def read_header(pngfile: BytesIO) -> bytes:
    header = pngfile.read(8)
    if VERB > 2:
        print(f"Read header: {header}")
    return header


def write_header(pngfile: BytesIO, header: bytes):
    pngfile.write(header)
    if VERB > 2:
        print(f"Wrote header: {header}")


def read_chunk(pngfile: BytesIO) -> Chunk | None:
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


def write_chunk(pngfile: BytesIO, chunk: Chunk):
    pngfile.write(chunk.pack())
    chunk.log(action="Wrote")


def bruteforce_ihdr_dimensions(chunk: Chunk) -> Chunk:
    for i, j in it.product(range(1, 10000), range(1, 10000)):
        new_chunk = chunk
        new_chunk.data = struct.pack(">II", i, j) + chunk.data[8:]
        new_chunk.recalc_crc()

        if VERB > 2:
            print(f"trying: width = {i}, height = {j}")

        if new_chunk.crc == chunk.crc:
            if VERB > 0:
                print(f"found matching CRC, width = {i}, height = {j}")

            return new_chunk

    raise Exception("Failed to find valid size by bruteforce")


def randomise_plte(chunk):
    new_chunk = Chunk(
        length=chunk.length,
        type=chunk.type,
        data=random.randbytes(chunk.length),
    )
    new_chunk.recalc_crc()

    if VERB > 0:
        print("Generated random PLTE chunk.")

    if VERB > 2:
        print(f"\tdata = {chunk.data}.")

    return new_chunk


def parse_file_chunks(input_file):
    chunks = []
    while (chunk := read_chunk(input_file)) is not None:
        chunks.append(chunk)

    return chunks


def parse_png(input_file) -> tuple[bytes, list[Chunk]]:
    header = read_header(input_file)
    chunks = parse_file_chunks(input_file)
    return header, chunks


def save_png(output_file: BytesIO, header: bytes, chunks: list[Chunk]):
    write_header(output_file, header)
    for chunk in chunks:
        write_chunk(output_file, chunk)


@click.command()
@click.argument("input-file", type=click.File("rb"))
@click.argument("output-file", type=click.File("wb"))
@click.option(
    "--fix-ihdr/--no-fix-ihdr",
    default=False,
    help="Brute force values to find the right dimensions for the image, using the CRC to verify the chunk data.",
)
@click.option(
    "--rand-plte/--no-rand-plte",
    default=False,
    help="Insert random data into the PLTE chunk if one exists.",
)
@click.option(
    "--fix-crc/--no-fix-crc",
    default=False,
    help="Re-calculate the CRC for every chunk.",
)
@click.option("--verbosity", default=0, help="Set the verbosity level.")
def main(input_file, output_file, fix_ihdr, rand_plte, fix_crc, verbosity):
    global VERB
    VERB = verbosity

    header, chunks = parse_png(input_file)

    if fix_ihdr:
        chunks = [(bruteforce_ihdr_dimensions(chunk) if chunk.type == "IHDR" else chunk) for chunk in chunks]

    if rand_plte:
        chunks = [randomise_plte(chunk) if chunk.type == "PLTE" else chunk for chunk in chunks]

    if fix_crc:
        for chunk in chunks:
            chunk.recalc_crc()

    save_png(output_file, header, chunks)


if __name__ == "__main__":
    main()
