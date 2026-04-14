# 🐺 Hop Emote Generator

Turn any image into a bouncy animated GIF, perfect for Discord emotes.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python hop_emote.py my_image.png
```

Output: `my_image_hop.gif`

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `-o` | `<input>_hop.gif` | Output path |
| `--size` | `128` | Canvas size (px) |
| `--speed` | `0.7` | Cycle duration (s) |
| `--height` | `14` | Jump height (px) |
| `--angle` | `3.5` | Tilt angle (°) |

```bash
# Example: bigger, slower, bouncier
python hop_emote.py cat.png -o cat_emote.gif --size 128 --speed 1.0 --height 20 --angle 5
```

## Discord Upload

Server Settings → Emoji → Upload Emoji → pick your `.gif`

Max file size: 256 KB (the script keeps it small).
