#!/usr/bin/env python
import sys
import logbook
import os
DEBUG = True
CERT_NUM = '20001000000300022815'
RFC_TEST = 'LAN7008173R5'

#??
PASS_KEY = '12345678a'
NAME_TEST = 'cert_test.{}'



PATH_PROYECT = os.path.dirname(__file__)

#~ Directorios de trabajo dentro de FOLDER_DEFAULT
NAME_CER = 'cert_test.{}'

PATH_XSLTPROC = 'xsltproc'
PATH_OPENSSL = 'openssl'

 
DELETE_SOURCE = True


#~ El tipo de TXT que se procesa, es la forma de personalizar cada tipo de TXT
#~ que genera cada ERP
TYPE_TXT = 1

 