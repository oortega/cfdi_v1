# -*- coding: utf-8 -*-
import pprint
import datetime 
import json
import os
from cfdi.cfdi import SATcfdi, CfdiStamp
from cfdi.finkok import PACFinkok
import tempfile

PATH = os.path.abspath(os.path.dirname(__file__))
CERT_NUM = '20001000000300022815'
key_path = os.path.join("cfdi/certificados","cert_test.key")
cert_path = os.path.join("cfdi/certificados","cert_test.cer")
pem_path = os.path.join("cfdi/certificados","cert_test.pem")
path_xlst = os.path.join("cfdi/xslt","cadena_3.3_1.2.xslt")
 


#Generamos un Dic
with open('cfdi_minimo.json') as f:
    datos = json.load(f)

#generar xml
cfdi = SATcfdi(datos)
xml = cfdi.get_xml()

#sellar la factura
cfdistamp = CfdiStamp(cfdi, key_path, cert_path, pem_path,CERT_NUM)
xml = cfdistamp.get_sello_fm(xml)


#Timbrar la factura 
timbrar = PACFinkok()
result = timbrar.cfdi_stamp(xml)

if result:
    print result['xml']
else:
    print timbrar.error


