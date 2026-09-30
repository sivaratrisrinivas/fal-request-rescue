# Local runner replaces the fal queue adapter

No fal key was available (fal requires credits), so the live path no longer
targets fal's queue. Live tests run against local Ollama instead: free,
open-source, no key, $0 per run. The flow keeps its shape — approval, caps,
request ID, status poll, cost record — which is what the prototype proves.
Image and video correctness still needs fal one day; the plumbing will not care.
