<a href="https://explosion.ai"><img src="https://explosion.ai/assets/img/logo.svg" width="125" height="125" align="right" /></a>

# catalogue: Super lightweight function registries for your library

`catalogue` is a tiny, zero-dependencies library that makes it easy to **add
function (or object) registries** to your code. Function registries are helpful
when you have objects that need to be both easily serializable and fully
customizable. Instead of passing a function into your object, you pass in an
identifier name, which the object can use to lookup the function from the
registry. This makes the object easy to serialize, because the name is a simple
string. If you instead saved the function, you'd have to use Pickle for
serialization, which has many drawbacks.

[![Azure Pipelines](https://img.shields.io/azure-devops/build/explosion-ai/public/14/master.svg?logo=azure-pipelines&style=flat-square&label=build)](https://dev.azure.com/explosion-ai/public/_build?definitionId=14)
[![Current Release Version](https://img.shields.io/github/v/release/explosion/catalogue.svg?style=flat-square&include_prereleases&logo=github)](https://github.com/explosion/catalogue/releases)
[![pypi Version](https://img.shields.io/pypi/v/catalogue.svg?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/catalogue/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/ambv/black)

## 👩‍💻 Usage

Let's imagine you're developing a Python package that needs to load data
somewhere. You've already implemented some loader functions for the most common
data types, but you want to allow the user to easily add their own. Using
`catalogue.create` you can create a new registry under the namespace
`your_package` &rarr; `loaders`.

```python
# YOUR PACKAGE
import catalogue

register_loader, get_loaders = catalogue.create("your_package", "loaders")
```

This gives you a `register_loader` decorator that your users can import and
decorate their custom loader functions with.

```python
# USER CODE
from your_package import register_loader

@register_loader("custom_loader")
def custom_loader(data):
    # Load something here...
    return data
```

The decorated function will be registered automatically and in your package,
you'll be able to access it by calling the getter function returned by
`catalogue.create` – in this case, `get_loaders`.

```python
# YOUR PACKAGE
def load_data(data, loader_id):
    all_loaders = get_loaders()  # {"custom_loader": custom_loader}
    loader = all_loaders[loader]
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
[entry points](https://packaging.python.org/tutorials/packaging-projects/#entry-points).

For instance, in [spaCy](https://spacy.io) we're starting to use function
registries to make the pipeline components much more customizable. Let's say one
user, Jo, develops a better tagging model using new machine learning research.
End-users of Jo's package should be able to write
`spacy.load("jo_tagging_model")`. They shouldn't need to remember to write
`import jos_tagged_model` first, just to run the function registries as a
side-effect. With entry points, the registration happens at install time – so
you don't need to rely on the import side-effects.

## 🎛 API

### <kbd>function</kbd> `catalogue.create`

Create a new registry for a given namespace. Returns a setter function that can
be used as a decorator or called with a name and `func` keyword argument.

| Argument     | Type            | Description                                                                                 |
| ------------ | --------------- | ------------------------------------------------------------------------------------------- |
| `*namespace` | str             | The namespace, e.g. `"spacy"` or `"spacy", "architectures"`.                                |
| **RETURNS**  | Tuple[Callable] | The setter (decorator to register functions) and getter (to retrieve registered functions). |

```python
register_architecture, get_architectures = catalogue.create("spacy", "architectures")

# Use as decorator
@register_architecture("custom_architecture")
def custom_architecture():
    pass

# Use as regular function
register_architecture("custom_architecture", func=custom_architecture)
```

### <kbd>function</kbd> `catalogue.check_exists`

Check if a namespace exists.

| Argument     | Type | Description                                                  |
| ------------ | ---- | ------------------------------------------------------------ |
| `*namespace` | str  | The namespace, e.g. `"spacy"` or `"spacy", "architectures"`. |
| **RETURNS**  | bool | Whether the namespace exists.                                |

```python
register_architecture, get_architectures = catalogue.create("spacy", "architectures")
assert catalogue.check_exists("spacy", "architectures")
```

### <kbd>function</kbd> `catalogue.register`

Register a function for a given namespace. Used in `catalogue.create` as a
partial function (with the given `namespace` applied).

| Argument    | Type       | Description                                               |
| ----------- | ---------- | --------------------------------------------------------- |
| `namespace` | Tuple[str] | The namespace to register.                                |
| `name`      | str        | The name to register under the namespace.                 |
| `func`      | Any        | Optional function to register (if not used as decorator). |
| **RETURNS** | Callable   | The decorator that takes one argument, the name.          |

```python
register_architecture = catalogue.register(("spacy", "architectures"), "my_custom_architecture")

```

### <kbd>function</kbd> `catalogue.get`

Get all functions for a given namespace. Used in `catalogue.create` as a partial
function (with the given `namespace` applied).

| Argument    | Type           | Description                              |
| ----------- | -------------- | ---------------------------------------- |
| `namespace` | Tuple[str]     | The namespace to get.                    |
| **RETURNS** | Dict[str, Any] | The registered functions, keyed by name. |

```python
all_architectures = catalogue.get(("spacy", "architectures"))
```

### <kbd>function</kbd> `catalogue.get_all`

Get all matches for a given namespace, e.g. `("a", "b", "c")` and `("a", "b")`
for namespace `("a", "b")`.

| Argument    | Type                  | Description                                                    |
| ----------- | --------------------- | -------------------------------------------------------------- |
| `namespace` | Tuple[str]            | The namespace.                                                 |
| **RETURNS** | Dict[Tuple[str], Any] | All entries for the namespace, keyed by their full namespaces. |

```python
all_entries = catalogue.get_all(("a", "b"))
# {("a", "b"): func, ("a", "b", "c"): func}
```
