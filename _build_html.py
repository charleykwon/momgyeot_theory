#!/usr/bin/env python3
"""Build single-file HTML edition of 맘곁 태교 이론편."""

import re
from pathlib import Path

DOCS = Path(__file__).parent / "docs"
# GitHub Pages는 /docs 폴더를 서빙. 마크다운 소스와 HTML 출력이 같은 폴더에 공존.
# .nojekyll로 Jekyll 파싱이 차단되어 .md 파일은 그대로 소스로 보존된다.
OUT = DOCS / "book.html"
DOCS.mkdir(exist_ok=True)

CHAPTERS = [
    ("prologue", "prologue.md", "들어가며", None),
    ("ch1", "01-why-now.md", "태교는 왜 지금 다시 필요할까", "1장"),
    ("ch2", "02-sajudang-intro.md", "사주당 이씨", "2장"),
    ("ch3", "03-modern-medicine.md", "현대 의학이 보는 태아의 발달", "3장"),
    ("ch4", "04-pregnancy-living.md", "임신 중의 식·운동·생활", "4장"),
    ("ch5", "05-five-senses-and-emotion.md", "오감으로 만나는 태아", "5장"),
    ("ch6", "06-mothers-emotion.md", "엄마의 감정은 태아의 환경이 된다", "6장"),
    ("ch7", "07-family-taegyo.md", "가족의 태교", "7장"),
    ("ch8", "08-father-taegyo.md", "아빠의 태교", "8장"),
    ("ch9", "09-good-vs-burdensome-taegyo.md", "좋은 태교와 부담스러운 태교의 차이", "9장"),
    ("ch10", "10-bridge-to-practice.md", "맘곁 태교의 다섯 원칙", "10장"),
    ("epilogue", "epilogue.md", "닫으며", None),
    ("appendix-a", "appendix-a-mapping.md", "『태교신기』 35절 전문 — 사주당 이씨와 현대 의학의 대화", "부록 A"),
    ("appendix-b", "appendix-b-checklist.md", "임신 280일 환경 점검 체크리스트", "부록 B"),
    ("appendix-c", "appendix-c-bibliography.md", "참고문헌", "부록 C"),
    ("appendix-d", "appendix-d-glossary.md", "도움 요청 가이드 · 용어집 · 빠른 찾아보기", "부록 D"),
    ("appendix-e", "appendix-e-series.md", "맘곁 태교 시리즈 안내", "부록 E"),
]


def strip_revision_note(text: str) -> str:
    """Drop the author-only revision note block from a chapter."""
    return re.sub(
        r"\n---\s*\n##\s*revision note.*?(?=\n---\s*\n|\Z)",
        "\n",
        text,
        flags=re.DOTALL,
    )


def parse_footnote_defs(text: str):
    """Pull out [^N]: definitions; return (text_without_defs, {n: def})."""
    defs = {}

    def grab(m):
        defs[m.group(1)] = m.group(2).strip()
        return ""

    text = re.sub(r"^\[\^(\d+)\]:\s*(.+)$", grab, text, flags=re.MULTILINE)
    return text, defs


def escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def replace_inline_footnotes(html_text: str, chapter_id: str, counter: dict) -> str:
    """Replace [^N] markers with linked superscripts.

    `counter` is mutated to track how many times each footnote number has been
    referenced in this chapter so each ref id stays unique in the document.
    """

    def repl(m):
        n = m.group(1)
        counter[n] = counter.get(n, 0) + 1
        suffix = "" if counter[n] == 1 else f"-{counter[n]}"
        return (
            f'<sup class="fn-ref">'
            f'<a href="#fn-{chapter_id}-{n}" '
            f'id="fnref-{chapter_id}-{n}{suffix}">{n}</a>'
            f"</sup>"
        )

    return re.sub(r"\[\^(\d+)\]", repl, html_text)


def apply_inline_markdown(text: str) -> str:
    """Apply minimal inline markdown after escape_html: links + bold + italic.

    `[text](url)` -> <a>; **bold** -> <strong>; *italic* -> <em>.
    Footnote markers `[^N]` must be substituted before this runs since they
    look like the link pattern but aren't.
    """
    # Markdown links: [text](url). Allow url with any non-paren chars.
    text = re.sub(
        r"\[([^\[\]]+?)\]\(([^()\s]+)\)",
        lambda m: f'<a href="{m.group(2)}" target="_blank" rel="noopener">{m.group(1)}</a>',
        text,
    )
    # Bold then italic. Bold first so ** isn't eaten by italic *.
    text = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    # Highlight pen markers. Allow multi-line spans (poetic line breaks).
    #   ==text==        yellow (주요 명제)
    #   =/text/=        peach  (마음·정서)
    #   =+text+=        sage   (실천 권고)
    text = re.sub(r"=/(.+?)/=", r'<mark class="pen-peach">\1</mark>', text, flags=re.DOTALL)
    text = re.sub(r"=\+(.+?)\+=", r'<mark class="pen-sage">\1</mark>', text, flags=re.DOTALL)
    text = re.sub(r"==(.+?)==", r'<mark class="pen-yellow">\1</mark>', text, flags=re.DOTALL)
    return text


def md_to_html(text: str, chapter_id: str):
    text = strip_revision_note(text)
    # Drop the leading H1 (chapter title is provided separately)
    text = re.sub(r"^#\s+.+\n", "", text, count=1)
    # Capture footnote defs from anywhere first (including 참고 자료 section)
    text, fn_defs = parse_footnote_defs(text)
    fn_counter: dict = {}
    # Then drop the 참고 자료 author-facing section entirely. Its [^N]: defs
    # were already extracted; the prose around them is editor-only meta.
    text = re.sub(
        r"\n---\s*\n##\s*참고\s*자료.*$",
        "",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(r"\n##\s*참고\s*자료.*$", "", text, flags=re.DOTALL)

    # Pre-extract markdown tables (header | sep | body…) to opaque markers.
    # Each marker is restored to a <table> when the line loop encounters it.
    table_map: dict = {}

    def render_table(block: str) -> str | None:
        rows = [l for l in block.split("\n") if l.strip().startswith("|")]
        if len(rows) < 2:
            return None

        def parse_row(line: str) -> list[str]:
            inner = line.strip().strip("|")
            return [c.strip() for c in inner.split("|")]

        header = parse_row(rows[0])
        sep_cells = parse_row(rows[1])
        if not all(re.match(r"^:?-+:?$", c) for c in sep_cells if c):
            return None
        body = [parse_row(r) for r in rows[2:]]
        if len(header) == 0:
            return None
        out_html = ['<table class="data">', "<thead><tr>"]
        for c in header:
            out_html.append(f"<th>{escape_html(c)}</th>")
        out_html.append("</tr></thead><tbody>")
        for row in body:
            out_html.append("<tr>")
            for c in row:
                cell = escape_html(c)
                cell = replace_inline_footnotes(cell, chapter_id, fn_counter)
                cell = apply_inline_markdown(cell)
                out_html.append(f"<td>{cell}</td>")
            out_html.append("</tr>")
        out_html.append("</tbody></table>")
        return "\n".join(out_html)

    def table_replacer(m):
        block = m.group(0)
        html = render_table(block)
        if html is None:
            return block
        marker = f"\x00TBL{len(table_map)}\x00"
        table_map[marker] = html
        return marker + "\n\n"

    text = re.sub(
        r"(?:^\|[^\n]*\|[ \t]*\n){2,}",
        table_replacer,
        text,
        flags=re.MULTILINE,
    )

    # Pre-extract :::raw ... ::: blocks for verbatim HTML passthrough.
    raw_map: dict = {}

    def raw_replacer(m):
        marker = f"\x00RAW{len(raw_map)}\x00"
        raw_map[marker] = m.group(1)
        return marker + "\n\n"

    text = re.sub(
        r"^:::raw\s*\n(.*?)\n:::\s*$",
        raw_replacer,
        text,
        flags=re.DOTALL | re.MULTILINE,
    )

    # Sub-heading collection for drawer accordion TOC
    sub_headings: list = []
    sub_counter = [0]

    out = []
    para = []
    in_list = False
    in_blockquote = False
    blockquote_lines = []

    def flush_para():
        nonlocal para
        if not para:
            return
        joined = "\n".join(para).strip()
        if not joined:
            para = []
            return
        # Escape HTML, then re-allow our footnote markup later
        joined = escape_html(joined)
        joined = replace_inline_footnotes(joined, chapter_id, fn_counter)
        joined = apply_inline_markdown(joined)
        # Single newlines inside a paragraph become <br> for poetic line breaks
        joined = joined.replace("\n", "<br>\n")
        out.append(f"<p>{joined}</p>")
        para = []

    def flush_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    def flush_blockquote():
        nonlocal in_blockquote, blockquote_lines
        if in_blockquote:
            processed = []
            for l in blockquote_lines:
                line_html = escape_html(l)
                line_html = replace_inline_footnotes(line_html, chapter_id, fn_counter)
                line_html = apply_inline_markdown(line_html)
                processed.append(line_html)
            content = "<br>\n".join(processed)
            out.append(f'<blockquote class="meta-note">{content}</blockquote>')
            blockquote_lines = []
            in_blockquote = False

    for raw in text.split("\n"):
        line = raw.rstrip()
        stripped = line.strip()

        if stripped in table_map:
            flush_para()
            flush_list()
            flush_blockquote()
            out.append(table_map[stripped])
            continue
        if stripped in raw_map:
            flush_para()
            flush_list()
            flush_blockquote()
            out.append(raw_map[stripped])
            continue
        if stripped == "":
            flush_para()
            flush_list()
            flush_blockquote()
            continue
        if stripped == "---":
            flush_para()
            flush_list()
            flush_blockquote()
            out.append('<hr class="section-break">')
            continue
        if stripped.startswith("### "):
            flush_para()
            flush_list()
            flush_blockquote()
            heading = escape_html(stripped[4:])
            out.append(f'<h4 class="subhead-2">{heading}</h4>')
            continue
        if stripped.startswith("## "):
            flush_para()
            flush_list()
            flush_blockquote()
            heading = escape_html(stripped[3:])
            sub_counter[0] += 1
            sub_id = f"{chapter_id}-s{sub_counter[0]}"
            sub_headings.append((sub_id, heading))
            out.append(f'<h3 id="{sub_id}" class="subhead">{heading}</h3>')
            continue
        if stripped.startswith("- "):
            flush_para()
            flush_blockquote()
            if not in_list:
                out.append('<ul class="bullets">')
                in_list = True
            item = escape_html(stripped[2:])
            item = replace_inline_footnotes(item, chapter_id, fn_counter)
            item = apply_inline_markdown(item)
            out.append(f"<li>{item}</li>")
            continue
        if stripped.startswith("> "):
            flush_para()
            flush_list()
            in_blockquote = True
            blockquote_lines.append(stripped[2:])
            continue
        # default: paragraph line
        flush_blockquote()
        flush_list()
        para.append(stripped)

    flush_para()
    flush_list()
    flush_blockquote()

    body = "\n".join(out)

    if fn_defs:
        items = []
        for n in sorted(fn_defs.keys(), key=int):
            d = escape_html(fn_defs[n])
            # Re-allow inline emphasis markers commonly used in citations
            d = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", d)
            d = re.sub(r"`([^`]+)`", r"<code>\1</code>", d)
            items.append(
                f'<li id="fn-{chapter_id}-{n}">{d} '
                f'<a class="fn-back" href="#fnref-{chapter_id}-{n}" '
                f'aria-label="본문으로 돌아가기">↩</a></li>'
            )
        body += (
            '\n<aside class="footnotes">\n'
            '<h4>각주</h4>\n<ol>\n'
            + "\n".join(items)
            + "\n</ol>\n</aside>"
        )

    return body, sub_headings


def build():
    # 챕터별 캐릭터 이미지 매핑 (graceful degradation — 파일 없으면 자동 비표시)
    chapter_illust = {
        "ch1":  ("mom-pregnant.png",  "임산부 일러스트"),
        "ch3":  ("fetus-3.png",       "태아 일러스트"),
        "ch5":  ("fetus-2.png",       "태아 일러스트"),
        "ch6":  ("mom-pregnant.png",  "임산부 일러스트"),
        "ch7":  ("family-faces.jpg",  "가족이 함께 둘러앉은 일러스트"),
        "ch8":  ("couple-heart.png",  "부부와 하트 일러스트"),
        "ch10": ("fetus-4.png",       "태아 일러스트"),
        "epilogue":  ("father-face.png", "아빠 얼굴 일러스트"),
    }

    toc_items = []
    sections = []
    drawer_items = []
    for cid, fname, title, num in CHAPTERS:
        text = (DOCS / fname).read_text(encoding="utf-8")
        body, subs = md_to_html(text, cid)
        label = f"{num} — {title}" if num else title
        toc_items.append(f'<li><a href="#{cid}">{escape_html(label)}</a></li>')

        # 챕터 헤더 일러스트 (파일 있으면 표시, 없으면 onerror로 자동 숨김)
        illust_html = ""
        if cid in chapter_illust:
            img_file, img_alt = chapter_illust[cid]
            illust_html = (
                f'<figure class="chapter-illust illust">'
                f'<img src="./images/{img_file}" alt="{escape_html(img_alt)}" '
                f"onerror=\"this.closest('.chapter-illust').style.display='none'\">"
                f"</figure>"
            )

        if num:
            header = (
                '<header class="chapter-header">'
                f'{illust_html}'
                f'<span class="chapter-num">{escape_html(num)}</span>'
                f'<h2 class="chapter-title">{escape_html(title)}</h2>'
                "</header>"
            )
        else:
            header = (
                '<header class="chapter-header">'
                f'{illust_html}'
                f'<h2 class="chapter-title">{escape_html(title)}</h2>'
                "</header>"
            )
        section_class = "chapter is-appendix" if cid.startswith("appendix-") else "chapter"
        sections.append(
            f'<section id="{cid}" class="{section_class}">\n{header}\n'
            f'<div class="chapter-body">\n{body}\n</div>\n</section>'
        )
        # Build drawer accordion item
        drawer_items.append(_build_drawer_item(cid, num, title, subs))

    toc_html = (
        '<nav class="toc"><h2>차례</h2><ol>\n'
        + "\n".join(toc_items)
        + "\n</ol></nav>"
    )
    chapters_html = "\n".join(sections)
    drawer_toc_html = (
        '<ol class="drawer-toc-list">\n'
        + "\n".join(drawer_items)
        + "\n</ol>"
    )

    template = (
        TEMPLATE.replace("{{TOC}}", toc_html)
        .replace("{{CHAPTERS}}", chapters_html)
        .replace("{{DRAWER_TOC}}", drawer_toc_html)
    )
    OUT.write_text(template, encoding="utf-8")
    print(f"wrote {OUT} ({len(template):,} bytes)")

    # Index redirect for GitHub Pages root URL.
    index_path = OUT.parent / "index.html"
    index_path.write_text(INDEX_REDIRECT, encoding="utf-8")
    # .nojekyll prevents GitHub Pages from running Jekyll on the output.
    (OUT.parent / ".nojekyll").write_text("", encoding="utf-8")


def _build_drawer_item(cid: str, num, title: str, subs: list) -> str:
    parts = [f'<li class="toc-item">', '<div class="toc-row">']
    parts.append(f'<a class="toc-link" href="#{cid}">')
    if num:
        parts.append(f'<span class="toc-num">{escape_html(num)}</span>')
    parts.append(f'<span class="toc-title">{escape_html(title)}</span>')
    parts.append("</a>")
    if subs:
        parts.append(
            f'<button class="toc-expand" type="button" '
            f'data-target="{cid}-subs" aria-label="펼치기" aria-expanded="false">▾</button>'
        )
    parts.append("</div>")
    if subs:
        parts.append(f'<ol id="{cid}-subs" class="toc-subs" hidden>')
        for sid, stext in subs:
            parts.append(f'<li><a href="#{sid}">{stext}</a></li>')
        parts.append("</ol>")
    parts.append("</li>")
    return "".join(parts)


INDEX_REDIRECT = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>
(function(){try{var s=localStorage.getItem('mamgyeot-theme');var d=s?(s==='dark'):(window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches);if(d)document.documentElement.classList.add('dark');}catch(e){}})();
</script>
<meta http-equiv="refresh" content="0; url=./book.html">
<title>맘곁 태교 — 이론편</title>
<meta name="description" content="사주당 이씨와 오늘의 의학이 같은 자리에서 만나는 책. 『맘곁 태교 — 이론편』. 권의철·최소라 공저, 바비즈코리아.">
<meta name="author" content="권의철, 최소라">
<meta property="og:title" content="맘곁 태교 — 이론편">
<meta property="og:description" content="사주당 이씨와 오늘의 의학이 같은 자리에서 만난다.">
<meta property="og:type" content="book">
<meta property="og:locale" content="ko_KR">
<link rel="canonical" href="./book.html">
<style>
  :root { --bg: #faf6f0; --text: #2c2826; --accent: #8c6e4e; }
  :root.dark { --bg: #1a1a1a; --text: #eaeaea; --accent: #8a9a5b; }
  body { font-family: 'Apple SD Gothic Neo', system-ui, sans-serif;
         display: flex; align-items: center; justify-content: center;
         min-height: 100vh; margin: 0;
         background: var(--bg); color: var(--text);
         transition: background-color 0.3s ease, color 0.3s ease; }
  a { color: var(--accent); text-decoration: none; border-bottom: 1px dotted var(--accent); }
</style>
</head>
<body>
<p>맘곁 태교 — 이론편으로 이동합니다 · <a href="./book.html">바로 가기</a></p>
</body>
</html>
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>
// 다크모드 — FOUC 방지를 위해 stylesheet 로드 전에 dark class 적용
(function(){
  try {
    var saved = localStorage.getItem('mamgyeot-theme');
    var dark = saved
      ? (saved === 'dark')
      : (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
    if (dark) document.documentElement.classList.add('dark');
  } catch(e) {}
})();
</script>
<title>맘곁 태교 — 이론편 · 사주당 이씨와 오늘의 의학이 같은 자리에서 만난다</title>
<meta name="description" content="사주당 이씨와 오늘의 의학이 같은 자리에서 만나는 책. 『맘곁 태교 — 이론편』. 권의철·최소라 공저, 바비즈코리아. 1800년 사주당 이씨의 『태교신기』를 오늘의 부모를 위한 언어로 다시 읽다.">
<meta name="author" content="권의철, 최소라">
<meta name="keywords" content="태교, 사주당, 태교신기, 임신, 모성건강, 맘곁, 바비즈코리아">
<meta property="og:title" content="맘곁 태교 — 이론편">
<meta property="og:description" content="사주당 이씨와 오늘의 의학이 같은 자리에서 만난다. 권의철·최소라 공저.">
<meta property="og:type" content="book">
<meta property="og:locale" content="ko_KR">
<meta property="og:site_name" content="맘곁 태교">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="맘곁 태교 — 이론편">
<meta name="twitter:description" content="사주당 이씨와 오늘의 의학이 같은 자리에서 만난다.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@300;400;500;600;700&family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #faf6f0;
  --bg-soft: #fffcf6;
  --text: #2c2826;
  --text-soft: #5b5450;
  --accent: #8c6e4e;
  --line: #e3dccf;
  --serif: 'Noto Serif KR', 'Apple SD Gothic Neo', 'Nanum Myeongjo', serif;
  --sans: 'Noto Sans KR', 'Apple SD Gothic Neo', system-ui, -apple-system, sans-serif;

  /* 다크모드 친화 변수 (라이트 기본값) */
  --bg-flow-from: #f3ece2;
  --card-modern-bg: #ffffff;
  --ring-bg: rgba(255, 252, 246, 0.4);
  --pen-yellow: rgba(245, 211, 100, 0.5);
  --pen-peach: rgba(244, 178, 154, 0.45);
  --pen-sage: rgba(167, 198, 169, 0.45);
  --shadow-soft: rgba(0, 0, 0, 0.06);
  --shadow-medium: rgba(0, 0, 0, 0.12);
  --shadow-strong: rgba(0, 0, 0, 0.18);
  --toast-bg: #2c2826;
  --toast-text: #ffffff;
  --backdrop: rgba(20, 18, 16, 0.32);
  --bg-flow-to-text: #ffffff;
  --mandala-center-text: #ffffff;
  --back-to-top-text: #ffffff;
}

/* 다크모드 — 야간 사용 환경. 완전 검정 회피, 올리브 액센트, 충분한 대비. */
:root.dark {
  --bg: #1a1a1a;
  --bg-soft: #1e1e1e;
  --text: #eaeaea;
  --text-soft: #b0b0b0;
  --accent: #8a9a5b;
  --line: #2c2c2c;

  --bg-flow-from: #2a2a2a;
  --card-modern-bg: #232323;
  --ring-bg: rgba(40, 40, 40, 0.6);
  --pen-yellow: rgba(245, 211, 100, 0.28);
  --pen-peach: rgba(244, 178, 154, 0.24);
  --pen-sage: rgba(167, 198, 169, 0.24);
  --shadow-soft: rgba(0, 0, 0, 0.3);
  --shadow-medium: rgba(0, 0, 0, 0.4);
  --shadow-strong: rgba(0, 0, 0, 0.55);
  --toast-bg: #2a2826;
  --toast-text: #eaeaea;
  --backdrop: rgba(0, 0, 0, 0.55);
  --bg-flow-to-text: #f5f5f0;
  --mandala-center-text: #f5f5f0;
  --back-to-top-text: #1a1a1a;
}

/* 모드 전환 부드럽게 */
body, .chapter, .drawer-nav, table.data, blockquote.meta-note,
.infographic-cards .card, .infographic-flow .flow-side,
.infographic-circle .ring, .infographic-mandala .mandala-petal,
.infographic-mandala .mandala-center, #drawer, #menu-toggle, #dark-toggle {
  transition: background-color 0.28s ease, color 0.28s ease, border-color 0.28s ease;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--serif);
  font-size: 17px;
  line-height: 1.95;
  font-weight: 400;
  word-break: keep-all;
  overflow-wrap: break-word;
}
.book {
  max-width: 680px;
  margin: 0 auto;
  padding: 64px 24px 96px;
}
.cover {
  text-align: center;
  padding: 80px 0 64px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 32px;
}
.front-page {
  text-align: center;
  padding: 80px 24px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 0;
}
.front-page.half-title .ft-brand {
  font-family: var(--sans);
  font-size: 12px;
  letter-spacing: 0.45em;
  color: var(--accent);
  text-transform: uppercase;
  margin-bottom: 24px;
}
.front-page.half-title .ft-main {
  font-size: 30px;
  font-weight: 500;
  margin: 0 0 14px;
  letter-spacing: -0.005em;
}
.front-page.half-title .ft-sub {
  font-size: 13.5px;
  color: var(--text-soft);
  letter-spacing: 0.08em;
  margin: 0;
}
.front-page.dedication {
  padding: 110px 24px;
  font-style: italic;
  color: var(--text-soft);
  font-size: 16px;
  line-height: 2;
}
.front-page.dedication .dedi { margin: 0; }
@media print {
  .front-page { page-break-after: always; }
}
.cover .brand {
  font-family: var(--sans);
  font-size: 13px;
  letter-spacing: 0.45em;
  color: var(--accent);
  text-transform: uppercase;
  margin-bottom: 28px;
}
.cover h1 {
  font-size: 44px;
  font-weight: 500;
  margin: 0 0 18px;
  letter-spacing: -0.01em;
}
.cover .sub {
  font-size: 15px;
  color: var(--text-soft);
  letter-spacing: 0.3em;
}
.cover .cover-tagline {
  margin-top: 24px;
  font-family: var(--serif);
  font-size: 14px;
  color: var(--text-soft);
  letter-spacing: 0.05em;
  font-style: italic;
}
.cover .cover-authors {
  margin-top: 36px;
  font-family: var(--sans);
  font-size: 13px;
  color: var(--text);
  letter-spacing: 0.15em;
}
.cover .cover-publisher {
  margin-top: 10px;
  font-family: var(--sans);
  font-size: 12px;
  color: var(--text-soft);
  letter-spacing: 0.15em;
}
.front-page.half-title .ft-authors {
  margin-top: 28px;
  font-family: var(--sans);
  font-size: 12.5px;
  color: var(--text);
  letter-spacing: 0.15em;
}
.toc {
  margin: 48px 0;
  padding: 32px 0;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}
.toc h2 {
  font-family: var(--sans);
  font-size: 13px;
  letter-spacing: 0.35em;
  color: var(--accent);
  font-weight: 500;
  margin: 0 0 22px;
  text-transform: uppercase;
}
.toc ol {
  list-style: none;
  padding: 0;
  margin: 0;
}
.toc li {
  margin: 6px 0;
  font-size: 16px;
}
.toc a {
  color: var(--text);
  text-decoration: none;
  border-bottom: 1px dotted transparent;
  padding-bottom: 2px;
  transition: color 0.15s, border-color 0.15s;
}
.toc a:hover {
  color: var(--accent);
  border-bottom-color: var(--accent);
}
.chapter {
  margin: 96px 0 80px;
  scroll-margin-top: 32px;
}
.chapter-header {
  margin-bottom: 48px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--line);
}
.chapter-num {
  display: block;
  font-family: var(--sans);
  font-size: 11px;
  letter-spacing: 0.45em;
  color: var(--accent);
  margin-bottom: 14px;
  text-transform: uppercase;
}
.chapter-title {
  font-size: 28px;
  font-weight: 500;
  margin: 0;
  line-height: 1.45;
  letter-spacing: -0.005em;
}
.chapter-body p {
  margin: 0 0 1.5em;
}
.chapter-body .subhead {
  font-size: 19px;
  font-weight: 500;
  margin: 2.4em 0 1em;
  color: var(--accent);
  letter-spacing: -0.005em;
}
.chapter-body .subhead-2 {
  font-size: 16px;
  font-weight: 500;
  margin: 1.8em 0 0.7em;
  color: var(--text);
  letter-spacing: -0.003em;
  font-family: var(--sans);
}
.chapter-body hr.section-break {
  border: 0;
  border-top: 1px solid var(--line);
  margin: 2.2em auto;
  width: 60px;
}
.chapter-body ul.bullets {
  margin: 1.2em 0 1.5em;
  padding-left: 1.4em;
}
.chapter-body ul.bullets li {
  margin: 0.5em 0;
}
.chapter-body blockquote.meta-note {
  margin: 1.6em 0;
  padding: 14px 22px;
  background: var(--bg-soft);
  border-left: 3px solid var(--line);
  font-size: 14.5px;
  color: var(--text-soft);
  font-family: var(--sans);
  line-height: 1.75;
}
sup.fn-ref {
  font-size: 10.5px;
  vertical-align: super;
  line-height: 0;
  margin-left: 1px;
}
sup.fn-ref a {
  color: var(--accent);
  text-decoration: none;
  padding: 0 2px;
}
sup.fn-ref a:hover { text-decoration: underline; }
aside.footnotes {
  margin: 3em 0 1em;
  padding: 24px 0 0;
  border-top: 1px solid var(--line);
  font-family: var(--sans);
  font-size: 13.5px;
  line-height: 1.75;
  color: var(--text-soft);
}
aside.footnotes h4 {
  font-size: 11.5px;
  letter-spacing: 0.35em;
  font-weight: 500;
  color: var(--accent);
  margin: 0 0 16px;
  text-transform: uppercase;
}
aside.footnotes ol {
  padding-left: 1.4em;
  margin: 0;
}
aside.footnotes li {
  margin: 0.7em 0;
  padding-left: 4px;
}
aside.footnotes a.fn-back {
  color: var(--accent);
  text-decoration: none;
  margin-left: 6px;
  font-size: 14px;
}
aside.footnotes a.fn-back:hover { text-decoration: underline; }
aside.footnotes em { font-style: italic; }
aside.footnotes code {
  font-family: var(--sans);
  background: var(--bg);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12.5px;
}
table.data {
  width: 100%;
  border-collapse: collapse;
  margin: 1.8em 0 2em;
  font-family: var(--sans);
  font-size: 14px;
  line-height: 1.6;
  border: 1px solid var(--line);
}
table.data thead { background: var(--bg-soft); }
table.data th, table.data td {
  text-align: left;
  vertical-align: top;
  padding: 11px 13px;
  border: 1px solid var(--line);
  word-break: keep-all;
}
table.data th {
  font-weight: 500;
  color: var(--accent);
  font-size: 12.5px;
  letter-spacing: 0.02em;
}
table.data td { color: var(--text); }
@media (max-width: 600px) {
  table.data { font-size: 13px; }
  table.data th, table.data td { padding: 9px 10px; }
}
@media print {
  table.data { font-size: 9pt; page-break-inside: avoid; }
}
.chapter-body a {
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px solid var(--line);
}
.chapter-body a:hover {
  border-bottom-color: var(--accent);
}
.chapter-body strong {
  font-weight: 600;
  color: var(--text);
}
.chapter-body em {
  font-style: italic;
}
.chapter-body mark {
  color: inherit;
  padding: 0 2px;
  border-radius: 2px;
}
.chapter-body mark.pen-yellow {
  background: linear-gradient(180deg,
    transparent 0%, transparent 55%,
    var(--pen-yellow) 55%, var(--pen-yellow) 92%,
    transparent 92%);
}
.chapter-body mark.pen-peach {
  background: linear-gradient(180deg,
    transparent 0%, transparent 55%,
    var(--pen-peach) 55%, var(--pen-peach) 92%,
    transparent 92%);
}
.chapter-body mark.pen-sage {
  background: linear-gradient(180deg,
    transparent 0%, transparent 55%,
    var(--pen-sage) 55%, var(--pen-sage) 92%,
    transparent 92%);
}
@media print {
  .chapter-body mark.pen-yellow { background: rgba(245, 211, 100, 0.35); }
  .chapter-body mark.pen-peach { background: rgba(244, 178, 154, 0.3); }
  .chapter-body mark.pen-sage { background: rgba(167, 198, 169, 0.3); }
}

/* =========== Hamburger menu + Drawer + Back-to-top + Resume =========== */
#menu-toggle {
  position: fixed; top: 18px; left: 18px; z-index: 50;
  width: 44px; height: 44px; padding: 0;
  background: var(--bg-soft); border: 1px solid var(--line);
  border-radius: 50%; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
  box-shadow: 0 2px 8px var(--shadow-soft);
  transition: background 0.18s, transform 0.18s;
}
#menu-toggle:hover { background: var(--bg); }
#menu-toggle:active { transform: scale(0.95); }
#menu-toggle span {
  display: block; width: 18px; height: 1.5px;
  background: var(--accent); border-radius: 1px;
}

#dark-toggle {
  position: fixed; top: 18px; right: 18px; z-index: 50;
  width: 44px; height: 44px; padding: 0;
  background: var(--bg-soft); border: 1px solid var(--line);
  border-radius: 50%; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; line-height: 1;
  box-shadow: 0 2px 8px var(--shadow-soft);
  transition: background 0.18s, transform 0.18s, box-shadow 0.18s;
}
#dark-toggle:hover {
  background: var(--bg);
  box-shadow: 0 3px 12px var(--shadow-medium);
}
#dark-toggle:active { transform: scale(0.95); }
#dark-toggle .dark-icon-dark { display: inline-block; }
#dark-toggle .dark-icon-light { display: none; }
:root.dark #dark-toggle .dark-icon-dark { display: none; }
:root.dark #dark-toggle .dark-icon-light { display: inline-block; }

#drawer-backdrop {
  position: fixed; inset: 0; z-index: 55;
  background: var(--backdrop);
  opacity: 0; pointer-events: none;
  transition: opacity 0.28s ease;
}
#drawer-backdrop.visible { opacity: 1; pointer-events: auto; }

#drawer {
  position: fixed; top: 0; left: 0; z-index: 60;
  width: 340px; max-width: 88vw; height: 100vh;
  background: var(--bg-soft); border-right: 1px solid var(--line);
  transform: translateX(-100%);
  transition: transform 0.28s ease;
  display: flex; flex-direction: column; overflow: hidden;
  box-shadow: 4px 0 24px var(--shadow-medium);
}
#drawer[aria-hidden="false"] { transform: translateX(0); }

.drawer-head {
  padding: 18px 20px; border-bottom: 1px solid var(--line);
  display: flex; align-items: center; justify-content: space-between;
}
.drawer-title {
  font-family: var(--sans); font-size: 12px; letter-spacing: 0.4em;
  color: var(--accent); text-transform: uppercase; font-weight: 500;
}
#drawer-close {
  background: none; border: none; font-size: 26px; line-height: 1;
  color: var(--text-soft); cursor: pointer; padding: 0 4px;
}
#drawer-close:hover { color: var(--text); }

.drawer-nav { flex: 1; overflow-y: auto; padding: 8px 0 24px; }
.drawer-toc-list { list-style: none; padding: 0; margin: 0; }
.toc-item { border-bottom: 1px solid var(--line); }
.toc-row { display: flex; align-items: stretch; }
.toc-link {
  flex: 1; padding: 12px 16px; text-decoration: none; color: var(--text);
  display: flex; flex-direction: column; gap: 3px; font-size: 14px;
}
.toc-link:hover { background: var(--bg); }
.toc-link .toc-num {
  font-family: var(--sans); font-size: 10.5px; letter-spacing: 0.25em;
  color: var(--accent); text-transform: uppercase;
}
.toc-link .toc-title { font-family: var(--serif); line-height: 1.4; }
.toc-expand {
  background: none; border: none; border-left: 1px solid var(--line);
  width: 40px; cursor: pointer; color: var(--text-soft);
  font-size: 13px; transition: transform 0.2s, background 0.2s;
}
.toc-expand:hover { background: var(--bg); }
.toc-expand.expanded { transform: rotate(180deg); }

.toc-subs {
  list-style: none; padding: 4px 0 10px; margin: 0;
  background: var(--bg);
}
.toc-subs li { margin: 0; }
.toc-subs a {
  display: block; padding: 7px 16px 7px 28px; font-size: 13px;
  color: var(--text-soft); text-decoration: none;
  border-left: 2px solid transparent;
}
.toc-subs a:hover {
  color: var(--text); border-left-color: var(--accent); background: var(--bg-soft);
}

#back-to-top {
  position: fixed; bottom: 24px; right: 24px; z-index: 40;
  width: 46px; height: 46px; border-radius: 50%; padding: 0;
  background: var(--accent); color: var(--back-to-top-text); border: none;
  font-size: 20px; cursor: pointer;
  box-shadow: 0 4px 14px var(--shadow-strong);
  transition: transform 0.2s, opacity 0.25s, background 0.28s ease;
}
#back-to-top:hover { transform: translateY(-2px); }
#back-to-top[hidden] { display: none; }

#resume-toast {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  z-index: 70; max-width: 92vw;
  background: var(--toast-bg); color: var(--toast-text);
  padding: 13px 18px; border-radius: 8px;
  display: flex; align-items: center; gap: 10px;
  font-size: 14px;
  box-shadow: 0 6px 22px var(--shadow-strong);
}
#resume-toast[hidden] { display: none; }
.resume-msg { flex: 1; line-height: 1.5; }
.resume-btn {
  background: rgba(255,255,255,0.14); color: #fff;
  border: 1px solid rgba(255,255,255,0.22);
  padding: 6px 12px; border-radius: 5px;
  font-size: 13px; cursor: pointer;
  font-family: var(--sans);
  white-space: nowrap;
}
.resume-btn:hover { background: rgba(255,255,255,0.24); }
.resume-btn.resume-yes {
  background: var(--accent); border-color: var(--accent);
}
.resume-btn.resume-yes:hover {
  background: #a18260;
}

@media (max-width: 600px) {
  #menu-toggle { top: 12px; left: 12px; width: 40px; height: 40px; }
  #dark-toggle { top: 12px; right: 12px; width: 40px; height: 40px; font-size: 16px; }
  #back-to-top { bottom: 16px; right: 16px; width: 40px; height: 40px; font-size: 17px; }
  #resume-toast { bottom: 16px; padding: 11px 14px; gap: 8px; font-size: 13px; }
}

@media print {
  /* 인쇄 시 다크 변수 무시하고 라이트 팔레트 강제 */
  :root.dark {
    --bg: #ffffff; --bg-soft: #ffffff; --text: #000000; --text-soft: #555555;
    --accent: #555555; --line: #cccccc;
  }
  #menu-toggle, #dark-toggle, #drawer, #drawer-backdrop, #back-to-top, #resume-toast { display: none !important; }
}

/* =========== 맘곁 캐릭터 일러스트 =========== */
/* 이미지 파일이 없으면 자동으로 영역이 사라진다 (onerror = display:none on parent figure). */
.illust { margin: 0; text-align: center; }
.illust img { max-width: 100%; height: auto; display: block; margin: 0 auto; }

/* 표지 — 로고 + 메인 일러스트 */
.cover .cover-logo {
  width: 64px; height: 64px;
  margin: 0 auto 18px;
  border-radius: 8px;
  overflow: hidden;
}
.cover .cover-logo img { width: 100%; height: 100%; object-fit: contain; }
.cover .cover-hero {
  margin: 28px auto 8px;
  max-width: 480px;
}
.cover .cover-hero img { width: 100%; height: auto; }

/* 챕터 헤더 일러스트 — 챕터 번호·제목 옆 작은 캐릭터 */
.chapter-illust {
  width: 92px; height: 92px;
  margin: 0 auto 14px;
}
.chapter-illust img { width: 100%; height: 100%; object-fit: contain; }

/* 시기별 태아 진행 — 3장 발달표 위 */
.fetus-progress {
  display: flex;
  gap: 6px;
  align-items: flex-end;
  justify-content: space-between;
  margin: 1.6em 0 1.2em;
  padding: 14px 10px 10px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: 8px;
}
.fetus-progress .stage {
  flex: 1;
  text-align: center;
  font-family: var(--sans);
  font-size: 11.5px;
  color: var(--text-soft);
  letter-spacing: 0.02em;
}
.fetus-progress .stage img {
  width: 100%; max-width: 70px;
  height: auto;
  margin: 0 auto 6px;
  display: block;
}
.fetus-progress .stage-label { display: block; }
@media (max-width: 600px) {
  .fetus-progress { gap: 3px; padding: 10px 6px 8px; }
  .fetus-progress .stage { font-size: 10.5px; }
  .fetus-progress .stage img { max-width: 52px; }
}
@media print {
  .fetus-progress { background: white; }
}
.chapter.is-appendix .chapter-num {
  color: #6b6358;
}
.chapter.is-appendix table.data {
  font-size: 13px;
}
@media (max-width: 700px) {
  .chapter.is-appendix table.data { font-size: 12px; }
  .chapter.is-appendix table.data th,
  .chapter.is-appendix table.data td { padding: 7px 8px; }
}

/* =========== Infographics =========== */
.infographic {
  margin: 2em auto;
  font-family: var(--sans);
  color: var(--text);
}
.infographic-caption {
  text-align: center;
  font-size: 12.5px;
  color: var(--text-soft);
  margin-top: 12px;
  letter-spacing: 0.02em;
}

/* 1. Concentric circles: 태아 ← 자궁 ← 엄마 ← 가족 ← 사회 */
.infographic-circle {
  position: relative;
  width: 360px;
  max-width: 90vw;
  aspect-ratio: 1 / 1;
  margin: 2em auto;
}
.infographic-circle .ring {
  position: absolute;
  border: 1.5px solid var(--accent);
  border-radius: 50%;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  font-size: 12.5px;
  color: var(--text-soft);
  padding-top: 7px;
  background: var(--ring-bg);
}
.infographic-circle .ring-society { width: 100%; height: 100%; left: 0; top: 0; }
.infographic-circle .ring-family  { width: 78%;  height: 78%;  left: 11%; top: 11%; }
.infographic-circle .ring-mother  { width: 58%;  height: 58%;  left: 21%; top: 21%; }
.infographic-circle .ring-uterus  { width: 38%;  height: 38%;  left: 31%; top: 31%; }
.infographic-circle .ring-fetus   {
  width: 18%; height: 18%; left: 41%; top: 41%;
  background: var(--accent);
  color: var(--bg-flow-to-text);
  align-items: center;
  padding-top: 0;
  font-size: 13px;
}

/* 2. 280-day timeline */
.infographic-timeline {
  display: flex;
  gap: 8px;
  border: 1px solid var(--line);
  border-radius: 6px;
  overflow: hidden;
}
.infographic-timeline .trimester {
  flex: 1;
  padding: 14px 14px;
  background: var(--bg-soft);
  border-right: 1px solid var(--line);
  font-size: 13px;
  line-height: 1.65;
}
.infographic-timeline .trimester:last-child { border-right: none; }
.infographic-timeline .t-label {
  font-weight: 600;
  color: var(--accent);
  margin-bottom: 6px;
  font-size: 12.5px;
  letter-spacing: 0.02em;
}
.infographic-timeline .t-content { color: var(--text); }

/* 3. Sajudang ↔ Modern medicine card pairs */
.infographic-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.infographic-cards .card-pair {
  display: grid;
  grid-template-columns: 1fr 32px 1fr;
  align-items: stretch;
  gap: 8px;
}
.infographic-cards .card {
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.55;
}
.infographic-cards .card.sajudang { background: var(--bg-soft); }
.infographic-cards .card.modern { background: var(--card-modern-bg); }
.infographic-cards .card-label {
  display: block;
  font-size: 10.5px;
  color: var(--accent);
  letter-spacing: 0.2em;
  margin-bottom: 4px;
  text-transform: uppercase;
}
.infographic-cards .card-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent);
  font-size: 16px;
}

/* 4. 부담 → 돌봄 flow */
.infographic-flow {
  display: grid;
  grid-template-columns: 1fr 40px 1fr;
  align-items: center;
  gap: 10px;
}
.infographic-flow .flow-side {
  padding: 16px 18px;
  border-radius: 8px;
  text-align: center;
  font-size: 14px;
  line-height: 1.55;
}
.infographic-flow .flow-from {
  background: var(--bg-flow-from);
  border: 1px solid var(--line);
  color: var(--text-soft);
}
.infographic-flow .flow-to {
  background: var(--accent);
  color: var(--bg-flow-to-text);
}
.infographic-flow .flow-arrow {
  text-align: center;
  font-size: 22px;
  color: var(--accent);
}
.infographic-flow .flow-label {
  display: block;
  font-size: 11px;
  letter-spacing: 0.18em;
  margin-bottom: 4px;
  opacity: 0.75;
  text-transform: uppercase;
}
.infographic-flow small {
  display: block;
  font-size: 12px;
  margin-top: 6px;
  opacity: 0.85;
}

/* 5. 다섯 원칙 만다라 */
.infographic-mandala {
  position: relative;
  width: 380px;
  max-width: 92vw;
  aspect-ratio: 1 / 1;
  margin: 2.4em auto;
}
.infographic-mandala .mandala-center {
  position: absolute;
  width: 38%;
  height: 38%;
  left: 31%;
  top: 31%;
  border-radius: 50%;
  background: var(--accent);
  color: var(--mandala-center-text);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  text-align: center;
  font-weight: 500;
  line-height: 1.4;
}
.infographic-mandala .mandala-petal {
  position: absolute;
  width: 31%;
  height: 31%;
  border-radius: 50%;
  border: 1.5px solid var(--accent);
  background: var(--bg-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--text);
  text-align: center;
  padding: 6px;
  line-height: 1.35;
}
.infographic-mandala .p1 { left: 34.5%; top: 0%; }
.infographic-mandala .p2 { left: 65%;   top: 22%; }
.infographic-mandala .p3 { left: 53%;   top: 64%; }
.infographic-mandala .p4 { left: 16%;   top: 64%; }
.infographic-mandala .p5 { left: 4%;    top: 22%; }

@media (max-width: 600px) {
  .infographic-cards .card-pair { grid-template-columns: 1fr; }
  .infographic-cards .card-arrow { display: none; }
  .infographic-flow { grid-template-columns: 1fr; }
  .infographic-flow .flow-arrow { transform: rotate(90deg); }
  .infographic-timeline { flex-direction: column; }
  .infographic-timeline .trimester { border-right: none; border-bottom: 1px solid var(--line); }
  .infographic-mandala { width: 320px; }
}
@media print {
  .infographic-circle .ring,
  .infographic-mandala .mandala-petal { background: white; }
  .infographic-flow .flow-to { background: #555; }
  .infographic-mandala .mandala-center { background: #555; }
  .infographic-cards .card.sajudang { background: #f8f8f8; }
}

@media (max-width: 600px) {
  body { font-size: 16px; line-height: 1.85; }
  .book { padding: 32px 20px 64px; }
  .cover { padding: 48px 0 32px; }
  .cover h1 { font-size: 30px; }
  .cover .sub { font-size: 13px; letter-spacing: 0.25em; }
  .chapter { margin: 64px 0; }
  .chapter-title { font-size: 23px; }
  .chapter-body .subhead { font-size: 17px; }
}

@media print {
  body { background: white; font-size: 11pt; line-height: 1.7; }
  .book { max-width: 100%; padding: 0; }
  .toc, .cover { page-break-after: always; }
  .chapter { page-break-before: always; margin: 0; padding: 24pt 0; }
  .chapter-header { border-bottom-color: #888; }
  a { color: inherit; text-decoration: none; }
  sup.fn-ref a { color: #555; }
  aside.footnotes { font-size: 9pt; }
}
</style>
</head>
<body>

<button id="menu-toggle" type="button" aria-label="차례 열기">
  <span></span><span></span><span></span>
</button>

<button id="dark-toggle" type="button" aria-label="다크모드 전환" title="다크모드 전환">
  <span class="dark-icon-dark" aria-hidden="true">🌙</span>
  <span class="dark-icon-light" aria-hidden="true">☀️</span>
</button>

<div id="drawer-backdrop"></div>

<aside id="drawer" aria-hidden="true">
  <header class="drawer-head">
    <span class="drawer-title">차례</span>
    <button id="drawer-close" type="button" aria-label="차례 닫기">×</button>
  </header>
  <nav class="drawer-nav">
{{DRAWER_TOC}}
  </nav>
</aside>

<button id="back-to-top" type="button" aria-label="맨 위로" hidden>↑</button>

<div id="resume-toast" hidden role="status">
  <span class="resume-msg">이전에 보시던 자리에서 이어 볼까요?</span>
  <button class="resume-btn resume-yes" type="button">이어서</button>
  <button class="resume-btn resume-no" type="button">처음부터</button>
</div>

<div class="book">
<header class="cover">
  <figure class="cover-logo illust"><img src="./images/logo.png" alt="맘곁 로고" onerror="this.closest('.cover-logo').style.display='none'"></figure>
  <div class="brand">맘곁</div>
  <h1>맘곁 태교</h1>
  <div class="sub">이론편</div>
  <figure class="cover-hero illust"><img src="./images/cover-illustration.png" alt="맘곁 태교 표지 일러스트 — 가족이 손을 잡고 함께 걷는 모습" onerror="this.closest('.cover-hero').style.display='none'"></figure>
  <div class="cover-tagline">사주당 이씨와 오늘의 의학이 같은 자리에서 만난다</div>
  <div class="cover-authors">권의철 · 최소라 공저</div>
  <div class="cover-publisher">펴낸곳 : 바비즈코리아</div>
</header>

<section class="front-page dedication">
  <p class="dedi">
    아이를 기다리는 모든 부모와<br>
    그 곁에 함께 머무는 사람들에게.
  </p>
</section>

{{TOC}}
{{CHAPTERS}}
</div>

<script>
(function() {
  'use strict';
  var STORAGE_KEY = 'mamgyeot-taegyo-section';
  var THEME_KEY = 'mamgyeot-theme';
  var menuToggle = document.getElementById('menu-toggle');
  var darkToggle = document.getElementById('dark-toggle');
  var drawer = document.getElementById('drawer');
  var drawerClose = document.getElementById('drawer-close');
  var drawerBackdrop = document.getElementById('drawer-backdrop');
  var backToTop = document.getElementById('back-to-top');
  var resumeToast = document.getElementById('resume-toast');

  // ---- Dark mode toggle ----
  function setTheme(isDark) {
    document.documentElement.classList.toggle('dark', isDark);
    try { localStorage.setItem(THEME_KEY, isDark ? 'dark' : 'light'); } catch (e) {}
    if (darkToggle) {
      darkToggle.setAttribute('aria-label',
        isDark ? '라이트 모드로 전환' : '다크 모드로 전환');
    }
  }
  if (darkToggle) {
    // 초기 aria-label은 현재 상태에 따라
    var startsDark = document.documentElement.classList.contains('dark');
    darkToggle.setAttribute('aria-label',
      startsDark ? '라이트 모드로 전환' : '다크 모드로 전환');
    darkToggle.addEventListener('click', function() {
      var isDark = !document.documentElement.classList.contains('dark');
      setTheme(isDark);
    });
  }
  // 시스템 선호가 바뀌면 따라간다(사용자가 명시적으로 저장한 적 없을 때만)
  if (window.matchMedia) {
    var mq = window.matchMedia('(prefers-color-scheme: dark)');
    var followSystem = function(e) {
      var saved;
      try { saved = localStorage.getItem(THEME_KEY); } catch (err) {}
      if (!saved) setTheme(e.matches);
    };
    if (mq.addEventListener) mq.addEventListener('change', followSystem);
    else if (mq.addListener) mq.addListener(followSystem);
  }

  // ---- Drawer open/close ----
  function openDrawer() {
    drawer.setAttribute('aria-hidden', 'false');
    drawerBackdrop.classList.add('visible');
    document.body.style.overflow = 'hidden';
  }
  function closeDrawer() {
    drawer.setAttribute('aria-hidden', 'true');
    drawerBackdrop.classList.remove('visible');
    document.body.style.overflow = '';
  }
  if (menuToggle) menuToggle.addEventListener('click', openDrawer);
  if (drawerClose) drawerClose.addEventListener('click', closeDrawer);
  if (drawerBackdrop) drawerBackdrop.addEventListener('click', closeDrawer);
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && drawer.getAttribute('aria-hidden') === 'false') {
      closeDrawer();
    }
  });

  // ---- Accordion expand/collapse ----
  var expandButtons = document.querySelectorAll('.toc-expand');
  expandButtons.forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      var target = document.getElementById(btn.getAttribute('data-target'));
      if (!target) return;
      var isHidden = target.hasAttribute('hidden');
      if (isHidden) {
        target.removeAttribute('hidden');
        btn.classList.add('expanded');
        btn.setAttribute('aria-expanded', 'true');
      } else {
        target.setAttribute('hidden', '');
        btn.classList.remove('expanded');
        btn.setAttribute('aria-expanded', 'false');
      }
    });
  });

  // ---- Close drawer on TOC link click ----
  document.querySelectorAll('.drawer-nav a').forEach(function(a) {
    a.addEventListener('click', function() {
      setTimeout(closeDrawer, 120);
    });
  });

  // ---- Back to top ----
  if (backToTop) {
    backToTop.addEventListener('click', function() {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    var ticking = false;
    window.addEventListener('scroll', function() {
      if (!ticking) {
        window.requestAnimationFrame(function() {
          if (window.scrollY > 400) backToTop.removeAttribute('hidden');
          else backToTop.setAttribute('hidden', '');
          ticking = false;
        });
        ticking = true;
      }
    }, { passive: true });
  }

  // ---- Resume reading: track current section ----
  var sections = document.querySelectorAll('section.chapter');
  var currentSection = null;
  if ('IntersectionObserver' in window && sections.length) {
    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          currentSection = entry.target.id;
        }
      });
      if (currentSection) {
        try { localStorage.setItem(STORAGE_KEY, currentSection); } catch (e) {}
      }
    }, { threshold: [0.2], rootMargin: '-80px 0px -55% 0px' });
    sections.forEach(function(s) { observer.observe(s); });
  }

  // ---- Show resume prompt on load (if applicable) ----
  function showResumePrompt() {
    if (!resumeToast) return;
    var saved;
    try { saved = localStorage.getItem(STORAGE_KEY); } catch (e) { return; }
    if (!saved) return;
    if (saved === 'prologue') return;  // start of book; no need to resume
    var target = document.getElementById(saved);
    if (!target) return;
    // Only show if user is currently near the top of the book
    if (window.scrollY > 200) return;

    var titleEl = target.querySelector('.chapter-title');
    var numEl = target.querySelector('.chapter-num');
    var label = '';
    if (numEl) label += numEl.textContent.trim();
    if (titleEl) {
      if (label) label += ' ';
      label += titleEl.textContent.trim();
    }
    var msgEl = resumeToast.querySelector('.resume-msg');
    if (msgEl && label) {
      msgEl.textContent = '이전에 보시던 「' + label + '」에서 이어 볼까요?';
    }
    resumeToast.removeAttribute('hidden');

    var yesBtn = resumeToast.querySelector('.resume-yes');
    var noBtn = resumeToast.querySelector('.resume-no');
    function dismiss() { resumeToast.setAttribute('hidden', ''); }
    if (yesBtn) yesBtn.addEventListener('click', function() {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      dismiss();
    }, { once: true });
    if (noBtn) noBtn.addEventListener('click', function() {
      try { localStorage.removeItem(STORAGE_KEY); } catch (e) {}
      dismiss();
    }, { once: true });
    setTimeout(dismiss, 12000);
  }
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(showResumePrompt, 600);
  } else {
    document.addEventListener('DOMContentLoaded', function() {
      setTimeout(showResumePrompt, 600);
    });
  }
})();
</script>

</body>
</html>
"""


if __name__ == "__main__":
    build()
