=============================
python-rasenmaeher-api
=============================

python-rasenmaeher-api


Configuration
-------------

This application can be configured with environment variables. Below is a example list of available variables.
You can find all available variables here https://github.com/pvarki/python-rasenmaeher-api/blob/main/src/rasenmaeher_api/settings.py.


.. list-table:: Container Variables
   :widths: 30 30 50
   :header-rows: 1

   * - ENV VAR
     - Default value
     - Info / Usage
   * - RM_PORT
     - 8000
     - Docker API listen port
   * - RM_WORKERS_COUNT
     - 2
     - Number of uvicorn workers
   * - RM_RELOAD
     - False
     - Reload service on code change
   * - RM_ENVIRONMENT
     - dev
     - Run dev / prod environment
   * - RM_CFSSL_HOST
     - None
     - CFSSL host url
   * - RM_CFSSL_PORT
     - None
     - CFSSL service port
   * - RM_KEYCLOAK_SERVER_URL
     - None
     - Keycloak server url  (http://1234:8080/auth)
   * - RM_KEYCLOAK_CLIENT_ID
     - None
     - Keycloak client id
   * - RM_KEYCLOAK_REALM_NAME
     - None
     - Keycloak realm name
   * - RM_KEYCLOAK_CLIENT_SECRET
     - None
     - Keycloak secert
   * - RM_LDAP_CONN_STRING
     - None
     - LDAP conn string
   * - RM_LDAP_USERNAME
     - None
     - LDAP username
   * - RM_LDAP_CLIENT_SECRET
     - None
     - LDAP connection secret
   * - RM_SQLITE_FILEPATH_PROD
     - /opt/rasenmaher/persistent/sqlite/rm_db.sql
     - location for sqlite database file in "prod"
   * - RM_SQLITE_FILEPATH_DEV
     - /tmp/rm_db.sql
     - location for sqlite database file in "dev", local development


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


Backend services manifest
-------------------------
Integration APIs are always https in port 4625.
Default location for the manifest is /pvarki/kraftwerk-rasenmaeher-init.json


```json
{
"dns": "sleepy-sloth.pvarki.fi",
"products": {
"tak": "tak.sleepy-sloth.pvarki.fi",
"ptt": "ptt.sleepy-sloth.pvarki.fi"
}
}
```




Api endpoints and usage
-----------------------
.. list-table:: API vimpain
   :widths: 12 8 30 50 50 80
   :header-rows: 1

   * - State
     - Method
     - URI
     - Request JSON
     - Response JSON
     - Api description                                                                              .
   * - Dummy
     - GET
     - /api/v1/enroll/status/{work_id}
     - NA
     - {'status':'None/Processing/Denied/WaitingForAcceptance/ReadyForDelivery/Delivered'}
     - Check the situation of enrollment process, None = no enrollment started, this work_id is free to use.
   * - Dummy
     - POST
     - /api/v1/enroll/init
     - {'work_id':'{work_id}'}
     - {'work_id':'{work_id}', 'id_hash':{id_string} }
     - Start service access enrollment for given {work_id}
   * - Dummy
     - GET
     - /api/v1/enroll/deliver/{id_string}
     - NA
     - {'dl_link':"{http://here.be/zip}"}
     - Deliver download link for enrollment zip
   * - Dummy
     - POST
     - /api/v1/enroll/accept
     - { 'permit_string':'{permit_string}, 'id_hash':'{id_hash}' '}
     - { 'access':'granted/denied/None', 'work_id':'{work_id}' }
     - Accept the enrollment request
   * - Testing
     - POST
     - /api/v1/product/sign_csr
     - { 'TO':'DO'}
     - { 'TO':'DO'}
     - Accept the enrollment request
   * - Testing
     - POST
     - /api/v1/enroll/accept
     - { 'permit_string':'{permit_string}, 'id_hash':'{id_hash}' '}
     - { 'access':'granted/denied/None', 'work_id':'{work_id}' }
     - Accept the enrollment request

Example usage
-------------



# REQUEST A NEW CERTIFICATE USING CSR (requires cfssl backend for the api container)

  ```curl -L -H "Content-Type: application/json" -d '{"csr": "-----BEGIN CERTIFICATE REQUEST-----\nMIIBUjCB+QIBADBqMQswCQYDVQQGEwJVUzEUMBIGA1UEChMLZXhhbXBsZS5jb20x\nFjAUBgNVBAcTDVNhbiBGcmFuY2lzY28xEzARBgNVBAgTCkNhbGlmb3JuaWExGDAW\nBgNVBAMTD3d3dy5leGFtcGxlLmNvbTBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IA\nBK/CtZaQ4VliKE+DLIVGLwtSxJgtUKRzGvN1EwI3HRgKDQ3l3urBIzHtUcdMq6HZ\nb8jX0O9fXYUOf4XWggrLk1agLTArBgkqhkiG9w0BCQ4xHjAcMBoGA1UdEQQTMBGC\nD3d3dy5leGFtcGxlLmNvbTAKBggqhkjOPQQDAgNIADBFAiAcvfhXnsLtzep2sKSa\n36W7G9PRbHh8zVGlw3Hph8jR1QIhAKfrgplKwXcUctU5grjQ8KXkJV8RxQUo5KKs\ngFnXYtkb\n-----END CERTIFICATE REQUEST-----\n"}' 127.0.0.1:8000/api/v1/takreg | jq```

# REQUEST A NEW CERTIFICATE WITHOUT CSR (requires cfssl backend for the api container)

  ```curl  -L -H "Content-Type: application/json" -d '{ "request": {"hosts":["harjoitus1.pvarki.fi"], "names":[{"C":"FI", "ST":"Jyvaskyla", "L":"KeskiSuomi", "O":"harjoitus1.pvarki.fi"}], "CN": "harjoitus1.pvarki.fi"}, "bundle":true, "profile":"client"}' 127.0.0.1:8000/takreg | jq```

# LIST CFSSL CRL LIST

  ```curl  -L -H "Content-Type: application/json" -d '{ "request": {"hosts":["harjoitus1.pvarki.fi"], "names":[{"C":"FI", "ST":"Jyvaskyla", "L":"KeskiSuomi", "O":"harjoitus1.pvarki.fi"}], "CN": "harjoitus1.pvarki.fi"}, "bundle":true, "profile":"client"}' 127.0.0.1:8000/takreg | jq```

The cfssl used behind API listens this kind of stuff https://github.com/cloudflare/cfssl/blob/master/doc/api/endpoint_newcert.txt

# Enrollment - Enroll a new work_id

  ```curl -H "Content-Type: application/json" -d '{"work_id":"porakoira666"}' http://127.0.0.1:8000/api/v1/enrollment/init```

# Enrollment - Check the status and availability of work_id

  ```curl http://127.0.0.1:8000/api/v1/enrollment/status/koira```

# Enrollment - Request the download link using the provided work_id_hash
  ```curl http://127.0.0.1:8000/api/v1/enrollment/deliver/zxzxzxzxzxzxzxxzzx```

# Enrollment - Accept enrollment using permit_str
  ```curl -H "Content-Type: application/json" -d '{"enroll_str":"zxzxzxzxzxzxzxxzzx", "permit_str":"PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1"}' http://127.0.0.1:8000/api/v1/enrollment/accept```

# Enrollment - Set download link for enrollment
  ```curl -H "Content-Type: application/json" -d '{"download_link":"https://kuvaton.com","enroll_str":"zxzxzxzxzxzxzxxzzx", "permit_str":"PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1"}' http://127.0.0.1:8000/api/v1/enrollment/config/set-dl-link```

# Enrollment - Set state for enrollment
  ```curl -H "Content-Type: application/json" -d '{"state":"ReadyForDelivery","enroll_str":"zxzxzxzxzxzxzxxzzx", "permit_str":"PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1"}' http://127.0.0.1:8000/api/v1/enrollment/config/set-state```

# Enrollment - Add new permit_str
  ```curl -H "Content-Type: application/json" -d '{"permissions_str":"all", "new_permit_hash":"too_short","permit_str":"PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1"}' http://127.0.0.1:8000/api/v1/enrollment/config/add-manager```

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

    docker exec -i rasenmaeher_api_devel /bin/bash -c "pre-commit install --install-hooks"
    docker exec -i rasenmaeher_api_devel /bin/bash -c "pre-commit run --all-files"

You need to have the container running, see above. Or alternatively use the docker run syntax but using
the running container is faster::

    docker run --rm -it -v `pwd`":/app" rasenmaeher_api:devel_shell -c "pre-commit run --all-files"

Test suite
^^^^^^^^^^

You can use the devel shell to run py.test when doing development, for CI use
the "tox" target in the Dockerfile::

    docker build --ssh default --target tox -t rasenmaeher_api:tox .
    docker run --rm -it --network host -v /var/run/docker.sock:/var/run/docker.sock -v `pwd`":/app" `echo $DOCKER_SSHAGENT` rasenmaeher_api:tox

NOTE: This will not work from the git submodule directory in the integration repo, docker tests
must be run from the original repo.

Production docker
^^^^^^^^^^^^^^^^^

There's a "production" target as well for running the application, remember to change that
architecture tag to arm64 if building on ARM::

    docker build --ssh default --target production -t rasenmaeher_api:amd64-latest .
    docker run --rm -it --name rasenmaeher_openapijson rasenmaeher_api:amd64-latest rasenmaeher_api openapi
    docker run -it --name rasenmaeher_api rasenmaeher_api:amd64-latest

There is also a specific target for just dumping the openapi.json::

    docker build --ssh default --target openapi -t rasenmaeher_api:amd64-openapi .
    docker run --rm -it --name rasenmaeher_openapijson rasenmaeher_api:amd64-openapi



Development
-----------

TLDR:

- Create and activate a Python 3.11 virtualenv (assuming virtualenvwrapper)::

    mkvirtualenv -p `which python3.11` my_virtualenv

- change to a branch::

    git checkout -b my_branch

- install Poetry: https://python-poetry.org/docs/#installation
- Install project deps and pre-commit hooks::

    poetry install
    pre-commit install --install-hooks
    pre-commit run --all-files

- Ready to go.

Remember to activate your virtualenv whenever working on the repo, this is needed
because pylint and mypy pre-commit hooks use the "system" python for now (because reasons).
