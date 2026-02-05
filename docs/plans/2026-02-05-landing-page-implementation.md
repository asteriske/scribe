# Landing Page Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite the Scribe landing page (`index.html`) with a modern editorial design featuring alternating full-width bands, detailed mode cards, and styled email mockups showing a real workflow.

**Architecture:** Single static HTML file with embedded CSS. No JavaScript. Full-width alternating background bands with centered content. Dark mode via `prefers-color-scheme`. Responsive via CSS grid and media queries.

**Tech Stack:** HTML5, CSS3 (custom properties, grid, flexbox)

**Design doc:** `docs/plans/2026-02-05-landing-page-redesign.md`

**Working directory:** `/Users/patrick/git/scribe/.worktrees/landing-page-redesign`

---

### Task 1: CSS Foundation & Hero Band

**Files:**
- Modify: `index.html` (full rewrite)

**Step 1: Replace `index.html` with the CSS foundation and hero section**

Replace the entire file. This establishes the full-width band layout pattern, CSS custom properties, dark mode, and the hero section.

Key CSS details:
- `--bg: #fafafa` / dark `#111113` — base background
- `--tinted: #f0f2f5` / dark `#1a1c20` — alternating band background
- `--text: #1a1a1a` / dark `#e8e8e8`
- `--muted: #6b7280` / dark `#9ca3af`
- `--accent: #2563eb` / dark `#60a5fa`
- `--card-bg: #ffffff` / dark `#222428`
- `--border: #e2e5e9` / dark `#333640`
- Body has no max-width or padding (bands go full-width)
- `.band` class: full-width with padding, contains a `.band-content` at `max-width: 960px; margin: 0 auto`
- `.band--tinted` modifier adds the tinted background
- Hero: centered text, title at ~2.75rem, tagline at ~1.25rem in muted, value prop at ~1.1rem

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Scribe - Turn podcasts and videos into readable summaries</title>
  <style>
    /* -- Custom properties, reset, band layout, hero styles -- */
  </style>
</head>
<body>
  <section class="band">
    <div class="band-content hero">
      <h1>Scribe</h1>
      <p class="hero-tagline">Turn podcasts and videos into readable summaries</p>
      <p class="hero-value">Email a link. Get a transcript and AI summary back in minutes.</p>
    </div>
  </section>
</body>
</html>
```

**Step 2: Open in browser and verify**

Run: `open index.html`

Check: Hero text is centered, looks good in both light and dark mode (toggle system appearance to verify). Full-width background, content centered at 960px max.

**Step 3: Commit**

```bash
git add index.html
git commit -m "feat: landing page CSS foundation and hero band"
```

---

### Task 2: How It Works Band

**Files:**
- Modify: `index.html`

**Step 1: Add the How It Works section after the hero band**

This is the first tinted band. Three steps in a horizontal grid (stacking on mobile).

```html
<section class="band band--tinted">
  <div class="band-content">
    <h2 class="section-title">How it works</h2>
    <div class="steps">
      <div class="step">
        <span class="step-num">1</span>
        <h3>Send</h3>
        <p>Email a YouTube or podcast link to Scribe</p>
      </div>
      <div class="step">
        <span class="step-num">2</span>
        <h3>Choose a mode</h3>
        <p>Add a keyword like <code>recipe</code> or <code>digest</code> to the subject line — or send with any subject for the default highlights mode</p>
      </div>
      <div class="step">
        <span class="step-num">3</span>
        <h3>Receive</h3>
        <p>Get back a structured summary, creator's notes, and full transcript</p>
      </div>
    </div>
  </div>
</section>
```

CSS additions:
- `.section-title`: centered, uppercase letter-spacing, muted color, small font size — editorial style section headers
- `.steps`: `display: grid; grid-template-columns: repeat(3, 1fr); gap: 2rem;`
- `.step`: text-align center, step-num is the accent-color circle badge
- `@media (max-width: 768px)`: `.steps` becomes single column

**Step 2: Open in browser and verify**

Check: Three steps horizontal on desktop, stacking on mobile (resize window). Tinted background spans full width. `code` elements styled inline.

**Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add How It Works band"
```

---

### Task 3: Modes Band

**Files:**
- Modify: `index.html`

**Step 1: Add the Modes section after the How It Works band**

Three cards in a grid, each with accent-color top border. Base background (not tinted).

```html
<section class="band">
  <div class="band-content">
    <h2 class="section-title">Modes</h2>
    <div class="modes">
      <div class="mode-card">
        <div class="mode-header">
          <h3>Highlights</h3>
          <span class="mode-badge">Default</span>
        </div>
        <p class="mode-trigger">Just send a link — no keyword needed</p>
        <p class="mode-desc">Extracts key points as a concise bullet-point list. Focuses on main ideas, notable facts, and actionable takeaways.</p>
        <div class="mode-sample">
          <p class="mode-sample-label">Example output</p>
          <ul>
            <li>Open-source models approaching proprietary performance levels</li>
            <li>Competitive advantage shifting to data quality and fine-tuning</li>
            <li>Enterprise adoption accelerating but governance lagging</li>
          </ul>
        </div>
      </div>

      <div class="mode-card">
        <div class="mode-header">
          <h3>Recipe</h3>
        </div>
        <p class="mode-trigger">Add <code>recipe</code> to your subject line</p>
        <p class="mode-desc">Extracts ingredients with amounts and step-by-step cooking instructions. Perfect for video recipes you want to save and actually cook from.</p>
        <div class="mode-sample">
          <p class="mode-sample-label">Example output</p>
          <p><strong>Ingredients:</strong> 1 lb ditalini, 2 cans cannellini beans, 4 cloves garlic...</p>
          <p><strong>Step 1:</strong> Sauté diced onion and garlic in olive oil until translucent...</p>
        </div>
      </div>

      <div class="mode-card">
        <div class="mode-header">
          <h3>Digest</h3>
        </div>
        <p class="mode-trigger">Add <code>digest</code> to your subject line</p>
        <p class="mode-desc">An opinionated analysis highlighting main topics, interesting questions, and counter-intuitive takes. For when you want more than just the facts.</p>
        <div class="mode-sample">
          <p class="mode-sample-label">Example output</p>
          <p>The most provocative claim: small language models running locally will replace cloud APIs for 80% of use cases within 18 months. The hosts disagree sharply on timeline...</p>
        </div>
      </div>
    </div>
  </div>
</section>
```

CSS additions:
- `.modes`: `display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem;`
- `.mode-card`: card-bg background, rounded corners, `border-top: 3px solid var(--accent)`, padding, subtle shadow
- `.mode-badge`: small pill next to "Highlights" header indicating it's the default
- `.mode-trigger`: small text with the `code` element for the keyword
- `.mode-sample`: inset block with slightly different background (tinted), smaller font, rounded corners
- `.mode-sample-label`: tiny uppercase label like "Example output"
- `@media (max-width: 768px)`: `.modes` becomes single column

**Step 2: Open in browser and verify**

Check: Three equal-width cards with accent top border. Sample snippets visible in inset blocks. Cards stack on mobile.

**Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add Modes band with detail cards"
```

---

### Task 4: See It In Action Band (Email Mockups)

**Files:**
- Modify: `index.html`

**Step 1: Add the workflow example section after the Modes band**

Tinted band with two email mockups side by side. This is the most visually complex section.

**"You send" mockup:**
- Mock window chrome: rounded top corners, row of three small circles (red/yellow/green or just gray dots), title "New Message"
- Email fields styled with labels in muted and values in regular text:
  - To: scribe@example.com
  - Subject: check this out
  - Body: `https://www.youtube.com/watch?v=dQw4w9WgXcQ` (or a plausible-looking URL)

**"You receive" mockup:**
- Same window chrome style but titled "Inbox"
- Fields:
  - From: Scribe
  - Subject: Highlights — The Future of Small Language Models
- Body with section headers (bold), each truncated:
  - **Summary**: 3 bullet points then `...`
  - **Creator's Notes**: 2 lines of show-notes context then `...`
  - **Transcript**: 2 lines of raw transcript then `...`

CSS additions:
- `.workflow`: `display: grid; grid-template-columns: 2fr 3fr; gap: 2rem; align-items: start;` (sent email narrower)
- `.email-mockup`: card-bg, rounded corners (larger radius ~12px), drop shadow
- `.email-chrome`: top bar with border-radius on top corners, three small dots (CSS-only circles using pseudo-elements or spans), muted background
- `.email-field`: flex row with `.email-label` (muted, fixed width) and `.email-value`
- `.email-body`: padding, normal text
- `.email-section-title`: bold, slightly larger, with top border separator between sections
- `.truncated`: muted color for the `...` indicator
- `.workflow-arrow`: a centered `→` between the mockups on desktop (hidden on mobile)
- `@media (max-width: 768px)`: `.workflow` becomes single column, arrow becomes `↓` or hidden

**Step 2: Open in browser and verify**

Check: Two email mockups side by side on desktop. Window chrome dots visible. Fields properly aligned. Truncated content with ellipsis. Stacks on mobile.

**Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add workflow example with email mockups"
```

---

### Task 5: Footer CTA & Final Polish

**Files:**
- Modify: `index.html`

**Step 1: Add the footer CTA band**

Base background, generous padding, centered text slightly larger than body.

```html
<section class="band">
  <div class="band-content cta">
    <p>Interested? Reach out for access to the service email address.</p>
  </div>
</section>
```

CSS: `.cta` centered, `font-size: 1.1rem`, muted color, `padding: 4rem 0`.

**Step 2: Review the full page and fix any visual issues**

Open the page and scroll through all bands. Check:
- Band backgrounds alternate correctly (base, tinted, base, tinted, base)
- Spacing between sections feels consistent
- Dark mode looks good (toggle system theme)
- Mobile layout works (resize to ~375px width)
- Typography hierarchy is clear
- Code elements are readable
- Email mockups are visually distinct from mode cards

Fix any spacing, alignment, or color issues found.

**Step 3: Commit**

```bash
git add index.html
git commit -m "feat: add footer CTA and polish landing page"
```
