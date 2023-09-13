#!/usr/bin/env python
import numpy as np
import pandas as pd
import struct
import sys
from collections import defaultdict

def warn(msg):
    yellow = "\x1b[0;33m"
    white = "\x1b[0;37m"
    print(f"{yellow}[warn] {msg}{white}", file=sys.stderr)

CAPSLOCK_SCANCODE = 0x39
CAPSLOCK_SENTINEL = "[CAPSLOCK]"

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <wireshark csv file>")
        sys.exit(0)

    df = pd.read_csv(sys.argv[1], index_col=0)

    capdata = df["HID Data"].dropna().reset_index(drop=True)

    data = ""
    prev_pressed = [0] * 6
    caps = False
    for i, hid_data in enumerate(capdata):
        modifiers, _pad, *pressed = bytes.fromhex(hid_data)
        # modifier bits: 
        # [MSB] right gui, right alt, right shift, right ctrl, left gui, left alt, left shift, left ctrl [LSB]
        shift = modifiers & 0b0010_0010 != 0
        upper = caps ^ shift
        for k in pressed:
            # keys are left packed so if we see a zero we are at the end
            if k == 0:
                break

            if k in prev_pressed:
                continue

            if (key := keymap.get((upper, k))) is None:
                warn(f"unrecognised scancode: k=0x{k:02x} @ {i}")
                continue

            if key == CAPSLOCK_SENTINEL:
                caps = not caps
                continue

            data += key
        prev_pressed = pressed

    print(data)

# add any missing ones based on wireshark's dissection
keymap = {
    (False, 0x04): "a", (True, 0x04): "A",
    (False, 0x05): "b", (True, 0x05): "B",
    (False, 0x06): "c", (True, 0x06): "C",
    (False, 0x07): "d", (True, 0x07): "D",
    (False, 0x08): "e", (True, 0x08): "E",
    (False, 0x09): "f", (True, 0x09): "F",
    (False, 0x0A): "g", (True, 0x0A): "G",
    (False, 0x0B): "h", (True, 0x0B): "H",
    (False, 0x0C): "i", (True, 0x0C): "I",
    (False, 0x0D): "j", (True, 0x0D): "J",
    (False, 0x0E): "k", (True, 0x0E): "K",
    (False, 0x0F): "l", (True, 0x0F): "L",
    (False, 0x10): "m", (True, 0x10): "M",
    (False, 0x11): "n", (True, 0x11): "N",
    (False, 0x12): "o", (True, 0x12): "O",
    (False, 0x13): "p", (True, 0x13): "P",
    (False, 0x14): "q", (True, 0x14): "Q",
    (False, 0x15): "r", (True, 0x15): "R",
    (False, 0x16): "s", (True, 0x16): "S",
    (False, 0x17): "t", (True, 0x17): "T",
    (False, 0x18): "u", (True, 0x18): "U",
    (False, 0x19): "v", (True, 0x19): "V",
    (False, 0x1A): "w", (True, 0x1A): "W",
    (False, 0x1B): "x", (True, 0x1B): "X",
    (False, 0x1C): "y", (True, 0x1C): "Y",
    (False, 0x1D): "z", (True, 0x1D): "Z",
    (False, 0x1E): "1", (True, 0x1E): "!",
    (False, 0x1F): "2", (True, 0x1F): '"',
    (False, 0x20): "3", (True, 0x20): "£",
    (False, 0x21): "4", (True, 0x21): "$",
    (False, 0x22): "5", (True, 0x22): "%",
    (False, 0x23): "6", (True, 0x23): "^",
    (False, 0x24): "7", (True, 0x24): "&",
    (False, 0x25): "8", (True, 0x25): "*",
    (False, 0x26): "9", (True, 0x26): "(",
    (False, 0x27): "0", (True, 0x27): ")",
    (False, 0x28): "\n",(True, 0x28): "\n",
    (False, 0x2A): "[DEL]",(True, 0x28): "[DEL]",
    (False, 0x2C): " ", (True, 0x2C): " ",
    (False, 0x2D): "-", (True, 0x2D): "_",
    (False, 0x2F): "[", (True, 0x2F): "{",
    (False, 0x30): "]", (True, 0x30): "}",
    (False, 0x31): "\\",(True, 0x31): "|",
    (False, 0x32): "#", (True, 0x32): "~",
    (False, 0x33): ";", (True, 0x33): ":",
    (False, 0x34): "'", (True, 0x34): "@",
    (False, 0x36): ",", (True, 0x36): ",",
    (False, 0x37): ".", (True, 0x37): ".",
    (False, 0x38): "/", (True, 0x38): "/",
    (False, CAPSLOCK_SCANCODE): CAPSLOCK_SENTINEL, (True, CAPSLOCK_SCANCODE): CAPSLOCK_SENTINEL,
}


if __name__ == "__main__":
    main()
