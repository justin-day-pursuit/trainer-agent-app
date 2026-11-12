# Trainer Progression App — Presentation Deck Materials

This directory contains the presentation deck materials for the Trainer Progression App, broken up into presentable formats suitable for PowerPoint, Keynote, Google Slides, or direct browser-based presentations.

---

## 📂 Formats Available

| Format | File / Directory | Description |
| :--- | :--- | :--- |
| **PowerPoint** | `presentation/deck.pptx` | 16:9 widescreen presentation with all 10 slides, high-definition graphics, titles, and embedded presenter speaker notes for each slide. |
| **Interactive HTML Deck** | `presentation/slides.html` | Browser-based slide deck with keyboard navigation (`←`/`→`/`Space`), fullscreen mode (`F`), thumbnail tray (`T`), and presenter notes drawer (`N`). No software installation required. |
| **Broken-Up Slides (PDF)** | `presentation/deck-slides/slide-01.pdf` – `slide-10.pdf` | Each slide isolated as a standalone, vector-accurate single-page PDF. |
| **Broken-Up Slides (PNG)** | `presentation/deck-slides/slide-01.png` – `slide-10.png` | Crisp 1920×1080 16:9 high-resolution images ready to drop into any presentation software. |
| **Original Deck** | `presentation/deck.pdf` | Original 10-page master PDF. |
| **Diagrams** | `presentation/diagrams/` | Standalone high-resolution PNG, PDF, and HTML source for the system architecture and agent workflow loop diagrams. |

---

## 📑 Slide Outline & Content Summary

1. **Slide 1 — Title**:
   - *Title*: FINAL PROJECT: Trainer Progression App
   - *Subtitle*: Next week’s workouts drafted from last week’s logs. The trainer approves every one.
   - *Presenters*: Yadan Taino and Justin Day
2. **Slide 2 — Who we are**:
   - *Pursuit L2 AI-Native Builders*:
     - **Yadan Taino** (Client Side & Design): Chat/voice logging, Workout Logger agent, progression rules, Trainer Assistant check-ins, app design.
     - **Justin Day** (Backend & Deployment): API, PostgreSQL database, Progression Planner safety agent, trainer authentication, live deployment on Render and Vercel.
3. **Slide 3 — The job: personal trainer**:
   - Four core duties from O*NET / BLS:
     - Assess abilities and goals
     - **Create and adjust programs** *(Our focus)*
     - **Monitor client progress** *(Our focus)*
     - Teach technique and safety
4. **Slide 4 — The pain points: slow, repetitive, easy to miss**:
   - *Slow*: Rebuilding every program week by week in Google Sheets.
   - *Repetitive*: Deterministic rep/weight progression math applied manually for every lift.
   - *Easy to miss*: In-chat pain notes slip by, and disengaging clients drift away quietly.
5. **Slide 5 — What we made easier, and how**:
   - Side-by-side comparison of "Today" vs "With our app" across client logging, program drafting, trainer review, injury safeguards, and client retention.
6. **Slide 6 — Architecture: AI reads, code decides the numbers**:
   - Frontends on Vercel (client private link + trainer dashboard), FastAPI backend on Render, Supabase PostgreSQL, and strict role separation:
     - **Workout Logger** (AI, Claude Sonnet 5.5): Conversational set extraction.
     - **Progression Engine** (Deterministic Code): Only source of truth for weights and reps.
     - **Progression Planner** (AI, Claude Haiku 5.5): Flags safety and injury conflicts.
     - **Trainer Assistant** (AI, Claude Sonnet 5.5): Inactivity triage and draft check-in outreach.
7. **Slide 7 — Agent Workflow Loop: The Complete Cycle**:
   - Full-bleed diagram depicting the 7-step weekly cycle and check-in loop with human checkpoints (Client confirm $\to$ Engine $\to$ Planner $\to$ Trainer approve $\to$ Client).
8. **Slide 8 — How one workout moves through**:
   - Step-by-step walkthrough of a concrete bench press session where pain was reported:
     - 1. Client logs $\to$ 2. Workout Logger extracts $\to$ 3. Client checks $\to$ 4. Engine holds lift $\to$ 5. Planner flags safety $\to$ 6. Trainer approves.
9. **Slide 9 — What we built: the whole loop, live**:
   - The Loom walkthrough plays in place of the old screenshot slide. In the browser deck it is the Loom player and starts when you arrive. The arrow keys move on. In PowerPoint or Keynote, start the slideshow and the same recording starts on this slide. A still picture means you are not in the slideshow yet; click it once.
10. **Slide 10 — Where it stands: live and tested end to end**:
    - Live URL (`trainer-agent-app.vercel.app`), feature delivery status, production E2E test results (9 of 10 checks passed), and next steps.

---

## 🚀 How to Present

### Option A: PowerPoint / Keynote / Google Slides
Open `presentation/deck.pptx` directly in Microsoft PowerPoint, Apple Keynote, or upload to Google Slides.
- Speaker notes are already pre-populated for each slide.
- Layout is locked to 16:9 widescreen.
- Slide 9 is the Loom walkthrough. Start the slideshow and it plays when you reach that slide. If you still see a still picture, click it once.

### Option B: Web Browser (Zero Setup)
Open `presentation/slides.html` in Chrome, Safari, Edge, or Firefox.
- **Next Slide**: `→` or `PageDown` or `Space`
- **Previous Slide**: `←` or `PageUp`
- **Slide 9**: the Loom walkthrough plays on its own. Let it finish, then move on with the right arrow. If you click inside the player, use the on-screen arrows to leave the slide.
- **Fullscreen Mode**: Press `F`
- **Presenter Notes**: Press `N` (opens/closes speaker notes panel)
- **Thumbnail Strip**: Press `T` (opens quick jump drawer)

### Option C: Re-generating Assets
To regenerate the slide images, individual PDFs, and `.pptx` file from `deck.pdf`:
```bash
# 1. Render slides to images and individual PDFs
# (Compiled using macOS native PDFKit / Cocoa)
clang -framework Foundation -framework PDFKit -framework AppKit -o /tmp/render_pdf_to_images /tmp/render_pdf_to_images.m
/tmp/render_pdf_to_images

# 2. Build the PowerPoint deck
backend/.venv/bin/python presentation/generate_deck.py
```
