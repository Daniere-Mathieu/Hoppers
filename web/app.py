"""
Hop Emote Generator – Web UI
─────────────────────────────
Flask backend that wraps hop_emote.py and serves a single-page interface.

Run:  python web/app.py          (from the project root)
      python -m web.app          (alternative)
"""

import atexit
import base64
import glob
import os
import sys
import tempfile
import time

from flask import Flask, jsonify, render_template, request

# Import the core generator from the parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from hop_emote import ANIMATION_TYPES, GENERATORS, save_apng, save_gif  # noqa: E402

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB

# Dedicated temp directory – isolated from system tmp, easy to mount as volume
TEMP_DIR = os.environ.get("HOPPERS_TMP") or os.path.join(tempfile.gettempdir(), "hoppers")
os.makedirs(TEMP_DIR, exist_ok=True)

# Stale file cleanup: delete temp files older than this (seconds)
TEMP_MAX_AGE = int(os.environ.get("HOPPERS_TMP_MAX_AGE", 300))  # 5 min default

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff"}
MAX_FILES = 20

# Parameter bounds: (min, max, default)
PARAM_BOUNDS = {
    "size":   (32,  512,  128),
    "frames": (4,   60,   20),
    "speed":  (0.1, 3.0,  0.7),
    "height": (0,   64,   14),
    "angle":  (0.0, 15.0, 3.5),
}


def purge_stale_temp_files():
    """Remove temp files older than TEMP_MAX_AGE to prevent storage leaks."""
    now = time.time()
    for path in glob.glob(os.path.join(TEMP_DIR, "hop_*")):
        try:
            if now - os.path.getmtime(path) > TEMP_MAX_AGE:
                os.unlink(path)
        except OSError:
            pass


def cleanup_all_temp_files():
    """Remove all temp files on shutdown."""
    for path in glob.glob(os.path.join(TEMP_DIR, "hop_*")):
        try:
            os.unlink(path)
        except OSError:
            pass


atexit.register(cleanup_all_temp_files)


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_params(form) -> dict:
    """Extract and validate generation parameters from form data."""
    fmt = form.get("format", "gif")
    if fmt not in ("gif", "apng"):
        fmt = "gif"

    animation = form.get("animation", "hop")
    if animation not in ANIMATION_TYPES:
        animation = "hop"

    size = clamp(int(form.get("size", 128)), *PARAM_BOUNDS["size"][:2])
    frames = clamp(int(form.get("frames", 20)), *PARAM_BOUNDS["frames"][:2])
    speed = clamp(float(form.get("speed", 0.7)), *PARAM_BOUNDS["speed"][:2])
    height = clamp(int(form.get("height", 14)), *PARAM_BOUNDS["height"][:2])
    angle = clamp(float(form.get("angle", 3.5)), *PARAM_BOUNDS["angle"][:2])

    return dict(fmt=fmt, animation=animation, size=size, frames=frames, speed=speed, height=height, angle=angle)


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/app")
def generator():
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def generate():
    files = request.files.getlist("files[]")
    files = [f for f in files if f.filename]

    if not files:
        return jsonify({"error": "No files uploaded"}), 400
    if len(files) > MAX_FILES:
        return jsonify({"error": f"Too many files (max {MAX_FILES})"}), 400

    try:
        params = parse_params(request.form)
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid parameter: {e}"}), 400

    frame_duration = int((params["speed"] * 1000) / params["frames"])
    results = []

    # Purge stale temp files from previous requests (crash recovery)
    purge_stale_temp_files()

    for f in files:
        if not allowed_file(f.filename):
            results.append({"filename": f.filename, "error": "Unsupported file type"})
            continue

        suffix = os.path.splitext(f.filename)[1] or ".png"
        tmp_in_path = None
        tmp_out_path = None

        try:
            # Save upload to temp file (Pillow needs a path)
            with tempfile.NamedTemporaryFile(
                suffix=suffix, delete=False, dir=TEMP_DIR, prefix="hop_in_"
            ) as tmp_in:
                f.save(tmp_in)
                tmp_in_path = tmp_in.name

            out_ext = ".png" if params["fmt"] == "apng" else ".gif"
            with tempfile.NamedTemporaryFile(
                suffix=out_ext, delete=False, dir=TEMP_DIR, prefix="hop_out_"
            ) as tmp_out:
                tmp_out_path = tmp_out.name

            # Generate animation
            generator = GENERATORS[params["animation"]]
            anim_frames = generator(
                input_path=tmp_in_path,
                canvas_size=params["size"],
                num_frames=params["frames"],
                jump_height=params["height"],
                max_angle=params["angle"],
            )

            if params["fmt"] == "apng":
                save_apng(anim_frames, tmp_out_path, frame_duration)
                content_type = "image/png"
            else:
                save_gif(anim_frames, tmp_out_path, frame_duration, canvas_size=params["size"])
                content_type = "image/gif"

            with open(tmp_out_path, "rb") as out_f:
                data = base64.b64encode(out_f.read()).decode("ascii")

            size_kb = os.path.getsize(tmp_out_path) / 1024
            base_name = os.path.splitext(f.filename)[0]
            out_filename = f"{base_name}_{params['animation']}{out_ext}"

            results.append({
                "filename": out_filename,
                "data": data,
                "content_type": content_type,
                "size_kb": round(size_kb, 1),
            })

        except Exception as e:
            results.append({"filename": f.filename, "error": str(e)})

        finally:
            if tmp_in_path and os.path.exists(tmp_in_path):
                os.unlink(tmp_in_path)
            if tmp_out_path and os.path.exists(tmp_out_path):
                os.unlink(tmp_out_path)

    return jsonify({"results": results})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
