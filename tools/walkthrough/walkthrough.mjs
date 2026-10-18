// Records a captioned walkthrough of Mac Disk Cleaner against a demo home folder.
// Usage: node walkthrough.mjs http://127.0.0.1:8820/ out-dir
import { chromium } from "playwright";
import fs from "fs";

// Narration clip lengths (seconds), produced by `say` before recording.
const DUR = JSON.parse(fs.readFileSync(new URL("./vo/durations.json", import.meta.url)));
const timeline = [];
let t0 = 0, pending = null;

const [url, outDir] = process.argv.slice(2);
const W = 1440, H = 900;

const browser = await chromium.launch({ channel: "chrome", headless: true });
const context = await browser.newContext({
  viewport: { width: W, height: H },
  deviceScaleFactor: 1,
  colorScheme: "light",
  recordVideo: { dir: outDir, size: { width: W, height: H } },
});
const page = await context.newPage();
t0 = Date.now();
const wait = ms => page.waitForTimeout(ms);

// Overlay: a visible cursor (headless video has none) and a caption pill.
const overlay = () => page.evaluate(() => {
  if (document.getElementById("__cursor")) return;
  const style = document.createElement("style");
  style.textContent = `
    #__cursor { position: fixed; z-index: 99999; width: 22px; height: 22px; margin: -3px 0 0 -3px; pointer-events: none;
      transition: transform .08s; filter: drop-shadow(0 2px 3px rgba(0,0,0,.35)); }
    #__cursor.down { transform: scale(.85); }
    #__ring { position: fixed; z-index: 99998; width: 44px; height: 44px; margin: -22px 0 0 -22px; border-radius: 50%;
      border: 3px solid #3e8ef7; pointer-events: none; opacity: 0; }
    #__ring.go { animation: __ring .5s ease-out; }
    @keyframes __ring { from { opacity: .9; transform: scale(.4); } to { opacity: 0; transform: scale(1.4); } }
    #__cap { position: fixed; z-index: 99997; left: 50%; bottom: 104px; transform: translate(-50%, 16px); opacity: 0;
      background: rgba(20,33,43,.94); color: #fff; font: 600 22px/1.35 "Mona Sans", -apple-system, sans-serif; font-stretch: 105%;
      padding: 16px 28px; border-radius: 16px; box-shadow: 0 16px 40px rgba(0,0,0,.3); max-width: 1000px; text-align: center;
      transition: opacity .35s, transform .35s; pointer-events: none; }
    #__cap.on { opacity: 1; transform: translate(-50%, 0); }
    #__cap small { display: block; font-weight: 500; font-size: 16px; opacity: .75; margin-top: 4px; }`;
  document.head.appendChild(style);
  const c = document.createElement("div");
  c.id = "__cursor";
  c.innerHTML = `<svg width="22" height="22" viewBox="0 0 22 22"><path d="M3 2l15 8.5-6.6 1.6L8.2 19z" fill="#14212b" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>`;
  const r = document.createElement("div"); r.id = "__ring";
  const cap = document.createElement("div"); cap.id = "__cap";
  document.body.append(c, r, cap);
  addEventListener("mousemove", e => { c.style.left = e.clientX + "px"; c.style.top = e.clientY + "px"; }, true);
  addEventListener("mousedown", e => { c.classList.add("down"); r.style.left = e.clientX + "px"; r.style.top = e.clientY + "px";
    r.classList.remove("go"); void r.offsetWidth; r.classList.add("go"); }, true);
  addEventListener("mouseup", () => c.classList.remove("down"), true);
});

let mouse = { x: W / 2, y: H / 2 };
async function moveTo(x, y, steps = 28) { await page.mouse.move(x, y, { steps }); mouse = { x, y }; }
async function moveToEl(locator, dx = 0.5, dy = 0.5) {
  await locator.scrollIntoViewIfNeeded();
  const b = await locator.boundingBox();
  await moveTo(b.x + b.width * dx, b.y + b.height * dy);
}
async function click(locator) { await moveToEl(locator); await wait(180); await page.mouse.down(); await wait(90); await page.mouse.up(); }
// Wait until the current narration line has finished before moving on.
async function settle() {
  if (!pending) return;
  const left = pending - Date.now();
  if (left > 0) await page.waitForTimeout(left);
  pending = null;
}
async function caption(text, sub = "", id) {
  await settle();
  const at = Date.now() + 250;   // caption fades in after 250 ms; the voice starts with it
  timeline.push({ id, ms: at - t0 });
  pending = at + DUR[id] * 1000 + 450;
  await page.evaluate(([t, s]) => { const el = document.getElementById("__cap"); el.classList.remove("on");
    setTimeout(() => { el.innerHTML = t + (s ? `<small>${s}</small>` : ""); el.classList.add("on"); }, 250); }, [text, sub]);
  await wait(400);
}
async function hideCaption() { await page.evaluate(() => document.getElementById("__cap").classList.remove("on")); await wait(350); }
async function smoothScroll(y, ms = 900) {
  await page.evaluate(([y, ms]) => new Promise(res => {
    const start = scrollY, t0 = performance.now();
    const step = t => { const k = Math.min(1, (t - t0) / ms), e = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      scrollTo(0, start + (y - start) * e); k < 1 ? requestAnimationFrame(step) : res(); };
    requestAnimationFrame(step);
  }), [y, ms]);
}

// ---------------------------------------------------------------- the walkthrough
await page.goto(url);
await page.waitForSelector("#welcome:not([hidden])");
await overlay();
await moveTo(W / 2, H / 2, 1);
await wait(600);
await caption("Mac Disk Cleaner", "Free, open-source. Finds what's really filling your Mac.", "intro");
await wait(2600);

await caption("Start a scan of your home folder", "", "scan");
await click(page.locator("#welcomeScan"));
await page.waitForSelector("#app:not([hidden])", { timeout: 60000 });
await wait(700);

await caption("Every regenerable folder, with its real size", "Caches and build output your tools recreate on their own", "summary");
await moveToEl(page.locator(".summary .big"));
await wait(2400);
await moveToEl(page.locator("#tab-clean .row").first(), 0.3, 0.5);
await wait(1800);
await smoothScroll(520, 1400);
await caption("Sorted into safe, check first, and clean with a command", "", "groups");
await wait(2600);
await smoothScroll(1250, 1600);
await wait(1800);
await smoothScroll(0, 1200);

await caption("Explore shows a treemap of any folder", "", "explore");
await click(page.locator('.tabs button[data-tab="explore"]'));
await wait(900);
await moveToEl(page.locator(".tile").nth(1), 0.5, 0.5);
await wait(1400);
await caption("Click a tile to drill in", "Green tiles are safe to delete", "drill");
const dev = page.locator('.tile[data-name="Developer"] > div');
await click(dev);
await wait(1400);
await click(page.locator('.tile[data-name="storefront"] > div'));
await wait(1200);
await moveToEl(page.locator('.tile[data-name=".next"]'), 0.4, 0.4);
await caption("Found it: a 42 GB Next.js cache hiding in one project", "", "found");
await wait(2800);
await click(page.locator(".crumbs button").first());
await wait(900);

await caption("Back in Clean up, select everything safe in one click", "", "select");
await click(page.locator('.tabs button[data-tab="clean"]'));
await wait(600);
await click(page.locator("#selSafe"));
await wait(1500);
await moveToEl(page.locator("#tray"), 0.3, 0.5);
await wait(1200);

await caption("Review exactly what will be removed, then delete", "", "review");
await click(page.locator("#bDel"));
await wait(1800);
await moveToEl(page.locator("#cList"), 0.5, 0.4);
await wait(1600);
await click(page.locator("#cYes"));
await page.waitForSelector("#toast.on", { timeout: 60000 });
await caption("Gone. The caches rebuild themselves next time you need them", "", "done");
await wait(3000);

await caption("Largest files lists the 300 biggest files on your Mac", "", "largest");
await click(page.locator('.tabs button[data-tab="files"]'));
await wait(1000);
await moveToEl(page.locator("#tab-files .row").first(), 0.3, 0.5);
await wait(1200);
await moveToEl(page.locator('#tab-files .row').first().locator('[data-act="reveal"]'));
await caption("Show in Finder, move to Trash, or delete permanently", "", "actions");
await wait(2400);

await caption("brew install openstruct/tap/mac-disk-cleaner", "openstruct.github.io/mac-disk-cleaner", "outro");
await moveTo(W - 120, 120);
await settle();
await wait(900);
await hideCaption();
await wait(300);

fs.writeFileSync(`${outDir}/timeline.json`, JSON.stringify(timeline, null, 1));
await context.close();
await browser.close();
console.log("recorded");
