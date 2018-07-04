FROM girder/girder:2.3.0

ARG PLUGIN_NAME="cis"

pip install gitpython

COPY . /girder/plugins/${PLUGIN_NAME}/
