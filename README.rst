=============================
python-rasenmaeher-api
=============================

python-rasenmaeher-api


Configuration
-------------

This application can be configured with environment variables.

| Environment variable     | Default value | Info                          |
| ------------------------ | ------------- | ----------------------------- |
| RM_PORT          | 8000          | Docker API listen port                |
| RM_WORKERS_COUNT | 2             | Number of uvicorn workers             |
| RM_RELOAD        | False         | Reload service on code change         |
| RM_ENVIRONMENT   | dev           | dev / prod environment                |



You can create `.env` file in the root directory and place all
environment variables here.


All environment variables should start with `RM_` prefix.

For example if you see in your "rasenmaeher_api/settings.py" a variable named like
`random_parameter`, you should provide the "RM_RANDOM_PARAMETER"
variable to configure the value. This behaviour can be changed by overriding `env_prefix` property
in `rasenmaeher_api.settings.Settings.Config`.

An example of .env file:
```bash
RM_RELOAD="True"
RM_PORT="8000"
RM_ENVIRONMENT="dev"
```

You can read more about BaseSettings class here: https://pydantic-docs.helpmanual.io/usage/settings/


Docker
------

For more controlled deployments and to get rid of "works on my computer" -syndrome, we always
make sure our software works under docker.

It's also a quick way to get started with a standard development environment.

SSH agent forwarding
^^^^^^^^^^^^^^^^^^^^

We need buildkit_::

    export DOCKER_BUILDKIT=1

.. _buildkit: https://docs.docker.com/develop/develop-images/build_enhancements/

And also the exact way for forwarding agent to running instance is different on OSX::

    export DOCKER_SSHAGENT="-v /run/host-services/ssh-auth.sock:/run/host-services/ssh-auth.sock -e SSH_AUTH_SOCK=/run/host-services/ssh-auth.sock"

and Linux::

    export DOCKER_SSHAGENT="-v $SSH_AUTH_SOCK:$SSH_AUTH_SOCK -e SSH_AUTH_SOCK"

Creating a development container
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Build image, create container and start it::

    docker build --ssh default --target devel_shell -t rasenmaeher_api:devel_shell .
    docker create --name rasenmaeher_api_devel -v `pwd`":/app" -it `echo $DOCKER_SSHAGENT` rasenmaeher_api:devel_shell
    docker start -i rasenmaeher_api_devel

pre-commit considerations
^^^^^^^^^^^^^^^^^^^^^^^^^

If working in Docker instead of native env you need to run the pre-commit checks in docker too::

    docker exec -i rasenmaeher_api_devel /bin/bash -c "pre-commit install"
    docker exec -i rasenmaeher_api_devel /bin/bash -c "pre-commit run --all-files"

You need to have the container running, see above. Or alternatively use the docker run syntax but using
the running container is faster::

    docker run --rm -it -v `pwd`":/app" rasenmaeher_api:devel_shell -c "pre-commit run --all-files"

Test suite
^^^^^^^^^^

You can use the devel shell to run py.test when doing development, for CI use
the "tox" target in the Dockerfile::

    docker build --ssh default --target tox -t rasenmaeher_api:tox .
    docker run --rm -it -v `pwd`":/app" `echo $DOCKER_SSHAGENT` rasenmaeher_api:tox

Production docker
^^^^^^^^^^^^^^^^^

TODO: Remove this section if this is a library and not an application

There's a "production" target as well for running the application, remember to change that
architecture tag to arm64 if building on ARM::

    docker build --ssh default --target production -t rasenmaeher_api:latest .
    docker run -it --name rasenmaeher_api rasenmaeher_api:amd64-latest

Development
-----------

TODO: Remove the repo init from this document after you have done it.

TLDR:

- Create and activate a Python 3.8 virtualenv (assuming virtualenvwrapper)::

    mkvirtualenv -p `which python3.8` my_virtualenv

- Init your repo (first create it on-line and make note of the remote URI)::

    git init
    git add .
    git commit -m 'Cookiecutter stubs'
    git remote add origin MYREPOURI
    git push origin master

- change to a branch::

    git checkout -b my_branch

- install Poetry: https://python-poetry.org/docs/#installation
- Install project deps and pre-commit hooks::

    poetry install
    pre-commit install
    pre-commit run --all-files

- Ready to go.

Remember to activate your virtualenv whenever working on the repo, this is needed
because pylint and mypy pre-commit hooks use the "system" python for now (because reasons).
