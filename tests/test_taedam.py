#!/usr/bin/env python3
"""한 줄 태담 위젯 계약 테스트 — Task 2 Revision v3.1 FINAL MVP CONTRACT.

docs/ 를 로컬 정적 서버로 띄우고 Playwright(Chromium)로 실제 동작을 검증한다.
문자열 검색만으로 끝내지 않고, 가능한 항목은 브라우저에서 실제로 조작해 확인한다.

    python3 tests/test_taedam.py            # 전체
    python3 tests/test_taedam.py 14 15      # 번호로 일부만

필요: playwright (+ chromium). 없으면 건너뛰지 않고 실패로 보고한다.
"""

import functools
import http.server
import json
import socket
import socketserver
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
PAGE = "practice-modern.html"
KEY = "mg_taegyo_draft_v1"
HOUR = 60 * 60 * 1000

# 태담을 이어 쓸 맘곁 화면. 로그인을 먼저 요구하지 않고 입력창으로 바로 보낸다.
# 쿼리는 고정 상수뿐이다 — 사용자가 쓴 본문은 절대 여기 실리지 않는다.
CONTINUE_URL = "https://www.momgyeot.com/tadam?mode=write&entry=taegyo"

# 위젯이 절대 담아서는 안 되는 문구 — taegyo 는 맘곁 저장 여부를 알 수 없다.
FORBIDDEN_PHRASES = ["기록했어요", "저장 완료", "맘곁에 저장했어요", "저장했어요"]


# ── 정적 서버 ────────────────────────────────────────────────────────────────
def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def start_server():
    port = free_port()
    handler = functools.partial(QuietHandler, directory=str(DOCS))
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, f"http://127.0.0.1:{port}"


# ── 테스트 하네스 ────────────────────────────────────────────────────────────
TESTS = []


def test(num, name):
    def deco(fn):
        TESTS.append((num, name, fn))
        return fn
    return deco


class Ctx:
    """테스트마다 새 브라우저 컨텍스트를 준다."""

    def __init__(self, browser, base, pw=None):
        self.browser = browser
        self.base = base
        self.pw = pw          # webkit 등 다른 엔진이 필요한 테스트용

    def page(self, init_scripts=(), seed=None, seed_raw=None, clipboard=True):
        ctx = self.browser.new_context()
        if clipboard:
            try:
                ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=self.base)
            except Exception:
                pass
        if seed is not None:
            seed_raw = json.dumps(seed, ensure_ascii=False)
        if seed_raw is not None:
            ctx.add_init_script(
                "try{localStorage.setItem(%s, %s);}catch(e){}"
                % (json.dumps(KEY), json.dumps(seed_raw))
            )
        for s in init_scripts:
            ctx.add_init_script(s)
        page = ctx.new_page()
        page.set_default_timeout(5000)
        page.goto(f"{self.base}/{PAGE}", wait_until="domcontentloaded")
        page.wait_for_selector("#td-widget")
        return page


def draft(text, age_ms=0, created_age_ms=None, v=1, anchor="part3"):
    now = int(time.time() * 1000)
    return {
        "v": v,
        "text": text,
        "createdAt": now - (created_age_ms if created_age_ms is not None else age_ms),
        "updatedAt": now - age_ms,
        "returnAnchor": anchor,
    }


def stored(page):
    raw = page.evaluate("() => localStorage.getItem(%s)" % json.dumps(KEY))
    return json.loads(raw) if raw else None


def type_text(page, s):
    page.fill("#td-text", s)


# 저장 디바운스(500ms)를 넘겨 커밋을 보장
def settle(page):
    page.wait_for_timeout(750)


# localStorage 를 고장내는 init script 들
BREAK_SET = """
(() => { const o = Storage.prototype.setItem;
  Storage.prototype.setItem = function (k, v) {
    if (k === %s) { const e = new Error('quota'); e.name = 'QuotaExceededError'; throw e; }
    return o.call(this, k, v); }; })();
""" % json.dumps(KEY)

BREAK_GET = """
(() => { const o = Storage.prototype.getItem;
  Storage.prototype.getItem = function (k) {
    if (k === %s) { const e = new Error('blocked'); e.name = 'SecurityError'; throw e; }
    return o.call(this, k); }; })();
""" % json.dumps(KEY)

# 클립보드 1단을 실패시킨다
REJECT_WRITETEXT = """
(() => { try { Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText: () => Promise.reject(new Error('denied')) } }); } catch (e) {} })();
"""

NO_CLIPBOARD_API = """
(() => { try { Object.defineProperty(navigator, 'clipboard', {
    configurable: true, value: undefined }); } catch (e) {} })();
"""


def exec_command(result):
    return """
(() => { document.execCommand = function (cmd) {
    if (cmd === 'copy') { window.__execCopyCalled = true; return %s; }
    return false; }; })();
""" % ("true" if result else "false")


# ── 1. 길이 의미론 ───────────────────────────────────────────────────────────
@test(1, "length uses UTF-16 code units")
def t1(c):
    page = c.page()
    type_text(page, "👶")          # 코드포인트 1개 = UTF-16 code unit 2개
    assert page.inner_text("#td-count").startswith("2 /"), page.inner_text("#td-count")
    type_text(page, "가나다")
    assert page.inner_text("#td-count").startswith("3 /")


@test(2, "Array.from / Intl.Segmenter absent from widget code")
def t2(c):
    html = (DOCS / PAGE).read_text(encoding="utf-8")
    start = html.index('id="td-widget"')
    tail = html[start:]
    assert "Array.from(" not in tail, "위젯 코드에 Array.from 사용됨"
    assert "Intl.Segmenter" not in tail, "위젯 코드에 Intl.Segmenter 사용됨"
    assert "trimmedValue" in tail and ".trim()" in tail


@test(3, "0 / 1 / 300 / 301 boundary")
def t3(c):
    page = c.page()
    # 0자 → 복사 불가
    assert page.is_disabled("#td-copy")
    # 1자 → 가능
    type_text(page, "가")
    assert page.is_enabled("#td-copy")
    # 300자 → 가능
    type_text(page, "가" * 300)
    assert page.inner_text("#td-count").startswith("300 /")
    assert page.is_enabled("#td-copy")
    # textarea 자체가 300 을 넘기지 못한다
    assert page.get_attribute("#td-text", "maxlength") == "300"
    # 저장된 301자 draft 는 유효하지 않은 것으로 취급된다
    p2 = c.page(seed=draft("나" * 301))
    assert stored(p2) is None, "301자 draft 가 살아남음"
    assert p2.input_value("#td-text") == ""
    assert p2.is_visible("#td-notice")


@test(4, "trimmed canonical value shared by counter / storage / clipboard")
def t4(c):
    page = c.page()
    type_text(page, "   안녕 아가야   ")
    settle(page)
    assert page.inner_text("#td-count").startswith("6 /"), page.inner_text("#td-count")
    assert stored(page)["text"] == "안녕 아가야"
    page.click("#td-copy")
    page.wait_for_selector("#td-success:not([hidden])")
    assert page.evaluate("() => navigator.clipboard.readText()") == "안녕 아가야"


# ── 2. 보관 수명 ─────────────────────────────────────────────────────────────
@test(5, "TTL 72h — expired draft removed and never shown")
def t5(c):
    expired = c.page(seed=draft("만료된 태담", age_ms=73 * HOUR))
    assert stored(expired) is None, "만료 draft 가 남아 있음"
    assert expired.input_value("#td-text") == ""
    assert expired.is_hidden("#td-restored")
    assert "만료된 태담" not in expired.content(), "만료 내용이 화면에 노출됨"
    alive = c.page(seed=draft("살아있는 태담", age_ms=71 * HOUR))
    assert stored(alive) is not None
    assert alive.input_value("#td-text") == "살아있는 태담"


@test(6, "view / copy does not refresh updatedAt")
def t6(c):
    d = draft("보관된 태담", age_ms=2 * HOUR)
    page = c.page(seed=d)
    before = stored(page)["updatedAt"]
    page.mouse.wheel(0, 400)
    settle(page)
    assert stored(page)["updatedAt"] == before, "조회/스크롤로 updatedAt 이 갱신됨"
    page.click("#td-copy")
    page.wait_for_selector("#td-success:not([hidden])")
    settle(page)
    assert stored(page)["updatedAt"] == before, "복사로 updatedAt 이 갱신됨"


@test(7, "actual edit refreshes updatedAt")
def t7(c):
    d = draft("처음 문장", age_ms=2 * HOUR)
    page = c.page(seed=d)
    before = stored(page)["updatedAt"]
    type_text(page, "처음 문장 그리고 덧붙임")
    settle(page)
    after = stored(page)
    assert after["updatedAt"] > before, "편집했는데 updatedAt 이 그대로"
    assert after["createdAt"] == d["createdAt"], "createdAt 이 바뀜"
    assert after["text"] == "처음 문장 그리고 덧붙임"


@test(8, "existing draft autoloads into editor with banner")
def t8(c):
    page = c.page(seed=draft("어제 남긴 한 줄", age_ms=26 * HOUR))
    assert page.input_value("#td-text") == "어제 남긴 한 줄"
    assert page.is_visible("#td-restored")
    assert page.is_visible("#td-sub")
    assert page.is_visible("#td-meta")
    # 배너는 본문을 중복 표시하지 않는다 (L-5 단순화)
    assert "어제 남긴 한 줄" not in page.inner_text("#td-restored")
    assert "불러왔어요" in page.inner_text("#td-restored")


@test(9, "no silent overwrite on load")
def t9(c):
    d = draft("건드리면 안 되는 문장", age_ms=5 * HOUR)
    page = c.page(seed=d)
    settle(page)
    got = stored(page)
    assert got["text"] == d["text"]
    assert got["updatedAt"] == d["updatedAt"], "로드만 했는데 updatedAt 변경"
    assert got["createdAt"] == d["createdAt"]


# ── 3. 파괴적 동작 확인 ──────────────────────────────────────────────────────
def _dialog_flow(c, button, ok_label):
    d = draft("지워질 후보", age_ms=1 * HOUR)
    page = c.page(seed=d)
    page.click(button)
    page.wait_for_selector("#td-dialog:not([hidden])")
    # 확인 전에는 아무것도 지워지지 않는다
    assert stored(page)["text"] == d["text"]
    # 기본 포커스는 취소
    assert page.evaluate("() => document.activeElement && document.activeElement.id") == "td-dlg-cancel"
    assert page.inner_text("#td-dlg-ok") == ok_label
    body = page.inner_text("#td-dlg-b")
    # 취소하면 그대로
    page.click("#td-dlg-cancel")
    page.wait_for_selector("#td-dialog", state="hidden")
    assert stored(page)["text"] == d["text"], "취소했는데 지워짐"
    # 확인하면 지워진다
    page.click(button)
    page.wait_for_selector("#td-dialog:not([hidden])")
    page.click("#td-dlg-ok")
    page.wait_for_selector("#td-dialog", state="hidden")
    assert stored(page) is None, "확인했는데 안 지워짐"
    assert page.input_value("#td-text") == ""
    assert page.is_hidden("#td-restored")
    return body


@test(10, "new draft requires destructive confirmation")
def t10(c):
    _dialog_flow(c, "#td-new", "지우고 새로 쓰기")


@test(11, "delete requires destructive confirmation")
def t11(c):
    _dialog_flow(c, "#td-del", "지우기")


@test(12, "delete copy makes no claim about Momgyeot save")
def t12(c):
    body = _dialog_flow(c, "#td-del", "지우기")
    assert "맘곁에 저장됐는지는 여기서 확인할 수 없어요" in body, body
    assert "다시 복구할 수 없습니다" in body, body
    for bad in FORBIDDEN_PHRASES:
        assert bad not in body, f"삭제 문구에 금지 표현: {bad}"


@test(13, "no '기록했어요' style CTA anywhere in the widget")
def t13(c):
    html = (DOCS / PAGE).read_text(encoding="utf-8")
    start = html.index('id="td-widget"')
    tail = html[start:]
    for bad in FORBIDDEN_PHRASES:
        assert bad not in tail, f"위젯에 금지 문구 발견: {bad}"
    assert "이 기기에서 임시 태담 지우기" in tail


# ── 4. 저장소 실패 ───────────────────────────────────────────────────────────
@test(14, "corrupted JSON — removed, empty state, user notified")
def t14(c):
    page = c.page(seed_raw="{이건 JSON 이 아님")
    assert stored(page) is None, "손상 값이 남아 있음"
    assert page.input_value("#td-text") == ""
    assert page.is_visible("#td-notice")
    assert "임시 보관은 하지 못했어요" in page.inner_text("#td-notice")
    assert page.is_hidden("#td-restored")


@test(15, "QuotaExceededError — notified, degraded mode")
def t15(c):
    page = c.page(init_scripts=[BREAK_SET])
    msg = "저장은 안 되지만 쓸 수는 있어야 한다"
    type_text(page, msg)
    settle(page)
    assert page.is_visible("#td-notice")
    assert "임시 보관은 하지 못했어요" in page.inner_text("#td-notice")
    assert page.inner_text("#td-count").startswith(f"{len(msg)} /"), page.inner_text("#td-count")
    assert page.is_enabled("#td-copy")


@test(16, "SecurityError on read — notified, degraded mode")
def t16(c):
    page = c.page(init_scripts=[BREAK_GET])
    assert page.is_visible("#td-notice")
    msg = "읽기가 막혀도 입력은 된다"
    type_text(page, msg)
    assert page.is_enabled("#td-copy")
    assert page.inner_text("#td-count").startswith(f"{len(msg)} /"), page.inner_text("#td-count")


@test(17, "clipboard still works in degraded mode")
def t17(c):
    page = c.page(init_scripts=[BREAK_SET])
    type_text(page, "복사는 되어야 한다")
    page.click("#td-copy")
    page.wait_for_selector("#td-success:not([hidden])")
    assert page.evaluate("() => navigator.clipboard.readText()") == "복사는 되어야 한다"


# ── 5. 클립보드 ──────────────────────────────────────────────────────────────
@test(18, "clipboard success path")
def t18(c):
    page = c.page()
    type_text(page, "오늘 네 발차기를 처음 느꼈어.")
    page.click("#td-copy")
    page.wait_for_selector("#td-success:not([hidden])")
    assert page.is_hidden("#td-edit")
    assert page.is_hidden("#td-manual")
    assert "복사했어요" in page.inner_text("#td-success")
    assert page.evaluate("() => navigator.clipboard.readText()") == "오늘 네 발차기를 처음 느꼈어."
    # 링크는 고정 URL. 본문이 섞여 들어가지 않는다.
    href = page.get_attribute("#td-go", "href")
    assert href == CONTINUE_URL, href
    assert "오늘 네 발차기를 처음 느꼈어." not in href
    # 되돌아가기
    page.click("#td-later")
    page.wait_for_selector("#td-edit:not([hidden])")


@test(19, "fallback chain: writeText reject -> execCommand -> manual")
def t19(c):
    # 1단 실패 + 2단 성공 → 성공 화면
    p1 = c.page(init_scripts=[REJECT_WRITETEXT, exec_command(True)])
    type_text(p1, "폴백 성공 경로")
    p1.click("#td-copy")
    p1.wait_for_selector("#td-success:not([hidden])")
    assert p1.evaluate("() => window.__execCopyCalled === true"), "execCommand 폴백이 호출되지 않음"

    # 1단 실패 + 2단 실패 → 수동 복사 화면
    p2 = c.page(init_scripts=[REJECT_WRITETEXT, exec_command(False)])
    type_text(p2, "폴백 실패 경로")
    p2.click("#td-copy")
    p2.wait_for_selector("#td-manual:not([hidden])")
    assert p2.is_hidden("#td-success")
    assert "자동 복사가 되지 않았어요" in p2.inner_text("#td-manual")

    # clipboard API 자체가 없는 환경 → 바로 2단
    p3 = c.page(init_scripts=[NO_CLIPBOARD_API, exec_command(False)], clipboard=False)
    type_text(p3, "API 없는 환경")
    p3.click("#td-copy")
    p3.wait_for_selector("#td-manual:not([hidden])")


@test(20, "manual panel exposes full text, pre-selected")
def t20(c):
    page = c.page(init_scripts=[REJECT_WRITETEXT, exec_command(False)])
    type_text(page, "  길게 눌러 복사할 문장  ")
    page.click("#td-copy")
    page.wait_for_selector("#td-manual:not([hidden])")
    val = page.input_value("#td-manual-text")
    assert val == "길게 눌러 복사할 문장", repr(val)
    sel = page.evaluate(
        "() => { const t = document.getElementById('td-manual-text');"
        " return [t.selectionStart, t.selectionEnd]; }"
    )
    assert sel == [0, len(val)], f"자동 전체 선택 안 됨: {sel}"


# ── 6. 보안 ──────────────────────────────────────────────────────────────────
@test(21, "malicious draft rendered as text, never as HTML")
def t21(c):
    payload = '<img src=x onerror="window.__pwned=1"><b>bold</b>'
    page = c.page(seed=draft(payload, age_ms=1 * HOUR))
    assert page.evaluate("() => window.__pwned") is None, "스크립트가 실행됨"
    assert page.evaluate("() => document.querySelectorAll('#td-widget img, #td-widget b').length") == 0
    assert page.input_value("#td-text") == payload


@test(22, "draft never enters URL and no network call is made")
def t22(c):
    ctx = c.browser.new_context()
    try:
        ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=c.base)
    except Exception:
        pass
    page = ctx.new_page()
    page.set_default_timeout(5000)
    page.goto(f"{c.base}/{PAGE}", wait_until="domcontentloaded")
    page.wait_for_selector("#td-widget")
    # 위젯이 준비된 뒤부터 기록한다. 페이지 자체의 폰트/이미지 로드는 대상이 아니다.
    external = []
    page.on("request", lambda r: None if r.url.startswith(c.base) else external.append(r.url))
    secret = "URL 에 들어가면 안 되는 문장"
    type_text(page, secret)
    settle(page)
    page.click("#td-copy")
    page.wait_for_selector("#td-success:not([hidden])")
    assert secret not in page.url, page.url
    assert page.evaluate("() => location.search") == ""
    assert secret not in page.evaluate("() => location.hash")
    assert external == [], f"외부 요청 발생: {external}"
    for sel in ["#td-go", "#td-go-edit"]:
        href = page.get_attribute(sel, "href")
        assert href == CONTINUE_URL, f"{sel}: {href}"
        # 고정 쿼리 외에 어떤 값도 붙지 않는다.
        assert secret not in href, href
        assert "prefill" not in href and "text=" not in href, href


@test(23, "expiry notice within 24h, calm wording otherwise")
def t23(c):
    soon = c.page(seed=draft("곧 만료", age_ms=50 * HOUR))     # 22시간 남음
    meta = soon.inner_text("#td-meta")
    assert "하루 안에 만료돼요" in meta, meta
    assert "다음 방문 때" in meta, meta
    assert "저장" in meta, meta
    later = c.page(seed=draft("여유 있음", age_ms=2 * HOUR))
    meta2 = later.inner_text("#td-meta")
    assert "72시간이 지나면 다음 방문 때" in meta2, meta2
    # "자동 물리 삭제" 류 표현을 쓰지 않는다
    html = (DOCS / PAGE).read_text(encoding="utf-8")
    assert "자동 물리 삭제" not in html


# ── 추가 계약 검증 ───────────────────────────────────────────────────────────
@test(24, "Korean 299 / 300 boundary")
def t24(c):
    page = c.page()
    type_text(page, "가" * 299)
    assert page.inner_text("#td-count").startswith("299 /")
    assert page.is_enabled("#td-copy")
    type_text(page, "가" * 300)
    settle(page)
    assert stored(page)["text"] == "가" * 300


@test(25, "emoji at the UTF-16 boundary is storable")
def t25(c):
    page = c.page()
    text = "👶" * 150            # UTF-16 code unit 300
    type_text(page, text)
    settle(page)
    assert page.inner_text("#td-count").startswith("300 /")
    assert stored(page)["text"] == text


@test(26, "blank editor must NOT delete the persisted backup")
def t26(c):
    d = draft("지워지면 안 되는 문장", age_ms=1 * HOUR)
    page = c.page(seed=d)
    # 전체 선택 후 삭제 — 실제 키 입력으로 재현
    page.click("#td-text")
    page.keyboard.press("ControlOrMeta+a")
    page.keyboard.press("Backspace")
    settle(page)
    assert page.input_value("#td-text") == ""
    assert page.is_disabled("#td-copy")
    got = stored(page)
    assert got is not None, "빈 입력이 확인 없이 보관본을 지웠다"
    assert got["text"] == d["text"]
    assert got["updatedAt"] == d["updatedAt"]


@test(27, "widget is absent from the theory book and the classic layout")
def t27(c):
    for name in ("book-modern.html", "book.html", "practice.html", "index.html"):
        html = (DOCS / name).read_text(encoding="utf-8")
        assert 'id="td-widget"' not in html, f"{name} 에 위젯이 들어감"
        assert "mg_taegyo_draft_v1" not in html, f"{name} 에 draft 키가 들어감"


@test(28, "no third-party executable script added by the widget")
def t28(c):
    html = (DOCS / PAGE).read_text(encoding="utf-8")
    start = html.index('id="td-widget"')
    tail = html[start:]
    for bad in ["<script src=", "fetch(", "XMLHttpRequest", "sendBeacon",
                "WebSocket", "<iframe", "googletagmanager", "clarity", "hotjar"]:
        assert bad not in tail, f"위젯 코드에 금지 요소: {bad}"


@test(29, "button text meets WCAG AA contrast in light and dark")
def t29(c):
    js = """(sel) => {
      const el = document.querySelector(sel);
      const cs = getComputedStyle(el);
      const parse = (v) => v.match(/\\d+(\\.\\d+)?/g).slice(0, 3).map(Number);
      const lum = (rgb) => { const f = rgb.map(v => { v /= 255;
        return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
        return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]; };
      const a = lum(parse(cs.color)), b = lum(parse(cs.backgroundColor));
      const hi = Math.max(a, b), lo = Math.min(a, b);
      return (hi + 0.05) / (lo + 0.05);
    }"""
    for theme in ("light", "dark"):
        page = c.page(init_scripts=[
            "try{localStorage.setItem('mamgyeot-theme', %s);}catch(e){}" % json.dumps(theme)])
        type_text(page, "대비 확인")
        for sel in ("#td-copy", ):
            ratio = page.evaluate(js, sel)
            assert ratio >= 4.5, f"{theme} {sel} 대비 {ratio:.2f}:1 (AA 4.5 미달)"
        page.click("#td-del") if page.is_visible("#td-sub") else None
        # 파괴적 버튼은 다이얼로그 안에 있으므로 열어서 확인한다
        page.evaluate("() => document.getElementById('td-dialog').hidden = false")
        ratio = page.evaluate(js, "#td-dlg-ok")
        assert ratio >= 4.5, f"{theme} #td-dlg-ok 대비 {ratio:.2f}:1 (AA 4.5 미달)"


# ── 7. Task 3 Revision 1 — Codex 리뷰 반영 ───────────────────────────────────
BREAK_REMOVE = """
(() => { const o = Storage.prototype.removeItem;
  Storage.prototype.removeItem = function (k) {
    if (k === %s) { const e = new Error('blocked'); e.name = 'SecurityError'; throw e; }
    return o.call(this, k); }; })();
""" % json.dumps(KEY)

RECORD_ACTIVATION = """
(() => { window.__activation = null;
  try { Object.defineProperty(navigator, 'clipboard', { configurable: true, value: {
    writeText: (t) => { window.__activation =
      !!(navigator.userActivation && navigator.userActivation.isActive);
      window.__copied = t; return Promise.resolve(); } } }); } catch (e) {} })();
"""


def confirm_dialog(page, button):
    page.click(button)
    page.wait_for_selector("#td-dialog", state="visible")
    page.click("#td-dlg-ok")
    page.wait_for_selector("#td-dialog", state="hidden")


@test(30, "pending debounce must not resurrect a deleted draft")
def t30(c):
    page = c.page(seed=draft("원본", age_ms=1 * HOUR))
    type_text(page, "막 입력한 새 문장")      # 디바운스 대기 시작
    confirm_dialog(page, "#td-del")            # 500ms 이내에 삭제 확정
    page.wait_for_timeout(1200)                # pending 콜백이 지나가도록 충분히 대기
    assert stored(page) is None, "pending save 가 삭제된 draft 를 되살렸다"
    assert page.input_value("#td-text") == ""


@test(31, "pending debounce must not resurrect on 'new draft'")
def t31(c):
    page = c.page(seed=draft("이전 문장", age_ms=1 * HOUR))
    type_text(page, "지우기 직전에 친 문장")
    confirm_dialog(page, "#td-new")
    page.wait_for_timeout(1200)
    got = stored(page)
    assert got is None, f"새로 쓰기 후 draft 가 되살아남: {got}"


@test(32, "navigation flushes pending draft synchronously")
def t32(c):
    page = c.page()
    secret = "이동 직전에 쓴 문장"
    type_text(page, secret)                    # 디바운스 아직 안 끝남
    page.evaluate("() => { const a = document.getElementById('td-go-edit');"
                  " a.removeAttribute('target'); a.setAttribute('href', '#part1'); }")
    page.click("#td-go-edit")                  # 즉시 이동 시도
    got = stored(page)
    assert got is not None, "이동 전에 flush 되지 않아 draft 가 사라졌다"
    assert got["text"] == secret


@test(33, "removeItem failure must not claim deletion")
def t33(c):
    d = draft("지워지지 않는 문장", age_ms=1 * HOUR)
    page = c.page(seed=d, init_scripts=[BREAK_REMOVE])
    confirm_dialog(page, "#td-del")
    notice = page.inner_text("#td-notice")
    assert "지우지 못했어요" in notice, notice
    assert "임시 보관은 하지 못했어요" not in notice, "저장 실패 문구를 삭제 실패에 재사용함"
    # UI 와 저장본이 그대로 남아야 한다
    assert page.input_value("#td-text") == d["text"]
    assert page.is_visible("#td-sub")
    raw = page.evaluate("() => { try { return localStorage.getItem(%s); } catch (e) { return null; } }"
                        % json.dumps(KEY))
    assert raw and d["text"] in raw, "삭제 실패인데 저장본이 사라졌다"


def _two_tabs(c, seed_draft):
    ctx = c.browser.new_context()
    ctx.add_init_script("try{localStorage.setItem(%s, %s);}catch(e){}"
                        % (json.dumps(KEY), json.dumps(json.dumps(seed_draft, ensure_ascii=False))))
    a, b = ctx.new_page(), ctx.new_page()
    for pg in (a, b):
        pg.set_default_timeout(5000)
        pg.goto(f"{c.base}/{PAGE}", wait_until="domcontentloaded")
        pg.wait_for_selector("#td-widget")
    return ctx, a, b


@test(34, "multi-tab: diverged tab must not silently overwrite")
def t34(c):
    ctx, a, b = _two_tabs(c, draft("공통 원본", age_ms=1 * HOUR))
    type_text(a, "A 탭에서만 친 문장")            # A 에 미저장 편집 발생
    b_text = "B 탭이 먼저 저장한 문장"
    b.evaluate("(t) => { localStorage.setItem(%s, JSON.stringify({v:1, text:t,"
               " createdAt: Date.now(), updatedAt: Date.now(), returnAnchor:''})); }"
               % json.dumps(KEY), b_text)
    a.wait_for_selector("#td-conflict", state="visible")   # A 가 충돌을 알린다
    a.wait_for_timeout(1200)                                # A 의 pending save 통과
    raw = a.evaluate("() => localStorage.getItem(%s)" % json.dumps(KEY))
    assert b_text in raw, "A 가 B 의 최신본을 조용히 덮어썼다"
    assert a.is_visible("#td-conflict")
    ctx.close()


@test(35, "multi-tab: conflict offers keep / load, default keeps this tab")
def t35(c):
    ctx, a, b = _two_tabs(c, draft("공통 원본", age_ms=1 * HOUR))
    type_text(a, "A 탭 내용")
    b.evaluate("() => { localStorage.setItem(%s, JSON.stringify({v:1, text:'B 탭 내용',"
               " createdAt: Date.now(), updatedAt: Date.now(), returnAnchor:''})); }"
               % json.dumps(KEY))
    a.wait_for_selector("#td-conflict", state="visible")
    # 자동 반영되지 않는다 — 이 탭 내용이 기본
    assert a.input_value("#td-text") == "A 탭 내용"
    a.click("#td-conflict-load")
    a.wait_for_selector("#td-conflict", state="hidden")
    assert a.input_value("#td-text") == "B 탭 내용"
    ctx.close()


@test(36, "storage event adopts external change when tab has no edits")
def t36(c):
    ctx, a, b = _two_tabs(c, draft("공통 원본", age_ms=1 * HOUR))
    b.evaluate("() => { localStorage.setItem(%s, JSON.stringify({v:1, text:'다른 탭이 고친 문장',"
               " createdAt: Date.now(), updatedAt: Date.now(), returnAnchor:''})); }"
               % json.dumps(KEY))
    a.wait_for_function("() => document.getElementById('td-text').value === '다른 탭이 고친 문장'")
    assert a.is_hidden("#td-conflict"), "편집 중이 아닌데 충돌을 띄웠다"
    ctx.close()


@test(37, "first session states the 72h retention up front")
def t37(c):
    page = c.page()
    lead = page.inner_text(".td-lead")
    assert "72시간" in lead, lead


@test(38, "first save immediately reveals delete / new-draft controls and expiry")
def t38(c):
    page = c.page()
    assert page.is_hidden("#td-sub")
    assert page.is_hidden("#td-meta")
    type_text(page, "처음 저장되는 문장")
    settle(page)
    assert page.is_visible("#td-sub"), "첫 저장 뒤에도 삭제 CTA 가 안 보임"
    assert page.is_visible("#td-meta")
    meta = page.inner_text("#td-meta")
    assert "저장" in meta and "72시간" in meta, meta
    assert page.is_hidden("#td-restored"), "새로 쓴 건데 '불러왔어요' 배너가 뜸"


@test(39, "textarea exposes an accessible name")
def t39(c):
    page = c.page()
    assert page.get_by_label("한 줄 태담", exact=True).count() == 1
    name = page.evaluate("""() => {
      const t = document.getElementById('td-text');
      const l = document.querySelector('label[for="td-text"]');
      return { hidden: l.hasAttribute('hidden'), text: l.textContent.trim(),
               rect: l.getBoundingClientRect().width > 0 }; }""")
    assert name["hidden"] is False, "label 이 hidden 이면 접근성 트리에서 사라진다"
    assert name["text"] == "한 줄 태담"


@test(40, "dialog traps Tab")
def t40(c):
    page = c.page(seed=draft("문장", age_ms=1 * HOUR))
    page.click("#td-del")
    page.wait_for_selector("#td-dialog", state="visible")
    seen = set()
    for _ in range(6):
        page.keyboard.press("Tab")
        seen.add(page.evaluate("() => document.activeElement.id"))
    assert seen <= {"td-dlg-cancel", "td-dlg-ok"}, f"포커스가 다이얼로그를 벗어남: {seen}"


@test(41, "dialog traps Shift+Tab")
def t41(c):
    page = c.page(seed=draft("문장", age_ms=1 * HOUR))
    page.click("#td-del")
    page.wait_for_selector("#td-dialog", state="visible")
    seen = set()
    for _ in range(6):
        page.keyboard.press("Shift+Tab")
        seen.add(page.evaluate("() => document.activeElement.id"))
    assert seen <= {"td-dlg-cancel", "td-dlg-ok"}, f"포커스가 다이얼로그를 벗어남: {seen}"


@test(42, "Escape closes dialog and restores focus to the trigger")
def t42(c):
    page = c.page(seed=draft("문장", age_ms=1 * HOUR))
    page.click("#td-del")
    page.wait_for_selector("#td-dialog", state="visible")
    page.keyboard.press("Escape")
    page.wait_for_selector("#td-dialog", state="hidden")
    assert page.evaluate("() => document.activeElement.id") == "td-del"
    assert stored(page) is not None, "Escape 로 닫았는데 지워짐"


@test(43, "background is not focusable while the dialog is open")
def t43(c):
    page = c.page(seed=draft("문장", age_ms=1 * HOUR))
    page.click("#td-del")
    page.wait_for_selector("#td-dialog", state="visible")
    inert = page.evaluate("""() => {
      const n = document.getElementById('td-edit');
      return { inert: n.inert === true, ariaHidden: n.getAttribute('aria-hidden') }; }""")
    assert inert["inert"] or inert["ariaHidden"] == "true", inert
    page.click("#td-dlg-cancel")
    page.wait_for_selector("#td-dialog", state="hidden")
    after = page.evaluate("""() => {
      const n = document.getElementById('td-edit');
      return { inert: n.inert === true, ariaHidden: n.getAttribute('aria-hidden') }; }""")
    assert after["inert"] is False and after["ariaHidden"] is None, after


@test(44, "copy success moves focus to a visible actionable element")
def t44(c):
    page = c.page()
    type_text(page, "복사 후 포커스 확인")
    page.click("#td-copy")
    page.wait_for_selector("#td-success:not([hidden])")
    info = page.evaluate("""() => {
      const a = document.activeElement;
      if (!a || a === document.body) return { id: null, visible: false };
      return { id: a.id, visible: !!(a.offsetWidth || a.offsetHeight || a.getClientRects().length) }; }""")
    assert info["visible"], f"포커스가 보이지 않는 곳에 있음: {info}"
    assert info["id"] in ("td-go", "td-success-h"), info


@test(45, "focus ring meets 3:1 against both surfaces in light and dark")
def t45(c):
    js = """() => {
      const card = document.querySelector('.td');
      const cs = getComputedStyle(card);
      const ring = cs.getPropertyValue('--td-focus').trim();
      const probe = document.createElement('span');
      probe.style.color = ring; document.body.appendChild(probe);
      const ringRgb = getComputedStyle(probe).color; probe.remove();
      const bodyBg = getComputedStyle(document.body).backgroundColor;
      const cardBg = cs.backgroundColor;
      const P = v => v.match(/\\d+(\\.\\d+)?/g).slice(0, 3).map(Number);
      const L = r => { const f = r.map(v => { v /= 255;
        return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
        return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]; };
      const ratio = (x, y) => { const a = L(P(x)), b = L(P(y));
        return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); };
      return { vsCard: ratio(ringRgb, cardBg), vsBody: ratio(ringRgb, bodyBg) };
    }"""
    for theme in ("light", "dark"):
        page = c.page(init_scripts=[
            "try{localStorage.setItem('mamgyeot-theme', %s);}catch(e){}" % json.dumps(theme)])
        r = page.evaluate(js)
        assert r["vsCard"] >= 3.0, f"{theme} focus ring vs card {r['vsCard']:.2f}:1 (<3:1)"
        assert r["vsBody"] >= 3.0, f"{theme} focus ring vs body {r['vsBody']:.2f}:1 (<3:1)"
        # 실제로 outline 에 그 색이 쓰이는지도 확인
        page.focus("#td-text")
        outline = page.evaluate("() => getComputedStyle(document.getElementById('td-text')).outlineColor")
        assert outline, outline


@test(46, "far-future updatedAt is treated as malformed, small skew is kept")
def t46(c):
    far = c.page(seed=draft("미래에서 온 문장", age_ms=-48 * HOUR))   # 48시간 미래
    assert stored(far) is None, "먼 미래 타임스탬프가 살아남음"
    assert far.input_value("#td-text") == ""
    assert far.is_visible("#td-notice")
    near = c.page(seed=draft("시계가 조금 빠른 문장", age_ms=-1 * HOUR))
    assert stored(near) is not None, "1시간 오차까지는 허용해야 한다"
    assert near.input_value("#td-text") == "시계가 조금 빠른 문장"


@test(47, "72h boundary — just inside kept, just outside removed")
def t47(c):
    TTL = 72 * HOUR
    inside = c.page(seed=draft("경계 안쪽", age_ms=TTL - 3000))
    assert stored(inside) is not None, "72h 직전인데 지워짐"
    outside = c.page(seed=draft("경계 바깥", age_ms=TTL + 3000))
    assert stored(outside) is None, "72h 경과인데 남아 있음"


@test(48, "clipboard write happens under user activation")
def t48(c):
    page = c.page(init_scripts=[RECORD_ACTIVATION], clipboard=False)
    type_text(page, "제스처 안에서 복사")
    page.click("#td-copy")
    page.wait_for_selector("#td-success:not([hidden])")
    assert page.evaluate("() => window.__copied") == "제스처 안에서 복사"
    act = page.evaluate("() => window.__activation")
    assert act is True, f"writeText 가 user activation 밖에서 호출됨: {act}"


# ── 8. Task 3 Revision 2 — 충돌 lifecycle 데이터 손실 ────────────────────────
REMOVE_FAILS_ONCE = """
(() => { let first = true; const o = Storage.prototype.removeItem;
  Storage.prototype.removeItem = function (k) {
    if (k === %s && first) { first = false;
      const e = new Error('blocked'); e.name = 'SecurityError'; throw e; }
    return o.call(this, k); }; })();
""" % json.dumps(KEY)


def write_from(page, text):
    """다른 탭이 직접 저장소에 쓴다 (storage 이벤트 발생)."""
    page.evaluate("(t) => { localStorage.setItem(%s, JSON.stringify({v:1, text:t,"
                  " createdAt: Date.now(), updatedAt: Date.now(), returnAnchor:''})); }"
                  % json.dumps(KEY), text)


def delete_from(page):
    page.evaluate("() => localStorage.removeItem(%s)" % json.dumps(KEY))


@test(49, "adopting the other tab's draft cancels the pending debounce")
def t49(c):
    ctx, a, b = _two_tabs(c, draft("공통 원본", age_ms=1 * HOUR))
    type_text(a, "A 탭 편집")
    write_from(b, "B 탭 최신 문장")
    a.wait_for_selector("#td-conflict", state="visible")
    # 디바운스는 500ms 라 Playwright 왕복으로는 살려둘 수 없다.
    # 같은 tick 안에서 새 편집(=pending 예약)과 불러오기 클릭을 함께 일으켜
    # "예약된 콜백이 살아 있는 상태에서 adopt" 라는 위험 순서를 확정적으로 만든다.
    a.evaluate("""() => {
      const ta = document.getElementById('td-text');
      ta.value = '되살아나면 안 되는 stale 문장';
      ta.dispatchEvent(new Event('input', { bubbles: true }));
      document.getElementById('td-conflict-load').click();
    }""")
    a.wait_for_selector("#td-conflict", state="hidden")
    assert a.input_value("#td-text") == "B 탭 최신 문장"
    a.wait_for_timeout(900)                     # 예약됐던 콜백이 지나가도록
    got = stored(a)
    assert got is not None and got["text"] == "B 탭 최신 문장", \
        f"stale 콜백이 불러온 내용을 되돌렸다: {got}"
    assert a.input_value("#td-text") == "B 탭 최신 문장"
    ctx.close()


@test(50, "clean-tab external delete cancels pending and clears the editor")
def t50(c):
    # 저장본과 같은 내용으로 input 을 일으키면 pending 은 예약되지만 divergence 는 없다.
    # 같은 tick 에서 삭제 + storage 이벤트까지 일으켜 clean 삭제 경로의 위험 순서를 확정한다.
    same = "같은 내용이라 발산하지 않는 문장"
    page = c.page(seed=draft(same, age_ms=1 * HOUR))
    page.evaluate("""(k) => {
      const ta = document.getElementById('td-text');
      ta.value = ta.value;                                   // 동일 내용 → 발산 없음
      ta.dispatchEvent(new Event('input', { bubbles: true })); // pending 예약
      const old = localStorage.getItem(k);
      localStorage.removeItem(k);
      window.dispatchEvent(new StorageEvent('storage',
        { key: k, oldValue: old, newValue: null }));
    }""", KEY)
    assert page.is_hidden("#td-conflict"), "clean 탭인데 충돌을 띄웠다"
    assert page.input_value("#td-text") == "", "삭제를 반영했는데 editor 가 남아 있다"
    assert page.is_hidden("#td-sub") and page.is_hidden("#td-meta")
    assert stored(page) is None
    page.wait_for_timeout(900)                                # 예약됐던 콜백 통과
    assert stored(page) is None, "clean 삭제 경로에서 pending 이 draft 를 되살렸다"
    assert page.input_value("#td-text") == ""


@test(51, "deletion conflict offers 'keep deleted' and never resurrects")
def t51(c):
    ctx, a, b = _two_tabs(c, draft("공통 원본", age_ms=1 * HOUR))
    type_text(a, "A 탭 문장")
    delete_from(b)
    a.wait_for_selector("#td-conflict", state="visible")
    # 삭제 충돌은 '불러오기' 문구를 쓰지 않는다
    assert "지웠어요" in a.inner_text("#td-conflict-h"), a.inner_text("#td-conflict-h")
    assert a.inner_text("#td-conflict-load") == "삭제된 상태 유지"
    assert "불러오기" not in a.inner_text("#td-conflict-load")
    a.click("#td-conflict-load")
    a.wait_for_selector("#td-conflict", state="hidden")
    assert a.input_value("#td-text") == ""
    assert a.is_hidden("#td-sub")
    a.wait_for_timeout(900)
    assert stored(a) is None, "삭제 유지를 골랐는데 저장소에 다시 생겼다"
    ctx.close()


@test(52, "keeping local content after external deletion requires explicit action")
def t52(c):
    ctx, a, b = _two_tabs(c, draft("공통 원본", age_ms=1 * HOUR))
    type_text(a, "A 탭이 지키고 싶은 문장")
    delete_from(b)
    a.wait_for_selector("#td-conflict", state="visible")
    a.wait_for_timeout(900)
    assert stored(a) is None, "명시적 선택 전에 자동 재생성됐다"
    a.click("#td-conflict-keep")
    a.wait_for_selector("#td-conflict", state="hidden")
    a.wait_for_timeout(300)
    got = stored(a)
    assert got is not None and got["text"] == "A 탭이 지키고 싶은 문장", got
    # 선택 이후에도 계속 편집·저장이 된다
    type_text(a, "그 뒤에 이어서 쓴 문장")
    settle(a)
    got2 = stored(a)
    assert got2["text"] == "그 뒤에 이어서 쓴 문장", got2
    ctx.close()


@test(53, "delete retry after failure restores persistence")
def t53(c):
    d = draft("지울 문장", age_ms=1 * HOUR)
    page = c.page(seed=d, init_scripts=[REMOVE_FAILS_ONCE])
    # 1차: 실패 → UI 유지 + 정확한 문구
    confirm_dialog(page, "#td-del")
    assert "지우지 못했어요" in page.inner_text("#td-notice")
    assert page.input_value("#td-text") == d["text"]
    assert stored(page) is not None
    # 2차: 성공 → 실제로 지워진다
    confirm_dialog(page, "#td-del")
    assert stored(page) is None, "재시도했는데 안 지워짐"
    assert page.input_value("#td-text") == ""
    # 그 뒤 새 draft 가 조용히 유실되지 않아야 한다
    type_text(page, "삭제 성공 뒤에 쓴 새 문장")
    settle(page)
    got = stored(page)
    assert got is not None and got["text"] == "삭제 성공 뒤에 쓴 새 문장", \
        f"삭제 재시도 성공 후에도 저장이 막혀 있다: {got}"


@test(54, "conflict 'keep this tab' requeries live storage before saving")
def t54(c):
    ctx, a, b = _two_tabs(c, draft("공통 원본", age_ms=1 * HOUR))
    keep_text = "A 탭이 지키려는 문장"
    type_text(a, keep_text)
    write_from(b, "두 번째 문장")
    a.wait_for_selector("#td-conflict", state="visible")
    write_from(b, "세 번째 문장")                 # 고르는 중에 또 바뀐다
    a.wait_for_timeout(300)
    assert a.is_visible("#td-conflict"), "제3의 write 후 충돌이 사라짐"
    a.click("#td-conflict-keep")                  # 이 탭 내용을 쓰겠다는 명시적 선택
    a.wait_for_selector("#td-conflict", state="hidden")
    a.wait_for_timeout(900)
    got = stored(a)
    # keep 이 live storage 를 다시 읽어 baseline 을 맞추지 않으면
    # baseline 불일치로 저장이 막혀 사용자의 선택이 조용히 사라진다.
    assert got is not None and got["text"] == keep_text, \
        f"keep 을 골랐는데 이 탭 내용이 저장되지 않았다: {got}"
    ctx.close()


@test(55, "success-panel Momgyeot CTA flushes pending draft")
def t55(c):
    page = c.page()
    secret = "성공 화면에서 이동하기 직전 문장"
    type_text(page, secret)
    page.evaluate("() => { document.getElementById('td-success').hidden = false;"
                  " const a = document.getElementById('td-go');"
                  " a.removeAttribute('target'); a.setAttribute('href', '#part1'); }")
    page.click("#td-go")
    got = stored(page)
    assert got is not None and got["text"] == secret, f"성공 화면 CTA 가 flush 하지 않음: {got}"


@test(56, "manual-panel Momgyeot CTA flushes pending draft")
def t56(c):
    page = c.page()
    secret = "수동 복사 화면에서 이동하기 직전 문장"
    type_text(page, secret)
    page.evaluate("() => { document.getElementById('td-manual').hidden = false;"
                  " const a = document.querySelector('#td-manual .td-go');"
                  " a.removeAttribute('target'); a.setAttribute('href', '#part1'); }")
    page.click("#td-manual .td-go")
    got = stored(page)
    assert got is not None and got["text"] == secret, f"수동 화면 CTA 가 flush 하지 않음: {got}"


@test(57, "flush failure blocks the first click, second click proceeds")
def t57(c):
    page = c.page(init_scripts=[BREAK_SET])
    type_text(page, "저장이 안 되는 상태의 문장")
    settle(page)
    assert page.is_visible("#td-notice")
    page.evaluate("() => { const a = document.getElementById('td-go-edit');"
                  " a.removeAttribute('target'); a.setAttribute('href', '#part1'); }")
    before = page.url
    page.click("#td-go-edit")                   # 1차: 막히고 안내만
    page.wait_for_timeout(200)
    assert page.url == before, f"flush 실패인데 첫 클릭에 그대로 이동함: {page.url}"
    assert "임시 보관은 하지 못했어요" in page.inner_text("#td-notice")
    page.click("#td-go-edit")                   # 2차: 사용자가 계속하기로 했다
    page.wait_for_timeout(200)
    assert page.url.endswith("#part1"), f"두 번째 클릭에도 이동하지 않음: {page.url}"


# ── 9. Task 3 Revision 2.1 — clean 탭 외부 삭제 ──────────────────────────────
def _clean_deleted_tabs(c):
    """A/B 두 탭이 같은 draft 를 열고, A 는 편집 없이 B 가 삭제한 상태."""
    ctx, a, b = _two_tabs(c, draft("다른 탭이 지울 공통 문장", age_ms=1 * HOUR))
    delete_from(b)
    a.wait_for_function("() => document.getElementById('td-text').value === ''")
    return ctx, a, b


def _point_to_hash(page, sel):
    page.evaluate("(s) => { const a = document.querySelector(s);"
                  " a.removeAttribute('target'); a.setAttribute('href', '#part1'); }", sel)


@test(58, "clean external delete clears editor and persisted UI without a conflict")
def t58(c):
    ctx, a, b = _clean_deleted_tabs(c)
    assert a.is_hidden("#td-conflict"), "편집이 없는 탭인데 충돌을 물었다"
    assert a.input_value("#td-text") == ""
    assert stored(a) is None
    assert a.is_hidden("#td-sub")
    assert a.is_hidden("#td-meta")
    assert a.is_hidden("#td-restored")
    assert a.is_disabled("#td-copy")
    ctx.close()


@test(59, "clean external delete — editor CTA must not resurrect the draft")
def t59(c):
    ctx, a, b = _clean_deleted_tabs(c)
    _point_to_hash(a, "#td-go-edit")
    a.click("#td-go-edit")
    a.wait_for_timeout(900)
    assert stored(a) is None, "이동 CTA 의 flush 가 지워진 draft 를 되살렸다"
    ctx.close()


@test(60, "clean external delete — copy-success CTA must not resurrect the draft")
def t60(c):
    ctx, a, b = _clean_deleted_tabs(c)
    a.evaluate("() => { document.getElementById('td-success').hidden = false; }")
    _point_to_hash(a, "#td-go")
    a.click("#td-go")
    a.wait_for_timeout(900)
    assert stored(a) is None, "복사 성공 CTA 의 flush 가 지워진 draft 를 되살렸다"
    ctx.close()


@test(61, "clean external delete — manual-copy CTA must not resurrect the draft")
def t61(c):
    ctx, a, b = _clean_deleted_tabs(c)
    a.evaluate("() => { document.getElementById('td-manual').hidden = false; }")
    _point_to_hash(a, "#td-manual .td-go")
    a.click("#td-manual .td-go")
    a.wait_for_timeout(900)
    assert stored(a) is None, "수동 복사 CTA 의 flush 가 지워진 draft 를 되살렸다"
    ctx.close()


# ── 10. Task 3 Revision 3 — 파트 진입 CTA (발견성) ──────────────────────────
JUMP_PARTS = ["part1", "part2", "part3", "part4", "part5"]


def _section(html, pid):
    import re
    m = re.search(r'<section id="%s" class="chapter">(.*?)</section>' % pid, html, re.S)
    return m.group(1) if m else None


@test(62, "jump CTA appears exactly once in each of part1..part5")
def t62(c):
    html = (DOCS / PAGE).read_text(encoding="utf-8")
    assert html.count('class="td-jump"') == 5, html.count('class="td-jump"')
    for pid in JUMP_PARTS:
        body = _section(html, pid)
        assert body is not None, f"{pid} 섹션 없음"
        assert body.count('class="td-jump"') == 1, f"{pid}: {body.count('class=\"td-jump\"')}개"
    for pid in ("prologue", "epilogue"):
        body = _section(html, pid)
        assert body is not None and body.count('class="td-jump"') == 0, f"{pid} 에 CTA 가 들어감"


@test(63, "every jump CTA href is exactly #td-widget")
def t63(c):
    import re
    html = (DOCS / PAGE).read_text(encoding="utf-8")
    hrefs = re.findall(r'class="td-jump-link" href="([^"]*)"', html)
    assert len(hrefs) == 5, hrefs
    assert all(h == "#td-widget" for h in hrefs), hrefs


@test(64, "jump CTA sits immediately after the chapter header")
def t64(c):
    import re
    html = (DOCS / PAGE).read_text(encoding="utf-8")
    for pid in JUMP_PARTS:
        body = _section(html, pid)
        assert re.search(r'</header>\s*<aside class="td-jump"', body), f"{pid}: header 직후가 아님"


@test(65, "clicking the CTA brings the widget into the viewport (Chromium + WebKit)")
def t65(c):
    def check(browser, label):
        ctx = browser.new_context(viewport={"width": 390, "height": 844},
                                  is_mobile=True, has_touch=True)
        page = ctx.new_page(); page.set_default_timeout(25000)
        page.goto(f"{c.base}/{PAGE}#part3", wait_until="load")
        page.wait_for_selector("#td-widget")
        page.wait_for_timeout(1200)                      # 레이아웃 안정 대기
        page.click('#part3 .td-jump-link')
        # html { scroll-behavior: smooth } 때문에 6만px 스크롤이 애니메이션된다.
        # 고정 대기 대신 scrollY 가 멈출 때까지 기다린다 (Chromium ~1.8s, WebKit ~0.5s).
        prev, settled = -1, False
        for _ in range(40):
            page.wait_for_timeout(250)
            y = page.evaluate("() => Math.round(scrollY)")
            if y == prev:
                settled = True
                break
            prev = y
        assert settled, f"{label}: 스크롤이 10초 안에 멈추지 않음"
        r = page.evaluate("""() => {
          const w = document.getElementById('td-widget');
          const b = w.getBoundingClientRect();
          const el = document.elementFromPoint(b.x + b.width / 2, b.y + 30);
          return { inViewport: b.top < innerHeight && b.bottom > 0,
                   y: Math.round(b.y),
                   inside: el ? w.contains(el) : false,
                   hit: el ? (el.id || el.tagName) : null };
        }""")
        ctx.close()
        assert r["inViewport"], f"{label}: 위젯이 뷰포트 밖 {r}"
        assert r["inside"], f"{label}: hit-test 가 위젯 밖 {r}"
    check(c.browser, "chromium")
    wk = c.pw.webkit.launch()
    try:
        check(wk, "webkit")
    finally:
        wk.close()


@test(66, "jump CTA is absent from the theory book and the classic layout")
def t66(c):
    for name in ("book-modern.html", "book.html", "practice.html", "index.html"):
        html = (DOCS / name).read_text(encoding="utf-8")
        assert 'class="td-jump"' not in html, f"{name} 에 CTA 가 들어감"
        assert "TAEDAM_JUMP" not in html, f"{name} 에 placeholder 잔여"


@test(67, "jump CTA text meets WCAG AA contrast in light and dark")
def t67(c):
    js = """() => {
      const P = v => v.match(/\\d+(\\.\\d+)?/g).slice(0, 3).map(Number);
      const L = r => { const f = r.map(v => { v /= 255;
        return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
        return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]; };
      const ratio = (x, y) => { const a = L(P(x)), b = L(P(y));
        return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); };
      const card = document.querySelector('.td-jump');
      const bg = getComputedStyle(card).backgroundColor;
      return {
        link: ratio(getComputedStyle(card.querySelector('.td-jump-link')).color, bg),
        head: ratio(getComputedStyle(card.querySelector('.td-jump-h')).color, bg),
        body: ratio(getComputedStyle(card.querySelector('.td-jump-b')).color, bg),
      };
    }"""
    for theme in ("light", "dark"):
        page = c.page(init_scripts=[
            "try{localStorage.setItem('mamgyeot-theme', %s);}catch(e){}" % json.dumps(theme)])
        r = page.evaluate(js)
        for k, v in r.items():
            assert v >= 4.5, f"{theme} .td-jump-{k} 대비 {v:.2f}:1 (AA 4.5 미달)"


@test(68, "widget remains a single instance and its logic is untouched")
def t68(c):
    html = (DOCS / PAGE).read_text(encoding="utf-8")
    assert html.count('id="td-widget"') == 1
    assert html.count("mg_taegyo_draft_v1") == 1
    # CTA 는 JS 를 추가하지 않는다
    import re
    for m in re.finditer(r'<aside class="td-jump".*?</aside>', html, re.S):
        blk = m.group(0)
        assert "<script" not in blk and "onclick" not in blk, "CTA 에 JS 가 붙음"


# ── 10. 상단 빠른 체험 경로 ─────────────────────────────────────────────────

@test(69, "top quick-entry CTA exists once, above the widget")
def t69(c):
    html = (DOCS / PAGE).read_text(encoding="utf-8")
    assert html.count('class="td-top"') == 1, "상단 CTA 는 하나여야 한다"
    top = html.index('class="td-top"')
    widget = html.index('id="td-widget"')
    assert top < widget, "상단 CTA 가 위젯보다 뒤에 있다"
    # 본문(첫 파트)보다도 앞이어야 읽기 전에 보인다
    assert top < html.index('id="part1"'), "상단 CTA 가 본문 뒤에 있다"


@test(70, "top CTA points at the existing widget and does not duplicate it")
def t70(c):
    html = (DOCS / PAGE).read_text(encoding="utf-8")
    import re
    m = re.search(r'<aside class="td-top".*?</aside>', html, re.S)
    assert m, "상단 CTA 마크업을 찾지 못했다"
    blk = m.group(0)
    assert 'href="#td-widget"' in blk, blk
    # 위젯은 여전히 하나뿐이다 — 복제하지 않았다
    assert html.count('id="td-widget"') == 1
    assert html.count("mg_taegyo_draft_v1") == 1
    # CTA 에 JS·본문·개인정보가 붙지 않는다
    assert "<script" not in blk and "onclick" not in blk
    assert "textarea" not in blk
    assert "http" not in blk, "상단 CTA 는 외부로 나가지 않는다"


@test(71, "top CTA renders and scrolls to the widget (Chromium)")
def t71(c):
    page = c.page()
    link = page.locator("aside.td-top a.td-top-link")
    assert link.count() == 1
    assert link.is_visible()
    page.goto(f"{c.base}/{PAGE}", wait_until="domcontentloaded")
    page.wait_for_selector("aside.td-top")
    page.click("aside.td-top a.td-top-link")
    page.wait_for_function(
        "() => { const e = document.getElementById('td-widget');"
        " if (!e) return false; const r = e.getBoundingClientRect();"
        " return r.top < window.innerHeight && r.bottom > 0; }",
        timeout=8000,
    )


@test(72, "adding the top CTA removed no existing content")
def t72(c):
    html = (DOCS / PAGE).read_text(encoding="utf-8")
    # 기존 구조가 모두 그대로 있다
    for anchor in ["prologue", "part1", "part2", "part3", "part4", "part5", "td-widget"]:
        assert f'id="{anchor}"' in html, f"{anchor} 가 사라졌다"
    # 파트별 진입 CTA 5개도 그대로다
    assert html.count('class="td-jump"') == 5, html.count('class="td-jump"')
    # 위젯의 무-네트워크 계약 유지
    for banned in ["fetch(", "XMLHttpRequest", "sendBeacon", "clipboard.readText"]:
        assert banned not in html, banned


@test(73, "the top CTA is absent from the theory book and the classic layout")
def t73(c):
    for other in ["book-modern.html", "book.html", "practice.html", "index.html"]:
        path = DOCS / other
        if not path.exists():
            continue
        html = path.read_text(encoding="utf-8")
        assert "td-top" not in html, f"{other} 에 상단 CTA 가 들어갔다"
        assert 'id="td-widget"' not in html, f"{other} 에 위젯이 들어갔다"


@test(74, "top CTA text meets WCAG AA contrast in light and dark")
def t74(c):
    # 67 번과 같은 계산을 상단 CTA 카드에 적용한다.
    js = """() => {
      const P = v => v.match(/\\d+(\\.\\d+)?/g).slice(0, 3).map(Number);
      const L = r => { const f = r.map(v => { v /= 255;
        return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
        return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]; };
      const ratio = (x, y) => { const a = L(P(x)), b = L(P(y));
        return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); };
      const card = document.querySelector('aside.td-top');
      const bg = getComputedStyle(card).backgroundColor;
      return {
        link: ratio(getComputedStyle(card.querySelector('.td-top-link')).color, bg),
        head: ratio(getComputedStyle(card.querySelector('.td-top-h')).color, bg),
        body: ratio(getComputedStyle(card.querySelector('.td-top-b')).color, bg),
      };
    }"""
    for theme in ("light", "dark"):
        page = c.page(init_scripts=[
            "try{localStorage.setItem('mamgyeot-theme', %s);}catch(e){}" % json.dumps(theme)])
        r = page.evaluate(js)
        for k, v in r.items():
            assert v >= 4.5, f"{theme} {k}: {v:.2f}:1"


# ── 러너 ─────────────────────────────────────────────────────────────────────
def main(argv):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("FAIL  playwright 가 없습니다. pip install playwright && playwright install chromium")
        return 2

    if not (DOCS / PAGE).exists():
        print(f"FAIL  {DOCS / PAGE} 가 없습니다. 먼저 python3 _build_html.py 를 실행하세요.")
        return 2

    wanted = {int(a) for a in argv if a.isdigit()} or None
    httpd, base = start_server()
    passed, failed = [], []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            c = Ctx(browser, base, pw)
            for num, name, fn in TESTS:
                if wanted and num not in wanted:
                    continue
                try:
                    fn(c)
                    passed.append(num)
                    print(f"  PASS  {num:>2}  {name}")
                except Exception as e:
                    failed.append((num, name, e))
                    print(f"  FAIL  {num:>2}  {name}\n          {type(e).__name__}: {e}")
            browser.close()
    finally:
        httpd.shutdown()

    total = len(passed) + len(failed)
    print(f"\n{len(passed)}/{total} passed")
    if failed:
        print("\n실패 목록:")
        for num, name, e in failed:
            print(f"  {num}. {name} — {type(e).__name__}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
