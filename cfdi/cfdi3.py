#!
# -*- coding: utf-8 -*-
from lxml import etree as ET
import datetime
from collections import OrderedDict

class SATcfdi(object):
    CFDI_VERSION = 'cfdi33'
    CERT_NUM = '20001000000300022815'
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

    def __init__(self, datos, version=CFDI_VERSION, CERT_NUM=CERT_NUM):
        self._sat_cfdi = self.SAT[version]
        self._name_space = '{{{}}}'.format(self._sat_cfdi['xmlns'])
        self._xsi = self.XSI
        self._pre = self._sat_cfdi['prefix']
        self._cfdi_xml = None
        self.error = ''
        self.CERT_NUM = CERT_NUM
        self._datos = datos

    def _now(self):
        return datetime.datetime.now().isoformat()[:19]

    def get_xml(self):
        self._comprobante()
        self._emisor()
        self._receptor()
        self._conceptos()
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
        attrib = self._datos['comprobante'] # OrderedDict(self._data['comprobante'])
        attrib[schema_location] = self._sat_cfdi['schema']
        self._cfdi_xml = ET.Element(node_name, attrib, nsmap=nsmap)
        '''
        porque schemaLocation no lo definiste en nmap si esta como xmlnsi: ya vi es un xsi

        '''
    def _emisor(self):
        self.set_sub_element(key_datos='emisor', name='Emisor')

    def _receptor(self):
        attrib = self._datos.get("receptor")
        node_name = '{}Receptor'.format(self._name_space)
        emisor = ET.SubElement(self._cfdi_xml, node_name, attrib)
    
    def _conceptos(self):
        conceptos = self._datos.get('conceptos')
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

    def set_sub_element(self, key_datos, name):
        attrib = self._datos.get(key_datos)
        node_name = '{name_space}{name}'.format(name_space=self._name_space, name=name)
        ET.SubElement(self._cfdi_xml, node_name, attrib)