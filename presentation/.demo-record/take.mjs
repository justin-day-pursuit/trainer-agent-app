/**
 * Records a continuous walkthrough of Trainer Progression.
 *
 * The picture keeps page loads and scrolling. Long silent loads and scrolls
 * are sped up later. Dead air after a line is trimmed. The trainer password
 * is read from the environment or a local file and is never printed.
 */

import { chromium } from "playwright";
import { spawn, execFile } from "node:child_process";
import { promisify } from "node:util";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const exec = promisify(execFile);
const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../..");
const work = here;
const ffmpeg = "/opt/homebrew/bin/ffmpeg";
const ffprobe = "/opt/homebrew/bin/ffprobe";
const LIVE = "https://trainer-agent-app.vercel.app";
const EMAIL = "coach.mike@pursuit.org";

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/** Reads the trainer password without ever writing it to the log. */
function readPassword() {
  const fromEnv = process.env.TRAINER_PASSWORD?.trim();
  if (fromEnv) return fromEnv;
  const file = path.join(work, ".trainer-password");
  if (fs.existsSync(file)) return fs.readFileSync(file, "utf8").trim();
  return "";
}

function stampFactory() {
  let origin = Date.now();
  const segments = [];
  const narrations = [];
  const stamp = () => (Date.now() - origin) / 1000;
  const reset = () => {
    origin = Date.now();
  };
  const mark = (kind, name) => {
    const start = stamp();
    return () => segments.push({ kind, name, start, end: stamp() });
  };
  return { stamp, reset, mark, segments, narrations };
}

/**
 * Draws the caption bar and the arrow cursor inside the page.
 * The page script runs again after each full load, so the bar survives navigation.
 */
async function installOverlay(context) {
  await context.addInitScript(() => {
    const mount = () => {
      if (document.getElementById("demo-caption")) return;
      const style = document.createElement("style");
      style.textContent = `
        #demo-caption {
          position: fixed; left: 28px; right: 28px; bottom: 16px; z-index: 2147483646;
          background: rgba(9,9,11,0.92); color: #f4f4f5; border-left: 4px solid #84cc16;
          border-radius: 12px; padding: 12px 16px; font: 600 18px/1.35 ui-sans-serif, system-ui, sans-serif;
          pointer-events: none;
        }
        #demo-cursor {
          position: fixed; z-index: 2147483647; width: 28px; height: 28px;
          pointer-events: none; left: 24px; top: 24px;
        }
      `;
      document.documentElement.appendChild(style);
      const cap = document.createElement("div");
      cap.id = "demo-caption";
      document.documentElement.appendChild(cap);
      const cur = document.createElement("div");
      cur.id = "demo-cursor";
      cur.innerHTML =
        '<svg width="28" height="28" viewBox="0 0 28 28"><path d="M4 3 L4 22 L10 17 L14 25 L17 23 L13 15 L22 15 Z" fill="#fafafa" stroke="#111" stroke-width="1.2"/></svg>';
      document.documentElement.appendChild(cur);
    };
    mount();
    document.addEventListener("DOMContentLoaded", mount);
    window.__demoCaption = (text) => {
      mount();
      const el = document.getElementById("demo-caption");
      if (el) el.textContent = text;
    };
    window.__demoCursor = (x, y) => {
      mount();
      const el = document.getElementById("demo-cursor");
      if (el) {
        el.style.left = x + "px";
        el.style.top = y + "px";
      }
    };
  });
}

function makeDriver(page, clock) {
  /** Puts the caption on the page itself so a navigation cannot wipe it. */
  const caption = async (text) => {
    await page.evaluate((value) => {
      let el = document.getElementById("demo-caption");
      if (!el) {
        el = document.createElement("div");
        el.id = "demo-caption";
        el.style.cssText = [
          "position:fixed", "left:24px", "right:24px", "bottom:16px", "z-index:2147483646",
          "background:rgba(9,9,11,0.94)", "color:#f4f4f5", "border-left:4px solid #84cc16",
          "border-radius:12px", "padding:12px 16px 12px 46px",
          "font:600 18px/1.35 ui-sans-serif,system-ui,sans-serif",
          "pointer-events:none",
        ].join(";");
        document.documentElement.appendChild(el);
      }
      el.style.padding = "12px 16px 12px 46px";
      el.textContent = value;
    }, text).catch(() => {});
  };
  /** Where the pointer is right now, so the next move can start from there. */
  let pointer = { x: 620, y: 150 };

  /** Draws one arrow at the real mouse position. The tip is the click point. */
  const place = async (x, y) => {
    const left = Math.max(16, Math.min(1240, x));
    const top = Math.max(16, Math.min(640, y));
    await page.evaluate(([cx, cy]) => {
      let el = document.getElementById("demo-cursor");
      if (!el) {
        el = document.createElement("div");
        el.id = "demo-cursor";
        el.style.cssText = "position:fixed;z-index:2147483647;width:22px;height:22px;pointer-events:none;";
        el.innerHTML = '<svg width="22" height="22" viewBox="0 0 22 22"><path d="M2 1 L2 16 L6.5 12.2 L9.2 19 L12 17.8 L9.2 11 L15.5 11 Z" fill="#fafafa" stroke="#111" stroke-width="1.2"/></svg>';
        document.documentElement.appendChild(el);
      }
      el.style.left = cx + "px";
      el.style.top = cy + "px";
    }, [left, top]).catch(() => {});
  };

  /**
   * Slides the pointer from where it is to the next control.
   * Short hops still take long enough to follow. Long crosses stay under a second and a half.
   */
  const travelTo = async (x, y) => {
    const destX = Math.max(40, Math.min(1200, x));
    const destY = Math.max(48, Math.min(600, y));
    const dist = Math.hypot(destX - pointer.x, destY - pointer.y);
    if (dist < 10) {
      pointer = { x: destX, y: destY };
      await page.mouse.move(destX, destY);
      await place(destX, destY);
      return;
    }
    const end = clock.mark("move", "travel");
    const duration = Math.min(1300, Math.max(780, dist * 1.7));
    const steps = Math.max(16, Math.round(duration / 36));
    const from = { ...pointer };
    for (let i = 1; i <= steps; i += 1) {
      const t = i / steps;
      const eased = t * t * (3 - 2 * t);
      const cx = from.x + (destX - from.x) * eased;
      const cy = from.y + (destY - from.y) * eased;
      await page.mouse.move(cx, cy);
      await place(cx, cy);
      await page.waitForTimeout(duration / steps);
    }
    pointer = { x: destX, y: destY };
    end();
  };
  const scroller = () => page.locator("div.flex-1.scrollable-container").first();

  /** Scrolls the page's own list, in small steps, so the motion stays visible. */
  const glide = async (pixels) => {
    const target = (await scroller().count()) > 0 ? scroller() : page.locator("main").first();
    const room = await target
      .evaluate((el) => ({
        max: el.scrollHeight - el.clientHeight,
        top: el.scrollTop,
      }))
      .catch(() => ({ max: 0, top: 0 }));
    if (room.max < 24) return;
    const available = pixels > 0 ? room.max - room.top : room.top;
    if (available < 24) return;
    const box = await target.boundingBox().catch(() => null);
    const driftX = box ? Math.min(1100, box.x + Math.min(box.width * 0.55, 280)) : pointer.x;
    const end = clock.mark("scroll", "glide");
    const steps = 22;
    const distance = Math.sign(pixels) * Math.min(Math.abs(pixels), available);
    for (let i = 0; i < steps; i += 1) {
      await target.evaluate((el, delta) => {
        el.scrollTop += delta;
      }, distance / steps).catch(async () => {
        await page.mouse.wheel(0, distance / steps);
      });
      const driftY = Math.min(560, pointer.y + ((pixels > 0 ? 70 : -40) * (i + 1)) / steps);
      await page.mouse.move(driftX, driftY);
      await place(driftX, driftY);
      await page.waitForTimeout(70);
    }
    pointer = { x: driftX, y: Math.min(560, pointer.y + (pixels > 0 ? 70 : -40)) };
    end();
  };

  /** Brings a control into the open area above the caption bar. */
  const reveal = async (locator) => {
    for (let i = 0; i < 8; i += 1) {
      const box = await locator.boundingBox().catch(() => null);
      if (box && box.y > 80 && box.y < 540) return box;
      if ((await scroller().count()) > 0) {
        await scroller().evaluate((el) => {
          el.scrollTop += 160;
        });
      } else {
        await page.mouse.wheel(0, 160);
      }
      await page.waitForTimeout(70);
    }
    await locator.scrollIntoViewIfNeeded().catch(() => {});
    return locator.boundingBox();
  };

  /**
   * Clicks with the arrow parked to the left of the label so the words stay readable.
   */
  const click = async (locator) => {
    for (let i = 0; i < 12; i += 1) {
      const seen = await locator.boundingBox().catch(() => null);
      const inView = seen && seen.y > 120 && seen.y + seen.height < 560;
      if (inView) break;
      const delta = !seen || seen.y > 120 ? 160 : -160;
      if ((await scroller().count()) > 0) {
        await scroller().evaluate((el, amount) => {
          el.scrollTop += amount;
        }, delta);
      } else {
        await page.mouse.wheel(0, delta);
      }
      await page.waitForTimeout(50);
    }
    const box = await locator.boundingBox();
    if (!box) throw new Error("Nothing to click");
    const x = box.x + Math.min(box.width - 8, Math.max(12, box.width * 0.3));
    const y = box.y + box.height / 2;
    await travelTo(x, y);
    await page.waitForTimeout(160);
    await locator.click({
      position: { x: Math.min(box.width - 8, Math.max(12, box.width * 0.3)), y: box.height / 2 },
    });
  };

  /**
   * Shows a short caption, records where the spoken line should start,
   * and keeps the picture up long enough for that line.
   */
  const speak = async (id, captionText, spoken, during) => {
    await caption(captionText);
    clock.narrations.push({ id, text: spoken, at: clock.stamp() });
    const end = clock.mark("speak", id);
    const estimate = spoken.split(/\s+/).length / 2.3 + 0.45;
    const started = Date.now();
    if (during) await during();
    end();
    const left = estimate * 1000 - (Date.now() - started);
    if (left > 200) {
      const endPad = clock.mark("pad", id);
      await page.waitForTimeout(left);
      endPad();
    }
  };

  return { caption, glide, click, speak, scroller };
}

async function recordClip(browser, name, run) {
  const dir = path.join(work, "video", name);
  fs.mkdirSync(dir, { recursive: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: { dir, size: { width: 1280, height: 720 } },
    colorScheme: "dark",
    locale: "en-US",
    timezoneId: "America/New_York",
  });
  await installOverlay(context);
  const page = await context.newPage();
  const clock = stampFactory();
  clock.reset();
  const driver = makeDriver(page, clock);
  let failed = null;
  try {
    await run(page, driver, clock);
  } catch (error) {
    failed = error;
    await page.screenshot({ path: path.join(work, `fail-${name}.png`) }).catch(() => {});
    console.error(name, error);
  }
  const video = page.video();
  await page.close().catch(() => {});
  await context.close();
  const webm = video ? await video.path() : "";
  return { webm, segments: clock.segments, narrations: clock.narrations, failed };
}

/** Walks the public site from the home page through the trainer sign-in form. */
async function recordPublic(page, ui, clock) {
  let end = clock.mark("load", "home");
  await ui.caption("Opening the home page");
  await page.goto(LIVE, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.getByRole("heading", { name: "Trainer Progression" }).waitFor({ timeout: 30000 });
  await ui.caption("Opening the home page");
  end();

  await ui.speak(
    "home",
    "Home page. The client uses a private link.",
    "This is Trainer Progression. A client starts on the home page and uses the private link from their trainer.",
    async () => {
      await ui.glide(220);
      await ui.glide(-220);
    }
  );

  const token = page.locator("#token-input");
  await ui.click(token);
  end = clock.mark("action", "type-token");
  await ui.caption("Entering the session link");
  await token.pressSequentially("demo-client-session", { delay: 48 });
  end();

  await ui.speak(
    "open",
    "Opening today's workout log",
    "The link goes in the box. The next click opens today's workout."
  );

  end = clock.mark("load", "client");
  await ui.caption("The workout log is loading");
  await ui.click(page.getByRole("button", { name: "Open My Workout Log" }));
  await page.waitForURL(/\/s\//, { timeout: 30000 });
  await ui.caption("The workout log is loading");
  await page.getByText(/Loading your plan|Today's session|Sent to your trainer/).first().waitFor({ timeout: 30000 });
  await page
    .getByText("Loading your plan...")
    .waitFor({ state: "hidden", timeout: 30000 })
    .catch(() => {});
  end();

  const pending = (await page.getByText("Sent to your trainer").count()) > 0;
  if (pending) {
    await ui.speak(
      "pending",
      "This week is already with the trainer.",
      "This week was already sent. The page stays on what she logged, and you can scroll through it.",
      () => ui.glide(360)
    );
  } else {
    if ((await page.getByRole("button", { name: "Discard" }).count()) > 0) {
      await ui.click(page.getByRole("button", { name: "Discard" }));
      await page.waitForTimeout(300);
    }
    await ui.speak(
      "plan",
      "Today's plan is on the page.",
      "Today's plan loads in the list. Scroll to read every exercise before logging.",
      () => ui.glide(280)
    );

    const note = page.getByLabel("Describe your workout");
    if ((await note.count()) > 0) {
      await ui.click(note);
      end = clock.mark("action", "type-note");
      await ui.caption("Typing what she lifted");
      await note.pressSequentially("Bench 135 for 3 sets of 10. Felt good.", { delay: 32 });
      end();
      await ui.speak(
        "note",
        "The note stays on the page until she checks it.",
        "She types what she actually did. Nothing is sent yet."
      );

      end = clock.mark("load", "logger");
      await ui.caption("Reading the note into sets");
      await ui.click(page.getByRole("button", { name: "Next: Check My Sets" }));
      await page
        .getByText(/Check your sets|Tell us what you lifted|Try Again/)
        .first()
        .waitFor({ timeout: 50000 });
      end();

      if ((await page.getByRole("heading", { name: "Check your sets" }).count()) > 0) {
        await ui.speak(
          "check",
          "Check the sets, then mark how they felt.",
          "The logger filled the sets. She checks every number and marks the work easy. Sending is still her choice.",
          async () => {
            const easies = page.getByRole("button", { name: "easy", exact: true });
            const count = await easies.count();
            for (let i = 0; i < count; i += 1) await ui.click(easies.nth(i));
            await ui.glide(180);
          }
        );
      }
    }
  }

  end = clock.mark("load", "progress");
  await ui.caption("Opening My Progress");
  await ui.click(page.getByRole("button", { name: "My Progress" }));
  await page.getByRole("heading", { name: "Your workouts" }).waitFor({ timeout: 20000 });
  await page
    .getByText("Loading...")
    .waitFor({ state: "hidden", timeout: 20000 })
    .catch(() => {});
  end();

  await ui.speak(
    "progress",
    "My Progress. Saved workouts, including pain notes.",
    "My Progress loads her saved workouts. A pain note stays visible on the session where she logged it.",
    () => ui.glide(420)
  );

  end = clock.mark("load", "back-home");
  await ui.caption("Back to the home page");
  await ui.click(page.getByRole("link", { name: "Back to home" }));
  await page.getByRole("heading", { name: "Trainer Progression" }).waitFor({ timeout: 20000 });
  await ui.caption("Back to the home page");
  end();

  await ui.speak(
    "signin-intro",
    "The trainer signs in with their own account.",
    "Back home, the trainer opens their own sign-in. Clients never use this form."
  );

  end = clock.mark("load", "login");
  await ui.caption("Opening trainer sign-in");
  await ui.click(page.getByRole("link", { name: "Sign In" }));
  await page.getByRole("heading", { name: "Trainer Sign In" }).waitFor({ timeout: 20000 });
  await ui.caption("Opening trainer sign-in");
  end();

  const email = page.getByPlaceholder("trainer@example.com");
  await ui.click(email);
  end = clock.mark("action", "type-email");
  await ui.caption("Entering the trainer email");
  await email.pressSequentially(EMAIL, { delay: 42 });
  end();

  const password = page.getByPlaceholder("••••••••");
  await ui.click(password);
  const secret = readPassword();
  if (secret) {
    end = clock.mark("action", "type-password");
    await ui.caption("The password stays masked");
    await password.pressSequentially(secret, { delay: 55 });
    end();
    end = clock.mark("load", "submit-login");
    await ui.caption("Signing in");
    await ui.click(page.getByRole("button", { name: "Open Trainer Dashboard" }));
    const landed = await page
      .getByRole("heading", { name: "Trainer Dashboard" })
      .waitFor({ timeout: 25000 })
      .then(() => true)
      .catch(() => false);
    end();
    if (!landed) {
      const message = await page.locator("form").locator("xpath=preceding-sibling::div[1]").textContent().catch(() => "");
      console.log("Login did not open the dashboard.", (message || "").slice(0, 140));
      await ui.speak(
        "login-held",
        "Sign-in stays on this form until the password is accepted.",
        "The password stays masked. The dashboard opens only after this form is accepted."
      );
      return false;
    }
    await walkDashboard(page, ui, clock);
    return true;
  }

  await ui.speak(
    "login",
    "Email is in. The password stays masked.",
    "This is the trainer sign-in. The email is entered, and the password stays hidden in this field. The dashboard opens after that password is accepted."
  );
  return false;
}

/** Shows the review queue: scroll, a draft, edit then cancel, search, roster, and the add form. */
async function walkDashboard(page, ui, clock) {
  let end = clock.mark("load", "queue");
  await ui.caption("Loading the review queue");
  await page
    .getByText("Loading plans...")
    .waitFor({ state: "visible", timeout: 4000 })
    .catch(() => {});
  await page
    .getByText(/David Chen|Attention Required|couldn't load your plans/)
    .first()
    .waitFor({ timeout: 25000 });
  end();

  await ui.speak(
    "queue",
    "The review queue. Scroll to see who is waiting.",
    "The dashboard opens on the review queue. Scroll to see who needs a check-in and whose plan is waiting.",
    () => ui.glide(320)
  );

  const elena = page.getByRole("button", { name: /Elena Rostova/ });
  if ((await elena.count()) > 0) {
    await ui.click(elena.first());
    await ui.speak(
      "triage",
      "A check-in draft. It is not sent from here.",
      "Elena's check-in is a draft the trainer can copy or edit. The app does not send it.",
      () => ui.glide(160)
    );
  }

  const edit = page.getByRole("button", { name: "Edit Target" }).first();
  if ((await edit.count()) > 0) {
    await ui.click(edit);
    await page.getByLabel(/target reps/i).first().waitFor({ timeout: 8000 });
    await ui.speak(
      "edit",
      "Edit Target opens the numbers. Cancel puts them back.",
      "Edit Target opens the numbers. Cancel puts them back. Approve stays with the trainer.",
      async () => {
        await page.waitForTimeout(900);
        await ui.click(page.getByRole("button", { name: "Cancel" }).first());
        await page.getByRole("button", { name: "Edit Target" }).first().waitFor({ timeout: 8000 });
      }
    );
  }

  const search = page.getByLabel("Search clients");
  if ((await search.count()) > 0) {
    await ui.click(search);
    end = clock.mark("action", "search");
    await ui.caption("Search filters the whole dashboard");
    await search.pressSequentially("Sarah", { delay: 90 });
    end();
    await ui.speak(
      "search",
      "Search filters the queue and the roster.",
      "Search filters the whole dashboard down to Sarah."
    );
    await search.fill("");
    await page.waitForTimeout(250);
  }

  await ui.speak(
    "roster",
    "The roster lists every client and their private link.",
    "The roster lists every client. Each private link is copied from here.",
    () => ui.glide(520)
  );

  const add = page.getByRole("button", { name: "Add client" });
  if ((await add.count()) > 0) {
    await ui.click(add.first());
    const name = page.getByLabel("Name", { exact: true });
    if ((await name.count()) > 0) {
      await ui.click(name);
      end = clock.mark("action", "add-name");
      await ui.caption("The new-client form. It is closed without saving.");
      await name.pressSequentially("Alex Riv", { delay: 70 });
      end();
    }
    await ui.speak(
      "add",
      "Closing the form does not create a client.",
      "Add client opens the form. Closing it does not save anyone.",
      async () => {
        await ui.click(page.getByRole("button", { name: "Add client" }).first());
      }
    );
  }
}

/** Starts the local app so the signed-in dashboard can load with its real queue. */
function startLocalApp() {
  const backend = spawn(
    path.join(root, "backend/.venv/bin/uvicorn"),
    ["app.main:app", "--port", "8000"],
    {
      cwd: path.join(root, "backend"),
      env: { ...process.env, SUPABASE_JWT_SECRET: "", DEBUG: "true" },
      stdio: "ignore",
    }
  );
  const frontend = spawn("npm", ["run", "dev", "--", "--port", "3000"], {
    cwd: path.join(root, "frontend"),
    stdio: "ignore",
  });
  return { backend, frontend };
}

async function waitForLocal() {
  const deadline = Date.now() + 90000;
  while (Date.now() < deadline) {
    try {
      const health = await fetch("http://localhost:8000/health");
      const home = await fetch("http://localhost:3000/trainer");
      if (health.ok && home.ok) return;
    } catch {
      // The servers are still booting.
    }
    await sleep(800);
  }
  throw new Error("Local app did not start");
}

function stopLocal(procs) {
  for (const proc of procs) {
    if (proc && !proc.killed) proc.kill("SIGTERM");
  }
}

async function probe(file) {
  const { stdout } = await exec(ffprobe, [
    "-v",
    "error",
    "-show_entries",
    "format=duration",
    "-of",
    "default=nw=1:nk=1",
    file,
  ]);
  return Number(stdout.trim());
}

/** Speeds long silent loads and scrolls, and drops tiny gaps. */
function planPieces(segments, duration) {
  const sorted = [...segments].filter((seg) => seg.end - seg.start > 0.08).sort((a, b) => a.start - b.start);
  const pieces = [];
  let cursor = 0;
  const pushGap = (start, end) => {
    if (end - start > 0.12) pieces.push({ start, end, speed: 1 });
  };
  for (const seg of sorted) {
    const start = Math.max(seg.start, cursor);
    if (start > cursor) pushGap(cursor, start);
    const dur = seg.end - start;
    if (dur <= 0.08) {
      cursor = Math.max(cursor, seg.end);
      continue;
    }
    if (seg.kind === "pad") {
      const keep = Math.min(dur, seg.keep ?? dur);
      pieces.push({ start, end: start + keep, speed: 1 });
      cursor = seg.cutUntil ?? seg.end;
      continue;
    }
    let speed = 1;
    if ((seg.kind === "load" || seg.kind === "scroll") && dur > 2.4) {
      const target = seg.kind === "load" ? Math.min(4.2, Math.max(2.3, dur * 0.42)) : Math.min(2.8, Math.max(1.7, dur * 0.55));
      speed = Math.min(seg.kind === "load" ? 5 : 2.4, dur / target);
      if (speed < 1.12) speed = 1;
    }
    const moves = sorted.filter((item) => item.kind === "move" && item.end > start && item.start < seg.end);
    if (speed > 1 && moves.length > 0) {
      let at = start;
      for (const move of moves) {
        const moveStart = Math.max(move.start, start);
        const moveEnd = Math.min(move.end, seg.end);
        if (moveStart > at + 0.08) pieces.push({ start: at, end: moveStart, speed });
        if (moveEnd > moveStart + 0.04) pieces.push({ start: moveStart, end: moveEnd, speed: 1 });
        at = Math.max(at, moveEnd);
      }
      if (seg.end > at + 0.08) pieces.push({ start: at, end: seg.end, speed });
    } else {
      pieces.push({ start, end: seg.end, speed });
    }
    cursor = seg.end;
  }
  if (duration - cursor > 0.12) pieces.push({ start: cursor, end: duration, speed: 1 });
  return pieces.filter((piece) => piece.end - piece.start > 0.08);
}

function mapTime(pieces, time) {
  let out = 0;
  for (const piece of pieces) {
    if (time >= piece.end) out += (piece.end - piece.start) / piece.speed;
    else if (time > piece.start) return out + (time - piece.start) / piece.speed;
    else return out;
  }
  return out;
}

async function renderClip(webm, segments, narrations, outFile) {
  const duration = await probe(webm);
  const audioDir = path.join(work, "audio");
  fs.mkdirSync(audioDir, { recursive: true });
  const cues = [];
  for (const line of narrations) {
    const aiff = path.join(audioDir, `${path.basename(outFile, ".mp4")}-${line.id}.aiff`);
    await exec("say", ["-v", "Samantha", "-r", "168", "-o", aiff, line.text]);
    cues.push({ ...line, aiff, dur: await probe(aiff) });
  }
  for (const pad of segments.filter((seg) => seg.kind === "pad")) {
    const cue = cues.find((item) => item.id === pad.name);
    const spoken = segments.find((seg) => seg.kind === "speak" && seg.name === pad.name);
    if (!cue || !spoken) continue;
    const moveDur = segments
      .filter((seg) => seg.kind === "move" && seg.end > spoken.start && seg.start < spoken.end)
      .reduce((sum, seg) => sum + (Math.min(seg.end, spoken.end) - Math.max(seg.start, spoken.start)), 0);
    const spokenDur = Math.max(0.2, spoken.end - spoken.start - moveDur);
    const need = Math.max(0.25, cue.dur + 0.3 - spokenDur);
    pad.cutUntil = pad.end;
    pad.keep = Math.min(pad.end - pad.start, need);
  }
  const pieces = planPieces(segments, duration);
  const filters = pieces.map((piece, index) => {
    return `[0:v]trim=start=${piece.start.toFixed(3)}:end=${piece.end.toFixed(3)},setpts=(PTS-STARTPTS)/${piece.speed.toFixed(4)},fps=25,scale=1280:720,setsar=1[v${index}]`;
  });
  filters.push(`${pieces.map((_, index) => `[v${index}]`).join("")}concat=n=${pieces.length}:v=1:a=0[v]`);
  const silentVideo = outFile.replace(/\.mp4$/, ".silent.mp4");
  await exec(ffmpeg, [
    "-y",
    "-i",
    webm,
    "-filter_complex",
    filters.join(";"),
    "-map",
    "[v]",
    "-an",
    "-c:v",
    "libx264",
    "-pix_fmt",
    "yuv420p",
    "-r",
    "25",
    silentVideo,
  ]);
  const videoDur = await probe(silentVideo);
  for (const cue of cues) cue.out = mapTime(pieces, cue.at);
  cues.sort((a, b) => a.out - b.out);
  for (let i = 0; i < cues.length; i += 1) {
    const room = (cues[i + 1]?.out ?? videoDur) - cues[i].out - 0.12;
    if (cues[i].dur > room && room > 0.5) {
      const tempo = Math.min(1.55, cues[i].dur / room);
      const sped = cues[i].aiff.replace(/\.aiff$/, ".sped.aiff");
      await exec(ffmpeg, ["-y", "-i", cues[i].aiff, "-filter:a", `atempo=${tempo.toFixed(3)}`, sped]);
      cues[i].aiff = sped;
      cues[i].dur = await probe(sped);
    }
  }
  const list = [];
  let cursor = 0;
  let part = 0;
  const wav = async (file) => {
    const next = path.join(audioDir, `${path.basename(outFile, ".mp4")}-${part}.wav`);
    part += 1;
    await exec(ffmpeg, ["-y", "-i", file, "-ar", "44100", "-ac", "2", next]);
    return next;
  };
  const gap = async (seconds) => {
    const next = path.join(audioDir, `${path.basename(outFile, ".mp4")}-gap-${part}.wav`);
    part += 1;
    await exec(ffmpeg, [
      "-y",
      "-f",
      "lavfi",
      "-i",
      "anullsrc=r=44100:cl=stereo",
      "-t",
      seconds.toFixed(3),
      next,
    ]);
    return next;
  };
  for (const cue of cues) {
    const hole = cue.out - cursor;
    if (hole > 0.04) list.push(`file '${await gap(hole)}'`);
    list.push(`file '${await wav(cue.aiff)}'`);
    cursor = Math.max(cursor, cue.out) + cue.dur;
  }
  if (videoDur - cursor > 0.04) list.push(`file '${await gap(videoDur - cursor)}'`);
  const listFile = path.join(audioDir, `${path.basename(outFile, ".mp4")}-list.txt`);
  fs.writeFileSync(listFile, list.join("\n"));
  const narration = outFile.replace(/\.mp4$/, ".wav");
  await exec(ffmpeg, ["-y", "-f", "concat", "-safe", "0", "-i", listFile, "-c", "copy", narration]);
  await exec(ffmpeg, [
    "-y",
    "-i",
    silentVideo,
    "-i",
    narration,
    "-filter_complex",
    "[1:a]apad[a]",
    "-map",
    "0:v",
    "-map",
    "[a]",
    "-c:v",
    "copy",
    "-c:a",
    "aac",
    "-b:a",
    "160k",
    "-shortest",
    outFile,
  ]);
  return videoDur;
}

async function main() {
  fs.mkdirSync(path.join(work, "video"), { recursive: true });
  const browser = await chromium.launch({
    channel: "chrome",
    headless: true,
    ignoreDefaultArgs: ["--enable-automation"],
  });
  let procs = null;
  try {
    const dashboardOnly = process.argv.includes("--dashboard-only");
    const clips = [];
    if (!dashboardOnly) {
      console.log("Recording the live site, including loads, scrolling, and sign-in.");
      const pub = await recordClip(browser, "public", recordPublic);
      if (pub.failed) throw pub.failed;
      clips.push(pub);
      if (pub.narrations.some((line) => line.id === "queue")) {
        console.log("Sign-in opened the dashboard in the same take.");
      }
    } else {
      console.log("Reusing the client and sign-in recording. Re-recording the dashboard.");
    }
    const alreadyIn = !dashboardOnly && clips[0]?.narrations.some((line) => line.id === "queue");
    if (!alreadyIn) {
      console.log("Sign-in form recorded. Starting the local dashboard so its load and scroll are in the picture.");
      procs = startLocalApp();
      await waitForLocal();
      await fetch("http://localhost:3000/trainer").catch(() => {});
      const dash = await recordClip(browser, "dashboard", async (page, ui, clock) => {
        const end = clock.mark("load", "dash-open");
        await ui.caption("Opening the trainer dashboard");
        await page.goto("http://localhost:3000/trainer", { waitUntil: "domcontentloaded", timeout: 45000 });
        await page.getByRole("heading", { name: "Trainer Dashboard" }).waitFor({ timeout: 30000 });
        await ui.caption("Opening the trainer dashboard");
        end();
        await walkDashboard(page, ui, clock);
      });
      if (dash.failed) throw dash.failed;
      clips.push(dash);
    }
    const rendered = [];
    for (const clip of clips) {
      const out = path.join(work, `edited-${path.basename(path.dirname(clip.webm))}.mp4`);
      const dur = await renderClip(clip.webm, clip.segments, clip.narrations, out);
      console.log("Edited", out, dur.toFixed(1) + "s");
      rendered.push(out);
    }
    const finalFile = path.join(root, "presentation/trainer-progression-walkthrough.mp4");
    if (dashboardOnly) rendered.unshift(path.join(work, "edited-public.mp4"));
    if (rendered.length === 1) {
      fs.copyFileSync(rendered[0], finalFile);
    } else {
      const list = path.join(work, "concat.txt");
      fs.writeFileSync(list, rendered.map((file) => `file '${file}'`).join("\n"));
      await exec(ffmpeg, ["-y", "-f", "concat", "-safe", "0", "-i", list, "-c", "copy", finalFile]);
    }
    console.log("Wrote", finalFile);
  } finally {
    await browser.close().catch(() => {});
    if (procs) stopLocal([procs.backend, procs.frontend]);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
