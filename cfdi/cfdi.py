#!
# -*- coding: utf-8 -*-
import os
from lxml import etree as ET
import datetime
from collections import OrderedDict
from M2Crypto import RSA
import base64
import hashlib
import os
import tempfile
import envoy
from io import StringIO, BytesIO
##ROGER

##termina
PATH = os.path.abspath(os.path.dirname(__file__))
class SATcfdi(object):
    CFDI_VERSION = 'cfdi33'
    XSI = 'http://www.w3.org/2001/XMLSchema-instance' ##????
    SAT = {
        'cfdi33': {
            'version': '3.3',
            'prefix': 'cfdi',
            'xmlns': 'http://www.sat.gob.mx/cfd/3',
            'schema': 'http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd',
        },
        'nomina12': {
            'version': '1.2',
            'prefix': 'nomina',
            'xmlns': 'http://www.sat.gob.mx/nomina12',
            'schema': 'http://www.sat.gob.mx/nomina12 http://www.sat.gob.mx/sitio_internet/cfd/nomina/nomina12.xsd',
        },
    }

    def __init__(self, data, version=CFDI_VERSION ):
        self._sat_cfdi = self.SAT[version]
        self._name_space = '{{{}}}'.format(self._sat_cfdi['xmlns'])
        self._xsi = self.XSI
        self._pre = self._sat_cfdi['prefix']
        self._cfdi_xml = None
        self.error = ''
        self._data = data


    def _now(self):
        return datetime.datetime.now().isoformat()[:19]

    def get_xml(self):
        self._comprobante()
        self._emisor()
        self._receptor()
        self._conceptos()
        self._impuestos()
        return self._to_xml()

 
    def _to_xml(self):
        self._cfdi_xml = ET.tostring(self._cfdi_xml,
            pretty_print=True, xml_declaration=True, encoding='utf-8')
        
        return self._cfdi_xml.decode('utf-8')


    def _comprobante(self):
        nsmap = {
            'cfdi': self._sat_cfdi['xmlns'],
            'xsi': self.XSI,
            #'schemaLocation': self._sat_cfdi['schema']
        }
        schema_location = ET.QName(self.XSI, 'schemaLocation')

        node_name = '{}Comprobante'.format(self._name_space)
        attrib = self._data['comprobante'] # OrderedDict(self._data['comprobante'])
        attrib[schema_location] = self._sat_cfdi['schema']

        attrib['Version'] = self._sat_cfdi['version']
        attrib['Fecha'] = self._now()

        self._cfdi_xml = ET.Element(node_name, attrib, nsmap=nsmap)
        '''
        porque schemaLocation no lo definiste en nmap si esta como xmlnsi: ya vi es un xsi

        '''
    def _emisor(self):
        self.set_sub_element(key_dic='emisor', name='Emisor')

    def _receptor(self):
        self.set_sub_element(key_dic='receptor', name='Receptor')
    def _receptor2(self):
        attrib = self._data.get("receptor")
        node_name = '{}Receptor'.format(self._name_space)
        emisor = ET.SubElement(self._cfdi_xml, node_name, attrib)
    
    def _conceptos(self):
        conceptos = self._data['conceptos']
        node_name = '{}Conceptos'.format(self._name_space)
        node_parent = ET.SubElement(self._cfdi_xml, node_name)
 
        for c in conceptos:
            #Se quita {"impurestos": {"traslados": {..}}} para que no lo tome como atributo, ya que todos los keys que no tienen dic son una atributo
            complement = c.pop('complemento', {})
            taxes = c.pop('impuestos', {})

            node_name = '{}Concepto'.format(self._name_space)
            node_child = ET.SubElement(node_parent, node_name, OrderedDict(c))

            if taxes:
                node_name = '{}Impuestos'.format(self._name_space)
                node_tax = ET.SubElement(node_child, node_name)
                if taxes.get('traslados', ''):
                    node_name = '{}Traslados'.format(self._name_space)
                    node = ET.SubElement(node_tax, node_name)
                    node_name = '{}Traslado'.format(self._name_space)
                    for t in taxes['traslados']:
                        ET.SubElement(node, node_name, OrderedDict(t))
                if taxes.get('retenciones', ''):
                    node_name = '{}Retenciones'.format(self._name_space)
                    node = ET.SubElement(node_tax, node_name)
                    node_name = '{}Retencion'.format(self._name_space)
                    for t in taxes['retenciones']:
                        ET.SubElement(node, node_name, OrderedDict(t))
    def _impuestos(self):
        node_name = '{}Impuestos'.format(self._name_space)
        taxes = self._data.get('impuestos', False)
        if not taxes:
            ET.SubElement(self._cfdi_xml, node_name)
            return

        traslados = taxes.pop('traslados', False)
        retenciones = taxes.pop('retenciones', False)
        node = ET.SubElement(self._cfdi_xml, node_name, OrderedDict(taxes))

        if traslados:
            node_name = '{}Traslados'.format(self._name_space)
            sub_node = ET.SubElement(node, node_name)
            node_name = '{}Traslado'.format(self._name_space)
            for t in traslados:
                ET.SubElement(sub_node, node_name, OrderedDict(t))

        if retenciones:
            node_name = '{}Retenciones'.format(self._name_space)
            sub_node = ET.SubElement(node, node_name)
            node_name = '{}Retencion'.format(self._name_space)
            for r in retenciones:
                ET.SubElement(sub_node, node_name, OrderedDict(r))
       
    def set_sub_element(self, key_dic, name):

        node_name = '{name_space}{name}'.format(name_space=self._name_space, name=name)
        attrib = self._data.get(key_dic)
        new_sub_element = ET.SubElement(self._cfdi_xml, node_name, attrib)

        return new_sub_element

class CfdiStamp(object):
    
    XSLT_PATH=os.path.join(PATH, "xslt","cadena_3.3_1.2.xslt")
    
    def __init__(self, cfdi_xml, key_path, cer_path, pem_path, cer_num, xslt_path=XSLT_PATH ):
        self.cfdi_xml = cfdi_xml
        self.key_path = key_path
        self.cer_path = cer_path
        self.pem_path = pem_path
        self.xslt_path = xslt_path
        self.cer_num = cer_num
        self.xml_sellado = None
    
    def _to_xml(self):
        self.xml_sellado = ET.tostring(self.xml_sellado,
            pretty_print=True, xml_declaration=True, encoding='utf-8')
        
        return self.xml_sellado.decode('utf-8')

    def cer_base64(self):
        c = envoy.run("openssl enc -base64 -in %s" % self.cer_path)
        base64_str = c.std_out
        base64_str = base64_str.replace('\n',"")
        return base64_str

    def get_sello_fm(self, cfdi):
        keys = RSA.load_key(self.pem_path)
        cert_file = open(self.cer_path, 'r')
        cert = base64.b64encode(cert_file.read())
        utf8_parser = ET.XMLParser(encoding='utf-8')
        xdoc = ET.fromstring(cfdi.encode('utf-8'), parser=utf8_parser)
        # xdoc = ET.fromstring(cfdi)

        comp = xdoc.get('Comprobante')
        xdoc.attrib['Certificado'] = cert
        xdoc.attrib['NoCertificado'] = self.cer_num

        xsl_root = ET.parse(self.XSLT_PATH)
        xsl = ET.XSLT(xsl_root)
        cadena_original = xsl(xdoc)
        digest = hashlib.new('sha256', str(cadena_original)).digest()
        sello = base64.b64encode(keys.sign(digest, "sha256"))

        comp = xdoc.get('Comprobante')
        xdoc.attrib['Sello'] = sello

        return ET.tostring(xdoc)
    ###Termina