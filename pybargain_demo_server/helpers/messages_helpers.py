#!/usr/bin/env python

import json
from flask.helpers import make_response
from pybargain_protocol.constants import MESSAGE_TYPES


'''
CONSTANTS
'''
# Defines some usefull constants
VALID_MEDIA_TYPES = ['application/bitcoin-' + mt for mt in MESSAGE_TYPES]

# seller_data keys
SDATA_PRODUCT_ID = 'pid'
SDATA_NEGO_ID    = 'nid'


'''
HTTP REQUEST
'''
def check_req_format(req):
    '''
    Checks if http request has a valid format (mime type and encoding)
    
    Parameters:
        req = http request
    '''
    ct_heads = req.headers.get('Content-Type','').split(';')
    valid_content_type =  any([(ct in VALID_MEDIA_TYPES) for ct in ct_heads])
    valid_encoding = req.headers.get('Content-Transfer-Encoding','') == 'binary'
    return valid_content_type and valid_encoding


def send_msg_sync(msg, next_msg_types):
    '''
    Sends a BargainingMessage as a synchronous response to a received http request
    Returns the response
    
    Parameters:
        msg            = BargainingMessage to be sent
        next_msg_types = list of expected message types for the next message
    '''
    if (msg is None) or (not msg.pbuff): return None
    
    resp = make_response(msg.pbuff)
    resp.headers['Content-Type'] = 'application/bitcoin-%s' % msg.msg_type 
    resp.headers['Content-Transfer-Encoding'] = 'binary'
    next_msg_types = ['application/bitcoin-' + nmt for nmt in next_msg_types]
    resp.headers['Accept'] = ','.join(next_msg_types)
    return resp


'''
SELLER DATA
'''
def get_seller_data(msg):
    '''
    Extracts the seller data from a BargainingMessage and returns a dictionary
    
    Parameters:
        msg = BargainingMessage
    '''
    if msg is None or msg.details is None: return {}
    sdata = msg.details.seller_data
    if sdata: return json.loads(sdata)
    else: return {}


def build_seller_data(nid = '', pid = ''):
    '''
    Builds and serializes the seller_data structure
    
    Parameter:
        nid = negotiation id
        pid = product id
    '''
    sdata = dict()
    if nid: sdata[SDATA_NEGO_ID] = nid
    if pid: sdata[SDATA_PRODUCT_ID] = pid
    return json.dumps(sdata)



    