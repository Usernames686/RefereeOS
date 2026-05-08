# C5-AG2 Group Submission

My C5-AG2: https://github.com/Usernames686/RefereeOS -- `scientific` -- input scientific manuscript, output auditable reviewer packet with claims, evidence, method critique, reproducibility notes, and area-chair synthesis.

Tagline: Turn a preprint into an auditable reviewer packet.

Base repo: https://github.com/VJDiPaola/RefereeOS

What changed: added an AG2 Beta reviewer team with `claim_extractor`, `method_critic`, and `area_chair`; `area_chair` calls `method_critic` through `Agent.as_tool(name="critique_methods")`.

Demo plan: run deterministic preflight, run AG2 Beta reviewer with an OpenRouter/DeepSeek/Gemini key, show README / AI_LOG / ATTRIBUTION, then run tests.
