# 09: Waiting strip plus Practice room

**What to build:** Inbox becomes a headline strip ("what needs you most",
report text per row, people waiting instead of database rows) and the replay
badge becomes ambient Practice chrome driven by the API `replay` flag —
unmistakable room, not a sticker label.

**Blocked by:** 08 proof-cards-closing-beat.

**Status:** ready-for-agent

## Comments

Implemented 2026-10-01 (ticket 09). Backend: list rows carry the redacted
report headline. Frontend: headline waiting strip with answer states, ambient
Practice chrome on inbox and detail (red live room when the flag ever flips),
badge pills removed, create form behind a discreet "New case" toggle — no
endpoint input on screen. Full suite 62/62, tsc/build clean, strip and room
screenshotted live. Debugging note: a stale pre-restart process squatted on
:8000 and served old rows — cleared by port, fresh server verified. All nine
tickets now shipped.

- [ ] Inbox rows show report headlines (list endpoint carries report text)
- [ ] Practice chrome frames replay mode; live would read as a different room
- [ ] Badge sticker removed in favor of the ambient flag
- [ ] No endpoint-ID input on the front screen
