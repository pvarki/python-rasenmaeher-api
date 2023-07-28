========================
RASENMAEHER integrations
========================

"One Ring to rule them all, One Ring to find them, One Ring to bring them all and in the darkness bind them."

Docker compositions, helpers etc to bring it all together into something resembling grand old ones.


Git submodules
--------------

When cloning for the first time use::

    git clone --recurse-submodules -j8 git@github.com:pvarki/docker-rasenmaeher-integration.git

When updating or checking out branches use::

    git submodule update

And if you forgot to --recurse-submodules run git submodule init to fix things.

The submodules are repos in their own right, if you plan to make changes into them change
to the directory and create new branch, commit and push changes as usual under that directory.

Running in local development mode
_________________________________

TLDR::

    docker-compose -f docker-compose-local.yml -f docker-compose-dev.yml build
    docker-compose -f docker-compose-local.yml -f docker-compose-dev.yml up

Launches all the services and runs rasenmaeher-api in uvicorn reload mode so any edits
you make under /api will soon be reflected in the running instance.


Directories that are submodules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

  - api https://github.com/pvarki/python-rasenmaeher-api
  - cfssl https://github.com/pvarki/docker-rasenmaeher-cfssl
  - fpintegration https://github.com/pvarki/python-rasenmaeher-rmfpapi
  - keycloak https://github.com/pvarki/docker-keycloak
  - kw_product_init https://github.com/pvarki/golang-kraftwerk-init-helper-cli
  - openldap https://github.com/pvarki/docker-openldap
  - mkcert https://github.com/pvarki/docker-mkcert
