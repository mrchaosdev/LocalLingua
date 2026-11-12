---
name: windows-integration
description: Implement Windows 11 process-specific Discord audio capture, WPF topmost overlay, and lifecycle handling.
---
# Skill: Windows integration

Read `docs/06-WINDOWS-CAPTURE.md` and Microsoft official ApplicationLoopback sample. Use diagnostic endpoint loopback as temporary baseline only. Implement Win11 process loopback with include-process-tree and verified process enumeration; identify Discord root correctly, handle process restarts and audio device changes. No Discord user tokens. WPF overlay must be topmost and draggable; optional click-through needs visible unlock hotkey. Check multi-monitor and 125/150% DPI. Test with Discord-only audio and simultaneous YouTube to establish true isolation. Document tested Windows build and exact proof.
