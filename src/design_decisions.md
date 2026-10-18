# Front-end design decisions

The web front end (`web/`) rebuilt for the new user, staff of the Bern Economic Development Agency, on the template https://github.com/Jesmilan/AI-template. Each entry: the step it belongs to, the decision, why, and the alternatives rejected. Newest at the bottom. Backend decisions stay in `decision.md`.

## DD-01 Step 1 (template analysis): the template is a config-only Vite + React + Tailwind starter

The repository (one commit, "Add files via upload") holds `README.md`, `index.html`, `package.json`, `package-lock.json`, `tailwind.config.js`, `postcss.config.js`, `vite.config.js` and `jsconfig.json`. **There is no `src/` folder**: the components its README describes (`Navbar`, `Hero`, `PromptBox`, `ChatPreview`, `ChatScreen`, `ThemeMenu`, `useTheme`, `useChat`, `askAI`, `siteConfig`, `ui/ai-text-loading`) and the `src/index.css` that holds the light/dark colour values were not uploaded.

What the template does provide:

| Part | Content |
| --- | --- |
| Stack | Vite 5, React 18, Tailwind 3 (PostCSS + autoprefixer), `motion`, `clsx` + `tailwind-merge` (`cn()`), `@/` alias to `src/` |
| Design tokens | `brand` blue scale 50–900 (`brand-600` #3e51c2 is the main blue); semantic colours `ink`, `page`, `surface`, `field`, `card`, `line` read from CSS variables so they switch with the theme; Inter (400/500/600) and JetBrains Mono; shadows `pill` (raised blue buttons), `soft`, `panel` |
| Motion | keyframes `ring` and `breathe` (pulsing logo while thinking), `pop` (source chips), `drift` (background blobs), `fadeUp` |
| Theming | `darkMode: 'class'`, an inline script in `index.html` that reads `localStorage('beda-theme')` before paint; README: light / dark (deep navy, `--page: 11 18 38`) / system menu |
| Look (from the README) | top bar, headline, a rounded "ask" box with the send button inside it, cards, a chat answer card with sources and copy/👍/👎 actions |

Nothing was run from the clone: it has no install scripts beyond `npm install`, and there was no source to run. The clone stays outside the repo and is not modified.

## DD-02 Step 2 (integration): port the design system into the existing Vite app; do not adopt the template's project

The template is a Vite + React app like ours, so there is no build-system conflict, but it ships no code to adopt, and its package versions are older than ours (React 18 vs 19, Vite 5 vs 8). The design tokens, the look described in its README and its file conventions are what can be carried over, so they are ported into `web/`. The nginx static serving, the Dockerfile, the `/api` proxy, `.env` (`VITE_API_BASE`) and the eslint setup stay as they are.

Rejected: replacing `web/` with the template project (downgrades React/Vite, nothing to gain without `src/`); stopping until the missing `src/` is uploaded (the tokens are enough to build the look, and the screens are specific to this tool anyway).

## DD-03 Step 2: Tailwind 4 through `@tailwindcss/vite`, tokens in CSS `@theme`

The template uses Tailwind 3.4 with PostCSS. Installing `tailwindcss@3.4.19` made `npm audit` report a high (`braces`, via `chokidar`/`micromatch`) and a moderate (`postcss-selector-parser`) advisory, fixable only by moving to Tailwind 4. Tailwind 4 (`tailwindcss` + `@tailwindcss/vite` 4.3.3, both declare Vite 8 support) gives 0 advisories, needs no `postcss.config.js`, `tailwind.config.js` or autoprefixer, and keeps tokens in one CSS file. The template's `tailwind.config.js` values are copied 1:1 into `@theme` in `web/src/index.css` (brand scale, semantic colours, font, shadows, keyframes), so its class names (`bg-brand-600`, `text-ink`, `bg-card`, `border-line/10`, `shadow-pill`, `shadow-soft`, `animate-ring`, `animate-fade-up`) work unchanged. The lockfile carries the `linux-*-musl` native builds, and `docker compose build web` on `node:22-alpine` succeeds.

Rejected: Tailwind 3 (audit findings, two config files plus PostCSS); hand-written CSS with the same tokens (the template's whole component vocabulary is Tailwind classes).

## DD-04 Step 2: semantic colours as hex values in `@theme`, dark values overridden under `prefers-color-scheme`

The template's `index.css` with the `R G B` triplets is missing, so the values are new: light uses white cards on a `#f5f7fc` surface with slate ink; dark uses the README's deep navy (`#0b1226` = `11 18 38`) with lighter navy cards. Tailwind 4 mixes opacity with `color-mix`, so the `rgb(var(--x) / <alpha-value>)` indirection the template needed in v3 is not needed; plain hex values in `@theme` are redefined on `:root` in the dark media query.

## DD-05 Step 2: dark mode follows the system; no theme menu, no localStorage, no inline script

The template's Light/Dark/System menu and `useTheme.js` were not in the repo. Agency staff use managed machines where the OS setting is the preference, and the toggle would add a component, a hook, browser storage and an inline pre-paint script for a tool used at work. Tailwind 4's default `dark:` variant is the media query, so `dark:` classes and the token overrides follow the OS. Rejected: rebuilding the three-way menu (code without a user need).

## DD-06 Step 2: Inter self-hosted through `@fontsource-variable/inter`, not Google Fonts

The template loads Inter from `fonts.googleapis.com`. That sends every staff member's IP address to Google on each visit, which public bodies in Switzerland and the EU avoid (nFADP / GDPR; LG München I, 3 O 17493/20). `@fontsource-variable/inter` puts the font files into the build, nginx serves them, and the browser loads only the `latin` subsets it needs. One variable font covers the 400/500/600 weights. JetBrains Mono is dropped: the only monospace text is the build id and request id, for which the system monospace is fine.

## DD-07 Step 2: template dependencies not taken over

`motion` (the chat's typing and pop-in animations; the two animations kept, the busy pulse and the fade-in, are CSS keyframes from the template), `clsx` + `tailwind-merge` (no component here merges caller-supplied class lists; repeated class sets are named component classes instead, DD-08), `autoprefixer`/`postcss` (DD-03). The `@/` alias is not needed: `src/` stays flat with six modules. Added dependencies in total: `tailwindcss`, `@tailwindcss/vite` (dev) and `@fontsource-variable/inter`.

## DD-08 Step 2: repeated class sets as a few component classes

Utilities are used inline as in the template, but sets that repeat across files are named once in `@layer components`: `card`, `field`, `label`, `hint`, `btn` (the template's raised blue pill with `shadow-pill`), `btn-ghost`, `chip`, `tag`, `warn`, `link`, `kicker`. This avoids duplicating 10-class strings in every component (instructions.md: no duplication). Rejected: a React `Button`/`Card` component library (more code for the same result).

## DD-09 Step 3 (layout): agency workspace, not a landing page

The template is a marketing landing page (hero, features, footer links) that turns into a full-screen chat. Staff need a work tool, so: a sticky top bar (logo mark, "Bern Economic Development Agency", product name as `h1`, translucent like the template's navbar), one centred column (`max-w-5xl`, `px-4` = 16px gutter), cards for each step. Dropped: hero headline, feature cards, footer link lists, the chat preview and the chat screen. The footer keeps the domain and index build id.

## DD-10 Step 3 (input): the template's prompt box becomes the business-model box

The primary input is the business model the company sent. It reuses the template's "ask" box shape: a rounded field with the send button inside its bottom-right corner, plus a character counter against the 5000-character limit the API enforces. Labels speak to staff ("Company business model (plain text)", "Draft need card"). Plain text only; the template's `+` attach button is not ported (no file upload in scope). The quick keyword search stays as a second, smaller card. After a draft arrives the page scrolls to the need card, which otherwise opens below the fold.

## DD-11 Step 3 (need card): same editor, numbered needs with their cited sentences

Sector, product and stage on one row (stacked on phones); each need is a row with a number badge, its text, its category and a Remove button, with the business-model sentences it was drafted from quoted under it. The `ignored` sentences (addressed to an AI system) are listed in an amber box above. Behaviour and limits (1–5 needs, ids n1–n5) are unchanged.

## DD-12 Step 3 (results): the confirmed card and coverage first, then groups of lead cards

The results page opens at the top (new searches scroll up; feedback keeps the scroll position) with "New search" and "Download report (PDF)" (link unchanged). A "Search for" card shows sector · product · stage, the `coverage_line`, and the feedback `message` when there is one. Lead groups keep the API's order and label with a count.

## DD-13 Step 3 (lead card): verification first, people beside the evidence

Each lead card shows, top to bottom:

1. Name; parent · host (link to the unit page) · page date · pages indexed; a "May be outdated" badge when `stale`; the `expertise` terms as tags.
2. Two columns on wide screens (`lg`), stacked on phones:
   - left, "Why it matches": the `explanation` (when not null), the needs the lead answers, then each quoted evidence sentence with its need and its full source address as the link text; "Projects, infrastructure and services" (`items`, kind shown as "Project" or "Infrastructure or service"); "About" (`summary`).
   - right, "People and contacts": one card per person.
3. The feedback chips, separated by a rule.

The source address is printed (not just "Source") so staff see which site and page a quote comes from before clicking. Evidence sits next to the people so a call list can be checked against the quotes without scrolling.

## DD-14 Step 3 (people): one card per person, contact badge, every value linked to where it was read

Each person shows titles + name, a "Contact person" tag when `contact`, the `function`, the `affiliation`, then a row of links: email (`mailto:`), phone (`tel:`), "Profile" (`profile_url`, when present) and "Source" (`source_url`, always). A person's own matching quote (`reason`) is shown under them in the same quote style as the lead's evidence. A lead with no people says so in one line.

## DD-15 Step 3: the introduction-request flow removed

The agency is now the user, so the form, the per-lead checkboxes and `Introduction.jsx` are deleted. `POST /api/requests/{id}/introduction` is no longer called by the front end.

## DD-16 Step 4 (link safety): one `Ext` component, http(s) only, fail loudly

Every external link goes through `Ext` in `parts.jsx`: `target="_blank" rel="noopener noreferrer"`, an arrow and a screen-reader "(opens in a new tab)". A URL that is not `http(s)://` throws during render. React 19's `createRoot(..., { onUncaughtError })` in `main.jsx` replaces the page with the error text, so a bad URL from the API is visible instead of a blank page (checked in the browser with a `javascript:` URL). Rejected: rendering such a URL as plain text (a silent fallback that hides a backend bug).

## DD-17 Step 4: `mailto:`/`tel:` only from values that look like an email or phone number

`mailto:` is built only when the value matches `local@domain.tld` with no spaces or `<>"`; `tel:` only when the value is digits, spaces and `+()./-` (6–20 characters), and the href keeps only digits and `+`. Any other value is shown as plain text: these fields are copied from web pages, and the rule asked for links only from values that look right. This is display of what the page said, not a repair.

## DD-18 Step 4: errors and the busy state in a fixed bottom stack

Feedback chips sit at the bottom of long result pages, so a status line or error at the top of the page would be off screen. A fixed bottom stack shows the busy pill (the template's pulsing `ring` animation, only with `motion-safe`) and the error card (`role="alert"`, the HTTP status, `detail`, `request_id`, a Dismiss button, scrolls when long). `src/api.js` is unchanged: one fetch wrapper, non-2xx throws with `detail` and `requestId`.

## DD-19 Step 4: accessibility

Every input has a visible or `sr-only` label; need rows name their number ("Category for need 2", "Remove need 2"); sections and lead cards are labelled by their headings; feedback chips are a labelled `group`; focus shows a 2px brand outline (the business-model box shows a ring on the whole box); muted text uses `ink` at 60% opacity or more (about 4.7:1 on white); placeholders are lighter.

## DD-20 Step 5 (verification): browser check with a temporary mock outside the repo

The API was not running (it is being changed in parallel), so the screens were checked with `npm run dev` under a throw-away Vite config in the session scratchpad that serves the fictional sample (`search_result.sample.json`) for `/api/*`. Nothing mock-related is in `web/`. Checked: draft → need card with cited and ignored sentences → search → lead cards with people, quotes and links; a feedback chip returns the `message`; a 500 shows `detail` and `request_id`; at 390px wide the page has no horizontal scroll; all external links carry `target="_blank" rel="noopener noreferrer"`; no console warnings.

## DD-21 Polish step (colour scheme): the template's tokens, light mode as the calm default look

Request: bring the front end closer to the template's look ("trusty interface feeling"). The brand scale and the six semantic tokens keep the template's names and roles. The values are tuned for a work tool. Light mode: a cool off-white page (`247 248 252`), white cards, `241 243 249` soft panels, a navy-tinted ink (`20 27 52`) instead of pure black, and borders drawn as ink at 10–15% opacity. Dark mode: the README's navy page (`11 18 38`) with slightly lighter navy cards. Light mode uses a grey page under white cards rather than the landing page's white-on-white, so a page with many cards keeps its structure without heavy borders. Colour is used sparingly: brand blue only for primary buttons, links, source chips, quote rules and the "Contact person" tag. Expertise and item kinds use neutral tags, and only staleness uses amber. Rejected: brand-filled tags everywhere (too loud and less credible), pure white page (cards blur into it).

## DD-22 Polish step (theme menu): Light / Dark / System added; supersedes DD-05

The README's theme menu is now in the top bar (`Theme.jsx`). It is a three-button group with `aria-pressed` state and icon buttons with labels, so it stays usable at phone width. It defaults to System. Why it is worth adding now: staff share their screen or print in meetings with companies, and they may want light mode on a dark OS, or the reverse. Dark mode is class-based again, as in the template (`@custom-variant dark` on `.dark`). A small inline script in `index.html` applies the choice before the first paint, as the template does, so a reload shows no light/dark flash. The stored choice (`localStorage` key `navigator-theme`) is a per-browser convenience only. Every read and write is wrapped in try/catch: if storage is blocked, the page follows the system, and a choice made in the menu lasts for the visit. "System" removes the key, and the page listens for OS theme changes. Rejected: a dropdown menu like the template's (needs focus management for the same three choices); keeping system-only (DD-05; staff asked for the template's feel, and this menu is part of it).

## DD-23 Polish step (typography): Inter 400/500/600, one type scale, tabular numbers

Only the template's three weights are used: 400 body, 500 labels, buttons, kickers and tags, 600 headings and names. There is no 700; the error title is a semibold paragraph. The scale is a 15px body with relaxed leading; 12px uppercase `kicker` labels with wide tracking for section names ("Why it matches", "People and contacts", "Feedback"); 18px semibold lead names; 24–30px semibold, tight-tracked page title. `tabular-nums` is applied to the character counter, page dates and page counts, group counts, phone numbers and the build id, so figures line up. Page dates read as "3 Nov 2025" (en-GB, UTC so the date never shifts by a day).

## DD-24 Polish step (motion): the template's keyframes, short, and off under reduced motion

All five template keyframes are in `@theme` with the template's timings:
- `fadeUp`: the hero, the need card, the results header, lead cards (staggered 80 ms) and quotes;
- `pop`: source chips, delayed 150 ms after their quote;
- `ring` + `breathe`: the logo mark while an API call runs, and the dot in the status pill;
- `drift`: one large, blurred, low-opacity brand glow behind the top of the page (`fixed`, `pointer-events-none`, `aria-hidden`, clipped so it cannot cause horizontal scroll);
- `pill` shadow: primary buttons, with a 2% press scale.

Hover changes are 150 ms colour transitions. One global rule under `prefers-reduced-motion: reduce` turns every animation and transition off. Smooth scrolling is CSS-only (`scroll-behavior` under `no-preference`), so the scroll to the need card is instant for those users too. Animations play only on mount: after feedback re-ranks, cards keep their keys and do not replay. Rejected: the template's typing-word-by-word and shimmering "Thinking…" text (the `motion` package; a results list does not stream, and moving text reads as a gimmick to staff checking evidence).

## DD-25 Polish step (loading state): the status says what Apertus is doing

`run(label, fn)` now takes the sentence shown while the call runs:
- "Apertus is drafting the need card from the business model…"
- "Searching research units in Bern and checking each explanation against its sources…"
- "Re-ranking the leads with your feedback…"

The pill sits at the bottom of the screen (`role="status"`, so screen readers announce it), next to the pulsing logo. Buttons are disabled while it runs. Rejected: skeleton cards (the search screen stays visible during the call, and a skeleton would claim a layout the result may not have, for example no leads).

## DD-26 Polish step (components): top bar, the rounded "ask" box, the pill search field

These are recreated from the README. The top bar is translucent with backdrop blur and holds the compass logo mark (an inline SVG, raised with `shadow-pill`), the agency kicker (hidden on phones, where the product name wraps to two lines instead of truncating) and the theme group. The page opens with a hero block ("New enquiry" kicker, title, one-line explanation) and the template's "ask" box: a rounded-3xl white panel with `shadow-panel`, a borderless textarea, and a footer row with the character counter and the "Draft need card" pill button inside the box. Quick search is a single-line pill field with the "Search" button inside it. The need card is labelled "Drafted by Apertus" so staff know its source. Rejected: "Step n of 3" labels (quick search skips the need card, so the numbering would be wrong half the time).

## DD-27 Polish step (verifiability): source chips tied to every claim; supersedes the printed address in DD-13

Every claim now ends in a source chip: a small outlined pill showing the host and the last page folder (`artorg.unibe.ch › group_members`), with the full URL on hover (`title`) and "Source:" for screen readers. That is enough to tell pages apart at a glance; the full address took several lines on phones. Each quote has a brand rule on its left, the quoted sentence, then a caption row ("For: <need>" + source chip). The quote is thus visually tied to its own link, for the lead's evidence and for a person's own quote alike. The lead header shows the unit's source chip, "Page dated …", "N pages indexed" and the amber "May be outdated" badge in one row. Each person card ends with its source chip ("listed on this page"), after email, phone and "Profile".

## DD-28 Polish step (hierarchy): reading order in a lead card

The order is: name → parent → provenance row → "Why it matches" (explanation in larger text, needs answered, quotes) → "Fields of expertise" (now a labelled section instead of tags under the title) → "Projects, infrastructure and services" (kind as a neutral tag before each link) → "About". People sit in a soft grey side panel that keeps its content height (it no longer stretches to the card height when empty). The feedback chips sit behind a "Feedback" kicker under a rule. The results header is "Results for" + company line + coverage line in a soft panel, with the feedback message in a brand-tinted panel. Group headings carry a count badge.

## DD-29 Polish step (verification)

The same temporary mock outside the repo (now with a 1.5 s delay on search so the loading state can be seen) was used in Chrome. Checked:
- light and dark themes via the new menu; System follows the OS and clears the stored key; a stored choice is applied before paint on reload;
- the drafting and searching status pills;
- need card, results and person cards in both themes;
- at 390px wide (iframe), no horizontal scroll before or after results, and the title wraps instead of truncating;
- the error card in light mode;
- no console warnings.

The built CSS contains the reduced-motion rule and the `.dark` token block. The OS reduced-motion setting itself could not be toggled from the browser tools.
