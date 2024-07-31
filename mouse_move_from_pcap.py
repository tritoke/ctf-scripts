#!/usr/bin/env python
import pandas as pd
import struct
import sys
from collections import namedtuple
from PIL import Image, ImageDraw
import os

DIFFERENTIATE_BUTTONS = os.getenv("DIFFERENTIATE_BUTTONS") is not None
DRAW_WIDTH = int(os.getenv("DRAW_WIDTH", "0"))

MouseHIDData = namedtuple(
    "MouseHIDData",
    ["x_off", "y_off", "wheel", "pan", "left_click", "right_click", "middle_click"],
)

MousePosition = namedtuple(
    "MousePosition",
    ["x", "y", "left_click", "right_click", "middle_click"],
)


def u12_to_i12(u12: int) -> int:
    mask_lower_11 = (1 << 11) - 1
    return (u12 >> 11) * -0x800 + (u12 & mask_lower_11)


def parse_packed_xy(xy: bytes) -> tuple[int, int]:
    xy_int = struct.unpack("<I", xy + bytes([0]))[0]
    x_u12 = xy_int & ((1 << 12) - 1)
    y_u12 = xy_int >> 12
    return u12_to_i12(x_u12), u12_to_i12(y_u12)


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <wireshark csv file>")
        sys.exit(0)

    df = pd.read_csv(sys.argv[1], index_col=0)

    capdata = df["HID Data"].dropna().reset_index(drop=True)

    hid_data: list[MouseHIDData] = []
    for row in capdata:
        report_id, buttons, xy, wheel, pan = struct.unpack(
            "<BH3sbb", bytes.fromhex(row)
        )

        if report_id != 2:
            print(f"[warn] report_id not recognised: {report_id = }")

        lm_clicked = buttons & 1 == 1
        rm_clicked = buttons & 2 == 2
        mm_clicked = buttons & 4 == 4

        x, y = parse_packed_xy(xy)

        hid_data += [MouseHIDData(x, y, wheel, pan, lm_clicked, rm_clicked, mm_clicked)]

    relative_positions = [MousePosition(0, 0, False, False, False)]
    for data in hid_data:
        last = relative_positions[-1]
        new_pos = last.x + data.x_off, last.y + data.y_off
        relative_positions += [MousePosition(*new_pos, *data[4:])]

    min_x = min(pos.x for pos in relative_positions)
    min_y = min(pos.y for pos in relative_positions)
    x_shift = -min_x
    y_shift = -min_y

    positions = [
        MousePosition(pos.x + x_shift, pos.y + y_shift, *pos[2:])
        for pos in relative_positions
    ]

    img_width = max(pos.x for pos in positions) + 1
    img_height = max(pos.y for pos in positions) + 1
    img = Image.new(mode="RGB", size=(img_width, img_height), color=(0xFF, 0xFF, 0xFF))
    img_draw = ImageDraw.Draw(img)

    for last_pos, pos in zip(positions, positions[1:]):
        if DIFFERENTIATE_BUTTONS:
            pixel = (
                0xFF if pos.left_click else 0x00,
                0xFF if pos.right_click else 0x00,
                0xFF if pos.middle_click else 0x00,
            )

            img_draw.line(
                [(last_pos.x, last_pos.y), (pos.x, pos.y)], fill=pixel, width=DRAW_WIDTH
            )
        elif pos.left_click or pos.right_click or pos.middle_click:
            img_draw.line(
                [(last_pos.x, last_pos.y), (pos.x, pos.y)],
                fill=(0, 0, 0),
                width=DRAW_WIDTH,
            )

    img.save("out.png")


if __name__ == "__main__":
    main()
