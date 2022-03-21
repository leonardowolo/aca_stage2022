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


def get_evictable_pods(cluster_api, node):
    field_selector = 'spec.nodeName=' + node
    pods = cluster_api.list_pod_for_all_namespaces(watch=False, field_selector=field_selector)
    pods_to_evict = []

    for pod in pods.items:
        if pod.metadata.owner_references[0].kind != 'DaemonSet':
            pods_to_evict.append(pod)
    print(pods_to_evict)


def lambda_handler(node):
    # Load the config file and init the client
    config.load_kube_config()
    cluster_api = client.CoreV1Api()

    print("Recieved a request to evict node", node)
    cordon_node(cluster_api, node)

    all_evicatable_pods = get_evictable_pods(cluster_api, node)
    print(all_evicatable_pods)

lambda_handler("k3d-cluster1-agent-0")