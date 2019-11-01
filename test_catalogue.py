# coding: utf8
from __future__ import unicode_literals

import pytest
import catalogue


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


def test_get_all():
    catalogue._set(("a", "b", "c"), "test")
    catalogue._set(("a", "b", "d"), "test")
    catalogue._set(("a", "b"), "test")
    catalogue._set(("b", "a"), "test")
    all_items = catalogue.get_all(("a", "b"))
    assert len(all_items) == 3
    assert ("a", "b", "c") in all_items
    assert ("a", "b", "d") in all_items
    assert ("a", "b") in all_items
    all_items = catalogue.get_all(("a", "b", "c"))
    assert len(all_items) == 1
    assert ("a", "b", "c") in all_items
    assert len(catalogue.get_all(("a", "b", "c", "d"))) == 0


def test_create_single_namespace():
    register_test, get_test = catalogue.create("test")
    assert catalogue.REGISTRY == {}

    @register_test("a")
    def a():
        pass

    def b():
        pass

    register_test("b", func=b)
    items = get_test()
    assert len(items) == 2
    assert items["a"] == a
    assert items["b"] == b
    assert catalogue.check_exists("test", "a")
    assert catalogue.check_exists("test", "b")
    assert catalogue._get(("test", "a")) == a
    assert catalogue._get(("test", "b")) == b

    with pytest.raises(TypeError):
        # The decorator only accepts one argument
        @register_test("x", "y")
        def x():
            pass


def test_create_multi_namespace():
    register_test, get_test = catalogue.create("x", "y")

    @register_test("z")
    def z():
        pass

    items = get_test()
    assert len(items) == 1
    assert items["z"] == z
    assert catalogue.check_exists("x", "y", "z")
    assert catalogue._get(("x", "y", "z")) == z
