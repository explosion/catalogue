from typing import Sequence, Any, Dict, Tuple, Callable, Optional, TypeVar, Union
import inspect

try:  # Python 3.8
    import importlib.metadata as importlib_metadata
except ImportError:
    import importlib_metadata  # type: ignore

# Only ever call this once for performance reasons
AVAILABLE_ENTRY_POINTS = importlib_metadata.entry_points()  # type: ignore

# This is where functions will be registered
REGISTRY: Dict[Tuple[str, ...], Any] = {}


InFunc = TypeVar("InFunc")


def create(*namespace: str, entry_points: bool = False) -> "Registry":
    """Create a new registry.

    *namespace (str): The namespace, e.g. "spacy" or "spacy", "architectures".
    entry_points (bool): Accept registered functions from entry points.
    RETURNS (Registry): The Registry object.
    """
    if check_exists(*namespace):
        raise RegistryError("Namespace already exists: {}".format(namespace))
    return Registry(namespace, entry_points=entry_points)


class Registry(object):
    def __init__(self, namespace: Sequence[str], entry_points: bool = False) -> None:
        """Initialize a new registry.

        namespace (Sequence[str]): The namespace.
        entry_points (bool): Whether to also check for entry points.
        """
        self.namespace = namespace
        self.entry_point_namespace = "_".join(namespace)
        self.entry_points = entry_points

    def __contains__(self, name: str) -> bool:
        """Check whether a name is in the registry.

        name (str): The name to check.
        RETURNS (bool): Whether the name is in the registry.
        """
        namespace = tuple(list(self.namespace) + [name])
        has_entry_point = self.entry_points and self.get_entry_point(name)
        return has_entry_point or namespace in REGISTRY

    def __call__(
        self, name: str, func: Optional[Any] = None
    ) -> Callable[[InFunc], InFunc]:
        """Register a function for a given namespace. Same as Registry.register.

        name (str): The name to register under the namespace.
        func (Any): Optional function to register (if not used as decorator).
        RETURNS (Callable): The decorator.
        """
        return self.register(name, func=func)

    def register(
        self, name: str, *, func: Optional[Any] = None
    ) -> Callable[[InFunc], InFunc]:
        """Register a function for a given namespace.

        name (str): The name to register under the namespace.
        func (Any): Optional function to register (if not used as decorator).
        RETURNS (Callable): The decorator.
        """

        def do_registration(func):
            _set(list(self.namespace) + [name], func)
            return func

        if func is not None:
            return do_registration(func)
        return do_registration

    def get(self, name: str) -> Any:
        """Get the registered function for a given name.

        name (str): The name.
        RETURNS (Any): The registered function.
        """
        if self.entry_points:
            from_entry_point = self.get_entry_point(name)
            if from_entry_point:
                return from_entry_point
            # load all modules in entry points to make sure we register functions from 
            # those modules
            for entry_point in AVAILABLE_ENTRY_POINTS.get(self.entry_point_namespace, []):
                entry_point.load()
        namespace = list(self.namespace) + [name]
        if not check_exists(*namespace):
            err = "Cant't find '{}' in registry {}. Available names: {}"
            current_namespace = " -> ".join(self.namespace)
            available = ", ".join(sorted(self.get_all().keys())) or "none"
            raise RegistryError(err.format(name, current_namespace, available))
        return _get(namespace)

    def get_all(self) -> Dict[str, Any]:
        """Get a all functions for a given namespace.

        namespace (Tuple[str]): The namespace to get.
        RETURNS (Dict[str, Any]): The functions, keyed by name.
        """
        global REGISTRY
        result = {}
        if self.entry_points:
            result.update(self.get_entry_points())
        for keys, value in REGISTRY.items():
            if len(self.namespace) == len(keys) - 1 and all(
                self.namespace[i] == keys[i] for i in range(len(self.namespace))
            ):
                result[keys[-1]] = value
        return result

    def get_entry_points(self) -> Dict[str, Any]:
        """Get registered entry points from other packages for this namespace.

        RETURNS (Dict[str, Any]): Entry points, keyed by name.
        """
        result = {}
        for entry_point in AVAILABLE_ENTRY_POINTS.get(self.entry_point_namespace, []):
            result[entry_point.name] = entry_point.load()
        return result

    def get_entry_point(self, name: str, default: Optional[Any] = None) -> Any:
        """Check if registered entry point is available for a given name in the
        namespace and load it. Otherwise, return the default value.

        name (str): Name of entry point to load.
        default (Any): The default value to return.
        RETURNS (Any): The loaded entry point or the default value.
        """
        for entry_point in AVAILABLE_ENTRY_POINTS.get(self.entry_point_namespace, []):
            if entry_point.name == name:
                return entry_point.load()
        return default

    def find(self, name: str) -> Dict[str, Optional[Union[str, int]]]:
        """Find the information about a registered function, including the
        module and path to the file it's defined in, the line number and the
        docstring, if available.

        name (str): Name of the registered function.
        RETURNS (Dict[str, Optional[Union[str, int]]]): The function info.
        """
        func = self.get(name)
        _, line_no = inspect.getsourcelines(func)
        module = inspect.getmodule(func)
        docstring = inspect.getdoc(func)
        return {
            "module": module.__name__ if module else None,
            "file": inspect.getfile(func),
            "line_no": line_no,
            "docstring": inspect.cleandoc(docstring) if docstring else None,
        }


def check_exists(*namespace: str) -> bool:
    """Check if a namespace exists.

    *namespace (str): The namespace.
    RETURNS (bool): Whether the namespace exists.
    """
    return namespace in REGISTRY


def _get(namespace: Sequence[str]) -> Any:
    """Get the value for a given namespace.

    namespace (Sequence[str]): The namespace.
    RETURNS (Any): The value for the namespace.
    """
    global REGISTRY
    if not all(isinstance(name, str) for name in namespace):
        err = "Invalid namespace. Expected tuple of strings, but got: {}"
        raise ValueError(err.format(namespace))
    namespace = tuple(namespace)
    if namespace not in REGISTRY:
        err = "Can't get namespace {} (not in registry)".format(namespace)
        raise RegistryError(err)
    return REGISTRY[namespace]


def _get_all(namespace: Sequence[str]) -> Dict[Tuple[str, ...], Any]:
    """Get all matches for a given namespace, e.g. ("a", "b", "c") and
    ("a", "b") for namespace ("a", "b").

    namespace (Sequence[str]): The namespace.
    RETURNS (Dict[Tuple[str], Any]): All entries for the namespace, keyed
        by their full namespaces.
    """
    global REGISTRY
    result = {}
    for keys, value in REGISTRY.items():
        if len(namespace) <= len(keys) and all(
            namespace[i] == keys[i] for i in range(len(namespace))
        ):
            result[keys] = value
    return result


def _set(namespace: Sequence[str], func: Any) -> None:
    """Set a value for a given namespace.

    namespace (Sequence[str]): The namespace.
    func (Callable): The value to set.
    """
    global REGISTRY
    REGISTRY[tuple(namespace)] = func


def _remove(namespace: Sequence[str]) -> Any:
    """Remove a value for a given namespace.

    namespace (Sequence[str]): The namespace.
    RETURNS (Any): The removed value.
    """
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
