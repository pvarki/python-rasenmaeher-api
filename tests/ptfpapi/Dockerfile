# syntax=docker/dockerfile:1.1.7-experimental
FROM python:3.9-bookworm as base
COPY requirements.txt /pysetup/
RUN pip3 install -r /pysetup/requirements.txt


FROM base as init
COPY fpinit.py /app/
ENTRYPOINT ["python3", "/app/fpinit.py" ]


FROM base as run
COPY fprun.py /app/
ENTRYPOINT ["python3", "/app/fprun.py" ]

FROM base as client
COPY fpclient.py muck_magic_hosts.sh /app/
ENTRYPOINT ["/app/muck_magic_hosts.sh"]
