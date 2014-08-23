#!/usr/bin/env python
'''
A class negotiating to sell a product/service
Implements a very basic strategy
'''
import calendar
from random import random, randint
from datetime import datetime
from bitcoin.main import sha256, privtopub, pubtoaddr
from bitcoin.transaction import address_to_script
from pybargain_protocol.constants import *
from pybargain_protocol.bargaining_cancellation import BargainingCancellationDetails
from pybargain_protocol.bargaining_message import BargainingMessage
from pybargain_protocol.bargaining_request_ack import BargainingRequestACKDetails
from pybargain_protocol.bargaining_completion import BargainingCompletionDetails
from pybargain_protocol.bargaining_proposal_ack import BargainingProposalACKDetails
from helpers.messages_helpers import build_seller_data


class NegotiatorService(object):
    
    
    '''
    CONSTANTS
    '''
    WELCOME_MSG     = 'Hi ! Here is our best offer for a BD-48T dedicated server (monthly rental)'
    AGREE_MSG       = 'Ok for this price. Please confirm the deal.'
    COMPLETION_MSG  = 'Deal ! Your transaction has been broadcast for validation'
    CANCEL_MSG      = 'We were unable to process your last message. Negotiation is aborted. Errors detected : %s'
    
    NEGO_MSGS       = ['Come on ! This is an Intel Xeon',
                       'This is cheaper than free',
                       'There\'s 256 IP addresses !',
                       'Oh please. I have many devices to feed',
                       'Do you try to kill my business ?',
                       'Did you notice the 32 cores and 64 threads ?',
                       'Let\'s agree on this price and I add a 2TB disk',
                       'What ? You\'re not serious ?',
                       'I can\'t propose a better price',
                       'Do you know the price on AWS ?',
                       'This is our last available instance. Don\'t miss the opportunity',
                       'Ok. I propose this price for a different model with 16 cores',
                       'Let\'s agree on this price and I add 16GB RAM',
                       'How about a laptop, instead ?',
                       'You won\'t find a better price anywhere else',
                       'This is the best model available right now !',
                       'This is an incredible opportunity !',
                       'This is my best price']
    
    '''
    ATTRIBUTES
    
    bargain_uri   = bargain uri used by the seller
    
    _privkey1     = first private key
    _pubkey1      = first public key
    _addr1        = first address
    _script1      = first output script
    
    _privkey2     = second private key
    _pubkey2      = second public key
    _addr2        = second address
    _script2      = second output script
    
    _privkeysign  = private key used to sign messages
    _pubkeysign   = public key used to sign messages
    '''
    
    
    def __init__(self, network, bargain_uri = ''):
        '''
        Constructor
        '''
        self.bargain_uri = bargain_uri
        
        magicbytes = MAGIC_BYTES_TESTNET if network == TESTNET else MAGIC_BYTES_MAINNET
        
        self._privkey1    = sha256('This is the first private key for the seller')
        self._pubkey1     = privtopub(self._privkey1)  
        self._addr1       = pubtoaddr(self._pubkey1, magicbytes)
        self._script1     = address_to_script(self._addr1)
        
        self._privkey2    = sha256('This is the second private key for the seller')
        self._pubkey2     = privtopub(self._privkey2) 
        self._addr2       = pubtoaddr(self._pubkey2, magicbytes)
        self._script2     = address_to_script(self._addr2)
        
        self._privkeysign = sha256('This is a private key used to sign messages sent by the seller')
        self._pubkeysign  = privtopub(self._privkeysign)  
        
    
    def process(self, nego):
        '''
        Builds the next message for a given negotiation
        
        Parameters:
            nego = the negotiation to process
        '''
        if nego is None: return None
        if not (nego.get_next_active_role() == ROLE_SELLER): return None
        
        msg      = None
        last_msg = nego.get_last_msg()
        
        if last_msg.status == MSG_STATUS_KO:
            msg = self._build_cancel_msg(last_msg, nego)
        elif last_msg.status == MSG_STATUS_OK:
            if nego.status == NEGO_STATUS_INITIALIZATION:
                msg = self._build_request_ack_msg(last_msg, nego)
            elif nego.status == NEGO_STATUS_NEGOTIATION:
                msg = self._build_proposal_ack_msg(last_msg, nego)
            elif nego.status == NEGO_STATUS_COMPLETION:
                msg = self._build_completion_msg(last_msg, nego)
            
        if msg == None: return None
        
        if msg.check_msg_fmt(nego.network):
            msg.sign(last_msg, SIGN_ECDSA_SHA256, self._pubkeysign, self._privkeysign)
            if nego.check_consistency(msg): 
                msg.pbuff = msg.serialize()
                return msg
            else: return None
        else: return None
                
    
    def _build_request_ack_msg(self, last_msg, nego):
        '''
        Builds a RequestACK message
        
        Parameters:
            last_msg = last message received from buyer            
            nego     = current negotiation
        '''
        time    = long(calendar.timegm(datetime.now().timetuple()))
        bdata   = last_msg.details.buyer_data
        sdata   = build_seller_data(nego.nid)
        network = nego.network
        expires = time + 1200L # 20 minutes
        uri     = self.bargain_uri
        memo    = NegotiatorService.WELCOME_MSG
        outputs = [{'amount': 150000000, 'script': self._script1}, 
                   {'amount': 100000000, 'script': self._script2}]
        dtls = BargainingRequestACKDetails(time, bdata, sdata, network, expires, uri, outputs, memo) 
        return BargainingMessage(TYPE_BARGAIN_REQUEST_ACK, dtls)
    
    
    def _build_proposal_ack_msg(self, last_msg, nego):
        '''
        Builds a ProposalACK message
        
        Parameters:
            last_msg = last message received from buyer
            nego     = current negotiation
        '''
        time    = long(calendar.timegm(datetime.now().timetuple()))
        bdata   = last_msg.details.buyer_data
        sdata   = build_seller_data(nego.nid)
        outputs, memo = self._compute_new_offer(last_msg, nego)
        dtls = BargainingProposalACKDetails(time, bdata, sdata, outputs, memo)
        return BargainingMessage(TYPE_BARGAIN_PROPOSAL_ACK, dtls)
    
    
    def _build_completion_msg(self, last_msg, nego):
        '''
        Builds a Proposal message
        
        Parameters:
            last_msg = last message received from buyer
            nego     = current negotiation
        '''
        time    = long(calendar.timegm(datetime.now().timetuple()))
        bdata   = last_msg.details.buyer_data
        sdata   = build_seller_data(nego.nid)
        txs     = last_msg.details.transactions
        memo    = NegotiatorService.COMPLETION_MSG
        dtls = BargainingCompletionDetails(time, bdata, sdata, txs, memo)
        return BargainingMessage(TYPE_BARGAIN_COMPLETION, dtls)


    def _build_cancel_msg(self, last_msg, nego):
        '''
        Builds a Cancellation message
        
        Parameters:
            last_msg = last message received from buyer            
            nego     = current negotiation
        '''
        time = long(calendar.timegm(datetime.now().timetuple()))
        bdata = last_msg.details.buyer_data
        sdata = build_seller_data(nego.nid)
        memo = NegotiatorService.CANCEL_MSG % ", ".join(last_msg.errors)
        dtls = BargainingCancellationDetails(time, bdata, sdata, memo)
        return BargainingMessage(TYPE_BARGAIN_CANCELLATION, dtls)
    
    
    def _select_memo(self):
        idx = randint(0, len(NegotiatorService.NEGO_MSGS) - 1)
        return NegotiatorService.NEGO_MSGS[idx]
    
    
    def _compute_new_offer(self, last_msg, nego):
        prev_idx = nego.length() - 2
        buyer_last_offer = last_msg.details.amount + last_msg.details.fees
        seller_last_offer = nego.get_msg_at_idx(prev_idx).details.amount
        
        if random() < 0.1: 
            # We keep the same offer (probability = 1/10)
            new_offer = nego.get_msg_at_idx(prev_idx).details.amount
            outputs =  nego.get_msg_at_idx(prev_idx).details.outputs
        else:
            def round_amount(x): return (x / 100000) * 100000
            # Computes a new offer
            gap = seller_last_offer - buyer_last_offer
            if gap < 1000000:
                new_offer = buyer_last_offer
            elif gap < 2000000:
                new_offer = seller_last_offer
            else:
                discount = int(random() * gap / 2)
                new_offer = round_amount(seller_last_offer - discount)
                new_offer = max(buyer_last_offer, new_offer)
            # Splits the offer in 2 outputs
            offer_part1 = round_amount(int(new_offer * 0.5))
            offer_part2 = new_offer - offer_part1
            outputs = [{'amount': offer_part1, 'script': self._script1}, 
                       {'amount': offer_part2, 'script': self._script2}]
            
        # Gets a content for memo field 
        memo = self.AGREE_MSG if (new_offer == buyer_last_offer) else self._select_memo()
        # Returns the new offer (outputs, memo)
        return (outputs, memo)
    
    
