# Gemini API replaces OpenRouter for all live calls

Both model touchpoints — disposition drafting and live execution — now use
the Gemini API (`x-goog-api-key` auth, `responseMimeType` plus
`responseSchema` for structured JSON) with the key the project already holds.
OpenRouter's free tier stayed rate-limited; Gemini answered live on both paths
(drafting once needed a retry past transient Google 503s). Model retired twice
under us during the swap (`gemini-2.0-flash`, `gemini-2.5-flash-lite`), so the
default pins to the model list, not memory: `gemini-3.5-flash`, overridable
via `GEMINI_MODEL`. The daily quota guard stays as an abuse meter.
