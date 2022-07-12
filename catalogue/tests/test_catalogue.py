from warnings import filterwarnings

import pytest
from pathlib import Path
import catalogue
try:  # Python 3.8
    import importlib.metadata as importlib_metadata
except (ImportError, ModuleNotFoundError):
    import importlib_metadata  # type: ignore
from .._importlib_metadata import backports
from configparser import ConfigParser
from typing import List


def _from_config(config: ConfigParser) -> List[importlib_metadata.EntryPoint]:
    return [
        importlib_metadata.EntryPoint(name=name, group=group, value=value)
        for group in config.sections()
        for name, value in config.items(group)
    ]


def _from_text(text: str) -> List[importlib_metadata.EntryPoint]:
    config = ConfigParser(delimiters='=')
    # case sensitive: https://stackoverflow.com/q/1611799/812183
    setattr(config, "optionxform", str)
    config.read_string(text)
    return _from_config(config)


@pytest.fixture(autouse=True)
def cleanup():
    catalogue.REGISTRY = {}
    yield


def test_get_set():
    catalogue._set(("a", "b", "c"), "test")
    assert len(catalogue.REGISTRY) == 1
    assert ("a", "b", "c") in catalogue.REGISTRY
    assert catalogue.check_exists("a", "b", "c")
    assert catalogue.REGISTRY[("a", "b", "c")] == "test"
    assert catalogue._get(("a", "b", "c")) == "test"
    with pytest.raises(catalogue.RegistryError):
        catalogue._get(("a", "b", "d"))
    with pytest.raises(catalogue.RegistryError):
        catalogue._get(("a", "b", "c", "d"))
    catalogue._set(("x", "y", "z1"), "test1")
    catalogue._set(("x", "y", "z2"), "test2")
    assert catalogue._remove(("a", "b", "c")) == "test"
    catalogue._set(("x", "y2"), "test3")
    with pytest.raises(catalogue.RegistryError):
        catalogue._remove(("x", "y"))
    assert catalogue._remove(("x", "y", "z2")) == "test2"


def test_registry_get_set():
    test_registry = catalogue.create("test")
    with pytest.raises(catalogue.RegistryError):
        test_registry.get("foo")
    test_registry.register("foo", func=lambda x: x)
    assert "foo" in test_registry


def test_registry_call():
    test_registry = catalogue.create("test")
    test_registry("foo", func=lambda x: x)
    assert "foo" in test_registry


def test_get_all():
    catalogue._set(("a", "b", "c"), "test")
    catalogue._set(("a", "b", "d"), "test")
    catalogue._set(("a", "b"), "test")
    catalogue._set(("b", "a"), "test")
    all_items = catalogue._get_all(("a", "b"))
    assert len(all_items) == 3
    assert ("a", "b", "c") in all_items
    assert ("a", "b", "d") in all_items
    assert ("a", "b") in all_items
    all_items = catalogue._get_all(("a", "b", "c"))
    assert len(all_items) == 1
    assert ("a", "b", "c") in all_items
    assert len(catalogue._get_all(("a", "b", "c", "d"))) == 0


def test_create_single_namespace():
    test_registry = catalogue.create("test")
    assert catalogue.REGISTRY == {}

    @test_registry.register("a")
    def a():
        pass

    def b():
        pass

    test_registry.register("b", func=b)
    items = test_registry.get_all()
    assert len(items) == 2
    assert items["a"] == a
    assert items["b"] == b
    assert catalogue.check_exists("test", "a")
    assert catalogue.check_exists("test", "b")
    assert catalogue._get(("test", "a")) == a
    assert catalogue._get(("test", "b")) == b

    with pytest.raises(TypeError):
        # The decorator only accepts one argument
        @test_registry.register("x", "y")
        def x():
            pass


def test_create_multi_namespace():
    test_registry = catalogue.create("x", "y")

    @test_registry.register("z")
    def z():
        pass

    items = test_registry.get_all()
    assert len(items) == 1
    assert items["z"] == z
    assert catalogue.check_exists("x", "y", "z")
    assert catalogue._get(("x", "y", "z")) == z


def test_entry_points():
    # Create a new EntryPoint object by pretending we have a setup.cfg and
    # use one of catalogue's util functions as the advertised function
    ep_string = "[options.entry_points]test_foo\n    bar = catalogue:check_exists"
    ep = _from_text(ep_string)
    catalogue.AVAILABLE_ENTRY_POINTS["test_foo"] = ep
    assert catalogue.REGISTRY == {}
    test_registry = catalogue.create("test", "foo", entry_points=True)
    entry_points = test_registry.get_entry_points()
    assert "bar" in entry_points
    assert entry_points["bar"] == catalogue.check_exists
    assert test_registry.get_entry_point("bar") == catalogue.check_exists
    assert catalogue.REGISTRY == {}
    assert test_registry.get("bar") == catalogue.check_exists
    assert test_registry.get_all() == {"bar": catalogue.check_exists}
    assert "bar" in test_registry


def test_registry_find():
    test_registry = catalogue.create("test_registry_find")
    name = "a"

    @test_registry.register(name)
    def a():
        """This is a registered function."""
        pass

    info = test_registry.find(name)
    assert info["module"] == "catalogue.tests.test_catalogue"
    assert info["file"] == str(Path(__file__))
    assert info["docstring"] == "This is a registered function."
    assert info["line_no"]


@pytest.mark.issue(32)
def test_selectable_group_interface():
    """Checks if the SelectableGroups dict interface works with backports.
    See https://github.com/python/importlib_metadata/pull/278 and
    https://github.com/python/importlib_metadata/issues/298 for further context.
    """
    filterwarnings('error')
    backports.entry_points().get("test")
