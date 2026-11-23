"""Unit tests for TemplateMixin."""

import base64
import json
import unittest
import zlib
from unittest.mock import MagicMock, PropertyMock

import pytest

from fabrictestbed_extensions.fablib import template_mixin
from fabrictestbed_extensions.fablib.template_mixin import TemplateMixin


class ConcreteTemplate(TemplateMixin):
    """Concrete implementation of TemplateMixin for testing."""

    _default_skip = ["secret_field"]
    _show_title = "Test Object"

    def __init__(self, name="test", data=None):
        super().__init__()
        self._name = name
        self._data = data or {"key": "value", "secret_field": "hidden"}
        self._fim = MagicMock()
        self._fim.name = name
        self._slice = MagicMock()

    def get_fim(self):
        return self._fim

    def toDict(self, skip=None):
        if skip:
            return {k: v for k, v in self._data.items() if k not in skip}
        return dict(self._data)

    def get_slice(self):
        return self._slice


class TestTemplateMixinInit(unittest.TestCase):
    """Tests for TemplateMixin initialization and caching."""

    def test_initial_state_is_dirty(self):
        obj = ConcreteTemplate()
        self.assertTrue(obj._fim_dirty)

    def test_initial_caches_are_none(self):
        obj = ConcreteTemplate()
        self.assertIsNone(obj._cached_reservation_id)
        self.assertIsNone(obj._cached_reservation_state)
        self.assertIsNone(obj._cached_error_message)
        self.assertIsNone(obj._cached_name)
        self.assertIsNone(obj._cached_dict)

    def test_invalidate_cache_resets_all(self):
        obj = ConcreteTemplate()
        obj._cached_reservation_id = "test-id"
        obj._cached_reservation_state = "Active"
        obj._cached_error_message = "some error"
        obj._cached_name = "cached-name"
        obj._cached_dict = {"cached": True}
        obj._fim_dirty = False

        obj._invalidate_cache()

        self.assertTrue(obj._fim_dirty)
        self.assertIsNone(obj._cached_reservation_id)
        self.assertIsNone(obj._cached_reservation_state)
        self.assertIsNone(obj._cached_error_message)
        self.assertIsNone(obj._cached_name)
        self.assertIsNone(obj._cached_dict)


class TestTemplateMixinGetName(unittest.TestCase):
    """Tests for get_name caching."""

    def test_get_name_from_fim(self):
        obj = ConcreteTemplate(name="my-node")
        name = obj.get_name()
        self.assertEqual(name, "my-node")

    def test_get_name_caches_result(self):
        obj = ConcreteTemplate(name="my-node")
        name1 = obj.get_name()
        obj._fim.name = "changed"
        name2 = obj.get_name()
        # Should return cached value
        self.assertEqual(name1, name2)

    def test_get_name_after_invalidate(self):
        obj = ConcreteTemplate(name="my-node")
        obj.get_name()
        obj._invalidate_cache()
        obj._fim.name = "new-name"
        name = obj.get_name()
        self.assertEqual(name, "new-name")

    def test_get_name_none_fim(self):
        obj = ConcreteTemplate()
        obj._fim = None
        name = obj.get_name()
        self.assertIsNone(name)


class TestTemplateMixinJson(unittest.TestCase):
    """Tests for toJson serialization."""

    def test_to_json_returns_valid_json(self):
        obj = ConcreteTemplate(data={"name": "test", "count": 42})
        result = obj.toJson()
        parsed = json.loads(result)
        self.assertEqual(parsed["name"], "test")
        self.assertEqual(parsed["count"], 42)


class TestTemplateMixinRender(unittest.TestCase):
    """Tests for Jinja2 template rendering."""

    def test_render_simple_template(self):
        obj = ConcreteTemplate(data={"host": "TACC", "cores": 4})
        # Mock the slice to return a context dict
        obj._slice.get_template_context.return_value = {"host": "TACC", "cores": 4}

        result = obj.render_template("Host: {{ host }}, Cores: {{ cores }}")
        self.assertEqual(result, "Host: TACC, Cores: 4")

    def test_render_with_default_skip(self):
        obj = ConcreteTemplate()
        # The _default_skip is ["secret_field"]
        obj._slice.get_template_context.return_value = {"key": "value"}

        result = obj.render_template("Key: {{ key }}")
        self.assertEqual(result, "Key: value")

        # Verify get_template_context was called with skip
        obj._slice.get_template_context.assert_called()


class TestTemplateMixinReservation(unittest.TestCase):
    """Tests for reservation info retrieval."""

    def test_get_reservation_id(self):
        obj = ConcreteTemplate()
        res_info = MagicMock()
        res_info.reservation_id = "res-123"
        obj._fim.get_property.return_value = res_info

        result = obj.get_reservation_id()
        self.assertEqual(result, "res-123")

    def test_get_reservation_id_caches(self):
        obj = ConcreteTemplate()
        res_info = MagicMock()
        res_info.reservation_id = "res-123"
        obj._fim.get_property.return_value = res_info

        obj.get_reservation_id()
        obj.get_reservation_id()
        # Should only call get_property once (cached)
        obj._fim.get_property.assert_called_once()

    def test_get_reservation_state(self):
        obj = ConcreteTemplate()
        res_info = MagicMock()
        res_info.reservation_state = "Active"
        obj._fim.get_property.return_value = res_info

        result = obj.get_reservation_state()
        self.assertEqual(result, "Active")

    def test_get_error_message(self):
        obj = ConcreteTemplate()
        res_info = MagicMock()
        res_info.error_message = "Something went wrong"
        obj._fim.get_property.return_value = res_info

        result = obj.get_error_message()
        self.assertEqual(result, "Something went wrong")

    def test_get_reservation_id_handles_exception(self):
        obj = ConcreteTemplate()
        obj._fim.get_property.side_effect = Exception("no property")

        result = obj.get_reservation_id()
        self.assertIsNone(result)


class TestTemplateMixinUserData(unittest.TestCase):
    """Tests for user data and fablib data."""

    def test_set_user_data(self):
        obj = ConcreteTemplate()
        obj.set_user_data({"key": "val"})
        obj._fim.set_property.assert_called_once()

    def test_get_user_data_empty(self):
        obj = ConcreteTemplate()
        obj._fim.get_property.side_effect = Exception("no data")
        result = obj.get_user_data()
        self.assertEqual(result, {})

    def test_get_fablib_data_empty(self):
        obj = ConcreteTemplate()
        obj._fim.get_property.side_effect = Exception("no data")
        result = obj.get_fablib_data()
        self.assertEqual(result, {})

    def test_get_fablib_manager_via_slice(self):
        obj = ConcreteTemplate()
        mock_fablib = MagicMock()
        obj._slice.get_fablib_manager.return_value = mock_fablib
        result = obj.get_fablib_manager()
        self.assertEqual(result, mock_fablib)

    def test_get_fablib_manager_no_slice(self):
        obj = ConcreteTemplate()
        obj._slice = None
        # Override get_slice to return None
        obj.get_slice = lambda: None
        result = obj.get_fablib_manager()
        self.assertIsNone(result)


class TestTemplateMixinPrettyNames(unittest.TestCase):
    """Tests for pretty name dict."""

    def test_default_pretty_names_empty(self):
        result = TemplateMixin.get_pretty_name_dict()
        self.assertEqual(result, {})


def _stored_user_data(obj):
    """Wire obj's FIM property bag to a dict so set_user_data/get_user_data
    round-trip as they would against FIM; return the dict."""
    storage = {}
    obj._fim.set_property.side_effect = lambda pname, pval: storage.update(
        {pname: str(pval)}
    )
    obj._fim.get_property.side_effect = lambda pname: storage.get(pname, "")
    return storage


@pytest.mark.parametrize(
    "data, mode, compressed",
    [
        ({"blob": "x" * 1900}, "needed", False),
        ({"blob": "abcdefghij" * 300}, "needed", True),
        ({"blob": "x" * 500}, "always", True),
        ({"zlib64": "not-compressed", "other": "y" * 2100}, "needed", True),
    ],
    ids=["fits-stays-plain", "too-large-compressed", "always", "user-zlib64-key"],
)
def test_user_data_round_trip(monkeypatch, data, mode, compressed):
    """Payloads round-trip. By default only a payload over UserData's
    2048-byte limit is compressed (fablib without compression reads the rest),
    and compression brings a 3 KB payload under the limit."""
    monkeypatch.setenv("FABRIC_COMPRESS_USER_DATA", mode)
    obj = ConcreteTemplate()
    storage = _stored_user_data(obj)
    obj.set_user_data(data)
    stored = json.loads(storage["user_data"])
    if compressed:
        assert set(stored) == {template_mixin.USER_DATA_COMPRESSED_KEY}
        assert len(storage["user_data"]) <= 2048
    else:
        assert stored == data
    assert obj.get_user_data() == data


def _compressed(data):
    return base64.b64encode(zlib.compress(json.dumps(data).encode())).decode()


@pytest.mark.parametrize(
    "stored, expected",
    [
        ({"old": "format", "nested": {"a": 1}}, None),
        ({"zlib64": "not-valid-base64!!!"}, None),
        (
            {
                "zlib64": _compressed({"a": 1, "fablib_data": {"v": 1, "w": 3}}),
                "fablib_data": {"v": 2},
            },
            {"a": 1, "fablib_data": {"v": 2, "w": 3}},
        ),
    ],
    ids=["legacy-plain", "corrupt-zlib64", "older-client-wrote-beside"],
)
def test_user_data_read(stored, expected):
    """Plain or undecodable user data reads back unchanged; a key that a fablib
    without compression wrote beside the compressed payload is merged over it."""
    obj = ConcreteTemplate()
    _stored_user_data(obj)["user_data"] = json.dumps(stored)
    assert obj.get_user_data() == (stored if expected is None else expected)
