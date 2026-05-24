#!/usr/bin/env python3
"""Generate tag36h11 PNG textures for Gazebo pallet markers."""

from __future__ import annotations

import argparse
import ctypes
from ctypes import POINTER, Structure, c_bool, c_char_p, c_int, c_uint32, c_uint64
from pathlib import Path

import numpy as np
from PIL import Image


class AprilTagFamily(Structure):
    _fields_ = [
        ("ncodes", c_uint32),
        ("codes", POINTER(c_uint64)),
        ("width_at_border", c_int),
        ("total_width", c_int),
        ("reversed_border", c_bool),
        ("nbits", c_uint32),
        ("bit_x", POINTER(c_uint32)),
        ("bit_y", POINTER(c_uint32)),
        ("h", c_uint32),
        ("name", c_char_p),
        ("impl", ctypes.c_void_p),
    ]


def load_tag36h11() -> tuple[ctypes.CDLL, POINTER(AprilTagFamily)]:
    lib = ctypes.CDLL("libapriltag.so")
    lib.tag36h11_create.restype = POINTER(AprilTagFamily)
    lib.tag36h11_destroy.argtypes = [POINTER(AprilTagFamily)]
    return lib, lib.tag36h11_create()


def render_tag(family: AprilTagFamily, tag_id: int, scale: int) -> Image.Image:
    if tag_id < 0 or tag_id >= family.ncodes:
        raise ValueError(f"tag id {tag_id} is outside tag36h11 range 0..{family.ncodes - 1}")

    total_width = family.total_width
    width_at_border = family.width_at_border
    offset = (total_width - width_at_border) // 2

    # tag36h11 total_width is 10 cells: 1 white quiet-border cell around an
    # 8-cell black/data tag. The detector size parameter refers to the 8-cell
    # black tag edge, so a 0.20 m visual board pairs with size=0.160 m.
    cells = np.full((total_width, total_width), 255, dtype=np.uint8)
    cells[offset : offset + width_at_border, offset : offset + width_at_border] = 0

    code = family.codes[tag_id]
    for bit_index in range(family.nbits):
        bit = (code >> (family.nbits - 1 - bit_index)) & 1
        x = offset + family.bit_x[bit_index]
        y = offset + family.bit_y[bit_index]
        cells[y, x] = 255 if bit else 0

    image = np.repeat(np.repeat(cells, scale, axis=0), scale, axis=1)
    return Image.fromarray(image, mode="L").convert("RGB")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        default="src/rbot/simulation/rlai_gazebo/models/pallet_tags/materials/textures",
        help="Output texture directory",
    )
    parser.add_argument("--ids", nargs="+", type=int, default=[1, 2, 3, 4])
    parser.add_argument("--scale", type=int, default=64)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    lib, family_ptr = load_tag36h11()
    try:
        family = family_ptr.contents
        for tag_id in args.ids:
            image = render_tag(family, tag_id, args.scale)
            out_path = out_dir / f"tag36h11_id{tag_id}.png"
            image.save(out_path)
            print(out_path)
    finally:
        lib.tag36h11_destroy(family_ptr)


if __name__ == "__main__":
    main()
