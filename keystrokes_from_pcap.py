#!/usr/bin/env python
import numpy as np
import pandas as pd
import struct
import sys

CAPS = False


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <wireshark csv file>")
        sys.exit(0)

    df = pd.read_csv(sys.argv[1], index_col=0)

    capdata = df["Leftover Capture Data"].dropna().reset_index(drop=True)

    data = ""
    for i in capdata:
        if not i:
            print("hi")
            continue
        arr = bytearray.fromhex(i)
        for k in arr[1:]:
            j = int(k)
            if j == 0:
                continue
            if j in keymap:
                kb = keymap[j]
                if "capslock" in kb.lower():
                    global CAPS
                    CAPS = not CAPS
                else:
                    if CAPS:
                        data += kb.upper()
                    else:
                        data += kb.lower()

    print(data)


keymap = {
    0x04: "A",
    0x05: "B",
    0x06: "C",
    0x07: "D",
    0x08: "E",
    0x09: "F",
    0x0A: "G",
    0x0B: "H",
    0x0C: "I",
    0x0D: "J",
    0x0E: "K",
    0x0F: "L",
    0x10: "M",
    0x11: "N",
    0x12: "O",
    0x13: "P",
    0x14: "Q",
    0x15: "R",
    0x16: "S",
    0x17: "T",
    0x18: "U",
    0x19: "V",
    0x1A: "W",
    0x1B: "X",
    0x1C: "Y",
    0x1D: "Z",
    0x1E: "1",
    0x1F: "2",
    0x20: "3",
    0x21: "4",
    0x22: "5",
    0x23: "6",
    0x24: "7",
    0x25: "8",
    0x26: "9",
    0x27: "0",
    0x2C: " ",
    0x2F: "{",
    0x30: "}",
    0x31: "\\",
    0x32: "#",
    0x33: ";",
    0x34: "'",
    0x35: "^",
    0x36: ",",
    0x37: ".",
    0x38: "/",
    0x39: "[CAPSLOCK]",
}


if __name__ == "__main__":
    main()
