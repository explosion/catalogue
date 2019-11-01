# coding: utf8
from __future__ import unicode_literals

from collections import OrderedDict
import functools
import sys

if sys.version_info[0] == 2:
    basestring_ = basestring  # noqa: F821
else:
    basestring_ = str


# This is where functions will be registered
REGISTRY = OrderedDict()


def create(*namespace):
    """Create a new registry."""
    if check_exists(*namespace):
        raise RegistryError("Namespace already exists: {}".format(namespace))
    return functools.partial(register, namespace)


def check_exists(*namespace):
    """Check if a namespace exists.

    *namespace (str): The namespace.
    RETURNS (bool): Whether the namespace exists.
    """
    return namespace in REGISTRY


def register(namespace, name, **kwargs):
    """Register a function for a given namespace. Can be called as a function
    or used as a decorator.

    namespace (List[str]): The namespace to register.
    name (str): The name to register under the namespace.
    func (Callable): Optional function to register (if not used as decorator).
    RETURNS (Callable): The decorator.
    """

    def do_registration(func):
        _set(list(namespace) + [name], func)
        return func

    func = kwargs.get("func")
    if func is not None:
        return do_registration(func)
    return do_registration


def _get(namespace):
    """Get the value for a given namespace.

    namespace (List[str]): The namespace.
    RETURNS: The value for the namespace.
    """
    global REGISTRY
    if not all(isinstance(name, basestring_) for name in namespace):
        err = "Invalid namespace. Expected list of strings, but got: {}"
        raise ValueError(err.format(namespace))
    namespace = tuple(namespace)
    if namespace not in REGISTRY:
        err = "Can't get namespace {} (not in registry)".format(namespace)
        raise RegistryError(err)
    return REGISTRY[namespace]


def _set(namespace, func):
    """Set a value for a given namespace.

    namespace (List[str]): The namespace.
    func (Callable): The value to set.
    """
    global REGISTRY
    REGISTRY[tuple(namespace)] = func


def _get_all(namespace):
    global REGISTRY
    result = OrderedDict()
    for keys, value in REGISTRY.items():
        if len(namespace) <= len(keys) and all(
            namespace[i] == keys[i] for i in range(len(namespace))
        ):
            result[keys] = value
    return result


def _remove(namespace):
    global REGISTRY
    namespace = tuple(namespace)
    if namespace not in REGISTRY:
        err = "Can't get namespace {} (not in registry)".format(namespace)
        raise RegistryError(err)
    removed = REGISTRY[namespace]
    del REGISTRY[namespace]
    return removed


class RegistryError(ValueError):
    pass
