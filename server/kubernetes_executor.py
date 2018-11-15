# This code was created for use in the KnowEnG Platform under the MIT License.
# LICENSE: https://github.com/KnowEnG/platform/blob/master/LICENSE
#
# It has been modified slightly and repurposed for use in this project.
#
#
"""This module defines constants and a base class for jobs that run 
   remotely using Kubernetes.

   Supports the following environment configurations:

   Variable Name              (Default Value)
   ------------------------------------------------
   - RUNLEVEL                 ('development')
   - TOKEN_FILE_PATH          ('/var/run/secrets/kubernetes.io/serviceaccount/token')
   - NODE_LABEL_NAME          ('')
   - NODE_LABEL_VALUE         ('')
   - KUBERNETES_SERVICE_HOST  ('10.0.0.1')
   - KUBERNETES_SERVICE_PORT  (443)
"""

import time
import logging
import os
import json

import requests

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

RUNLEVEL = os.getenv('RUNLEVEL', 'development')

# Read Kubernetes auth token from the ServiceAccount file on disk
token_file_path = os.getenv(\
    'TOKEN_FILE_PATH', '/var/run/secrets/kubernetes.io/serviceaccount/token')
token_file = open(token_file_path, 'r')
auth_token = token_file.read()
default_headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + auth_token
}
token_file.close()

class KubernetesJob(object):
    """Base class for jobs that run remotely via Kubernetes."""

    # The name of the label under which to schedule these jobs
    node_label_name = os.getenv('NODE_LABEL_NAME', '')
    node_label_value = os.getenv('NODE_LABEL_VALUE', '')
    
    user_pvc_mount_path = '/pvc'

    # FIXME: this may not work across namespaces... detect via DNS instead?
    # Use the service discovery environment variables created by k8s
    # See https://kubernetes.io/docs/concepts/services-networking/service/#environment-variables
    kubernetes_apiuri = os.getenv('KUBERNETES_SERVICE_HOST', '10.0.0.1') + ':' + \
        str(os.getenv('KUBERNETES_SERVICE_PORT', 443))
      
    def __init__(self, username, job_name, namespace, timeout, init_command, command, docker_image, num_cpus, max_ram_mb):
        """Initializes self.

        Args:
            username (str): The username of the owner of this job.
            job_name (str): A name to identify the job in Kubernetes.
            init_command (str): The full command to run in the initContainer.
            command (str): The full command to run in the container.
            timeout (int): The maximum execution time in seconds.
            docker_image (str): The docker image name for Kubernetes to run.
            num_cpus (int): The number of CPUs to allocate for the job. Note
                AWS m4.xl is 4 CPUs.
            max_ram_mb (int): The maximum RAM in megabytes to allocate for the
                job. Note AWS m4.xl is 16 GB.

        Returns:
            None: None.

        """
        LOGGER.debug('KubernetesJob.__init__')
        self.job_name = job_name
        self.timeout = timeout
        self.namespace = namespace
        self.docker_image = docker_image
        self.num_cpus = num_cpus
        self.max_ram_mb = max_ram_mb
        self.username = username
        self.init_command = init_command
        self.command = command

        # CPU is measured in microns (m) or integers, where 1000m = 1 CPU
        # RAM is measured in MB (M) or GB (G)

        # Assume that this value is in MB
        self.limits_ram = self.max_ram_mb

        # Assume that this value is in microns
        self.limits_cpu = 1000 * self.num_cpus

        # TODO: Increase the resources requested for production pods
        # FIXME: Is this what caused the outOfCpu problem during the demo?
        self.requests_ram = 512
        self.requests_cpu = 500

        if self.requests_ram > self.limits_ram:
            err_message = 'Invalid resources: requested memory (' + \
                str(self.requests_ram) + ') may ' + \
                'not exceed memory limit (' + str(self.limits_ram) + ')'
            LOGGER.error(err_message)
            raise ValueError(err_message)

        if self.requests_cpu > self.limits_cpu:
            err_message = 'Invalid resources: requested CPU may (' + \
                str(self.requests_cpu) + ') not exceed CPU limit (' + \
                self.limits_cpu +')'
            LOGGER.error(err_message)
            raise ValueError(err_message)


    def submit(self):
        """Submits a Kubernetes job to run the given command in a docker
        container.

        Args:
            command (str): The command to run inside the container.

        Returns:
            None: None.

        """
        LOGGER.debug('KubernetesJob.submit')
        
        if self.is_running():
            return True

        # Build up a JSON spec to submit to Kubernetes
        # TODO: refactor - extract method
        payload = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            # TODO: Fix hard-coded namespace
            "metadata": {"name": self.job_name, "namespace": self.namespace},
            "spec": {
                # FIXME: due to k8s bug, not currently
                # working when restartPolicy=OnFailure
                #"backoffLimit": 5,  # failure threshold

                "securityContext": {
                    "runAsUser": 1000,
                    "fsGroup": 100
                },
                "activeDeadlineSeconds": self.timeout,
                "template": {
                    "metadata": {"name": self.job_name},
                    "spec": {
                        "restartPolicy": "OnFailure",
                        "containers": [
                            {
                                "name": self.job_name, # This could be pipeline_slug?
                                "image": self.docker_image,
                                "imagePullPolicy": "Always",
                                "workingDir": KubernetesJob.user_pvc_mount_path,
                                "command": ["bash"],
                                "args": ["-c", self.command],
                                "resources": {
                                    "requests": {
                                        "cpu": str(self.requests_cpu) + 'm',
                                        "memory": str(self.requests_ram) + 'M'
                                    },
                                    "limits": {
                                        "cpu": str(self.limits_cpu) + 'm',
                                        "memory": str(self.limits_ram) + "M"
                                    }
                                },
                                "lifecycle": {
                                  "postStart": {
                                    "exec": {
                                      "command": ["/bin/sh", "-c", "cd /usr/local/matlab/extern/engines/python && python setup.py build -b /tmp install"]
                                    }
                                  }
                                },
                                "volumeMounts": [
                                    # TODO: Where should we mount the user's PVC?
                                    {
                                        "name": "userdata",
                                        "mountPath": KubernetesJob.user_pvc_mount_path,
                                        "subPath": self.job_name
                                    },
                                    {
                                        "name": "matlab",
                                        "mountPath": "/usr/local/matlab"
                                    }
                                ]
                            }
                        ],
                        # TODO: How do we get the name of the user's PVC?
                        "volumes": [
                            {
                                "name": "userdata",
                                "persistentVolumeClaim": {"claimName": "claim-" + self.username }
                            },
                            {
                                "name": "matlab",
                                "hostPath": {
                                    "path": "/usr/local/MATLAB/R2018a"
                                }
                            }
                        ]
                    }
                }
            }
        }
        
        if self.init_command is not None:
            payload['spec']['template']['spec']['initContainers'] = [
                {
                    "name": "init-copy-source",
                    "image": "alpine",
                    "command": [ "bin/sh" ],
                    "args": [ "-c", self.init_command ],
                    "volumeMounts": [
                        {
                            "name": "userdata",
                            "mountPath": "/pvc",
                        }
                    ]
                }
            ]

        # If this is production, adjust payload before submitting
        if RUNLEVEL == 'production':
            # IMPORTANT: adjust volumes to mount from EFS instead of hostPath
            # These EFS PVCs must exist in Kubernetes, and /networks will need
            # to be populated from the current contents of the networks shared mount
            volumes = []
            for vol in payload['spec']['template']['spec']['volumes']:
                vol_name = vol['name']
                volume = {
                    "name": vol_name,
                    "persistentVolumeClaim": {"claimName": "nfs-" + vol_name}
                }
                LOGGER.info('Converted to Kubernetes volume: ' + json.dumps(volume))
                volumes.append(volume)

            payload['spec']['template']['spec']['volumes'] = volumes

            # Optional: Add a nodeSelector to schedule these jobs in
            # the "pipes" auto-scaling instance group on AWS
            payload['spec']['template']['spec']['nodeSelector'] = {}
            if KubernetesJob.node_label_name != "":
                if KubernetesJob.node_label_value != "":
                    payload['spec']['template']['spec']['nodeSelector'][KubernetesJob.node_label_name] = \
                        KubernetesJob.node_label_value
                else:
                    payload['spec']['template']['spec']['nodeSelector'][KubernetesJob.node_label_name] = \
                        True

            LOGGER.info('Production job payload: ' + json.dumps(payload))

        # submit to Kubernetes
        LOGGER.debug('>>> Submitting payload: ' + json.dumps(payload))
        LOGGER.info('Starting ' + self.job_name + '...')
        master_host = 'https://' + \
            KubernetesJob.kubernetes_apiuri + \
            '/apis/batch/v1/namespaces/' + self.namespace + '/jobs'
        response = requests.post(master_host, json=payload, \
            headers=default_headers, verify=False)
        is_response_ok(response, 1, -1)

    def is_running(self):
        """Returns True if the job is running, else False.

        Returns:
            boolean: True if the job is running, else False.

        """
        LOGGER.debug('KubernetesJob.is_running')

        url = 'https://' + KubernetesJob.kubernetes_apiuri + \
            '/apis/batch/v1/namespaces/' + self.namespace + '/jobs/' + self.job_name

        LOGGER.debug('Checking that job exists: ' + url)
        response = requests.get(url, headers=default_headers, verify=False)
        ok = is_response_ok(response, 1, -1)
        # If no exception was raised, our request returned a response
        return ok

    def is_failed(self):
        """Returns True if the job has failed, else returns False.

        Returns:
            boolean: True if the job has failed, else False.

        """
        # TODO: Reach out to Kubernetes API to check job status
        LOGGER.debug('KubernetesJob.is_failed')

        url = 'https://' + KubernetesJob.kubernetes_apiuri + \
                '/apis/batch/v1/namespaces/' + self.namespace + '/jobs/' + self.job_name
        LOGGER.debug('Getting job status from ' + url)
        request_lambda = lambda: requests.get(\
            url, headers=default_headers, verify=False)
        k8s_response = retry_request_until_ok(request_lambda, 1, 2)
        return_val = False
        if k8s_response is not None:
            json_resp = json.loads(k8s_response.text)
            LOGGER.debug('>>> Got response: ' + k8s_response.text)
            status = json_resp['status']
            if 'conditions' in status:
                conditions = status['conditions']
                for condition in conditions:
                    if 'type' in condition and condition['type'] == "Failed":
                        return_val = condition['status'] == 'True'
                        LOGGER.debug(self.job_name + ' is failed? ' + \
                            str(return_val))
            else:
                LOGGER.debug('No job status conditions found: ' + \
                    str(return_val))
        return return_val

    def get_error_message(self):
        """Returns the error message if this job has failed, else returns None.

        Returns:
            str: The error message if this job has failed, else None.

        """
        # Reach out to Kubernetes API to retrieve job logs
        # TODO: this has not been tested very thoroughly

        LOGGER.debug('KubernetesJob.get_error_message')
        LOGGER.debug(' >>> Reading error message for: ' + self.job_name)

        # Look up the pod_name for this job
        pods_url = 'https://' + \
            KubernetesJob.kubernetes_apiuri + \
            '/api/v1/namespaces/' + self.namespace + '/pods?labelSelector=job-name%3D' + \
            self.job_name

        LOGGER.debug('Getting pod name from ' + pods_url)
        request_lambda = lambda: requests.get(\
            pods_url, headers=default_headers, verify=False)
        k8s_response = retry_request_until_ok(request_lambda, 3, 1)
        return_val = "Please wait, fetching logs..."
        if k8s_response is not None:
            job_pods = k8s_response.json()
            
            if len(job_pods['items']) <= 0:
                return_val = "Please wait, fetching logs..."
                return return_val
            # FIXME: We assume there is only one matching job
            job_pod = job_pods['items'][0]
            pod_name = job_pod['metadata']['name']
            LOGGER.debug('>>> Got pod name: ' + pod_name)

            # Then read and return the logs from that pod
            logs_url = 'https://' + \
                KubernetesJob.kubernetes_apiuri + \
                '/api/v1/namespaces/' + self.namespace + '/pods/' + pod_name + '/log'

            LOGGER.debug('Getting logs from ' + logs_url)
            request_lambda2 = lambda: requests.get(\
                logs_url, headers=default_headers, verify=False)
            k8s_response2 = retry_request_until_ok(request_lambda2, 3, 1)
            if k8s_response2 is not None:
                return_val = k8s_response2.text
                LOGGER.debug('Got logs: ' + return_val)
            else:
                return_val = "Error reading logs"
        else:
            return_val = "Please wait, fetching logs..."
        return return_val

    def is_done(self):
        """Returns True if the job is done, else returns False. TODO confirm
        behavior if done but deleted.

        Returns:
            boolean: True if the job is done, else False.

        """
        LOGGER.debug('KubernetesJob.is_done')

        url = 'https://' + KubernetesJob.kubernetes_apiuri + \
            '/apis/batch/v1/namespaces/' + self.namespace + '/jobs/' + self.job_name

        LOGGER.debug('Getting job status from ' + url)
        request_lambda = lambda: requests.get(\
            url, headers=default_headers, verify=False)
        k8s_response = retry_request_until_ok(request_lambda, 1, 0)
        return_val = False
        if k8s_response is not None:
            json_resp = json.loads(k8s_response.text)
            LOGGER.debug('>>> Got response: ' + k8s_response.text)
            status = json_resp['status']
            if 'conditions' in status:
                conditions = status['conditions']
                for condition in conditions:
                    if 'type' in condition and condition['type'] == "Complete":
                        return_val = condition['status'] == 'True'
                        LOGGER.debug(self.job_name + ' is done? ' + \
                            str(return_val))
            else:
                LOGGER.debug('No job status conditions found: ' + str(return_val))
        return return_val

    def delete(self):
        """Deletes the job from Kubernetes. Note that while `kubectl delete job`
        will also clean up the remaining pods, the REST API apparently does not
        share this behavior. So we make a few extra REST calls to scale down and
        clean up any leftover pod resources.

        Returns:
            None: None.

        """
        k8s_hostname = 'https://' + \
            KubernetesJob.kubernetes_apiuri
        jobs_url = k8s_hostname + '/apis/batch/v1/namespaces/' + self.namespace + '/jobs/' + \
            self.job_name

        # Get current Job object to scale it down
        LOGGER.debug('Removing orphaned job pods for ' + str(self.job_name))
        jobs_get_response = requests.get(\
            jobs_url, headers=default_headers, verify=False)
        ok = is_response_ok(jobs_get_response, 1, -1)
        if ok:
            # Scale current number of Pods for the Job down to zero
            job_json = jobs_get_response.json()
            job_json['spec']['parallelism'] = 0
            LOGGER.debug('Changing job parallelism to zero...')
            jobs_put_response = requests.put(jobs_url, data=json.dumps(job_json), \
                headers=default_headers, verify=False)
            ok = is_response_ok(jobs_put_response, 1, -1)
        if ok:
            # Check for any leftover pod replicas
            LOGGER.debug('Looking up job uid: ' + str(self.job_name))
            job_controller_uid = job_json['metadata']['labels']['controller-uid']

            # NOTE: "%3D" is a URL-encoded equal sign ("=")
            pod_list_url = k8s_hostname + '/api/v1/namespaces/' + self.namespace + '/pods?' + \
                'labelSelector=controller-uid%3D' + str(job_controller_uid)

            continue_deleting = True
            while continue_deleting:
                pod_list_response = requests.get(\
                    pod_list_url, headers=default_headers, verify=False)
                ok = is_response_ok(pod_list_response, 1, -1)

                orphaned_pod_list = pod_list_response.json()
                LOGGER.debug('Checking for orphaned job pods for: ' + \
                    str(self.job_name))
                if not orphaned_pod_list['items']:
                    LOGGER.info('All pods removed for job: ' + \
                        str(self.job_name))
                    continue_deleting = False
                else:
                    LOGGER.debug('Orphaned pod found!')
                    orphan_pod = orphaned_pod_list['items'][0]
                    pod_name = orphan_pod['metadata']['name']
                    LOGGER.debug('Deleting orphaned pod: ' + str(pod_name))
                    pod_delete_url = k8s_hostname + \
                        '/api/v1/namespaces/' + self.namespace + '/pods/' + pod_name
                    pod_delete_response = requests.delete(pod_delete_url, \
                        headers=default_headers, verify=False)
                    if is_response_ok(pod_delete_response, 1, -1):
                        LOGGER.debug('Pod deleted: ' + str(pod_name))

            # Then delete the Job itself
            LOGGER.debug('Deleting job: ' + self.job_name)
            job_delete_response = requests.delete(jobs_url, \
                headers=default_headers, verify=False)
            ok = is_response_ok(job_delete_response, 1, -1)

            LOGGER.debug('Job successfully deleted!')

    @staticmethod
    def get_all_job_names():
        """Returns all job names known to Kubernetes.

        Returns:
            list(str): A list of job names.

        """
        url = 'https://' + KubernetesJob.kubernetes_apiuri + \
            '/apis/batch/v1/namespaces/' + self.namespace + '/jobs'
        LOGGER.debug('Getting all job names from ' + url)
        return_val = []
        request_lambda = lambda: requests.get(\
            url, headers=default_headers, verify=False)
        k8s_response = retry_request_until_ok(request_lambda, 1, 0)
        if k8s_response is not None:
            return_val = [job['name'] for job in k8s_response.json()]
        return return_val


def retry_request_until_ok(request_lambda, num_attempts, retry_delay_seconds):
    """Retries a request until either the request succeeds or num_attemps is
    exceeded.

    Args:
        request_lambda (lambda): A no-arg lambda that runs the request and
            returns the response.
        num_attemps (int): The maximum number of attempts to make.
        retry_delay_seconds (float): The number of seconds to wait between
            attempts.

    Returns:
        Response: A response object in the event of a successful request, else
            None.

    """
    return_val = None
    for attempt in range(0, num_attempts):
        response = request_lambda()
        ok = is_response_ok(response, attempt+1, retry_delay_seconds)
        if ok:
            return_val = response
            break
        time.sleep(retry_delay_seconds)
    return return_val        
        
        
def is_response_ok(response, attempt_number, retry_delay_seconds):
    """Checks a response from a requests call for errors. Logs any errors and
    returns a boolean indicating success.

    Args:
        response (Response): The response from a requests call.
        attempt_number (int): The number of times the requests call has been
            attempted.
        retry_delay_seconds (float): The number of seconds until the next
            attempt, or None if there will be no next attempt.

    Returns:
        boolean: True if the response contains no HTTP error codes, else False.

    """
    return_val = False
    retry_msg = ''
    if retry_delay_seconds is not None:
        retry_msg = 'Retrying in ' + str(retry_delay_seconds) + ' seconds.'
    try:
        response.raise_for_status()
        # only error I've ever seen is a 500; if this code path ends up failing
        # on others, we'll examine the logs and figure out the right way to
        # handle
        if response.status_code == 500:
            LOGGER.warning('Request returned 500 on attempt ' + \
                str(attempt_number) + '. ' + retry_msg)
        else:
            return_val = True
    except requests.exceptions.HTTPError as http_err:
        LOGGER.debug('Response: ' + str(http_err))
        error_message = http_err.response.text
        LOGGER.debug(error_message)
        LOGGER.warning('Request returned ' + \
            str(http_err.response.status_code) + ' on attempt #' + \
            str(attempt_number) + '. ' + retry_msg)
    except requests.exceptions.Timeout as e1:
        # Maybe set up for a retry, or continue in a retry loop
        LOGGER.warning('Timed out on attempt #' + str(attempt_number) + \
            '. ' + retry_msg)
    except requests.exceptions.TooManyRedirects as e2:
        # Tell the user their URL was bad and try a different one
        LOGGER.warning('Too many redirects on attempt #' + \
            str(attempt_number) + '. ' + retry_msg)
    except requests.exceptions.RequestException as e3:
        # catastrophic error. bail.
        LOGGER.warning('Unknown error encountered on attempt #' + \
            str(attempt_number) + '. ' + retry_msg)
    return return_val
