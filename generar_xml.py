# -*- coding: utf-8 -*-
import pprint
import datetime 
import json
import os
from cfdi.cfdi import SATcfdi

PATH = os.path.abspath(os.path.dirname(__file__))
CERT_NUM = '20001000000300022815'
key_path = os.path.join("cfdi/certificados","cert_test.key")
cert_path = os.path.join("cfdi/certificados","cert_test.cer")
pem_path = os.path.join("cfdi/certificados","cert_test2.pem")
path_xlst = os.path.join("cfdi/xslt","cadena_3.3_1.2.xslt")
 


#Generamos un Dic
with open('cfdi_minimo.json') as f:
    datos = json.load(f)

cfdi = SATcfdi(datos)
print cfdi.get_xml()
#print datos

#Sellamos la Factura

xml_sellado = CfdiStamp(cfdi, key_path, cert_path, pem_path)
xml_sellado = xml_sellado.get_sello()
print xml_sellado


# from lxml import etree as ET
 
# root = ET.Element('background')
# starttime = ET.SubElement(root, 'starttime', {"xd": "xd"})
# hour = ET.SubElement(starttime, 'hour')
# hour.text = '00'
# minute = ET.SubElement(starttime, 'minute', {"xd2": "xd2"})
# minute.text = '00'
# second = ET.SubElement(starttime, 'second')
# second.text = '01'

#print ET.tostring(root, pretty_print=True, xml_declaration=True)