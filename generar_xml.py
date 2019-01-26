# -*- coding: utf-8 -*-
import pprint
import datetime 
import json
import os
from cfdi.cfdi import SATcfdi, CfdiStamp

PATH = os.path.abspath(os.path.dirname(__file__))
CERT_NUM = '20001000000300022815'
key_path = os.path.join("cfdi/certificados","cert_test.key")
cert_path = os.path.join("cfdi/certificados","cert_test.cer")
pem_path = os.path.join("cfdi/certificados","cert_test2.pem")
path_xlst = os.path.join("cfdi/xslt","cadena_3.3_1.2.xslt")
 


#Generamos un Dic
with open('cfdi_minimo.json') as f:
    datos = json.load(f)

# cfdi = SATcfdi(datos)
# print cfdi.get_xml()
#print datos

#Sellamos la Factura

# xml_sellado = CfdiStamp(cfdi, key_path, cert_path, pem_path)
# xml_sellado = xml_sellado.get_sello()
# print xml_sellado


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


##ROGER

'''Proceso para sellar la factura partiendo de un archivo PEM '''
def timbrar():
    from suds.client import Client
    import logging
    import base64
     
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('suds.client').setLevel(logging.DEBUG)
    logging.getLogger('suds.transport').setLevel(logging.DEBUG)
    logging.getLogger('suds.xsd.schema').setLevel(logging.DEBUG)
    logging.getLogger('suds.wsdl').setLevel(logging.DEBUG)
     
    # Username and Password, assigned by FINKOK
    username = 'wisphub@gmail.com'
    password = 'Wisphub@cuentas1'
     
    # Read the xml file and encode it on base64
    invoice_path = "generados/cfdi_generado.xml"
    file = open(invoice_path)
    lines = "".join(file.readlines())
    xml = base64.encodestring(lines)
     
    # Consuming the stamp service
    url = "https://demo-facturacion.finkok.com/servicios/soap/stamp.wsdl"
    client = Client(url,cache=None)
    contenido = client.service.stamp(xml,username,password)
    print contenido
    xml = contenido.xml
     
    # Get stamped xml
    archivo = open("stamp.xml","w")
    archivo.write(str(xml))
    archivo.close()
     
    # Get SOAP Request
    last_request = client.last_sent()
    req_file = open('request.xml', 'w')
    req_file.write(str(last_request))
    req_file.close()
     
    # Get SOAP Response
    last_response = client.last_received()
    res_file = open('response.xml', 'w')
    res_file.write(str(last_response))
    res_file.close()

# cfdi = SATcfdi(datos)
# xml = cfdi.get_xml()
# cfdistamp = CfdiStamp(cfdi, key_path, cert_path, pem_path)
# xml = cfdistamp.get_sello_fm(xml, CERT_NUM, cert_path, pem_path)
#xmltest = xml.write("generados/cfdi_generado.xml", pretty_print=True)

timbrar()

##termina