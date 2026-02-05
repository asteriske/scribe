# Landing Page Redesign

## Goal

Redesign the Scribe landing page to better showcase the service through real workflow examples, detailed mode descriptions, and a more polished visual presentation.

## Design Decisions

- **Aesthetic:** Modern editorial (Stripe/Linear style) — clean typography, generous whitespace, subtle gradients
- **Layout:** Full-width alternating bands (tinted/base backgrounds) creating visual rhythm while keeping all content in a single scroll
- **Email mockups:** Styled HTML/CSS cards that look like email compose/receive windows (no screenshots or images)
- **Modes shown:** Highlights (default), Recipe, Digest — Kindle omitted as it's a personal routing feature
- **Workflow example:** One detailed highlights example with truncated sections (ellipsis after a few lines per section)
- **Tech:** Pure HTML/CSS, no JavaScript, dark mode via `prefers-color-scheme`

## Page Structure

### Band 1: Hero (base background)

- "Scribe" title, large
- Tagline: "Turn podcasts and videos into readable summaries"
- One-liner value prop: "Email a link. Get a transcript and AI summary back in minutes."
- Subtle gradient transition into the next band

### Band 2: How It Works (tinted background)

Three steps laid out horizontally (stacking on mobile):

1. **Send** — "Email a YouTube or podcast link to Scribe"
2. **Choose a mode** — "Add a keyword like `recipe` or `digest` to the subject line — or send with any subject for the default highlights mode"
3. **Receive** — "Get back a structured summary, creator's notes, and full transcript"

Each step has a number badge. The middle step includes a small inline example like `Subject: recipe` to make mode selection concrete.

### Band 3: Modes (base background)

Three cards side by side (stacking on mobile), one per mode:

**Highlights (Default)**
- Trigger: "Just send a link — no keyword needed"
- Description: Extracts key points as a concise bullet-point list. Focuses on main ideas, notable facts, and actionable takeaways. The go-to mode for most content.
- Sample snippet: 3-4 realistic bullet points

**Recipe**
- Trigger: "Add `recipe` to your subject line"
- Description: Extracts ingredients with amounts and step-by-step cooking instructions. Perfect for video recipes you want to save and actually cook from.
- Sample snippet: A couple ingredients and a step or two

**Digest**
- Trigger: "Add `digest` to your subject line"
- Description: An opinionated analysis that highlights main topics, interesting questions raised, and counter-intuitive takes. For when you want more than just the facts.
- Sample snippet: A couple lines of analytical summary

Each card has a subtle accent-color top border for definition.

### Band 4: See It In Action (tinted background)

Two styled email mockups side by side (stacking on mobile):

**"You send" (narrower, left/top)**
- Styled as a compose window
- To: scribe@example.com
- Subject: (casual or blank — reinforces no keyword = highlights mode)
- Body: A YouTube URL, nothing else

**"You receive" (wider, right/bottom)**
- Styled as a received message
- From: Scribe
- Subject: "Highlights — The Future of Small Language Models"
- Body with clear section headers, each truncated after 2-3 lines:
  - **Summary** — Bullet-point highlights, then `...`
  - **Creator's Notes** — Show-notes-style context, then `...`
  - **Transcript** — Raw transcript text, then `...`

Mockups have light drop shadows and rounded corners, floating above the tinted band. Connected by a subtle arrow or visual indicator on desktop.

### Band 5: Footer CTA (base background)

Centered text, slightly larger than body copy: "Interested? Reach out for access to the service email address."

Generous vertical padding to feel intentional.

## Visual Design Details

- **Max content width:** ~960px (up from 800px)
- **Fonts:** System font stack (same as current)
- **Colors:** Current accent blue (#2563eb / #60a5fa dark) with a tinted band color (soft blue-gray in light mode, deeper neutral in dark mode)
- **Dark mode:** Maintained via `prefers-color-scheme` media query
- **Cards:** Subtle border or shadow, rounded corners, accent-color top border on mode cards
- **Email mockups:** Rounded container with a mock title bar (dots or minimal chrome), field labels in muted color, body in normal text
- **Responsive:** Three-column grids collapse to single column on mobile, side-by-side email mockups stack vertically

## Files Changed

- `index.html` — Complete rewrite of the landing page

## Out of Scope

- JavaScript interactivity
- External images or assets
- Kindle mode on the public page
- Collapsible/expandable sections
- Navigation bar or multi-page structure
