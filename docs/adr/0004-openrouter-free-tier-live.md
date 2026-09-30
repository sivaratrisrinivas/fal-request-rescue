# OpenRouter free tier replaces the local runner

The local Ollama plan died to a simpler idea: the key we already hold.
OpenRouter's free tier (50 requests a day, no credits) executes live tests
for $0 with real generation IDs back. The daily quota is enforced in code
next to the spend caps, and 429s surface as 503 with a retry-tomorrow message
instead of a 500. LLM drafting already used the same key, so the whole live
surface now runs on one credential that lives only in the server environment.
