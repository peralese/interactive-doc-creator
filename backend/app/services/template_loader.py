"""Load bundled JSON templates into the database on startup."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.template import Template

logger = logging.getLogger(__name__)


async def load_bundled_templates(db: AsyncSession) -> int:
    """Insert templates that do not already exist, preserving user edits."""
    directory = Path(settings.template_storage_path)
    if not directory.is_dir():
        return 0
    loaded = 0
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if await db.get(Template, payload["id"]) is not None:
                continue
            metadata = payload.get("metadata", {})
            duration = metadata.get("estimated_duration")
            estimated_duration = None
            if isinstance(duration, int):
                estimated_duration = duration
            elif isinstance(duration, str):
                digits = "".join(character for character in duration if character.isdigit())
                if digits:
                    estimated_duration = int(digits[:2])
            db.add(
                Template(
                    id=payload["id"],
                    name=payload["name"],
                    description=payload.get("description"),
                    version=payload.get("version", "1.0"),
                    content={
                        "sections": payload.get("sections", []),
                        "metadata": metadata,
                    },
                    category=metadata.get("category"),
                    estimated_duration=estimated_duration,
                    difficulty=metadata.get("difficulty"),
                )
            )
            loaded += 1
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("Skipping invalid template %s: %s", path, exc)
    await db.commit()
    return loaded
