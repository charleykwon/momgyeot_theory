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

# 실천편 — 같은 빌더로 sibling 사이트 구성
PRACTICE_CHAPTERS = [
    ("prologue",  "practice/prologue.md",   "들어가며",                 None),
    ("part1",     "practice/part1.md",      "태아 이전의 마음 준비",    "PART 1"),
    ("part2",     "practice/part2.md",      "임신 초기 태교",           "PART 2"),
    ("part3",     "practice/part3.md",      "임신 중기 태교",           "PART 3"),
    ("part4",     "practice/part4.md",      "임신 후기 태교",           "PART 4"),
    ("part5",     "practice/part5.md",      "출산과 첫 만남",           "PART 5"),
    ("epilogue",  "practice/epilogue.md",   "닫으며",                   None),
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
        if stripped.startswith("##### "):
            flush_para()
            flush_list()
            flush_blockquote()
            heading = escape_html(stripped[6:])
            heading = apply_inline_markdown(heading)
            out.append(f'<h6 class="subhead-4">{heading}</h6>')
            continue
        if stripped.startswith("#### "):
            flush_para()
            flush_list()
            flush_blockquote()
            heading = escape_html(stripped[5:])
            heading = apply_inline_markdown(heading)
            out.append(f'<h5 class="subhead-3">{heading}</h5>')
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


# 이론편 챕터별 캐릭터 일러스트
THEORY_ILLUST = {
    "ch1":  ("mom-pregnant.png",  "임산부 일러스트"),
    "ch3":  ("fetus-3.png",       "태아 일러스트"),
    "ch5":  ("fetus-2.png",       "태아 일러스트"),
    "ch6":  ("mom-pregnant.png",  "임산부 일러스트"),
    "ch7":  ("family-faces.jpg",  "가족이 함께 둘러앉은 일러스트"),
    "ch8":  ("couple-heart.png",  "부부와 하트 일러스트"),
    "ch10": ("fetus-4.png",       "태아 일러스트"),
    "epilogue":  ("father-face.png", "아빠 얼굴 일러스트"),
}

THEORY_CTA = {
    "prologue": ("📖", "1장부터 천천히 읽어 보기",
                "오늘 한 장만 펴 봐도 충분합니다.", "#ch1"),
    "ch1": ("💬", "오늘 한 문장 태담하기",
            "배에 손을 얹고 \"나 여기 있어\" 한 마디로 시작해 보세요.", None),
    "ch2": ("📜", "사주당의 한 문장 적어 두기",
            "본문에서 마음에 닿은 한 줄을 메모장에 옮겨 적어 보세요.", None),
    "ch3": ("🩺", "다음 산전 진료에서 물어볼 한 가지 정하기",
            "이 장에서 궁금해진 점 하나를 검진 메모로 옮겨 두세요.", None),
    "ch4": ("🍽️", "내일 한 끼만 다르게 차려 보기",
            "거창한 식단보다 한 끼의 결이 부드러워지는 시도를 해 보세요.", None),
    "ch5": ("👂", "조용한 1분 — 아이의 청각에 닿기",
            "하루 한 번 1분, 배에 손을 얹고 같은 노래를 작게 들려주세요.", None),
    "ch6": ("🌿", "오늘의 감정에 한 줄 이름 붙이기",
            "\"오늘 내 마음의 색은 ___\" — 하루의 결을 짧게 메모해 보세요.", None),
    "ch7": ("🏠", "배우자·가족과 함께 이 장 읽기",
            "가족 한 사람에게 이 장의 한 문단을 보여 주세요.", None),
    "ch8": ("👨", "오늘 아빠의 한 행동 정하기",
            "배에 손 얹기, 함께 산책 한 번, 잠들기 전 한 마디 — 한 가지를 골라 보세요.", None),
    "ch9": ("⚖️", "지난 한 주의 태교를 한 줄로 정리하기",
            "잘한 것과 부담된 것을 같은 무게로 적어 보세요.", None),
    "ch10": ("✨", "다섯 원칙 중 한 가지 골라 한 주 살아 보기",
             "연결·반복·기록·다정한 생활·이해 가운데 가장 마음이 가는 하나로.", None),
    "epilogue": ("📱", "맘곁에서 일상으로 이어 가기",
                "책에서 만난 다섯 원칙을 하루 안으로 옮기는 자리 — 맘곁 사이트.",
                "https://www.momgyeot.com"),
}

# 실천편 PART별 "다음 행동" CTA — 실천 중심 책의 결에 맞춰 행동 카드
PRACTICE_CTA = {
    "prologue": ("✨", "오늘 한 마디 — 첫 인사",
                "\"안녕, 아가야. 엄마(아빠)야.\" 한 마디만 건네 봐도 시작입니다.", "#part1"),
    "part1": ("🌱", "임신을 준비하는 마음 정리하기",
              "오늘 배우자와 한 가지 — 식·운동·정서 중 — 함께 점검해 보세요.", None),
    "part2": ("📝", "초기 태담 한 줄 적어 두기",
              "보이지 않는 시기, 손편지처럼 한 문장만 남겨 보세요.", None),
    "part3": ("🤲", "태동 느낀 시간을 메모하기",
              "오늘 처음/가장 강하게 느낀 태동의 시간과 결을 기록해 보세요.", None),
    "part4": ("🌙", "출산 가방·출산 계획서 한 가지 정하기",
              "거창한 준비 대신 오늘 한 가지만 — 동선·신호·연락처 중 하나.", None),
    "part5": ("👶", "산후 회고 한 줄 — 이론편 부록 B로",
              "출산 직후의 결을 한 줄로 적어 두는 자리가 부록 B 4단계입니다.", "./book-modern.html#appendix-b"),
    "epilogue": ("📱", "맘곁과 함께 다음 시간으로",
                "임신·출산·육아의 결을 잇는 자리 — 맘곁 사이트로 이어 갑니다.",
                "https://www.momgyeot.com"),
}


def build_book(*, chapters, classic_filename, modern_filename,
               chapter_illust, chapter_cta,
               book_title, book_subtitle, book_tagline,
               cover_image, cover_image_alt,
               other_book_label, other_book_classic, other_book_modern,
               has_appendix=True):
    """한 책을 두 디자인으로 빌드한다 (classic + modern)."""
    toc_body_items = []
    toc_appendix_items = []
    sections = []
    drawer_items = []
    for cid, fname, title, num in chapters:
        text = (DOCS / fname).read_text(encoding="utf-8")
        body, subs = md_to_html(text, cid)
        label = f"{num} — {title}" if num else title
        toc_li = f'<li><a href="#{cid}">{escape_html(label)}</a></li>'
        if cid.startswith("appendix-"):
            toc_appendix_items.append(toc_li)
        else:
            toc_body_items.append(toc_li)

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
        # "다음 행동" CTA 카드 — 부록 외 챕터 본문 끝에 자동 주입
        cta_html = ""
        if cid in chapter_cta:
            icon, headline, sub, target = chapter_cta[cid]
            target_attr = f'href="{escape_html(target)}"' if target else 'href="#" onclick="return false;"'
            cta_html = (
                '<aside class="next-action" aria-label="다음 행동">\n'
                '  <span class="next-action-tag">다음 행동</span>\n'
                f'  <div class="next-action-icon" aria-hidden="true">{icon}</div>\n'
                '  <div class="next-action-text">\n'
                f'    <strong class="next-action-headline">{escape_html(headline)}</strong>\n'
                f'    <span class="next-action-sub">{escape_html(sub)}</span>\n'
                '  </div>\n'
                + (f'  <a class="next-action-link" {target_attr}>이동 →</a>\n' if target else '')
                + '</aside>'
            )
        sections.append(
            f'<section id="{cid}" class="{section_class}">\n{header}\n'
            f'<div class="chapter-body">\n{body}\n{cta_html}\n</div>\n</section>'
        )
        # Build drawer accordion item (본문/부록 분리)
        drawer_items.append((cid, _build_drawer_item(cid, num, title, subs)))

    if has_appendix and toc_appendix_items:
        toc_html = (
            '<nav class="toc">\n'
            '  <h2>차례</h2>\n'
            '  <div class="toc-group">\n'
            '    <h3 class="toc-group-label">본문</h3>\n'
            '    <ol class="toc-body">\n'
            + "\n".join(toc_body_items)
            + '\n    </ol>\n'
            '  </div>\n'
            '  <div class="toc-group">\n'
            '    <h3 class="toc-group-label">부록</h3>\n'
            '    <ol class="toc-appendix">\n'
            + "\n".join(toc_appendix_items)
            + '\n    </ol>\n'
            '  </div>\n'
            '</nav>'
        )
    else:
        toc_html = (
            '<nav class="toc">\n'
            '  <h2>차례</h2>\n'
            '  <div class="toc-group">\n'
            '    <ol class="toc-body">\n'
            + "\n".join(toc_body_items)
            + '\n    </ol>\n'
            '  </div>\n'
            '</nav>'
        )
    chapters_html = "\n".join(sections)
    drawer_body_list = [html for cid, html in drawer_items if not cid.startswith("appendix-")]
    drawer_appendix_list = [html for cid, html in drawer_items if cid.startswith("appendix-")]
    if has_appendix and drawer_appendix_list:
        drawer_toc_html = (
            '<div class="drawer-group">\n'
            '<h4 class="drawer-group-label">본문</h4>\n'
            '<ol class="drawer-toc-list">\n'
            + "\n".join(drawer_body_list)
            + "\n</ol>\n"
            '</div>\n'
            '<div class="drawer-group">\n'
            '<h4 class="drawer-group-label">부록</h4>\n'
            '<ol class="drawer-toc-list">\n'
            + "\n".join(drawer_appendix_list)
            + "\n</ol>\n"
            '</div>'
        )
    else:
        drawer_toc_html = (
            '<ol class="drawer-toc-list">\n'
            + "\n".join(drawer_body_list)
            + "\n</ol>"
        )

    def fill(template_str: str, modern_target: bool) -> str:
        # 이 템플릿이 모던인지 클래식인지에 따라 theme-switcher 타겟이 달라진다
        theme_target = classic_filename if modern_target else modern_filename
        theme_label = "클래식" if modern_target else "모던"
        out = (template_str
               .replace("{{TOC}}", toc_html)
               .replace("{{CHAPTERS}}", chapters_html)
               .replace("{{DRAWER_TOC}}", drawer_toc_html)
               .replace("{{BOOK_TITLE}}", escape_html(book_title))
               .replace("{{BOOK_SUBTITLE}}", escape_html(book_subtitle))
               .replace("{{BOOK_TAGLINE}}", escape_html(book_tagline))
               .replace("{{COVER_IMAGE}}", escape_html(cover_image))
               .replace("{{COVER_IMAGE_ALT}}", escape_html(cover_image_alt))
               .replace("{{THEME_TARGET}}", escape_html(theme_target))
               .replace("{{THEME_LABEL}}", escape_html(theme_label))
               .replace("{{OTHER_BOOK_LABEL}}", escape_html(other_book_label))
               .replace("{{OTHER_BOOK_TARGET}}",
                        escape_html(other_book_modern if modern_target else other_book_classic)))
        return out

    classic_html = fill(TEMPLATE, modern_target=False)
    classic_path = DOCS / classic_filename
    classic_path.write_text(classic_html, encoding="utf-8")
    print(f"wrote {classic_path} ({len(classic_html):,} bytes)")

    modern_html = fill(TEMPLATE_MODERN, modern_target=True)
    modern_path = DOCS / modern_filename
    modern_path.write_text(modern_html, encoding="utf-8")
    print(f"wrote {modern_path} ({len(modern_html):,} bytes)")


def build():
    """이론편 + 실천편 두 책을 모두 빌드한다."""
    # 이론편
    build_book(
        chapters=CHAPTERS,
        classic_filename="book.html",
        modern_filename="book-modern.html",
        chapter_illust=THEORY_ILLUST,
        chapter_cta=THEORY_CTA,
        book_title="맘곁 태교 — 이론편",
        book_subtitle="이론편",
        book_tagline="사주당 이씨와 오늘의 의학이 같은 자리에서 만난다",
        cover_image="book-cover.png",
        cover_image_alt="맘곁 태교 표지 — 권의철·최소라 공저, 가족 일러스트 표지",
        other_book_label="실천편",
        other_book_classic="practice.html",
        other_book_modern="practice-modern.html",
        has_appendix=True,
    )
    # 실천편
    build_book(
        chapters=PRACTICE_CHAPTERS,
        classic_filename="practice.html",
        modern_filename="practice-modern.html",
        chapter_illust={},  # 실천편은 캐릭터 매핑 없음 (필요 시 추가)
        chapter_cta=PRACTICE_CTA,
        book_title="맘곁 태교 — 실천편",
        book_subtitle="실천편",
        book_tagline="말을 거는 순간, 사랑이 시작됩니다",
        cover_image="book-cover-practice.png",
        cover_image_alt="맘곁 태교 — 실천편 표지",
        other_book_label="이론편",
        other_book_classic="book.html",
        other_book_modern="book-modern.html",
        has_appendix=False,
    )

    # Landing page
    index_path = DOCS / "index.html"
    index_path.write_text(INDEX_REDIRECT, encoding="utf-8")
    print(f"wrote {index_path} ({len(INDEX_REDIRECT):,} bytes)")
    # .nojekyll prevents GitHub Pages from running Jekyll on the output.
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")


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
<title>맘곁 태교 — 사주당 이씨와 오늘의 의학 · 이론편 · 실천편</title>
<meta name="description" content="혼자 버티는 시간이 아니라 함께 지나가는 시간. 1800년 사주당 이씨의 시선과 오늘의 의학·실천을 한자리에서 만나는 두 권의 책.">
<meta name="author" content="권의철, 최소라">
<meta name="keywords" content="태교, 사주당, 태교신기, 임신, 출산, 모성건강, 태담, 맘곁, 바비즈코리아">
<meta name="theme-color" content="#7a5e40">
<meta property="og:title" content="맘곁 태교 — 사주당 이씨와 오늘의 의학">
<meta property="og:description" content="혼자 버티는 시간이 아니라 함께 지나가는 시간. 이론편 · 실천편을 한자리에서.">
<meta property="og:type" content="website">
<meta property="og:locale" content="ko_KR">
<meta property="og:site_name" content="맘곁 태교">
<meta property="og:url" content="https://taegyo.momgyeot.com/">
<meta property="og:image" content="https://taegyo.momgyeot.com/images/book-cover.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="맘곁 태교 — 사주당 이씨와 오늘의 의학">
<meta name="twitter:description" content="혼자 버티는 시간이 아니라 함께 지나가는 시간.">
<meta name="twitter:image" content="https://taegyo.momgyeot.com/images/book-cover.png">
<link rel="canonical" href="https://taegyo.momgyeot.com/">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "name": "맘곁",
      "alternateName": "Momgyeot",
      "url": "https://www.momgyeot.com",
      "logo": "https://taegyo.momgyeot.com/images/logo.png",
      "parentOrganization": { "@type": "Organization", "name": "바비즈코리아" }
    },
    {
      "@type": "Book",
      "name": "맘곁 태교 — 이론편",
      "author": [
        { "@type": "Person", "name": "권의철" },
        { "@type": "Person", "name": "최소라" }
      ],
      "publisher": { "@type": "Organization", "name": "바비즈코리아" },
      "inLanguage": "ko",
      "url": "https://taegyo.momgyeot.com/book-modern.html",
      "image": "https://taegyo.momgyeot.com/images/book-cover.png",
      "description": "사주당 이씨의 『태교신기』와 오늘의 의학·DOHaD가 같은 자리에서 만나는 이해의 책. 10장 본문 + 부록 A–E.",
      "datePublished": "2026-04-28"
    },
    {
      "@type": "Book",
      "name": "맘곁 태교 — 실천편",
      "author": [
        { "@type": "Person", "name": "권의철" },
        { "@type": "Person", "name": "최소라" }
      ],
      "publisher": { "@type": "Organization", "name": "바비즈코리아" },
      "inLanguage": "ko",
      "url": "https://taegyo.momgyeot.com/practice-modern.html",
      "image": "https://taegyo.momgyeot.com/images/book-cover-practice.png",
      "description": "임신 준비부터 첫 만남까지 — 시기별 태담과 일상 실천 5개 PART."
    }
  ]
}
</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@500;700&family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #f5f3f0; --bg-soft: #ffffff;
    --text: #1a1612; --text-soft: #45403b;
    --accent: #7a5e40; --accent-rose: #c49db0;
    --accent-sage: #8fa985; --accent-mustard: #c8a35a;
    --line: #d9d0bf;
    --serif: 'Noto Serif KR', serif;
    --sans: 'Noto Sans KR', 'Apple SD Gothic Neo', system-ui, -apple-system, sans-serif;
  }
  :root.dark {
    --bg: #1c1c1c; --bg-soft: #262626;
    --text: #ececec; --text-soft: #b6b2ad;
    --accent: #d49380; --accent-rose: #d4adbe;
    --accent-sage: #a3bc99; --accent-mustard: #d6b676;
    --line: #333;
  }
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body {
    margin: 0;
    font-family: var(--sans);
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
    word-break: keep-all;
    -webkit-font-smoothing: antialiased;
  }
  .landing { max-width: 760px; margin: 0 auto; padding: 56px 24px 80px; }

  /* 헤더 */
  .lp-header {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 36px;
  }
  .lp-brand {
    font-family: var(--sans); font-size: 12px;
    letter-spacing: 0.36em; color: var(--accent);
    text-transform: uppercase; font-weight: 700;
  }
  .lp-dark-toggle {
    width: 40px; height: 40px;
    background: var(--bg-soft); border: 1px solid var(--line);
    border-radius: 50%; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px;
  }
  .lp-dark-toggle .dark-icon-light { display: none; }
  :root.dark .lp-dark-toggle .dark-icon-dark { display: none; }
  :root.dark .lp-dark-toggle .dark-icon-light { display: inline-block; }

  /* 히어로 */
  .lp-hero {
    text-align: center;
    margin-bottom: 56px;
    padding: 36px 24px 40px;
    background: var(--bg-soft);
    border: 1px solid var(--line);
    border-radius: 18px;
  }
  .lp-hero-cover {
    max-width: 280px; margin: 0 auto 24px;
    border-radius: 12px; overflow: hidden;
    box-shadow: 0 8px 28px rgba(0,0,0,0.12);
  }
  .lp-hero-cover img { display: block; width: 100%; height: auto; }
  .lp-hero h1 {
    font-family: var(--serif);
    font-size: 38px; font-weight: 700;
    margin: 0 0 8px;
    letter-spacing: -0.02em; line-height: 1.25;
  }
  .lp-hero-sub {
    font-size: 14px; color: var(--accent);
    letter-spacing: 0.25em; font-weight: 600;
    text-transform: uppercase;
  }
  .lp-hero-tagline {
    margin: 18px auto 0; max-width: 520px;
    font-size: 16px; color: var(--text);
    line-height: 1.7;
  }
  .lp-hero-meta {
    margin-top: 22px;
    font-size: 13px; color: var(--text-soft);
    letter-spacing: 0.06em;
  }
  /* 히어로 CTA 3개 — 앱 / 이론편 / 실천편 */
  .lp-hero-ctas {
    margin: 26px auto 0; max-width: 540px;
    display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px;
  }
  .lp-cta {
    display: flex; flex-direction: column; align-items: center; gap: 4px;
    padding: 12px 10px;
    text-decoration: none;
    border-radius: 10px;
    font-family: var(--sans);
    transition: transform 0.18s, box-shadow 0.18s;
  }
  .lp-cta:hover { transform: translateY(-2px); }
  .lp-cta-emoji { font-size: 22px; line-height: 1; }
  .lp-cta-label { font-size: 13px; font-weight: 700; letter-spacing: -0.005em; }
  .lp-cta-sub { font-size: 11px; color: var(--text-soft); letter-spacing: 0.02em; }
  .lp-cta-app {
    background: var(--accent); color: #fff;
    box-shadow: 0 4px 14px rgba(122, 94, 64, 0.28);
  }
  .lp-cta-app .lp-cta-sub { color: rgba(255,255,255,0.78); }
  :root.dark .lp-cta-app { box-shadow: 0 4px 14px rgba(212, 147, 128, 0.3); }
  .lp-cta-book {
    background: var(--bg);
    border: 1px solid var(--line);
    color: var(--text);
  }
  .lp-cta-book:hover { border-color: var(--accent); }
  @media (max-width: 480px) {
    .lp-hero-ctas { grid-template-columns: 1fr; gap: 8px; }
    .lp-cta { flex-direction: row; justify-content: center; padding: 14px; }
    .lp-cta-emoji { font-size: 18px; margin-right: 6px; }
    .lp-cta-sub { display: none; }
  }

  /* 두 책 카드 */
  .lp-books {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
    margin: 18px 0 22px;
  }
  .lp-book {
    display: grid;
    grid-template-columns: 100px 1fr;
    gap: 16px; align-items: stretch;
    padding: 18px;
    background: var(--bg-soft);
    border: 1px solid var(--line);
    border-radius: 14px;
    text-decoration: none;
    color: var(--text);
    transition: transform 0.18s, border-color 0.18s, box-shadow 0.18s;
  }
  .lp-book:hover {
    transform: translateY(-2px);
    border-color: var(--accent);
    box-shadow: 0 6px 18px rgba(0,0,0,0.08);
  }
  .lp-book-cover {
    margin: 0;
    border-radius: 8px; overflow: hidden;
    background: var(--bg);
    display: flex; align-items: center; justify-content: center;
    aspect-ratio: 5/7;
  }
  .lp-book-cover img { width: 100%; height: 100%; object-fit: cover; }
  /* 실천편 카드 — 가족 일러스트는 일러스트 배경색과 매칭, contain으로 4명+아기 모두 보이게 */
  .lp-book-cover--family {
    background: #788A1E;
  }
  .lp-book-cover--family img {
    object-fit: contain;
  }
  .lp-book-meta { display: flex; flex-direction: column; gap: 4px; }
  .lp-book-tag {
    font-size: 10.5px; font-weight: 700;
    letter-spacing: 0.22em; text-transform: uppercase;
    color: var(--accent);
  }
  .lp-book-title {
    margin: 2px 0 4px;
    font-family: var(--serif);
    font-size: 17px; font-weight: 700;
    line-height: 1.35;
    color: var(--text);
    letter-spacing: -0.005em;
  }
  .lp-book-desc {
    margin: 0; font-size: 13px;
    color: var(--text-soft); line-height: 1.6;
    flex: 1;
  }
  .lp-book-cta {
    margin-top: 8px;
    font-size: 13px; font-weight: 700;
    color: var(--accent);
  }

  /* 디자인 4링크 줄 */
  .lp-design-row {
    margin-top: 8px;
    padding: 14px 16px;
    background: var(--bg-soft);
    border: 1px dashed var(--line);
    border-radius: 10px;
    display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
    font-family: var(--sans);
    font-size: 12.5px;
  }
  .lp-design-label {
    font-weight: 700; letter-spacing: 0.18em;
    color: var(--text-soft); text-transform: uppercase;
    margin-right: 4px;
  }
  .lp-design-link {
    color: var(--text);
    text-decoration: none;
    padding: 5px 10px;
    border-radius: 6px;
    transition: background 0.15s;
  }
  .lp-design-link:hover { background: var(--bg); color: var(--accent); }

  /* 맘곁 앱 프로모 */
  .lp-app-card {
    display: flex; align-items: center; gap: 22px;
    padding: 22px 24px;
    background: var(--bg-soft);
    border: 1px solid var(--line);
    border-left: 4px solid var(--accent);
    border-radius: 14px;
  }
  .lp-app-qr {
    flex-shrink: 0; padding: 8px;
    background: #fff; border: 1px solid var(--line); border-radius: 10px;
    line-height: 0; text-decoration: none;
  }
  .lp-app-qr img { display: block; width: 140px; height: 140px; }
  .lp-app-meta { display: flex; flex-direction: column; gap: 14px; }
  .lp-app-stanza { margin: 0; font-size: 14.5px; line-height: 1.85; color: var(--text); }
  .lp-app-stanza strong { color: var(--accent); font-weight: 700; }
  .lp-app-link {
    align-self: flex-start;
    background: var(--accent); color: #fff;
    text-decoration: none; font-family: var(--sans);
    font-size: 14px; font-weight: 600;
    padding: 10px 16px; border-radius: 999px;
    transition: transform 0.18s;
  }
  .lp-app-link:hover { transform: translateY(-1px); }
  @media (max-width: 600px) {
    .lp-app-card { flex-direction: column; align-items: flex-start; gap: 16px; padding: 18px; }
    .lp-app-qr img { width: 120px; height: 120px; }
  }

  /* 섹션 */
  .lp-section { margin: 0 0 56px; }
  .lp-section h2 {
    font-family: var(--sans); font-size: 13px;
    letter-spacing: 0.32em; color: var(--accent);
    text-transform: uppercase; font-weight: 700;
    margin: 0 0 16px;
  }
  .lp-section h2::before { content: "❯ "; }
  .lp-section-lede {
    font-family: var(--serif);
    font-size: 19px; font-weight: 500;
    line-height: 1.7;
    color: var(--text);
    margin: 0 0 18px;
    letter-spacing: -0.005em;
  }

  /* 책 소개 */
  .lp-about p { font-size: 15px; line-height: 1.85; margin: 0 0 1em; color: var(--text); }

  /* 차례 미리보기 */
  .lp-toc-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 8px;
    list-style: none; padding: 0; margin: 0;
  }
  .lp-toc-grid li { margin: 0; }
  .lp-toc-grid a {
    display: block;
    padding: 12px 14px;
    background: var(--bg-soft);
    border: 1px solid var(--line);
    border-left: 3px solid var(--accent);
    border-radius: 8px;
    text-decoration: none;
    color: var(--text);
    font-size: 14px;
    line-height: 1.45;
    font-weight: 500;
    transition: border-color 0.15s, transform 0.15s;
  }
  .lp-toc-grid a:hover { transform: translateY(-1px); }
  .lp-toc-grid li:nth-child(5n+2) a { border-left-color: var(--accent-sage); }
  .lp-toc-grid li:nth-child(5n+3) a { border-left-color: var(--accent-rose); }
  .lp-toc-grid li:nth-child(5n+4) a { border-left-color: var(--accent-mustard); }
  .lp-toc-grid li:nth-child(5n+5) a { border-left-color: var(--accent); }
  .lp-toc-num {
    display: block;
    font-family: var(--sans); font-size: 10.5px;
    letter-spacing: 0.22em; text-transform: uppercase;
    color: var(--accent); font-weight: 700;
    margin-bottom: 2px;
  }

  /* 푸터 */
  .lp-footer {
    margin-top: 64px;
    padding-top: 28px;
    border-top: 1px solid var(--line);
    font-size: 12px;
    color: var(--text-soft);
    line-height: 1.7;
  }
  .lp-footer-grid {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 16px; align-items: end;
  }
  .lp-footer a {
    color: var(--accent); text-decoration: none;
    border-bottom: 1px dotted var(--accent);
  }
  @media (max-width: 600px) {
    .landing { padding: 32px 18px 56px; }
    .lp-hero { padding: 28px 18px 32px; }
    .lp-hero h1 { font-size: 30px; }
    .lp-toc-grid { grid-template-columns: 1fr 1fr; }
    .lp-footer-grid { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>

<div class="landing">

<header class="lp-header">
  <span class="lp-brand">맘곁 · 바비즈코리아</span>
  <button class="lp-dark-toggle" type="button" aria-label="다크모드 전환" onclick="(function(){document.documentElement.classList.toggle('dark');try{localStorage.setItem('mamgyeot-theme',document.documentElement.classList.contains('dark')?'dark':'light');}catch(e){}})()">
    <span class="dark-icon-dark" aria-hidden="true">🌙</span>
    <span class="dark-icon-light" aria-hidden="true">☀️</span>
  </button>
</header>

<section class="lp-hero">
  <h1>맘곁 태교</h1>
  <div class="lp-hero-sub">이론편 · 실천편</div>
  <p class="lp-hero-tagline">혼자 버티는 시간이 아니라 함께 지나가는 시간.<br>1800년 사주당 이씨와 오늘의 의학이 같은 자리에서 만나는 두 권의 책.</p>
  <div class="lp-hero-ctas" role="group" aria-label="시작하기">
    <a class="lp-cta lp-cta-app" href="https://www.momgyeot.com" target="_blank" rel="noopener">
      <span class="lp-cta-emoji" aria-hidden="true">📱</span>
      <span class="lp-cta-label">맘곁 앱</span>
      <span class="lp-cta-sub">곁에 두기</span>
    </a>
    <a class="lp-cta lp-cta-book" href="./book-modern.html">
      <span class="lp-cta-emoji" aria-hidden="true">📘</span>
      <span class="lp-cta-label">이론편</span>
      <span class="lp-cta-sub">왜 그런지</span>
    </a>
    <a class="lp-cta lp-cta-book" href="./practice-modern.html">
      <span class="lp-cta-emoji" aria-hidden="true">📗</span>
      <span class="lp-cta-label">실천편</span>
      <span class="lp-cta-sub">오늘 한 마디</span>
    </a>
  </div>
  <div class="lp-hero-meta">권의철 · 최소라 공저 · 펴낸곳 바비즈코리아</div>
</section>

<section class="lp-section lp-series">
  <h2>두 권의 책</h2>
  <p class="lp-section-lede">한 권은 왜 그러한지를, 한 권은 오늘 무엇을 할지를 이야기합니다.</p>
  <div class="lp-books">
    <a class="lp-book" href="./book-modern.html">
      <figure class="lp-book-cover">
        <img src="./images/book-cover.png" alt="이론편 표지" onerror="this.parentElement.style.display='none'">
      </figure>
      <div class="lp-book-meta">
        <span class="lp-book-tag">이론편</span>
        <h3 class="lp-book-title">사주당 이씨와 오늘의 의학</h3>
        <p class="lp-book-desc">10장 본문 + 부록 A–E. 임신·태교를 둘러싼 이해의 결을 정리한 책.</p>
        <span class="lp-book-cta">왜 그런지 이해하기 →</span>
      </div>
    </a>
    <a class="lp-book" href="./practice-modern.html">
      <figure class="lp-book-cover lp-book-cover--family">
        <img src="./images/family-faces.jpg" alt="실천편 — 맘곁 가족 일러스트" onerror="this.parentElement.style.display='none'">
      </figure>
      <div class="lp-book-meta">
        <span class="lp-book-tag">실천편</span>
        <h3 class="lp-book-title">말을 거는 순간, 사랑이 시작됩니다</h3>
        <p class="lp-book-desc">PART 1–5. 임신 준비부터 첫 만남까지, 오늘 해 볼 수 있는 작은 일들.</p>
        <span class="lp-book-cta">오늘 한 마디부터 →</span>
      </div>
    </a>
  </div>
  <div class="lp-design-row">
    <span class="lp-design-label">또 다른 결로 읽기</span>
    <a class="lp-design-link" href="./book.html">📜 이론편 세리프판</a>
    <a class="lp-design-link" href="./practice.html">📜 실천편 세리프판</a>
  </div>
</section>

<section class="lp-section lp-about">
  <h2>이 책에 대하여</h2>
  <p class="lp-section-lede">무엇을 해야 한다고 가르치는 책이 아니라, 무엇이 이미 일어나고 있는지를 함께 보는 책으로.</p>
  <p>『맘곁 태교 — 이론편』은 1800년 사주당 이씨가 짓고 1801년 아들 유희가 한글 음을 단 『태교신기』의 시선을 오늘의 임신·출산과 연결한다. 이 책은 <strong>잘해야 하는 과제로서의 태교</strong>가 아니라, <strong>이해해도 괜찮은 한 시간으로서의 태교</strong>를 이야기한다.</p>
  <p>본문은 10장. 임신을 둘러싼 변화부터 사주당 이씨, 현대 의학의 태아 발달, 임신 중 식·운동·생활, 오감, 엄마의 감정, 가족 태교, 아빠의 태교, 좋은 태교와 부담스러운 태교, 그리고 맘곁의 다섯 원칙까지 — 한 번에 읽지 않아도 좋다.</p>
  <p>부록 A는 『태교신기』 35절 전문 매핑, 부록 B는 임신 280일 환경 점검 카드 체크리스트, 부록 C는 참고문헌, 부록 D는 도움 요청 가이드와 용어집, 부록 E는 시리즈 안내(이론편 · 실천편)로 구성된다.</p>
</section>

<section class="lp-section">
  <h2>이론편 차례</h2>
  <ol class="lp-toc-grid">
    <li><a href="./book-modern.html#prologue"><span class="lp-toc-num">prologue</span>들어가며</a></li>
    <li><a href="./book-modern.html#ch1"><span class="lp-toc-num">1장</span>태교는 왜 지금 다시 필요할까</a></li>
    <li><a href="./book-modern.html#ch2"><span class="lp-toc-num">2장</span>사주당 이씨</a></li>
    <li><a href="./book-modern.html#ch3"><span class="lp-toc-num">3장</span>현대 의학이 보는 태아의 발달</a></li>
    <li><a href="./book-modern.html#ch4"><span class="lp-toc-num">4장</span>임신 중의 식·운동·생활</a></li>
    <li><a href="./book-modern.html#ch5"><span class="lp-toc-num">5장</span>오감으로 만나는 태아</a></li>
    <li><a href="./book-modern.html#ch6"><span class="lp-toc-num">6장</span>엄마의 감정은 태아의 환경이 된다</a></li>
    <li><a href="./book-modern.html#ch7"><span class="lp-toc-num">7장</span>가족의 태교</a></li>
    <li><a href="./book-modern.html#ch8"><span class="lp-toc-num">8장</span>아빠의 태교</a></li>
    <li><a href="./book-modern.html#ch9"><span class="lp-toc-num">9장</span>좋은 태교와 부담스러운 태교의 차이</a></li>
    <li><a href="./book-modern.html#ch10"><span class="lp-toc-num">10장</span>맘곁 태교의 다섯 원칙</a></li>
    <li><a href="./book-modern.html#epilogue"><span class="lp-toc-num">epilogue</span>닫으며</a></li>
    <li><a href="./book-modern.html#appendix-a"><span class="lp-toc-num">부록 A</span>『태교신기』 35절 매핑</a></li>
    <li><a href="./book-modern.html#appendix-b"><span class="lp-toc-num">부록 B</span>임신 280일 체크리스트</a></li>
    <li><a href="./book-modern.html#appendix-c"><span class="lp-toc-num">부록 C</span>참고문헌</a></li>
    <li><a href="./book-modern.html#appendix-d"><span class="lp-toc-num">부록 D</span>도움 요청 가이드 · 용어집</a></li>
    <li><a href="./book-modern.html#appendix-e"><span class="lp-toc-num">부록 E</span>맘곁 태교 시리즈</a></li>
  </ol>
</section>

<section class="lp-section">
  <h2>실천편 차례</h2>
  <ol class="lp-toc-grid">
    <li><a href="./practice-modern.html#prologue"><span class="lp-toc-num">prologue</span>들어가며</a></li>
    <li><a href="./practice-modern.html#part1"><span class="lp-toc-num">PART 1</span>태아 이전의 마음 준비</a></li>
    <li><a href="./practice-modern.html#part2"><span class="lp-toc-num">PART 2</span>임신 초기 태교</a></li>
    <li><a href="./practice-modern.html#part3"><span class="lp-toc-num">PART 3</span>임신 중기 태교</a></li>
    <li><a href="./practice-modern.html#part4"><span class="lp-toc-num">PART 4</span>임신 후기 태교</a></li>
    <li><a href="./practice-modern.html#part5"><span class="lp-toc-num">PART 5</span>출산과 첫 만남</a></li>
    <li><a href="./practice-modern.html#epilogue"><span class="lp-toc-num">epilogue</span>닫으며</a></li>
  </ol>
</section>

<section class="lp-section lp-app-promo">
  <h2>맘곁과 함께 지나가기</h2>
  <p class="lp-section-lede">책에서 만난 이해를 일상으로 잇는 자리.</p>
  <div class="lp-app-card">
    <a class="lp-app-qr" href="https://www.momgyeot.com" target="_blank" rel="noopener" aria-label="맘곁 사이트 QR (www.momgyeot.com)">
      <img src="./images/momgyeot-qr.png" alt="맘곁 공식 사이트 QR 코드" width="140" height="140">
    </a>
    <div class="lp-app-meta">
      <p class="lp-app-stanza">
        <strong>예비맘곁</strong>은 부모가 되기 전 마음과 관계를 준비하는 자리,<br>
        <strong>임신맘곁</strong>은 아기와 처음으로 연결을 시작하는 자리,<br>
        <strong>육아맘곁</strong>은 함께 살아가는 리듬을 만드는 자리.
      </p>
      <a class="lp-app-link" href="https://www.momgyeot.com" target="_blank" rel="noopener">
        📱 맘곁 사이트 — www.momgyeot.com
      </a>
    </div>
  </div>
</section>

<section class="lp-section">
  <h2>도움이 필요할 때</h2>
  <p class="lp-section-lede">혼자 견디지 않아도 됩니다.</p>
  <p style="font-size: 14.5px; color: var(--text); line-height: 1.75;">생명·안전·정서적 어려움이 클 때 가장 빨리 닿을 수 있는 자리는 <a href="tel:119" style="color: var(--accent); font-weight: 700;">119</a> · <a href="tel:1393" style="color: var(--accent); font-weight: 700;">1393</a>(자살예방) · <a href="tel:1577-0199" style="color: var(--accent); font-weight: 700;">1577-0199</a>(정신건강위기상담, 24시간) · <a href="tel:1366" style="color: var(--accent); font-weight: 700;">1366</a>(여성긴급전화)입니다. 자세한 안내는 <a href="./book-modern.html#appendix-d" style="color: var(--accent); font-weight: 600;">부록 D — 도움 요청 가이드</a>를 펴 보세요.</p>
</section>

<footer class="lp-footer">
  <div class="lp-footer-grid">
    <div>
      © 2026 권의철 · 최소라. 펴낸곳 바비즈코리아.<br>
      『맘곁 태교 — 이론편』 · 1판 1쇄 2026년 4월 28일.<br>
      이 페이지는 <a href="https://github.com/charleykwon/momgyeot_theory" target="_blank" rel="noopener">GitHub</a>에서 관리되며, 원고는 <code style="font-family: monospace; font-size: 11px; background: var(--bg-soft); padding: 1px 5px; border-radius: 3px;">docs/*.md</code> 파일에서 직접 확인할 수 있습니다.
    </div>
  </div>
</footer>

</div>

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
<title>{{BOOK_TITLE}} · {{BOOK_TAGLINE}}</title>
<meta name="description" content="『{{BOOK_TITLE}}』 · {{BOOK_TAGLINE}}. 권의철·최소라 공저, 바비즈코리아.">
<meta name="author" content="권의철, 최소라">
<meta name="keywords" content="태교, 사주당, 태교신기, 임신, 모성건강, 맘곁, 바비즈코리아">
<meta property="og:title" content="{{BOOK_TITLE}}">
<meta property="og:description" content="{{BOOK_TAGLINE}}">
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
  --bg: #fbf8f2;
  --bg-soft: #fffefa;
  --text: #1a1612;
  --text-soft: #45403b;
  --accent: #7a5e40;
  --line: #d9d0bf;
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
  --pen-yellow: rgba(245, 211, 100, 0.5);
  --pen-peach: rgba(244, 178, 154, 0.42);
  --pen-sage: rgba(167, 198, 169, 0.42);
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
  font-size: 17.5px;
  line-height: 1.9;
  font-weight: 400;
  word-break: keep-all;
  overflow-wrap: break-word;
}
.book {
  max-width: 680px;
  margin: 0 auto;
  padding: 64px 24px 96px;
}
/* 풀-블리드 아트 표지 — 이미지 한 장만, 텍스트 없음 */
.book-cover {
  margin: -64px -24px 48px;  /* 데스크탑: book.padding(64,24) 만큼 외부로 풀폭 */
  padding: 0;
  background: transparent;
}
.book-cover-art { margin: 0; display: block; }
.book-cover-art img {
  display: block;
  width: 100%;
  height: auto;
  margin: 0;
}
@media (max-width: 600px) {
  /* 모바일에서는 .book padding이 32px 20px로 줄어드므로 음의 margin도 맞춰준다 */
  .book-cover { margin: -32px -20px 32px; }
}
@media print {
  .book-cover { page-break-after: always; margin: 0; }
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
  color: var(--text);
  font-size: 16.5px;
  line-height: 2;
  font-weight: 400;
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
  font-size: 14.5px;
  color: var(--text);
  letter-spacing: 0.04em;
  font-weight: 500;
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
.toc .toc-group + .toc-group {
  margin-top: 28px;
  padding-top: 22px;
  border-top: 1px solid var(--line);
}
.toc-group-label {
  font-family: var(--sans);
  font-size: 11.5px;
  letter-spacing: 0.32em;
  color: var(--text-soft);
  font-weight: 600;
  margin: 0 0 14px;
  text-transform: uppercase;
}
.toc ol {
  list-style: none;
  padding: 0;
  margin: 0;
}
.toc li {
  margin: 8px 0;
  font-size: 16.5px;
}
.toc ol.toc-appendix li { font-size: 15px; color: var(--text-soft); }
.toc a {
  color: var(--text);
  text-decoration: none;
  border-bottom: 1px dotted transparent;
  padding-bottom: 2px;
  font-weight: 500;
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
.chapter-body .subhead-3 {
  font-size: 14.5px;
  font-weight: 600;
  margin: 1.4em 0 0.6em;
  color: var(--accent);
  letter-spacing: 0;
  font-family: var(--sans);
}
.chapter-body .subhead-4 {
  font-size: 13.5px;
  font-weight: 600;
  margin: 1.2em 0 0.5em;
  color: var(--text);
  letter-spacing: 0.01em;
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
  font-style: normal;
  font-weight: 700;
  background: linear-gradient(180deg,
    transparent 0%, transparent 60%,
    var(--pen-yellow) 60%, var(--pen-yellow) 92%,
    transparent 92%);
  padding: 0 2px;
}
/* 본문 영문 인용은 이탤릭 유지 (각주·참고문헌 표 등) */
aside.footnotes em,
.chapter.is-appendix table.data em {
  font-style: italic;
  font-weight: inherit;
  background: none;
  padding: 0;
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
.drawer-group + .drawer-group { margin-top: 6px; }
.drawer-group-label {
  font-family: var(--sans); font-size: 10.5px; letter-spacing: 0.32em;
  color: var(--text-soft); font-weight: 600;
  text-transform: uppercase;
  padding: 14px 18px 8px; margin: 0;
  background: var(--bg);
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}
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

#theme-switcher, #series-switcher {
  position: fixed; top: 22px; z-index: 50;
  padding: 6px 14px;
  background: var(--bg-soft); border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--text-soft);
  font-family: var(--sans); font-size: 12px;
  letter-spacing: 0.1em;
  text-decoration: none;
  box-shadow: 0 2px 8px var(--shadow-soft);
  transition: background 0.18s, color 0.18s, border-color 0.18s;
}
#theme-switcher { right: 74px; }
#series-switcher { right: 154px; }
#theme-switcher:hover, #series-switcher:hover { background: var(--bg); color: var(--accent); border-color: var(--accent); }

@media (max-width: 600px) {
  #menu-toggle { top: 12px; left: 12px; width: 40px; height: 40px; }
  #dark-toggle { top: 12px; right: 12px; width: 40px; height: 40px; font-size: 16px; }
  #theme-switcher { top: 16px; right: 62px; padding: 5px 11px; font-size: 11px; }
  #series-switcher { top: 16px; right: 130px; padding: 5px 11px; font-size: 11px; }
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

/* 챕터 헤더 일러스트 — 가운데 정렬, 컴팩트 사이즈 */
.chapter-illust {
  margin: 0 auto 14px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  height: 96px;
}
.chapter-illust img {
  max-width: 80px;
  max-height: 96px;
  width: auto;
  height: auto;
  object-fit: contain;
  display: block;
}
@media (max-width: 600px) {
  .chapter-illust { height: 80px; }
  .chapter-illust img { max-width: 68px; max-height: 80px; }
}

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
/* =========== 장 끝 태담 카드 (실천편) =========== */
.chapter-end-script {
  margin: 2.4em 0 2em;
  padding: 22px 24px 20px;
  background: linear-gradient(135deg, var(--bg-soft) 0%, var(--bg) 100%);
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  border-radius: 12px;
  font-family: var(--sans);
  position: relative;
}
.cend-head {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px dashed var(--line);
}
.cend-tag {
  display: inline-block;
  padding: 4px 12px;
  background: var(--accent);
  color: #fff;
  border-radius: 999px;
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.18em; text-transform: uppercase;
}
.cend-extra {
  font-size: 12px; font-weight: 500;
  color: var(--text-soft);
  letter-spacing: 0.05em;
}
.cend-body {
  margin: 0;
  padding: 0;
  background: transparent;
  border: none;
  font-size: 15px; line-height: 1.85;
  color: var(--text);
  font-style: italic;
  font-weight: 400;
}
.cend-body::before { content: none; }

/* =========== 상황별 태담 10선 카드 그리드 (실천편) =========== */
.situ-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
  margin: 1.4em 0 2em;
  counter-reset: situ;
}
.situ-card {
  padding: 18px 20px 16px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: 12px;
  font-family: var(--sans);
  display: flex; flex-direction: column;
}
.situ-card-head {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--line);
}
.situ-num {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 30px; height: 30px;
  padding: 0 8px;
  background: var(--accent);
  color: #fff;
  border-radius: 999px;
  font-size: 12px; font-weight: 800;
  letter-spacing: 0.04em;
  font-variant-numeric: tabular-nums;
}
.situ-card-title {
  margin: 0;
  font-size: 14.5px; font-weight: 700;
  color: var(--text);
  letter-spacing: -0.005em;
}
.situ-card-body {
  margin: 0;
  padding: 12px 14px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-left: none;
  border-radius: 8px;
  font-size: 14px; line-height: 1.7;
  color: var(--text);
  font-style: italic;
}
.situ-card-body::before { content: none; }
.situ-card:nth-child(5n+2) .situ-num { background: #6aa1c2; }
.situ-card:nth-child(5n+3) .situ-num { background: #8fa766; }
.situ-card:nth-child(5n+4) .situ-num { background: #e08aa1; }
.situ-card:nth-child(5n+5) .situ-num { background: #c8a35a; }
@media (max-width: 600px) {
  .situ-grid { grid-template-columns: 1fr; }
}

/* =========== 시기별 변화 타임라인 (실천편) =========== */
.period-timeline {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
  margin: 1.6em 0 2em;
}
.period-card {
  padding: 18px 20px 16px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-top: 4px solid var(--accent);
  border-radius: 12px;
  font-family: var(--sans);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.period-tag {
  font-size: 13px; font-weight: 700;
  letter-spacing: 0.03em;
  color: var(--accent);
}
.period-month {
  font-size: 11px; font-weight: 600;
  letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--text-soft);
  margin-bottom: 4px;
}
.period-body {
  margin: 6px 0 0;
  font-size: 14px; line-height: 1.65;
  color: var(--text);
}
.period-card:nth-child(5n+2) { border-top-color: #6aa1c2; }
.period-card:nth-child(5n+2) .period-tag { color: #4d85a8; }
.period-card:nth-child(5n+3) { border-top-color: #8fa766; }
.period-card:nth-child(5n+3) .period-tag { color: #5e7459; }
.period-card:nth-child(5n+4) { border-top-color: #e08aa1; }
.period-card:nth-child(5n+4) .period-tag { color: #b86276; }
.period-card:nth-child(5n+5) { border-top-color: #c8a35a; }
.period-card:nth-child(5n+5) .period-tag { color: #a48345; }
.period-card--imminent {
  border-top-color: #d97757 !important;
  background: rgba(217, 119, 87, 0.06);
}
.period-card--imminent .period-tag { color: #b04830 !important; }
@media (max-width: 600px) {
  .period-timeline { grid-template-columns: 1fr; }
}

/* D-DAY 카운트다운 */
.dday-row {
  margin: 1.4em 0 1.8em;
  padding: 18px 20px 16px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: 12px;
  font-family: var(--sans);
}
.dday-head { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.dday-icon { font-size: 18px; }
.dday-label {
  font-size: 11.5px; font-weight: 700;
  letter-spacing: 0.22em; text-transform: uppercase;
  color: var(--accent);
}
.dday-cards {
  list-style: none; margin: 0; padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 8px;
}
.dday-card {
  padding: 12px 14px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 10px;
  text-align: center;
  display: flex; flex-direction: column; gap: 2px;
}
.dday-week {
  font-size: 18px; font-weight: 800;
  color: var(--accent);
  letter-spacing: -0.005em;
  font-variant-numeric: tabular-nums;
}
.dday-month {
  font-size: 11px; color: var(--text-soft);
  letter-spacing: 0.06em;
}
.dday-remain {
  margin-top: 4px;
  padding-top: 6px;
  border-top: 1px dashed var(--line);
  font-size: 12.5px; color: var(--text);
  font-weight: 600;
}

/* =========== 태담 기본 공식 (실천편 PART 1) =========== */
.talk-formula {
  margin: 1.6em 0 2em;
  padding: 22px 22px 18px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.04);
  font-family: var(--sans);
}
.talk-formula-row {
  display: flex; flex-wrap: wrap; align-items: center;
  gap: 8px;
  margin-bottom: 18px;
  padding-bottom: 16px;
  border-bottom: 1px dashed var(--line);
}
.talk-chip {
  display: inline-block;
  padding: 7px 14px;
  border-radius: 999px;
  font-size: 13.5px; font-weight: 600;
  letter-spacing: -0.005em;
  color: #fff;
}
.talk-chip--1 { background: #c8a874; }
.talk-chip--2 { background: #6aa1c2; }
.talk-chip--3 { background: #e08aa1; }
.talk-chip--4 { background: #8fa766; }
.talk-plus {
  font-size: 18px; font-weight: 600;
  color: var(--text-soft);
  user-select: none;
}
.talk-formula-example { position: relative; }
.talk-example-tag {
  display: inline-block;
  font-size: 10.5px; font-weight: 700;
  letter-spacing: 0.22em; text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 8px;
}
.talk-example-line {
  margin: 0 0 6px;
  display: flex; flex-wrap: wrap; align-items: center;
  gap: 10px;
  font-size: 14.5px; line-height: 1.65;
  color: var(--text);
}
.talk-example-line span { flex: 1; min-width: 0; }
.talk-example-label {
  font-size: 11.5px; font-weight: 700;
  letter-spacing: -0.005em;
  padding: 3px 10px;
  border-radius: 999px;
  color: #fff;
  font-style: normal;
  white-space: nowrap;
}
@media (max-width: 600px) {
  .talk-formula-row { gap: 6px; }
  .talk-chip { padding: 6px 11px; font-size: 12.5px; }
  .talk-plus { font-size: 14px; }
  .talk-example-line { gap: 6px; }
}

/* =========== 첫 태담 스크립트 카드 (실천편) =========== */
.script-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
  margin: 1.6em 0 2em;
}
.script-grid--single { grid-template-columns: minmax(0, 480px); justify-content: start; }
.script-card {
  padding: 18px 20px 16px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  border-radius: 12px;
  font-family: var(--sans);
}
.script-card-head {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 10px;
}
.script-pin { font-size: 18px; line-height: 1; }
.script-card-title {
  margin: 0; font-size: 15px; font-weight: 700;
  color: var(--text); letter-spacing: -0.005em;
}
.script-card-body {
  margin: 0;
  padding: 12px 14px;
  background: var(--bg);
  border-left: none;
  border-radius: 8px;
  font-size: 14px; line-height: 1.7;
  color: var(--text);
  font-style: italic;
}
.script-card-body::before { content: none; }
.script-card:nth-child(5n+2) { border-left-color: #6aa1c2; }
.script-card:nth-child(5n+3) { border-left-color: #e08aa1; }
.script-card:nth-child(5n+4) { border-left-color: #e8c553; }
.script-card:nth-child(5n+5) { border-left-color: #8fa766; }
.script-card--dad { border-left-color: #7e5ea7; }
@media (max-width: 600px) {
  .script-grid { grid-template-columns: 1fr; }
}

/* =========== 감정 색상표 (실천편 PART 1) =========== */
.color-palette {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
  margin: 1.6em 0 2em;
}
.color-card {
  --card-bg: #f5f0e6;
  --card-accent: #b89d72;
  --card-text: #2c2826;
  position: relative;
  padding: 24px 22px 22px;
  background: var(--card-bg);
  border-radius: 12px;
  border: 1px solid rgba(0,0,0,0.06);
  box-shadow: 0 2px 10px rgba(0,0,0,0.04);
  font-family: var(--sans);
  overflow: hidden;
}
.color-card::before {
  content: ""; position: absolute;
  top: 0; left: 0; right: 0; height: 8px;
  background: var(--card-accent);
}
.color-swatch {
  display: inline-block;
  width: 28px; height: 28px;
  border-radius: 50%;
  background: var(--card-accent);
  border: 2px solid rgba(255,255,255,0.7);
  box-shadow: 0 2px 6px rgba(0,0,0,0.12);
  margin-bottom: 10px;
}
.color-name {
  margin: 0 0 6px;
  font-size: 17px; font-weight: 700;
  color: var(--card-text);
  letter-spacing: -0.005em;
}
.color-keywords {
  margin: 0 0 10px;
  font-size: 13.5px;
  color: var(--card-text);
  opacity: 0.78;
  line-height: 1.55;
}
.color-quote {
  margin: 0;
  padding: 10px 14px;
  background: rgba(255,255,255,0.55);
  border-radius: 8px;
  font-size: 13.5px;
  color: var(--card-text);
  line-height: 1.6;
  font-style: italic;
}

.color-card--beige  { --card-bg: #f0e3cb; --card-accent: #c8a874; --card-text: #4a3a23; }
.color-card--yellow { --card-bg: #fbeec1; --card-accent: #e8c553; --card-text: #5a4815; }
.color-card--olive  { --card-bg: #d8e0bd; --card-accent: #8fa766; --card-text: #38461c; }
.color-card--pink   { --card-bg: #f6d9de; --card-accent: #e08aa1; --card-text: #6e2e3e; }
.color-card--blue   { --card-bg: #d2e1ec; --card-accent: #6aa1c2; --card-text: #234862; }
.color-card--gray   { --card-bg: #d6d4cf; --card-accent: #5a5853; --card-text: #2a2925; color: var(--card-text); }
.color-card--violet { --card-bg: #ddd0ea; --card-accent: #7e5ea7; --card-text: #382356; }

/* 다크모드 — 카드 배경은 그대로 두되 인쇄 가능성 고려 */
:root.dark .color-card {
  border-color: rgba(255,255,255,0.08);
  box-shadow: 0 4px 14px rgba(0,0,0,0.3);
}
:root.dark .color-quote {
  background: rgba(0,0,0,0.18);
}
@media (max-width: 600px) {
  .color-palette { grid-template-columns: 1fr; }
}
@media print {
  .color-card { page-break-inside: avoid; box-shadow: none; }
}

/* =========== 부록 D 안전 박스 =========== */
.safety-board { margin: 1.6em 0 2em; }
.safety-emergency {
  margin: 0 0 24px;
  padding: 22px 24px 24px;
  background: linear-gradient(135deg, #fff5f0 0%, #ffe9e0 100%);
  border: 2px solid #d97757;
  border-radius: 14px;
  box-shadow: 0 4px 16px rgba(217, 119, 87, 0.15);
}
:root.dark .safety-emergency {
  background: linear-gradient(135deg, #2a1f1c 0%, #3a2520 100%);
  border-color: #c9805f;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
}
.safety-emergency-head {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 6px;
}
.safety-emergency-icon { font-size: 28px; line-height: 1; }
.safety-emergency-title {
  font-family: var(--sans);
  font-size: 18px; font-weight: 700;
  margin: 0;
  color: #b04830;
  letter-spacing: -0.005em;
}
:root.dark .safety-emergency-title { color: #ffb89e; }
.safety-emergency-lede {
  font-family: var(--sans); font-size: 14px;
  color: var(--text); line-height: 1.6;
  margin: 0 0 14px;
}
.safety-emergency-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 8px;
}
.safety-call {
  display: block;
  padding: 12px 14px;
  background: #ffffff;
  border: 1px solid rgba(176, 72, 48, 0.3);
  border-radius: 10px;
  text-decoration: none;
  text-align: center;
  transition: transform 0.15s, box-shadow 0.15s;
}
:root.dark .safety-call { background: #1a1a1a; border-color: rgba(255, 184, 158, 0.3); }
.safety-call:hover { transform: translateY(-1px); box-shadow: 0 3px 10px rgba(0,0,0,0.1); }
.safety-call-num {
  display: block;
  font-family: var(--sans); font-size: 22px; font-weight: 800;
  color: #b04830;
  letter-spacing: -0.005em;
  font-variant-numeric: tabular-nums;
}
:root.dark .safety-call-num { color: #ffb89e; }
.safety-call-label {
  display: block; margin-top: 2px;
  font-family: var(--sans); font-size: 11.5px;
  color: var(--text-soft);
  letter-spacing: 0;
}

.safety-tiers {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
  gap: 14px;
}
.safety-tier {
  padding: 18px 20px 16px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-left: 5px solid var(--accent);
  border-radius: 12px;
  font-family: var(--sans);
}
.safety-tier--soft { border-left-color: #8c6e4e; }
.safety-tier--rose { border-left-color: #c97b8a; }
.safety-tier--sage { border-left-color: #6e8669; }
.safety-tier--mustard { border-left-color: #c8a35a; }
.safety-tier--lavender { border-left-color: #8a7da3; }
.safety-tier-head { margin-bottom: 6px; }
.safety-tier-tag {
  display: inline-block;
  font-size: 10.5px; font-weight: 700;
  letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 4px;
}
.safety-tier--rose .safety-tier-tag { color: #b86276; }
.safety-tier--sage .safety-tier-tag { color: #5e7459; }
.safety-tier--mustard .safety-tier-tag { color: #a48345; }
.safety-tier--lavender .safety-tier-tag { color: #7a6f8c; }
.safety-tier-title {
  font-size: 16px; font-weight: 700;
  margin: 0 0 6px; color: var(--text);
  line-height: 1.4; letter-spacing: -0.005em;
}
.safety-tier-lede {
  font-size: 13.5px; color: var(--text-soft);
  margin: 0 0 10px; line-height: 1.6;
}
.safety-tier-list {
  list-style: none; padding: 0; margin: 0 0 12px;
  font-size: 13px; line-height: 1.65;
}
.safety-tier-list li {
  padding: 4px 0 4px 18px;
  position: relative;
  color: var(--text);
}
.safety-tier-list li::before {
  content: "•"; position: absolute; left: 4px;
  color: var(--accent); font-weight: 700;
}
.safety-tier-list strong { font-weight: 700; }
.safety-tier-actions { display: flex; flex-wrap: wrap; gap: 6px; }
.safety-tier-btn {
  display: inline-block;
  padding: 7px 12px;
  background: var(--accent);
  color: #ffffff !important;
  text-decoration: none !important;
  border: 1px solid var(--accent) !important;
  border-radius: 999px;
  font-size: 12.5px; font-weight: 600;
  letter-spacing: -0.005em;
  transition: transform 0.15s, opacity 0.15s;
}
.safety-tier-btn:hover { transform: translateY(-1px); }
.safety-tier-btn--ghost {
  background: transparent !important;
  color: var(--text) !important;
  border-color: var(--line) !important;
}
.safety-tier-btn--ghost:hover { border-color: var(--accent) !important; color: var(--accent) !important; }

.safety-footnote {
  margin: 22px 0 0;
  padding: 12px 16px;
  background: var(--bg);
  border: 1px dashed var(--line);
  border-radius: 8px;
  font-family: var(--sans);
  font-size: 12px; line-height: 1.65;
  color: var(--text-soft);
}
@media (max-width: 600px) {
  .safety-emergency { padding: 18px 18px 20px; }
  .safety-emergency-grid { grid-template-columns: repeat(2, 1fr); }
  .safety-tiers { grid-template-columns: 1fr; }
}
@media print {
  .safety-emergency, .safety-tier { page-break-inside: avoid; box-shadow: none; }
  .safety-tier-btn { background: transparent !important; color: #000 !important; border-color: #999 !important; }
}

/* =========== 부록 B 카드형 체크리스트 =========== */
.check-board { margin: 1.4em 0 2em; }
.check-stage {
  margin: 1.6em 0 2em;
  padding: 22px 22px 20px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: 0 2px 10px var(--shadow-soft);
}
.check-stage-head { margin-bottom: 16px; }
.check-stage-meta {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 8px;
}
.check-stage-num {
  font-family: var(--sans); font-size: 11px; font-weight: 600;
  letter-spacing: 0.25em; text-transform: uppercase;
  color: #fff; background: var(--accent);
  padding: 4px 11px; border-radius: 999px;
}
.check-stage-range {
  font-family: var(--sans); font-size: 12px;
  color: var(--text-soft); letter-spacing: 0.04em;
}
.check-stage-title {
  font-family: var(--sans);
  font-size: 18px; font-weight: 700;
  margin: 0 0 4px;
  color: var(--text); letter-spacing: -0.005em;
}
.check-stage-sub {
  font-family: var(--sans);
  font-size: 13.5px; color: var(--text-soft);
  margin: 0 0 12px;
  line-height: 1.55;
}
.check-stage-progress {
  display: flex; align-items: center; gap: 10px;
  font-family: var(--sans); font-size: 12px; color: var(--text-soft);
}
.check-progress-bar {
  flex: 1; height: 5px; border-radius: 999px;
  background: var(--bg);
  position: relative; overflow: hidden;
}
.check-progress-bar::after {
  content: ""; position: absolute;
  left: 0; top: 0; bottom: 0;
  width: var(--progress, 0%);
  background: var(--accent);
  transition: width 0.3s ease;
}
.check-progress-text { font-weight: 600; min-width: 48px; text-align: right; font-variant-numeric: tabular-nums; }

.check-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 10px;
  margin-top: 12px;
}
.check-card {
  display: grid;
  grid-template-columns: 22px 1fr;
  grid-template-rows: auto auto auto;
  column-gap: 12px; row-gap: 4px;
  padding: 14px 16px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.18s, background 0.18s, box-shadow 0.18s;
  font-family: var(--sans);
}
.check-card:hover {
  border-color: var(--accent);
  box-shadow: 0 2px 8px var(--shadow-soft);
}
.check-card input[type="checkbox"] {
  grid-row: 1 / span 3; grid-column: 1;
  width: 18px; height: 18px; margin: 3px 0 0;
  accent-color: var(--accent);
  cursor: pointer;
}
.check-card .check-area {
  grid-column: 2; grid-row: 1;
  font-size: 10.5px; font-weight: 700;
  letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--accent);
}
.check-card .check-item {
  grid-column: 2; grid-row: 2;
  font-size: 14px; line-height: 1.55;
  color: var(--text);
}
.check-card .check-ref {
  grid-column: 2; grid-row: 3;
  font-size: 11.5px; color: var(--text-soft);
  letter-spacing: 0.02em;
}
.check-card:has(input:checked) {
  background: rgba(140, 110, 78, 0.08);
  border-color: var(--accent);
}
.check-card:has(input:checked) .check-item {
  text-decoration: line-through;
  text-decoration-color: var(--text-soft);
  color: var(--text-soft);
}
.check-board-tools {
  display: flex; align-items: center; justify-content: space-between;
  margin: 18px 0 0; padding-top: 16px;
  border-top: 1px dashed var(--line);
  font-family: var(--sans); font-size: 12.5px;
}
.check-reset {
  background: none; border: 1px solid var(--line);
  color: var(--text-soft);
  padding: 6px 14px; border-radius: 999px;
  font-family: var(--sans); font-size: 12.5px;
  cursor: pointer;
  transition: border-color 0.18s, color 0.18s;
}
.check-reset:hover { border-color: var(--accent); color: var(--accent); }
.check-board-note { color: var(--text-soft); font-size: 11.5px; }
@media (max-width: 600px) {
  .check-stage { padding: 18px 16px 16px; }
  .check-cards { grid-template-columns: 1fr; }
}
@media print {
  .check-card { page-break-inside: avoid; }
  .check-card input[type="checkbox"] { print-color-adjust: exact; }
  .check-board-tools { display: none; }
}

/* 다음 행동 CTA — 챕터 끝 카드 */
.next-action {
  display: flex; align-items: center; gap: 16px;
  margin: 3em 0 1em;
  padding: 18px 22px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  border-radius: 10px;
  position: relative;
}
.next-action-tag {
  position: absolute; top: -10px; left: 18px;
  background: var(--accent); color: #fff;
  font-family: var(--sans); font-size: 10.5px; font-weight: 600;
  letter-spacing: 0.2em; text-transform: uppercase;
  padding: 3px 10px; border-radius: 999px;
}
.next-action-icon {
  font-size: 28px; line-height: 1;
  flex-shrink: 0;
}
.next-action-text { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.next-action-headline {
  font-family: var(--sans);
  font-size: 15px; font-weight: 600;
  color: var(--text);
  letter-spacing: -0.005em;
}
.next-action-sub {
  font-family: var(--sans);
  font-size: 13.5px;
  color: var(--text-soft);
  line-height: 1.6;
}
.next-action-link {
  flex-shrink: 0;
  background: var(--accent); color: #fff;
  text-decoration: none;
  font-family: var(--sans); font-size: 13px; font-weight: 600;
  padding: 8px 14px; border-radius: 999px;
  transition: transform 0.18s, box-shadow 0.18s;
}
.next-action-link:hover { transform: translateY(-1px); }
.chapter.is-appendix .next-action { display: none; }
@media (max-width: 600px) {
  .next-action { flex-wrap: wrap; padding: 16px 18px; gap: 12px; }
  .next-action-icon { font-size: 24px; }
  .next-action-text { flex: 1 1 60%; }
  .next-action-link { width: 100%; text-align: center; }
}
@media print { .next-action { page-break-inside: avoid; } }

/* 맘곁 브랜드 — 함께 지나가는 시간 */
.momgyeot-brand {
  margin: 2.2em 0 1.4em;
  padding: 28px 26px 22px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  border-radius: 12px;
  font-family: var(--serif);
  color: var(--text);
  line-height: 1.85;
}
.momgyeot-brand .momgyeot-lead {
  font-family: var(--sans);
  font-size: 13px; font-weight: 700;
  letter-spacing: 0.22em; color: var(--accent);
  margin: 0 0 14px;
}
.momgyeot-brand .momgyeot-stanza {
  margin: 0 0 14px; font-size: 15.5px;
}
.momgyeot-brand .momgyeot-stanza em {
  font-style: normal;
  background: linear-gradient(180deg, transparent 60%, rgba(196, 157, 176, 0.35) 60%);
  padding: 0 2px;
}
.momgyeot-brand .momgyeot-stanza strong { color: var(--accent); font-weight: 700; }
.momgyeot-stages {
  list-style: none; padding: 0;
  margin: 22px 0 18px;
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
}
.momgyeot-stage {
  display: flex; flex-direction: column; gap: 8px;
  padding: 16px 14px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 10px;
  position: relative;
}
.momgyeot-stage .stage-tag {
  font-family: var(--sans); font-size: 13px; font-weight: 700;
  letter-spacing: 0.06em; color: var(--text-soft);
}
.momgyeot-stage .stage-desc {
  font-family: var(--sans); font-size: 12.5px;
  color: var(--text-soft); line-height: 1.6;
}
.momgyeot-stage.is-current {
  background: var(--bg-soft);
  border-color: var(--accent);
  box-shadow: 0 2px 10px var(--shadow-soft);
}
.momgyeot-stage.is-current .stage-tag { color: var(--accent); }
.momgyeot-stage.is-current .stage-desc { color: var(--text); }
.momgyeot-stage .stage-now {
  position: absolute; top: -10px; right: 12px;
  background: var(--accent); color: #fff;
  font-family: var(--sans); font-size: 10.5px; font-weight: 600;
  letter-spacing: 0.12em;
  padding: 3px 9px; border-radius: 999px;
  white-space: nowrap;
}
.momgyeot-brand .momgyeot-now {
  margin: 18px 0 6px;
  font-family: var(--sans); font-size: 14.5px; font-weight: 500;
  color: var(--text); line-height: 1.75;
}
.momgyeot-brand .momgyeot-cta {
  margin: 0; font-family: var(--serif); font-size: 17px; font-style: italic;
  color: var(--accent);
}
@media (max-width: 600px) {
  .momgyeot-brand { padding: 22px 18px 18px; }
  .momgyeot-stages { grid-template-columns: 1fr; gap: 10px; }
  .momgyeot-stage .stage-now { right: 10px; top: -9px; }
}
@media print {
  .momgyeot-brand { page-break-inside: avoid; background: #fff !important; border-color: #ccc !important; }
  .momgyeot-stage { background: #fff !important; box-shadow: none !important; }
}

/* 맘곁 공식 사이트 QR 카드 */
.momgyeot-card {
  display: flex; align-items: center; gap: 22px;
  margin: 1.6em 0;
  padding: 22px 24px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: 12px;
}
.momgyeot-qr {
  flex-shrink: 0; display: block; line-height: 0;
  padding: 8px; background: #fff; border: 1px solid var(--line); border-radius: 8px;
}
.momgyeot-qr img { display: block; width: 140px; height: 140px; }
.momgyeot-meta { display: flex; flex-direction: column; gap: 6px; }
.momgyeot-tag {
  font-family: var(--sans); font-size: 11px; font-weight: 600;
  letter-spacing: 0.18em; color: var(--accent); text-transform: none;
}
.momgyeot-link {
  font-family: var(--sans); font-size: 18px; font-weight: 700;
  color: var(--text); text-decoration: none; border-bottom: 1px dashed var(--accent);
  align-self: flex-start;
}
.momgyeot-link:hover { color: var(--accent); }
.momgyeot-hint { font-family: var(--sans); font-size: 13px; color: var(--text-soft); line-height: 1.6; }
@media (max-width: 600px) {
  .momgyeot-card { flex-direction: column; align-items: flex-start; gap: 14px; padding: 18px; }
  .momgyeot-qr img { width: 120px; height: 120px; }
}
@media print { .momgyeot-card { page-break-inside: avoid; background: #fff !important; border-color: #ccc !important; } }

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

<a id="theme-switcher" href="./{{THEME_TARGET}}" title="{{THEME_LABEL}} 디자인으로 보기">{{THEME_LABEL}}</a>
<a id="series-switcher" href="./{{OTHER_BOOK_TARGET}}" title="시리즈 — {{OTHER_BOOK_LABEL}} 보기">📘 {{OTHER_BOOK_LABEL}}</a>

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
<section class="book-cover">
  <figure class="book-cover-art">
    <img src="./images/{{COVER_IMAGE}}" alt="{{COVER_IMAGE_ALT}}" onerror="this.closest('.book-cover').style.display='none'">
  </figure>
</section>

<header class="cover">
  <figure class="cover-logo illust"><img src="./images/logo.png" alt="맘곁 로고" onerror="this.closest('.cover-logo').style.display='none'"></figure>
  <div class="brand">맘곁</div>
  <h1>맘곁 태교</h1>
  <div class="sub">{{BOOK_SUBTITLE}}</div>
  <figure class="cover-hero illust"><img src="./images/cover-illustration.png" alt="맘곁 태교 표지 일러스트 — 가족이 손을 잡고 함께 걷는 모습" onerror="this.closest('.cover-hero').style.display='none'"></figure>
  <div class="cover-tagline">{{BOOK_TAGLINE}}</div>
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

  // ---- Close drawer + scroll to anchor on TOC link click ----
  // body.overflow is locked to 'hidden' while drawer is open, which blocks
  // the browser's default anchor scroll. So intercept, close drawer first,
  // then explicitly scroll to the target.
  document.querySelectorAll('.drawer-nav a[href^="#"]').forEach(function(a) {
    a.addEventListener('click', function(e) {
      var href = a.getAttribute('href');
      if (!href || href === '#') return;
      var target = document.getElementById(href.slice(1));
      if (!target) return;
      e.preventDefault();
      closeDrawer();
      requestAnimationFrame(function() {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        try { history.replaceState(null, '', href); } catch (err) {}
      });
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

  // ---- Checklist (부록 B) — localStorage 동기화 + 진행률 ----
  function initChecklists() {
    var boards = document.querySelectorAll('.check-board');
    boards.forEach(function(board) {
      var key = 'momgyeot-checklist-' + (board.getAttribute('data-checklist') || 'default');
      var saved = {};
      try { saved = JSON.parse(localStorage.getItem(key) || '{}'); } catch (e) { saved = {}; }
      var inputs = board.querySelectorAll('input[type="checkbox"][data-key]');
      inputs.forEach(function(inp) {
        if (saved[inp.getAttribute('data-key')]) inp.checked = true;
        inp.addEventListener('change', function() {
          saved[inp.getAttribute('data-key')] = inp.checked;
          try { localStorage.setItem(key, JSON.stringify(saved)); } catch (e) {}
          updateProgress(inp.closest('.check-stage'));
        });
      });
      board.querySelectorAll('.check-stage').forEach(updateProgress);
      var resetBtn = board.querySelector('.check-reset');
      if (resetBtn) {
        resetBtn.addEventListener('click', function() {
          if (!confirm('전체 체크 상태를 초기화할까요?')) return;
          inputs.forEach(function(inp) { inp.checked = false; });
          try { localStorage.removeItem(key); } catch (e) {}
          board.querySelectorAll('.check-stage').forEach(updateProgress);
        });
      }
    });
  }
  function updateProgress(stage) {
    if (!stage) return;
    var inps = stage.querySelectorAll('input[type="checkbox"]');
    var total = inps.length;
    var done = 0;
    inps.forEach(function(i) { if (i.checked) done++; });
    var bar = stage.querySelector('.check-progress-bar');
    var txt = stage.querySelector('.check-progress-text');
    var pct = total > 0 ? Math.round((done / total) * 100) : 0;
    if (bar) bar.style.setProperty('--progress', pct + '%');
    if (txt) txt.textContent = done + ' / ' + total;
  }
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    initChecklists();
  } else {
    document.addEventListener('DOMContentLoaded', initChecklists);
  }
})();
</script>

</body>
</html>
"""


TEMPLATE_MODERN = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>
(function(){try{var s=localStorage.getItem('mamgyeot-theme');var d=s?(s==='dark'):(window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches);if(d)document.documentElement.classList.add('dark');}catch(e){}})();
</script>
<title>맘곁 태교 — 이론편 · 모던</title>
<meta name="description" content="사주당 이씨와 오늘의 의학이 같은 자리에서 만나는 책. 모던 디자인 버전.">
<meta name="author" content="권의철, 최소라">
<meta property="og:title" content="맘곁 태교 — 이론편 (모던)">
<meta property="og:type" content="book">
<meta property="og:locale" content="ko_KR">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&family=Noto+Serif+KR:wght@500;600;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #f5f3f0;
  --bg-soft: #ffffff;
  --text: #2c2c2c;
  --text-soft: #585858;
  --accent: #b86f5c;
  --accent-rose: #c49db0;
  --accent-sage: #8fa985;
  --accent-mustard: #c8a35a;
  --accent-lavender: #9c8fb0;
  --line: #e5e1da;
  --line-strong: #d6d0c5;
  --serif: 'Noto Serif KR', serif;
  --sans: 'Noto Sans KR', 'Apple SD Gothic Neo', system-ui, -apple-system, sans-serif;
  --card-shadow: 0 2px 10px rgba(0,0,0,0.04);
  --card-shadow-hover: 0 6px 18px rgba(0,0,0,0.08);

  --pen-yellow: rgba(245, 211, 100, 0.5);
  --pen-peach: rgba(244, 178, 154, 0.45);
  --pen-sage: rgba(167, 198, 169, 0.45);
  --backdrop: rgba(20, 18, 16, 0.32);
  --shadow-soft: rgba(0, 0, 0, 0.06);
  --shadow-medium: rgba(0, 0, 0, 0.12);
  --shadow-strong: rgba(0, 0, 0, 0.18);
  --toast-bg: #2c2826;
  --toast-text: #ffffff;
  --back-to-top-text: #ffffff;
  --bg-flow-from: #efeae0;
  --bg-flow-to-text: #ffffff;
  --card-modern-bg: #ffffff;
  --ring-bg: rgba(255, 255, 255, 0.55);
  --mandala-center-text: #ffffff;
}

:root.dark {
  --bg: #1c1c1c;
  --bg-soft: #262626;
  --text: #ececec;
  --text-soft: #b6b2ad;
  --accent: #d49380;
  --accent-rose: #d4adbe;
  --accent-sage: #a3bc99;
  --accent-mustard: #d6b676;
  --accent-lavender: #b3a6c4;
  --line: #333;
  --line-strong: #444;
  --card-shadow: 0 2px 10px rgba(0,0,0,0.35);
  --card-shadow-hover: 0 6px 18px rgba(0,0,0,0.5);

  --pen-yellow: rgba(245, 211, 100, 0.5);
  --pen-peach: rgba(244, 178, 154, 0.42);
  --pen-sage: rgba(167, 198, 169, 0.42);
  --backdrop: rgba(0, 0, 0, 0.55);
  --shadow-soft: rgba(0, 0, 0, 0.3);
  --shadow-medium: rgba(0, 0, 0, 0.4);
  --shadow-strong: rgba(0, 0, 0, 0.55);
  --toast-bg: #2a2826;
  --toast-text: #eaeaea;
  --back-to-top-text: #1c1c1c;
  --bg-flow-from: #2a2a2a;
  --bg-flow-to-text: #f5f5f0;
  --card-modern-bg: #232323;
  --ring-bg: rgba(40, 40, 40, 0.6);
  --mandala-center-text: #f5f5f0;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body, .chapter, .drawer-nav, table.data, blockquote.meta-note,
#drawer, #menu-toggle, #dark-toggle, #theme-switcher,
.toc-card, .ch-card {
  transition: background-color 0.28s ease, color 0.28s ease, border-color 0.28s ease;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  font-size: 18px;
  line-height: 1.85;
  font-weight: 400;
  word-break: keep-all;
  overflow-wrap: break-word;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.book {
  max-width: 720px;
  margin: 0 auto;
  padding: 64px 28px 96px;
}

/* 풀-블리드 아트 표지 — 이미지 한 장만 */
.book-cover {
  margin: -64px -22px 36px;
  padding: 0;
}
.book-cover-art {
  margin: 0;
  display: block;
  border-radius: 0 0 18px 18px;
  overflow: hidden;
}
.book-cover-art img {
  display: block;
  width: 100%;
  height: auto;
  margin: 0;
}
@media (max-width: 600px) {
  /* 모바일 .book padding(28px 14px)에 맞춰 음의 margin 보정 */
  .book-cover { margin: -28px -14px 24px; }
}
@media print {
  .book-cover { page-break-after: always; margin: 0; }
}

/* =========== Cover (모던) =========== */
.cover {
  text-align: center;
  padding: 56px 24px 48px;
  background: var(--bg-soft);
  border-radius: 18px;
  border: 1px solid var(--line);
  box-shadow: var(--card-shadow);
  margin-bottom: 36px;
}
.cover .cover-logo {
  width: 56px; height: 56px; margin: 0 auto 20px;
  border-radius: 14px; overflow: hidden;
  background: var(--bg);
  display: flex; align-items: center; justify-content: center;
}
.cover .cover-logo img { width: 100%; height: 100%; object-fit: contain; }
.cover .brand {
  display: inline-block;
  font-family: var(--sans);
  font-size: 11.5px;
  letter-spacing: 0.4em;
  color: var(--accent);
  text-transform: uppercase;
  background: rgba(184, 111, 92, 0.1);
  padding: 5px 14px;
  border-radius: 999px;
  margin-bottom: 22px;
}
.cover h1 {
  font-family: var(--serif);
  font-size: 38px; font-weight: 700;
  margin: 0 0 10px;
  letter-spacing: -0.015em;
  line-height: 1.25;
}
.cover .sub {
  font-size: 13.5px;
  color: var(--text-soft);
  letter-spacing: 0.25em;
  font-weight: 500;
}
.cover .cover-hero { margin: 24px auto 6px; max-width: 440px; }
.cover .cover-hero img { width: 100%; height: auto; }
.cover .cover-tagline {
  margin-top: 22px;
  font-size: 14px;
  color: var(--text);
  letter-spacing: 0.02em;
  font-weight: 500;
}
.cover .cover-authors {
  margin-top: 28px;
  font-size: 13px;
  color: var(--text);
  letter-spacing: 0.12em;
  font-weight: 600;
}
.cover .cover-publisher {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-soft);
  letter-spacing: 0.12em;
}

/* =========== Front pages =========== */
.front-page {
  text-align: center;
  padding: 56px 24px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: 16px;
  margin-bottom: 24px;
  box-shadow: var(--card-shadow);
}
.front-page.dedication {
  padding: 76px 24px;
  font-size: 16px;
  line-height: 2.05;
  color: var(--text);
}
.front-page.dedication .dedi { margin: 0; }
.front-page.dedication::before {
  content: "🌿";
  display: block;
  font-size: 22px;
  margin-bottom: 18px;
  opacity: 0.7;
}
@media print { .front-page { page-break-after: always; } }

/* =========== TOC (카드 그리드) =========== */
.toc {
  margin: 16px 0 56px;
}
.toc h2 {
  font-family: var(--sans);
  font-size: 12px;
  letter-spacing: 0.4em;
  color: var(--accent);
  font-weight: 700;
  margin: 0 0 18px;
  text-transform: uppercase;
  text-align: center;
}
.toc h2::before { content: "📖 "; letter-spacing: normal; }
.toc .toc-group + .toc-group { margin-top: 36px; }
.toc-group-label {
  font-family: var(--sans);
  font-size: 11.5px;
  letter-spacing: 0.3em;
  color: var(--text-soft);
  font-weight: 700;
  margin: 0 0 14px;
  text-transform: uppercase;
  text-align: center;
}
.toc-group-label::before { content: "❯ "; color: var(--accent); }
.toc ol {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}
.toc ol.toc-appendix { grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); }
.toc ol.toc-appendix a {
  background: var(--bg);
  border-color: var(--line);
  font-weight: 500;
  font-size: 13.5px;
  color: var(--text-soft);
}
.toc ol.toc-appendix a:hover { color: var(--text); }
.toc li { margin: 0; font-size: 14.5px; }
.toc a {
  display: block;
  padding: 14px 16px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-left: 3px solid var(--accent);
  border-radius: 10px;
  color: var(--text);
  text-decoration: none;
  font-weight: 500;
  line-height: 1.5;
  transition: border-color 0.18s, transform 0.18s, box-shadow 0.18s;
}
.toc a:hover {
  transform: translateY(-1px);
  box-shadow: var(--card-shadow);
  border-left-color: var(--accent);
}
.toc li:nth-child(5n+1) a { border-left-color: var(--accent); }
.toc li:nth-child(5n+2) a { border-left-color: var(--accent-sage); }
.toc li:nth-child(5n+3) a { border-left-color: var(--accent-rose); }
.toc li:nth-child(5n+4) a { border-left-color: var(--accent-mustard); }
.toc li:nth-child(5n+5) a { border-left-color: var(--accent-lavender); }

/* =========== Chapter (LongBlack 스타일 — 타이포 중심) =========== */
.chapter {
  margin: 36px 0;
  padding: 48px 36px 40px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: 14px;
  scroll-margin-top: 32px;
}
.chapter-header {
  margin-bottom: 36px;
  padding-bottom: 0;
  border-bottom: none;
  text-align: left;
}
.chapter-num {
  display: inline-block;
  font-family: var(--sans);
  font-size: 12px;
  letter-spacing: 0.28em;
  color: var(--accent);
  margin-bottom: 14px;
  text-transform: uppercase;
  font-weight: 700;
  padding: 0;
  background: transparent;
}
.chapter:nth-of-type(5n+2) .chapter-num { color: var(--accent-sage); background: transparent; }
.chapter:nth-of-type(5n+3) .chapter-num { color: var(--accent-rose); background: transparent; }
.chapter:nth-of-type(5n+4) .chapter-num { color: var(--accent-mustard); background: transparent; }
.chapter:nth-of-type(5n+5) .chapter-num { color: var(--accent-lavender); background: transparent; }
.chapter-title {
  font-family: var(--sans);
  font-size: 34px;
  font-weight: 800;
  margin: 0;
  line-height: 1.32;
  letter-spacing: -0.02em;
  color: var(--text);
}

.chapter-illust {
  margin: 0 0 14px;
  display: flex;
  align-items: flex-end;
  justify-content: flex-start;
  height: 96px;
}
.chapter-illust img {
  max-width: 80px;
  max-height: 96px;
  width: auto;
  height: auto;
  object-fit: contain;
  display: block;
}
@media (max-width: 600px) {
  .chapter-illust { height: 80px; }
  .chapter-illust img { max-width: 68px; max-height: 80px; }
}

/* =========== Body — LongBlack 스타일 가독성 =========== */
.chapter-body {
  font-size: 18px;
  line-height: 1.85;
  color: var(--text);
}
.chapter-body p {
  margin: 0 0 1.55em;
  letter-spacing: -0.005em;
}

/* 소제목 — 두꺼운 가중치, 좌측 컬러 바만 */
.chapter-body .subhead {
  font-family: var(--sans);
  font-size: 22px;
  font-weight: 800;
  margin: 2.4em 0 0.9em;
  color: var(--text);
  letter-spacing: -0.015em;
  line-height: 1.4;
  position: relative;
  padding-left: 16px;
}
.chapter-body .subhead::before {
  content: "";
  position: absolute;
  left: 0; top: 0.18em; bottom: 0.18em;
  width: 4px;
  border-radius: 2px;
  background: var(--accent);
}
.chapter-body .subhead-2 {
  font-family: var(--sans);
  font-size: 17px;
  font-weight: 700;
  margin: 1.9em 0 0.6em;
  color: var(--accent);
  letter-spacing: -0.005em;
}
.chapter-body .subhead-3 {
  font-family: var(--sans);
  font-size: 15px;
  font-weight: 700;
  margin: 1.5em 0 0.5em;
  color: var(--accent-sage);
  letter-spacing: -0.003em;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(143, 169, 133, 0.08);
  border-radius: 999px;
}
:root.dark .chapter-body .subhead-3 {
  background: rgba(163, 188, 153, 0.1);
}
.chapter-body .subhead-4 {
  font-family: var(--sans);
  font-size: 14px;
  font-weight: 700;
  margin: 1.3em 0 0.5em;
  color: var(--text);
  letter-spacing: -0.005em;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* 섹션 구분선 — 큰 여백만으로 (장식 없음) */
.chapter-body hr.section-break {
  border: 0; background: transparent;
  margin: 2.4em 0;
  height: 1px;
  width: 48px;
  background: var(--line-strong);
  opacity: 0.6;
}

/* 불릿 — 컬러 도트, 본문 사이즈와 같은 크기 */
.chapter-body ul.bullets {
  margin: 1.3em 0 1.6em;
  padding-left: 0;
  list-style: none;
}
.chapter-body ul.bullets li {
  margin: 0.6em 0;
  position: relative;
  padding-left: 24px;
  line-height: 1.75;
}
.chapter-body ul.bullets li::before {
  content: "";
  position: absolute;
  left: 6px; top: 0.78em;
  width: 7px; height: 7px;
  border-radius: 50%;
  background: var(--accent);
}
.chapter-body ul.bullets li:nth-child(5n+2)::before { background: var(--accent-sage); }
.chapter-body ul.bullets li:nth-child(5n+3)::before { background: var(--accent-rose); }
.chapter-body ul.bullets li:nth-child(5n+4)::before { background: var(--accent-mustard); }
.chapter-body ul.bullets li:nth-child(5n+5)::before { background: var(--accent-lavender); }

/* 인용/메모 → 매거진 풀-쿼트 (LongBlack 스타일) */
.chapter-body blockquote.meta-note {
  margin: 2em 0;
  padding: 6px 0 6px 20px;
  background: transparent;
  border: none;
  border-left: 3px solid var(--accent);
  border-radius: 0;
  font-size: 18.5px;
  color: var(--text);
  line-height: 1.7;
  font-weight: 500;
  letter-spacing: -0.005em;
}
.chapter-body blockquote.meta-note::before { content: none; }

/* 강조 마커 */
.chapter-body strong { font-weight: 700; color: var(--text); }
.chapter-body em {
  font-style: normal;
  font-weight: 700;
  background: linear-gradient(180deg,
    transparent 0%, transparent 60%,
    var(--pen-yellow) 60%, var(--pen-yellow) 92%,
    transparent 92%);
  padding: 0 2px;
}
/* 영문 인용·각주·참고문헌 표는 이탤릭 유지 */
aside.footnotes em,
.chapter.is-appendix table.data em {
  font-style: italic;
  font-weight: inherit;
  background: none;
  padding: 0;
}
.chapter-body mark { color: inherit; padding: 0 3px; border-radius: 3px; }
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

.chapter-body a {
  color: var(--accent);
  text-decoration: none;
  border-bottom: 1px solid var(--accent);
  transition: background 0.18s, color 0.18s;
  padding: 0 1px;
  border-radius: 2px;
}
.chapter-body a:hover {
  background: rgba(184, 111, 92, 0.1);
}

/* 각주 */
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
  margin: 2.6em 0 0;
  padding: 22px 22px 18px;
  background: var(--bg);
  border-radius: 10px;
  border: 1px solid var(--line);
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-soft);
}
aside.footnotes h4 {
  font-size: 11px;
  letter-spacing: 0.3em;
  font-weight: 700;
  color: var(--accent);
  margin: 0 0 12px;
  text-transform: uppercase;
}
aside.footnotes h4::before { content: "📎 "; letter-spacing: normal; }
aside.footnotes ol { padding-left: 1.3em; margin: 0; }
aside.footnotes li { margin: 0.6em 0; padding-left: 4px; }
aside.footnotes a.fn-back {
  color: var(--accent); text-decoration: none;
  margin-left: 6px; font-size: 13px;
}
aside.footnotes em { font-style: italic; }
aside.footnotes code {
  background: var(--bg-soft);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12px;
}

/* 표 — 줄무늬 행으로 스캔 용이 */
table.data {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  margin: 1.8em 0 2.2em;
  font-size: 14px;
  line-height: 1.65;
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: var(--card-shadow);
}
table.data thead { background: var(--bg); }
table.data th, table.data td {
  text-align: left;
  vertical-align: top;
  padding: 13px 15px;
  border-bottom: 1px solid var(--line);
  word-break: keep-all;
}
table.data th {
  font-weight: 700;
  color: var(--accent);
  font-size: 12px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
table.data tbody tr:nth-child(even) td { background: rgba(0,0,0,0.015); }
:root.dark table.data tbody tr:nth-child(even) td { background: rgba(255,255,255,0.025); }
table.data tr:last-child td { border-bottom: none; }
@media (max-width: 600px) {
  table.data { font-size: 12.5px; }
  table.data th, table.data td { padding: 9px 10px; }
}

/* =========== 장 끝 태담 카드 (실천편, 모던) =========== */
.chapter-end-script {
  margin: 2.6em 0 2.2em;
  padding: 26px 28px 24px;
  background: linear-gradient(135deg, var(--bg-soft) 0%, var(--bg) 100%);
  border: 1px solid var(--line);
  border-left: 5px solid var(--accent);
  border-radius: 14px;
  font-family: var(--sans);
  position: relative;
}
.cend-head {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px dashed var(--line);
}
.cend-tag {
  display: inline-block;
  padding: 5px 14px;
  background: var(--accent);
  color: #fff;
  border-radius: 999px;
  font-size: 11.5px; font-weight: 700;
  letter-spacing: 0.22em; text-transform: uppercase;
}
.cend-extra {
  font-size: 13px; font-weight: 500;
  color: var(--text-soft);
  letter-spacing: 0.04em;
}
.cend-body {
  margin: 0;
  padding: 0;
  background: transparent;
  border: none;
  font-size: 16px; line-height: 1.85;
  color: var(--text);
  font-style: normal;
  font-weight: 500;
  letter-spacing: -0.005em;
}
.cend-body::before { content: none; }

/* =========== 상황별 태담 10선 카드 그리드 (실천편, 모던) =========== */
.situ-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
  margin: 1.6em 0 2.2em;
}
.situ-card {
  padding: 22px 24px 20px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: 14px;
  font-family: var(--sans);
  display: flex; flex-direction: column;
  transition: transform 0.18s, box-shadow 0.18s;
}
.situ-card:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0,0,0,0.06); }
.situ-card-head {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px dashed var(--line);
}
.situ-num {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 36px; height: 36px;
  padding: 0 10px;
  background: var(--accent);
  color: #fff;
  border-radius: 999px;
  font-size: 14px; font-weight: 800;
  letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums;
}
.situ-card-title {
  margin: 0;
  font-size: 16px; font-weight: 800;
  color: var(--text);
  letter-spacing: -0.01em;
  line-height: 1.4;
}
.situ-card-body {
  margin: 0;
  padding: 14px 16px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-left: none;
  border-radius: 10px;
  font-size: 14.5px; line-height: 1.75;
  color: var(--text);
  font-style: normal;
  font-weight: 500;
}
.situ-card-body::before { content: none; }
.situ-card:nth-child(5n+2) .situ-num { background: var(--accent-sage); }
.situ-card:nth-child(5n+3) .situ-num { background: var(--accent-rose); }
.situ-card:nth-child(5n+4) .situ-num { background: var(--accent-mustard); }
.situ-card:nth-child(5n+5) .situ-num { background: var(--accent-lavender); }
@media (max-width: 600px) {
  .situ-grid { grid-template-columns: 1fr; }
  .situ-card { padding: 20px 20px 18px; }
}

/* =========== 시기별 변화 타임라인 (실천편, 모던) =========== */
.period-timeline {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
  margin: 1.8em 0 2.2em;
}
.period-card {
  padding: 22px 24px 20px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-top: 5px solid var(--accent);
  border-radius: 14px;
  font-family: var(--sans);
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: transform 0.18s, box-shadow 0.18s;
}
.period-card:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0,0,0,0.06); }
.period-tag {
  font-size: 16px; font-weight: 800;
  letter-spacing: -0.005em;
  color: var(--accent);
  font-variant-numeric: tabular-nums;
}
.period-month {
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.2em; text-transform: uppercase;
  color: var(--text-soft);
  margin-bottom: 6px;
}
.period-body {
  margin: 8px 0 0;
  padding-top: 12px;
  border-top: 1px dashed var(--line);
  font-size: 14.5px; line-height: 1.7;
  color: var(--text);
  font-weight: 500;
}
.period-card:nth-child(5n+2) { border-top-color: var(--accent-sage); }
.period-card:nth-child(5n+2) .period-tag { color: var(--accent-sage); }
.period-card:nth-child(5n+3) { border-top-color: var(--accent-rose); }
.period-card:nth-child(5n+3) .period-tag { color: var(--accent-rose); }
.period-card:nth-child(5n+4) { border-top-color: var(--accent-mustard); }
.period-card:nth-child(5n+4) .period-tag { color: var(--accent-mustard); }
.period-card:nth-child(5n+5) { border-top-color: var(--accent-lavender); }
.period-card:nth-child(5n+5) .period-tag { color: var(--accent-lavender); }
.period-card--imminent {
  border-top-color: #d97757 !important;
  background: linear-gradient(180deg, rgba(217, 119, 87, 0.08) 0%, transparent 100%);
}
.period-card--imminent .period-tag { color: #b04830 !important; }
@media (max-width: 600px) {
  .period-timeline { grid-template-columns: 1fr; }
}

/* D-DAY 카운트다운 (모던) */
.dday-row {
  margin: 1.6em 0 2em;
  padding: 22px 24px 20px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-left: 5px solid var(--accent);
  border-radius: 14px;
  font-family: var(--sans);
}
.dday-head { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.dday-icon { font-size: 22px; }
.dday-label {
  font-size: 12px; font-weight: 700;
  letter-spacing: 0.24em; text-transform: uppercase;
  color: var(--accent);
}
.dday-cards {
  list-style: none; margin: 0; padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
}
.dday-card {
  padding: 14px 16px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: 12px;
  text-align: center;
  display: flex; flex-direction: column; gap: 2px;
}
.dday-week {
  font-size: 22px; font-weight: 800;
  color: var(--accent);
  letter-spacing: -0.01em;
  font-variant-numeric: tabular-nums;
}
.dday-month {
  font-size: 11.5px; color: var(--text-soft);
  letter-spacing: 0.06em; font-weight: 600;
}
.dday-remain {
  margin-top: 6px;
  padding-top: 8px;
  border-top: 1px dashed var(--line);
  font-size: 13px; color: var(--text);
  font-weight: 700;
}

/* =========== 태담 기본 공식 (실천편, 모던) =========== */
.talk-formula {
  margin: 1.8em 0 2.2em;
  padding: 26px 26px 22px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 16px;
  font-family: var(--sans);
}
.talk-formula-row {
  display: flex; flex-wrap: wrap; align-items: center;
  gap: 10px;
  margin-bottom: 22px;
  padding-bottom: 20px;
  border-bottom: 1px dashed var(--line);
}
.talk-chip {
  display: inline-block;
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 14px; font-weight: 700;
  letter-spacing: -0.005em;
  color: #fff;
}
.talk-chip--1 { background: #c8a874; }
.talk-chip--2 { background: #6aa1c2; }
.talk-chip--3 { background: #e08aa1; }
.talk-chip--4 { background: #8fa766; }
.talk-plus {
  font-size: 20px; font-weight: 700;
  color: var(--text-soft);
  user-select: none;
}
.talk-formula-example { position: relative; }
.talk-example-tag {
  display: inline-block;
  font-size: 11px; font-weight: 700;
  letter-spacing: 0.24em; text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 10px;
}
.talk-example-line {
  margin: 0 0 8px;
  display: flex; flex-wrap: wrap; align-items: center;
  gap: 12px;
  font-size: 15px; line-height: 1.7;
  color: var(--text);
}
.talk-example-line span { flex: 1; min-width: 0; }
.talk-example-label {
  font-size: 11.5px; font-weight: 700;
  letter-spacing: -0.005em;
  padding: 4px 12px;
  border-radius: 999px;
  color: #fff;
  font-style: normal;
  white-space: nowrap;
}
@media (max-width: 600px) {
  .talk-formula-row { gap: 7px; }
  .talk-chip { padding: 7px 13px; font-size: 13px; }
  .talk-plus { font-size: 16px; }
  .talk-example-line { gap: 8px; font-size: 14.5px; }
}

/* =========== 첫 태담 스크립트 카드 (실천편, 모던) =========== */
.script-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
  margin: 1.8em 0 2.2em;
}
.script-grid--single { grid-template-columns: minmax(0, 520px); justify-content: start; }
.script-card {
  padding: 22px 24px 20px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-left: 5px solid var(--accent);
  border-radius: 14px;
  font-family: var(--sans);
  transition: transform 0.18s, box-shadow 0.18s;
}
.script-card:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(0,0,0,0.08); }
.script-card-head {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 14px;
}
.script-pin { font-size: 22px; line-height: 1; }
.script-card-title {
  margin: 0; font-size: 16px; font-weight: 800;
  color: var(--text); letter-spacing: -0.01em;
}
.script-card-body {
  margin: 0;
  padding: 14px 16px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-left: none;
  border-radius: 10px;
  font-size: 15px; line-height: 1.75;
  color: var(--text);
  font-style: normal;
  font-weight: 500;
}
.script-card-body::before { content: none; }
.script-card:nth-child(5n+2) { border-left-color: #6aa1c2; }
.script-card:nth-child(5n+3) { border-left-color: #e08aa1; }
.script-card:nth-child(5n+4) { border-left-color: #e8c553; }
.script-card:nth-child(5n+5) { border-left-color: #8fa766; }
.script-card--dad { border-left-color: #7e5ea7; }
@media (max-width: 600px) {
  .script-grid { grid-template-columns: 1fr; }
  .script-card { padding: 20px 20px 18px; }
}

/* =========== 감정 색상표 (실천편 PART 1, 모던) =========== */
.color-palette {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
  margin: 1.8em 0 2.2em;
}
.color-card {
  --card-bg: #f5f0e6;
  --card-accent: #b89d72;
  --card-text: #2c2826;
  position: relative;
  padding: 28px 24px 24px;
  background: var(--card-bg);
  border-radius: 16px;
  border: 1px solid rgba(0,0,0,0.06);
  box-shadow: 0 4px 14px rgba(0,0,0,0.06);
  font-family: var(--sans);
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
}
.color-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(0,0,0,0.1);
}
.color-card::before {
  content: ""; position: absolute;
  top: 0; left: 0; right: 0; height: 10px;
  background: var(--card-accent);
}
.color-swatch {
  display: inline-block;
  width: 36px; height: 36px;
  border-radius: 50%;
  background: var(--card-accent);
  border: 3px solid rgba(255,255,255,0.85);
  box-shadow: 0 3px 10px rgba(0,0,0,0.18);
  margin-bottom: 12px;
}
.color-name {
  margin: 0 0 8px;
  font-size: 19px; font-weight: 800;
  color: var(--card-text);
  letter-spacing: -0.01em;
  font-family: var(--sans);
}
.color-keywords {
  margin: 0 0 14px;
  font-size: 14px;
  color: var(--card-text);
  opacity: 0.78;
  line-height: 1.6;
  font-weight: 500;
}
.color-quote {
  margin: 0;
  padding: 12px 16px;
  background: rgba(255,255,255,0.55);
  border-radius: 10px;
  font-size: 14px;
  color: var(--card-text);
  line-height: 1.65;
  font-style: italic;
  font-weight: 500;
}

.color-card--beige  { --card-bg: #f0e3cb; --card-accent: #c8a874; --card-text: #4a3a23; }
.color-card--yellow { --card-bg: #fbeec1; --card-accent: #e8c553; --card-text: #5a4815; }
.color-card--olive  { --card-bg: #d8e0bd; --card-accent: #8fa766; --card-text: #38461c; }
.color-card--pink   { --card-bg: #f6d9de; --card-accent: #e08aa1; --card-text: #6e2e3e; }
.color-card--blue   { --card-bg: #d2e1ec; --card-accent: #6aa1c2; --card-text: #234862; }
.color-card--gray   { --card-bg: #d6d4cf; --card-accent: #5a5853; --card-text: #2a2925; }
.color-card--violet { --card-bg: #ddd0ea; --card-accent: #7e5ea7; --card-text: #382356; }

:root.dark .color-card {
  border-color: rgba(255,255,255,0.08);
  box-shadow: 0 4px 14px rgba(0,0,0,0.4);
}
:root.dark .color-quote {
  background: rgba(0,0,0,0.2);
}
@media (max-width: 600px) {
  .color-palette { grid-template-columns: 1fr; gap: 12px; }
  .color-card { padding: 22px 20px 20px; }
}
@media print {
  .color-card { page-break-inside: avoid; box-shadow: none; }
}

/* =========== 부록 D 안전 박스 (모던) =========== */
.safety-board { margin: 1.6em 0 2em; }
.safety-emergency {
  margin: 0 0 28px;
  padding: 26px 28px 28px;
  background: linear-gradient(135deg, #fff3ec 0%, #ffe1d2 100%);
  border: 2px solid #d97757;
  border-radius: 16px;
  box-shadow: 0 6px 20px rgba(217, 119, 87, 0.18);
}
:root.dark .safety-emergency {
  background: linear-gradient(135deg, #2c1f1c 0%, #3a2520 100%);
  border-color: #c9805f;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.55);
}
.safety-emergency-head {
  display: flex; align-items: center; gap: 14px;
  margin-bottom: 8px;
}
.safety-emergency-icon { font-size: 32px; line-height: 1; }
.safety-emergency-title {
  font-family: var(--sans);
  font-size: 22px; font-weight: 800;
  margin: 0;
  color: #b04830;
  letter-spacing: -0.015em;
  line-height: 1.3;
}
:root.dark .safety-emergency-title { color: #ffb89e; }
.safety-emergency-lede {
  font-family: var(--sans); font-size: 15px;
  color: var(--text); line-height: 1.65;
  margin: 0 0 16px;
  font-weight: 500;
}
.safety-emergency-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 10px;
}
.safety-call {
  display: block;
  padding: 14px 16px;
  background: #ffffff;
  border: 1px solid rgba(176, 72, 48, 0.3);
  border-radius: 12px;
  text-decoration: none !important;
  text-align: center;
  transition: transform 0.15s, box-shadow 0.15s;
  border-bottom: 1px solid rgba(176, 72, 48, 0.3) !important;
}
:root.dark .safety-call { background: #1c1c1c; border-color: rgba(255, 184, 158, 0.3) !important; }
.safety-call:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 14px rgba(0,0,0,0.1);
  background: #fff !important;
}
.safety-call-num {
  display: block;
  font-family: var(--sans); font-size: 24px; font-weight: 800;
  color: #b04830;
  letter-spacing: -0.005em;
  font-variant-numeric: tabular-nums;
}
:root.dark .safety-call-num { color: #ffb89e; }
.safety-call-label {
  display: block; margin-top: 3px;
  font-family: var(--sans); font-size: 12px;
  color: var(--text-soft);
  letter-spacing: 0;
  font-weight: 500;
}

.safety-tiers {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.safety-tier {
  padding: 20px 22px 18px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-left: 5px solid var(--accent);
  border-radius: 14px;
  font-family: var(--sans);
}
.safety-tier--soft { border-left-color: var(--accent); }
.safety-tier--rose { border-left-color: var(--accent-rose); }
.safety-tier--sage { border-left-color: var(--accent-sage); }
.safety-tier--mustard { border-left-color: var(--accent-mustard); }
.safety-tier--lavender { border-left-color: var(--accent-lavender); }
.safety-tier-head { margin-bottom: 8px; }
.safety-tier-tag {
  display: inline-block;
  font-size: 10.5px; font-weight: 700;
  letter-spacing: 0.22em; text-transform: uppercase;
  color: var(--accent);
  margin-bottom: 4px;
}
.safety-tier--rose .safety-tier-tag { color: var(--accent-rose); }
.safety-tier--sage .safety-tier-tag { color: var(--accent-sage); }
.safety-tier--mustard .safety-tier-tag { color: var(--accent-mustard); }
.safety-tier--lavender .safety-tier-tag { color: var(--accent-lavender); }
.safety-tier-title {
  font-size: 17px; font-weight: 800;
  margin: 0 0 8px; color: var(--text);
  line-height: 1.4; letter-spacing: -0.01em;
}
.safety-tier-lede {
  font-size: 14px; color: var(--text-soft);
  margin: 0 0 12px; line-height: 1.65;
}
.safety-tier-list {
  list-style: none; padding: 0; margin: 0 0 14px;
  font-size: 13.5px; line-height: 1.7;
}
.safety-tier-list li {
  padding: 5px 0 5px 20px;
  position: relative;
  color: var(--text);
}
.safety-tier-list li::before {
  content: "•"; position: absolute; left: 6px;
  color: var(--accent); font-weight: 700;
}
.safety-tier-list strong { font-weight: 700; }
.safety-tier-actions { display: flex; flex-wrap: wrap; gap: 6px; }
.safety-tier-btn {
  display: inline-block;
  padding: 8px 14px;
  background: var(--accent) !important;
  color: #ffffff !important;
  text-decoration: none !important;
  border: 1px solid var(--accent) !important;
  border-radius: 999px;
  font-size: 12.5px; font-weight: 700;
  letter-spacing: -0.005em;
  transition: transform 0.15s;
}
.safety-tier-btn:hover { transform: translateY(-1px); }
.safety-tier-btn--ghost {
  background: transparent !important;
  color: var(--text) !important;
  border-color: var(--line) !important;
}
.safety-tier-btn--ghost:hover { border-color: var(--accent) !important; color: var(--accent) !important; }

.safety-footnote {
  margin: 24px 0 0;
  padding: 14px 18px;
  background: var(--bg-soft);
  border: 1px dashed var(--line);
  border-radius: 10px;
  font-family: var(--sans);
  font-size: 12.5px; line-height: 1.7;
  color: var(--text-soft);
}
@media (max-width: 600px) {
  .safety-emergency { padding: 22px 20px 22px; }
  .safety-emergency-title { font-size: 19px; }
  .safety-emergency-grid { grid-template-columns: repeat(2, 1fr); }
  .safety-tiers { grid-template-columns: 1fr; }
}
@media print {
  .safety-emergency, .safety-tier { page-break-inside: avoid; box-shadow: none; }
  .safety-tier-btn { background: transparent !important; color: #000 !important; border-color: #999 !important; }
}

/* =========== 부록 B 카드형 체크리스트 (모던) =========== */
.check-board { margin: 1.4em 0 2em; }
.check-stage {
  margin: 1.8em 0 2.2em;
  padding: 26px 26px 22px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 16px;
}
.check-stage-head { margin-bottom: 18px; }
.check-stage-meta {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 10px;
}
.check-stage-num {
  font-family: var(--sans); font-size: 11px; font-weight: 700;
  letter-spacing: 0.24em; text-transform: uppercase;
  color: #fff; background: var(--accent);
  padding: 4px 12px; border-radius: 999px;
}
.check-stage:nth-of-type(5n+2) .check-stage-num { background: var(--accent-sage); }
.check-stage:nth-of-type(5n+3) .check-stage-num { background: var(--accent-rose); }
.check-stage:nth-of-type(5n+4) .check-stage-num { background: var(--accent-mustard); }
.check-stage:nth-of-type(5n+5) .check-stage-num { background: var(--accent-lavender); }
.check-stage-range {
  font-family: var(--sans); font-size: 13px;
  color: var(--text-soft); letter-spacing: 0.04em;
  font-weight: 500;
}
.check-stage-title {
  font-family: var(--sans);
  font-size: 20px; font-weight: 800;
  margin: 0 0 6px;
  color: var(--text); letter-spacing: -0.015em;
  line-height: 1.35;
}
.check-stage-sub {
  font-family: var(--sans);
  font-size: 14.5px; color: var(--text-soft);
  margin: 0 0 14px; line-height: 1.55;
}
.check-stage-progress {
  display: flex; align-items: center; gap: 10px;
  font-family: var(--sans); font-size: 12.5px; color: var(--text-soft);
}
.check-progress-bar {
  flex: 1; height: 5px; border-radius: 999px;
  background: var(--bg-soft);
  position: relative; overflow: hidden;
  border: 1px solid var(--line);
}
.check-progress-bar::after {
  content: ""; position: absolute;
  left: 0; top: 0; bottom: 0;
  width: var(--progress, 0%);
  background: var(--accent);
  transition: width 0.3s ease;
}
.check-progress-text { font-weight: 700; min-width: 52px; text-align: right; font-variant-numeric: tabular-nums; }

.check-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
  gap: 12px;
  margin-top: 14px;
}
.check-card {
  display: grid;
  grid-template-columns: 22px 1fr;
  grid-template-rows: auto auto auto;
  column-gap: 14px; row-gap: 5px;
  padding: 16px 18px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.18s, background 0.18s, box-shadow 0.18s;
  font-family: var(--sans);
}
.check-card:hover {
  border-color: var(--accent);
  box-shadow: 0 2px 10px var(--shadow-soft);
}
.check-card input[type="checkbox"] {
  grid-row: 1 / span 3; grid-column: 1;
  width: 18px; height: 18px; margin: 4px 0 0;
  accent-color: var(--accent);
  cursor: pointer;
}
.check-card .check-area {
  grid-column: 2; grid-row: 1;
  font-size: 10.5px; font-weight: 700;
  letter-spacing: 0.2em; text-transform: uppercase;
  color: var(--accent);
}
.check-card[data-area="신체"] .check-area,
.check-card[data-area="청각"] .check-area,
.check-card[data-area="청각 환경"] .check-area { color: var(--accent-sage); }
.check-card[data-area="정서"] .check-area,
.check-card[data-area="정서 환경"] .check-area { color: var(--accent-rose); }
.check-card[data-area="가족"] .check-area,
.check-card[data-area="부부 환경"] .check-area { color: var(--accent-mustard); }
.check-card[data-area="정보 환경"] .check-area,
.check-card[data-area="시각"] .check-area { color: var(--accent-lavender); }
.check-card .check-item {
  grid-column: 2; grid-row: 2;
  font-size: 15px; line-height: 1.6;
  color: var(--text);
  font-weight: 500;
}
.check-card .check-ref {
  grid-column: 2; grid-row: 3;
  font-size: 11.5px; color: var(--text-soft);
  letter-spacing: 0.03em;
}
.check-card:has(input:checked) {
  background: rgba(184, 111, 92, 0.08);
  border-color: var(--accent);
}
.check-card:has(input:checked) .check-item {
  text-decoration: line-through;
  text-decoration-color: var(--text-soft);
  color: var(--text-soft);
}
:root.dark .check-card:has(input:checked) {
  background: rgba(212, 147, 128, 0.1);
}
.check-board-tools {
  display: flex; align-items: center; justify-content: space-between;
  margin: 22px 0 0; padding-top: 18px;
  border-top: 1px dashed var(--line);
  font-family: var(--sans); font-size: 12.5px;
}
.check-reset {
  background: none; border: 1px solid var(--line);
  color: var(--text-soft);
  padding: 7px 16px; border-radius: 999px;
  font-family: var(--sans); font-size: 12.5px; font-weight: 500;
  cursor: pointer;
  transition: border-color 0.18s, color 0.18s, background 0.18s;
}
.check-reset:hover { border-color: var(--accent); color: var(--accent); background: var(--bg-soft); }
.check-board-note { color: var(--text-soft); font-size: 11.5px; }
@media (max-width: 600px) {
  .check-stage { padding: 20px 18px 18px; border-radius: 14px; }
  .check-cards { grid-template-columns: 1fr; }
  .check-stage-title { font-size: 18px; }
}
@media print {
  .check-stage { page-break-inside: auto; box-shadow: none; }
  .check-card { page-break-inside: avoid; }
  .check-card input[type="checkbox"] { print-color-adjust: exact; }
  .check-board-tools { display: none; }
}

/* 다음 행동 CTA — 챕터 끝 카드 (모던) */
.next-action {
  display: flex; align-items: center; gap: 18px;
  margin: 3em 0 1em;
  padding: 22px 24px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-left: 5px solid var(--accent);
  border-radius: 14px;
  position: relative;
}
.next-action-tag {
  position: absolute; top: -11px; left: 20px;
  background: var(--accent); color: #fff;
  font-family: var(--sans); font-size: 10.5px; font-weight: 700;
  letter-spacing: 0.22em; text-transform: uppercase;
  padding: 4px 12px; border-radius: 999px;
}
.next-action-icon { font-size: 32px; line-height: 1; flex-shrink: 0; }
.next-action-text { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.next-action-headline {
  font-family: var(--sans);
  font-size: 17px; font-weight: 700;
  color: var(--text);
  letter-spacing: -0.01em;
  line-height: 1.4;
}
.next-action-sub {
  font-family: var(--sans);
  font-size: 14.5px;
  color: var(--text-soft);
  line-height: 1.65;
}
.next-action-link {
  flex-shrink: 0;
  background: var(--accent); color: #fff;
  text-decoration: none; border-bottom: none;
  font-family: var(--sans); font-size: 13px; font-weight: 700;
  padding: 9px 16px; border-radius: 999px;
  transition: transform 0.18s;
}
.next-action-link:hover { transform: translateY(-1px); background: var(--accent); }
.chapter.is-appendix .next-action { display: none; }
@media (max-width: 600px) {
  .next-action { flex-wrap: wrap; padding: 20px 18px; gap: 12px; }
  .next-action-icon { font-size: 26px; }
  .next-action-text { flex: 1 1 60%; }
  .next-action-link { width: 100%; text-align: center; }
}
@media print {
  .next-action { page-break-inside: avoid; background: white !important; border-color: #ccc !important; }
  .next-action-link { display: none; }
}

/* 맘곁 브랜드 — 함께 지나가는 시간 */
.momgyeot-brand {
  margin: 2.4em 0 1.6em;
  padding: 32px 30px 26px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  border-radius: 14px;
  box-shadow: 0 1px 6px var(--shadow-soft);
  font-family: var(--sans);
  color: var(--text);
  line-height: 1.85;
}
.momgyeot-brand .momgyeot-lead {
  font-size: 13px; font-weight: 700;
  letter-spacing: 0.22em; color: var(--accent);
  margin: 0 0 16px;
}
.momgyeot-brand .momgyeot-stanza {
  margin: 0 0 14px; font-size: 16px;
}
.momgyeot-brand .momgyeot-stanza em {
  font-style: normal;
  background: linear-gradient(180deg, transparent 60%, rgba(196, 157, 176, 0.4) 60%);
  padding: 0 2px;
}
.momgyeot-brand .momgyeot-stanza strong { color: var(--accent); font-weight: 700; }
.momgyeot-stages {
  list-style: none; padding: 0;
  margin: 24px 0 20px;
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px;
}
.momgyeot-stage {
  display: flex; flex-direction: column; gap: 10px;
  padding: 18px 16px;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 12px;
  position: relative;
}
.momgyeot-stage .stage-tag {
  font-size: 13.5px; font-weight: 700;
  letter-spacing: 0.06em; color: var(--text-soft);
}
.momgyeot-stage .stage-desc {
  font-size: 13px; color: var(--text-soft); line-height: 1.65;
}
.momgyeot-stage.is-current {
  background: var(--bg-soft);
  border-color: var(--accent);
  box-shadow: 0 2px 12px var(--shadow-soft);
}
.momgyeot-stage.is-current .stage-tag { color: var(--accent); }
.momgyeot-stage.is-current .stage-desc { color: var(--text); }
.momgyeot-stage .stage-now {
  position: absolute; top: -11px; right: 14px;
  background: var(--accent); color: #fff;
  font-size: 10.5px; font-weight: 700;
  letter-spacing: 0.12em;
  padding: 3px 10px; border-radius: 999px;
  white-space: nowrap;
}
.momgyeot-brand .momgyeot-now {
  margin: 20px 0 6px;
  font-size: 15px; font-weight: 500;
  color: var(--text); line-height: 1.75;
}
.momgyeot-brand .momgyeot-cta {
  margin: 0; font-size: 17px; font-weight: 600;
  color: var(--accent);
}
@media (max-width: 600px) {
  .momgyeot-brand { padding: 24px 20px 20px; }
  .momgyeot-stages { grid-template-columns: 1fr; gap: 12px; }
  .momgyeot-stage .stage-now { right: 12px; top: -10px; }
}
@media print {
  .momgyeot-brand { page-break-inside: avoid; background: #fff !important; border-color: #ccc !important; box-shadow: none !important; }
  .momgyeot-stage { background: #fff !important; box-shadow: none !important; }
}

/* 맘곁 공식 사이트 QR 카드 */
.momgyeot-card {
  display: flex; align-items: center; gap: 24px;
  margin: 1.8em 0;
  padding: 24px 26px;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: 0 1px 6px var(--shadow-soft);
}
.momgyeot-qr {
  flex-shrink: 0; display: block; line-height: 0;
  padding: 10px; background: #fff; border: 1px solid var(--line); border-radius: 10px;
  border-bottom: none;
}
.momgyeot-qr img { display: block; width: 150px; height: 150px; }
.momgyeot-meta { display: flex; flex-direction: column; gap: 8px; }
.momgyeot-tag {
  font-family: var(--sans); font-size: 11.5px; font-weight: 700;
  letter-spacing: 0.18em; color: var(--accent);
}
.momgyeot-link {
  font-family: var(--sans); font-size: 19px; font-weight: 700;
  color: var(--text); text-decoration: none; border-bottom: 1.5px solid var(--accent);
  align-self: flex-start; padding-bottom: 1px;
}
.momgyeot-link:hover { color: var(--accent); }
.momgyeot-hint { font-family: var(--sans); font-size: 13.5px; color: var(--text-soft); line-height: 1.6; }
@media (max-width: 600px) {
  .momgyeot-card { flex-direction: column; align-items: flex-start; gap: 16px; padding: 20px; }
  .momgyeot-qr img { width: 130px; height: 130px; }
}
@media print {
  .momgyeot-card { page-break-inside: avoid; background: #fff !important; border-color: #ccc !important; box-shadow: none !important; }
}

/* 부록은 한 톤 차분히 */
.chapter.is-appendix .chapter-num {
  color: var(--text-soft);
  background: var(--bg);
}

/* =========== Hamburger / Drawer / Dark / Theme switcher =========== */
#menu-toggle {
  position: fixed; top: 18px; left: 18px; z-index: 50;
  width: 44px; height: 44px; padding: 0;
  background: var(--bg-soft); border: 1px solid var(--line);
  border-radius: 50%; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;
  box-shadow: 0 2px 8px var(--shadow-soft);
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
}
#dark-toggle .dark-icon-dark { display: inline-block; }
#dark-toggle .dark-icon-light { display: none; }
:root.dark #dark-toggle .dark-icon-dark { display: none; }
:root.dark #dark-toggle .dark-icon-light { display: inline-block; }

#theme-switcher, #series-switcher {
  position: fixed; top: 22px; z-index: 50;
  padding: 6px 14px;
  border-radius: 999px;
  font-family: var(--sans); font-size: 12px;
  letter-spacing: 0.12em; font-weight: 600;
  text-decoration: none;
  box-shadow: 0 2px 8px var(--shadow-medium);
  transition: transform 0.18s, box-shadow 0.18s;
}
#theme-switcher {
  right: 134px;
  background: var(--accent); color: #ffffff;
}
#series-switcher {
  right: 214px;
  background: var(--bg-soft); color: var(--accent);
  border: 1px solid var(--line);
}
#theme-switcher:hover, #series-switcher:hover { transform: translateY(-1px); box-shadow: 0 4px 14px var(--shadow-strong); }

/* 다운로드 버튼 + 메뉴 */
#download-btn {
  position: fixed; top: 18px; right: 74px; z-index: 50;
  width: 44px; height: 44px; padding: 0;
  background: var(--bg-soft); border: 1px solid var(--line);
  border-radius: 50%; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; line-height: 1;
  box-shadow: 0 2px 8px var(--shadow-soft);
  transition: background 0.18s, transform 0.18s, box-shadow 0.18s;
  color: var(--accent);
}
#download-btn:hover {
  background: var(--bg);
  box-shadow: 0 3px 12px var(--shadow-medium);
}
#download-btn:active { transform: scale(0.95); }
#download-menu {
  position: fixed; top: 70px; right: 18px; z-index: 65;
  background: var(--bg-soft);
  border: 1px solid var(--line);
  border-radius: 12px;
  box-shadow: 0 6px 24px var(--shadow-strong);
  padding: 6px;
  display: none;
  min-width: 200px;
  font-family: var(--sans);
}
#download-menu[data-open="true"] { display: block; }
#download-menu button, #download-menu a {
  display: flex; align-items: center; gap: 10px;
  width: 100%;
  padding: 11px 14px;
  background: none; border: none;
  border-radius: 8px;
  color: var(--text);
  font-family: var(--sans); font-size: 14px;
  text-align: left; cursor: pointer;
  text-decoration: none;
  transition: background 0.15s;
}
#download-menu button:hover, #download-menu a:hover {
  background: var(--bg);
  color: var(--accent);
}
#download-menu .dl-icon { font-size: 17px; line-height: 1; width: 22px; text-align: center; }
#download-menu .dl-label { flex: 1; font-weight: 600; }
#download-menu .dl-sub { display: block; font-size: 11.5px; color: var(--text-soft); font-weight: 400; margin-top: 2px; }

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
  color: var(--accent); text-transform: uppercase; font-weight: 700;
}
#drawer-close {
  background: none; border: none; font-size: 26px; line-height: 1;
  color: var(--text-soft); cursor: pointer; padding: 0 4px;
}
.drawer-nav { flex: 1; overflow-y: auto; padding: 8px 0 24px; }
.drawer-group + .drawer-group { margin-top: 6px; }
.drawer-group-label {
  font-family: var(--sans); font-size: 10.5px; letter-spacing: 0.3em;
  color: var(--text-soft); font-weight: 700;
  text-transform: uppercase;
  padding: 14px 18px 8px; margin: 0;
  background: var(--bg);
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}
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
  color: var(--accent); text-transform: uppercase; font-weight: 600;
}
.toc-expand {
  background: none; border: none; border-left: 1px solid var(--line);
  width: 40px; cursor: pointer; color: var(--text-soft);
  font-size: 13px; transition: transform 0.2s, background 0.2s;
}
.toc-expand:hover { background: var(--bg); }
.toc-expand.expanded { transform: rotate(180deg); }
.toc-subs { list-style: none; padding: 4px 0 10px; margin: 0; background: var(--bg); }
.toc-subs li { margin: 0; }
.toc-subs a {
  display: block; padding: 7px 16px 7px 28px; font-size: 13px;
  color: var(--text-soft); text-decoration: none;
  border-left: 2px solid transparent;
}
.toc-subs a:hover { color: var(--text); border-left-color: var(--accent); background: var(--bg-soft); }

#back-to-top {
  position: fixed; bottom: 24px; right: 24px; z-index: 40;
  width: 46px; height: 46px; border-radius: 50%; padding: 0;
  background: var(--accent); color: var(--back-to-top-text); border: none;
  font-size: 20px; cursor: pointer;
  box-shadow: 0 4px 14px var(--shadow-strong);
}
#back-to-top[hidden] { display: none; }
#resume-toast {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  z-index: 70; max-width: 92vw;
  background: var(--toast-bg); color: var(--toast-text);
  padding: 13px 18px; border-radius: 12px;
  display: flex; align-items: center; gap: 10px;
  font-size: 14px;
  box-shadow: 0 6px 22px var(--shadow-strong);
}
#resume-toast[hidden] { display: none; }
.resume-msg { flex: 1; line-height: 1.5; }
.resume-btn {
  background: rgba(255,255,255,0.14); color: #fff;
  border: 1px solid rgba(255,255,255,0.22);
  padding: 6px 12px; border-radius: 999px;
  font-size: 13px; cursor: pointer;
  font-family: var(--sans); white-space: nowrap;
}
.resume-btn.resume-yes { background: var(--accent); border-color: var(--accent); }

@media (max-width: 600px) {
  body { font-size: 18px; line-height: 1.85; }
  .book { padding: 28px 18px 64px; }
  .chapter { padding: 32px 22px 28px; margin: 22px 0; border-radius: 12px; }
  .chapter-title { font-size: 28px; line-height: 1.3; }
  .chapter-body { font-size: 18px; line-height: 1.85; }
  .chapter-body .subhead { font-size: 20px; }
  .chapter-body .subhead-2 { font-size: 16px; }
  .chapter-body blockquote.meta-note { font-size: 17.5px; }
  .toc ol { grid-template-columns: 1fr; }
  #menu-toggle { top: 12px; left: 12px; width: 40px; height: 40px; }
  #dark-toggle { top: 12px; right: 12px; width: 40px; height: 40px; font-size: 16px; }
  #download-btn { top: 12px; right: 60px; width: 40px; height: 40px; font-size: 16px; }
  #theme-switcher { top: 16px; right: 108px; padding: 5px 11px; font-size: 11px; }
  #series-switcher { top: 16px; right: 178px; padding: 5px 11px; font-size: 11px; }
  #download-menu { top: 60px; right: 12px; min-width: 180px; }
  #back-to-top { bottom: 16px; right: 16px; width: 40px; height: 40px; font-size: 17px; }
}

/* fetus-progress / 인포그래픽은 클래식과 같은 변수 그대로 사용 */
.illust { margin: 0; text-align: center; }
.illust img { max-width: 100%; height: auto; display: block; margin: 0 auto; }
.fetus-progress {
  display: flex; gap: 8px; align-items: stretch; justify-content: space-between;
  margin: 1.8em 0 1.4em; padding: 16px 10px 12px;
  background: var(--bg); border: 1px solid var(--line); border-radius: 14px;
}
.fetus-progress .stage {
  flex: 1; text-align: center;
  font-size: 11.5px; color: var(--text-soft);
  padding: 10px 4px 8px;
  border-radius: 10px;
  background: var(--bg-soft);
  display: flex; flex-direction: column; align-items: center;
  font-weight: 600;
}
.fetus-progress .stage:nth-child(7n+1) { background: rgba(184, 111, 92, 0.1); }
.fetus-progress .stage:nth-child(7n+2) { background: rgba(196, 157, 176, 0.13); }
.fetus-progress .stage:nth-child(7n+3) { background: rgba(143, 169, 133, 0.13); }
.fetus-progress .stage:nth-child(7n+4) { background: rgba(200, 163, 90, 0.13); }
.fetus-progress .stage:nth-child(7n+5) { background: rgba(156, 143, 176, 0.13); }
.fetus-progress .stage:nth-child(7n+6) { background: rgba(184, 111, 92, 0.1); }
.fetus-progress .stage:nth-child(7n+7) { background: rgba(143, 169, 133, 0.13); }
.fetus-progress .stage img { width: 100%; max-width: 64px; height: auto; margin: 0 auto 6px; display: block; }
@media (max-width: 600px) {
  .fetus-progress { gap: 4px; padding: 10px 6px 8px; }
  .fetus-progress .stage { padding: 7px 2px 6px; font-size: 10.5px; }
  .fetus-progress .stage img { max-width: 48px; }
}

.infographic { margin: 2em auto; color: var(--text); }
.infographic-caption { text-align: center; font-size: 12.5px; color: var(--text-soft); margin-top: 12px; }
.infographic-circle { position: relative; width: 360px; max-width: 90vw; aspect-ratio: 1/1; margin: 2em auto; }
.infographic-circle .ring {
  position: absolute; border: 1.5px solid var(--accent); border-radius: 50%;
  display: flex; align-items: flex-start; justify-content: center;
  font-size: 12.5px; color: var(--text-soft); padding-top: 7px; background: var(--ring-bg);
}
.infographic-circle .ring-society { width:100%; height:100%; left:0; top:0; }
.infographic-circle .ring-family  { width:78%;  height:78%;  left:11%; top:11%; }
.infographic-circle .ring-mother  { width:58%;  height:58%;  left:21%; top:21%; }
.infographic-circle .ring-uterus  { width:38%;  height:38%;  left:31%; top:31%; }
.infographic-circle .ring-fetus   {
  width:18%; height:18%; left:41%; top:41%;
  background: var(--accent); color: var(--bg-flow-to-text);
  align-items:center; padding-top:0; font-size:13px;
}
.infographic-timeline {
  display: flex; gap: 8px;
  border: 1px solid var(--line); border-radius: 10px; overflow: hidden;
}
.infographic-timeline .trimester {
  flex: 1; padding: 14px; background: var(--bg);
  border-right: 1px solid var(--line); font-size: 13px; line-height: 1.65;
}
.infographic-timeline .trimester:last-child { border-right: none; }
.infographic-timeline .t-label {
  font-weight: 700; color: var(--accent); margin-bottom: 6px;
  font-size: 12px; letter-spacing: 0.04em;
}
.infographic-cards { display: flex; flex-direction: column; gap: 10px; }
.infographic-cards .card-pair {
  display: grid; grid-template-columns: 1fr 32px 1fr;
  align-items: stretch; gap: 8px;
}
.infographic-cards .card {
  padding: 12px 14px; border: 1px solid var(--line); border-radius: 10px;
  font-size: 13px; line-height: 1.55;
}
.infographic-cards .card.sajudang { background: var(--bg); }
.infographic-cards .card.modern { background: var(--card-modern-bg); }
.infographic-cards .card-label {
  display: block; font-size: 10.5px; color: var(--accent);
  letter-spacing: 0.2em; margin-bottom: 4px; text-transform: uppercase;
  font-weight: 700;
}
.infographic-cards .card-arrow {
  display: flex; align-items: center; justify-content: center;
  color: var(--accent); font-size: 16px;
}
.infographic-flow {
  display: grid; grid-template-columns: 1fr 40px 1fr;
  align-items: center; gap: 10px;
}
.infographic-flow .flow-side {
  padding: 16px 18px; border-radius: 10px; text-align: center;
  font-size: 14px; line-height: 1.55;
}
.infographic-flow .flow-from {
  background: var(--bg-flow-from); border: 1px solid var(--line); color: var(--text-soft);
}
.infographic-flow .flow-to { background: var(--accent); color: var(--bg-flow-to-text); }
.infographic-flow .flow-arrow { text-align: center; font-size: 22px; color: var(--accent); }
.infographic-flow .flow-label {
  display: block; font-size: 11px; letter-spacing: 0.18em;
  margin-bottom: 4px; opacity: 0.75; text-transform: uppercase;
}
.infographic-flow small { display: block; font-size: 12px; margin-top: 6px; opacity: 0.85; }
.infographic-mandala {
  position: relative; width: 380px; max-width: 92vw;
  aspect-ratio: 1/1; margin: 2.4em auto;
}
.infographic-mandala .mandala-center {
  position: absolute; width: 38%; height: 38%; left: 31%; top: 31%;
  border-radius: 50%; background: var(--accent); color: var(--mandala-center-text);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; text-align: center; font-weight: 600; line-height: 1.4;
}
.infographic-mandala .mandala-petal {
  position: absolute; width: 31%; height: 31%; border-radius: 50%;
  border: 1.5px solid var(--accent); background: var(--bg-soft);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; color: var(--text); text-align: center;
  padding: 6px; line-height: 1.35;
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
  /* 인쇄/PDF: 다크모드 강제 라이트 — 다크 사용자도 깔끔한 PDF */
  :root.dark {
    --bg: #ffffff; --bg-soft: #ffffff;
    --text: #1a1612; --text-soft: #4a443f;
    --accent: #7a5e40; --accent-rose: #a87a8c;
    --accent-sage: #6e8669; --accent-mustard: #a48345;
    --accent-lavender: #7a6f8c;
    --line: #d9d0bf; --line-strong: #b8ad9a;
    --card-shadow: none; --card-shadow-hover: none;
    --bg-flow-from: #efeae0; --card-modern-bg: #ffffff;
    --ring-bg: rgba(255, 255, 255, 0.55);
  }

  body { background: white; font-size: 11pt; line-height: 1.75; }
  .book { max-width: 100%; padding: 0 16pt; }
  .book-cover { margin: 0 0 24pt; page-break-after: always; }
  .chapter, .cover, .front-page {
    box-shadow: none !important;
    border: none !important;
    page-break-inside: avoid;
    page-break-before: auto;
  }
  .chapter { page-break-before: always; padding: 12pt 0; margin: 0; }
  .toc { page-break-after: always; }

  /* 다운로드/메뉴/네비 chrome 모두 숨김 */
  #menu-toggle, #dark-toggle, #theme-switcher, #download-btn, #download-menu,
  #drawer, #drawer-backdrop, #back-to-top, #resume-toast {
    display: none !important;
  }

  .chapter-title { font-size: 22pt; }
  .chapter-body { font-size: 11pt; line-height: 1.75; }
  .chapter-body .subhead { font-size: 14pt; page-break-after: avoid; }
  table.data { font-size: 9pt; page-break-inside: avoid; }
  aside.footnotes { font-size: 9pt; page-break-inside: avoid; }
  a { color: inherit !important; text-decoration: none !important; border: none !important; background: transparent !important; }
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
<button id="download-btn" type="button" aria-label="다운로드" title="다운로드 (PDF/HTML)" aria-haspopup="true" aria-expanded="false">
  <span aria-hidden="true">📥</span>
</button>
<div id="download-menu" role="menu" aria-label="다운로드 옵션">
  <button type="button" id="dl-pdf" role="menuitem">
    <span class="dl-icon" aria-hidden="true">📄</span>
    <span class="dl-label">PDF로 저장<span class="dl-sub">브라우저 인쇄 → PDF로 저장</span></span>
  </button>
  <a id="dl-html" href="./book-modern.html" download="맘곁태교-이론편-모던.html" role="menuitem">
    <span class="dl-icon" aria-hidden="true">💾</span>
    <span class="dl-label">HTML 파일 받기<span class="dl-sub">오프라인 보관용 단일 파일</span></span>
  </a>
</div>
<a id="theme-switcher" href="./{{THEME_TARGET}}" title="{{THEME_LABEL}} 디자인으로 보기">{{THEME_LABEL}}</a>
<a id="series-switcher" href="./{{OTHER_BOOK_TARGET}}" title="시리즈 — {{OTHER_BOOK_LABEL}} 보기">📘 {{OTHER_BOOK_LABEL}}</a>

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
<section class="book-cover">
  <figure class="book-cover-art">
    <img src="./images/{{COVER_IMAGE}}" alt="{{COVER_IMAGE_ALT}}" onerror="this.closest('.book-cover').style.display='none'">
  </figure>
</section>

<header class="cover">
  <figure class="cover-logo illust"><img src="./images/logo.png" alt="맘곁 로고" onerror="this.closest('.cover-logo').style.display='none'"></figure>
  <h1>맘곁 태교</h1>
  <div class="sub">{{BOOK_SUBTITLE}}</div>
  <figure class="cover-hero illust"><img src="./images/cover-illustration.png" alt="맘곁 태교 표지 일러스트" onerror="this.closest('.cover-hero').style.display='none'"></figure>
  <div class="cover-tagline">{{BOOK_TAGLINE}}</div>
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
  var downloadBtn = document.getElementById('download-btn');
  var downloadMenu = document.getElementById('download-menu');
  var dlPdfBtn = document.getElementById('dl-pdf');
  var drawer = document.getElementById('drawer');
  var drawerClose = document.getElementById('drawer-close');
  var drawerBackdrop = document.getElementById('drawer-backdrop');
  var backToTop = document.getElementById('back-to-top');
  var resumeToast = document.getElementById('resume-toast');

  function setTheme(isDark) {
    document.documentElement.classList.toggle('dark', isDark);
    try { localStorage.setItem(THEME_KEY, isDark ? 'dark' : 'light'); } catch (e) {}
  }
  if (darkToggle) {
    darkToggle.addEventListener('click', function() {
      setTheme(!document.documentElement.classList.contains('dark'));
    });
  }

  // ---- Download menu ----
  function closeDlMenu() {
    if (!downloadMenu) return;
    downloadMenu.setAttribute('data-open', 'false');
    if (downloadBtn) downloadBtn.setAttribute('aria-expanded', 'false');
  }
  function openDlMenu() {
    if (!downloadMenu) return;
    downloadMenu.setAttribute('data-open', 'true');
    if (downloadBtn) downloadBtn.setAttribute('aria-expanded', 'true');
  }
  if (downloadBtn) {
    downloadBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      var open = downloadMenu && downloadMenu.getAttribute('data-open') === 'true';
      if (open) closeDlMenu(); else openDlMenu();
    });
  }
  if (dlPdfBtn) {
    dlPdfBtn.addEventListener('click', function() {
      closeDlMenu();
      // 인쇄 다이얼로그 → 사용자가 "PDF로 저장" 선택
      setTimeout(function() { window.print(); }, 120);
    });
  }
  if (downloadMenu) {
    downloadMenu.addEventListener('click', function(e) {
      // 항목 클릭 시 메뉴는 닫고 기본 동작은 유지
      if (e.target.closest('a, button')) closeDlMenu();
    });
  }
  document.addEventListener('click', function(e) {
    if (!downloadMenu) return;
    if (downloadMenu.getAttribute('data-open') !== 'true') return;
    if (e.target.closest('#download-btn, #download-menu')) return;
    closeDlMenu();
  });
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && downloadMenu && downloadMenu.getAttribute('data-open') === 'true') {
      closeDlMenu();
    }
  });
  if (window.matchMedia) {
    var mq = window.matchMedia('(prefers-color-scheme: dark)');
    var followSystem = function(e) {
      var saved; try { saved = localStorage.getItem(THEME_KEY); } catch (err) {}
      if (!saved) setTheme(e.matches);
    };
    if (mq.addEventListener) mq.addEventListener('change', followSystem);
    else if (mq.addListener) mq.addListener(followSystem);
  }

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
    if (e.key === 'Escape' && drawer.getAttribute('aria-hidden') === 'false') closeDrawer();
  });

  document.querySelectorAll('.toc-expand').forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.preventDefault(); e.stopPropagation();
      var target = document.getElementById(btn.getAttribute('data-target'));
      if (!target) return;
      var hidden = target.hasAttribute('hidden');
      if (hidden) {
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

  // body.overflow is locked while drawer is open, which blocks default
  // anchor scroll. Close drawer first, then scroll to target manually.
  document.querySelectorAll('.drawer-nav a[href^="#"]').forEach(function(a) {
    a.addEventListener('click', function(e) {
      var href = a.getAttribute('href');
      if (!href || href === '#') return;
      var target = document.getElementById(href.slice(1));
      if (!target) return;
      e.preventDefault();
      closeDrawer();
      requestAnimationFrame(function() {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        try { history.replaceState(null, '', href); } catch (err) {}
      });
    });
  });

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

  var sections = document.querySelectorAll('section.chapter');
  var currentSection = null;
  if ('IntersectionObserver' in window && sections.length) {
    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) currentSection = entry.target.id;
      });
      if (currentSection) {
        try { localStorage.setItem(STORAGE_KEY, currentSection); } catch (e) {}
      }
    }, { threshold: [0.2], rootMargin: '-80px 0px -55% 0px' });
    sections.forEach(function(s) { observer.observe(s); });
  }

  function showResumePrompt() {
    if (!resumeToast) return;
    var saved; try { saved = localStorage.getItem(STORAGE_KEY); } catch (e) { return; }
    if (!saved || saved === 'prologue') return;
    var target = document.getElementById(saved);
    if (!target) return;
    if (window.scrollY > 200) return;
    var titleEl = target.querySelector('.chapter-title');
    var numEl = target.querySelector('.chapter-num');
    var label = '';
    if (numEl) label += numEl.textContent.trim();
    if (titleEl) { if (label) label += ' '; label += titleEl.textContent.trim(); }
    var msgEl = resumeToast.querySelector('.resume-msg');
    if (msgEl && label) msgEl.textContent = '이전에 보시던 「' + label + '」에서 이어 볼까요?';
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

  // ---- Checklist (부록 B) — localStorage 동기화 + 진행률 ----
  function initChecklists() {
    var boards = document.querySelectorAll('.check-board');
    boards.forEach(function(board) {
      var key = 'momgyeot-checklist-' + (board.getAttribute('data-checklist') || 'default');
      var saved = {};
      try { saved = JSON.parse(localStorage.getItem(key) || '{}'); } catch (e) { saved = {}; }
      var inputs = board.querySelectorAll('input[type="checkbox"][data-key]');
      inputs.forEach(function(inp) {
        if (saved[inp.getAttribute('data-key')]) inp.checked = true;
        inp.addEventListener('change', function() {
          saved[inp.getAttribute('data-key')] = inp.checked;
          try { localStorage.setItem(key, JSON.stringify(saved)); } catch (e) {}
          updateProgress(inp.closest('.check-stage'));
        });
      });
      board.querySelectorAll('.check-stage').forEach(updateProgress);
      var resetBtn = board.querySelector('.check-reset');
      if (resetBtn) {
        resetBtn.addEventListener('click', function() {
          if (!confirm('전체 체크 상태를 초기화할까요?')) return;
          inputs.forEach(function(inp) { inp.checked = false; });
          try { localStorage.removeItem(key); } catch (e) {}
          board.querySelectorAll('.check-stage').forEach(updateProgress);
        });
      }
    });
  }
  function updateProgress(stage) {
    if (!stage) return;
    var inps = stage.querySelectorAll('input[type="checkbox"]');
    var total = inps.length;
    var done = 0;
    inps.forEach(function(i) { if (i.checked) done++; });
    var bar = stage.querySelector('.check-progress-bar');
    var txt = stage.querySelector('.check-progress-text');
    var pct = total > 0 ? Math.round((done / total) * 100) : 0;
    if (bar) bar.style.setProperty('--progress', pct + '%');
    if (txt) txt.textContent = done + ' / ' + total;
  }
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    initChecklists();
  } else {
    document.addEventListener('DOMContentLoaded', initChecklists);
  }
})();
</script>

</body>
</html>
"""


if __name__ == "__main__":
    build()
