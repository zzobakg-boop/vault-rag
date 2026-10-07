#!/usr/bin/env python3
"""학습지 HTML 캡처 — 편집 전후를 같은 조건으로 찍는다 (2026-10-07 메인·역사·사회 합의).

    python3 ws_shot.py <개념편.html> [--out DIR] [--tag before|after] [--sel "CSS 선택자"] [--widths 390,1100]

- 폭마다 전체 페이지 한 장(<이름>_<tag>_<폭>.png). --sel 을 주면 그 요소들만 따로 찍는다.
- 함정 둘을 기본 처리한다(worksheet-publish §측정 함정):
  ① loading=lazy 그림은 화면 밖에서 0×0 → eager로 바꾸고 끝까지 스크롤한 뒤 찍는다.
  ② SVG에는 hidden 속성이 안 듣는다 → 이 스크립트는 숨김을 바꾸지 않는다. 보이는지 판정은 getComputedStyle로.
"""
import argparse, pathlib, sys
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("html")
ap.add_argument("--out", default="/tmp/ws_shot")
ap.add_argument("--tag", default="now")
ap.add_argument("--sel", default="")
ap.add_argument("--widths", default="390,1100")
a = ap.parse_args()

src = pathlib.Path(a.html).resolve()
if not src.exists():
    sys.exit(f"없음: {src}")
out = pathlib.Path(a.out)
out.mkdir(parents=True, exist_ok=True)
stem = src.stem[:40]

with sync_playwright() as p:
    b = p.chromium.launch()
    for w in [int(x) for x in a.widths.split(",")]:
        pg = b.new_page(viewport={"width": w, "height": 900}, device_scale_factor=2 if w <= 500 else 1)
        pg.goto(src.as_uri(), wait_until="load")
        pg.evaluate("""() => { document.querySelectorAll('img[loading=lazy]').forEach(i => i.loading = 'eager'); }""")
        pg.evaluate("""async () => { for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); } window.scrollTo(0, 0); }""")
        pg.wait_for_load_state("networkidle")
        f = out / f"{stem}_{a.tag}_{w}.png"
        pg.screenshot(path=str(f), full_page=True)
        print(f)
        if a.sel:
            for i, el in enumerate(pg.query_selector_all(a.sel)):
                el.scroll_into_view_if_needed()
                g = out / f"{stem}_{a.tag}_{w}_sel{i}.png"
                el.screenshot(path=str(g))
                print(g)
        pg.close()
    b.close()
