---
name: spy
description: >-
  Pull a competitor's running ads - which creatives, since when, how long,
  which format - and break down their hooks, CTAs and offers into a swipe
  table. Use when the user names a brand and says "경쟁사 광고", "spy",
  "무슨 광고 돌려", "ad library", "what ads are they running", or wants
  hooks to borrow for ads or reels.
---

# spy

Public ad transparency data only. Never log in to anything, never scrape
Meta or Instagram directly.

## Sources, in order

All through the firecrawl MCP (`firecrawl_scrape` with an `alexandria` body).
Discovery with `firecrawl_find_tools` is free; executions cost credits, so say
roughly what a run will cost before a big one.

| source | covers | cost (firecrawl credits) | notes |
| --- | --- | --- | --- |
| `upspring` `advertisers/search` → `ads/browse` | Meta (Facebook/Instagram) ads, with hook text, archetype, delivery strength | 50 per non-empty page | Mostly US/global DTC brands. Empty result costs nothing. Try first. |
| `adstransparency-google-com` `ad-transparency/suggest` → `list_ads` → `get_ad` | Google / YouTube ads | 5 per call | Korean brands are here. Use `region: "KR"`. |
| User screen recordings of the Meta Ad Library (facebook.com/ads/library, public, no login) | Meta ads Upspring lacks | 0 | Ask for these when the brand is Korean and Instagram matters. Analyse with `/reels-style` measure.py. |

Google specifics learned the hard way:

- `suggest` can return several advertiser accounts for one brand (the brand
  itself and its media agencies). List ads from each.
- `start_date` does not reliably filter; filter by `last_shown_at` yourself.
  An ad last shown within ~2 days of today is running now.
- Large results come back "retained": follow `nextTool` and query them with
  the firecrawl `bash` capability and `jq`, small slices only.
- IMAGE ads: `preview.image_url` on `tpc.googlesyndication.com`. Download it
  with curl and read the image yourself (needs that host in the network
  allowlist). Firecrawl's own image text extraction garbles Korean.
- VIDEO ads: the preview is a JavaScript render with no readable text or
  video id. Report them as counts and dates, and ask the user for screen
  recordings of the ones that matter.

## Output

Write `.claude/brands/<slug>/spy-YYYY-MM-DD.md`:

1. Summary: accounts found, ads running now, formats, campaign waves (group by
   `first_shown_at`), longest-running creatives (days shown is the best public
   proxy for "this one works").
2. Table: format | first shown | last shown | days | hook | CTA | offer | link.
   Hook/CTA/offer only where actually read; never guess them from the brand.
3. Patterns: which hook formulas and offers repeat, what is new this wave.
4. Steal list: 5 hooks re-written for the user's account (formula only, new
   words), ready for `/ig-reel` or `/bulkcreative`.

Offer to commit the file. Note what each source could not show.
