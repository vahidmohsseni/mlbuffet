from json import JSONDecodeError
from os import path, getenv

import gevent
import requests
from deprecated.classic import deprecated

from utils.storage_pojos import HttpJsonResponse
from utils.ipscan import IPScan

# Request constants
OVERLAY_NETWORK = getenv('OVERLAY_NETWORK')
URI_SCHEME = 'http://'


def _url(resource):
    #    return URI_SCHEME + LOAD_BALANCER_ENDPOINT + resource
    return URI_SCHEME + 'modelhost:8000' + resource


def _is_ok(code):
    return str(code).startswith('2')


def _get(resource):
    return requests.get(_url(resource)).json()


def _post(resource, json_data):
    response = requests.post(_url(resource), json=json_data).json()
    return response


@deprecated
def _put(resource, files):
    response = requests.put(_url(resource), files=files).json()
    if _is_ok(response['http_status']['code']):
        update_models()
    return response


def _put2(resource, files):
    MODELHOST_IP_LIST = IPScan('modelhost')

    for IP in MODELHOST_IP_LIST:
        url = URI_SCHEME + IP + ':8000' + resource
        response = requests.put(url, files=files).json()

        if not _is_ok(response['http_status']['code']):
            return HttpJsonResponse(
                500, http_status_description='One or more modelhosts returned non 2XX HTTP code').get_response()
    return HttpJsonResponse(
        200, http_status_description='OK').get_response()


def _delete(resource):
    raw_response = requests.delete(_url(resource))
    try:
        response = raw_response.json()
        if _is_ok(response['http_status']['code']):
            update_models()
    except JSONDecodeError:
        response = raw_response.text
        update_models()

    return response


def upload_new_model(tag, new_model, filename):
    resource = '/modelhost/models/' + tag
    return _put2(resource, {'model': new_model, 'filename': filename})


def delete_model(tag):
    resource = '/modelhost/models/' + tag
    update_models()
    return _delete(resource)


def test_load_balancer(data_array):
    resource = '/modelhost/api/test'

    jobs = [gevent.spawn(_get, path.join(resource, str(elem)))
            for elem in data_array]
    gevent.wait(jobs)

    # Print modelhosts responses and check if all HTTP codes are 2XX
    all_responses_2xx = True
    for job in jobs:
        if not _is_ok(job.value['http_status']['code']):
            all_responses_2xx = False

        print(f'Received response: {job.value}')

    if all_responses_2xx:
        return HttpJsonResponse(200).get_response()
    return HttpJsonResponse(
        500, http_status_description='One or more modelhosts returned non 2XX HTTP code').get_response()


def update_models():
    resource = '/modelhost/updatemodels'
    MODELHOST_IP_LIST = IPScan('modelhost')
    for IP in MODELHOST_IP_LIST:
        url = URI_SCHEME + IP + ":8000" + resource
        print(url)
        gevent.spawn(requests.get, url=url)
    return HttpJsonResponse(200).get_response()
