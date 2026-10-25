---
name: watch
description: >-
  Watch a video the way a person would - turn it into timed frames plus a
  word-timed transcript, then read both together. Use when the user sends a
  screen recording, a video file, a Google Drive video or a reel link and says
  "봐줘", "이 영상 분석해줘", "watch this", "와치", or when /reels-style,
  /ig-viral or /adscore need to know what happens in a reel second by second.
---

# watch

Claude cannot play a video. It can read pictures and text. So a video becomes
a picture book: one frame per scene change (at least one a second), each
stamped with its time, and the words spoken between that frame and the next.

## Getting the video

| What the user sends | How to get it |
|---|---|
| A file attached in chat | It is already under `/root/.claude/uploads/...` |
| A Google Drive file or folder | Download it with the Google Drive connector |
| An Instagram reel link | Instagram is blocked from the cloud session. Look the reel up in Firecrawl's Oriane index (`instagram/post-lookup`, `projection: "full"`, 40 credits) for its transcript and frames. If it is not indexed, ask for a screen recording |

## Run it

```
python3 .claude/skills/watch/watch.py <video> --out <scratchpad>/watch/<name>
```

- `--every 1.0` max seconds between frames. Raise it for videos over 2 minutes.
- `--scene 0.3` scene-change threshold. Lower gives more frames.
- `--no-stt` skip the transcript.

Output in `--out`: `frames/`, `sheet_01.jpg ...` (12 stamped frames per sheet),
`words.json`, `timeline.md`.

The transcript uses ElevenLabs Speech to Text with `ELEVENLABS_API_KEY`. If
the key lacks the Speech to Text permission the script still writes frames and
says the transcript was skipped. Tell the user once that the permission is off
and that on-screen captions in the frames are the fallback.

## Read it

Read every sheet with the Read tool, then `timeline.md`. Describe the video by
time: what is on screen, what is said, when the scene or caption changes. For
a reference reel pull out the hook (first 3 seconds, on screen and spoken),
the beat changes, caption position and length, and the ending ask.

Screen recordings include the phone UI. Ignore the status bar, the account
row and the caption under the video unless the user asks about them.
