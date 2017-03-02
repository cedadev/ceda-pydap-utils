'''
Created on 12 Jan 2017

@author: wat
'''

import logging

from datetime import datetime
from uuid import uuid4

from OpenSSL.SSL import Error

from ndg.saml.saml2.binding.soap.client.attributequery import \
                                                    AttributeQuerySslSOAPBinding
from ndg.saml.saml2.binding.soap.client.requestbase import RequestResponseError
from ndg.saml.saml2.core import (AttributeQuery, SAMLVersion, Attribute, Issuer,
                                 Subject, NameID, DecisionType)

from urllib2 import URLError

from ndg.saml.saml2.binding.soap.client.authzdecisionquery import \
                                            AuthzDecisionQuerySslSOAPBinding
from ndg.saml.utils.factory import AuthzDecisionQueryFactory
from ndg.soap.client import UrlLib2SOAPClientError

logger = logging.getLogger(__name__)


ATTRIBUTE_FIRST_NAME = 'urn:esg:first:name'
ATTRIBUTE_LAST_NAME = 'urn:esg:last:name'
ATTRIBUTE_EMAIL_ADDRESS = 'urn:esg:email:address'


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

def attribute_query(environ, attribute_requests, subject_id, subject_id_format='urn:esg:openid'):
    """
    Make a query for a set of attributes
    Returns a dictionary of values for each attribute in the query
    
    @param attribute_requests: SAML Attribute instances
    @param subject_id: The ID of the subject, e.g. openid
    @param subject_id_format: optional format of the ID, default is openid
    """
    
    # Grab info from the environ
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
    query.subject.nameID.format = subject_id_format
    query.subject.nameID.value = subject_id
    
    # Specify what attributes to query for
    for attribute_request in attribute_requests:
        query.attributes.append(attribute_request)
    
    try:
        response = client_binding.send(query, uri=attr_service_uri)
        attribute_results = {}
        
        assertion = next(iter(response.assertions or []), None)
        if assertion:
            statement = next(iter(assertion.attributeStatements or []), None)
            if statement:
                for attribute in statement.attributes:
                    values = []
                    for attribute_value in attribute.attributeValues:
                        values.append(attribute_value.value)
                    
                    attribute_results[attribute.name] = values
        
        return attribute_results
        
    except (RequestResponseError, Error) as e:
        logger.error("Error processing SOAP query for {0}: {1}".format(id, e))

def get_attribute_value(environ, openid, attribute):
    """
    Return a single value for an attribute
    """
    
    value = None
    result = attribute_query(environ, [attribute], openid)
    
    values = result.get(attribute.name)
    if values:
        value = next(iter(values or []), None)
    
    return value

def get_user_details(environ, openid):
    """
    Return a dictionary containing a user's
    first name, last name and email address
    """
    
    attribute_names = [
        ('first_name', ATTRIBUTE_FIRST_NAME),
        ('last_name', ATTRIBUTE_LAST_NAME),
        ('email_address', ATTRIBUTE_EMAIL_ADDRESS)
    ]
    
    attributes = []
    for _, name in attribute_names:
        attribute = Attribute()
        attribute.name = name
        attribute.nameFormat = 'http://www.w3.org/2001/XMLSchema#string'
        
        attributes.append(attribute)
    
    result = attribute_query(environ, attributes, openid)
    
    if result:
        user_details = {}
        for attribute_name in attribute_names:
            name, index = attribute_name
            values = result.get(index)
            
            value = values
            if values and len(values) == 1:
                value = values[0]
            
            user_details[name] = value
        
        return user_details
