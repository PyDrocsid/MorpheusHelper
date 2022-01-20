# MorpheusHelper Technical Documentation

**Last updated:** 2022-01-20\
_Document generation aided by **Documatic**_

Automatic Documentation

* [Introduction](#introduction)
* [Code Overview](#code-overview)

## Introduction

This is a technical document detailing
        at a high-level
        what MorpheusHelper does, how it operates,
        and how it is built.

The outline of this document was generated
        by **Documatic**.
<!---Documatic-section-group: arch-start--->


## Project Architecture


<!---Documatic-section-arch: container-start--->
The project uses Docker to build a maintainable environment for the project, using python:3.10-alpine as a base image. During build, the container expects ARG variables PIPENV_NOSPIN=true, PIPENV_VENV_IN_PROJECT=true.


<!---Documatic-section-arch: container-end--->

<!---Documatic-section-group: arch-end--->

<!---Documatic-section-group: helloworld-start--->


## Code Overview

The codebase has a flat structure.
<!---Documatic-section-helloworld: setup-start--->

No exact compatable Python version has been detected.
Versions below 3.8 are compatable.

Install from pypi with `pip install main`.



<!---Documatic-section-helloworld: setup-end--->

<!---Documatic-section-helloworld: entrypoints-start--->


<!---Documatic-section-helloworld: entrypoints-end--->

<!---Documatic-section-group: concept-start--->
## Concepts
<!---Documatic-section-group: concept-end--->

<!---Documatic-section-group: helloworld-end--->

<!---Documatic-section-group: dev-start--->


## Developers
<!---Documatic-section-dev: setup-start--->





<!---Documatic-section-dev: setup-end--->

<!---Documatic-section-dev: ci-start--->
The project uses GitHub Actions for CI/CD.

| CI File | Purpose |
|:----|:----|
| docker_clean | Executes on delete for any branch |
| ci | Executes on push for any branch, pull_request for any branch |


<!---Documatic-section-dev: ci-end--->

<!---Documatic-section-group: dev-end--->
