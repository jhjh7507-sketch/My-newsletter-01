---
name: bulkcreative
description: >-
  Write 20 on-brand ad and post copies at once from a brand guideline and tone
  & manner - hooks, primary text, headlines and CTAs across five angles, each
  checked for AI tells and scored. Use when the user gives a brand guide, tone
  doc or product brief and asks for "카피 20개", "광고 문구", "bulk copy",
  "variations", "카피 뽑아줘", or needs ad copy for a campaign or sponsorship.
---

# bulkcreative

Twenty copies, five angles, one brand voice. Fast enough to replace a first
round from an agency, honest enough to say which ones are weak.

## 1. Load the brand

Brands live in `.claude/brands/<slug>/`:

- `guide.md`: who it is for, what it sells, the promise, words it uses and
  never uses, tone (with one example sentence for each tone rule), legal
  must-nots (claims it cannot make, required disclaimers).
- `offers.md`: current products, prices, promos, end dates.

If the user hands over a new guide (pasted text, PDF, image, link), write it
into this shape first and show the user the summary. Ask only for what is
missing and blocks writing: the product, the audience, the offer. Never invent
a price, a discount, a review or a statistic.

## 2. Brief

Settle before writing (defaults in brackets):

| field | example |
| --- | --- |
| product / offer | 경량 러닝 재킷, 첫 구매 15% |
| channel | Instagram feed ad [Meta: primary text, headline, CTA button] |
| goal | purchase [or traffic, leads, followers, sponsor post] |
| audience | 20-30대 출퇴근 러너 |
| must say / must not say | from guide.md |

## 3. Write 20

Five angles x four copies. Angles (swap one if the brand guide rules it out):

1. **문제 공감**: the pain before the product.
2. **결과·변화**: the after state, concrete.
3. **증거**: specs, materials, numbers the brand actually published.
4. **비교·반전**: a belief the audience holds, turned.
5. **오퍼·긴급**: the promo and its real end date.

Each copy:

```
#07 [증거] 
훅 (첫 줄, 피드에서 잘리기 전 40자 이내):
본문 (primary text, 125자 이내 권장):
헤드라인 (40자 이내):
CTA 버튼: 지금 구매하기 | 자세히 알아보기 | ...
```

Vary hook formulas inside each angle (question, number, contrast, "~하는
사람 특징", direct address). No two copies may open with the same first three
words.

## 4. Check

- Run every copy through `/ig-human` (`detect.py`), strip em dashes, slop
  words and invisible characters. Korean scoring is rough; read it, do not
  trust it blindly.
- Score each copy with the `/adscore` rubric (hook, copy, CTA, offer; no
  performance data yet, so that part is blank). Mark the top 5.
- Re-check every claim against guide.md and offers.md.

## 5. Deliver

Save to `output/copy/<slug>-YYYY-MM-DD.md` (git-ignored) with a table up top:
#, angle, hook, score. Show the top 5 in chat, link the file for the rest.
Offer to turn the top hooks into reels with `/reels-make`.
