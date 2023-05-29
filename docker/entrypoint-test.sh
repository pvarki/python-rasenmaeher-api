#!/bin/bash -l
set -e
source /.venv/bin/activate
if [ "$#" -eq 0 ]; then
  # Kill cache, pytest complains about it if running local and docker tests in mapped volume
  find tests  -type d -name '__pycache__' -print0 | xargs -0 rm -rf {}
  # Make sure the service itself is installed
  poetry install
  # Make sure pre-commit checks were not missed because reasons
  pre-commit run --all-files
  # Then run the tests
  pytest --junitxml=pytest.xml tests/
  # If pre-commit does not run these, enable them
  # mypy src tests
  # pylint src tests
  # bandit --skip=B101 -r src
else
  exec "$@"
fi
