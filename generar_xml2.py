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
 


def timbrar():
    from suds.client import Client
    import base64

    # Username and Password, assigned by FINKOK
    username = 'pruebas-finkok@correolibre.net'
    password = '5c9a88da105bff9a8c430cb713f6d35269f51674bdc5963c1501b7316366'
     
    # Read the xml file and encode it on base64
    invoice_path = "sellado.xml"
    file = open(invoice_path)
    lines = "".join(file.readlines())
    xml = base64.encodestring(lines)
     
    # Consuming the stamp service
    url = "https://demo-facturacion.finkok.com/servicios/soap/stamp.wsdl"
    client = Client(url,cache=None)
    contenido = client.service.stamp(xml,username,password)
    print contenido
    xml = contenido.xml
     
#Generamos un Dic
with open('cfdi_minimo.json') as f:
    datos = json.load(f)


#Generamos XML
cfdi = SATcfdi(datos)
xml = cfdi.get_xml()

#Sellamos la factura
cfdistamp = CfdiStamp(cfdi, key_path, cert_path, pem_path,CERT_NUM)
xml = cfdistamp.get_sello_fm(xml)

#Guardamos el xml sellado para usarlo en timbrar()
res_file = open('sellado.xml', 'w')
res_file.write(str(xml))
res_file.close()

#timbrar()

timbrar()

 