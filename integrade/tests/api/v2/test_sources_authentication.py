"""docs string goes here"""

from datetime import datetime
import json

from integrade import sources_api
from integrade.tests.constants import (
    SOURCES_URL
)
from integrade.tests.utils import get_credentials


def create_auth_obj_in_sources():
    """Get authentication object from Sources"""
    creds = get_credentials()
    client = sources_api.Client(
        SOURCES_URL,
        auth=creds
    )
    now = datetime.now()
    unique_name = now.strftime('%m_%d_%Y-%H:%M:%S')
    name = f'integrade_test_source_{unique_name}'
    # Get Source object id.
    source_data = json.dumps({'name': name, 'source_type_id': '2'})
    source_r = client.request('post', 'sources', data=source_data)
    source_response = json.loads(source_r.content)
    source_id = source_response['id']
    # Get Endpoint object id.
    endpoint_data = json.dumps({'role': 'aws', 'source_id': source_id})
    endpoint_r = client.request(
        'post', 'endpoints', data=endpoint_data)
    endpoint_response = json.loads(endpoint_r.content)
    endpoint_id = endpoint_response['id']
    # Get Authentication object id.
    auth_data = json.dumps({'resource_id': endpoint_id,
                            'resource_type': 'Endpoint',
                            'username': 'AWSKEYUSEREXAMPLE',
                            'password': 'AWSSECRETKEYEXAMPLE'})
    auth_r = client.request('post', 'authentications', data=auth_data)
    auth_response = json.loads(auth_r.content)
    auth_id = auth_response['id']
    auth_id_response = client.request('get', f'authentications/{auth_id}')

    print(source_response)
    print(endpoint_response)
    print(auth_id_response.text)
    import ipdb; ipdb.set_trace()
    return auth_id_response
