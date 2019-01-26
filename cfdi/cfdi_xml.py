#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime

from xml.etree import ElementTree as ET
from xml.dom.minidom import parseString

from logbook import Logger

from settings import DEBUG, RFC_TEST, CERT_NUM


log = Logger('XML')
CFDI_ACTUAL = 'cfdi33'
NOMINA_ACTUAL = 'nomina12'

SAT = {
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'cfdi32': {
        'version': '3.2',
        'prefix': 'cfdi',
        'xmlns': 'http://www.sat.gob.mx/cfd/3',
        'schema': 'http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv32.xsd',
    },
    'cfdi33': {
        'version': '3.3',
        'prefix': 'cfdi',
        'xmlns': 'http://www.sat.gob.mx/cfd/3',
        'schema': 'http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd',
    },
    'nomina11': {
        'version': '1.1',
        'prefix': 'nomina',
        'xmlns': 'http://www.sat.gob.mx/nomina',
        'schema': 'http://www.sat.gob.mx/nomina http://www.sat.gob.mx/sitio_internet/cfd/nomina/nomina11.xsd',
    },
    'nomina12': {
        'version': '1.2',
        'prefix': 'nomina',
        'xmlns': 'http://www.sat.gob.mx/nomina12',
        'schema': 'http://www.sat.gob.mx/nomina12 http://www.sat.gob.mx/sitio_internet/cfd/nomina/nomina12.xsd',
    },
}


class CFDI(object):

    def __init__(self, version=CFDI_ACTUAL):
        self._sat_cfdi = SAT[version]
        self._xsi = SAT['xsi']
        self._pre = self._sat_cfdi['prefix']
        self._cfdi = None
        self.error = ''

    def _now(self):
        return datetime.datetime.now().isoformat()[:19]

    def get_xml(self, datos):
        if not self._validate(datos):
            return

        self._comprobante(datos['comprobante'])
        self._relacionados(datos.get('relacionados', {}))
        self._emisor(datos['emisor'])
        self._receptor(datos['receptor'])
        self._conceptos(datos['conceptos'])

        node_tax = True
        if 'complementos' in datos and 'pagos' in datos['complementos']:
            node_tax = False
        if node_tax:
            self._impuestos(datos['impuestos'])

        if 'nomina' in datos:
            self._nomina(datos['nomina'])
        if 'complementos' in datos:
            self._complementos(datos['complementos'])
        addenda = datos.get('addenda', '')
        self._addenda(addenda)
        return self._to_pretty_xml()

    def _to_pretty_xml(self):
        source = ET.tostring(self._cfdi, encoding='utf-8')
        tree = parseString(source)
        xml = tree.toprettyxml(encoding='utf-8').decode('utf-8')
        return xml

    def _validate(self, datos):
        if 'nomina' in datos:
            return self._validate_nomina(datos)
        return True

    def _validate_nomina(self, datos):
        comprobante = datos['comprobante']

        validators = (
            ('MetodoDePago', 'NA'),
            ('TipoCambio', '1'),
            ('Moneda', 'MXN'),
            ('TipoDeComprobante', 'egreso'),
        )
        for f, v in validators:
            if f in comprobante:
                if v != comprobante[f]:
                    msg = 'El atributo: {}, debe ser: {}'.format(f, v)
                    self.error = msg
                    return False
        return True

    def _comprobante(self, datos):
        attributes = {}
        attributes['xmlns:{}'.format(self._pre)] = self._sat_cfdi['xmlns']
        attributes['xmlns:xsi'] = self._xsi
        attributes['xsi:schemaLocation'] = self._sat_cfdi['schema']
        attributes.update(datos)

        if DEBUG:
            attributes['Fecha'] = self._now()
            attributes['NoCertificado'] = CERT_NUM

        if not 'Version' in attributes:
            attributes['Version'] = self._sat_cfdi['version']
        if not 'Fecha' in attributes:
            attributes['Fecha'] = self._now()

        self._cfdi = ET.Element('{}:Comprobante'.format(self._pre), attributes)
        return

    def _relacionados(self, datos):
        if not datos:
            return

        node_name = '{}:CfdiRelacionados'.format(self._pre)
        value = {'TipoRelacion': datos['tipo']}
        node = ET.SubElement(self._cfdi, node_name, value)
        for uuid in datos['uuids']:
            if not uuid.strip():
                continue
            node_name = '{}:CfdiRelacionado'.format(self._pre)
            value = {'UUID': uuid}
            ET.SubElement(node, node_name, value)
        return

    def _emisor(self, datos):
        if DEBUG:
            datos['Rfc'] = RFC_TEST

        node_name = '{}:Emisor'.format(self._pre)
        emisor = ET.SubElement(self._cfdi, node_name, datos)
        return

    def _receptor(self, datos):
        node_name = '{}:Receptor'.format(self._pre)
        emisor = ET.SubElement(self._cfdi, node_name, datos)
        return

    def _conceptos(self, datos):
        conceptos = ET.SubElement(self._cfdi, '{}:Conceptos'.format(self._pre))
        for row in datos:
            complemento = {}
            if 'complemento' in row:
                complemento = row.pop('complemento')

            taxes = {}
            if 'impuestos' in row:
                taxes = row.pop('impuestos')
            node_name = '{}:Concepto'.format(self._pre)
            concepto = ET.SubElement(conceptos, node_name, row)

            if taxes['traslados'] or taxes['retenciones']:
                node_name = '{}:Impuestos'.format(self._pre)
                impuestos = ET.SubElement(concepto, node_name)
                if 'traslados' in taxes and taxes['traslados']:
                    node_name = '{}:Traslados'.format(self._pre)
                    traslados = ET.SubElement(impuestos, node_name)
                    for traslado in taxes['traslados']:
                        ET.SubElement(
                            traslados, '{}:Traslado'.format(self._pre), traslado)
                if 'retenciones' in taxes and taxes['retenciones']:
                    node_name = '{}:Retenciones'.format(self._pre)
                    retenciones = ET.SubElement(impuestos, node_name)
                    for retencion in taxes['retenciones']:
                        ET.SubElement(
                            retenciones, '{}:Retencion'.format(self._pre), retencion)

            if 'InformacionAduanera' in row:
                for field in fields:
                    if field in row['InformacionAduanera']:
                        attributes[field] = row['InformacionAduanera'][field]
                if attributes:
                    node_name = '{}:InformacionAduanera'.format(self._pre)
                    ET.SubElement(concepto, node_name, attributes)

            if 'CuentaPredial' in row:
                attributes = {'numero': row['CuentaPredial']}
                node_name = '{}:CuentaPredial'.format(self._pre)
                ET.SubElement(concepto, node_name, attributes)

            if 'autRVOE' in row:
                fields = (
                    'version',
                    'nombreAlumno',
                    'CURP',
                    'nivelEducativo',
                    'autRVOE',
                )
                for field in fields:
                    if field in row['autRVOE']:
                        attributes[field] = row['autRVOE'][field]
                node_name = '{}:ComplementoConcepto'.format(self._pre)
                complemento = ET.SubElement(concepto, node_name)
                ET.SubElement(complemento, 'iedu:instEducativas', attributes)
        return

    def _impuestos(self, datos):
        if not datos:
            node_name = '{}:Impuestos'.format(self._pre)
            ET.SubElement(self._cfdi, node_name)
            return

        attributes = {}
        fields = ('TotalImpuestosTrasladados', 'TotalImpuestosRetenidos')
        for field in fields:
            if field in datos:
                attributes[field] = datos[field]
        node_name = '{}:Impuestos'.format(self._pre)
        impuestos = ET.SubElement(self._cfdi, node_name, attributes)

        if 'retenciones' in datos:
            retenciones = ET.SubElement(impuestos, '{}:Retenciones'.format(self._pre))
            for row in datos['retenciones']:
                ET.SubElement(retenciones, '{}:Retencion'.format(self._pre), row)

        if 'traslados' in datos:
            traslados = ET.SubElement(impuestos, '{}:Traslados'.format(self._pre))
            for row in datos['traslados']:
                ET.SubElement(traslados, '{}:Traslado'.format(self._pre), row)
        return

    def _nomina(self, datos):
        sat_nomina = SAT[NOMINA_ACTUAL]
        pre = sat_nomina['prefix']
        complemento = ET.SubElement(self._cfdi, '{}:Complemento'.format(self._pre))

        emisor = datos.pop('Emisor', None)
        receptor = datos.pop('Receptor', None)
        percepciones = datos.pop('Percepciones', None)
        deducciones = datos.pop('Deducciones', None)

        attributes = {}
        attributes['xmlns:{}'.format(pre)] = sat_nomina['xmlns']
        attributes['xsi:schemaLocation'] = sat_nomina['schema']
        attributes.update(datos)

        if not 'Version' in attributes:
            attributes['Version'] = sat_nomina['version']

        nomina = ET.SubElement(complemento, '{}:Nomina'.format(pre), attributes)
        if emisor:
            ET.SubElement(nomina, '{}:Emisor'.format(pre), emisor)
        if receptor:
            ET.SubElement(nomina, '{}:Receptor'.format(pre), receptor)
        if percepciones:
            detalle = percepciones.pop('detalle', None)
            percepciones = ET.SubElement(nomina, '{}:Percepciones'.format(pre), percepciones)
            for row in detalle:
                ET.SubElement(percepciones, '{}:Percepcion'.format(pre), row)
        if deducciones:
            detalle = deducciones.pop('detalle', None)
            deducciones = ET.SubElement(nomina, '{}:Deducciones'.format(pre), deducciones)
            for row in detalle:
                ET.SubElement(deducciones, '{}:Deduccion'.format(pre), row)
        return

    def _complementos(self, datos):
        if 'ce' in datos:
            return self._complemento_ce(datos)

        if 'pagos' in datos:
            return self._complemento_pagos(datos)

        return

    def _complemento_pagos(self, datos):
        complemento = ET.SubElement(self._cfdi, '{}:Complemento'.format(self._pre))
        pre = 'pago10'
        datos = datos.pop('pagos')
        relacionados = datos.pop('relacionados')

        attributes = {}
        attributes['xmlns:{}'.format(pre)] = \
            'http://www.sat.gob.mx/Pagos'
        attributes['xsi:schemaLocation'] = \
            'http://www.sat.gob.mx/Pagos ' \
            'http://www.sat.gob.mx/sitio_internet/cfd/Pagos/Pagos10.xsd'
        attributes.update(datos)
        pagos = ET.SubElement(
            complemento, '{}:Pagos'.format(pre), attributes)

        for pay in relacionados:
            related = pay.pop('relacionados')
            node_pay = ET.SubElement(pagos, '{}:Pago'.format(pre), pay)
            for r in related:
                ET.SubElement(node_pay, '{}:DoctoRelacionado'.format(pre), r)
        return

    def _complemento_ce(self, datos):
        complemento = ET.SubElement(self._cfdi, '{}:Complemento'.format(self._pre))
        pre = 'cce11'
        datos = datos.pop('ce')
        emisor = datos.pop('emisor')
        propietario = datos.pop('propietario')
        receptor = datos.pop('receptor')
        destinatario = datos.pop('destinatario')
        conceptos = datos.pop('conceptos')

        attributes = {}
        attributes['xmlns:{}'.format(pre)] = \
            'http://www.sat.gob.mx/ComercioExterior11'
        attributes['xsi:schemaLocation'] = \
            'http://www.sat.gob.mx/ComercioExterior11 ' \
            'http://www.sat.gob.mx/sitio_internet/cfd/ComercioExterior11/ComercioExterior11.xsd'
        attributes.update(datos)
        ce = ET.SubElement(
            complemento, '{}:ComercioExterior'.format(pre), attributes)

        attributes = {}
        if 'Curp' in emisor:
            attributes = {'Curp': emisor.pop('Curp')}
        node = ET.SubElement(ce, '{}:Emisor'.format(pre), attributes)
        ET.SubElement(node, '{}:Domicilio'.format(pre), emisor)

        if propietario:
            ET.SubElement(ce, '{}:Propietario'.format(pre), propietario)

        attributes = {}
        if 'NumRegIdTrib' in receptor:
            attributes = {'NumRegIdTrib': receptor.pop('NumRegIdTrib')}
        node = ET.SubElement(ce, '{}:Receptor'.format(pre), attributes)
        ET.SubElement(node, '{}:Domicilio'.format(pre), receptor)

        attributes = {}
        if 'NumRegIdTrib' in destinatario:
            attributes = {'NumRegIdTrib': destinatario.pop('NumRegIdTrib')}
        if 'Nombre' in destinatario:
            attributes.update({'Nombre': destinatario.pop('Nombre')})
        node = ET.SubElement(ce, '{}:Destinatario'.format(pre), attributes)
        ET.SubElement(node, '{}:Domicilio'.format(pre), destinatario)

        node = ET.SubElement(ce, '{}:Mercancias'.format(pre))
        fields = ('Marca', 'Modelo', 'SubModelo', 'NumeroSerie')
        for row in conceptos:
            detalle = {}
            for f in fields:
                if f in row:
                    detalle[f] = row.pop(f)
            concepto = ET.SubElement(node, '{}:Mercancia'.format(pre), row)
            if detalle:
                ET.SubElement(
                    concepto, '{}:DescripcionesEspecificas'.format(pre), detalle)
        return

    def _addenda(self, datos):
        if not datos:
            return

        addenda = ET.SubElement(self._cfdi, 'Addenda', {'value': datos})
        return
