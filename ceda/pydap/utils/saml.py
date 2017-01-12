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
                                 Subject, NameID)


def get_user_roles(environ, openid):
    '''Get the roles of a user, return a list of roles'''
    if openid:
        user_roles = _get_roles_from_openid(environ, openid)
    
        return user_roles


def _get_roles_from_openid(environ, openid):
    logger = logging.getLogger(__name__)
    query = AttributeQuery()
    
    saml_trusted_ca_dir = environ.get('saml_trusted_ca_dir', '')
    attribute_service_uri = environ.get('attribute_service_uri', '')
    
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
    
    # Specify what attributes want to query for - CEDA roles
    ceda_roles = Attribute()
    ceda_roles.name = "urn:ceda:security:authz:1.0:attr"
    ceda_roles.nameFormat = "http://www.w3.org/2001/XMLSchema#string"
    
    query.attributes.append(ceda_roles)
    
    # Prepare web service call and despatch
    request = AttributeQuerySslSOAPBinding()
    request.sslCACertDir = saml_trusted_ca_dir
    request.clockSkewTolerance = 1 # 1 second tolerance
    
    ceda_role_names = []
    try:
        response = request.send(query, uri=attribute_service_uri)
        for assertion in response.assertions:
            for statement in assertion.attributeStatements:
                for attribute in statement.attributes:
                    if attribute.name == ceda_roles.name:
                        for attr_value in attribute.attributeValues:
                            ceda_role_names.append(attr_value.value)
    except (RequestResponseError, Error) as e:
        logger.error("Error processing SOAP query for {0}: {1}".format(openid, e))
    
    return ceda_role_names
