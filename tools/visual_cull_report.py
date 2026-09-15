#!/usr/bin/env python3
"""Build 推薦/可選/捨棄 HTML report from visual-labels.json. Originals never modified."""
from __future__ import annotations

import argparse
import csv
import html
import json
import shutil
from collections import defaultdict
from pathlib import Path

BUCKET_ZH = {"keep": "推薦入相簿", "maybe": "可選", "discard": "建議捨棄"}


def load_pixcull_scores(out: Path) -> dict[str, float]:
    path = out / "pixcull" / "scores.csv"
    scores: dict[str, float] = {}
    if not path.is_file():
        return scores
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            name = (row.get("filename") or Path(row.get("path", "")).name).strip()
            try:
                scores[name] = float(row.get("score_final") or 0)
            except ValueError:
                continue
    return scores


def load_metrics(out: Path) -> dict[str, dict]:
    path = out / "image-metrics.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {r["file"]: r for r in data.get("rows", []) if r.get("file")}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--skip-copy",
        action="store_true",
        help="Rebuild HTML/CSV only; do not recopy keepers/review originals.",
    )
    args = parser.parse_args()
    out = Path(args.output).expanduser().resolve()
    index = json.loads((out / "review-index.json").read_text(encoding="utf-8"))
    labels = json.loads((out / "visual-labels.json").read_text(encoding="utf-8"))
    source = Path(index["source"])
    title = args.title
    pix = load_pixcull_scores(out)
    metrics = load_metrics(out)

    by_file = {r["file"]: r for r in labels["rows"]}
    by_i = {r["i"]: r for r in labels["rows"] if "i" in r}
    rows = []
    for p in index["photos"]:
        lab = by_file.get(p["file"]) or by_i.get(p["i"])
        if not lab:
            lab = {"bucket": "discard", "caption": "未標", "note": "缺少視覺標籤"}
        fname = Path(p["file"]).name
        score = lab.get("score_final", pix.get(fname, pix.get(p["file"])))
        met = metrics.get(p["file"]) or metrics.get(fname) or {}
        rows.append(
            {
                **p,
                "bucket": lab["bucket"],
                "caption": lab.get("caption", ""),
                "note": lab.get("note", ""),
                "score_final": score if score not in (None, "") else "",
                "burst_id": lab.get("burst_id", ""),
                "burst_rank": lab.get("burst_rank", ""),
                "burst_size": lab.get("burst_size", ""),
                "exposure": lab.get("exposure", met.get("exposure", "")),
                "mean_luma": lab.get("mean_luma", met.get("mean_luma", "")),
                "people_group": lab.get("people_group", met.get("people_group", "")),
                "people_in_focus": lab.get("people_in_focus", met.get("people_in_focus", "")),
                "face_half_zh": lab.get("face_half_zh", met.get("face_half_zh", "")),
                "laplacian_subject": lab.get("laplacian_subject", met.get("laplacian_subject", "")),
                "shadow_score": lab.get("shadow_score", met.get("shadow_score", "")),
                "shadow_zh": lab.get("shadow_zh", met.get("shadow_zh", "")),
            }
        )

    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[r["bucket"]] += 1

    csv_path = out / "culling-report.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "file",
                "bucket",
                "caption",
                "note",
                "width",
                "height",
                "sharp",
                "score_final",
                "burst_id",
                "burst_rank",
                "burst_size",
                "exposure",
                "mean_luma",
                "people_group",
                "people_in_focus",
                "face_half_zh",
                "shadow_zh",
                "shadow_score",
            ],
        )
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    "file": r["file"],
                    "bucket": BUCKET_ZH.get(r["bucket"], r["bucket"]),
                    "caption": r["caption"],
                    "note": r["note"],
                    "width": r["width"],
                    "height": r["height"],
                    "sharp": r["sharp"],
                    "score_final": r.get("score_final", ""),
                    "burst_id": r.get("burst_id", ""),
                    "burst_rank": r.get("burst_rank", ""),
                    "burst_size": r.get("burst_size", ""),
                    "exposure": r.get("exposure", ""),
                    "mean_luma": r.get("mean_luma", ""),
                    "people_group": r.get("people_group", ""),
                    "people_in_focus": r.get("people_in_focus", ""),
                    "face_half_zh": r.get("face_half_zh", ""),
                    "shadow_zh": r.get("shadow_zh", ""),
                    "shadow_score": r.get("shadow_score", ""),
                }
            )

    def score_lines(r: dict) -> list[str]:
        lines = []
        exp = r.get("exposure") or ""
        luma = r.get("mean_luma")
        if exp:
            try:
                lines.append(f"曝光 {exp} · {float(luma):.0f}")
            except (TypeError, ValueError):
                lines.append(f"曝光 {exp}")
        people = r.get("people_group") or ""
        face = r.get("face_half_zh") or ""
        if people:
            bit = f"對焦 {people}"
            if face and face != "—":
                bit += f" · {face}"
            elif people == "無人":
                bit += " · 無五官"
            lines.append(bit)
        bid = r.get("burst_id")
        br = r.get("burst_rank")
        bs = r.get("burst_size")
        try:
            burst_n = int(bs)
        except (TypeError, ValueError):
            burst_n = 0
        if bid not in (None, "") and burst_n >= 2:
            if br not in (None, ""):
                lines.append(f"連拍組 #{bid} · {br}/{bs}")
            else:
                lines.append(f"連拍組 #{bid}")
        shd = r.get("shadow_zh") or ""
        ss = r.get("shadow_score")
        if shd or ss not in (None, ""):
            try:
                lines.append(f"黑影 {shd or '—'} · {float(ss):.0f}")
            except (TypeError, ValueError):
                lines.append(f"黑影 {shd or '—'}")
        bits = []
        sf = r.get("score_final")
        if sf not in (None, ""):
            try:
                bits.append(f"pix {float(sf):.3f}")
            except (TypeError, ValueError):
                bits.append(f"pix {sf}")
        if r.get("sharp") not in (None, ""):
            try:
                bits.append(f"sharp {float(r['sharp']):.0f}")
            except (TypeError, ValueError):
                pass
        if r.get("laplacian_subject") not in (None, ""):
            try:
                bits.append(f"主體 {float(r['laplacian_subject']):.0f}")
            except (TypeError, ValueError):
                pass
        if bits:
            lines.append(" · ".join(bits))
        return lines

    def discard_reason(r: dict) -> str:
        cap = (r.get("caption") or "").strip()
        note = (r.get("note") or "").strip()
        extras: list[str] = []
        if r.get("exposure") in ("過暗", "過曝"):
            extras.append(r["exposure"])
        if r.get("face_half_zh") == "五官不清":
            extras.append("五官不清")
        parts: list[str] = []
        if cap:
            parts.append(cap)
        if note and note not in cap:
            parts.append(note)
        for extra in extras:
            if extra not in cap and extra not in note:
                parts.append(extra)
        return " · ".join(parts) or "未標原因"

    def card_html(r: dict) -> str:
        src = html.escape(f"thumbs/{r['thumb']}")
        cap = html.escape(r["caption"])
        name = html.escape(Path(r["file"]).name)
        meta = "".join(f'<div class="score">{html.escape(s)}</div>' for s in score_lines(r))
        exp = html.escape(str(r.get("exposure") or ""))
        people = html.escape(str(r.get("people_group") or ""))
        face = html.escape(str(r.get("face_half_zh") or ""))
        shadow = html.escape(str(r.get("shadow_zh") or ""))
        reason_html = ""
        if r.get("bucket") == "discard":
            reason_html = (
                f'<div class="reason">原因：{html.escape(discard_reason(r))}</div>'
            )
        return (
            f'<article class="card" data-exp="{exp}" data-people="{people}" data-face="{face}" data-shadow="{shadow}">'
            f'<img src="{src}" loading="lazy" alt="{cap}">'
            f'<div class="cap">{cap}</div>'
            f"{reason_html}"
            f"{meta}"
            f'<div class="fn">{name}</div></article>'
        )

    def cards(bucket: str) -> str:
        selected = [r for r in rows if r["bucket"] == bucket]
        if bucket == "discard":
            selected.sort(
                key=lambda r: (
                    0 if r["caption"] == "動作重複" else 1,
                    r.get("burst_id") or 0,
                    r.get("burst_rank") or 99,
                )
            )
        parts = []
        last_burst = object()
        for r in selected:
            if bucket == "discard" and r["caption"] == "動作重複":
                bid = r.get("burst_id") or 0
                if bid != last_burst:
                    last_burst = bid
                    n = r.get("burst_size") or ""
                    parts.append(
                        f'<h3 class="burst">連拍組 #{bid} · {n} 張（組內比分）</h3>'
                    )
            elif last_burst is not object() and r["caption"] != "動作重複":
                last_burst = object()
            parts.append(card_html(r))
        return "\n".join(parts)

    doc = f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} · 選片</title>
  <style>
    :root {{ font-family: "Segoe UI", "Microsoft JhengHei", sans-serif; }}
    body {{ margin: 0; background: #f3eee6; color: #222; }}
    .bar {{ display: flex; align-items: center; justify-content: space-between;
            padding: 12px 20px; color: #fff; font-size: 20px; font-weight: 700; }}
    .bar.keep {{ background: #2e7d32; }}
    .bar.maybe {{ background: #8d6e4f; }}
    .bar.discard {{ background: #8b2e2e; }}
    .bar .count {{ font-size: 14px; font-weight: 500; opacity: .9; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px;
             padding: 16px 18px 28px; max-width: 1100px; margin: 0 auto; }}
    .card {{ background: #ece8e1; border: 1px solid #d5d0c8; }}
    .card img {{ width: 100%; aspect-ratio: 3/4; object-fit: contain; background: #ddd8d0; display: block; }}
    .cap {{ padding: 8px 10px 2px; font-size: 14px; color: #555; text-align: center; }}
    .reason {{ padding: 0 10px 4px; font-size: 13px; color: #8b2e2e; text-align: center; line-height: 1.35; }}
    .score {{ padding: 0 10px 2px; font-size: 12px; color: #3d6b8a; text-align: center; font-variant-numeric: tabular-nums; }}
    .fn {{ padding: 0 10px 10px; font-size: 11px; color: #888; text-align: center; }}
    .burst {{ grid-column: 1 / -1; margin: 8px 0 0; padding: 8px 10px; background: #e4dcd0;
             color: #5a5148; font-size: 14px; font-weight: 700; }}
    .intro {{ padding: 18px 20px 8px; max-width: 1100px; margin: 0 auto; color: #444; }}
    .intro h1 {{ margin: 0 0 8px; font-size: 22px; }}
    .filters {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0 4px; }}
    .filters button {{ border: 1px solid #c9c2b6; background: #fff; color: #444; padding: 4px 10px;
                       border-radius: 14px; cursor: pointer; font-size: 13px; }}
    .filters button.on {{ background: #3d6b8a; color: #fff; border-color: #3d6b8a; }}
    .card.hide, .burst.hide {{ display: none; }}
    nav {{ position: sticky; top: 0; z-index: 2; display: flex; gap: 0; }}
    nav a {{ flex: 1; text-align: center; padding: 10px; color: #fff; text-decoration: none; font-weight: 700; }}
    nav a.k {{ background: #2e7d32; }} nav a.m {{ background: #8d6e4f; }} nav a.d {{ background: #8b2e2e; }}
  </style>
</head>
<body>
  <nav>
    <a class="k" href="#keep">推薦入相簿 {counts['keep']}</a>
    <a class="m" href="#maybe">可選 {counts['maybe']}</a>
    <a class="d" href="#discard">建議捨棄 {counts['discard']}</a>
  </nav>
  <div class="intro">
    <h1>{html.escape(title)}</h1>
    <p>來源 {html.escape(str(source))} · 共 {len(rows)} 張 · 原檔未刪未移。
    推薦 {counts['keep']} · 可選 {counts['maybe']} · 捨棄 {counts['discard']}。
    每個連拍組內，五官清楚且曝光、銳利度可接受時最多留 5 張；看不見五官直接捨棄。
    若整場 keep 未滿 50 張，改為每組不論分數都留相對最好的 5 張。
    每張捨棄都會標<strong>原因</strong>。顯示曝光、對焦人數、五官、觀眾黑影、連拍組編號，以及 PixCull／銳利度。</p>
    <div class="filters" id="filters">
      <button type="button" data-key="all" class="on">全部</button>
      <button type="button" data-key="exp" data-val="過暗">過暗</button>
      <button type="button" data-key="exp" data-val="過曝">過曝</button>
      <button type="button" data-key="people" data-val="1人">1人</button>
      <button type="button" data-key="people" data-val="2-5人">2-5人</button>
      <button type="button" data-key="people" data-val="5人以上">5人以上</button>
      <button type="button" data-key="people" data-val="無人">無人</button>
      <button type="button" data-key="face" data-val="五官不清">五官不清</button>
      <button type="button" data-key="shadow" data-val="無黑影">無黑影</button>
      <button type="button" data-key="shadow" data-val="黑影擋住主角">黑影擋住主角</button>
    </div>
  </div>
  <section id="keep">
    <div class="bar keep"><span>推薦入相簿</span><span class="count">{counts['keep']} 張</span></div>
    <div class="grid">{cards('keep')}</div>
  </section>
  <section id="maybe">
    <div class="bar maybe"><span>可選（想要先入）</span><span class="count">{counts['maybe']} 張</span></div>
    <div class="grid">{cards('maybe')}</div>
  </section>
  <section id="discard">
    <div class="bar discard"><span>建議捨棄</span><span class="count">{counts['discard']} 張</span></div>
    <div class="grid">{cards('discard')}</div>
  </section>
  <script>
    const filters = document.getElementById('filters');
    if (filters) {{
      filters.addEventListener('click', (ev) => {{
        const btn = ev.target.closest('button');
        if (!btn) return;
        filters.querySelectorAll('button').forEach((b) => b.classList.remove('on'));
        btn.classList.add('on');
        const key = btn.dataset.key;
        const val = btn.dataset.val || '';
        document.querySelectorAll('article.card').forEach((card) => {{
          const show = key === 'all' || card.getAttribute('data-' + key) === val;
          card.classList.toggle('hide', !show);
        }});
        document.querySelectorAll('h3.burst').forEach((h) => {{
          h.classList.toggle('hide', key !== 'all');
        }});
      }});
    }}
  </script>
</body>
</html>
"""
    html_path = out / "culling-report.html"
    html_path.write_text(doc, encoding="utf-8")

    n = m = 0
    keepers = out / "keepers"
    review = out / "review"
    if not args.skip_copy:
        if keepers.exists():
            shutil.rmtree(keepers)
        keepers.mkdir(parents=True)
        for r in rows:
            if r["bucket"] != "keep":
                continue
            src = source / r["file"]
            if src.is_file():
                dest = keepers / Path(r["file"]).name
                shutil.copy2(src, dest)
                n += 1

        if review.exists():
            shutil.rmtree(review)
        review.mkdir(parents=True)
        for r in rows:
            if r["bucket"] != "maybe":
                continue
            src = source / r["file"]
            if src.is_file():
                dest = review / Path(r["file"]).name
                shutil.copy2(src, dest)
                m += 1

    print(f"HTML {html_path}")
    print(f"CSV  {csv_path}")
    if args.skip_copy:
        print("skipped keepers/review recopy")
    else:
        print(f"keepers copied {n} → {keepers}")
        print(f"review copied {m} → {review}")
    print(f"keep {counts['keep']} · maybe {counts['maybe']} · discard {counts['discard']}")


if __name__ == "__main__":
    main()
