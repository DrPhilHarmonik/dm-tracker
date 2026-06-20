import json

import yaml

from screens.common import format_io_error, tint_border, PALETTE
from models import ENTITY_TYPES


class _FakeStyles:
    def __init__(self):
        self.border = None


class _FakeWidget:
    def __init__(self):
        self.styles = _FakeStyles()


def test_tint_border_uses_the_entity_types_palette_color():
    widget = _FakeWidget()
    tint_border(widget, "enemy")
    assert widget.styles.border == ("solid", PALETTE["enemy"])


def test_tint_border_falls_back_for_unknown_type():
    widget = _FakeWidget()
    tint_border(widget, "not-a-real-type")
    assert widget.styles.border == ("solid", "#0f3460")


def test_palette_has_a_color_for_every_entity_type():
    for entity_type in ENTITY_TYPES:
        assert entity_type in PALETTE


def test_json_decode_error_is_categorized_before_generic_value_error():
    try:
        json.loads("not json")
    except json.JSONDecodeError as ex:
        assert format_io_error(ex).startswith("Could not parse JSON:")
    else:
        raise AssertionError("expected JSONDecodeError")


def test_yaml_error_is_categorized():
    try:
        yaml.safe_load("key: [unclosed")
    except yaml.YAMLError as ex:
        assert format_io_error(ex).startswith("Could not parse vault YAML frontmatter:")
    else:
        raise AssertionError("expected YAMLError")


def test_permission_error_is_categorized_before_generic_os_error():
    ex = PermissionError(13, "Permission denied")
    ex.filename = "/root/secret.json"
    assert format_io_error(ex) == "Permission denied: /root/secret.json"


def test_file_not_found_error_is_categorized():
    ex = FileNotFoundError(2, "No such file or directory")
    ex.filename = "/tmp/missing.json"
    assert format_io_error(ex) == "Path not found: /tmp/missing.json"


def test_is_a_directory_error_is_categorized():
    ex = IsADirectoryError(21, "Is a directory")
    ex.filename = "/tmp/some_dir"
    assert format_io_error(ex) == "Expected a file but found a directory: /tmp/some_dir"


def test_generic_value_error_is_categorized_as_validation():
    assert format_io_error(ValueError("Unsupported backup format")) == "Validation error: Unsupported backup format"


def test_generic_os_error_falls_back_to_filesystem_error():
    assert format_io_error(OSError("disk full")) == "Filesystem error: disk full"


def test_unrecognized_exception_falls_back_to_unexpected_error():
    assert format_io_error(RuntimeError("boom")) == "Unexpected error: boom"
