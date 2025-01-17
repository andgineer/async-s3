[![Build Status](https://github.com/andgineer/async-s3/workflows/CI/badge.svg)](https://github.com/andgineer/async-s3/actions)
[![Coverage](https://raw.githubusercontent.com/andgineer/async-s3/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/andgineer/async-s3/blob/python-coverage-comment-action-data/htmlcov/index.html)
# async-s3

S3 Bucket helper utils. 

Async list objects by folders or by prefix groups with recursion limit.

# Documentation

[Async S3](https://andgineer.github.io/async-s3/)

# Developers

Do not forget to run `. ./activate.sh`.

For work it need [uv](https://github.com/astral-sh/uv) installed.

Use [pre-commit](https://pre-commit.com/#install) hooks for code quality:

    pre-commit install

## Allure test report

* [Allure report](https://andgineer.github.io/async-s3/builds/tests/)

# Scripts

Install [invoke](https://docs.pyinvoke.org/en/stable/) preferably with [pipx](https://pypa.github.io/pipx/):

    pipx install invoke

For a list of available scripts run:

    invoke --list

For more information about a script run:

    invoke <script> --help


## Coverage report
* [Codecov](https://app.codecov.io/gh/andgineer/async-s3/tree/main/src%2Fasync_s3)
* [Coveralls](https://coveralls.io/github/andgineer/async-s3)

> Created with cookiecutter using [template](https://github.com/andgineer/cookiecutter-python-package)