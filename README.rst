========================
RASENMAEHER integrations
========================

"One Ring to rule them all, One Ring to find them, One Ring to bring them all and in the darkness bind them."

Docker compositions, helpers etc to bring it all together into something resembling grand old ones.


Git submodules
--------------

When cloning for the first time use::

    git clone --recurse-submodules -j8 git@github.com:pvarki/docker-rasenmaeher-integration.git

When checking updating or checking out branches use::

    git submodule update

The submodules are repos in their own right, if you plan to make changes into them change
to the directory and create new branch, commit and push changes as usual under that directory.

Directories that are submodules
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

  - api https://github.com/pvarki/python-rasenmaeher-api
  - cfssl https://github.com/pvarki/docker-rasenmaeher-cfssl
  - keycloak https://github.com/pvarki/docker-keycloak
  - openldap https://github.com/pvarki/docker-openldap
