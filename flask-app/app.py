from __future__ import annotations
from flask import Flask, render_template, send_file, redirect, url_for, request, flash
from pathlib import Path
from datetime import datetime
from .config import SECRET_KEY, DEBUG, CAPTURE_DIR, LOG_FILE, TL_ACTIVE_FLAG
from .utils import read_latest_states, now_str
from .camera import capture_still, snapshot_path
from .timelapse import TL

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY

    # start timelapse thread once
    if not TL.is_alive():
        TL.start()

    @app.route("/")
    def index():
        states = read_latest_states(LOG_FILE)
        days = sorted([p.name for p in CAPTURE_DIR.glob("*") if p.is_dir()], reverse=True)[:10]
        latest = sorted(CAPTURE_DIR.glob("**/*.jpg"), reverse=True)
        latest_path = latest[0] if latest else None
        return render_template("index.html",
                               states=states,
                               latest_image=latest_path.name if latest_path else None,
                               latest_dir=str(latest_path.parent.relative_to(CAPTURE_DIR)) if latest_path else None,
                               days=days,
                               timelapse_on=TL_ACTIVE_FLAG.exists(),
                               now=now_str())

    @app.route("/snapshot")
    def snapshot():
        out = snapshot_path()
        capture_still(out)
        return send_file(out, mimetype="image/jpeg")

    @app.route("/image/<day>/<filename>")
    def image(day, filename):
        path = CAPTURE_DIR / day / filename
        if not path.exists():
            return "Not found", 404
        return send_file(path, mimetype="image/jpeg")

    @app.post("/timelapse/toggle")
    def toggle_timelapse():
        if TL_ACTIVE_FLAG.exists():
            TL_ACTIVE_FLAG.unlink(missing_ok=True)
            flash("Timelapse stopped.", "info")
        else:
            TL_ACTIVE_FLAG.touch()
            flash("Timelapse started.", "success")
        return redirect(url_for("index"))

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
