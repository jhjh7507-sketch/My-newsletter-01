#!/usr/bin/env python3
"""Response score (out of 40) from real reel or ad numbers.

Organic reel (Instagram insights):
  python3 metrics.py --views 12000 --reach 9000 --likes 480 --comments 35 --shares 60 \
    --saves 210 --follows 18 --avg-watch 7.5 --length 30 [--skip-rate 0.55]
Paid ad (Meta Ads Manager):
  python3 metrics.py --impressions 50000 --clicks 900 --spend 300000 --purchases 24 \
    --revenue 1440000 --video-3s 15000 --thruplays 6000

Bands are rules of thumb, not platform benchmarks. Metrics without inputs are
listed as missing and excluded; the score is scaled over what was measured.
"""
import argparse

# name: (weight, low/ok/good thresholds, higher_is_better, unit)
BANDS = {
    "engagement_rate": (8, (0.03, 0.06, 0.10), True, "%"),
    "save_rate": (7, (0.005, 0.01, 0.03), True, "%"),
    "share_rate": (7, (0.004, 0.01, 0.02), True, "%"),
    "completion": (8, (0.30, 0.50, 0.70), True, "%"),
    "skip_rate": (4, (0.70, 0.50, 0.35), False, "%"),
    "follows_per_1k": (6, (1.0, 2.0, 5.0), True, ""),
    "ctr": (8, (0.008, 0.015, 0.025), True, "%"),
    "hook_rate": (8, (0.20, 0.30, 0.40), True, "%"),
    "hold_rate": (6, (0.25, 0.40, 0.55), True, "%"),
    "cvr": (6, (0.01, 0.025, 0.05), True, "%"),
    "roas": (8, (1.5, 2.5, 4.0), True, "x"),
}
LABELS = ["낮음", "보통", "좋음", "매우 좋음"]


def band(value, th, higher):
    lo, ok, good = th
    if higher:
        return 0 if value < lo else 1 if value < ok else 2 if value < good else 3
    return 0 if value > lo else 1 if value > ok else 2 if value > good else 3


def div(a, b):
    return a / b if a is not None and b else None


def main():
    ap = argparse.ArgumentParser()
    for f in ("views", "reach", "likes", "comments", "shares", "saves", "follows", "avg-watch",
              "length", "skip-rate", "impressions", "clicks", "spend", "purchases", "revenue",
              "video-3s", "thruplays"):
        ap.add_argument("--" + f, type=float)
    a = ap.parse_args()

    eng = None
    if a.reach and None not in (a.likes, a.comments, a.shares, a.saves):
        eng = (a.likes + a.comments + a.shares + a.saves) / a.reach
    m = {
        "engagement_rate": eng,
        "save_rate": div(a.saves, a.reach),
        "share_rate": div(a.shares, a.reach),
        "completion": div(a.avg_watch, a.length),
        "skip_rate": a.skip_rate,
        "follows_per_1k": div(a.follows * 1000 if a.follows is not None else None, a.reach),
        "ctr": div(a.clicks, a.impressions),
        "hook_rate": div(a.video_3s, a.impressions),
        "hold_rate": div(a.thruplays, a.video_3s),
        "cvr": div(a.purchases, a.clicks),
        "roas": div(a.revenue, a.spend),
    }
    got, total_w, missing = 0.0, 0.0, []
    print(f"{'지표':<16}{'값':>10}  등급")
    for k, (w, th, hi, unit) in BANDS.items():
        v = m[k]
        if v is None:
            missing.append(k)
            continue
        b = band(v, th, hi)
        got += w * (b + 1) / 4
        total_w += w
        shown = f"{v * 100:.2f}%" if unit == "%" else f"{v:.2f}{unit}"
        print(f"{k:<16}{shown:>10}  {LABELS[b]}")
    if a.spend and a.purchases:
        print(f"{'cpa':<16}{a.spend / a.purchases:>10,.0f}  (참고)")
    if a.views and a.reach:
        print(f"{'views/reach':<16}{a.views / a.reach:>10.2f}  (재시청·공유 유입 신호)")
    score = round(40 * got / total_w) if total_w else None
    print(f"\n반응 점수: {score}/40" if score is not None else "\n반응 점수: 입력된 숫자가 없음")
    if missing:
        print("측정 안 됨: " + ", ".join(missing))


if __name__ == "__main__":
    main()
