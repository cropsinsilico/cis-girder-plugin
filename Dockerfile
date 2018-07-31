FROM girder/girder:2.3.0

ARG PLUGIN_NAME="cis"

RUN pip install gitpython pyaml cis_interface

COPY girder.local.cfg /girder/girder/conf/
COPY Dockerfile /girder
COPY . /girder/plugins/${PLUGIN_NAME}/
