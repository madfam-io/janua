"""The engagement-lifecycle template ids resolve to real files.

The registry is a strict whitelist; a registered id whose file is missing
falls back to generate_fallback_html silently — branded mail degrading to a
bare key dump with nothing failing. Mirror of the letterhead-logo existence
doctrine: defaults must exist on disk.
"""

from pathlib import Path

from app.routers.v1.email import EMAIL_TEMPLATES, TEMPLATE_FILENAMES, _get_safe_template_path

ENGAGEMENT_IDS = [
    "transactional/agreement-accepted",
    "transactional/workspace-activated",
]


def test_engagement_ids_are_registered_in_both_registries():
    for template_id in ENGAGEMENT_IDS:
        assert template_id in EMAIL_TEMPLATES
        assert template_id in TEMPLATE_FILENAMES


def test_engagement_template_files_exist_on_disk():
    for template_id in ENGAGEMENT_IDS:
        assert Path(_get_safe_template_path(template_id)).is_file(), template_id


def test_every_required_variable_has_a_slot_in_its_template():
    """A required variable with no {{slot}} is silently dropped by the
    string-substitution renderer; a slot with no registered variable renders
    literally. Both directions pinned."""
    for template_id in ENGAGEMENT_IDS:
        content = Path(_get_safe_template_path(template_id)).read_text(encoding="utf-8")
        for variable in EMAIL_TEMPLATES[template_id]["required"]:
            assert f"{{{{{variable}}}}}" in content, f"{template_id} lacks slot {variable}"
