import os, sys, threading, time, tempfile, shutil, subprocess, importlib.util
from pathlib import Path
from datetime import datetime, timedelta
from io import BytesIO

from flask import Flask, render_template, send_file, abort, jsonify, make_response, request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from camera import Camera

CSV_FILE   = (ROOT / "grow_tent_data.csv").resolve()
CONFIG_FILE= (ROOT / "config.py").resolve()
BACKUP_DIR = (ROOT / "config_backups")
BACKUP_DIR.mkdir(exist_ok=True)
CACHE_DIR  = (Path(__file__).resolve().parent / "cache")
CACHE_DIR.mkdir(exist_ok=True)

SNAPSHOT_INTERVAL = 30
GRAPH_INTERVAL    = 60
SNAPSHOT_SIZE     = (640, 480)
SNAPSHOT_QUALITY  = 75
DASHBOARD_HOURS   = 24
MAX_TAIL_LINES    = 4000

def tail_lines(path: Path, max_lines: int):
    try:
        with open(path, 'rb') as f:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            data = bytearray()
            lines = 0
            chunk = 1024
            while end > 0 and lines < max_lines:
                read_size = min(chunk, end)
                f.seek(end - read_size, os.SEEK_SET)
                buf = f.read(read_size)
                data[:0] = buf
                end -= read_size
                lines = data.count(b'\n')
            return data.decode('utf-8', errors='ignore').splitlines()[-max_lines:]
    except FileNotFoundError:
        return []

def parse_header(header_line: str):
    cols = [c.strip() for c in header_line.split(',')]
    return {name:i for i,name in enumerate(cols)}

def read_latest_from_csv():
    lines = tail_lines(CSV_FILE, 2)
    if len(lines) < 2:
        return None
    idx = parse_header(lines[0])
    last = lines[-1].split(',')
    def g(col):
        i = idx.get(col)
        if i is None or i >= len(last):
            return None
        return last[i]
    def fnum(x):
        try: return float(x)
        except: return None
    return {
        "timestamp": g("timestamp"),
        "temperature_c": fnum(g("temperature_c")),
        "humidity_pct": fnum(g("humidity_pct")),
        "pressure_hpa": fnum(g("pressure_hpa")),
        "gas_ohms": fnum(g("gas_ohms")),
        "relays": {k: (g(k) or "") for k in [
            "lights","air_pump","nutrient_pump","circ_fan1","circ_fan2",
            "exhaust_fan","humidifier","heater","dehumidifier"
        ]}
    }

def load_series(hours=DASHBOARD_HOURS):
    lines = tail_lines(CSV_FILE, MAX_TAIL_LINES)
    if not lines:
        return [], [], [], []
    idx = parse_header(lines[0])
    from datetime import datetime as _dt
    cutoff = _dt.now() - timedelta(hours=hours)
    ts, T, H, P = [], [], [], []
    for line in lines[1:]:
        parts = line.split(',')
        try:
            t = _dt.strptime(parts[idx["timestamp"]], "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        if t < cutoff:
            continue
        def f(col):
            try: return float(parts[idx[col]])
            except Exception: return None
        ts.append(t); T.append(f("temperature_c")); H.append(f("humidity_pct")); P.append(f("pressure_hpa"))
    return ts, T, H, P

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def render_graph_png(ts, ys, title, ylabel, outpath: Path):
    if not ts or not ys:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (800, 400), (255,255,255))
        d = ImageDraw.Draw(img)
        d.text((20,20), f"No data for {title}", fill=(0,0,0))
        img.save(outpath, "PNG")
        return
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(ts, ys)
    ax.set_title(f"{title} – last {DASHBOARD_HOURS}h")
    ax.set_xlabel("Time"); ax.set_ylabel(ylabel)
    fig.autofmt_xdate()
    fig.savefig(outpath, format="png", bbox_inches="tight")
    plt.close(fig)

def background_cache_worker():
    cam = None
    if Camera.available:
        try:
            cam = Camera()
        except Exception:
            cam = None
    t0 = 0; g0 = 0
    while True:
        now = time.time()
        if cam and now - t0 >= SNAPSHOT_INTERVAL:
            try:
                jpg = cam.capture_jpeg(size=SNAPSHOT_SIZE, quality=SNAPSHOT_QUALITY)
                tmp = CACHE_DIR / "snapshot.tmp"
                with open(tmp, "wb") as f: f.write(jpg)
                os.replace(tmp, CACHE_DIR / "snapshot.jpg")
            except Exception:
                pass
            t0 = now
        if now - g0 >= GRAPH_INTERVAL:
            try:
                ts, T, H, P = load_series(DASHBOARD_HOURS)
                render_graph_png(ts, T, "Temperature (°C)", "Temperature (°C)", CACHE_DIR / "graph_temperature_c.png")
                render_graph_png(ts, H, "Humidity (%)", "Humidity (%)", CACHE_DIR / "graph_humidity_pct.png")
                render_graph_png(ts, P, "Pressure (hPa)", "Pressure (hPa)", CACHE_DIR / "graph_pressure_hpa.png")
            except Exception:
                pass
            g0 = now
        time.sleep(0.5)

app = Flask(__name__, template_folder="templates", static_folder="static")

_worker_started = False
_worker_lock = threading.Lock()
def ensure_worker():
    global _worker_started
    with _worker_lock:
        if not _worker_started:
            th = threading.Thread(target=background_cache_worker, daemon=True)
            th.start()
            _worker_started = True

# Settings helpers
CONFIG_FIELDS = {
    "LIGHTS_ON_TIME":{"type":"str"}, "LIGHTS_OFF_TIME":{"type":"str"},
    "TEMP_THRESHOLD_EXHAUST_ON":{"type":"float"}, "TEMP_THRESHOLD_HEATER_ON":{"type":"float"},
    "HUMIDITY_HIGH_FOR_FANS":{"type":"float"}, "HUMIDITY_LOW_HUMIDIFIER":{"type":"float"},
    "HUMIDITY_HIGH_DEHUMIDIFIER":{"type":"float"},
    "AIR_OUT_TIMES":{"type":"list[str]"}, "AIR_OUT_DURATION":{"type":"int"},
    "CONTROL_INTERVAL":{"type":"int"},
    "ENABLE_LIGHTS":{"type":"bool"}, "ENABLE_AIR_PUMP":{"type":"bool"}, "ENABLE_NUTRIENT_PUMP":{"type":"bool"},
    "ENABLE_CIRC_FAN1":{"type":"bool"}, "ENABLE_CIRC_FAN2":{"type":"bool"}, "ENABLE_EXHAUST_FAN":{"type":"bool"},
    "ENABLE_HUMIDIFIER":{"type":"bool"}, "ENABLE_HEATER":{"type":"bool"}, "ENABLE_DEHUMIDIFIER":{"type":"bool"},
}
def _import_config_dict():
    spec = importlib.util.spec_from_file_location("config", CONFIG_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore
    return {k: getattr(mod, k) for k in dir(mod) if k.isupper()}
def _coerce(val, typ):
    if typ=="str": return str(val).strip()
    if typ=="int": return int(val)
    if typ=="float": return float(val)
    if typ=="bool":
        if isinstance(val,str): return val.lower() in ("1","true","on","yes")
        return bool(val)
    if typ=="list[str]": return [x.strip() for x in str(val).split(",") if x.strip()]
    raise ValueError(typ)
def _validate_config(incoming):
    out = {}
    for k, meta in CONFIG_FIELDS.items():
        if meta["type"]=="bool":
            out[k] = _coerce("on" if incoming.get(k) else "off","bool")
        else:
            if k not in incoming: raise ValueError(f"Missing field: {k}")
            out[k] = _coerce(incoming[k], meta["type"])
        if k in ("LIGHTS_ON_TIME","LIGHTS_OFF_TIME"):
            hhmm = out[k]; ok = len(hhmm)==5 and hhmm[2]==":"
            if not ok: raise ValueError(f"{k} must be HH:MM")
            h,m = hhmm.split(":")
            if not (0<=int(h)<=23 and 0<=int(m)<=59): raise ValueError(f"{k} out of range")
    return out
def _render_config(pyvals, original=None):
    if original is None: original = {}
    lines = []
    lines.append("# ==============================")
    lines.append("# Grow Tent Controller – config (generated by web UI)")
    lines.append("# ==============================\n")
    # keep pins & paths
    for k in ["LIGHTS_PIN","AIR_PUMP_PIN","NUTRIENT_PUMP_PIN","CIRCULATORY_FAN1_PIN","CIRCULATORY_FAN2_PIN",
              "EXHAUST_FAN_PIN","HUMIDIFIER_PIN","HEATER_PIN","DEHUMIDIFIER_PIN","SENSOR_I2C_BUSNUM",
              "CSV_PATH","LOG_PATH"]:
        if k in original: lines.append(f"{k} = {repr(original[k]) if isinstance(original[k], str) else original[k]}")
    lines.append(f"LIGHTS_ON_TIME  = {repr(pyvals['LIGHTS_ON_TIME'])}")
    lines.append(f"LIGHTS_OFF_TIME = {repr(pyvals['LIGHTS_OFF_TIME'])}")
    for k in ["TEMP_THRESHOLD_EXHAUST_ON","TEMP_THRESHOLD_HEATER_ON","HUMIDITY_HIGH_FOR_FANS",
              "HUMIDITY_LOW_HUMIDIFIER","HUMIDITY_HIGH_DEHUMIDIFIER","AIR_OUT_DURATION","CONTROL_INTERVAL"]:
        lines.append(f"{k} = {pyvals[k]}")
    lines.append("AIR_OUT_TIMES = " + repr(pyvals["AIR_OUT_TIMES"]))
    for k in ["ENABLE_LIGHTS","ENABLE_AIR_PUMP","ENABLE_NUTRIENT_PUMP","ENABLE_CIRC_FAN1","ENABLE_CIRC_FAN2",
              "ENABLE_EXHAUST_FAN","ENABLE_HUMIDIFIER","ENABLE_HEATER","ENABLE_DEHUMIDIFIER"]:
        lines.append(f"{k} = {bool(pyvals[k])}")
    return "\n".join(lines) + "\n"
def _atomic_write_config(new_text):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"config.py.{ts}.bak"
    shutil.copy2(CONFIG_FILE, backup)
    import tempfile, os
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(CONFIG_FILE.parent)) as tf:
        tf.write(new_text); tempname = tf.name
    os.replace(tempname, CONFIG_FILE)
    return str(backup)
def _try_restart():
    try:
        subprocess.check_call(["sudo","/bin/systemctl","restart","growtent.service"])
        return True, ""
    except Exception as e:
        return False, str(e)

@app.route("/")
def index():
    ensure_worker()
    latest = read_latest_from_csv()
    return render_template("index.html", latest=latest, cam_available=Camera.available)

@app.route("/api/stats")
def api_stats():
    latest = read_latest_from_csv()
    if latest is None: return jsonify({"ok": False, "error": "no data"}), 404
    return jsonify({"ok": True, "data": latest})

@app.route("/snapshot.jpg")
def snapshot():
    ensure_worker()
    target = CACHE_DIR / "snapshot.jpg"
    if not target.exists(): abort(503, description="No snapshot yet")
    resp = send_file(target, mimetype="image/jpeg")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp

@app.route("/graph/<metric>.png")
def graph(metric):
    ensure_worker()
    name_map = {"temperature_c":"Temperature (°C)","humidity_pct":"Humidity (%)","pressure_hpa":"Pressure (hPa)"}
    if metric not in name_map: abort(404)
    path = CACHE_DIR / f"graph_{metric}.png"
    if not path.exists():
        ts, T, H, P = load_series(DASHBOARD_HOURS)
        series = {"temperature_c":T,"humidity_pct":H,"pressure_hpa":P}[metric]
        render_graph_png(ts, series, name_map[metric], name_map[metric], path)
    resp = send_file(path, mimetype="image/png")
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp

@app.route("/settings", methods=["GET","POST"])
def settings():
    current = _import_config_dict()
    errors = []; saved = False; restarted = None
    if request.method == "POST":
        try:
            payload = _validate_config(request.form)
            new_text = _render_config(payload, original=current)
            backup = _atomic_write_config(new_text)
            saved = True
            if request.form.get("restart") == "1":
                ok, err = _try_restart(); restarted = ok
                if not ok: errors.append("Restart failed. Configure sudoers or restart manually.")
        except Exception as e:
            errors.append(str(e))
        current = _import_config_dict()
    editable = {k: current.get(k) for k in CONFIG_FIELDS.keys()}
    return render_template("settings.html", editable=editable, fields=CONFIG_FIELDS, saved=saved, errors=errors, restarted=restarted)

if __name__ == "__main__":
    ensure_worker()
    app.run(host="0.0.0.0", port=8000, debug=True)
