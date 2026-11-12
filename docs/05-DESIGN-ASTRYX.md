# UI/UX design system — Astryx by Meta, not a clone

## Sources and use
Site: https://astryx.atmeta.com/ — Docs https://astryx.atmeta.com/docs/getting-started — Repo https://github.com/meta/astryx (MIT). Astryx is **a React component/design system** currently in beta. The user likes its modern, spacious, understated interface; use official packages for foundation and customize visual identity. Do NOT copy Meta assets, page imagery or logos; do NOT invent an '@astryx' library.

## Product personality
- Name: **LocalLingua**; working title only (check trademark if published).
- Focus: purposeful, calm, responsive, low-distraction tool. Audio and subtitle are primary, AI decorations are secondary.
- Default: subtle dark graphite theme for nighttime Discord, optional light theme.
- Palette suggestion (application-level, independent of Astryx token names):
  - Background `#0F1117`, panel `#191D27`, elevated `#222736`, border `#353C4B`.
  - Text primary `#F1F4FA`, muted `#A8B1C3`, quiet `#7E899B`.
  - Accent cool periwinkle `#8B9BFF`, success `#58C69A`, warning `#E6B873`, error `#ED7C81`.
- Typography: use Astryx neutral typography and configured font stack; no bundling copyrighted/unlicensed fonts. 13–15px UI; captions 20–30px adjustable.
- Spacing: 4/8/12/16/24/32; radii 10–14px for sections; clean lines and 1px borders.
- Avoid gaudy gradients and huge cards, use one highlight to direct attention to current translation.
- Respect reduced motion; no flashing audio waves for decorative effect.

## Information architecture
**Screen A — Live Console**
- Left sidebar width ~224px: Live, History (optional), Glossary (P1), Benchmark, Settings.
- Top bar: LocalLingua, current source `Discord`/`System Diagnostic`, ASR model, local/online label, status LED.
- Center 65–72%: current Vietnamese subtitle prominent; English original directly underneath in a subtle color; 6–10 latest lines below.
- Right inspector width ~260px on wide screens: current pipeline status, audio RMS, ASR and translation p50/p95, dropped frames, GPU memory.
- Bottom transport: Start/Pause/Stop, translation preset, capture source, last failure. No misleading active toggle if host isn't connected.

**Screen B — Compact caption panel**
- Width ~350–620px; large Vietnamese translation 2–3 lines and small English original (optional).
- Status dot small; drag handle, pin/topmost icon, size control, opacity control. Avoid obscuring entire Discord call.

**Screen C — Settings**
- Input source (system diagnostic vs Discord isolated), audio output device, language fixed EN→VI, model backend status, quality mode, glossary, privacy and export preferences.
- Disabled source selector explains gating: `Discord-only capture chưa hoàn thành/không khả dụng` rather than pretending success.

**Screen D — Diagnostics**
- Audio level and sample rate, model loaded, queue length, median/p95 timings, VRAM. Actions: play test wav, test translation, compare profiles. All run locally.

## States to design deliberately
`Not started`, `Starting`, `Listening`, `Speech detected`, `Transcribing`, `Translating`, `Degraded: backlog`, `Paused`, `Stopped`, `Error: no audio`, `Error: model unavailable`, `Error: Discord source lost`.

## Caption semantics and visual hierarchy
- Tentative EN in muted grey (never pretend finalized).
- Tentative VI with soft accent label **Đang dịch...** and visible subtle revision status.
- Final VI high contrast; final EN secondary; timestamp accessible.
- On translator failure show EN and explicit issue (never show a fake Vietnamese caption).
- Long sentences wrap; max 3 lines visible, full transcript scroll in dashboard; no auto-scroll if user reading history.

## Astryx official installation (developer executes)
```powershell
cd apps/web
npm install
npx @astryxdesign/cli init
npx @astryxdesign/cli component Button
npx @astryxdesign/cli component Card
npx @astryxdesign/cli theme list
```
The scaffold uses `@astryxdesign/core/Button`, `@astryxdesign/core/theme` and `@astryxdesign/theme-neutral/built`, supported by official docs. Keep ordered CSS imports:
```css
@import '@astryxdesign/core/reset.css';
@import '@astryxdesign/core/astryx.css';
@import '@astryxdesign/theme-neutral/theme.css';
```
For a custom theme use official `npx @astryxdesign/cli theme add neutral`, `defineTheme` + build, not shadowing private CSS vars. Product-specific layout may use ordinary CSS, but shared controls must prefer Astryx. Always consult `astryx component <Name>` for props.

## Interaction rules
- Dashboard Ctrl+Enter: start/pause only if user assigned; Escape should close popover not kill capture silently.
- Make all model statuses screenreader readable. Controls have visible labels; keyboard focus high contrast.
- Overlay pointer behavior: default draggable; optional lock/click-through activated explicitly. Hotkey to unlock overlay so it isn't permanently unclickable.
- Ensure WebSocket reconnect gives current state; never make user believe captions are live when disconnected.

## Responsive behavior
- >1200px: sidebar + transcript + inspector.
- 800–1200px: hide inspector behind collapsible panel; current captions retain width.
- <800px: single-column; source selector and start action remain at top; avoid overflow.
- Overlay is independent/native window (WPF), not a browser floating window confined to tab bounds.

## Component checklist
- Astryx Card for structured content, Button for actions, Badge when informative, native/verified Astryx select or accessible HTML select if needed.
- Contrast and motion accessibility checks, dark/light, keyboard-only, 150% DPI scaling, Windows multi-monitor.
- Only ship after screenshot review with owner; design is utility, not a marketing landing page.
