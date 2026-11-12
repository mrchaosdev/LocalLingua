---
name: astryx-ui
description: Build Astryx-native accessible React dashboard and coherent WPF subtitle overlay for LocalLingua.
---
# Skill: Astryx UI

Read `docs/05-DESIGN-ASTRYX.md`. Read official docs via project-installed CLI:
```powershell
cd apps/web
npm install
npx @astryxdesign/cli init
npx @astryxdesign/cli component Button
npx @astryxdesign/cli component Card
```

Use `@astryxdesign/core`, `@astryxdesign/theme-neutral/built` and CSS reset/astryx/theme imports; use plain CSS for app-specific layout; do not recreate core design components manually when official component exists. Ensure live state, live/disconnected indicator and tentative/final label. Do NOT show an action that cannot execute. Provide light/dark review and keyboard navigation; UI caption text remains legible in both. On each UI iteration screenshot and inspect with owner.
