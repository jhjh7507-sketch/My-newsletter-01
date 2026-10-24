---
name: adscore
description: >-
  Score an ad or reel out of 100 - hook, copy, CTA, offer, and real response
  from its numbers - so "what is weak" is a number, not a feeling. Use when
  the user shares an ad, a reel, a script or its insights and asks "점수 매겨줘",
  "뭐가 약해", "adscore", "평가해줘", "왜 안 터졌어", or before publishing a
  script, and for deciding which reel counts as viral.
---

# adscore

Two halves. **Creative** (60 points) is judged from the ad itself and works
before anything is posted. **Response** (40 points) comes only from real
numbers and is computed, never estimated.

## 1. Creative score (60)

Read the rubric in `rubric.json` and score each criterion against its anchors.
Quote the exact line you are scoring. One sentence of reason each.

| criterion | points | what earns full marks |
| --- | --- | --- |
| hook | 20 | first 1-3 s / first line stops a scroll: specific, tension, speaks to "you", payload up front |
| copy | 15 | one idea, concrete nouns, no filler, sounds like a person (`/ig-human` detect.py) |
| CTA | 10 | one ask, low friction, says what happens next |
| offer | 15 | clear value, a reason to act now, believable; organic reel: the "save/share" payoff |

For video, also check the first frame: is the hook on screen as text?

## 2. Response score (40)

Ask for whatever the user has (Instagram insights or Ads Manager) and run:

```bash
python3 .claude/skills/adscore/metrics.py --views 12000 --reach 9000 --likes 480 --comments 35 \
  --shares 60 --saves 210 --follows 18 --avg-watch 7.5 --length 30 --skip-rate 0.55
python3 .claude/skills/adscore/metrics.py --impressions 50000 --clicks 900 --spend 300000 \
  --purchases 24 --revenue 1440000 --thruplays 6000 --video-3s 15000
```

It prints each rate, its band and the response score. Missing inputs score
nothing and are listed, not guessed. Bands are rules of thumb for Korean
Instagram and Meta ads; say so when reporting.

## 3. Report

```
총점 71/100  (크리에이티브 46/60 · 반응 25/40)
가장 약한 것: CTA 4/10 - "자세히 보기"만 있고 다음에 뭐가 나오는지 없음
바로 고칠 것 3개: ...
```

Always end with three concrete fixes, rewritten lines included. For reels in
the strategy loop, a reel whose views beat the account's median by 3x or more
is the "viral" one to recycle (see `.claude/instagram/strategy.md`); record
the score in `.claude/instagram/log.md`.
