import sys
import yaml
import time
import logging


from kubernetes import client, config
from kubernetes.client.rest import ApiException
logging.basicConfig(level=logging.DEBUG)



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
    return pods_to_evict


def evict_pod(cluster_api, pod_name, namespace):
    print("Evicting", pod_name, "in namespace", namespace, "!")
    delete_options = client.V1DeleteOptions()
    delete_options.grace_period_seconds = 750
    metadata = client.V1ObjectMeta(name=pod_name, namespace=namespace)
    body = client.V1Eviction(metadata=metadata, api_version="policy/v1", kind="Eviction", delete_options=delete_options)

    try:
        cluster_api.create_namespaced_pod_eviction(name=pod_name, namespace=namespace, body=body)
    except ApiException as error:
        print("Exception when evicting %s: %s\n" % (pod_name, error))


def lambda_handler(node):
    # Load the config file and init the client
    config.load_kube_config()
    cluster_api = client.CoreV1Api()

    print("Recieved a request to evict node", node)
    cordon_node(cluster_api, node)

    all_evicatable_pods = get_evictable_pods(cluster_api, node)
    for pod in all_evicatable_pods:
        evict_pod(cluster_api, pod.metadata.name, pod.metadata.namespace)
    
    remaining_pods = []
    endtime = time.time() + 60 * 3

    while time.time() < endtime:
        remaining_pods = get_evictable_pods(cluster_api, node)
        if not remaining_pods:
            print("All pods have been evicted.  Safe to proceed with node termination")
            break
        else:
            print("Waiting for " + str(len(remaining_pods)) + " pods to evict!")
            time.sleep(5)

    if remaining_pods:
        print("The following pods did not drain successfully:")
        for pod in remaining_pods:
            print(pod.metadata.namespace + "/" + pod.metadata.name)
        time.sleep(30)

lambda_handler("k3d-cluster1-agent-0")