# Reading and listen tools for learning

Asked: what actually helps people learn from reading and from listen-while-reading, according to primary sources, and how that lines up with Arsenal's Academy reader. Compared `docs/internal/helper/reader-recommendations.md` against `ReaderView.tsx` and `academy.css`, then against the papers and specs those recommendations invoke. Date: 2026-08-30.

This is a design note for engineers, not a literature dump. If a claim in our docs could not be traced to a paper or spec, it is marked as such.

## Verdict

The reader is on solid ground for the things that matter most at the layout layer. Paginated pages, left-aligned text, cream paper with high contrast, 18px body, line-height 1.5, narration off until the user asks, and an advisory session nudge are the right defaults. Those choices match WCAG presentation rules, the scrolling-versus-pages literature, and how Kindle and Apple Books actually ship. The avoid-list is also mostly right: Sans Forgetica, Bionic Reading as default, RSVP, full justify, and OpenDyslexic-as-proven are marketing. Keep them out of the default path.

The recommendations oversell three ideas that sound scientific and are not. First, simultaneous audio plus highlighted text does not "reliably" improve comprehension for fluent L1 readers going at their own pace. Clinton-Lisell's 2023 meta-analysis found a trivial overall benefit, and that benefit vanished when reading was self-paced. Second, a CSS amber shift after 8pm is not melatonin science. Chang, Aeschbach, Duffy, and Czeisler measured LED e-readers versus print books, not cream versus slightly yellower cream. Third, a 25-minute timer does not "support memory consolidation." Consolidation is a sleep story. The timer is a focus nudge. Call it that.

The biggest gap is not karaoke highlighting. It is user control. Every serious product in this space, Kindle, Apple Books, Immersive Reader, Voice Dream, lets the reader change font size. WCAG 1.4.4 requires resize to 200 percent. We ship a fixed 1.125rem serif with no size control, no theme picker, and a font we do not even bundle. Bookerly Light 300 is a brand preference sitting on Georgia. That is fine as a default. It is not fine as the only option, and it is not "purpose-built for screen reading" in any peer-reviewed sense. Amazon said that on a product page.

Implementation drift is real and concentrated in playback. The docs cap speed at 1.5x and warn above 1.3x. The app offers 1.75x and 2x and warns only above 1.5x. Recent lecture-speed work is kinder to 1.5x than our docs claimed, and harsher on treating 2x as free. For listen-while-reading specifically, 2x is a bigger bet than the video-lecture papers justify, because the eyes have to keep up with the voice. Hyphenation is recommended on and implemented off. Column width is specified as 65ch and implemented as a two-page spread that fills the window. The page-turn animation is 320ms, not 150 to 200ms.

`Valentini et al. 2024` is a ghost citation. I could not find that paper. The 2024 result that matches the Bionic Reading claim is Snell, one author, Acta Psychologica.

## Docs vs app

| Recommendation | Implemented? | Evidence says |
|---|---|---|
| Bookerly Light 300 body, Regular 400 headings, Inter UI, no font picker | Partial. Stack is `'Bookerly', 'Iowan Old Style', Georgia, 'Times New Roman', serif`. Bookerly is licensed and not bundled. Reader chrome is Arial Narrow, not Inter. Weight 300/400 matches. No picker. | Keep a serif default. Drop the "no alternative at launch" line. Font size and a small font menu have more evidence than Bookerly itself. |
| 18px / 1.125rem, line-height 1.5, letter-spacing 0.01em, paragraph margin 1.5em, rem units, never below 16px | Yes for type metrics. The 16px floor is documented as iOS zoom insurance. | Line-height 1.5 matches WCAG 1.4.8 and 1.4.12. 18px is a reasonable default. The iOS zoom rule is about form controls, not body copy. |
| Max 65ch, margins `min(8vw, 80px)`, left-align, hyphenation on | Partial. Left-align yes. Hyphenation is `hyphens: none`. Margins are `min(6vw, 64px)`. No 65ch cap. Two CSS columns fill the viewport. | 65ch is in the right band, not "the" optimum. Dyson found 55 CPL better for comprehension than 100. WCAG caps width at 80 characters. Left-align is correct. Hyphenation is a typesetting choice, not a learning effect. |
| Paginated default, arrows + keyboard, 150 to 200ms slide, no curl, reflow only on font-size change | Mostly. Paginated, overflow hidden, arrows, keyboard. Flip is a 320ms hairline sweep. ResizeObserver reflows on viewport change, which is required. Reduced motion snaps. | Pagination as default is the strongest layout claim we have. Animation duration is taste. |
| Paper `#FAF6EC`, ink `#2C2C2C`, chrome `#E8E2D4`, contrast >= 8.5:1, WCAG AA 4.5 / target 7:1, auto warm-shift after 8pm | Colors match. Computed contrast is about 12.9:1, not 8.5. Warm mode (`hour >= 20` or `< 6`) ambers paper to `#f3e6c9`. Spoken-already words use `#8a8475` at about 3.45:1, which fails AA. | Cream + high contrast: keep. 8pm CSS hue: keep as comfort, drop the sleep claim. Fix muted "already read" contrast. |
| Word gold + sentence band, default 1.0x, speeds 1.0 to 1.5 in 0.1 steps, warn above 1.3x with "Retention may decrease above 1.5x", off by default, word-level then sentence fallback | Partial. Off until play. Word-level when timings exist, else simulated 165 WPM. Speeds `[0.75, 1, 1.25, 1.5, 1.75, 2]`. Warns only above 1.5x, different copy. Auto page-turn follows speech. | Optional bimodal: keep. "Reliably improves comprehension": drop. Offer 0.75x. Cap the default path at 1.5x. 2x can exist behind a stronger warning. |
| 25-minute countdown, overlay nudge, not a lock | Yes. `SESSION_SECONDS = 25 * 60`. Overlay copy claims consolidation. Timer starts paused. | Advisory timer: keep. Consolidation language: change. 25 minutes is Pomodoro folklore, not a memory threshold. |
| Avoid scrolling default, Sans Forgetica, Bionic default, RSVP, full justify, `#FFFFFF` / `#000000`, playback >1.5x default, forced Pomodoro lockouts, blanket bold, OpenDyslexic as proven | Followed as defaults. App still exposes 1.75x and 2x. | Avoid-list holds except the 1.5x cliff and the lockout claim. See below. |

## Technique by technique

### Font

**What we recommend.** Bookerly Light for body, Regular for headings, Inter for UI. No user-facing alternative at launch. "Purpose-built for screen reading."

**What the source actually says.** Amazon's 2015 Paperwhite listing calls Bookerly "an exclusive font crafted from the ground up for reading on digital screens" and says the typesetting engine, hyphenation, justification, kerning, ligatures, "helps you read faster with less eyestrain." That is first-party marketing. I found no independent trial of Bookerly versus Georgia or Literata on comprehension. Dalton Maag designed it for Kindle. "Large x-height, refined serifs, optimized kerning" is not in a paper. Inter is a UI face. Nothing about Inter improves learning from prose.

**Products.** Kindle ships Bookerly as default and still offers a font menu. Apple Books offers Original, Palatino, and others, plus bold and spacing sliders. Immersive Reader offers Calibri, Comic Sans, and Sitka. Voice Dream includes OpenDyslexic as an option.

**Keep / change / drop.** Keep a serif default with open counters. Georgia or Iowan Old Style is what users actually see today. Change: ship a licensed face or stop naming Bookerly as if it were loaded. Drop "no alternative at launch." A size control matters more than which serif.

### Body type

**What we recommend.** 18px (1.125rem), line-height 1.5, letter-spacing 0.01em, paragraph spacing 1.5em, rem units, never below 16px because iOS zooms.

**What the source actually says.** WCAG 2.2 SC 1.4.8 (AAA) asks for line spacing at least space-and-a-half and paragraph spacing at least 1.5 times the line spacing, as a user-available mechanism, not a required authored value. SC 1.4.12 (AA) requires that content still works if the user sets line-height to 1.5, paragraph spacing to 2em, letter-spacing to 0.12em, and word-spacing to 0.16em. Our authored 0.01em tracking is far below that override. That is fine if the layout does not break when a user agent applies 1.4.12. I did not test that. The 16px iOS rule is Safari auto-zoom on focused form controls with `font-size` under 16px. Body copy at 18px is unrelated.

Zorzi et al. 2012 found extra-large letter spacing improved speed and accuracy for Italian and French children with dyslexia, on the fly, by reducing crowding. That is a stronger spacing result than 0.01em of tracking. Replications are mixed. Treat extra spacing as an option, not the default.

**Products.** Kindle, Apple Books, and Immersive Reader all expose size. Immersive Reader has a spacing toggle. Apple Books has character, word, line, and margin sliders.

**Keep / change / drop.** Keep 18px / 1.5 / rem. Change: add a size control, and make sure 1.4.12 overrides do not clip columns. Drop the iOS-zoom justification for body text.

### Column and margins

**What we recommend.** Max 65ch, about 66 CPL. Left-aligned. Hyphenation on. "66 characters per line is the evidence-backed optimal. Full justify creates rivers that hurt all readers, especially dyslexic users."

**What the source actually says.** Dyson and Haselgrove 2001 compared 25, 55, and 100 CPL on screen. Medium length, 55 CPL, produced the highest comprehension and was read faster than short lines. 100 CPL was faster than 55 but worse for comprehension. They did not test 66. Bringhurst's print advice of roughly 45 to 75 characters is craft tradition, not a trial. WCAG 1.4.8 says width no more than 80 characters, and text is not justified. That is an accessibility ceiling and a no-justify rule, not an optimum of 66.

I did not find a named RCT that isolates "rivers harm dyslexic readers." The no-justify rule is still correct. Uneven word spacing is a documented readability problem, and WCAG forbids full justify as a required presentation.

**Products.** Immersive Reader exposes column width as a first-class control. Kindle's 2015 typesetting engine went the other way: hyphenation plus justification to even the rag. Apple Books lets the user turn Justify Text on or off. We should not copy Amazon's justify.

**Keep / change / drop.** Keep left-align. Keep a measure in the 50 to 75 character band. Change: stop calling 66 "the" optimum. The two-page spread already produces something near Dyson's 55 on a laptop, which is luck, not spec. Hyphenation can go on for a tighter rag. It is not a learning feature. Drop any implication that 65ch was measured.

### Pagination

**What we recommend.** Paginated default. Fixed canvas. Spatial memory. "Scrolling destroys this." Reflow only on font-size change. 150 to 200ms slide, no curl.

**What the source actually says.** This is the recommendation that holds up best, with caveats about how hard we sell it.

Piolat, Roussey, and Thunin 1997 had undergraduates read a 574-word informational text on screen, paged versus scrolled. Paging supported a better spatial representation of the text and better location of information. Sanchez and Wiley 2009, two experiments, found scrolling reduced understanding of complex web topics, especially for readers with lower working memory. That is the paper behind "scrolling hurts comprehension," and it is about complex expository material, not a 500-word cutoff. I could not find the ">500 words" threshold.

Hou, Wu, and Harrell 2017 argued that if on-screen presentation imitates paper, cognitive-map construction improves. Li, Chen, and Yang 2013 added a visual cue map to an e-book and improved navigation and review scores. Mangen, Olivier, and Velay 2019 compared a 28-page mystery on Kindle DX versus a print pocket book. Most comprehension tests were equal. Print was better for chronology and locating events in the text. They attributed that to kinesthetic feedback from the physical book, not to "Kindle uses pages, so pages win." Kindle already paginates. Pagination is not a complete substitute for print.

Delgado, Vargas, Ackerman, and Salmeron 2018 is the screen-versus-paper meta-analysis our docs cite. 54 studies, 171,055 participants, paper advantage Hedge's g = -0.21 for digital. Moderators: larger paper advantage under time pressure, for informational text, and in later publication years. Narrative-only studies did not show the paper advantage. Clinton 2019, Journal of Research in Reading, 33 experiments, n = 2,799: screens worse than paper, g = -0.25, again limited to expository text, g = -0.32, with no difference for narrative, g = -0.04. Readers also calibrated worse on screens. Neither meta-analysis is a pagination trial. They are medium comparisons. Using them to justify "don't scroll" is a stretch. Using them to justify "this is a learning reader, so make it as paper-like as you can" is fair.

The "reflow only on font-size change" line fights the viewport. If the window changes, pages must be remeasured or the columns lie. The app's ResizeObserver is correct. The doc is wrong.

**Products.** Kindle and Apple Books default to pages. Apple offers Curl, Fast Fade, or Scroll. Immersive Reader scrolls. Voice Dream scrolls, with an optional page-by-page scroll.

**Keep / change / drop.** Keep pagination as default. Keep keyboard and edge turn. Change the animation spec to match the 320ms hairline, or slow the code down to the spec. Neither duration has a learning paper behind it. Drop "scrolling destroys spatial memory" as a universal. It impairs cognitive maps for complex informational text, especially for lower-WMC readers. Offer scroll later as an opt-in, the way Apple does.

### Color and contrast

**What we recommend.** Warm cream `#FAF6EC`, ink `#2C2C2C`, chrome `#E8E2D4`, contrast at least 8.5:1, AA 4.5:1 minimum, target 7:1. Auto warm-shift after 8pm "to protect sleep and memory consolidation." Avoid pure white and pure black. Black causes "halation."

**What the source actually says.** WCAG 2.2 SC 1.4.3 (AA): 4.5:1 for normal text. SC 1.4.6 (AAA): 7:1. Our pair computes to about 12.9:1. Warm mode about 10.6:1. Both clear AAA. The "8.5:1" figure is not in WCAG. I do not know where it came from.

Chang, Aeschbach, Duffy, and Czeisler 2015, PNAS: evening reading on a light-emitting e-reader versus a printed book. The LED condition suppressed melatonin by about 55%, delayed dim-light melatonin onset by more than 1.5 hours, lengthened sleep latency, and reduced next-morning alertness. Cajochen et al. 2011: LED-backlit screens with more 464 nm light suppressed melatonin versus non-LED screens. Cajochen, Munch, Kobialka et al. 2005: 460 nm light suppresses melatonin more than 550 nm. None of these papers test shifting a webpage from `#FAF6EC` to `#f3e6c9`. The photon count at the eye is dominated by display luminance and spectral power, which CSS cannot fix. Night Shift / f.lux / OS-level night display is the actual intervention. Our class is a mood shift.

I found no primary paper that `#FFFFFF` backgrounds reduce comprehension, or that `#000000` text causes halation that harms learning. High contrast helps low vision. Some readers prefer cream. Kindle and Apple Books offer sepia, inverse, and dark for that reason. WCAG 1.4.8 wants the user to pick foreground and background colors. A locked cream is a good default and a failed 1.4.8 mechanism.

Already-spoken words fade to `--read-muted` `#8a8475` on `#faf6ec`, about 3.45:1. That fails AA for body-sized text. Karaoke should not make the trail unreadable.

**Products.** Kindle: white, sepia, dark, plus warmth on later Paperwhites at the hardware backlight. Apple Books: themes including Quiet and Bold, brightness, background modes. Immersive Reader: Light and Dark.

**Keep / change / drop.** Keep cream and the 7:1 target. Keep evening warmth as optional comfort. Change: user themes, including a dark sepia. Fix muted-word contrast. Drop sleep and consolidation as the rationale for `.reader--warm`.

### Bimodal, read while listen

**What we recommend.** Audio with word-level gold highlight and a sentence band. Default 1.0x. Speeds 1.0 to 1.5 in 0.1 steps. Tooltip above 1.3x: "Retention may decrease above 1.5x." Off by default. Word-level primary, sentence fallback. "Simultaneous audio + highlighted text reliably improves comprehension, especially for complex non-fiction and L2 readers. Keep it optional for fluent readers, it can cause cognitive overload on easy material."

**What the source actually says.** This is the claim that most needs shrinking.

Clinton-Lisell 2023, Educational Research: Theory and Practice: 30 studies, N = 1,945, 62 effects. Reading-while-listening versus reading only: overall g = 0.18. When the reading-only condition was self-paced, the difference disappeared, g = 0.06, 95% CI [-0.07, 0.19]. When reading was experimenter-paced, RWL won, g = 0.41. Too few studies to generalize to struggling readers or L2 incidental vocabulary, though those groups are the ones theory predicts will benefit. Dual-channel (Paivio; Mayer) says two streams can help. Cognitive load / redundancy (Sweller; Mayer, Heiser, and Lonn 2001) says duplicating the same words in print and speech can hurt when presentation is fast and pictures compete. Mayer's redundancy principle was measured on narrated animations with on-screen text, not on a novel with a highlight. The honest reading of both theories: optional RWL, user-paced, no pictures fighting the words. That is what we built. "Reliably improves" is not what the meta-analysis found.

Hui 2024, Modern Language Journal: L2 English learners comprehended better in RWL than listening-only, no better than reading-only, and silent reading speed / text complexity did not moderate. L2 RWL is a listening scaffold more than a reading booster. Koh 2023 found L1-L2 orthographic distance moderated the effect. RWL helped Korean learners of Chinese more than learners of closer scripts. So "especially L2" is sometimes true and sometimes not.

Li 2014, Educational Measurement: Issues and Practice, 23 studies, 114 effects: read-aloud accommodations helped students with and without disabilities, more so with disabilities, more so on reading tests than math, and more when a human read than when a machine did. That is a testing accommodation literature. It supports offering audio to struggling readers. It does not say karaoke highlighting is the active ingredient, and it slightly prefers human narration over TTS.

I found no RCT that word-level highlight beats sentence-level highlight beats no highlight for comprehension. Kopp and D'Mello 2016 is cited in the Clinton-Lisell review as a no-difference RWL study. Product literature treats highlighting as place-keeping. That is a real job. It is not a comprehension effect until someone measures it.

Playback speed is a different literature, and it is mostly lecture video, not bimodal reading. Murphy, Hoover, Agadzhanyan, Kuehn, and Castel 2022: 1x, 1.5x, 2x, 2.5x lecture video. Immediate and 1-week tests. Impairment versus 1x only at 2.5x. Chen, Murphy, and Castel 2024: audio-only and audio-visual, speeds through 2.5x, plus distractions. Test performance held to 2x, they still advise not exceeding 2x, and visuals helped at faster speeds. Tharumalingam, Roberts, Fawcett, and Risko 2025 meta-analysis, 24 studies, 110 effects: increasing lecture speed can impair test scores, but the cost is small and often non-significant at 1.5x and below, larger beyond. Cheng et al. 2021, smaller meta: g = -0.21 at about 1.4x to 1.5x, g = -0.36 at 1.8x to 2x.

So our docs' "retention degrades above 1.5x, long-term recall significantly worse" overstates Murphy and undersells Tharumalingam's small cost already at 1.5x. The 1.3x tooltip is invented. Nobody's paper has a 1.3x cliff. For listen-while-reading, the conservative move is still: default 1.0x, comfortable band 0.75x to 1.5x, warn at 2x. Simulated narration at 165 WPM is in the audiobook band Rayner et al. 2016 quote as comfortable speech, 150 to 160 WPM. Fine.

Word timings versus a WPM walk: timings are the product feature. The cadence fallback will desync on long words, punctuation, and headings. That is an implementation quality issue, not a science one.

**Products.** Kindle Immersion Reading: professional Audible narration, synchronized highlighting, optional, Whispersync keeps place across read and listen. Microsoft Immersive Reader: TTS, word highlight as it speaks, Line Focus, syllables, picture dictionary, translation. Speechify: word-level karaoke, advertised speeds up to 4.5x. Treat 4.5x as a coverage toy, not a study setting. Voice Dream: word and line highlight, 50 to 500 WPM, rewind by sentence or paragraph, per-book speed memory. NaturalReader: TTS plus highlight. Apple Books: audiobooks exist. Line Guide is visual, not karaoke.

**Keep / change / drop.** Keep optional, off by default, word-level when you have timings, auto page-follow. Change the speed ladder to include 0.75x, default 1x, and treat 1.75x / 2x as advanced with a real warning. Persist speed per source, as the docs promised and Voice Dream already does. Drop "reliably improves comprehension." The honest tooltip is: audio helps when decoding is the bottleneck or when you would otherwise lose the thread. It does not replace reading for fluent readers on easy prose, and it can fight you if the voice outruns your eyes.

### Session timer

**What we recommend.** 25 minutes. Countdown always visible. Overlay: take a 5-minute break. Not a lock. "25 to 50 minutes then off-screen breaks support memory consolidation. Rigid interruptions increase frustration."

**What the source actually says.** Francesco Cirillo's Pomodoro Technique is a productivity book, 25 on / 5 off. Biwer, Wiradhany, oude Egbrink, and de Bruin 2023, British Journal of Educational Psychology, is the rare trial. 87 students, one day of self-study: self-regulated breaks versus 24/6 Pomodoro versus 12/3. Self-regulators took longer sessions and longer breaks, and reported more fatigue and distractedness, less concentration and motivation. No difference in mental effort or task completion. Systematic breaks had mood and apparent efficiency benefits. The paper does not measure memory. It does not find that forced lockouts increase frustration. If anything, the timed groups felt better.

Sleep consolidates memory. Diekelmann and Born's review line is the one people mean when they say consolidation. A 5-minute coffee overlay is attention restoration, closer to Ariga and Lleras 2011 on brief diversions, not systems consolidation. Off-screen is still good advice. Do not dress it as neuroscience.

**Products.** Apple Books has daily reading goals, not Pomodoro. Kindle has a sleep timer on Immersion audio. Voice Dream has a sleeper timer. None of them lock you out of the book.

**Keep / change / drop.** Keep an advisory 25-minute nudge. Change the overlay copy. Drop consolidation. The "do not force a stop" UX choice is still right even if Biwer found timed breaks felt better. A full-screen card that can be dismissed is the product we want. A hard lock is still rude.

### Avoid list, item by item

**Scrolling as default.** Supported for complex informational text and lower working memory. Overstated as universal destruction of recall. Keep as default-off. See Pagination.

**Sans Forgetica / memory fonts.** Supported. Geller, Davis, and Peterson 2020, Memory: three preregistered experiments, generation effect worked, Sans Forgetica did not, pre-highlighting beat it on a passage. Taylor, Sanson, Burnell, Wade, and Garry 2020: rated more difficult, memory equal or worse. Later DRM work found costs. Drop from the product. Do not offer it as a "study font."

**Bionic Reading as default.** Supported. Snell 2024, Acta Psychologica, 100 paragraphs, Bionic versus normal, no reading-time difference. Our docs cite `Valentini et al. 2024`. I could not find that paper. If someone meant Snell, fix the citation. Keep out of the default. Do not ship it as a gimmick either unless a later trial with dyslexic readers says otherwise. Snell did not test that population.

**RSVP.** Supported as an avoid. Rayner, Schotter, Masson, Potter, and Treiman 2016: speed-accuracy tradeoff, RSVP removes regressions that repair comprehension. Schotter, Tran, and Rayner 2014: blocking regressions hurt garden-path recovery. Di Nocera, Ricciardi, and Juola 2018: RSVP at 250, 300, 350 WPM matched normal reading on comprehension. 400 and 450 WPM were worse. Threshold around 350 WPM. Our "comprehension drops 20 to 40% above 350 WPM" is a sharper number than that paper reports. I could not verify 20 to 40%. Avoid RSVP anyway. The mechanism, no regressions, is solid.

**Full justification.** Supported via WCAG 1.4.8. Keep left-align.

**Pure white / pure black.** Comfort and glare folklore. Not a comprehension finding. Keep cream as default. Offer white and inverted for users who want them. Low-vision readers often want maximum contrast. Locking them to warm gray is not accessibility.

**Playback above 1.5x as default.** Default 1.0x is correct. "Retention degrades, long-term recall significantly worse" overstates Murphy 2022. Tharumalingam 2025 says a small cost can already show at 1.5x. Keep 1.0x default. Do not treat 1.5x as poison. Treat 2x as the line where you warn.

**Forced Pomodoro lockouts.** Partially off. Biwer 2023 found systematic breaks felt better, not worse. Still do not hard-lock the reader. The recommendation's UX instinct is better than its citation.

**Blanket bold.** Von Restorff 1933 is the isolation effect: the distinct item is remembered. Emphasizing everything removes the isolation. Reasonable design rule. Not a modern RCT on "never bold a whole paragraph."

**OpenDyslexic as proven.** Supported. Wery and Diliberto 2017, Annals of Dyslexia: OpenDyslexic versus Arial and Times New Roman, elementary students with dyslexia, no gain in rate or accuracy, some negative fluency effects, no preference for the font. Kuster, van Weerdenburg, Gompel, and Bosman 2018: Dyslexie font, same story. Offer as a preference if you offer font choice. Do not market it. Spacing, Zorzi 2012, has a better claim than the letter shapes.

## What we are missing

Only items with a real paper or spec behind them, that the Academy reader does not have.

**Font-size control.** WCAG 1.4.4. Kindle, Apple Books, Immersive Reader, Voice Dream. This is the highest-value missing control. Pagination already reflows on resize. Wire a size stepper to that.

**User-chosen colors.** WCAG 1.4.8. Dark sepia at night is what readers already expect. Our warm class is a start. A three-theme switch, paper / sepia / dark, is the product.

**Extra spacing as an option.** Zorzi et al. 2012 plus WCAG 1.4.12. Immersive Reader's spacing toggle. Not the default. A single "more space" preset is enough.

**Line focus.** Immersive Reader Line Focus, one / three / five lines. Apple Books Line Guide. Weaker trial evidence than spacing, strong place-keeping face validity for ADHD and fatigue. Cheap to add on a paginated canvas.

**Regression-friendly audio.** Schotter et al. 2014 is why RSVP is bad. The same logic says listen-while-reading needs skip-back by sentence, tap-a-word to seek, and pause that does not lose the highlight. Voice Dream's navigation units are the reference. We have play, pause, restart from zero. That is not enough when a sentence does not parse.

**Per-source speed and voice memory.** Voice Dream documents this. Our docs promised persistent per-book preference. The app stores a bookmark spread, not speed.

**Retrieval practice, not more highlighting.** Dunlosky, Rawson, Marsh, Nathan, and Willingham 2013 rate highlighting and rereading as low utility, practice testing and distributed practice as high. Academy already has flashcards and quiz. The reader should push into those after a session, not grow a highlighter that people mistake for studying. User highlights are still useful as bookmarks. Do not sell them as encoding.

**A font menu, including a dyslexia-preference face.** Wery says OpenDyslexic does not win on speed. Users still ask for it. Immersive Reader and Voice Dream offer it. Preference, not default, matches our own avoid-list.

**Human-quality narration when it exists.** Li 2014 found human read-aloud beat machine on tests. Kindle Immersion Reading is professional audio plus highlight. Our synthesized clips plus a 165 WPM fake cadence are a prototype of that feature, not the feature.

Not missing, despite the discourse: Bionic Reading, Sans Forgetica, RSVP, OpenDyslexic as a cure, 4.5x Speechify, Pac-Man disappearing text. Voice Dream attributes Pac-Man to Harvard and MIT and "2x with no loss of comprehension." That is a product sentence. Rayner 2016 is the rebuttal.

## Sources

1. Delgado, P., Vargas, C., Ackerman, R., and Salmeron, L. Don't throw away your printed books: A meta-analysis on the effects of reading media on reading comprehension. Educational Research Review, 2018. https://doi.org/10.1016/j.edurev.2018.09.003
2. Clinton, V. Reading from paper compared to screens: A systematic review and meta-analysis. Journal of Research in Reading, 2019. https://doi.org/10.1111/1467-9817.12269
3. Geller, J., Davis, S. D., and Peterson, D. J. Sans Forgetica is not desirable for learning. Memory, 2020. https://doi.org/10.1080/09658211.2020.1797096
4. Taylor, A. S., Sanson, M., Burnell, R., Wade, K. A., and Garry, M. Disfluent difficulties are not desirable difficulties: the (lack of) effect of Sans Forgetica on memory. Memory, 2020. https://doi.org/10.1080/09658211.2020.1758726
5. Snell, J. No, Bionic Reading does not work. Acta Psychologica, 2024. https://doi.org/10.1016/j.actpsy.2024.104304
6. Wery, J. J., and Diliberto, J. A. The effect of a specialized dyslexia font, OpenDyslexic, on reading rate and accuracy. Annals of Dyslexia, 2017. https://doi.org/10.1007/s11881-016-0127-1
7. Kuster, S. M., van Weerdenburg, M., Gompel, M., and Bosman, A. M. T. Dyslexie font does not benefit reading in children with or without dyslexia. Annals of Dyslexia, 2018. https://doi.org/10.1007/s11881-017-0154-6
8. W3C. Web Content Accessibility Guidelines (WCAG) 2.2. 2023. https://www.w3.org/TR/WCAG22/
9. Amazon. Kindle Paperwhite (2015) product listing, Bookerly and typesetting engine claims. https://www.amazon.com/dp/B01BFIBRIE
10. Amazon. Other Reading Accessibility Settings on Fire Tablet. Immersion Reading with Audible, synchronized highlighting. https://www.amazon.com/gp/help/customer/display.html?nodeId=TjCHGCnIKBM42lnQrE
11. Amazon KDP. Audiobooks Through ACX. Whispersync for Voice and Immersion Reading described. https://kdp.amazon.com/help/topic/G201014330
12. Microsoft Learn. What is Azure AI Immersive Reader? https://learn.microsoft.com/en-us/azure/ai-services/immersive-reader/overview
13. Microsoft Learn. Immersive Reader SDK reference. Font, spacing, theme, syllables, parts of speech. https://learn.microsoft.com/en-us/azure/ai-services/immersive-reader/reference
14. Apple. Read books in the Books app on iPhone. Font size, themes, Line Guide, justify toggle, page turn styles. https://support.apple.com/guide/iphone/read-books-iphc1af7c57/ios
15. Speechify. Product site. Word highlighting, advertised speeds up to 4.5x. Implementation illustration only. https://speechify.com/
16. Voice Dream. Reader feature list. Word and line highlighting, 50 to 500 WPM, sentence skip, OpenDyslexic, color themes. Product claims, not efficacy evidence. https://www.voicedream.com/reader/reader-feature-list/
17. Clinton-Lisell, V. Does reading while listening to text improve comprehension compared to reading only? A systematic review and meta-analysis. Educational Research: Theory and Practice, 2023. http://www.nrmera.org/wp-content/uploads/2023/09/ER-TP-V34-3_9-Clinton-Lisell-Does-Reading-While-Listening-to-Text-VCL20.pdf
18. Hui, B. Scaffolding comprehension with reading while listening and the role of reading speed and text complexity. Modern Language Journal, 2024. https://doi.org/10.1111/modl.12905
19. Koh, J. Deconstructing the benefits of reading-while-listening on L2 reading comprehension: The influence of cross-orthographic distance. Foreign Language Annals, 2023. https://doi.org/10.1111/flan.12732
20. Li, H. The effects of read-aloud accommodations for students with and without disabilities: A meta-analysis. Educational Measurement: Issues and Practice, 2014. https://doi.org/10.1111/emip.12027
21. Mayer, R. E., Heiser, J., and Lonn, S. Cognitive constraints on multimedia learning: When presenting more material results in less understanding. Journal of Educational Psychology, 2001. https://doi.org/10.1037/0022-0663.93.1.187
22. Murphy, D. H., Hoover, K. M., Agadzhanyan, K., Kuehn, J. C., and Castel, A. D. Learning in double time: The effect of lecture video speed on immediate and delayed comprehension. Applied Cognitive Psychology, 2022. https://castel.psych.ucla.edu/wp-content/uploads/sites/111/2021/11/ACP-Lecture-Speed-Murphy-2021-in-press.pdf
23. Chen, A., Murphy, D. H., and Castel, A. D. The effect of playback speed and distractions on the comprehension of audio and audio-visual materials. Educational Psychology Review, 2024. https://doi.org/10.1007/s10648-024-09917-7
24. Tharumalingam, T., Roberts, B. R. T., Fawcett, J. M., and Risko, E. F. Increasing video lecture playback speed can impair test performance: a meta-analysis. Educational Psychology Review, 2025. https://doi.org/10.1007/s10648-025-10003-9
25. Piolat, A., Roussey, J.-Y., and Thunin, O. Effects of screen presentation on text reading and revising. International Journal of Human-Computer Studies, 1997. https://static.trogu.com/documents/articles/palgrave/references/piolat%20thunin%20effects%20of%20screen%201997.pdf
26. Sanchez, C. A., and Wiley, J. To scroll or not to scroll: Scrolling, working memory capacity, and comprehending complex texts. Human Factors, 2009. https://doi.org/10.1177/0018720809352788
27. Mangen, A., Olivier, G., and Velay, J.-L. Comparing comprehension of a long text read in print book and on Kindle: Where in the text and when in the story? Frontiers in Psychology, 2019. https://doi.org/10.3389/fpsyg.2019.00038
28. Li, L. Y., Chen, G. D., and Yang, S. J. Construction of cognitive maps to improve e-book reading and navigation. Computers and Education, 2013. https://doi.org/10.1016/j.compedu.2012.07.010
29. Dyson, M. C., and Haselgrove, M. The influence of reading speed and line length on the effectiveness of reading from screen. International Journal of Human-Computer Studies, 2001. https://doi.org/10.1006/ijhc.2001.0458
30. Chang, A.-M., Aeschbach, D., Duffy, J. F., and Czeisler, C. A. Evening use of light-emitting eReaders negatively affects sleep, circadian timing, and next-morning alertness. PNAS, 2015. https://doi.org/10.1073/pnas.1418490112
31. Cajochen, C., Frey, S., Anders, D., et al. Evening exposure to a light-emitting diodes (LED)-backlit computer screen affects circadian physiology and cognitive performance. Journal of Applied Physiology, 2011. https://doi.org/10.1152/japplphysiol.00165.2011
32. Cajochen, C., Munch, M., Kobialka, S., et al. High sensitivity of human melatonin, alertness, thermoregulation, and heart rate to short wavelength light. Journal of Clinical Endocrinology and Metabolism, 2005. https://doi.org/10.1210/jc.2004-0957
33. Rayner, K., Schotter, E. R., Masson, M. E. J., Potter, M. C., and Treiman, R. So much to read, so little time: How do we read, and can speed reading help? Psychological Science in the Public Interest, 2016. https://doi.org/10.1177/1529100615623267
34. Schotter, E. R., Tran, R., and Rayner, K. Don't believe what you read (only once): Comprehension is supported by regressions during reading. Psychological Science, 2014. https://doi.org/10.1177/0956797614531148
35. Di Nocera, F., Ricciardi, O., and Juola, J. F. Rapid serial visual presentation: degradation of inferential reading comprehension as a function of speed. International Journal of Human Factors and Ergonomics, 2018. https://doi.org/10.1504/IJHFE.2018.096118
36. Zorzi, M., Barbiero, C., Facoetti, A., et al. Extra-large letter spacing improves reading in dyslexia. PNAS, 2012. https://doi.org/10.1073/pnas.1205566109
37. Dunlosky, J., Rawson, K. A., Marsh, E. J., Nathan, M. J., and Willingham, D. T. Improving students' learning with effective learning techniques. Psychological Science in the Public Interest, 2013. https://doi.org/10.1177/1529100612453266
38. Biwer, F., Wiradhany, W., oude Egbrink, M. G. A., and de Bruin, A. B. H. Understanding effort regulation: Comparing 'Pomodoro' breaks and self-regulated breaks. British Journal of Educational Psychology, 2023. https://doi.org/10.1111/bjep.12593
39. Hou, J., Wu, Y., and Harrell, E. Reading on paper and screen among senior adults: Cognitive map and technophobia. Frontiers in Psychology, 2017. https://doi.org/10.3389/fpsyg.2017.02225

Could not verify: `Valentini et al. 2024` as cited in `reader-recommendations.md`. No matching paper on Bionic Reading or OpenDyslexic under that name. Use Snell 2024 and Wery and Diliberto 2017 instead.
