# MVP Polish Design

Make Scribe presentable for demos to non-technical users and potential investors.

## Goals

- Allow users to customize summary output via email subject keywords
- Provide onboarding through a static landing page
- Keep implementation minimal - leverage existing tag/prompt system

## Summary Modes

Three tags at launch:

| Tag | Trigger | Prompt |
|-----|---------|--------|
| `highlights` | Default (no keyword needed) | Extract the key points from this transcription as a concise bullet-point list. Focus on main ideas, notable facts, and actionable takeaways. |
| `recipe` | `recipe` in subject | (existing) Ingredients list + cooking steps |
| `digest` | `digest` in subject | Summarize the following podcast subscription. Pay special attention to main topics, questions asked and hot takes or counter-intuitive opinions. |

### Implementation

1. Add `highlights` tag to `frontend/frontend/config/tag_configs.json`
2. Add `digest` tag to `frontend/frontend/config/tag_configs.json`
3. Keep existing `kindle` and `recipe` tags
4. Change emailer's `default_tag` from `"email"` to `"highlights"` in config

## Landing Page

Static HTML page hosted on GitHub Pages.

### Hosting

- Single `index.html` file with inline CSS
- No build step, no Jekyll
- Deployed via GitHub Pages (new repo or `docs/` folder)

### Content Sections

1. **Hero** - "Turn podcasts and videos into readable summaries"

2. **How it works** - Three-step flow:
   - Email a YouTube or podcast URL to the service
   - Receive a transcription and summary within minutes
   - Optionally specify a mode for tailored output

3. **Supported sources**:
   - YouTube videos
   - Apple Podcasts
   - Direct audio URLs (.mp3, .m4a, etc.)

4. **Available modes** - Table:
   | Mode | How to use | What you get |
   |------|-----------|--------------|
   | Default | Just send the URL | Bullet-point highlights |
   | Recipe | Include "recipe" in subject | Ingredients + steps |
   | Digest | Include "digest" in subject | Incisive analysis with hot takes |

5. **Example output** - Sample summary showing what users receive

6. **Getting access** - Soft CTA directing users to contact for the email address

### Design

Clean, minimal. Consider Pico CSS or Simple.css for polish without complexity, or hand-written CSS.

## Out of Scope

- User accounts or authentication
- Web form for URL submission
- Dynamic content on landing page
- Changes to email processing flow

## End-to-End Flow

1. User visits GitHub Pages site, learns how the service works
2. Admin shares the email address personally
3. User emails a URL, optionally with "recipe" or "digest" in subject
4. User receives a summary tailored to the mode (defaulting to highlights)
