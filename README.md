# cis-girder-plugin
Adds API endpoints to Girder 2.3 for interacting with the Crops in Silico framework.

# Overview
This is a jumping-off point for creating a new server-side REST API plugin for Girder.

This plugin was developed using the Labs Workbench: https://www.workbench.nationaldataservice.org

# Usage
To use this plugin, simply load it into your Girder instance/image (see below), login to Girder as an administrator, and navigate to the "Plugins" page

From here, you should see the new plugin listed and be offered an option to enable it.

If you do choose to enable it, you will be prompted to automatically restart/rebuild Girder (has no effect on stored data).

## Without Docker
Simply clone this repo into your `/girder/plugins` directory - you may need to restart the server to see the new plugin.

## With Docker
This plugin will need to be copied into your Docker image for Girder.

Run the following command to produce a Docker image containing the plugin
```
export GIRDER_PLUGIN_NAME="my-plugin-name"
docker build --build-args PLUGIN_NAME="${GIRDER_PLUGIN_NAME}" -t girder/girder:2.3.0-${GIRDER_PLUGIN_NAME} .
```

You can then run this image in place of your existing Girder Docker image to access your new plugin.

# Development
You can develop a plugin most easily when Girder is configured with `mode=development`.

This causes any changes on disk to trigger Girder to rebuild itself and restart.

Note that in containerized environments, this happens transparently without the need to restart the container.

## Without Docker
There are several ways to run Girder without Docker, but none with which I am familiar enough to document.

See http://girder.readthedocs.io/en/latest/deploy.html for more details

## With Docker
To quickly get up and running with Girder under Docker, simply run the following two commands:
```
docker run -itd -p 27017:27017 mongo
docker run -itd --link mongo -p 8080:8080 girder/girder:2.3.0-${GIRDER_PLUGIN_NAME} -d mongodb://mongo:27017/girder
```

Navigating to `http://localhost:8080` should then bring you to the Girder UI, where you can test your plugin.

## In Labs Workbench
You can actually develop plugins for Girder without installing anything locally using the [NDS Labs Workbench](http://www.nationaldataservice.org/platform/workbench.html).

1. Navigate and **Login** to the [Workbench](https://www.workbench.nationaldataservice.org)
2. Import the `girder23` application (seen below) into your Workbench **Catalog**
3. Add an instance of `girder23` and a Cloud9 Python IDE from the **Catalog**
4. On the **Dashboard**, edit your Cloud9 IDE's `Data` tab to mount `AppData/stackid-girder23` to `/workspace`
    * Make sure to substitute the stackid of your new `girder23` application
5. On the **Dashboard**, start up the Girder and Cloud9 IDE applications
6. Once Cloud9 is "Running" (e.g. turns green), click the link on the **Dashboard** to the IDE
6. Inside the IDE, use the terminal at the bottom to clone this repository into your Cloud9 `/workspace`

### The `girder23` Application
```
{
    "key": "girder23",
    "label": "Girder",
    "description": "Web-based data management platform.",
    "image": {
        "registry": "",
        "name": "girder/girder",
        "tags": [
            "2.3.0"
        ]
    },
    "display": "stack",
    "access": "external",
    "depends": [
        {
            "key": "mongo",
            "required": true
        }
    ],
    "args": [
        "-d",
        "mongodb://$(MONGO_PORT_27017_TCP_ADDR):$(MONGO_PORT_27017_TCP_PORT)/girder"
    ],
    "ports": [
        {
            "port": 8080,
            "protocol": "http",
            "contextPath": "/"
        }
    ],
    "repositories": [
        {
            "url": "https://github.com/girder/girder",
            "type": "git"
        }
    ],
    "readinessProbe": {
        "type": "",
        "path": "",
        "port": 0,
        "initialDelay": 0,
        "timeout": 0
    },
    "volumeMounts": [
        {
            "mountPath": "/girder/plugins/cis"
        }
    ],
    "resourceLimits": {
        "cpuMax": 500,
        "cpuDefault": 100,
        "memMax": 2000,
        "memDefault": 50
    },
    "tags": [
        "20",
        "2",
        "36"
    ],
    "info": "https://nationaldataservice.atlassian.net/wiki/display/NDSC/Girder",
    "authRequired": true
}
```
