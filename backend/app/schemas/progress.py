"""Progress-status fields shared by sessions and captures.

``progress_status`` tracks where a piece of work stands from the author's point
of view (in progress → done → published). It is separate from
``Session.status``, which the session lifecycle and cleanup code own.
"""

from typing import Annotated, Literal

from pydantic import AfterValidator, BeforeValidator, Field

ProgressStatusValue = Literal["in_progress", "done", "published"]


def _default_in_progress(value: object) -> object:
    # Rows created before the column existed have NULL; treat them as in progress.
    return "in_progress" if value is None else value


def _check_published_url(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not value.lower().startswith(("http://", "https://")):
        raise ValueError("published_url must start with http:// or https://")
    return value


ProgressStatus = Annotated[ProgressStatusValue, BeforeValidator(_default_in_progress)]

PublishedUrl = Annotated[
    str | None,
    Field(None, max_length=1000, description="Where the finished work was posted"),
    AfterValidator(_check_published_url),
]
