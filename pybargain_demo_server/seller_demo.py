#!/usr/bin/env python

import uuid
from datetime import datetime
from functools import update_wrapper
from flask import Flask
from flask.globals import request
from flask.helpers import make_response, url_for
from pybargain_protocol.constants import *
from pybargain_protocol.negotiation import Negotiation
from pybargain_protocol.bargaining_message import BargainingMessage
from pybargain_protocol.helpers.bc_api import blockr_sum_unspent_inputs
from helpers.messages_helpers import check_req_format, get_seller_data, send_msg_sync, SDATA_NEGO_ID
from services.negotiator_service import NegotiatorService
from services.nego_db_service import NegoDbService



'''
CONSTANTS
'''
NETWORK = TESTNET
SUM_UNSPENT_FUNC = blockr_sum_unspent_inputs


'''
INITIALIZATION
'''
# Initializes the flask app
app = Flask(__name__)

# Initializes services to access databases or services
# For this toy project we use fake dbs storing data in memory
nego_db_service = NegoDbService()
negotiator = NegotiatorService(NETWORK)


'''
FLASK UTILITY METHODS
'''
# NoCache decorator 
# Required to fix a problem with IE which caches all XMLHttpRequest responses 
def nocache(f):
    def add_nocache(*args, **kwargs):
        resp = make_response(f(*args, **kwargs))
        resp.headers.add('Last-Modified', datetime.now())
        resp.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0')
        resp.headers.add('Pragma', 'no-cache')
        return resp
    return update_wrapper(add_nocache, f)


'''
END POINTS
'''
@app.route('/bargain', methods=['POST'])
@nocache
def bargain():
    try:
    
        nego = None
        nid  = ''   
        
        # Checks format of http request
        if not check_req_format(request): return '', 400
        # Gets the protobuff message (TODO Checks message size ?)
        pbuff = request.data
        # Deserializes the message
        msg = BargainingMessage.deserialize(pbuff)
        
        '''
        Processes the received message
        '''
        if msg.msg_type == TYPE_BARGAIN_REQUEST:
            '''
            Let's start a new negotiation
            '''
            # Checks message format
            if msg.check_msg_fmt(NETWORK): 
                # Builds a new negotiation object
                nid = str(uuid.uuid4())
                nego = Negotiation(nid, ROLE_SELLER, NETWORK)  
                # Checks message / negotiation consistency
                nego.check_consistency(msg)
                # Appends the message to the chain
                nego.append(msg)
                # Writes negotiation into db
                nego_db_service.create_nego(nid, nego)
            else:
                # Invalid message format. Sets an error on the message.
                # It will trigger the sending of a CANCEL message. 
                msg.log_error("Invalid message format")   
        else:
            '''
            Let's continue an existing negotiation
            '''
            # Extracts negotiation id from the message
            sdata = get_seller_data(msg)
            nid = sdata.get(SDATA_NEGO_ID, '') 
            # Gets the negotiation from db
            nego = nego_db_service.get_nego_by_id(nid)
            if nego is None: 
                # Sets an error on the message if nego wasn't found
                # It will trigger the sending of a CANCEL message. 
                msg.log_error("Negotiation cannot be found")
            else:
                # Checks message has not already been received
                if nego.already_received(msg): return '', 200        
                # If message is a PROPOSAL, prechecks the transactions
                if msg.msg_type == TYPE_BARGAIN_PROPOSAL:
                    last_msg = nego.get_last_msg()
                    nego.precheck_txs(msg, last_msg, SUM_UNSPENT_FUNC)  
                # Checks message format (and consistency with negotiation if valid format)
                if msg.check_msg_fmt(NETWORK): 
                    nego.check_consistency(msg)    
                # Appends the message to the chain
                nego.append(msg)
                # Writes negotiation into db
                nego_db_service.update_nego(nid, nego)    
        
        '''
        Builds and sends a response
        '''
        # Checks message status
        if msg.status == MSG_STATUS_UND:
            # We were unable to validate the message.
            # Response will be sent asynchronously (not implemented in demo)
            return '', 200
        
        # Checks if negotiation has reached a final state
        if nego.status in [NEGO_STATUS_COMPLETED, NEGO_STATUS_CANCELLED]:
            # Returns an http ack
            return '', 200        
        # Asks negotiator to build the next message (applying a very basic strategy)
        if not (nego is None):
            negotiator.bargain_uri = url_for('bargain', _external=True) 
            new_msg = negotiator.process(nego) 
            if not (new_msg is None):
                # Appends the new message to the chain
                nego.append(new_msg)
                nego_db_service.update_nego(nid, nego)             
                # Sends the new message as a http response
                next_msg_types = nego.get_next_msg_types()
                response = send_msg_sync(new_msg, next_msg_types)
                return response, 200
            else:
                # Something went wrong on our side
                # Returns an http ack for now. Response will be sent asynchronously (not implemented in demo)
                return '', 200
        else:
            # Something went wrong on our side. We don't find the negotiation
            return '', 400
        
        '''
        Cleaning (for demo purpose)
        '''
        # Removes completed negos from memory
        if nego.status in [NEGO_STATUS_COMPLETED, NEGO_STATUS_CANCELLED]:
            nego_db_service.delete_nego(nid)
    
    except Exception, e:
        return '', 500

if __name__ == '__main__':
    # Comment/uncomment following lines to switch "production" / debug mode
    #app.run(host='0.0.0.0', port=8082)
    app.run(debug=True, port=8082)
    