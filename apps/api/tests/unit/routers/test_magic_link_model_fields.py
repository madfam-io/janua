"""Both magic-link paths queried a column that does not exist.

`MagicLink` tracks consumption with a nullable `used_at` timestamp; there is
no boolean `used`. `MagicLink.used == False` therefore raised AttributeError
at request time, so every real token 500'd — in the pre-existing POST verify
endpoint as well as the GET callback added on 2026-08-13.

A route-registration test does not catch this: the route existed and answered
correctly when called WITHOUT a token, because the query is never reached on
that path. These assert the query itself.
"""

import inspect

from app.models import MagicLink
from app.routers.v1 import auth


def test_model_tracks_consumption_with_used_at():
    assert hasattr(MagicLink, "used_at")
    assert not hasattr(MagicLink, "used"), (
        "If a boolean `used` column is ever added, revisit both magic-link "
        "queries — they filter on used_at IS NULL."
    )


def test_no_handler_filters_on_a_nonexistent_used_column():
    source = inspect.getsource(auth)
    assert "MagicLink.used ==" not in source
    assert "magic_link.used = True" not in source


def test_both_paths_filter_unconsumed_links():
    """The GET callback and the POST verify must both exclude spent links."""
    for handler in (auth.magic_link_callback, auth.verify_magic_link):
        source = inspect.getsource(handler)
        assert "MagicLink.used_at.is_(None)" in source, handler.__name__
        assert "magic_link.used_at = " in source, handler.__name__
