#!/usr/bin/env python3
"""실천편 마크다운 정돈 — CHAPTER 라벨/10선/잡티 제거 후 카드 UI로.

이 스크립트는 docs/practice/*.md 를 일괄 처리한다. 변환기(_convert_practice.py)
이후 한 번 더 실행해야 하는 클린업 패스.
"""
import re
from pathlib import Path

TARGETS = [
    Path("docs/practice/part2.md"),
    Path("docs/practice/part3.md"),
    Path("docs/practice/part4.md"),
    Path("docs/practice/part5.md"),
]


def wrap_chapter_end_script(text: str) -> str:
    """`CHAPTER N 태담[...]` + 다음 5줄 정도의 스크립트 → :::raw card."""
    pattern = re.compile(
        r"^(?:💬\s*)?CHAPTER\s+(\d+)\s+태담\s*(?:\(([^)]+)\))?\s*$\n"
        r"((?:^[^#\n].*\n){1,12}?)"  # 본문 라인 (헤딩이 아닌 줄들)
        r"(?=^\s*$|^#|\Z)",  # 빈 줄 / 다음 헤딩까지
        re.MULTILINE,
    )

    def repl(m):
        num = m.group(1)
        suffix = m.group(2) or ""
        body = m.group(3).strip()
        # script body lines preserved as <br>로 연결된 1개 단락
        body_html = body.replace("\n", " ").strip()
        title_extra = f' <span class="cend-extra">({suffix})</span>' if suffix else ""
        return (
            "\n:::raw\n"
            '<aside class="chapter-end-script" aria-label="장 끝 태담">\n'
            f'  <header class="cend-head"><span class="cend-tag">CHAPTER {num} · 태담</span>{title_extra}</header>\n'
            f'  <blockquote class="cend-body">{body_html}</blockquote>\n'
            "</aside>\n:::\n\n"
        )

    return pattern.sub(repl, text)


def drop_ch4_marker(text: str) -> str:
    """`CHAPTER 4 ⭐` 단독 라벨은 다음 ## 헤더 직전 시각 구분으로 변환되거나 제거.

    원본은 "CHAPTER 4 ⭐\n## 초기 태담 펼쳐보기 ..." 형태. 그냥 라벨만 제거하고
    바로 다음 ## 가 절을 자연스럽게 시작하게 한다.
    """
    return re.sub(r"^CHAPTER\s+4\s*⭐\s*$\n?", "", text, flags=re.MULTILINE)


def convert_10_situations(text: str) -> str:
    """`### 🌱 ... 상황별 태담 10선` 다음의 `01 ... \n 본문`을 카드 그리드로.

    형태:
        ### 🌱 ... 상황별 태담 10선
        01 라벨1
        본문 라인 ...
        02 라벨2
        본문 라인 ...
    """
    # 10선 헤더부터 다음 ##/### 까지 블록을 찾음
    block_pattern = re.compile(
        r"^(### 🌱?\s*[^\n]*상황별 태담\s*10선[^\n]*)$\n"  # 헤더
        r"(.*?)"
        r"(?=^##\s|^###\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )

    def repl(m):
        header = m.group(1)
        body = m.group(2)
        # 본문에서 "01 LABEL\n본문...\n02 LABEL\n본문..." 패턴 추출
        item_pattern = re.compile(
            r"^(\d{2})\s+([^\n]+)$\n((?:(?!^\d{2}\s).)*)",
            re.MULTILINE | re.DOTALL,
        )
        items = []
        for im in item_pattern.finditer(body):
            num = im.group(1)
            label = im.group(2).strip()
            content = im.group(3).strip()
            content_html = "<br>".join(
                line.strip() for line in content.split("\n") if line.strip()
            )
            items.append((num, label, content_html))

        if len(items) < 3:
            return m.group(0)  # 조건 미충족 시 원본 유지

        cards_html = "\n".join(
            f'  <article class="situ-card">\n'
            f'    <header class="situ-card-head">\n'
            f'      <span class="situ-num">{n}</span>\n'
            f'      <h5 class="situ-card-title">{l}</h5>\n'
            f'    </header>\n'
            f'    <blockquote class="situ-card-body">{c}</blockquote>\n'
            f"  </article>"
            for n, l, c in items
        )
        return (
            f"{header}\n\n"
            ":::raw\n"
            '<div class="situ-grid" aria-label="상황별 태담 10선">\n'
            f"{cards_html}\n"
            "</div>\n"
            ":::\n"
        )

    return block_pattern.sub(repl, text)


def main():
    base = Path(__file__).parent
    for rel in TARGETS:
        path = base / rel
        if not path.exists():
            print(f"skip: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        original = text

        text = drop_ch4_marker(text)
        text = wrap_chapter_end_script(text)
        text = convert_10_situations(text)

        if text != original:
            path.write_text(text, encoding="utf-8")
            print(f"polished {path}")
        else:
            print(f"unchanged {path}")


if __name__ == "__main__":
    main()
