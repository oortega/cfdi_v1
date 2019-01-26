# -*- coding: utf-8 -*-
import pprint
from cfdi.cfdi_xml import CFDI
from cfdi import util
import datetime 
import json
from pprint import pprint
import os
import tempfile
CERT_NUM = '20001000000300022815'
#Generamos un Dic
with open('cfdi_minimo.json') as f:
    datos = json.load(f)

#Generamos el XML
cfdi = CFDI()
doc = cfdi.get_xml(datos)
#print(xml)

'''
como generar xml en python?
usas lxml o xml?
no conviene usar una plantilla, asi como se usa en django?
para que siver adenda, complementos. cuando voy a usarlos?

como agregar atributos al xml?
'''

#Sellamos XML

PATH = os.path.abspath(os.path.dirname(__file__))

pass_key = os.path.join("cfdi/certificados","cert_test.key")
ruta_cer = os.path.join("cfdi/certificados","cert_test.cer")
path_pem = os.path.join("cfdi/certificados","cert_test2.pem")
path_xlst = os.path.join("cfdi/xslt","cadena_3.3_1.2.xslt")
 
print pass_key
print ruta_cer
#def sellar_xml(origen, ruta_cer, ruta_xslt, pass_key, cert_num):

#delete, path_pem = util.validate_pem(ruta_cer, pass_key)

file_obj, file_tmp_path = tempfile.mkstemp()
os.write(file_obj, doc)  


sello = util.get_sello(file_tmp_path, path_xlst, path_pem, ruta_cer)
print sello

xml_firmado = util.add_sello(file_tmp_path, sello, CERT_NUM, 'cfdi/certificados/')

print xml_firmado



#xml = util.add_sello(doc, sello, cert_num, ruta_cer)








#Timbramos XML



