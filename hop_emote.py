"""
Hop Emote Generator
───────────────────
Takes any image and applies a left-right hop animation.
Outputs a 128x128 animated image ready for Discord emotes.

Supports GIF and APNG output. Use APNG (--format apng) for full color
and smooth transparency — no palette artifacts.

Usage:
    python hop_emote.py input.png
    python hop_emote.py input.png --format apng
    python hop_emote.py input.png -o output.gif --size 128 --speed 0.7
"""

import argparse
import math
import os
import sys
from PIL import Image


def make_frame(sprite: Image.Image, canvas_size: int, angle_deg: float, y_offset: int) -> Image.Image:
    """Create a single animation frame with the sprite rotated and offset."""
    sw, sh = sprite.size

    # Rotate around bottom-center
    rotated = sprite.rotate(
        -angle_deg,
        resample=Image.BICUBIC,
        expand=True,
        center=(sw // 2, sh),
    )

    # Place on canvas, centered horizontally, bottom-aligned with y_offset
    frame = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    rx, ry = rotated.size
    paste_x = (canvas_size - rx) // 2
    bottom_margin = max(6, int(canvas_size * 0.06))
    paste_y = canvas_size - ry - bottom_margin + y_offset
    frame.paste(rotated, (paste_x, paste_y), rotated)
    return frame


def generate_frames(
    input_path: str,
    canvas_size: int = 128,
    num_frames: int = 20,
    jump_height: int = 14,
    max_angle: float = 3.5,
) -> list[Image.Image]:
    """Generate all RGBA animation frames."""
    sprite = Image.open(input_path).convert("RGBA")

    # Scale sprite to fit inside the canvas with room for the jump
    max_sprite = int(canvas_size * 0.7)
    sprite.thumbnail((max_sprite, max_sprite), Image.LANCZOS)

    frames = []
    for i in range(num_frames):
        t = i / num_frames

        if t < 0.5:
            phase = t / 0.5
            y_offset = int(-abs(math.sin(phase * math.pi)) * jump_height)
            angle = max_angle * math.cos(phase * math.pi)
        else:
            phase = (t - 0.5) / 0.5
            y_offset = int(-abs(math.sin(phase * math.pi)) * jump_height)
            angle = -max_angle * math.cos(phase * math.pi)

        frames.append(make_frame(sprite, canvas_size, angle, y_offset))

    return frames


def save_gif(frames: list[Image.Image], output_path: str, frame_duration: int, canvas_size: int = 128):
    """Save frames as animated GIF (palette-based, 255 colors + transparency)."""
    gif_frames = []
    # Build a shared palette from all frames to avoid color shifts
    all_pixels = Image.new("RGBA", (canvas_size * len(frames), canvas_size))
    for i, f in enumerate(frames):
        all_pixels.paste(f, (i * canvas_size, 0))
    shared_palette = all_pixels.convert("RGB").quantize(colors=255, method=2)

    gif_frames = []
    for f in frames:
        alpha = f.getchannel("A")
        # Quantize using the shared palette for consistency
        p = f.convert("RGB").quantize(palette=shared_palette, dither=Image.Dither.FLOYDSTEINBERG)
        # Remap transparent pixels to index 255
        mask = Image.eval(alpha, lambda a: 255 if a < 128 else 0)
        p.paste(255, mask=mask)
        p.info["transparency"] = 255
        gif_frames.append(p)

    gif_frames[0].save(
        output_path,
        save_all=True,
        append_images=gif_frames[1:],
        duration=frame_duration,
        loop=0,
        disposal=2,
        transparency=255,
    )


def save_apng(frames: list[Image.Image], output_path: str, frame_duration: int):
    """Save frames as APNG (full RGBA, no color loss)."""
    from apng import APNG, PNG
    import io

    apng = APNG()
    for f in frames:
        buf = io.BytesIO()
        f.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        apng.append(PNG.from_bytes(buf.read()), delay=frame_duration)

    apng.save(output_path)


def main():
    parser = argparse.ArgumentParser(description="Generate a hopping emote from any image.")
    parser.add_argument("input", help="Path to input image (PNG, WebP, JPG, etc.)")
    parser.add_argument("-o", "--output", default=None, help="Output path (default: <input>_hop.<format>)")
    parser.add_argument("--format", choices=["gif", "apng"], default="gif",
                        help="Output format: gif (small, palette colors) or apng (full color, smooth transparency)")
    parser.add_argument("--size", type=int, default=128, help="Canvas size in px (default: 128)")
    parser.add_argument("--frames", type=int, default=20, help="Number of frames (default: 20)")
    parser.add_argument("--speed", type=float, default=0.7, help="Cycle duration in seconds (default: 0.7)")
    parser.add_argument("--height", type=int, default=14, help="Jump height in px (default: 14)")
    parser.add_argument("--angle", type=float, default=3.5, help="Max tilt angle in degrees (default: 3.5)")

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    ext = "png" if args.format == "apng" else "gif"
    output = args.output or f"{os.path.splitext(args.input)[0]}_hop.{ext}"

    frame_duration = int((args.speed * 1000) / args.frames)

    frames = generate_frames(
        input_path=args.input,
        canvas_size=args.size,
        num_frames=args.frames,
        jump_height=args.height,
        max_angle=args.angle,
    )

    if args.format == "apng":
        save_apng(frames, output, frame_duration)
    else:
        save_gif(frames, output, frame_duration, canvas_size=args.size)

    size_kb = os.path.getsize(output) / 1024
    fmt_label = "APNG" if args.format == "apng" else "GIF"
    print(f"Format:    {fmt_label}")
    print(f"Generated: {output}")
    print(f"Size:      {size_kb:.1f} KB {'(OK for Discord)' if size_kb < 256 else '(WARNING: over 256 KB Discord limit!)'}")
    print(f"Frames:    {args.frames} @ {frame_duration}ms each")
    print(f"Canvas:    {args.size}x{args.size}px")


if __name__ == "__main__":
    main()