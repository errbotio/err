# coding=utf-8
import logging
import sys
from datetime import timedelta

import pytest

from errbot.backend_plugin_manager import BackendPluginManager
from errbot.backends.test import ShallowConfig
from errbot.bootstrap import CORE_STORAGE, bot_config_defaults
from errbot.storage import StoreMixin
from errbot.storage.base import StoragePluginBase
from errbot.utils import (
    entry_point_plugins,
    format_timedelta,
    split_string_after,
    version2tuple,
)

log = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "v1,v2",
    [
        ("2.0.0", "2.0.1"),
        ("2.0.0", "2.1.0"),
        ("2.0.0", "3.0.0"),
        ("2.0.0-alpha", "2.0.0-beta"),
        ("2.0.0-beta", "2.0.0-rc1"),
        ("2.0.0-rc1", "2.0.0-rc2"),
        ("2.0.0-rc2", "2.0.0-rc3"),
        ("2.0.0-rc2", "2.0.0"),
        ("2.0.0-beta", "2.0.1"),
    ],
)
def test_version_check(v1, v2):
    assert version2tuple(v1) < version2tuple(v2)


@pytest.mark.parametrize(
    "version",
    [
        "1.2.3.4",
        "1.2",
        "1.2.-beta",
        "1.2.3-toto",
        "1.2.3-rc",
    ],
)
def test_version_check_negative(version):
    with pytest.raises(ValueError):
        version2tuple(version)


def test_formattimedelta():
    td = timedelta(0, 60 * 60 + 13 * 60)
    assert "1 hours and 13 minutes" == format_timedelta(td)


def test_storage():
    key = "test"

    __import__("errbot.config-template")
    config = ShallowConfig()
    config.__dict__.update(sys.modules["errbot.config-template"].__dict__)
    bot_config_defaults(config)

    spm = BackendPluginManager(
        config, "errbot.storage", "Memory", StoragePluginBase, CORE_STORAGE
    )
    storage_plugin = spm.load_plugin()

    persistent_object = StoreMixin()
    persistent_object.open_storage(storage_plugin, "test")
    persistent_object[key] = "à value"
    assert persistent_object[key] == "à value"
    assert key in persistent_object
    del persistent_object[key]
    assert key not in persistent_object
    assert len(persistent_object) == 0


def test_split_string_after_returns_original_string_when_chunksize_equals_string_size():
    str_ = "foobar2000" * 2
    splitter = split_string_after(str_, len(str_))
    split = [chunk for chunk in splitter]
    assert [str_] == split


def test_split_string_after_returns_original_string_when_chunksize_equals_string_size_plus_one():
    str_ = "foobar2000" * 2
    splitter = split_string_after(str_, len(str_) + 1)
    split = [chunk for chunk in splitter]
    assert [str_] == split


def test_split_string_after_returns_two_chunks_when_chunksize_equals_string_size_minus_one():
    str_ = "foobar2000" * 2
    splitter = split_string_after(str_, len(str_) - 1)
    split = [chunk for chunk in splitter]
    assert ["foobar2000foobar200", "0"] == split


def test_split_string_after_returns_two_chunks_when_chunksize_equals_half_length_of_string():
    str_ = "foobar2000" * 2
    splitter = split_string_after(str_, int(len(str_) / 2))
    split = [chunk for chunk in splitter]
    assert ["foobar2000", "foobar2000"] == split


def test_entry_point_plugins_no_groups():
    result = entry_point_plugins("does_not_exist")
    assert [] == result


def test_entry_point_plugins_valid_groups():
    results = entry_point_plugins("console_scripts")
    match = False
    for result in results:
        if result.endswith("errbot/errbot.cli"):
            match = True
    assert match
