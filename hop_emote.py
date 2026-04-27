"""
Hop Emote Generator
───────────────────
Takes any image and applies an animation.
Outputs an animated image ready for Discord emotes.

Supports GIF and APNG output. Use APNG (--format apng) for full color
and smooth transparency — no palette artifacts.

Usage:
    python hop_emote.py input.png
    python hop_emote.py input.png --animation spin
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
    **_kwargs,
) -> list[Image.Image]:
    """Generate all RGBA animation frames for the hop animation."""
    sprite = Image.open(input_path).convert("RGBA")

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


ANIMATION_TYPES = [
    "hop", "spin", "shake", "bounce", "pulse",
    "swing", "jelly", "float", "zoom", "slide", "flip", "twist",
    "custom",
]


def _load_sprite(input_path: str, canvas_size: int, scale: float = 0.7) -> Image.Image:
    sprite = Image.open(input_path).convert("RGBA")
    max_sprite = int(canvas_size * scale)
    sprite.thumbnail((max_sprite, max_sprite), Image.LANCZOS)
    return sprite


def generate_frames_spin(
    input_path: str,
    canvas_size: int = 128,
    num_frames: int = 20,
    **_kwargs,
) -> list[Image.Image]:
    """Full 360-degree rotation around the center."""
    sprite = _load_sprite(input_path, canvas_size)
    sw, sh = sprite.size

    frames = []
    for i in range(num_frames):
        angle = (i / num_frames) * 360.0
        rotated = sprite.rotate(
            -angle,
            resample=Image.BICUBIC,
            expand=True,
            center=(sw // 2, sh // 2),
        )
        frame = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        rx, ry = rotated.size
        paste_x = (canvas_size - rx) // 2
        paste_y = (canvas_size - ry) // 2
        frame.paste(rotated, (paste_x, paste_y), rotated)
        frames.append(frame)

    return frames


def generate_frames_shake(
    input_path: str,
    canvas_size: int = 128,
    num_frames: int = 20,
    intensity: int = 6,
    **_kwargs,
) -> list[Image.Image]:
    """Rapid horizontal shaking — like a vibrating notification."""
    sprite = _load_sprite(input_path, canvas_size)
    sw, sh = sprite.size

    frames = []
    for i in range(num_frames):
        t = i / num_frames
        x_offset = int(math.sin(t * math.pi * 6) * intensity)

        frame = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        paste_x = (canvas_size - sw) // 2 + x_offset
        bottom_margin = max(6, int(canvas_size * 0.06))
        paste_y = canvas_size - sh - bottom_margin
        frame.paste(sprite, (paste_x, paste_y), sprite)
        frames.append(frame)

    return frames


def generate_frames_bounce(
    input_path: str,
    canvas_size: int = 128,
    num_frames: int = 20,
    jump_height: int = 20,
    squash: float = 0.3,
    **_kwargs,
) -> list[Image.Image]:
    """Vertical bounce with squash-and-stretch on landing."""
    sprite = _load_sprite(input_path, canvas_size)
    sw, sh = sprite.size

    frames = []
    for i in range(num_frames):
        t = i / num_frames
        bounce_val = abs(math.sin(t * math.pi))
        y_offset = int(-bounce_val * jump_height)

        landing_proximity = 1.0 - bounce_val
        squash_factor = 1.0 + squash * (landing_proximity ** 3)
        stretch_factor = 1.0 / squash_factor

        new_w = max(1, int(sw * squash_factor))
        new_h = max(1, int(sh * stretch_factor))
        squashed = sprite.resize((new_w, new_h), Image.LANCZOS)

        frame = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        paste_x = (canvas_size - new_w) // 2
        bottom_margin = max(6, int(canvas_size * 0.06))
        paste_y = canvas_size - new_h - bottom_margin + y_offset
        frame.paste(squashed, (paste_x, paste_y), squashed)
        frames.append(frame)

    return frames


def generate_frames_pulse(
    input_path: str,
    canvas_size: int = 128,
    num_frames: int = 20,
    scale_amount: float = 0.2,
    **_kwargs,
) -> list[Image.Image]:
    """Rhythmic scale-up / scale-down heartbeat effect."""
    sprite = _load_sprite(input_path, canvas_size, scale=0.55)
    sw, sh = sprite.size

    frames = []
    for i in range(num_frames):
        t = i / num_frames
        scale = 1.0 + scale_amount * abs(math.sin(t * math.pi))

        new_w = max(1, int(sw * scale))
        new_h = max(1, int(sh * scale))
        scaled = sprite.resize((new_w, new_h), Image.LANCZOS)

        frame = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        paste_x = (canvas_size - new_w) // 2
        paste_y = (canvas_size - new_h) // 2
        frame.paste(scaled, (paste_x, paste_y), scaled)
        frames.append(frame)

    return frames


def generate_frames_swing(
    input_path: str,
    canvas_size: int = 128,
    num_frames: int = 20,
    max_angle: float = 15.0,
    **_kwargs,
) -> list[Image.Image]:
    """Pendulum swing from a top-center pivot point."""
    sprite = _load_sprite(input_path, canvas_size)
    sw, sh = sprite.size

    frames = []
    for i in range(num_frames):
        t = i / num_frames
        angle = max_angle * math.sin(t * 2 * math.pi)
        rotated = sprite.rotate(
            -angle,
            resample=Image.BICUBIC,
            expand=True,
            center=(sw // 2, 0),
        )
        frame = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        rx, ry = rotated.size
        paste_x = (canvas_size - rx) // 2
        paste_y = max(2, (canvas_size - ry) // 4)
        frame.paste(rotated, (paste_x, paste_y), rotated)
        frames.append(frame)

    return frames


def generate_frames_jelly(
    input_path: str,
    canvas_size: int = 128,
    num_frames: int = 20,
    intensity: float = 0.15,
    **_kwargs,
) -> list[Image.Image]:
    """Wobbly jelly deformation — alternating X/Y squash."""
    sprite = _load_sprite(input_path, canvas_size)
    sw, sh = sprite.size

    frames = []
    for i in range(num_frames):
        t = i / num_frames
        sx = 1.0 + intensity * math.sin(t * 2 * math.pi)
        sy = 1.0 - intensity * math.sin(t * 2 * math.pi)

        new_w = max(1, int(sw * sx))
        new_h = max(1, int(sh * sy))
        deformed = sprite.resize((new_w, new_h), Image.LANCZOS)

        frame = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        paste_x = (canvas_size - new_w) // 2
        bottom_margin = max(6, int(canvas_size * 0.06))
        paste_y = canvas_size - new_h - bottom_margin
        frame.paste(deformed, (paste_x, paste_y), deformed)
        frames.append(frame)

    return frames


def generate_frames_float(
    input_path: str,
    canvas_size: int = 128,
    num_frames: int = 20,
    amplitude: int = 10,
    **_kwargs,
) -> list[Image.Image]:
    """Gentle floating up and down — dreamy hover effect."""
    sprite = _load_sprite(input_path, canvas_size)
    sw, sh = sprite.size

    frames = []
    for i in range(num_frames):
        t = i / num_frames
        y_offset = int(amplitude * math.sin(t * 2 * math.pi))

        frame = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        paste_x = (canvas_size - sw) // 2
        paste_y = (canvas_size - sh) // 2 + y_offset
        frame.paste(sprite, (paste_x, paste_y), sprite)
        frames.append(frame)

    return frames


def generate_frames_zoom(
    input_path: str,
    canvas_size: int = 128,
    num_frames: int = 20,
    scale_amount: float = 0.5,
    **_kwargs,
) -> list[Image.Image]:
    """Zoom in from small to full size and back."""
    sprite = _load_sprite(input_path, canvas_size, scale=0.5)
    sw, sh = sprite.size

    frames = []
    for i in range(num_frames):
        t = i / num_frames
        scale = (1.0 - scale_amount) + scale_amount * abs(math.sin(t * math.pi))

        new_w = max(1, int(sw * (1.0 + scale)))
        new_h = max(1, int(sh * (1.0 + scale)))
        scaled = sprite.resize((new_w, new_h), Image.LANCZOS)

        frame = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        paste_x = (canvas_size - new_w) // 2
        paste_y = (canvas_size - new_h) // 2
        frame.paste(scaled, (paste_x, paste_y), scaled)
        frames.append(frame)

    return frames


def generate_frames_slide(
    input_path: str,
    canvas_size: int = 128,
    num_frames: int = 20,
    distance: int = 20,
    **_kwargs,
) -> list[Image.Image]:
    """Slide left and right in a smooth loop."""
    sprite = _load_sprite(input_path, canvas_size)
    sw, sh = sprite.size

    frames = []
    for i in range(num_frames):
        t = i / num_frames
        x_offset = int(distance * math.sin(t * 2 * math.pi))

        frame = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        paste_x = (canvas_size - sw) // 2 + x_offset
        bottom_margin = max(6, int(canvas_size * 0.06))
        paste_y = canvas_size - sh - bottom_margin
        frame.paste(sprite, (paste_x, paste_y), sprite)
        frames.append(frame)

    return frames


def generate_frames_flip(
    input_path: str,
    canvas_size: int = 128,
    num_frames: int = 20,
    **_kwargs,
) -> list[Image.Image]:
    """Horizontal flip — simulated 3D card-flip via X-axis squash."""
    sprite = _load_sprite(input_path, canvas_size)
    sw, sh = sprite.size

    frames = []
    for i in range(num_frames):
        t = i / num_frames
        scale_x = abs(math.cos(t * 2 * math.pi))
        scale_x = max(0.05, scale_x)

        new_w = max(1, int(sw * scale_x))
        squished = sprite.resize((new_w, sh), Image.LANCZOS)

        frame = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        paste_x = (canvas_size - new_w) // 2
        bottom_margin = max(6, int(canvas_size * 0.06))
        paste_y = canvas_size - sh - bottom_margin
        frame.paste(squished, (paste_x, paste_y), squished)
        frames.append(frame)

    return frames


def generate_frames_twist(
    input_path: str,
    canvas_size: int = 128,
    num_frames: int = 20,
    max_angle: float = 25.0,
    **_kwargs,
) -> list[Image.Image]:
    """Twist back and forth with a slight vertical bounce."""
    sprite = _load_sprite(input_path, canvas_size)
    sw, sh = sprite.size

    frames = []
    for i in range(num_frames):
        t = i / num_frames
        angle = max_angle * math.sin(t * 2 * math.pi)
        y_offset = int(-6 * abs(math.sin(t * 2 * math.pi)))

        rotated = sprite.rotate(
            -angle,
            resample=Image.BICUBIC,
            expand=True,
            center=(sw // 2, sh // 2),
        )
        frame = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        rx, ry = rotated.size
        paste_x = (canvas_size - rx) // 2
        paste_y = (canvas_size - ry) // 2 + y_offset
        frame.paste(rotated, (paste_x, paste_y), rotated)
        frames.append(frame)

    return frames


def generate_frames_custom(
    input_path: str,
    canvas_size: int = 128,
    num_frames: int = 20,
    move_x: int = 0,
    move_y: int = 0,
    rotation: float = 0.0,
    scale_amount: float = 0.0,
    cycles: int = 1,
    **_kwargs,
) -> list[Image.Image]:
    """User-defined animation loop with configurable X/Y, rotation, scale, and cycles."""
    base_scale = 0.55 if (abs(scale_amount) > 0.01) else 0.7
    sprite = _load_sprite(input_path, canvas_size, scale=base_scale)
    sw, sh = sprite.size

    frames = []
    for i in range(num_frames):
        t = i / num_frames
        phase = t * cycles * 2 * math.pi

        x_off = int(move_x * math.sin(phase))
        y_off = int(move_y * math.sin(phase))

        cur_angle = rotation * math.sin(phase)

        cur_scale = 1.0 + scale_amount * abs(math.sin(phase))
        new_w = max(1, int(sw * cur_scale))
        new_h = max(1, int(sh * cur_scale))
        scaled = sprite.resize((new_w, new_h), Image.LANCZOS)

        if abs(cur_angle) > 0.01:
            scaled = scaled.rotate(
                -cur_angle,
                resample=Image.BICUBIC,
                expand=True,
                center=(new_w // 2, new_h // 2),
            )
            new_w, new_h = scaled.size

        frame = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        paste_x = (canvas_size - new_w) // 2 + x_off
        paste_y = (canvas_size - new_h) // 2 + y_off
        frame.paste(scaled, (paste_x, paste_y), scaled)
        frames.append(frame)

    return frames


GENERATORS = {
    "hop": generate_frames,
    "spin": generate_frames_spin,
    "shake": generate_frames_shake,
    "bounce": generate_frames_bounce,
    "pulse": generate_frames_pulse,
    "swing": generate_frames_swing,
    "jelly": generate_frames_jelly,
    "float": generate_frames_float,
    "zoom": generate_frames_zoom,
    "slide": generate_frames_slide,
    "flip": generate_frames_flip,
    "twist": generate_frames_twist,
    "custom": generate_frames_custom,
}


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
    parser = argparse.ArgumentParser(description="Generate an animated emote from any image.")
    parser.add_argument("input", help="Path to input image (PNG, WebP, JPG, etc.)")
    parser.add_argument("-o", "--output", default=None, help="Output path (default: <input>_<animation>.<format>)")
    parser.add_argument("--animation", choices=ANIMATION_TYPES, default="hop",
                        help="Animation type (default: hop)")
    parser.add_argument("--format", choices=["gif", "apng"], default="gif",
                        help="Output format: gif (small, palette colors) or apng (full color, smooth transparency)")
    parser.add_argument("--size", type=int, default=128, help="Canvas size in px (default: 128)")
    parser.add_argument("--frames", type=int, default=20, help="Number of frames (default: 20)")
    parser.add_argument("--speed", type=float, default=0.7, help="Cycle duration in seconds (default: 0.7)")
    parser.add_argument("--height", type=int, default=14, help="Jump height in px (default: 14)")
    parser.add_argument("--angle", type=float, default=3.5, help="Max tilt angle in degrees (default: 3.5)")
    parser.add_argument("--move-x", type=int, default=0, help="Custom: horizontal movement amplitude in px")
    parser.add_argument("--move-y", type=int, default=0, help="Custom: vertical movement amplitude in px")
    parser.add_argument("--rotation", type=float, default=0.0, help="Custom: rotation amplitude in degrees")
    parser.add_argument("--scale-amount", type=float, default=0.0, help="Custom: scale oscillation amount (0-1)")
    parser.add_argument("--cycles", type=int, default=1, help="Custom: number of loops per animation cycle")

    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Error: file not found: {args.input}")
        sys.exit(1)

    ext = "png" if args.format == "apng" else "gif"
    output = args.output or f"{os.path.splitext(args.input)[0]}_{args.animation}.{ext}"

    frame_duration = int((args.speed * 1000) / args.frames)

    generator = GENERATORS[args.animation]
    frames = generator(
        input_path=args.input,
        canvas_size=args.size,
        num_frames=args.frames,
        jump_height=args.height,
        max_angle=args.angle,
        move_x=args.move_x,
        move_y=args.move_y,
        rotation=args.rotation,
        scale_amount=args.scale_amount,
        cycles=args.cycles,
    )

    if args.format == "apng":
        save_apng(frames, output, frame_duration)
    else:
        save_gif(frames, output, frame_duration, canvas_size=args.size)

    size_kb = os.path.getsize(output) / 1024
    fmt_label = "APNG" if args.format == "apng" else "GIF"
    print(f"Animation: {args.animation}")
    print(f"Format:    {fmt_label}")
    print(f"Generated: {output}")
    print(f"Size:      {size_kb:.1f} KB {'(OK for Discord)' if size_kb < 256 else '(WARNING: over 256 KB Discord limit!)'}")
    print(f"Frames:    {args.frames} @ {frame_duration}ms each")
    print(f"Canvas:    {args.size}x{args.size}px")


if __name__ == "__main__":
    main()