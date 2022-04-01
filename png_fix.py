#!/usr/bin/env python
import click
import struct
import binascii
import random
import itertools as it

VERB = 0


def read_header(pngfile):
    header = pngfile.read(8)
    if VERB > 2:
        print(f"Read header: {header}")
    return header


def write_header(pngfile, header):
    pngfile.write(header)
    if VERB > 2:
        print(f"Wrote header: {header}")


def read_chunk(pngfile):
    try:
        (length,) = struct.unpack(">I", pngfile.read(4))
        chunk_type = pngfile.read(4).decode()
        chunk_data = pngfile.read(length)
        (crc,) = struct.unpack("!I", pngfile.read(4))
    except struct.error:
        return None

    if VERB > 0:
        print(f"Read {chunk_type} chunk")

    if VERB > 1:
        print(f"\tlength = {length}")

    if VERB > 2:
        print(f"\tdata = {chunk_data}")

    if VERB > 1:
        print(f"\tcrc = {crc:08X}")


    return length, chunk_type, chunk_data, crc


def write_chunk(pngfile, chunk):
    l, ct, cd, crc = chunk

    if VERB > 0:
        print(f"Wrote {ct} chunk")

    if VERB > 1:
        print(f"\tlength = {l}")

    if VERB > 2:
        print(f"\tdata = {cd}")

    if VERB > 1:
        print(f"\tcrc = {crc:08X}")

    pngfile.write(
        struct.pack(">I", l)
        + ct.encode("UTF-8")
        + cd
        + struct.pack("!I", crc)
    )


def parse_ihdr_data(cd):
    items = struct.unpack(">IIBBBBB", cd)
    if VERB > 2:
        print("Parsed IHDR: ", *items)

    return items


def calc_crc(ct, data):
    return binascii.crc32(ct.encode() + data)


def recalc_chunk_crc(l, ct, cd):
    return (l, ct, cd, calc_crc(ct, cd))


def bruteforce_ihdr_dimensions(chunk):
    l, ct, cd, crc = chunk
    xl, yl, bd, col_t, cm, fm, im = parse_ihdr_data(cd)

    for i, j in it.product(range(1, 10000), range(1, 10000)):
        new_data = struct.pack(">II", i, j) + cd[8:]

        if VERB > 2:
            print(f"trying: width = {i}, height = {j}")

        if calc_crc(ct, new_data) == crc:
            if VERB > 0:
                print(f"found matching CRC, width = {i}, height = {j}")

            return (l, ct, new_data, crc)

    return chunk


def randomise_plte(chunk):
    l, ct, *_ = chunk

    cd = random.randbytes(l)

    if VERB > 0:
        print("Generated random PLTE chunk.")

    if VERB > 2:
        print(f"\tdata = {cd}.")

    return recalc_chunk_crc(l, ct, cd)


def parse_file_chunks(input_file):
    chunks = []
    while (chunk := read_chunk(input_file)) is not None:
        chunks.append(chunk)

    return chunks


def parse_png(input_file):
    header = read_header(input_file)
    chunks = parse_file_chunks(input_file)
    return header, chunks


def save_png(output_file, header, chunks):
    write_header(output_file, header)
    for chunk in chunks:
        write_chunk(output_file, chunk)


@click.command()
@click.argument("input-file", type=click.File("rb"))
@click.argument("output-file", type=click.File("wb"))
@click.option("--fix-ihdr/--no-fix-ihdr",   default=False, help="Brute force values to find the right dimensions for the image, using the CRC to verify the chunk data.")
@click.option("--rand-plte/--no-rand-plte", default=False, help="Insert random data into the PLTE chunk if one exists.")
@click.option("--fix-crc/--no-fix-crc",     default=False, help="Re-calculate the CRC for every chunk.")
@click.option("--verbosity", default=0, help="Set the verbosity level.")
def main(input_file, output_file, fix_ihdr, rand_plte, fix_crc, verbosity):
    global VERB
    VERB = verbosity

    header, chunks = parse_png(input_file)

    if fix_ihdr:
        chunks = [
            bruteforce_ihdr_dimensions(chunk) if chunk[1] == "IHDR" else chunk
            for chunk in chunks
        ]

    if rand_plte:
        chunks = [
            randomise_plte(chunk) if chunk[1] == "PLTE" else chunk
            for chunk in chunks
        ]

    if fix_crc:
        chunks = [
            recalc_chunk_crc(*chunk[:3])
            for chunk in chunks
        ]

    save_png(output_file, header, chunks)

if __name__ == "__main__":
    main()
