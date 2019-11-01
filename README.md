<a href="https://explosion.ai"><img src="https://explosion.ai/assets/img/logo.svg" width="125" height="125" align="right" /></a>

# catalogue: Super lightweight function registries for your library

Catalogue is a tiny, zero-dependencies library that makes it easy to add
function (or object) registries to your code. Function registries are helpful
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

## Usage

```python
import catalogue

register_architecture, get_architectures = catalogue.create("spacy", "architectures")
```

```python
@register_architecture("custom_architecture")
def custom_architecture():
    pass
```

```python
all_architectures = get_architectures()
```
