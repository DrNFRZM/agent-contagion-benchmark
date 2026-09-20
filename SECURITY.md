# Security and safety statement

## What this project is

A small, self-contained simulation benchmark that measures how one **harmless, fictional false fact**
spreads (or fails to spread) between LLM-style agents connected in different communication topologies.
It is research on AI-system **reliability and fault propagation**. It is not an attack tool.

## Controlled and non-operational by design

- **Synthetic content only.** Every fact concerns invented planets ("the capital of Veloria is Arden").
  The injected fault changes one such fact ("Arden" becomes "Mira"). There is no real-world information,
  no personal data, no credentials, and no instructions of any kind in the payload.
- **No external targets.** The code never scans, contacts, or interacts with third-party systems.
  The default backend is a deterministic mock that runs offline. The optional API backend only calls an
  endpoint that *you* configure through environment variables, with prompts built from the synthetic facts above.
- **No exploit code.** There is no malware, no persistence mechanism, no authentication bypass, no
  credential handling beyond reading an optional API key from your own environment, and no destructive payload.
- **No prompt-injection payloads.** The "fault" is a plain false statement in an agent's memory. The project
  does not contain jailbreaks, instruction-override strings, or techniques for hijacking real agent products.
- **Secrets stay out of the repo.** API keys are read from environment variables only and are never written
  to disk or logged by this code. `.gitignore` excludes `.env`, key files, model weights, caches and large outputs.
  CI uses only the mock backend and needs no secrets.

## What is deliberately out of scope

Adaptive adversaries, attacks on real deployed agent frameworks, tool-use or code-execution abuse, data
exfiltration, and anything that would be useful primarily for harming a real system. If you extend this
project, please keep contributions inside the synthetic, closed-world setting.

## Reporting a concern

If you believe some part of the repository could be misused or you find an accidentally committed secret,
please open a GitHub issue that does not include the secret itself, or email nikbakhshfarzam@gmail.com.
