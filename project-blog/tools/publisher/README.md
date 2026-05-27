# Scratchpad Publisher

This service bridges HedgeDoc notes to Jekyll posts.

Endpoints:

- `GET /healthz`
- `GET /status/{note_id}?user_email=...`
- `POST /publish`
- `POST /unpublish`

Request body for `POST /publish` and `POST /unpublish`:

```json
{
  "note_id": "abc123",
  "user_email": "member@example.com",
  "display_name": "Member Name"
}
```

Behavior:

- First publish creates a stable `_posts/YYYY-MM-DD-slug.md`
- Later publish calls update the same file
- Unpublish keeps the file and sets `published: false`
- `author:` is populated from the first publish request unless already present
- `hedgedoc-map.yml` stores note id to filename mappings

Auth:

- allowed users: `/etc/oauth2-proxy/emails.txt`
- admins: `/etc/oauth2-proxy/admins.txt`

Deployment notes:

- mount the git repo root into the container
- point `GIT_REPO_DIR` at the git repo root
- point `BLOG_CONTENT_DIR` at the Jekyll project directory inside that repo
- mount `/etc/oauth2-proxy` read-only into the container
- expose the publisher to HedgeDoc's browser origin, either through nginx or direct CORS
- pin `HEDGEDOC_IMAGE` before shipping the custom toolbar build
