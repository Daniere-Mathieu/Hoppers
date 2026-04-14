"""
Hop Emote Generator
───────────────────
Takes any image and applies a left-right hop animation.
Outputs a 128x128 animated GIF ready for Discord emotes.

Usage:
    python hop_emote.py input.png
    python hop_emote.py input.png -o output.gif
    python hop_emote.py input.png --size 64 --speed 0.6 --height 14 --angle 3.5
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


def generate_hop_gif(
    input_path: str,
    output_path: str,
    canvas_size: int = 128,
    num_frames: int = 20,
    jump_height: int = 14,
    max_angle: float = 3.5,
    cycle_duration: float = 0.7,
):
    """Generate an animated hopping GIF from any input image."""

    # Load and prepare sprite
    sprite = Image.open(input_path).convert("RGBA")

    # Scale sprite to fit inside the canvas with some room for the jump
    max_sprite = int(canvas_size * 0.7)
    sprite.thumbnail((max_sprite, max_sprite), Image.LANCZOS)

    # Generate frames
    frames = []
    for i in range(num_frames):
        t = i / num_frames  # 0..1

        # Two hops per cycle: right tilt then left tilt
        if t < 0.5:
            phase = t / 0.5
            y_offset = int(-abs(math.sin(phase * math.pi)) * jump_height)
            angle = max_angle * math.cos(phase * math.pi)
        else:
            phase = (t - 0.5) / 0.5
            y_offset = int(-abs(math.sin(phase * math.pi)) * jump_height)
            angle = -max_angle * math.cos(phase * math.pi)

        frames.append(make_frame(sprite, canvas_size, angle, y_offset))

    # Convert RGBA to palette mode with transparency for GIF
    gif_frames = []
    for f in frames:
        alpha = f.getchannel("A")
        p = f.convert("RGB").quantize(colors=128, method=2)
        mask = Image.eval(alpha, lambda a: 255 if a < 128 else 0)
        p.paste(0, mask=mask)
        p.info["transparency"] = 0
        gif_frames.append(p)

    # Frame duration in ms
    frame_duration = int((cycle_duration * 1000) / num_frames)

    # Save
    gif_frames[0].save(
        output_path,
        save_all=True,
        append_images=gif_frames[1:],
        duration=frame_duration,
        loop=0,
        disposal=2,
        transparency=0,
    )

    size_kb = os.path.getsize(output_path) / 1024
    print(f"Generated: {output_path}")
    print(f"Size:      {size_kb:.1f} KB {'(OK for Discord)' if size_kb < 256 else '(WARNING: over 256 KB Discord limit!)'}")
    print(f"Frames:    {num_frames} @ {frame_duration}ms each")
    print(f"Canvas:    {canvas_size}x{canvas_size}px")


def main():
    parser = argparse.ArgumentParser(description="Generate a hopping emote GIF from any image.")
    parser.add_argument("input", help="Path to input image (PNG, WebP, JPG, etc.)")
    parser.add_argument("-o", "--output", default=None, help="Output GIF path (default: <input>_hop.gif)")
    parser.add_argument("--size", type=int, default=128, help="Canvas size in px (default: 128)")
    parser.add_argument("--frames", type=int, default=20, help="Number of frames (default: 20)")
    parser.add_argument("--speed", type=float, default=0.7, help="Cycle duration in seconds (default: 0.7)")
    parser.add_argument("--height", type=int, default=14, help="Jump height in px (default: 14)")
    parser.add_argument("--angle", type=float, default=3.5, help="Max tilt angle in degrees (default: 3.5)")

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    output = args.output or os.path.splitext(args.input)[0] + "_hop.gif"

    generate_hop_gif(
        input_path=args.input,
        output_path=output,
        canvas_size=args.size,
        num_frames=args.frames,
        jump_height=args.height,
        max_angle=args.angle,
        cycle_duration=args.speed,
    )


if __name__ == "__main__":
    main()
