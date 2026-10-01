# Eval limitations (06)

- Accuracy 1.00 is on synthetic families: variants share base payloads and the
  engine is deterministic, so paraphrases score identically. Treat held-out 1.00
  as a regression tripwire, not a real-world rate.
- Preview runs go to the Gemini API free tier (real generation
  ID, structured JSON back); live drafting hit transient Google 503s, so a
  green draft run is pending. The failure path is verified (503, no 500).
  A Gemini preview is not a fal request test: it validates neither fal
  rendering, queue, nor callback behavior.
  Safety cases assert gates, not live behavior.
- Gold revision policy: disagreements must revise gold labels before any rate
  claim (case-01 corrected→need-information in this round for that reason).
