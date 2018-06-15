FROM girder/girder:2.3.0

ARG PLUGIN_NAME="cis"

COPY . /girder/plugins/${PLUGIN_NAME}/
