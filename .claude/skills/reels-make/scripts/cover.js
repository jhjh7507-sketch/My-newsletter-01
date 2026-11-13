// Center-account reel cover: the frame on top, darkening to black from the middle down,
// a small white line and a big yellow line in the 3:4 grid window (2026-11-13 template).
//   node cover.js frame.jpg "다이어트 중이시면" "식단 하지 마세요" out.jpg
// Needs the pre-installed Playwright (NODE_PATH=$(npm root -g)). Output 1080x1920 JPEG.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
const [bg, small, big, out] = process.argv.slice(2);
if (!out) { console.error('usage: node cover.js frame.jpg "small line" "big line" out.jpg'); process.exit(1); }
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
// Measured from the user's reference cover (460x605 grid crop): text at 49% and 62% of the
// 3:4 window (y 240-1680), headline about 91% of the width, yellow #f7d45e, shade from 33% down.
const html = `<!doctype html><html lang="ko"><head><meta charset="utf-8">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css">
<style>*{margin:0;padding:0;box-sizing:border-box}html,body{width:1080px;height:1920px;overflow:hidden;background:#000}
.bg{position:absolute;inset:0;background:url("file://${path.resolve(bg)}") center/cover no-repeat}
.shade{position:absolute;inset:0;background:linear-gradient(to bottom,rgba(0,0,0,0) 715px,rgba(0,0,0,.32) 816px,rgba(0,0,0,.5) 888px,rgba(0,0,0,.68) 960px,rgba(0,0,0,.92) 1032px,rgba(0,0,0,.94) 1920px)}
.t{position:absolute;left:0;right:0;text-align:center;font-family:Pretendard,sans-serif;white-space:nowrap;transform:translateY(-50%)}
.s{top:946px;font-size:58px;font-weight:700;color:#fff;letter-spacing:-.02em}
.b{top:1131px;font-size:150px;font-weight:900;color:#f7d45e;letter-spacing:-.045em}</style></head>
<body><div class="bg"></div><div class="shade"></div><div class="t s">${esc(small)}</div><div class="t b"><span>${esc(big)}</span></div></body></html>`;
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  const tmp = path.resolve(out + '.html'); fs.writeFileSync(tmp, html);
  await p.goto('file://' + tmp); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(500);
  const fsz = await p.evaluate(() => { const el = document.querySelector('.b'), sp = el.querySelector('span'); let f = 150;
    while (sp.getBoundingClientRect().width > 983 && f > 60) { f -= 2; el.style.fontSize = f + 'px'; } return f; });
  await p.screenshot({ path: out, type: 'jpeg', quality: 92 }); fs.unlinkSync(tmp); await b.close();
  console.log(`${out}: headline ${fsz}px`);
})();
