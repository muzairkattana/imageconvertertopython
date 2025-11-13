import argparse
import textwrap
from pathlib import Path
import runpy

import numpy as np
from PIL import Image, ImageFilter


IMAGE_EXTENSIONS = [
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.webp",
    "*.bmp",
    "*.gif",
    "*.tif",
    "*.tiff",
]


def find_latest_image(folder: Path) -> Path:
    """Find the most recently modified image in the given folder."""
    candidates = []
    for pattern in IMAGE_EXTENSIONS:
        candidates.extend(folder.glob(pattern))

    if not candidates:
        raise SystemExit(
            "No image files found in this folder. "
            "Supported extensions: png, jpg, jpeg, webp, bmp, gif, tif, tiff."
        )

    return max(candidates, key=lambda p: p.stat().st_mtime)


def image_to_points_sketch(image_path: str, max_size: int = 160):
    """Open image, resize, detect edges, and return list of edge points."""
    img = Image.open(image_path).convert("L")  # grayscale
    img.thumbnail((max_size, max_size))  # keep aspect ratio, max side = max_size

    # Simple edge detection using Pillow
    edges = img.filter(ImageFilter.FIND_EDGES)

    arr = np.array(edges)
    # Threshold: keep brighter (stronger edge) pixels
    threshold = float(arr.mean())
    ys, xs = np.where(arr > threshold)

    points = list(zip(xs.tolist(), ys.tolist()))
    width, height = img.size
    return (width, height), points


def image_to_points_color(image_path: str, max_size: int = 80):
    """Open image, resize, and return list of (x, y, (r,g,b)) pixels for color mode."""
    img = Image.open(image_path).convert("RGB")
    img.thumbnail((max_size, max_size))  # keep aspect ratio

    arr = np.array(img)  # shape (h, w, 3)
    h, w, _ = arr.shape

    points = []
    for y in range(h):
        for x in range(w):
            r, g, b = arr[y, x].tolist()
            points.append((x, y, (r, g, b)))

    return (w, h), points


def generate_python_code_sketch(width: int, height: int, points):
    """Generate Python source code that draws a black-and-white sketch using matplotlib."""
    code = f'''\
import matplotlib.pyplot as plt

WIDTH, HEIGHT = {width}, {height}
POINTS = {points!r}


def main():
    xs = [p[0] for p in POINTS]
    ys = [HEIGHT - p[1] for p in POINTS]  # flip Y so image isn't upside-down

    plt.figure(figsize=(WIDTH / 80, HEIGHT / 80), facecolor="white")
    plt.scatter(xs, ys, s=1, c="black", marker=".", linewidths=0)
    plt.axis("off")
    plt.gca().set_aspect("equal", adjustable="box")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
'''
    return textwrap.dedent(code)


def generate_python_code_color(width: int, height: int, points):
    """Generate Python source code that draws a color image using matplotlib."""
    code = f'''\
import matplotlib.pyplot as plt

WIDTH, HEIGHT = {width}, {height}
# Each point is (x, y, (r, g, b))
POINTS = {points!r}


def main():
    xs = [p[0] for p in POINTS]
    ys = [HEIGHT - p[1] for p in POINTS]  # flip Y so image isn't upside-down
    colors = [
        (rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
        for (_, _, rgb) in POINTS
    ]

    plt.figure(figsize=(WIDTH / 50, HEIGHT / 50), facecolor="white")
    plt.scatter(xs, ys, s=8, c=colors, marker="s", linewidths=0)
    plt.axis("off")
    plt.gca().set_aspect("equal", adjustable="box")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
'''
    return textwrap.dedent(code)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Convert an image into Python code that draws it. "
            "If no image is specified, the newest image in this folder is used."
        )
    )
    parser.add_argument(
        "--image",
        "-i",
        help=(
            "Path to input image (any format Pillow supports). "
            "If omitted, the most recently modified image in the current folder is used."
        ),
    )
    parser.add_argument(
        "--out",
        "-o",
        default="sketch_draw.py",
        help="Output Python file that will contain the drawing code (default: sketch_draw.py)",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=160,
        help=(
            "Maximum width/height in pixels. Larger = more detail but bigger Python file. "
            "Used for sketch mode; color mode uses a smaller default internally."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["sketch", "color"],
        default="sketch",
        help="Choose 'sketch' (black-and-white edges) or 'color' (colored pixels).",
    )

    args = parser.parse_args()

    cwd = Path(".").resolve()

    if args.image:
        image_path = Path(args.image)
    else:
        image_path = find_latest_image(cwd)

    if not image_path.is_file():
        raise SystemExit(f"Input image not found: {image_path}")

    print(f"Using image: {image_path}")

    if args.mode == "sketch":
        (w, h), points = image_to_points_sketch(str(image_path), max_size=args.max_size)
        code = generate_python_code_sketch(w, h, points)
    else:
        # color mode: use a smaller size by default if user left max-size at default
        size = args.max_size if args.max_size != 160 else 80
        (w, h), points = image_to_points_color(str(image_path), max_size=size)
        code = generate_python_code_color(w, h, points)

    out_path = Path(args.out)
    out_path.write_text(code, encoding="utf-8")
    print(f"Generated Python file: {out_path}")
    print("Opening drawing window...")

    # Immediately run the generated script so the user sees the image.
    runpy.run_path(str(out_path))


if __name__ == "__main__":
    main()

