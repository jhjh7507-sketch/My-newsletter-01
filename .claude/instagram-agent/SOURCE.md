Source: https://github.com/Jakeschincariol/instagram-agent-skill
Commit: d03c56bb598be770c60b201f94237e5d1a4268a6 (MIT, see LICENSE)

Skills live in ../skills/ig-*. voice.template.md is the voice profile template;
the skills read and write .claude/instagram/ at the repo root (voice.md,
swipe.md, plan.md, log.md). Changed from upstream ~/.claude/instagram/ so the
files persist in git across cloud sessions; commit them after a skill writes.
