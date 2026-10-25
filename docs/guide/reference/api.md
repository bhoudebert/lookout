# HTTP API

The dashboard uses this API; so can your scripts. When `lookout serve` is running, interactive documentation is at `/api/docs` and the machine-readable schema at `/api/openapi.json`.

| Method and path                        | Does                                                                                                                                                                                     |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /api/items`                       | List and filter: `priority`, `channel` (with its subcategories), `source`, `state`, `starred`, `text`, `limit`, `offset`. Default: new and seen.                                         |
| `GET /api/items/{id}`                  | One item with its text and the rank explanation.                                                                                                                                         |
| `POST /api/items/{id}/rating`          | `{"rating": 1}` thumbs up, `-1` thumbs down; the rating the item already has clears it. Returns the item and an `undo` payload.                                                          |
| `POST /api/items/{id}/actions`         | `open`, `done`, `snooze` (`hours` or `until`), `reopen`, `star`, `unstar`. Returns the item and an `undo` payload.                                                                       |
| `POST /api/items/{id}/restore`         | Put an item back as an `undo` payload says.                                                                                                                                              |
| `POST /api/items/bulk`                 | One action on several ids, all or nothing.                                                                                                                                               |
| `POST /api/items/seen-below`           | Mark new items less urgent than a priority as seen.                                                                                                                                      |
| `GET /api/taxonomy`                    | The categories (channels: name, description, item count, sources that name them) .                                                                                                       |
| `POST /api/refile`                     | File existing items again: by rule where a source decides, else queued for the model's next run. Returns `{filed, queued}`.                                                              |
| `GET /api/source-types`                | The types of source and the settings each takes, so a form can be built.                                                                                                                 |
| `POST /api/sources`                    | Add a source: `name`, `type`, `settings`, `channels`, `keywords`, `enabled`. 409 if the name is taken, 422 with the reason if invalid.                                                   |
| `PUT /api/sources/{name}`              | Replace a source's settings (not its name or type).                                                                                                                                      |
| `DELETE /api/sources/{name}`           | Delete a source; its items stay.                                                                                                                                                         |
| `POST /api/channels`                   | Add a channel: `name`, `description`.                                                                                                                                                    |
| `POST /api/channels/{name}/move`       | Move a category and its subcategories inside `parent` (empty: top level). Items and sources follow. 404 unknown, 409 if the target exists or for `Other`, 422 inside itself or too deep. |
| `PATCH`, `DELETE /api/channels/{name}` | Change a description; delete a channel (409 while a source feeds it, and for `Other`).                                                                                                   |
| `GET /api/sources`                     | Sources and their health.                                                                                                                                                                |
| `PATCH /api/sources/{name}`            | `{ "enabled": true }` or `false`.                                                                                                                                                        |
| `GET /api/run`, `POST /api/run`        | Status of the run; start one (202), or get the one in progress.                                                                                                                          |
| `DELETE /api/profile`                  | Forget what was learnt from your actions.                                                                                                                                                |
| `GET /api/health`                      | Liveness and version.                                                                                                                                                                    |

Errors are `{ "detail": "..." }` with 404 for an unknown id, 409 for an action that makes no sense in the item's state, and 422 for a malformed request.
