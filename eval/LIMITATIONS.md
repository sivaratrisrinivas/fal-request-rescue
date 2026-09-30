# Eval limitations (06)

- Accuracy 1.00 is on synthetic families: variants share base payloads and the
  engine is deterministic, so paraphrases score identically. Treat held-out 1.00
  as a regression tripwire, not a real-world rate.
- Live submit and live LLM drafting are code-complete; the free tier is
  currently rate-limiting, so a real green run is pending quota reset. The
  429 path is verified (503, retry tomorrow, no 500). Safety cases assert
  gates, not live behavior.
- Gold revision policy: disagreements must revise gold labels before any rate
  claim (case-01 corrected→need-information in this round for that reason).
