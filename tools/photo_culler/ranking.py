"""Similar-group de-dupe and Keep / Review / Reject labeling."""

from __future__ import annotations

from .scoring import hamming


def group_similar(rows: list[dict], threshold: int) -> list[list[dict]]:
    groups: list[list[dict]] = []
    used: set[int] = set()
    for i, row in enumerate(rows):
        if i in used:
            continue
        group = [row]
        used.add(i)
        for j in range(i + 1, len(rows)):
            if j in used:
                continue
            if hamming(row["dhash"], rows[j]["dhash"]) <= threshold:
                group.append(rows[j])
                used.add(j)
        groups.append(group)
    return groups


def label_rows(
    rows: list[dict],
    similar_threshold: int,
    review_percent: float,
    max_keepers: int = 0,
) -> list[dict]:
    """
    Label rows as keeper / review / reject.

    Default max_keepers=0 means no hard top-N cap — volume comes from scores.
    """
    if not rows:
        return []

    sharp_values = sorted(r["sharpness"] for r in rows)
    blur_cutoff = sharp_values[max(0, int(len(sharp_values) * 0.15) - 1)]
    median_sharp = sharp_values[len(sharp_values) // 2]

    groups = group_similar(rows, similar_threshold)
    labeled: list[dict] = []

    for group in groups:
        ranked = sorted(group, key=lambda r: r["score"], reverse=True)
        best = ranked[0]
        for idx, row in enumerate(ranked):
            item = dict(row)
            item["group_size"] = len(group)

            very_blurry = row["sharpness"] < max(median_sharp * 0.12, 1e-6)
            is_blurry = very_blurry or (
                row["sharpness"] <= blur_cutoff
                and row["sharpness"] < max(best["sharpness"] * 0.55, 1e-6)
            )

            severe_occlusion = row.get("occlusion_penalty", 0) >= 12
            no_subject = not row.get("has_subject", False) and row.get("person_count", 0) == 0

            if is_blurry and (very_blurry or len(group) == 1 or idx > 0 or row["score"] < 35):
                item["suggestion"] = "reject"
                item["reason"] = "likely blurry vs batch"
            elif severe_occlusion and (idx > 0 or row["score"] < best["score"] * 0.9):
                item["suggestion"] = "reject"
                item["reason"] = row.get("occlusion_reason", "severe audience occlusion")
            elif no_subject and row["score"] < 40:
                item["suggestion"] = "reject"
                item["reason"] = "no usable subject"
            elif idx == 0:
                item["suggestion"] = "keeper"
                if row.get("has_subject"):
                    item["reason"] = "usable subject (pose)"
                elif len(group) > 1:
                    item["reason"] = "best in similar group"
                else:
                    item["reason"] = "strong technical score"
            elif best["score"] - row["score"] >= 6 or row["score"] < best["score"] * 0.85:
                item["suggestion"] = "reject"
                item["reason"] = "weaker duplicate or low score"
            else:
                item["suggestion"] = "review"
                item["reason"] = "similar alternative"
            labeled.append(item)

    # Promote clear subject shots that were not blur/occlusion rejected
    for row in labeled:
        if row["suggestion"] == "reject":
            continue
        if row.get("has_subject") and row["suggestion"] != "keeper":
            if row.get("occlusion_penalty", 0) < 12:
                row["suggestion"] = "keeper"
                row["reason"] = "usable subject (pose)"

    # Soft demotion when no hard max-keepers cap:
    # demote the bottom review_percent of keepers (by score) to review.
    keepers = [r for r in labeled if r["suggestion"] == "keeper"]
    if not max_keepers and keepers and review_percent > 0 and len(keepers) > 1:
        ranked_scores = sorted((r["score"] for r in keepers), reverse=True)
        keep_n = max(1, int(round(len(ranked_scores) * (1 - review_percent))))
        keep_cutoff = ranked_scores[keep_n - 1]
        for row in labeled:
            if row["suggestion"] == "keeper" and row["score"] < keep_cutoff:
                row["suggestion"] = "review"
                row["reason"] = f"below top {int((1 - review_percent) * 100)}% score cutoff"
            elif (
                row["suggestion"] == "keeper"
                and row["score"] == keep_cutoff
                and row["group_size"] == 1
                and not row.get("has_subject")
            ):
                row["suggestion"] = "review"
                row["reason"] = "borderline solo shot"

    # Optional hard top-N (off by default)
    if max_keepers and max_keepers > 0:
        ranked_keepers = sorted(
            [r for r in labeled if r["suggestion"] == "keeper"],
            key=lambda r: (1 if r.get("has_subject") else 0, r["score"]),
            reverse=True,
        )
        keep_set = {id(r) for r in ranked_keepers[:max_keepers]}
        for row in labeled:
            if row["suggestion"] == "keeper" and id(row) not in keep_set:
                row["suggestion"] = "review"
                row["reason"] = f"outside top {max_keepers} keepers"

    labeled.sort(
        key=lambda r: (
            -{"keeper": 2, "review": 1, "reject": 0}[r["suggestion"]],
            -(1 if r.get("has_subject") else 0),
            -r["score"],
        )
    )
    return labeled
