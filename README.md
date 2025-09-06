[![Build Status](https://github.com/andgineer/async-s3/workflows/CI/badge.svg)](https://github.com/andgineer/async-s3/actions)
[![Coverage](https://raw.githubusercontent.com/andgineer/async-s3/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/andgineer/async-s3/blob/python-coverage-comment-action-data/htmlcov/index.html)
# async-s3

S3 bucket helper utilities.

Asynchronously lists objects by folders or grouped by prefix, with an optional recursion limit.

# Documentation

[Async S3](https://andgineer.github.io/async-s3/)

# Developers

Run `. ./activate.sh` to create/activate the virtual environment.

Requires [uv](https://github.com/astral-sh/uv) for dependency management.

Use [pre-commit](https://pre-commit.com/#install) hooks for code quality:

    pre-commit install

## Allure Test Report

* [Allure report](https://andgineer.github.io/async-s3/builds/tests/)

# Scripts

Install [invoke](https://docs.pyinvoke.org/en/stable/) preferably with [pipx](https://pypa.github.io/pipx/):

    pipx install invoke

For a list of available scripts, run:

    invoke --list

For more information about a script, run:

    invoke <script> --help


## Coverage Reports
* [Codecov](https://app.codecov.io/gh/andgineer/async-s3/tree/main/src%2Fasync_s3)
* [Coveralls](https://coveralls.io/github/andgineer/async-s3)

> Created with cookiecutter using [template](https://github.com/andgineer/cookiecutter-python-package)
