#!/usr/bin/env python

import string

base64 = string.ascii_uppercase + string.ascii_lowercase + string.digits + "+/"


def decode_base64(s: str) -> tuple[bytes, str]:
    out = []
    curr_char = 0
    bitpos = 0
    for c in s:
        if c == "=":
            bits = 0
        else:
            bits = base64.index(c)

        # print(
        #     f"{bytes(out).decode(errors="ignore"):<10}, {c = }, curr_char = 0b{curr_char:08b}, {bitpos = }, bits = 0b{bits:08b}"
        # )

        match bitpos:
            case 0:
                curr_char = bits << 2
                bitpos = 6
            case 6:
                curr_char |= bits >> 4
                out.append(curr_char)
                curr_char = (bits & 0b1111) << 4
                bitpos = 4
            case 4:
                curr_char |= bits >> 2
                out.append(curr_char)
                curr_char = (bits & 0b11) << 6
                bitpos = 2
            case 2:
                curr_char |= bits
                out.append(curr_char)
                bitpos = 0

        # print(
        #     f"{bytes(out).decode(errors="ignore"):<10}, {c = }, curr_char = 0b{curr_char:08b}, {bitpos = }, bits = 0b{bits:08b}"
        # )

    if s.endswith("=="):
        last_byte = out.pop()
        last_byte = out.pop()
        return bytes(out), f"{last_byte >> 4:04b}"
    if s.endswith("="):
        last_byte = out.pop()
        return bytes(out), f"{last_byte >> 6:02b}"
    else:
        return bytes(out), ""


with open("strings") as f:
    lines = f.read().splitlines()

all_hidden = ""
for line in lines:
    data, hidden = decode_base64(line)
    all_hidden += hidden

out = [int(all_hidden[i : i + 8], 2) for i in range(0, len(all_hidden), 8)]
print(bytes(out))
