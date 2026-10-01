---
name: fal Request Rescue
description: A support analyst's case reader. One verdict per screen, one action per screen.
colors:
  accent: "#0071e3"
  accent-pressed: "#0068d1"
  ink: "#1d1d1f"
  secondary: "#6e6e73"
  hairline: "#e8e8ed"
  wash: "#f5f5f7"
  ok: "#1d8127"
typography:
  headline:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "32px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  title:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "20px"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  body:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "11px"
    fontWeight: 400
    letterSpacing: "0.12em"
  mono:
    fontFamily: "ui-monospace, SF Mono, Menlo, Consolas, monospace"
    fontSize: "13px"
rounded:
  md: "10px"
  lg: "12px"
spacing:
  section: "40px"
  row: "14px"
  page-bottom: "96px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "#ffffff"
    rounded: "{rounded.lg}"
    padding: "14px 24px"
  button-primary-pressed:
    backgroundColor: "{colors.accent-pressed}"
    textColor: "#ffffff"
    rounded: "{rounded.lg}"
    padding: "14px 24px"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.accent-pressed}"
    padding: "12px 0"
---

# Design System: fal Request Rescue

## Overview

**Creative North Star: "The Quiet Instrument"**

The interface behaves like a well-made tool left on a clean desk: white ground, hairline divisions, one blue reserved for the single thing you can do. Nothing glows, nothing shouts, nothing competes with the verdict. Density comes from the waiting list itself, never from panels or chrome. The Practice identity survives only as a small letterspaced status line — a whisper, not a sticker.

**Key Characteristics:**
- One screen, one verdict, one filled button.
- Hairlines separate; boxes never contain.
- The accent appears exactly once per screen, on the primary action.

## Colors

Restrained strategy: neutrals plus one accent. The blue is rationed — its rarity is the point.

### Primary
- **Instrument Blue** (#0071e3): The single primary button per screen, and nothing else. White text on it.

### Neutral
- **Ink** (#1d1d1f): All body and heading text.
- **Quiet Gray** (#6e6e73): Secondary text — report quotes, evidence sources, statuses, timestamps. Never on its own as a control color.
- **Hairline** (#e8e8ed): Every divider — list rows, finding rows, table rules, disclosure boundaries.
- **Wash** (#f5f5f7): Changed diff rows and nothing else.
- **White** (#ffffff): The only ground.

### Named Rules (optional, powerful)
**The One Voice Rule.** The accent blue is used on exactly one control per screen: the primary action. Secondary tools are quiet text in a darker pressed blue (#0068d1) that holds 4.5:1 on white.
**The No Boxes Rule.** Content is separated by 1px hairlines, never enclosed in bordered cards or tinted panels.

## Typography

**Display Font:** System sans (-apple-system, Segoe UI, Roboto) (with sans-serif fallback)
**Body Font:** System sans (same stack)
**Label/Mono Font:** System mono (ui-monospace, SF Mono, Menlo) for IDs, values, diffs, and packets only.

**Character:** Neutral, product-like, invisible. Type carries hierarchy through size and weight steps, never through color or decoration.

### Hierarchy
- **Headline** (700, 32px, 1.2, -0.02em): The verdict. One per screen.
- **Title** (600, 20px, 1.3, -0.01em): Section headings, always with more space above (40px) than below (4px).
- **Body** (400, 17px, 1.5): Reading text. Measure held near 70ch in the 640px column.
- **Label** (400, 11px, 0.12em letterspaced, uppercase): Status lines only — Practice/Synthetic, table headers.
- **Mono** (400, 13px): Data, never prose.

### Named Rules (optional)
**The System Voice Rule.** No webfonts, no serifs, no display faces. The tool speaks in the operating system's voice.

## Layout

A single 640px centered column on every screen, 20px side padding, 96px bottom breathing room. Waiting list rows and finding rows are full-bleed hairline rules inside the column. Secondary tools hide one tap down inside labeled disclosures; the visible screen always holds exactly one primary action. Mobile is the same column at full width — no separate treatment needed.

## Elevation & Depth

Flat, explicitly. There are no shadows anywhere in the system. Depth is conveyed by dividers and whitespace alone. The primary button answers presses by darkening its fill, never by lifting.

## Shapes

Slightly rounded rectangles: inputs at 10px, the primary button at 12px. List rows and findings are square-cut rules. Icons are 1.5px-stroke line SVGs (chevron, check) — never glyphs, never emoji.

## Components

### Buttons
- **Shape:** Fully rounded-rectangle primary (12px radius), full column width, 17px semibold.
- **Primary:** Instrument Blue fill (#0071e3), white text, 14px vertical padding. Darkens to pressed blue on mousedown.
- **Hover / Focus:** No hover lift or glow. Keyboard focus gets a 2px accent outline offset 3px, everywhere.
- **Quiet:** Text-only in pressed blue, 12px vertical padding. Used for every secondary tool.

### Rows (list items, findings)
- **Style:** 14px vertical padding, 1px hairline bottom rule, no background, no border box.
- **State:** Tappable rows carry a 12px chevron; nothing else signals tappability.

### Inputs / Fields
- **Style:** 1px hairline border, 10px radius, 10–12px padding, white ground, inherit body type.
- **Focus:** 2px accent outline with border shift to accent.
- **Error / Disabled:** Errors render as plain red body text with role="alert"; no error boxes.

### Disclosures
- **Style:** Hairline top rule, 17px summary row with chevron, no marker glyphs, 16px bottom padding when open.
- **Purpose:** The only container in the system. Houses all secondary tools and all "show me why" evidence.

## Do's and Don'ts

### Do:
- **Do** keep exactly one filled button on any visible screen.
- **Do** separate content with 1px #e8e8ed hairlines.
- **Do** render IDs, values, diffs, and packets in 13px system mono.
- **Do** theme selection (accent tint) and focus rings (2px accent, 3px offset) from the palette.

### Don't:
- **Don't** put the accent on anything except the primary action.
- **Don't** enclose content in bordered cards or tinted panels.
- **Don't** use emoji, unicode arrows, or glyph icons — draw 1.5px SVG.
- **Don't** add shadows, gradients, kickers above headings, or colored edge borders.
- **Don't** ship a screen with two competing primary actions; demote to a disclosure.
