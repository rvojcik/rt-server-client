#
# Process Dell Warranty API
#
#
# Return dictionary
#
# { 'description': ....,
#   'datetime': <datetimeobject>
# }
#
# Example:
# {
#   'description': u'ND ProSupport For IT On-Site Extended with Dates',
#   'datetime': datetime.datetime(2016, 4, 15, 23, 59, 59, 999000)
# }
#

import requests
import datetime

auth_addr = 'https://apigtwb2c.us.dell.com/auth/oauth/v2/token'
api_addr = 'https://apigtwb2c.us.dell.com/PROD/sbil/eapi/v5/asset-entitlements'
grant_type = 'client_credentials'

def process_entitlements(array):
    """ Process entitlements """

    output = {}

    for element in array['entitlements']:
        dt_obj = datetime.datetime.strptime(element['endDate'], '%Y-%m-%dT%H:%M:%S.%fZ')
        if 'datetime' in output.keys():
            if output['datetime'] <= dt_obj:
                output['datetime'] = dt_obj
                output['description'] = element['serviceLevelDescription']
        else:
            output['datetime'] = dt_obj
            output['description'] = element['serviceLevelDescription']

    return output


def get_dell_warranty(config, service_tag):
    """ Return Dell Warranty information """
    # Read config
    client_id = config.get('global','dell_auth_client_id')
    client_secret = config.get('global','dell_auth_secret')

    # Authentification
    auth_data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': grant_type
    }

    r = requests.post(auth_addr, data = auth_data)

    if r.status_code == 200:
        try:
            auth_array = r.json()
        except ValueError:
            # Unable to decode json
            return False

        if 'access_token' in auth_array.keys():
            # We have token for auth, lets get information about server
            headers = {
                'Accept': 'application/json',
                'Authorization': 'Bearer ' + auth_array['access_token']
            }

            request_url = '%s?servicetags=%s' % (api_addr, service_tag)
            r = requests.get(request_url, headers = headers)

            if r.status_code == 200:
                try:
                    content_array = r.json()
                except ValueError:
                    # Unable to decode JSON in warranty response
                    return False

                if len(content_array) == 0:
                    # No output
                    return False

                # Process Warranty information
                if 'entitlements' in content_array[0].keys():
                    response = process_entitlements(content_array[0])
                    return response
                else:
                    # Missing erray with entitlements
                    return False

            else:
                # Wrong response code from API warranty
                return False
        else:
            # Unable to find access_token in response
            return False
    else:
        # Unable to autentificate
        return False

