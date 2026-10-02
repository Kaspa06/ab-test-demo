from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json
import math
import mimetypes
import random
import sqlite3
import uuid

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "ab_test.db"
HOST = "127.0.0.1"
PORT = 5000


def db_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS visitors (
                user_id TEXT PRIMARY KEY,
                variant TEXT NOT NULL CHECK(variant IN ('A', 'B')),
                source TEXT NOT NULL DEFAULT 'real',
                persona TEXT,
                viewed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                clicked INTEGER NOT NULL DEFAULT 0,
                clicked_at DATETIME
            )
            """
        )
        conn.commit()


def get_or_create_visitor(user_id=None, source="real", persona=None):
    if user_id:
        with db_conn() as conn:
            row = conn.execute("SELECT * FROM visitors WHERE user_id = ?", (user_id,)).fetchone()
            if row:
                return row

    user_id = user_id or str(uuid.uuid4())
    variant = random.choice(["A", "B"])
    with db_conn() as conn:
        conn.execute(
            "INSERT INTO visitors (user_id, variant, source, persona) VALUES (?, ?, ?, ?)",
            (user_id, variant, source, persona),
        )
        conn.commit()
        return conn.execute("SELECT * FROM visitors WHERE user_id = ?", (user_id,)).fetchone()


def normal_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def stats_for(a_n, a_c, b_n, b_c):
    a_rate = a_c / a_n if a_n else 0.0
    b_rate = b_c / b_n if b_n else 0.0
    diff = b_rate - a_rate
    lift = diff / a_rate if a_rate > 0 else None
    p_value = z = ci_low = ci_high = None

    if a_n > 0 and b_n > 0:
        se_ci = math.sqrt((a_rate * (1 - a_rate) / a_n) + (b_rate * (1 - b_rate) / b_n))
        if se_ci > 0:
            ci_low = diff - 1.96 * se_ci
            ci_high = diff + 1.96 * se_ci

        pooled = (a_c + b_c) / (a_n + b_n)
        se_test = math.sqrt(pooled * (1 - pooled) * (1 / a_n + 1 / b_n))
        if se_test > 0:
            z = diff / se_test
            p_value = 2 * (1 - normal_cdf(abs(z)))

    return {
        "a": {"visitors": a_n, "clicks": a_c, "rate": a_rate},
        "b": {"visitors": b_n, "clicks": b_c, "rate": b_rate},
        "difference": diff,
        "relative_lift": lift,
        "z_score": z,
        "p_value": p_value,
        "ci95": {"low": ci_low, "high": ci_high},
        "significant_05": bool(p_value is not None and p_value < 0.05),
    }


def results_payload():
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT variant, COUNT(*) AS visitors, SUM(clicked) AS clicks FROM visitors GROUP BY variant"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) AS n FROM visitors").fetchone()["n"]
        by_source = conn.execute(
            "SELECT source, COUNT(*) AS visitors, SUM(clicked) AS clicks FROM visitors GROUP BY source ORDER BY visitors DESC"
        ).fetchall()

    values = {"A": (0, 0), "B": (0, 0)}
    for row in rows:
        values[row["variant"]] = (row["visitors"], row["clicks"] or 0)

    payload = stats_for(values["A"][0], values["A"][1], values["B"][0], values["B"][1])
    payload["total_visitors"] = total
    payload["sources"] = [dict(r) for r in by_source]
    return payload


class Handler(BaseHTTPRequestHandler):
    server_version = "ABDemo/1.0"

    def log_message(self, fmt, *args):
        pass

    def send_bytes(self, data, content_type="text/plain; charset=utf-8", status=200, extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def send_text(self, text, content_type="text/html; charset=utf-8", status=200, extra_headers=None):
        self.send_bytes(text.encode("utf-8"), content_type, status, extra_headers)

    def send_json(self, obj, status=200, extra_headers=None):
        self.send_text(json.dumps(obj), "application/json; charset=utf-8", status, extra_headers)

    def cookie_user_id(self):
        raw = self.headers.get("Cookie")
        if not raw:
            return None
        cookie = SimpleCookie()
        cookie.load(raw)
        morsel = cookie.get("ab_user_id")
        return morsel.value if morsel else None

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            source = query.get("source", ["real"])[0]
            persona = query.get("persona", [None])[0]
            row = get_or_create_visitor(self.cookie_user_id(), source, persona)
            template = (APP_DIR / "templates" / "landing.html").read_text(encoding="utf-8")
            cta = "Learn more" if row["variant"] == "A" else "Start free trial"
            html = template.replace("{{CTA}}", cta).replace("{{VARIANT}}", row["variant"])
            headers = {
                "Set-Cookie": f"ab_user_id={row['user_id']}; Path=/; Max-Age=2592000; SameSite=Lax",
                "X-AB-Variant": row["variant"],
            }
            return self.send_text(html, extra_headers=headers)

        if path == "/dashboard":
            html = (APP_DIR / "templates" / "dashboard.html").read_text(encoding="utf-8")
            return self.send_text(html)

        if path == "/api/results":
            return self.send_json(results_payload())

        if path.startswith("/static/"):
            target = (APP_DIR / path.lstrip("/")).resolve()
            static_root = (APP_DIR / "static").resolve()
            if static_root not in target.parents or not target.exists() or not target.is_file():
                return self.send_text("Not found", "text/plain; charset=utf-8", 404)
            content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            return self.send_bytes(target.read_bytes(), content_type)

        return self.send_text("Not found", "text/plain; charset=utf-8", 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", "0"))
        if length:
            self.rfile.read(length)

        if path == "/api/click":
            user_id = self.cookie_user_id()
            if not user_id:
                return self.send_json({"ok": False, "error": "No experiment user cookie"}, 400)
            with db_conn() as conn:
                row = conn.execute("SELECT * FROM visitors WHERE user_id = ?", (user_id,)).fetchone()
                if not row:
                    return self.send_json({"ok": False, "error": "Unknown visitor"}, 404)
                if not row["clicked"]:
                    conn.execute(
                        "UPDATE visitors SET clicked = 1, clicked_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                        (user_id,),
                    )
                    conn.commit()
            return self.send_json({"ok": True})

        if path == "/api/reset":
            with db_conn() as conn:
                conn.execute("DELETE FROM visitors")
                conn.commit()
            return self.send_json({"ok": True})

        return self.send_text("Not found", "text/plain; charset=utf-8", 404)


def main():
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"A/B demo running: http://{HOST}:{PORT}")
    print(f"Dashboard:        http://{HOST}:{PORT}/dashboard")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
