#!
# -*- coding: utf-8 -*-
#from lxml import etree as ET
from xml.etree import ElementTree as ET
from xml.dom.minidom import parseString
import datetime


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

        return self._to_xml()

 
    def _to_xml(self):
        source = ET.tostring(self._cfdi_xml, encoding='utf-8')
        tree = parseString(source)
        xml = tree.toprettyxml(encoding='utf-8').decode('utf-8')
        return xml

    def _comprobante(self):
        attributes = {}
        attributes['xmlns:{}'.format(self._pre)] = self._sat_cfdi['xmlns']
        attributes['xmlns:xsi'] = self._xsi
        attributes['xsi:schemaLocation'] = self._sat_cfdi['schema']
        attributes.update(self._datos.get('comprobante'))
        attributes['NoCertificado'] = self.CERT_NUM        
        attributes['Version'] = self._sat_cfdi['version']
        attributes['Fecha'] = self._now()

        self._cfdi_xml = ET.Element('{}:Comprobante'.format(self._pre), attributes)
        