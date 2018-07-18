FROM girder/girder:2.3.0

ARG PLUGIN_NAME="cis"

RUN pip install gitpython pyaml cis_interface

COPY README.md server/ plugin* /girder/plugins/${PLUGIN_NAME}/
COPY Dockerfile /girder
COPY girder.local.cfg /girder/girder/conf/
