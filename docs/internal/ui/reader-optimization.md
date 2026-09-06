# Reading App — Design Recommendations

---

## 1. Font

| Role | Font | Weight |
|------|------|--------|
| Body text | Bookerly | Light (300) |
| Chapter titles / headings | Bookerly | Regular (400) |
| UI / labels | Inter | Regular |

> Bookerly was purpose-built for screen reading: large x-height, refined serifs, and optimized kerning. Use it as the default with no user-facing alternative needed at launch.

---

## 2. Body Type

| Property | Value |
|----------|-------|
| Font size | `18px` (`1.125rem`) |
| Line height | `1.5` |
| Letter spacing | `0.01em` |
| Word spacing | default |
| Paragraph spacing | `1.5em` bottom margin |

> Always use `rem` units so user browser font preferences are respected. Never go below `16px` (triggers iOS Safari zoom on inputs).

---

## 3. Column & Margins

| Property | Value |
|----------|-------|
| Max column width | `65ch` (~66 CPL) |
| Side margins | `min(8vw, 80px)` |
| Text alignment | Left-aligned (no full justify) |
| Hyphenation | On |

> 66 characters per line is the evidence-backed optimal. Left-align — full justification creates spacing rivers that hurt all readers, especially dyslexic users.

---

## 4. Pagination

- **Default mode:** Paginated (no scrolling). Each page is a fixed, stable canvas.
- **Page turn:** Left `‹` / Right `›` arrow buttons on page edges, plus keyboard arrows.
- **Animation:** Current page slides out to the left, next page slides in from the right. `150–200ms`, `ease-in-out`. No skeuomorphic curl.
- **Layout stability:** Text must occupy the same position on every page (no reflow mid-read). Recalculate pagination only on font-size change.

> Fixed pages preserve spatial memory — the brain remembers *where* on a page information appeared, which aids recall. Scrolling destroys this.

---

## 5. Color & Contrast

| Element | Value |
|---------|-------|
| Background | `#FAF6EC` (warm cream) |
| Body text | `#2C2C2C` |
| Contrast ratio | ≥ 8.5:1 ✓ |
| UI chrome | `#E8E2D4` |

### Rules
- Minimum contrast: **4.5:1** (WCAG AA). Target **7:1** for body text.
- Add an **auto warm-shift after 8pm** (shift background toward amber, reduce brightness) to protect sleep and memory consolidation.

---

## 6. Bimodal — Read While Listen

- **Feature:** Audio narration plays while the corresponding text is highlighted in sync.
- **Highlight style:** Word-level soft gold highlight with a lighter sentence-level band for context.
- **Default playback speed:** `1.0×`
- **Recommended speeds:** `1.0×` · `1.1×` · `1.2×` · `1.3×` · `1.4×` · `1.5×`
- **Speed warning:** Display a soft tooltip above `1.3×`: *"Retention may decrease above 1.5×."*
- **Toggle:** Off by default. Persistent per-book user preference.
- **Granularity:** Word-level sync primary; fall back to sentence-level if word timestamps unavailable.

> Simultaneous audio + highlighted text reliably improves comprehension, especially for complex non-fiction and L2 readers. Keep it optional for fluent readers — it can cause cognitive overload on easy material.

---

## 7. Session Timer

- **Duration:** 25 minutes.
- **Display:** Countdown in the top-right corner, always visible.
- **On completion:** Gentle full-screen overlay — *"Nice work. Take a 5-minute break away from the screen."* One-tap to dismiss and continue or start a break.
- **Do not:** Force a stop. The timer is a nudge, not a lock.

> Focused reading sessions of 25–50 minutes followed by off-screen breaks support memory consolidation. Rigid interruptions increase frustration — keep it advisory.

---

## 8. What to Avoid

| Avoid | Why |
|-------|-----|
| **Scrolling as default** | Breaks spatial memory; hurts recall for text >500 words |
| **Sans Forgetica / "memory fonts"** | Multiple rigorous replications found zero benefit; some show harm |
| **Bionic Reading (bold half-words) as default** | No peer-reviewed evidence of improved speed or retention |
| **RSVP speed-reading mode** | Eliminates regressions the brain needs; comprehension drops 20–40% above 350 WPM |
| **Full justification** | Creates spacing rivers; harms dyslexic readers |
| **Pure white background `#FFFFFF`** | Higher glare and fatigue than cream; no comprehension benefit |
| **Pure black text `#000000`** | Excessive contrast causes halation; soften to `#2C2C2C` |
| **Playback >1.5× by default** | Retention degrades; long-term recall significantly worse |
| **Forced Pomodoro lockouts** | Rigid breaks increase frustration without memory benefit vs self-regulated breaks |
| **Blanket bold/emphasis** | Only works via the Von Restorff isolation effect — emphasizing everything emphasizes nothing |
| **OpenDyslexic as a "proven" accessibility feature** | No reading-speed or accuracy improvement in controlled studies; offer as a preference only |

---

*Sources: Delgado et al. 2018 meta-analysis (n=171,055); Clinton 2019; Geller et al. 2020; Valentini et al. 2024; WCAG 2.2; Amazon Bookerly design notes.*
