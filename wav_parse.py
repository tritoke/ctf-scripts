#!/usr/bin/env python
import struct


class WavFile:
    header_format = "4sI4s4sIHHIIHH4sI"

    def __init__(self, fname):
        with open(fname, "rb") as f:
            self.__parse(f)

    def __parse(self, fp):

        (
            self.magic,
            self.file_size,
            self.file_type_header,
            self.format_chunk_marker,
            self.len_fmt_data,
            self.fmt_type,
            self.no_chans,
            self.samp_rate,
            self.sr_bps_cs_8,
            self.bps_cs_8,
            self.bps,
            self.data_header,
            self.file_size_data,
        ) = struct.unpack(
            self.header_format, fp.read(struct.calcsize(self.header_format))
        )
        self.data = fp.read()

    def save(self, fname):
        with open(fname, "wb") as f:
            f.write(
                struct.pack(
                    self.header_format,
                    self.magic,
                    self.file_size,
                    self.file_type_header,
                    self.format_chunk_marker,
                    self.len_fmt_data,
                    self.fmt_type,
                    self.no_chans,
                    self.samp_rate,
                    self.sr_bps_cs_8,
                    self.bps_cs_8,
                    self.bps,
                    self.data_header,
                    self.file_size_data,
                )
            )
            f.write(self.data)

    def print_header(self):
        print(
            f"""
WavFile(,
    magic: {self.magic},
    file_size: {self.file_size},
    file_type_header: {self.file_type_header},
    format_chunk_marker: {self.format_chunk_marker},
    len_fmt_data: {self.len_fmt_data},
    fmt_type: {self.fmt_type},
    no_chans: {self.no_chans},
    samp_rate: {self.samp_rate},
    sr_bps_cs_8: {self.sr_bps_cs_8},
    bps_cs_8: {self.bps_cs_8},
    bps: {self.bps},
    data_header: {self.data_header},
    file_size_data: {self.file_size_data},
)
            """
        )


def main():
    br = WavFile("BankRobbing")
    valid = WavFile("valid.wav")

    br.print_header()
    valid.print_header()

    br.magic = valid.magic
    br.file_size = len(br.data) + struct.calcsize(WavFile.header_format) - 8
    br.file_type_header = valid.file_type_header
    br.format_chunk_marker = valid.format_chunk_marker
    br.len_fmt_data = valid.len_fmt_data
    br.fmt_type = 1 #valid.fmt_type
    br.no_chans = 1 #valid.no_chans
    br.samp_rate = valid.samp_rate
    br.sr_bps_cs_8 = valid.sr_bps_cs_8
    br.bps_cs_8 = valid.bps_cs_8
    br.bps = valid.bps
    br.data_header = valid.data_header
    br.file_size_data = br.file_size - struct.calcsize(WavFile.header_format)

    br.print_header()
    valid.print_header()

    br.save("fixed.wav")


if __name__ == "__main__":
    main()
