"""
Generate a proper rounded-corner macOS .icns icon for MP4toGIF.
Requires: Pillow (pip install Pillow)
Usage:   python make_icon.py
Output:  2.icns (overwrites the existing one)
"""

import struct
import io
from PIL import Image, ImageDraw


# ── 1. Generate the icon image ──────────────────────────────────────────
def make_icon_image(size=1024):
    """Create a rounded-corner macOS-style icon (squircle shape)."""

    # Approximate macOS squircle: use a generous corner radius.
    # macOS standard: radius ≈ size * 0.224  (same as iOS/macOS icon mask)
    r = int(size * 0.224)

    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    # Background gradient — blue accent
    # Simple: flat color with subtle inner glow effect
    margin = int(size * 0.02)
    draw.rounded_rectangle(
        [(margin, margin), (size - margin - 1, size - margin - 1)],
        radius=r,
        fill=(74, 140, 240, 255),   # #4a8cf0 — accent blue
    )

    # Play triangle (▶) — centered white
    cx, cy = size / 2, size / 2
    tri_scale = size / 1024       # make triangle size proportional
    pts = [
        (cx - 140 * tri_scale, cy - 220 * tri_scale),  # top-left
        (cx - 140 * tri_scale, cy + 220 * tri_scale),  # bottom-left
        (cx + 240 * tri_scale, cy),                     # right point
    ]
    draw.polygon([(int(x), int(y)) for x, y in pts] + [(int(pts[0][0]), int(pts[0][1]))],
                 fill=(255, 255, 255, 255))

    return im


# ── 2. ICNS binary format helpers ───────────────────────────────────────
# macOS icon types — we target 10.7+ (Lion, 2011).  Modern ARGB types
# cover sizes from 128 to 1024 px; smaller sizes use PNG-compressed entries.
ICONS = [
    # (ostype,  size,  use_png)
    ("icp4",    16,  True),    # 16x16   PNG
    ("icp5",    32,  True),    # 32x32   PNG
    ("icp6",    64,  True),    # 64x64   PNG
    ("ic07",   128,  True),    # 128x128 PNG (ARGB → blank on modern macOS)
    ("ic08",   256,  True),    # 256x256 PNG
    ("ic09",   512,  True),    # 512x512 PNG
    ("ic10",  1024,  True),    # 1024x1024 PNG
]


def pack_icon_entry(ostype, data):
    """Pack one ICNS entry: 4-byte type + 4-byte size + data."""
    entry_size = 8 + len(data)
    return ostype.encode("ascii") + struct.pack(">I", entry_size) + data


def make_icns(im):
    """Build a complete .icns file from a 1024×1024 RGBA image."""
    entries = []

    for ostype, sz, use_png in ICONS:
        if use_png:
            # Resize → save as PNG → embed directly
            buf = io.BytesIO()
            icon = im.resize((sz, sz), Image.LANCZOS)
            icon.save(buf, format="PNG", optimize=True)
            entries.append(pack_icon_entry(ostype, buf.getvalue()))
        else:
            # Resize → pack as raw ARGB (A,R,G,B per pixel, row-major)
            icon = im.resize((sz, sz), Image.LANCZOS)
            pix = icon.tobytes("raw", "BGRA")
            # BGRA → ARGB: swap R↔B, then put A first
            argb = bytearray(len(pix))
            for i in range(0, len(pix), 4):
                b, g, r, a = pix[i], pix[i+1], pix[i+2], pix[i+3]
                argb[i]   = a
                argb[i+1] = r
                argb[i+2] = g
                argb[i+3] = b
            entries.append(pack_icon_entry(ostype, bytes(argb)))

    # ICNS header: magic "icns" + 4-byte total size
    body = b"".join(entries)
    header = b"icns" + struct.pack(">I", 8 + len(body))
    return header + body


# ── 3. Main ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating 1024×1024 rounded-corner icon...")
    img = make_icon_image(1024)

    print("Packaging into .icns format...")
    icns_data = make_icns(img)

    out = "2.icns"
    with open(out, "wb") as f:
        f.write(icns_data)

    print(f"[OK] Done - {out}  ({len(icns_data):,} bytes)")
    print("  Sizes: 16, 32, 64, 128, 256, 512, 1024 px")
    print("  All with rounded corners (squircle) baked in.")
