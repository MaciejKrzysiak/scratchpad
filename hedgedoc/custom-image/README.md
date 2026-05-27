# Custom HedgeDoc Image

This directory is the staging area for the pinned Scratchpad HedgeDoc build.

Plan:

1. Determine the exact HedgeDoc tag currently running on the server.
2. Replace `HEDGEDOC_IMAGE` in `hedgedoc/docker-compose.yml` with a pinned custom tag.
3. Patch the matching HedgeDoc frontend so the top toolbar can:
   - call HedgeDoc `/me`
   - call publisher `GET /status/{note_id}`
   - show `Publish to Scratchpad`, `Update Scratchpad`, and `Unpublish from Scratchpad`
   - show a `Draft`, `Published`, or `Unpublished` badge
4. Build on the server with `docker compose build hedgedoc`.

The publisher API is already prepared for that frontend contract.
