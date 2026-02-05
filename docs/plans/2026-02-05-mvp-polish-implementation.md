# MVP Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Scribe demo-ready with customizable summary modes and a landing page for onboarding.

**Architecture:** Add two new tags (`highlights`, `digest`) to existing tag_configs.json, change emailer default, and create a static GitHub Pages landing page.

**Tech Stack:** JSON config, Python (pydantic-settings), HTML/CSS

---

## Task 1: Add `highlights` tag to tag_configs.json

**Files:**
- Modify: `frontend/frontend/config/tag_configs.json`

**Step 1: Edit tag_configs.json to add highlights tag**

Add the `highlights` entry to the `tags` object:

```json
"highlights": {
  "api_endpoint": "http://10.100.2.50:1234/v1",
  "model": "openai/gpt-oss-20b",
  "api_key_ref": null,
  "system_prompt": "Extract the key points from this transcription as a concise bullet-point list. Focus on main ideas, notable facts, and actionable takeaways."
}
```

**Step 2: Verify JSON is valid**

Run: `python -c "import json; json.load(open('frontend/frontend/config/tag_configs.json'))"`
Expected: No output (success)

**Step 3: Commit**

```bash
git add frontend/frontend/config/tag_configs.json
git commit -m "feat: add highlights tag for bullet-point summaries"
```

---

## Task 2: Add `digest` tag to tag_configs.json

**Files:**
- Modify: `frontend/frontend/config/tag_configs.json`

**Step 1: Edit tag_configs.json to add digest tag**

Add the `digest` entry to the `tags` object (same prompt as `kindle`):

```json
"digest": {
  "api_endpoint": "http://10.100.2.50:1234/v1",
  "model": "openai/gpt-oss-20b",
  "api_key_ref": null,
  "system_prompt": "Summarize the following podcast subscription. Pay special attention to main topics, questions asked and hot takes or counter-intuitive opinions."
}
```

**Step 2: Verify JSON is valid**

Run: `python -c "import json; json.load(open('frontend/frontend/config/tag_configs.json'))"`
Expected: No output (success)

**Step 3: Commit**

```bash
git add frontend/frontend/config/tag_configs.json
git commit -m "feat: add digest tag for incisive summaries"
```

---

## Task 3: Change emailer default_tag to highlights

**Files:**
- Modify: `emailer/emailer/config.py`
- Modify: `emailer/tests/test_config.py`

**Step 1: Update the failing test first**

In `emailer/tests/test_config.py`, change line 72 from:
```python
    assert settings.default_tag == "email"
```
to:
```python
    assert settings.default_tag == "highlights"
```

**Step 2: Run test to verify it fails**

Run: `cd emailer && python -m pytest tests/test_config.py::test_config_defaults -v`
Expected: FAIL with `AssertionError: assert 'email' == 'highlights'`

**Step 3: Update config.py default**

In `emailer/emailer/config.py`, change line 46 from:
```python
    default_tag: str = "email"
```
to:
```python
    default_tag: str = "highlights"
```

**Step 4: Run test to verify it passes**

Run: `cd emailer && python -m pytest tests/test_config.py::test_config_defaults -v`
Expected: PASS

**Step 5: Run all emailer tests**

Run: `cd emailer && python -m pytest tests/ -v`
Expected: All tests pass

**Step 6: Commit**

```bash
git add emailer/emailer/config.py emailer/tests/test_config.py
git commit -m "feat: change default tag from email to highlights"
```

---

## Task 4: Create landing page HTML

**Files:**
- Create: `landing/index.html`

**Step 1: Create landing directory**

Run: `mkdir -p landing`

**Step 2: Create index.html**

Create `landing/index.html` with the following content:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Scribe - Turn podcasts and videos into readable summaries</title>
  <style>
    :root {
      --bg: #fafafa;
      --text: #222;
      --muted: #666;
      --accent: #2563eb;
      --card-bg: #fff;
      --border: #e5e5e5;
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --bg: #1a1a1a;
        --text: #eee;
        --muted: #999;
        --accent: #60a5fa;
        --card-bg: #2a2a2a;
        --border: #444;
      }
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 2rem 1rem;
      max-width: 800px;
      margin: 0 auto;
    }
    h1 { font-size: 2rem; margin-bottom: 0.5rem; }
    h2 { font-size: 1.25rem; margin: 2rem 0 1rem; color: var(--muted); }
    p { margin-bottom: 1rem; }
    .hero { text-align: center; padding: 2rem 0 3rem; }
    .hero p { color: var(--muted); font-size: 1.1rem; }
    .steps {
      display: grid;
      gap: 1rem;
      margin: 1rem 0;
    }
    .step {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1rem 1.25rem;
    }
    .step-num {
      display: inline-block;
      background: var(--accent);
      color: #fff;
      width: 1.5rem;
      height: 1.5rem;
      border-radius: 50%;
      text-align: center;
      font-size: 0.875rem;
      line-height: 1.5rem;
      margin-right: 0.5rem;
    }
    .sources {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin: 1rem 0;
    }
    .source {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 0.5rem 1rem;
      font-size: 0.9rem;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 1rem 0;
    }
    th, td {
      text-align: left;
      padding: 0.75rem;
      border-bottom: 1px solid var(--border);
    }
    th { color: var(--muted); font-weight: 500; }
    code {
      background: var(--card-bg);
      border: 1px solid var(--border);
      padding: 0.125rem 0.375rem;
      border-radius: 4px;
      font-size: 0.875rem;
    }
    .example {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.25rem;
      margin: 1rem 0;
    }
    .example-label {
      font-size: 0.75rem;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.5rem;
    }
    .example pre {
      white-space: pre-wrap;
      font-size: 0.875rem;
      line-height: 1.5;
    }
    .cta {
      text-align: center;
      padding: 2rem 0;
      color: var(--muted);
    }
  </style>
</head>
<body>
  <div class="hero">
    <h1>Scribe</h1>
    <p>Turn podcasts and videos into readable summaries</p>
  </div>

  <h2>How it works</h2>
  <div class="steps">
    <div class="step">
      <span class="step-num">1</span>
      Email a YouTube or podcast URL to the service
    </div>
    <div class="step">
      <span class="step-num">2</span>
      Receive a transcription and summary within minutes
    </div>
    <div class="step">
      <span class="step-num">3</span>
      Optionally specify a mode for tailored output
    </div>
  </div>

  <h2>Supported sources</h2>
  <div class="sources">
    <span class="source">YouTube videos</span>
    <span class="source">Apple Podcasts</span>
    <span class="source">Direct audio URLs (.mp3, .m4a)</span>
  </div>

  <h2>Available modes</h2>
  <table>
    <thead>
      <tr>
        <th>Mode</th>
        <th>How to use</th>
        <th>What you get</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Default</td>
        <td>Just send the URL</td>
        <td>Bullet-point highlights</td>
      </tr>
      <tr>
        <td>Recipe</td>
        <td>Include <code>recipe</code> in subject</td>
        <td>Ingredients + steps</td>
      </tr>
      <tr>
        <td>Digest</td>
        <td>Include <code>digest</code> in subject</td>
        <td>Incisive analysis with hot takes</td>
      </tr>
    </tbody>
  </table>

  <h2>Example output</h2>
  <div class="example">
    <div class="example-label">Sample highlights summary</div>
    <pre>Key points from "The Future of AI" podcast:

• Large language models are becoming commoditized, with open-source alternatives approaching proprietary performance levels

• The real competitive advantage is shifting to data quality and domain-specific fine-tuning

• Multimodal capabilities (text, image, audio) will be table stakes within 2 years

• Enterprise adoption is accelerating but governance frameworks are lagging behind

• The hosts predict consolidation in the AI tooling space by end of 2026</pre>
  </div>

  <div class="cta">
    <p>Interested? Reach out for access to the service email address.</p>
  </div>
</body>
</html>
```

**Step 3: Verify HTML renders**

Run: `open landing/index.html` (on macOS) or open in browser manually
Expected: Clean landing page with all sections visible

**Step 4: Commit**

```bash
git add landing/index.html
git commit -m "feat: add static landing page for GitHub Pages"
```

---

## Task 5: Add .nojekyll for GitHub Pages

**Files:**
- Create: `landing/.nojekyll`

**Step 1: Create .nojekyll file**

Run: `touch landing/.nojekyll`

This tells GitHub Pages to serve the HTML directly without Jekyll processing.

**Step 2: Commit**

```bash
git add landing/.nojekyll
git commit -m "chore: add .nojekyll for GitHub Pages"
```

---

## Task 6: Update .gitignore for landing directory

**Files:**
- Check: `.gitignore`

**Step 1: Verify landing/ is not ignored**

Run: `git check-ignore landing/index.html || echo "not ignored"`
Expected: "not ignored"

If ignored, remove the relevant line from .gitignore.

**Step 2: Skip commit if no changes needed**

---

## Summary

After completing all tasks:

1. **Tags available:** `highlights` (default), `recipe`, `digest`, `kindle`
2. **Emailer behavior:** Emails without a tag keyword default to `highlights` mode
3. **Landing page:** Ready at `landing/index.html` for GitHub Pages deployment

**To deploy landing page:**
1. Push branch to remote
2. In GitHub/Forgejo repo settings, configure Pages to serve from `landing/` folder on main branch
   (Or create a separate repo for the landing page if preferred)
