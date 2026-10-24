# HTTP API

The dashboard uses this API; so can your scripts. When `lookout serve` is running, interactive documentation is at `/api/docs` and the machine-readable schema at `/api/openapi.json`.

| Method and path                 | Does                                                                                                                          |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `GET /api/items`                | List and filter: `priority`, `category`, `source`, `state`, `starred`, `text`, `limit`, `offset`. Default: new and seen.      |
| `GET /api/items/{id}`           | One item with its text and the rank explanation.                                                                              |
| `POST /api/items/{id}/actions`  | `open`, `done`, `dismiss`, `snooze` (`hours` or `until`), `reopen`, `star`, `unstar`. Returns the item and an `undo` payload. |
| `POST /api/items/{id}/restore`  | Put an item back as an `undo` payload says.                                                                                   |
| `POST /api/items/bulk`          | One action on several ids, all or nothing.                                                                                    |
| `POST /api/items/seen-below`    | Mark new items less urgent than a priority as seen.                                                                           |
| `GET /api/sources`              | Sources and their health.                                                                                                     |
| `PATCH /api/sources/{name}`     | `{ "enabled": true }` or `false`.                                                                                             |
| `GET /api/run`, `POST /api/run` | Status of the run; start one (202), or get the one in progress.                                                               |
| `DELETE /api/profile`           | Forget what was learnt from your actions.                                                                                     |
| `GET /api/health`               | Liveness and version.                                                                                                         |

Errors are `{ "detail": "..." }` with 404 for an unknown id, 409 for an action that makes no sense in the item's state, and 422 for a malformed request.
