'''
Created on 12 Jan 2017

@author: wat
'''

import logging

from datetime import datetime
from uuid import uuid4

from OpenSSL.SSL import Error

from urllib2 import URLError

from ndg.saml.saml2.binding.soap.client.attributequery import \
                                                    AttributeQuerySslSOAPBinding
from ndg.saml.saml2.binding.soap.client.requestbase import RequestResponseError
from ndg.saml.saml2.core import (AttributeQuery, SAMLVersion, Attribute, Issuer,
                                 Subject, NameID, DecisionType)

from ndg.soap.client import UrlLib2SOAPClientError
from ndg.saml.saml2.core import (Issuer, Subject, NameID)
from ndg.saml.saml2.binding.soap.client.authzdecisionquery import \
                                            AuthzDecisionQuerySslSOAPBinding
from ndg.saml.utils.factory import AuthzDecisionQueryFactory

logger = logging.getLogger(__name__)


def get_authz_decision(environ, url, remote_user):
    saml_trusted_ca_dir = environ.get('saml_trusted_ca_dir', '')
    authz_service_uri = environ.get('authz_service_uri', '')
    
    client_binding = AuthzDecisionQuerySslSOAPBinding()
    client_binding.sslCACertDir = saml_trusted_ca_dir
    client_binding.clockSkewTolerance = 1 # 1 second tolerance
    
    # Make a new query object
    query = AuthzDecisionQueryFactory.create()
    
    # Copy constant settings. These constants were set at 
    # initialisation
    query.subject = Subject()
    query.subject.nameID = NameID()
    query.subject.nameID.format = 'urn:esg:openid'
    
    query.issuer = Issuer()
    query.issuer.format = Issuer.X509_SUBJECT
    query.issuer.value = 'O=NDG, OU=Security, CN=localhost'
   
    # Set dynamic settings particular to this individual request 
    query.subject.nameID.value = remote_user
    query.resource = url
    
    try:
        saml_authz_response = client_binding.send(query,
                                             uri=authz_service_uri)
        
    except (UrlLib2SOAPClientError, URLError) as e:
        import traceback
        
        if isinstance(e, UrlLib2SOAPClientError):
            logger.error("Error, HTTP %s response from authorisation "
                      "service %r requesting access to %r: %s", 
                      e.urllib2Response.code,
                      authz_service_uri, 
                      url,
                      traceback.format_exc())
        else:
            logger.error("Error, calling authorisation service %r "
                      "requesting access to %r: %s", 
                      authz_service_uri, 
                      url,
                      traceback.format_exc())
    
    assertions = saml_authz_response.assertions
    
    # Set HTTP 403 Forbidden response if any of the decisions returned are
    # deny or indeterminate status
    fail_decisions = (DecisionType.DENY, #@UndefinedVariable
                     DecisionType.INDETERMINATE) #@UndefinedVariable
    
    # Review decision statement(s) in assertions and enforce the decision
    assertion = None
    for assertion in assertions:
        for authz_decision_statement in assertion.authzDecisionStatements:
            assertion = authz_decision_statement.decision.value
            if assertion in fail_decisions:
                break

    if assertion is None:
        logger.error(
            "No assertions set in authorisation decision response "
            "from {0}".format(authz_service_uri)
        )
    
    return assertion

def userid_query(environ, openid):
    saml_trusted_ca_dir = environ.get('saml_trusted_ca_dir', '')
    attr_service_uri = environ.get('attr_service_uri', '')
    
    client_binding = AttributeQuerySslSOAPBinding()
    client_binding.sslCACertDir = saml_trusted_ca_dir
    client_binding.clockSkewTolerance = 1 # 1 second tolerance
    
    # Make a new query object
    query = AttributeQuery()
    
    query.version = SAMLVersion(SAMLVersion.VERSION_20)
    query.id = str(uuid4())
    query.issueInstant = datetime.utcnow()
    
    query.issuer = Issuer()
    query.issuer.format = Issuer.X509_SUBJECT
    query.issuer.value = '/O=STFC/OU=SPBU/CN=test'
    
    query.subject = Subject()
    query.subject.nameID = NameID()
    query.subject.nameID.format = "urn:esg:openid"
    query.subject.nameID.value = openid
    
    # Specify what attribute to query for
    id_attr = Attribute()
    id_attr.name = "urn:esg:first:name"
    id_attr.nameFormat = "http://www.w3.org/2001/XMLSchema#string"
    
    query.attributes.append(id_attr)
    
    userid = openid
    try:
        response = client_binding.send(query, uri=attr_service_uri)
        
        assertion = next(iter(response.assertions or []), None)
        if assertion:
            statement = next(iter(assertion.attributeStatements or []), None)
            if statement:
                attribute = next(iter(statement.attributes or []), None)
                if attribute:
                    attr_value = next(iter(attribute.attributeValues or []), None)
                    if attr_value:
                        userid = attr_value.value;
        
    except (RequestResponseError, Error) as e:
        logger.error("Error processing SOAP query for {0}: {1}".format(openid, e))
    
    return userid
