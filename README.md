# cis-girder-plugin
Adds API endpoints for interacting with the Crops in Silico framework.

# Overview
This is a jumping-off point for creating a new server-side REST API plugin for Girder.

This plugin was developed using the Labs Workbench: https://www.workbench.nationaldataservice.org

# Usage
To use this plugin, simply load it into your Girder instance/image, login as an administratorm and navigate to the "Plugins" page

From here, you should see the new plugin listed and be offered an option to enable it.

If you do choose to enable it, you will be prompted to automatically restart/rebuild Girder.

## With Docker
This plugin will need to be copied into your Docker image for Girder.

Run the following command to produce a Docker image containing the plugin
```
docker build -t girder/girder:cis .
```

You can then run this image in place of your existing one to enable the plugin.

## Without Docker
Simply clone this repo into your `/girder/plugins` directory - you may need to restart the server to see the new plugin.

# Development
1. Import the `girder23` application (seen below) into Workbench catalog
2. Add an instance of `girder23` and a Cloud9 Python IDE from the catalog
3. On the dashboard, edit your Cloud9 IDE's `Data` tab to mount `AppData/stackid-girder23` to `/workspace`
    * Make sure to substitute in the stackid of your new girder application
4. Start up the Girder and Cloud9 IDE applications
5. Clone this repository into your Cloud9 `/workspace`

## The `girder23` Application
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
