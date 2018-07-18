# Basic test process
# docker run -d --net host mongo
# docker run --net host -it -v `pwd`:/girder/plugins/cis --entrypoint=bash cropsinsilico/girder-ctest
PYTHON_VERSION="3.4"
COVERAGE_EXECUTABLE="/usr/local/bin/coverage"
FLAKE8_EXECUTABLE="/usr/local/bin/flake8"
VIRTUALENV_EXECUTABLE="/usr/local/bin/virtualenv"
PYTHON_EXECUTABLE="/usr/bin/python3"
TEST_GROUP="python"

girder-install web --dev
mkdir /girder/build
cd /girder/build
cmake /girder  -DRUN_CORE_TESTS=OFF -DBUILD_JAVASCRIPT_TESTS=OFF -DPYTHON_STATIC_ANALYSIS=OFF -DJAVASCRIPT_STYLE_TESTS=OFF -DTEST_PLUGINS="cis"
ctest -VV
