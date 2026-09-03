# Artifact contract

`summary.json` and `final.json` are immutable outputs for one execution identity.
If either target already exists, the handler must reject before `execute()` and must not create any additional artifact.
