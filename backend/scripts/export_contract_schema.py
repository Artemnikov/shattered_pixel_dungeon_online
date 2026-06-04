"""Export the WebSocket entity contract as a JSON Schema for the frontend.

The Pydantic models in app.engine.entities.base are the single source of truth for
the shapes that cross the socket (Player, Mob, the discriminated Item union, etc.).
This script dumps them to a JSON Schema that `json-schema-to-typescript` turns into
`frontend/src/types/generated/entities.ts`, so the TypeScript types provably match
the backend models — re-run it whenever those models change.

Only the *entity* shapes are generated here. The message envelopes (INIT /
STATE_UPDATE), event payloads, and outgoing client messages are assembled as plain
dicts in main.py and are hand-written in `frontend/src/types/contract.ts`.

Run via `npm run gen:schema` (from frontend/) or directly inside the backend venv.
"""

import json
import sys
from pathlib import Path

# Running this file directly puts scripts/ on sys.path, not the backend root;
# add the backend root so `app` imports resolve regardless of the launch cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import BaseModel

from app.engine.entities.base import Mob, Player


class _Contract(BaseModel):
    """Wrapper whose fields drag every referenced entity model into `$defs`.

    Player transitively pulls in Belongings, QuickSlot, Effect, Position, and the
    full AnyItem discriminated union (every item variant), so listing Player + Mob
    here is enough to emit the whole entity graph.
    """

    player: Player
    mob: Mob


def _strip_property_titles(node: object) -> None:
    """Drop auto-generated per-field `title`s so json-schema-to-typescript emits
    inline field types instead of a named alias for every scalar (Id, Hp1, ...).

    Model-level names still come from the `$defs` keys, so the interface names
    (Player, Mob, Potion, ...) are preserved — only the noise is removed.
    """
    if isinstance(node, dict):
        node.pop("title", None)
        for value in node.values():
            _strip_property_titles(value)
    elif isinstance(node, list):
        for item in node:
            _strip_property_titles(item)


def main() -> None:
    # mode="serialization" matches the wire format (model_dump): it includes
    # @computed_field views like Player.inventory / equipped_weapon that the client
    # reads but which validation-mode schemas omit.
    schema = _Contract.model_json_schema(mode="serialization", ref_template="#/$defs/{model}")
    _strip_property_titles(schema)

    repo_root = Path(__file__).resolve().parents[2]
    out_path = repo_root / "frontend" / "src" / "types" / "generated" / "contract.schema.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(schema, indent=2) + "\n")

    print(f"Wrote entity contract schema -> {out_path}")


if __name__ == "__main__":
    main()
