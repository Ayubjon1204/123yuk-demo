import json
import socket
import threading
import time
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path

import uvicorn
from playwright.sync_api import sync_playwright
from scripts.serve_demo import DemoHandler

from app.config import Settings
from app.main import create_app
from app.parking import SNAPSHOT_AS_OF, DemoDataAdapter

REPO = Path(__file__).resolve().parents[2]


def test_zavod_widget_direct_route_accessibility_privacy_safe_render_and_reset():
    assert (REPO / "frontend/support-agent/widget.js").read_bytes() == (REPO / "zavod/ai-support/widget.js").read_bytes()
    handler = partial(DemoHandler, directory=str(REPO))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}/123yuk-demo"
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        api_port = probe.getsockname()[1]
    api = uvicorn.Server(uvicorn.Config(
        create_app(
            Settings("", "gemini-3.5-flash-lite", False, "2026-10-10T07:00:00Z", (f"http://127.0.0.1:{server.server_port}",)),
            DemoDataAdapter(SNAPSHOT_AS_OF),
        ),
        host="127.0.0.1", port=api_port, log_level="error", access_log=False,
    ))
    api_thread = threading.Thread(target=api.run, daemon=True)
    api_thread.start()
    try:
        deadline = time.monotonic() + 5
        while not api.started and time.monotonic() < deadline:
            time.sleep(0.01)
        assert api.started
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            xss = "<img src=x onerror=window.__widget_xss=1>"
            seen = []
            slow = False

            def fake_api(route):
                if slow:
                    time.sleep(0.4)
                    return
                seen.append(json.loads(route.request.post_data or "{}"))
                route.fulfill(status=200, content_type="application/json", body=json.dumps({
                    "message": xss,
                    "scope_status": "in_scope",
                    "ai_status": "disabled",
                    "mode": "demo",
                    "source": "none",
                    "evidence": [],
                }))

            page.route("**/api/v1/assistant/chat", fake_api)
            page.goto(f"{base}/zavod/dashboard/", wait_until="domcontentloaded")
            assert page.locator("yuk-support-widget").count() == 1
            page.add_style_tag(content=".launcher{display:none!important}")
            launcher = page.get_by_role("button", name="123YUK yordam chatini ochish")
            assert launcher.is_visible()
            launcher.click()
            dialog = page.get_by_role("dialog", name="123YUK yordam")
            assert dialog.is_visible()
            page.get_by_role("textbox", name="Xabaringiz").fill("test")
            page.keyboard.press("Enter")
            page.get_by_text("Lokal backend manzilini sozlang.", exact=False).wait_for()
            page.get_by_role("button", name="Suhbatni tozalash").click()
            page.evaluate("(url) => { document.querySelector('yuk-support-widget').apiBase = url }", base)
            page.get_by_role("textbox", name="Xabaringiz").fill("private-marker: parking")
            page.keyboard.press("Enter")
            page.get_by_text(xss, exact=True).wait_for()
            page.get_by_text("AI xizmati o‘chiq; lokal FAQ va parking hisoblari ishlaydi.", exact=True).wait_for()
            assert page.evaluate("window.__widget_xss || false") is False
            assert "<img" not in page.locator("yuk-support-widget").evaluate("el => el.shadowRoot.querySelector('.messages').innerHTML")
            assert seen[0]["message"] == "private-marker: parking"
            page.get_by_role("button", name="Suhbatni tozalash").click()
            assert page.locator("yuk-support-widget").evaluate("el => el.shadowRoot.querySelector('.messages').children.length") == 0

            page.unroute("**/api/v1/assistant/chat", fake_api)
            page.evaluate("(url) => { document.querySelector('yuk-support-widget').apiBase = url }", f"http://127.0.0.1:{api_port}")
            page.get_by_role("textbox", name="Xabaringiz").fill("Parkingda nechta avtomobil bor?")
            page.keyboard.press("Enter")
            page.get_by_text("Parkingda 14 ta demo avtomobil bor", exact=False).wait_for()

            slow = True
            page.route("**/api/v1/assistant/chat", fake_api)
            page.evaluate("""() => {
              const original = window.setTimeout.bind(window);
              window.setTimeout = (callback, ms, ...args) => original(callback, ms === 20000 ? 50 : ms, ...args);
            }""")
            page.get_by_role("textbox", name="Xabaringiz").fill("timeout-test")
            page.keyboard.press("Enter")
            page.get_by_text("So‘rov vaqti tugadi.", exact=False).wait_for(timeout=3000)

            page.add_script_tag(url=f"{base}/zavod/ai-support/widget.js")
            assert page.locator("yuk-support-widget").count() == 1
            page.set_viewport_size({"width": 375, "height": 667})
            page.get_by_role("button", name="123YUK yordam chatini ochish").click()
            box = page.get_by_role("dialog", name="123YUK yordam").bounding_box()
            assert box is not None and box["x"] >= 0 and box["y"] >= 0
            assert box["x"] + box["width"] <= 375
            assert box["y"] + box["height"] <= 667
            page.keyboard.press("Escape")
            assert not page.get_by_role("dialog", name="123YUK yordam").is_visible()
            browser.close()
    finally:
        api.should_exit = True
        api_thread.join(timeout=5)
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
