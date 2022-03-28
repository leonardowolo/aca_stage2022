from asyncio.log import logger
import sys
import yaml
import time
import logging


from kubernetes import client, config
from kubernetes.client.rest import ApiException

LOG_FORMAT = "%(asctime)s %(levelname)s : %(message)s"
logging.basicConfig(filename='lambda.log', level=logging.INFO, format=LOG_FORMAT, datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger()


def lambda_handler(node):
    # Load the config file and init the client
    config.load_kube_config()
    cluster_api = client.CoreV1Api()

    logger.info("Received a request to evict node {}".format(node))

    all_evicatable_pods = get_evictable_pods(cluster_api, node)
    unhealthy_pods = get_pod_status(all_evicatable_pods)

    if not unhealthy_pods:
        logger.info("There are no unhealthy pods on node {}. Node will be cordoned".format(node))
        time.sleep(5)
        cordon_node(cluster_api, node)
        logger.info("{} pods need to be evicted on node {}".format(str(len(all_evicatable_pods)), node))
        for pod in all_evicatable_pods:
            evict_pod(cluster_api, pod.metadata.name, pod.metadata.namespace)
        time.sleep(15)

        remaining_pods = []
        endtime = time.time() + 60 * 3

        while time.time() < endtime:
            remaining_pods = get_evictable_pods(cluster_api, node)
            if not remaining_pods:
                logger.info("All pods have been evicted. Safe to proceed with node termination")
                break
            else:
                logger.info("Waiting for {} pods to evict".format(str(len(remaining_pods))))
                time.sleep(5)

        if remaining_pods:
            logger.warning("The following pods did not drain successfully:")
            for pod in remaining_pods:
                logger.warning("{} / {}".format(pod.metadata.namespace, pod.metadata.name))
            time.sleep(45)
    else:
        logger.error("Not all pods on node {} are healthy. Check de pods before upgrading.".format(node))


def cordon_node(cluster_api, node):
    logger.info("Cordoning Node {}".format(node))
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
        logger.warning("Exception when cordoning {}: {}\n".format(node, error))


def get_evictable_pods(cluster_api, node):
    field_selector = 'spec.nodeName=' + node
    pods = cluster_api.list_pod_for_all_namespaces(watch=False, field_selector=field_selector)
    pods_to_evict = []

    for pod in pods.items:
        if pod.metadata.owner_references[0].kind != 'DaemonSet':
            pods_to_evict.append(pod)
    return pods_to_evict


def get_pod_status(pods):
    unhealthy_pod = 0
    for pod in pods:
        if pod.status.phase != 'Running':
            unhealthy_pod += 1

    if unhealthy_pod > 0:
        return True
    else:
        return False


def evict_pod(cluster_api, pod_name, namespace):
    logger.info("Evicting {} in namespace {}".format(pod_name, namespace))
    delete_options = client.V1DeleteOptions()
    delete_options.grace_period_seconds = 600
    metadata = client.V1ObjectMeta(name=pod_name, namespace=namespace)
    body = client.V1Eviction(metadata=metadata, api_version="policy/v1", kind="Eviction", delete_options=delete_options)

    try:
        cluster_api.create_namespaced_pod_eviction(name=pod_name, namespace=namespace, body=body)
    except ApiException as error:
        logger.warning("Exception when evicting {}: {}\n".format(pod_name, error))



lambda_handler("k3d-cluster1-agent-1")