# Eval limitations (06)

- Accuracy 1.00 is on synthetic families: variants share base payloads and the
  engine is deterministic, so paraphrases score identically. Treat held-out 1.00
  as a regression tripwire, not a real-world rate.
- Live fal submit and live LLM drafting are code-complete but unproven (no fal
  key; OpenRouter free tier 429s). The live path now targets local Ollama
  instead, which is provable for $0 once a runner is up. Safety cases assert
  gates, not live behavior.
- Gold revision policy: disagreements must revise gold labels before any rate
  claim (case-01 corrected→need-information in this round for that reason).
