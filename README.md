<a href="https://explosion.ai"><img src="https://explosion.ai/assets/img/logo.svg" width="125" height="125" align="right" /></a>

# catalogue: Lightweight function registries and configurations for your library

`catalogue` is a small library that

- makes it easy to **add function (or object) registries** to your code
- offers a **configuration system** letting you conveniently describe arbitrary trees of objects.

_Function registries_ are helpful when you have objects that need to be both easily serializable and fully
customizable. Instead of passing a function into your object, you pass in an
identifier name, which the object can use to lookup the function from the
registry. This makes the object easy to serialize, because the name is a simple
string. If you instead saved the function, you'd have to use Pickle for
serialization, which has many drawbacks.

_Configuration_ is a huge challenge for machine-learning code because you may want to expose almost any
detail of any function as a hyperparameter. The setting you want to expose might be arbitrarily far
down in your call stack, so it might need to pass all the way through the CLI or REST API,
through any number of intermediate functions, affecting the interface of everything along the way.
And then once those settings are added, they become hard to remove later. Default values also
become hard to change without breaking backwards compatibility.

To solve this problem, `catalogue` offers a config system that lets you easily describe arbitrary trees of objects.
The objects can be created via function calls you register using a simple decorator syntax. You can even version the
functions you create, allowing you to make improvements without breaking backwards compatibility. The most similar
config system we’re aware of is [Gin](https://github.com/google/gin-config), which uses a similar syntax, and also allows you to link the configuration system
to functions in your code using a decorator. `catalogue`'s config system is simpler and emphasizes a different workflow via a
subset of Gin’s functionality.

[![Azure Pipelines](https://img.shields.io/azure-devops/build/explosion-ai/public/14/master.svg?logo=azure-pipelines&style=flat-square&label=build)](https://dev.azure.com/explosion-ai/public/_build?definitionId=14)
[![Current Release Version](https://img.shields.io/github/v/release/explosion/catalogue.svg?style=flat-square&include_prereleases&logo=github)](https://github.com/explosion/catalogue/releases)
[![pypi Version](https://img.shields.io/pypi/v/catalogue.svg?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/catalogue/)
[![conda Version](https://img.shields.io/conda/vn/conda-forge/catalogue.svg?style=flat-square&logo=conda-forge&logoColor=white)](https://anaconda.org/conda-forge/catalogue)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/ambv/black)

## ⏳ Installation

```bash
pip install catalogue
```

```bash
conda install -c conda-forge catalogue
```

> ⚠️ **Important note:** `catalogue` v2.0+ is only compatible with Python 3.6+.
> For Python 2.7+ compatibility, use `catalogue` v1.x.

## 👩‍💻 Usage

### Function registry

Let's imagine you're developing a Python package that needs to load data
somewhere. You've already implemented some loader functions for the most common
data types, but you want to allow the user to easily add their own. Using
`catalogue.create` you can create a new registry under the namespace
`your_package` &rarr; `loaders`.

```python
# YOUR PACKAGE
import catalogue

loaders = catalogue.create("your_package", "loaders")
```

This gives you a `loaders.register` decorator that your users can import and
decorate their custom loader functions with.

```python
# USER CODE
from your_package import loaders

@loaders.register("custom_loader")
def custom_loader(data):
    # Load something here...
    return data
```

The decorated function will be registered automatically and in your package,
you'll be able to access all loaders by calling `loaders.get_all`.

```python
# YOUR PACKAGE
def load_data(data, loader_id):
    print("All loaders:", loaders.get_all()) # {"custom_loader": <custom_loader>}
    loader = loaders.get(loader_id)
    return loader(data)
```

The user can now refer to their custom loader using only its string name
(`"custom_loader"`) and your application will know what to do and will use their
custom function.

```python
# USER CODE
from your_package import load_data

load_data(data, loader_id="custom_loader")
```

### Configurations

The configuration system parses a `.cfg` file like

```ini
[training]
patience = 10
dropout = 0.2
use_vectors = false

[training.logging]
level = "INFO"

[nlp]
# This uses the value of training.use_vectors
use_vectors = ${training.use_vectors}
lang = "en"
```

and resolves it to a `Dict`:

```json
{
  "training": {
    "patience": 10,
    "dropout": 0.2,
    "use_vectors": false,
    "logging": {
      "level": "INFO"
    }
  },
  "nlp": {
    "use_vectors": false,
    "lang": "en"
  }
}
```

The config is divided into sections, with the section name in square brackets – for
example, `[training]`. Within the sections, config values can be assigned to keys using `=`. Values can also be referenced
from other sections using the dot notation and placeholders indicated by the dollar sign and curly braces. For example,
`${training.use_vectors}` will receive the value of use_vectors in the training block. This is useful for settings that
are shared across components.

The config format has three main differences from Python’s built-in configparser:

1. JSON-formatted values. `catalogue` passes all values through `json.loads` to interpret them. You can use atomic
   values like strings, floats, integers or booleans, or you can use complex objects such as lists or maps.
2. Structured sections. `catalogue` uses a dot notation to build nested sections. If you have a section named
   `[section.subsection]`, `catalogue` will parse that into a nested structure, placing subsection within section.
3. References to registry functions. If a key starts with `@`, `catalogue` will interpret its value as the name of a
   function registry, load the function registered for that name and pass in the rest of the block as arguments. If type
   hints are available on the function, the argument values (and return value of the function) will be validated against
   them. This lets you express complex configurations, like a training pipeline where `batch_size` is populated by a
   function that yields floats.

There’s no pre-defined scheme you have to follow; how you set up the top-level sections is up to you. At the end of
it, you’ll receive a dictionary with the values that you can use in your script – whether it’s complete initialized
functions, or just basic settings.

For instance, let’s say you want to define a new optimizer. You'd define its arguments in `config.cfg` like so:

```ini
[optimizer]
@optimizers = "my_cool_optimizer.v1"
learn_rate = 0.001
gamma = 1e-8
```

To load and parse this configuration:

```python
import dataclasses
from typing import Union, Iterable

from catalogue import catalogue_registry, Config

# Create a new registry.
catalogue_registry.create("optimizers")


# Define a dummy optimizer class.
@dataclasses.dataclass
class MyCoolOptimizer:
    learn_rate: float
    gamma: float


@catalogue_registry.optimizers.register("my_cool_optimizer.v1")
def make_my_optimizer(learn_rate: Union[float, Iterable[float]], gamma: float):
    return MyCoolOptimizer(learn_rate, gamma)


# Load the config file from disk, resolve it and fetch the instantiated optimizer object.
config = Config().from_disk("./config.cfg")
resolved = catalogue_registry.resolve(config)
optimizer = resolved["optimizer"]  # MyCoolOptimizer(learn_rate=0.001, gamma=1e-08)
```

Under the hood, `catalogue` will look up the `"my_cool_optimizer.v1"` function in the "optimizers" registry and then
call it with the arguments `learn_rate` and `gamma`. If the function has type annotations, it will also validate the
input. For instance, if `learn_rate` is annotated as a float and the config defines a string, `catalogue` will raise an
error.

The Thinc documentation offers further information on the configuration system:

- [recursive blocks](https://thinc.ai/docs/usage-config#registry-recursive)
- [defining variable positional arguments](https://thinc.ai/docs/usage-config#registries-args)
- [using interpolation](https://thinc.ai/docs/usage-config#config-interpolation)
- [using custom registries](https://thinc.ai/docs/usage-config#registries-custom)
- [advanced type annotations with Pydantic](https://thinc.ai/docs/usage-config#advanced-types)
- [using base schemas](https://thinc.ai/docs/usage-config#advanced-types-base-schema)
- [filling a configuration with defaults](https://thinc.ai/docs/usage-config#advanced-types-fill-defaults)

## ❓ FAQ

#### But can't the user just pass in the `custom_loader` function directly?

Sure, that's the more classic callback approach. Instead of a string ID,
`load_data` could also take a function, in which case you wouldn't need a
package like this. `catalogue` helps you when you need to produce a serializable
record of which functions were passed in. For instance, you might want to write
a log message, or save a config to load back your object later. With
`catalogue`, your functions can be parameterized by strings, so logging and
serialization remains easy – while still giving you full extensibility.

#### How do I make sure all of the registration decorators have run?

Decorators normally run when modules are imported. Relying on this side-effect
can sometimes lead to confusion, especially if there's no other reason the
module would be imported. One solution is to use
[entry points](https://packaging.python.org/specifications/entry-points/).

For instance, in [spaCy](https://spacy.io) we're starting to use function
registries to make the pipeline components much more customizable. Let's say one
user, Jo, develops a better tagging model using new machine learning research.
End-users of Jo's package should be able to write
`spacy.load("jo_tagging_model")`. They shouldn't need to remember to write
`import jos_tagged_model` first, just to run the function registries as a
side-effect. With entry points, the registration happens at install time – so
you don't need to rely on the import side-effects.

## 🎛 API

### Registry

#### <kbd>function</kbd> `catalogue.create`

Create a new registry for a given namespace. Returns a setter function that can
be used as a decorator or called with a name and `func` keyword argument. If
`entry_points=True` is set, the registry will check for
[Python entry points](https://packaging.python.org/tutorials/packaging-projects/#entry-points)
advertised for the given namespace, e.g. the entry point group
`spacy_architectures` for the namespace `"spacy", "architectures"`, in
`Registry.get` and `Registry.get_all`. This allows other packages to
auto-register functions.

| Argument       | Type       | Description                                                                                    |
| -------------- | ---------- | ---------------------------------------------------------------------------------------------- |
| `*namespace`   | `str`      | The namespace, e.g. `"spacy"` or `"spacy", "architectures"`.                                   |
| `entry_points` | `bool`     | Whether to check for entry points of the given namespace and pre-populate the global registry. |
| **RETURNS**    | `Registry` | The `Registry` object with methods to register and retrieve functions.                         |

```python
architectures = catalogue.create("spacy", "architectures")

# Use as decorator
@architectures.register("custom_architecture")
def custom_architecture():
    pass

# Use as regular function
architectures.register("custom_architecture", func=custom_architecture)
```

#### <kbd>class</kbd> `Registry`

The registry object that can be used to register and retrieve functions. It's
usually created internally when you call `catalogue.create`.

##### <sup><kbd>method</kbd> `Registry.__init__`</sup>

Initialize a new registry. If `entry_points=True` is set, the registry will
check for
[Python entry points](https://packaging.python.org/tutorials/packaging-projects/#entry-points)
advertised for the given namespace, e.g. the entry point group
`spacy_architectures` for the namespace `"spacy", "architectures"`, in
`Registry.get` and `Registry.get_all`.

| Argument       | Type         | Description                                                                      |
| -------------- | ------------ | -------------------------------------------------------------------------------- |
| `namespace`    | `Tuple[str]` | The namespace, e.g. `"spacy"` or `"spacy", "architectures"`.                     |
| `entry_points` | `bool`       | Whether to check for entry points of the given namespace in `get` and `get_all`. |
| **RETURNS**    | `Registry`   | The newly created object.                                                        |

```python
# User-facing API
architectures = catalogue.create("spacy", "architectures")
# Internal API
architectures = Registry(("spacy", "architectures"))
```

##### <sup><kbd>method</kbd> `Registry.__contains__`</sup>

Check whether a name is in the registry.

| Argument    | Type   | Description                          |
| ----------- | ------ | ------------------------------------ |
| `name`      | `str`  | The name to check.                   |
| **RETURNS** | `bool` | Whether the name is in the registry. |

```python
architectures = catalogue.create("spacy", "architectures")

@architectures.register("custom_architecture")
def custom_architecture():
    pass

assert "custom_architecture" in architectures
```

##### <sup><kbd>method</kbd> `Registry.__call__`</sup>

Register a function in the registry's namespace. Can be used as a decorator or
called as a function with the `func` keyword argument supplying the function to
register. Delegates to `Registry.register`.

##### <sup><kbd>method</kbd> `Registry.register`</sup>

Register a function in the registry's namespace. Can be used as a decorator or
called as a function with the `func` keyword argument supplying the function to
register.

| Argument    | Type       | Description                                               |
| ----------- | ---------- | --------------------------------------------------------- |
| `name`      | `str`      | The name to register under the namespace.                 |
| `func`      | `Any`      | Optional function to register (if not used as decorator). |
| **RETURNS** | `Callable` | The decorator that takes one argument, the name.          |

```python
architectures = catalogue.create("spacy", "architectures")

# Use as decorator
@architectures.register("custom_architecture")
def custom_architecture():
    pass

# Use as regular function
architectures.register("custom_architecture", func=custom_architecture)
```

##### <sup><kbd>method</kbd> `Registry.get`</sup>

Get a function registered in the namespace.

| Argument    | Type  | Description              |
| ----------- | ----- | ------------------------ |
| `name`      | `str` | The name.                |
| **RETURNS** | `Any` | The registered function. |

```python
custom_architecture = architectures.get("custom_architecture")
```

##### <sup><kbd>method</kbd> `Registry.get_all`</sup>

Get all functions in the registry's namespace.

| Argument    | Type             | Description                              |
| ----------- | ---------------- | ---------------------------------------- |
| **RETURNS** | `Dict[str, Any]` | The registered functions, keyed by name. |

```python
all_architectures = architectures.get_all()
# {"custom_architecture": <custom_architecture>}
```

##### <sup><kbd>method</kbd> `Registry.get_entry_points`</sup>

Get registered entry points from other packages for this namespace. The name of
the entry point group is the namespace joined by `_`.

| Argument    | Type             | Description                             |
| ----------- | ---------------- | --------------------------------------- |
| **RETURNS** | `Dict[str, Any]` | The loaded entry points, keyed by name. |

```python
architectures = catalogue.create("spacy", "architectures", entry_points=True)
# Will get all entry points of the group "spacy_architectures"
all_entry_points = architectures.get_entry_points()
```

##### <sup><kbd>method</kbd> `Registry.get_entry_point`</sup>

Check if registered entry point is available for a given name in the namespace
and load it. Otherwise, return the default value.

| Argument    | Type  | Description                                      |
| ----------- | ----- | ------------------------------------------------ |
| `name`      | `str` | Name of entry point to load.                     |
| `default`   | `Any` | The default value to return. Defaults to `None`. |
| **RETURNS** | `Any` | The loaded entry point or the default value.     |

```python
architectures = catalogue.create("spacy", "architectures", entry_points=True)
# Will get entry point "custom_architecture" of the group "spacy_architectures"
custom_architecture = architectures.get_entry_point("custom_architecture")
```

##### <sup><kbd>method</kbd> `Registry.find`</sup>

Find the information about a registered function, including the
module and path to the file it's defined in, the line number and the
docstring, if available.

| Argument    | Type                         | Description                         |
| ----------- | ---------------------------- | ----------------------------------- |
| `name`      | `str`                        | Name of the registered function.    |
| **RETURNS** | `Dict[str, Union[str, int]]` | The information about the function. |

```python
import catalogue

architectures = catalogue.create("spacy", "architectures", entry_points=True)

@architectures("my_architecture")
def my_architecture():
    """This is an architecture"""
    pass

info = architectures.find("my_architecture")
# {'module': 'your_package.architectures',
#  'file': '/path/to/your_package/architectures.py',
#  'line_no': 5,
#  'docstring': 'This is an architecture'}
```

#### <kbd>function</kbd> `catalogue.check_exists`

Check if a namespace exists.

| Argument     | Type   | Description                                                  |
| ------------ | ------ | ------------------------------------------------------------ |
| `*namespace` | `str`  | The namespace, e.g. `"spacy"` or `"spacy", "architectures"`. |
| **RETURNS**  | `bool` | Whether the namespace exists.                                |

### Config

#### <kbd>class</kbd> `Config`

This class holds the model and training [configuration](https://thinc.ai/docs/usage-config) and can load and save the
INI-style configuration format from/to a string, file or bytes. The `Config` class is a subclass of `dict` and uses
Python’s `ConfigParser` under the hood.

##### <sup><kbd>method</kbd> `Config.__init__`</sup>

Initialize a new `Config` object with optional data.

```python
from catalogue import Config
config = Config({"training": {"patience": 10, "dropout": 0.2}})
```

| Argument          | Type                                      | Description                                                                                                                                                 |
| ----------------- | ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `data`            | `Optional[Union[Dict[str, Any], Config]]` | Optional data to initialize the config with.                                                                                                                |
| `section_order`   | `Optional[List[str]]`                     | Top-level section names, in order, used to sort the saved and loaded config. All other sections will be sorted alphabetically.                              |
| `is_interpolated` | `Optional[bool]`                          | Whether the config is interpolated or whether it contains variables. Read from the `data` if it’s an instance of `Config` and otherwise defaults to `True`. |

##### <sup><kbd>method</kbd> `Config.from_str`</sup>

Load the config from a string.

```python
from catalogue import Config

config_str = """
[training]
patience = 10
dropout = 0.2
"""
config = Config().from_str(config_str)
print(config["training"])  # {'patience': 10, 'dropout': 0.2}}
```

| Argument      | Type             | Description                                                                                                          |
| ------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------- |
| `text`        | `str`            | The string config to load.                                                                                           |
| `interpolate` | `bool`           | Whether to interpolate variables like `${section.key}`. Defaults to `True`.                                          |
| `overrides`   | `Dict[str, Any]` | Overrides for values and sections. Keys are provided in dot notation, e.g. `"training.dropout"` mapped to the value. |
| **RETURNS**   | `Config`         | The loaded config.                                                                                                   |

##### <sup><kbd>method</kbd> `Config.to_str`</sup>

Load the config from a string.

```python
from catalogue import Config

config = Config({"training": {"patience": 10, "dropout": 0.2}})
print(config.to_str()) # '[training]\npatience = 10\n\ndropout = 0.2'
```

| Argument      | Type   | Description                                                                 |
| ------------- | ------ | --------------------------------------------------------------------------- |
| `interpolate` | `bool` | Whether to interpolate variables like `${section.key}`. Defaults to `True`. |
| **RETURNS**   | `str`  | The string config.                                                          |

##### <sup><kbd>method</kbd> `Config.to_bytes`</sup>

Serialize the config to a byte string.

```python
from catalogue import Config

config = Config({"training": {"patience": 10, "dropout": 0.2}})
config_bytes = config.to_bytes()
print(config_bytes)  # b'[training]\npatience = 10\n\ndropout = 0.2'
```

| Argument      | Type             | Description                                                                                                          |
| ------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------- |
| `interpolate` | `bool`           | Whether to interpolate variables like `${section.key}`. Defaults to `True`.                                          |
| `overrides`   | `Dict[str, Any]` | Overrides for values and sections. Keys are provided in dot notation, e.g. `"training.dropout"` mapped to the value. |
| **RETURNS**   | `str`            | The serialized config.                                                                                               |

##### <sup><kbd>method</kbd> `Config.from_bytes`</sup>

Load the config from a byte string.

```python
from catalogue import Config

config = Config({"training": {"patience": 10, "dropout": 0.2}})
config_bytes = config.to_bytes()
new_config = Config().from_bytes(config_bytes)
```

| Argument      | Type     | Description                                                                 |
| ------------- | -------- | --------------------------------------------------------------------------- |
| `bytes_data`  | `bool`   | The data to load.                                                           |
| `interpolate` | `bool`   | Whether to interpolate variables like `${section.key}`. Defaults to `True`. |
| **RETURNS**   | `Config` | The loaded config.                                                          |

##### <sup><kbd>method</kbd> `Config.to_disk`</sup>

Serialize the config to a file.

```python
from catalogue import Config

config = Config({"training": {"patience": 10, "dropout": 0.2}})
config.to_disk("./config.cfg")
```

| Argument      | Type               | Description                                                                 |
| ------------- | ------------------ | --------------------------------------------------------------------------- |
| `path`        | `Union[Path, str]` | The file path.                                                              |
| `interpolate` | `bool`             | Whether to interpolate variables like `${section.key}`. Defaults to `True`. |

##### <sup><kbd>method</kbd> `Config.from_disk`</sup>

Load the config from a file.

```python
from catalogue import Config

config = Config({"training": {"patience": 10, "dropout": 0.2}})
config.to_disk("./config.cfg")
new_config = Config().from_disk("./config.cfg")
```

| Argument      | Type               | Description                                                                                                          |
| ------------- | ------------------ | -------------------------------------------------------------------------------------------------------------------- |
| `path`        | `Union[Path, str]` | The file path.                                                                                                       |
| `interpolate` | `bool`             | Whether to interpolate variables like `${section.key}`. Defaults to `True`.                                          |
| `overrides`   | `Dict[str, Any]`   | Overrides for values and sections. Keys are provided in dot notation, e.g. `"training.dropout"` mapped to the value. |
| **RETURNS**   | `Config`           | The loaded config.                                                                                                   |

##### <sup><kbd>method</kbd> `Config.copy`</sup>

Deep-copy the config.

| Argument    | Type     | Description        |
| ----------- | -------- | ------------------ |
| **RETURNS** | `Config` | The copied config. |

##### <sup><kbd>method</kbd> `Config.interpolate`</sup>

Interpolate variables like `${section.value}` or `${section.subsection}` and return a copy of the config with interpolated
values. Can be used if a config is loaded with `interpolate=False`, e.g. via `Config.from_str`.

```python
from catalogue import Config

config_str = """
[hyper_params]
dropout = 0.2

[training]
dropout = ${hyper_params.dropout}
"""
config = Config().from_str(config_str, interpolate=False)
print(config["training"])  # {'dropout': '${hyper_params.dropout}'}}
config = config.interpolate()
print(config["training"])  # {'dropout': 0.2}}
```

| Argument    | Type     | Description                                    |
| ----------- | -------- | ---------------------------------------------- |
| **RETURNS** | `Config` | A copy of the config with interpolated values. |

##### <sup><kbd>method</kbd> `Config.merge`</sup>

Deep-merge two config objects, using the current config as the default. Only merges sections and dictionaries and not
other values like lists. Values that are provided in the updates are overwritten in the base config, and any new values
or sections are added. If a config value is a variable like `${section.key}` (e.g. if the config was loaded with
`interpolate=False)`, **the variable is preferred**, even if the updates provide a different value. This ensures that variable
references aren’t destroyed by a merge.

> :warning: Note that blocks that refer to registered functions using the `@` syntax are only merged if they are
> referring to the same functions. Otherwise, merging could easily produce invalid configs, since different functions
> can take different arguments. If a block refers to a different function, it’s overwritten.

```python
from catalogue import Config

base_config_str = """
[training]
patience = 10
dropout = 0.2
"""
update_config_str = """
[training]
dropout = 0.1
max_epochs = 2000
"""

base_config = Config().from_str(base_config_str)
update_config = Config().from_str(update_config_str)
merged = Config(base_config).merge(update_config)
print(merged["training"])  # {'patience': 10, 'dropout': 1.0, 'max_epochs': 2000}
```

| Argument    | Type                            | Description                                         |
| ----------- | ------------------------------- | --------------------------------------------------- |
| `overrides` | `Union[Dict[str, Any], Config]` | The updates to merge into the config.               |
| **RETURNS** | `Config`                        | A new config instance containing the merged config. |

#### Config Attributes

| Argument          | Type   | Description                                                                                                                                                              |
| ----------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `is_interpolated` | `bool` | Whether the config values have been interpolated. Defaults to `True` and is set to `False` if a config is loaded with `interpolate=False`, e.g. using `Config.from_str`. |
