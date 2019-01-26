# -*- coding: utf-8 -*-
import pprint
import datetime 
import json
import os
from cfdi.cfdi import SATcfdi, CfdiStamp
import tempfile

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
cfdi_xml =  cfdi.get_xml()
#print cfdi_xml
#print datos

#Sellamos la Factura

xml_instace = CfdiStamp(cfdi_xml, key_path, cert_path, pem_path, CERT_NUM)
xml_sellado = xml_instace.add_sello()
#print xml_sellado

res_file = open('sellado.xml', 'w')
res_file.write(xml_sellado)
res_file.close()


#Timbramos la factura

print type(xml_sellado)
from suds.client import Client
import base64

username = 'wisphub@gmail.com'
password = 'Wisphub@cuentas1'

#file_obj, file_tmp_path = tempfile.mkstemp()
#os.write(file_obj, xml_sellado)

# invoice_path = "invoice.xml"
invoice_path = "sellado.xml"
file = open(invoice_path, 'r')

lines = "".join(file.readlines())
xml = base64.encodestring(lines)
 

# Consuming the stamp service
url = "https://demo-facturacion.finkok.com/servicios/soap/stamp.wsdl"
client = Client(url,cache=None)
contenido = client.service.stamp(xml,username,password)
xml = contenido.xml
print contenido
# Get stamped xml

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


