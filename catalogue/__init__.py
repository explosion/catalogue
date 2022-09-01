from typing import Sequence, Any, Dict, Tuple, Callable, Optional, TypeVar, Union
from typing import List
import inspect
import re
from collections import defaultdict

try:  # Python 3.8
    import importlib.metadata as importlib_metadata
except ImportError:
    from . import _importlib_metadata as importlib_metadata  # type: ignore

try:  # Python 3.10
    from importlib.metadata import SelectableGroups  # type: ignore
except ImportError:

    class _NotImplemented:
        pass

    SelectableGroups = _NotImplemented  # type: ignore

# Only ever call this once for performance reasons
AVAILABLE_ENTRY_POINTS = importlib_metadata.entry_points()  # type: ignore

# This is where functions will be registered
REGISTRY: Dict[Tuple[str, ...], Dict[int, Any]] = defaultdict(dict)


InFunc = TypeVar("InFunc")


def create(*namespace: str, entry_points: bool = False) -> "Registry":
    """Create a new registry.

    *namespace (str): The namespace, e.g. "spacy" or "spacy", "architectures".
    entry_points (bool): Accept registered functions from entry points.
    RETURNS (Registry): The Registry object.
    """
    if check_exists(*namespace):
        raise RegistryError(f"Namespace already exists: {namespace}")
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
        name, version = _parse_version(name)
        namespace = tuple(list(self.namespace) + [name])
        has_entry_point = self.entry_points and self.get_entry_point(name)
        return has_entry_point or namespace in REGISTRY

    def __call__(
        self, name: str, func: Optional[Any] = None, version: Optional[int] = None
    ) -> Callable[[InFunc], InFunc]:
        """Register a function for a given namespace. Same as Registry.register.

        name (str): The name to register under the namespace.
        func (Any): Optional function to register (if not used as decorator).
        RETURNS (Callable): The decorator.
        """
        return self.register(name, func=func, version=version)

    def register(
        self, name: str, *, func: Optional[Any] = None, version: Optional[int] = None
    ) -> Callable[[InFunc], InFunc]:
        """Register a function for a given namespace.

        name (str): The name to register under the namespace.
        func (Any): Optional function to register (if not used as decorator).
        RETURNS (Callable): The decorator.
        """
        if version is None:
            name, version = _parse_version(name)

        def do_registration(func):
            _set(list(self.namespace) + [name], func, version)
            return func

        if func is not None:
            return do_registration(func)
        return do_registration

    def get(self, name: str, *, version: Optional[int] = None) -> Any:
        """Get the registered function for a given name.

        name (str): The name.
        RETURNS (Any): The registered function.
        """
        if version is None:
            name, version = _parse_version(name)
        if self.entry_points:
            from_entry_point = self.get_entry_point(name)
            if from_entry_point:
                return from_entry_point
        namespace = list(self.namespace) + [name]
        if not check_exists(*namespace):
            current_namespace = " -> ".join(self.namespace)
            available = ", ".join(sorted(self.get_all().keys())) or "none"
            raise RegistryError(
                f"Cant't find '{name}' in registry {current_namespace}. Available names: {available}"
            )
        if version is None:
            version = -1
        return _get(namespace, version)

    def get_all(self) -> Dict[str, Any]:
        """Get all functions belonging to this registry's namespace.
        If there are more version for the same function return then in
        "func.v1" format otherwise just "func".

        RETURNS (Dict[str, Any]): The functions, keyed by name.
        """
        global REGISTRY
        result = {}
        if self.entry_points:
            result.update(self.get_entry_points())
        # Create a copy of the global registry in case it gets modified during iteration.
        for keys, versions in REGISTRY.copy().items():
            if len(self.namespace) == len(keys) - 1 and keys[:-1] == self.namespace:
                if len(versions) > 1:
                    for version, value in versions.items():
                        result[f"{keys[-1]}.v{version}"] = value
                else:
                    result[keys[-1]] = list(versions.values())[0]
        return result

    def get_entry_points(self) -> Dict[str, Any]:
        """Get registered entry points from other packages for this namespace.

        RETURNS (Dict[str, Any]): Entry points, keyed by name.
        """
        result = {}
        for entry_point in self._get_entry_points():
            result[entry_point.name] = entry_point.load()
        return result

    def get_entry_point(self, name: str, default: Optional[Any] = None) -> Any:
        """Check if registered entry point is available for a given name in the
        namespace and load it. Otherwise, return the default value.

        name (str): Name of entry point to load.
        default (Any): The default value to return.
        RETURNS (Any): The loaded entry point or the default value.
        """
        for entry_point in self._get_entry_points():
            if entry_point.name == name:
                return entry_point.load()
        return default

    def _get_entry_points(self) -> List[importlib_metadata.EntryPoint]:
        if isinstance(AVAILABLE_ENTRY_POINTS, SelectableGroups):
            return AVAILABLE_ENTRY_POINTS.select(group=self.entry_point_namespace)
        else:  # dict
            return AVAILABLE_ENTRY_POINTS.get(self.entry_point_namespace, [])

    def find(self, name: str, *, version: Optional[int] = None) -> Dict[str, Optional[Union[str, int]]]:
        """Find the information about a registered function, including the
        module and path to the file it's defined in, the line number and the
        docstring, if available.

        name (str): Name of the registered function.
        RETURNS (Dict[str, Optional[Union[str, int]]]): The function info.
        """
        if version is None:
            name, version = _parse_version(name)
        func = self.get(name, version=version)
        module = inspect.getmodule(func)
        # These calls will fail for Cython modules so we need to work around them
        line_no: Optional[int] = None
        file_name: Optional[str] = None
        try:
            _, line_no = inspect.getsourcelines(func)
            file_name = inspect.getfile(func)
        except (TypeError, ValueError):
            pass
        docstring = inspect.getdoc(func)
        return {
            "module": module.__name__ if module else None,
            "file": file_name,
            "line_no": line_no,
            "docstring": inspect.cleandoc(docstring) if docstring else None,
        }


def check_exists(*namespace: str) -> bool:
    """Check if a namespace exists.

    *namespace (str): The namespace.
    RETURNS (bool): Whether the namespace exists.
    """
    return namespace in REGISTRY


def _get(namespace: Sequence[str], version: Optional[int] = None) -> Any:
    """Get the value for a given namespace.

    namespace (Sequence[str]): The namespace.
    version (int): Version of the value.
        If -1 or non-existent version is provided returns highest.
    RETURNS (Any): The value for the namespace.
    """
    global REGISTRY
    if not all(isinstance(name, str) for name in namespace):
        raise ValueError(
            f"Invalid namespace. Expected tuple of strings, but got: {namespace}"
        )
    namespace = tuple(namespace)
    if namespace not in REGISTRY:
        raise RegistryError(f"Can't get namespace {namespace} (not in registry)")

    if version not in REGISTRY[namespace] or version is None or version == -1:
        version = max(REGISTRY[namespace].keys())
    return REGISTRY[namespace][version]


def _get_all(namespace: Sequence[str]) -> Dict[Tuple[str, ...], Any]:
    """Get all matches for a given namespace, e.g. ("a", "b", "c") and
    ("a", "b") for namespace ("a", "b").

    namespace (Sequence[str]): The namespace.
    RETURNS (Dict[Tuple[str], Any]): All entries for the namespace, keyed
        by their full namespaces.
    """
    global REGISTRY
    result = {}
    for keys, value in REGISTRY.copy().items():
        if len(namespace) <= len(keys) and all(
            namespace[i] == keys[i] for i in range(len(namespace))
        ):
            result[keys] = value
    return result


def _set(namespace: Sequence[str], func: Any, version: Optional[int] = None) -> None:
    """Set a value for a given namespace.

    namespace (Sequence[str]): The namespace.
    func (Callable): The value to set.
    """
    if version is None:
        version = 1
    global REGISTRY
    REGISTRY[tuple(namespace)][version] = func


def _remove(namespace: Sequence[str], version: Optional[int] = None) -> Any:
    """Remove a value for a given namespace.

    namespace (Sequence[str]): The namespace.
    version (int): The version to remove, if None provided remove all.
    RETURNS (Any): The removed value.
    """
    global REGISTRY
    namespace = tuple(namespace)
    if namespace not in REGISTRY:
        raise RegistryError(f"Can't get namespace {namespace} (not in registry)")
    if version is not None:
        removed = REGISTRY[namespace][version]
        del REGISTRY[namespace][version]
        return removed
    else:
        version = max(REGISTRY[namespace].keys())
        latest = REGISTRY[namespace][version]
        del REGISTRY[namespace]
        return latest


def _parse_version(name) -> Tuple[str, int]:
    """
    Parse version number from name.
    Versions are integers like func.v3 or func.v49.
    """
    vstr = re.search(r"\.v[0-9]+$", name)
    if vstr is not None:
        version = int(name[vstr.start() + 2:])
        return name[:vstr.start()], version
    else:
        return name, 1


class RegistryError(ValueError):
    pass
