import sys
import yaml
import time


from kubernetes import client, config
from kubernetes.client.rest import ApiException



def cordon_node(cluster_api, node):
    print("Cordoning Node " + node)
    patch_body = {
        'apiVersion': 'v1',
        'kind': 'Node',
        'metadata': {
            'name': node
        },
        'spec': {
            'unschedulable': True
        }
    }

    try:
        cluster_api.patch_node(node, patch_body)
    except ApiException as error:
        print("Exception when cordoning %s: %s\n" % (node, error))



def lambda_handler(node):
    # Load the config file and init the client
    config.load_kube_config()
    cluster_api = client.CoreV1Api()

    print("Recieved a request to evict node", node)
    cordon_node(cluster_api, node)

lambda_handler("k3d-cluster1-agent-0")