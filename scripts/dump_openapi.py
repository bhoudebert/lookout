"""Print the API's OpenAPI document; the frontend's TypeScript types are generated from it."""

import json
from typing import TYPE_CHECKING, cast

from lookout.adapters.http.app import create_app

if TYPE_CHECKING:
    from lookout.application.services import Services

if __name__ == "__main__":
    # The routes only touch services when called, so building the schema needs none.
    api = create_app(cast("Services", None))
    print(json.dumps(api.openapi(), indent=2, sort_keys=True))  # noqa: T201
