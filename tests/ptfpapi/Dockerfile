# syntax=docker/dockerfile:1.1.7-experimental
FROM python:3.14-trixie AS base
COPY requirements.txt /pysetup/
RUN pip3 install -r /pysetup/requirements.txt


FROM base AS init
COPY fpinit.py /app/
ENTRYPOINT ["python3", "/app/fpinit.py" ]


FROM base AS run
COPY fprun.py /app/
ENTRYPOINT ["python3", "/app/fprun.py" ]

FROM base AS client
COPY fpclient.py fpclient_entrypoint.sh /app/
ENTRYPOINT ["/app/fpclient_entrypoint.sh"]
