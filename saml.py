#!/usr/bin/env python

import requests
import json
import boto3
import sys
from bs4 import BeautifulSoup
import base64
import xml.etree.ElementTree as ET
import datetime
import pickle
import os
import getpass
from os.path import expanduser
from configobj import ConfigObj
from pytz import timezone
import pytz
try:
   input = raw_input
except NameError:
   pass

debug = False

awsdir = os.path.join(expanduser('~'), '.aws')                          # AWS Directory
credentials_file = os.path.join(awsdir, 'credentials')                  # AWS Credentials File
auth_cache_file = os.path.join(expanduser('~'), '.assumedRole.pkl')     # AWS Credentials cache file
config_user_file = os.path.join(expanduser('~'), '.aws', 'user')
env_names_file = os.path.join(expanduser('~'), '.aws', 'env.json')

def check_credentials_file():
    if not os.path.isfile(credentials_file):
        print("Credentials file: %s doesn't exist." % credentials_file)
        return False
    else:
        print("Credentials file: %s in place." % credentials_file)
        return True


def update_credentials_file(aws_access_key_id, aws_secret_access_key, aws_session_token):

    config = ConfigObj()
    config['default'] = {}
    config['default']['aws_access_key_id'] = aws_access_key_id
    config['default']['aws_secret_access_key'] = aws_secret_access_key
    config['default']['aws_session_token'] = aws_session_token
    config['default']['aws_security_token'] = aws_session_token     # for compatibility with ansible ec2.py inventory script

    if not os.path.exists(awsdir):
        os.makedirs(awsdir)

    try:
        with open(credentials_file, 'wb') as configfile:
            config.write(configfile)
    except IOError:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)

    # Change file permissions
    os.chmod(credentials_file, int('0600', 8))

    print("\nDone, credentials file: %s created/refreshed." % credentials_file)
    exit()


def auth_cached():
    try:
        with open(auth_cache_file, 'rb') as input:
            assumedRoleObject = pickle.load(input)

        credentials = assumedRoleObject['Credentials']
    except:
        return None

    return credentials


def auth_live():
    url = 'https://amplis.deutsche-boerse.com/auth/json/authenticate'
    payload = {'realm': '/internet', 'spEntityID': 'urn:amazon:webservices'}
    headers = {'Content-Type': 'application/json'}

    try:
        r1 = requests.post(url, params=payload, headers=headers)
        r1j = r1.json()
        if debug:
            print('Url:         ' + r1.url)
            print('Status Code: ' + str(r1.status_code))
            print('Reason:      ' + r1.reason)
            #print 'Text:        ' + r1.text
            print('Headers:     ' + str(r1.headers))
            print('Text:')
            print(json.dumps(r1j, indent=2))
    except:
        print('Request failed, check network connection!')
        return None

    try:
        if os.path.isfile(config_user_file):
            userfile = open(config_user_file, 'r') 
            temp = userfile.readline().strip()
            print("Using username: " + temp)
            r1j['callbacks'][0]['input'][0]['value'] = temp
        else:
            r1j['callbacks'][0]['input'][0]['value'] = input('Username: ')     # should locate 'IDToken1'
        r1j['callbacks'][1]['input'][0]['value'] = input('MFA token: ')      # should locate 'IDToken2'
        r1j['callbacks'][2]['input'][0]['value'] = getpass.getpass('Password: ')   # should locate 'IDToken3'
        if debug:
            print(json.dumps(r1j, indent=2))
    except Exception as e:
        print('No valid form to fill returned - ' + str(e))
        return None

    try:
        r2 = requests.post(url, params=payload, headers=headers, data=json.dumps(r1j))
        r2j = r2.json()
        if debug:
            print('Url:        ' + r2.url)
            print('Status Code:' + str(r2.status_code))
            print('Reason:     ' + r2.reason)
            #print 'Text:       ' + r2.text
            print('Headers:    ' + str(r2.headers))
            print('Text:')
            print(json.dumps(r2j, indent=2))
    except:
        print('Request failed, check network connection!')
        return None

    try:
        token = r2j['tokenId']
    except:
        print('Authentication failed!')
        return None

    if debug:
        print('Extracted token: ' + token)

    if debug: # some interesting debug code
        url = 'https://amplis.deutsche-boerse.com/auth/json/users'
        payload = {'realm': '/internet', '_action': 'idFromSession'}
        headers = {'Content-Type': 'application/json', 'Cookie': 'es=' + token}

        try:
            r3 = requests.post(url, params=payload, headers=headers)
            r3j = r3.json()
            print('Url:         ' + r3.url)
            print('Status Code: ' + str(r3.status_code))
            print('Reason:      ' + r3.reason)
            #print 'Text:        ' + r3.text
            print('Headers:     ' + str(r3.headers))
            print('Text:')
            print(json.dumps(r3j, indent=2))
        except:
            print('Request failed, check network connection!')
            return None

        id = r3j['id']
        if debug:
            print('Extracted id: ' + id)

        url = 'https://amplis.deutsche-boerse.com/auth/json/users/' + id
        payload = {'realm': '/internet'}
        headers = {'Content-Type': 'application/json', 'Cookie': 'es=' + token}

        r4 = requests.get(url, params=payload, headers=headers)
        r4j = r4.json()
        print('Url:         ' + r4.url)
        print('Status Code: ' + str(r4.status_code))
        print('Reason:      ' + r4.reason)
        #print 'Text:        ' + r4.text
        print('Headers:     ' + str(r4.headers))
        print(json.dumps(r4j, indent=2))

    url = 'https://amplis.deutsche-boerse.com/auth/saml2/jsp/idpSSOInit.jsp'
    payload = {'metaAlias': '/internet/idp', 'spEntityID': 'urn:amazon:webservices', 'redirected': 'true'}
    headers = {'Cookie': 'es=' + token,
               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
               'Accept-Encoding': 'gzip, deflate, br',
               'Accept-Language': 'de,en-US;q=0.7,en;q=0.3'}

    r5 = requests.get(url, params=payload, headers=headers)
    if debug:
        print('Url:         ' + r5.url)
        print('Status Code: ' + str(r5.status_code))
        print('Reason:      ' + r5.reason)
        print('Text:        ' + r5.text)
        print('Headers:     ' + str(r5.headers))

    soup = BeautifulSoup(r5.text, 'html.parser')
    assertion = ''

    # Look for the SAMLResponse attribute of the input tag (determined by
    # analyzing the debug print lines above)
    for inputtag in soup.find_all('input'):
        if(inputtag.get('name') == 'SAMLResponse'):
            if debug:
                print(inputtag.get('value'))
            assertion = inputtag.get('value')

    if debug:
        print(base64.b64decode(assertion))

    # Parse the returned assertion and extract the authorized roles
    awsroles = []
    root = ET.fromstring(base64.b64decode(assertion))
    for saml2attribute in root.iter('{urn:oasis:names:tc:SAML:2.0:assertion}Attribute'):
        if (saml2attribute.get('Name') == 'https://aws.amazon.com/SAML/Attributes/Role'):
            for saml2attributevalue in saml2attribute.iter('{urn:oasis:names:tc:SAML:2.0:assertion}AttributeValue'):
                awsroles.append(saml2attributevalue.text)

    # Note the format of the attribute value should be role_arn,principal_arn
    # but lots of blogs list it as principal_arn,role_arn so let's reverse
    # them if needed
    for awsrole in awsroles:
        chunks = awsrole.split(',')
        if'saml-provider' in chunks[0]:
            newawsrole = chunks[1] + ',' + chunks[0]
            index = awsroles.index(awsrole)
            awsroles.insert(index, newawsrole)
            awsroles.remove(awsrole)

    # If I have more than one role, ask the user which one they want,
    # otherwise just proceed
    env_names = json.loads('{}')
    if os.path.isfile(env_names_file):
        try:
            temp = open(env_names_file).read()
            env_names = json.loads(temp)
        except (RuntimeError, TypeError, NameError, AttributeError, OSError, ValueError, ), e:
            print('\033[91m' + 'Error while reading file ' + env_names_file + '\033[0m')
            print('\033[91m' + format(e) + '\033[0m')

    if debug:
        print("Number of awsroles found: " + str(len(awsroles)))
    if len(awsroles) > 1:
        i = 0
        print("Please choose the role you would like to assume:")
        for awsrole in awsroles:
            env_number = awsrole.split(',')[0].split(':')[4]
            env_role = awsrole.split(',')[0].split(':')[5]
            env_name = '' if env_names.get(env_number) is None else ' - ' + '\033[1;92m' + env_names.get(env_number) + '\033[0m'
            print('[' +  str(i) + ']: ' + env_number + ' - ' + env_role + env_name)
            i += 1
        print("Selection: ")
        selectedroleindex = input()

        # Basic sanity check of input
        if int(selectedroleindex) > (len(awsroles) - 1):
            print('You selected an invalid role index, please try again')
            sys.exit(0)

        role_arn = awsroles[int(selectedroleindex)].split(',')[0]
        principal_arn = awsroles[int(selectedroleindex)].split(',')[1]
    else:
        role_arn = awsroles[0].split(',')[0]
        principal_arn = awsroles[0].split(',')[1]

    if debug:
        print("Role ARN:      " + role_arn)
        print("Principal ARN: " + principal_arn)

    client = boto3.client('sts')
    assumedRoleObject = client.assume_role_with_saml(
        RoleArn=role_arn,
        PrincipalArn=principal_arn,
        SAMLAssertion=assertion)

    with open(auth_cache_file, 'wb') as output:
        pickle.dump(assumedRoleObject, output, pickle.HIGHEST_PROTOCOL)

    credentials = assumedRoleObject['Credentials']
    return credentials

# Iterate over credentials functions
ret_code = 0

for fun in [auth_cached, auth_live]:
    credentials = fun()

    try:
        # skip in case cache is empty
        if not credentials:
            continue
        utc    = pytz.utc
        berlin = timezone('Europe/Berlin')
        aws_access_key_id = credentials['AccessKeyId'],
        aws_secret_access_key = credentials['SecretAccessKey']
        aws_session_token = credentials['SessionToken']

        exp = credentials['Expiration']  # offset aware time
        now = utc.localize(datetime.datetime.utcnow())   # now is utcnow offset aware
        diff = exp - now

        if diff.total_seconds() < 300:
            print("Credential update necessary")
            continue    # update (auth_live) when credentials will timout in 5 minutes

        print('Key ID:         ' + str(aws_access_key_id[0]))
        print('Access Key:     ' + str(aws_secret_access_key))
        print('Security/Session Token:  ' + str(aws_session_token))
        print('Expiration:     ' + str(credentials['Expiration'].astimezone(berlin).strftime('%Y-%m-%d %H:%M:%S%z')))
        print('Expiration(UTC):' + str(credentials['Expiration'].strftime('%Y-%m-%d %H:%M:%S%z')))
        print('Time till expiration: ' + str(diff.seconds/60) + ' min')

        if diff.total_seconds() >= 3590:          # true if new credentials are created
            print('Updating credentials file... ')
            update_credentials_file(aws_access_key_id[0], aws_secret_access_key, aws_session_token)
        else:
            if check_credentials_file() == True:
                print('No need to update.\nRemains ' + str(diff.total_seconds()) + ' seconds.')
            else:
                print("will update credentials file:")
                update_credentials_file(aws_access_key_id[0], aws_secret_access_key, aws_session_token)
        break

    except Exception as e:
        import traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)

sys.exit(ret_code)
