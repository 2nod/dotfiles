# Cache key migration plan

Status: implementation and tests complete.

## Durable contract

- The canonical key is `{tenant_id}:{item_id}`.
- Readers use `item_id` as a legacy fallback during the rollout.

## Completed work

- Added tenant-scoped key generation.
- Preserved the legacy read path.
- Added regression tests.
