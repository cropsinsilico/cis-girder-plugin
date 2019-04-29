FROM girder/girder:2.3.0

ARG PLUGIN_NAME="cis"

RUN pip install gitpython pyaml yggdrasil

COPY . /girder/plugins/${PLUGIN_NAME}/
COPY Dockerfile /girder
COPY girder.local.cfg /girder/girder/conf/
