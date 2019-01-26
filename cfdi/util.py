#!/usr/bin/env python
# -*- coding: utf-8 -*-
import base64
import chardet
import json
import os
import re
import subprocess
from collections import defaultdict
from xml.etree import ElementTree as ET
from logbook import Logger
from settings import DEBUG, PATH_XSLTPROC, PATH_OPENSSL, TYPE_TXT, NAME_CER
import tempfile

log = Logger('UTIL')


def call(args):
    return subprocess.check_output(args, shell=True).decode()


def get_home_user():
    return os.path.expanduser('~')


def join(*paths):
    return os.path.join(*paths)


def exists(path):
    return os.path.exists(path)


def is_file(path):
    return os.path.isfile(path)


def kill(path):
    try:
        os.remove(path)
    except:
        pass
    return


def validate_folder(path):
    if not DEBUG:
        return ''

    msg = ''
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except PermissionError:
            msg = 'No se pudo crear el directorio destino'
            return msg
    if not os.access(path, os.W_OK):
        msg = 'No tienes derecho de escritura en el directorio destino'
    return msg


def get_files(path, ext='xml'):
    docs = []
    for folder, _, files in os.walk(path):
        pattern = re.compile('\.{}'.format(ext), re.IGNORECASE)
        docs += [join(folder,f) for f in files if pattern.search(f)]
    return tuple(docs)


def load_data(path, format_files):
    if format_files == 'json':
        return load_json(path)

    if format_files == 'txt':
        return load_txt(path)
    return

def load_json(path):
    data = None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.loads(f.read())
    except ValueError as e:
        msg = 'load_json: {}'.format(e)
        log.error(msg)
    return data


def load_txt(path):
    if TYPE_TXT == 1:
        return load_txt_1(path)


def _complemento_pagos(data, complemento, details_pays):
    fields = ('', 'Version')
    info = complemento.pop('C00')
    data['complementos']['pagos'] = {}
    for i, f in enumerate(fields):
        if not f or not info[i]:
            continue
        data['complementos']['pagos'][f] = info[i]

    #~ Pay
    fields_pay = (
        'FechaPago',
        'FormaDePagoP',
        'MonedaP',
        'TipoCambioP',
        'Monto',
        'NumOperacion',
        'RfcEmisorCtaOrd',
        'NomBancoOrdExt',
        'CtaOrdenante',
        'RfcEmisorCtaBen',
        'CtaBeneficiario',
        'TipoCadPago',
        'CertPago',
        'CadPago',
        'SelloPago',
    )
    #~ Related
    fields_related = (
        'IdDocumento',
        'Serie',
        'Folio',
        'MonedaDR',
        'TipoCambioDR',
        'MetodoDePagoDR',
        'NumParcialidad',
        'ImpSaldoAnt',
        'ImpPagado',
        'ImpSaldoInsoluto',
    )

    pays = []
    for l in details_pays:
        if l[0] == 'C01':
            pay = {}
            for i, f in enumerate(fields_pay):
                if not l[i+1]:
                    continue
                pay[f] = l[i+1]
            pay['relacionados'] = []
            pays.append(pay)
        else:
            doc = {}
            for i, f in enumerate(fields_related):
                if not l[i+1]:
                    continue
                doc[f] = l[i+1]
            pays[-1]['relacionados'].append(doc)

    data['complementos']['pagos']['relacionados'] = pays

    # ~ info = complemento.pop('C01')

    # ~ data['complementos']['pagos']['pago'] = {}
    # ~ for i, f in enumerate(fields):
        # ~ if not info[i]:
            # ~ continue
        # ~ data['complementos']['pagos']['pago'][f] = info[i]


    # ~ data['complementos']['pagos']['relacionados'] = []
    # ~ for r in relacionados:
        # ~ doc = {}
        # ~ for i, f in enumerate(fields):
            # ~ if not r[i]:
                # ~ continue
            # ~ doc[f] = r[i]
        # ~ data['complementos']['pagos']['relacionados'].append(doc)

    return data


def load_txt_1(path):
    CODEC_WIN = 'ISO-8859-1'
    data = {
        'comprobante': {},
        'emisor': {},
        'receptor': {},
        'conceptos': [],
        'impuestos': {},
        'complementos': {},
        'relacionados': {},
    }
    conceptos = []
    conceptos2 = []
    complementos = {}
    impuestos = []
    lotes = []
    partes = []
    is_pays = False
    details_pays = []

    source = {}

    code = chardet.detect(open(path, 'rb').read())
    encoding = 'utf8'
    if code['encoding'] == CODEC_WIN:
        encoding = CODEC_WIN

    with open(path, 'r', encoding=encoding) as f:
        for line in f:
            info = line.split('|')
            if info[0] == '02' and info[2]:
                data['relacionados']['tipo'] = info[2]
                data['relacionados']['uuids'] = info[3:]
                continue

            if info[0] == '05':
                conceptos.append(info[1:])
                continue

            if info[0] == '06':
                impuestos.append(info[1:])
                continue

            if info[0] == '09':
                lotes.append(info[1:])
                continue

            if info[0] == '10':
                source[info[0]] = '|'.join(info[2:])
                continue

            if info[0] == '11':
                source[info[0]] = '|'.join(info[2:])
                continue

            if info[0] == '12':
                partes.append(info[2:])
                continue

            if info[0][0] == 'C':
                if info[1] == 'pagos':
                    complementos[info[0]] = info[1:]
                    is_pays = True
                    continue

                if is_pays:
                    details_pays.append(info)
                    continue

                if info[0] == 'C05':
                    conceptos2.append(info[1:])
                else:
                    complementos[info[0]] = info[1:]
                continue

            source[info[0]] = info[1:]


    #~ Comprobante
    fields = ('',
        'Version',
        'Serie',
        'Folio',
        'Fecha',
        'Sello',
        'FormaPago',
        'CondicionesDePago',
        'SubTotal',
        'Descuento',
        'Moneda',
        'TipoCambio',
        'Total',
        'TipoDeComprobante',
        'MetodoPago',
        'LugarExpedicion',
        'Confirmacion',
        'TotalImpuestosTrasladados',
        'TotalImpuestosRetenidos',
    )
    for i, f in enumerate(fields):
        if not f or not source['01'][i]:
            continue
        if f == 'TotalImpuestosTrasladados':
            data['impuestos'][f] = source['01'][i]
        elif f == 'TotalImpuestosRetenidos':
            data['impuestos'][f] = source['01'][i]
        else:
            data['comprobante'][f] = source['01'][i]

    #~ ToDo UUIDs relacionados

    #~ Emisor
    fields = ('',
        'Rfc',
        'Nombre',
        'RegimenFiscal',
    )
    for i, f in enumerate(fields):
        if not f or not source['03'][i]:
            continue
        data['emisor'][f] = source['03'][i]

    #~ Receptor
    fields = ('',
        'Rfc',
        'Nombre',
        'ResidenciaFiscal',
        'NumRegIdTrib',
        'UsoCFDI',
    )
    for i, f in enumerate(fields):
        if not f:
            continue
        if source['04'][i]:
            data['receptor'][f] = source['04'][i]

    #~ Conceptos
    fields = ('',
        'ClaveProdServ',
        'NoIdentificacion',
        'Cantidad',
        'ClaveUnidad',
        'Unidad',
        'Descripcion',
        'ValorUnitario',
        'Importe',
        'Descuento',
        'Complemento',
        'Pedimento',
    )
    #~ ToDo Cuenta Predial

    for c in conceptos:
        #~ print (c)
        concepto = {'complemento': {}, 'impuestos': {}}
        for i, f in enumerate(fields):
            if not f:
                continue
            if f == 'Complemento':
                continue
            if f == 'Pedimento' and c[i]:
                concepto['complemento']['NumeroPedimento'] = c[i]
                continue
            if c[i]:
                concepto[f] = c[i]

        t = c[i:]
        traslados = []
        retenciones = []

        for i in range(1, 20, 5):
            if not t[i].split():
                continue
            if i in (1, 6):
                traslados.append({
                    'Base': t[i + 0],
                    'Impuesto': t[i + 1],
                    'TipoFactor': t[i + 2],
                    'TasaOCuota': t[i + 3],
                    'Importe': t[i + 4],
                })
                tax = {
                    'Impuesto': t[i + 1],
                    'TipoFactor': t[i + 2],
                    'TasaOCuota': t[i + 3],
                }
            else:
                retenciones.append({
                    'Base': t[i + 0],
                    'Impuesto': t[i + 1],
                    'TipoFactor': t[i + 2],
                    'TasaOCuota': t[i + 3],
                    'Importe': t[i + 4],
                })

        concepto['impuestos']['traslados'] = traslados
        concepto['impuestos']['retenciones'] = retenciones
        data['conceptos'].append(concepto)

    if 'TotalImpuestosTrasladados' in data['impuestos']:
        tmp = []
        for impuesto in impuestos:
            tax = {
                'Impuesto': impuesto[1],
                'TipoFactor': impuesto[2],
                'TasaOCuota': impuesto[3],
                'Importe': impuesto[4],
            }
            tmp.append(tax)
        data['impuestos']['traslados'] = tuple(tmp)

    if 'TotalImpuestosRetenidos' in data['impuestos']:
        tax = {
            'Impuesto': source['07'][1],
            'Importe': source['07'][2],
        }
        data['impuestos']['retenciones'] = (tax,)

    if '10' in source:
        addendas = {
            'datos': source['10'],
            'lotes': lotes,
            '11': source.get('11', ''),
            'partes': partes,
        }
        data['addenda'] = json.dumps(addendas)

    if not complementos['C00'][0].strip():
        return data

    if complementos['C00'][0] == 'pagos':
        return _complemento_pagos(data, complementos, details_pays)

    #~ Complemento Comercio Exterior
    #~ Revisar Subdivision y Observaciones
    fields = ('',
        'Version',
        'MotivoTraslado',
        'TipoOperacion',
        'ClaveDePedimento',
        'CertificadoOrigen',
        'NumCertificadoOrigen',
        'NumeroExportadorConfiable',
        'Incoterm',
        'Observaciones',
        'Subdivision',
        'TipoCambioUSD',
        'TotalUSD',
    )
    info = complementos.pop('C00')
    data['complementos']['ce'] = {}
    for i, f in enumerate(fields):
        if not f or not info[i]:
            continue
        data['complementos']['ce'][f] = info[i]

    #~ CE Emisor
    fields = (
        'Curp',
        'Calle',
        'NumeroExterior',
        'NumeroInterior',
        'Colonia',
        'Localidad',
        'Referencia',
        'Municipio',
        'Estado',
        'Pais',
        'CodigoPostal',
    )
    info = complementos.pop('C01')
    data['complementos']['ce']['emisor'] = {}
    for i, f in enumerate(fields):
        if not info[i]:
            continue
        data['complementos']['ce']['emisor'][f] = info[i]

    #~ CE Propietario
    fields = (
        'NumRegIdTrib',
        'ResidenciaFiscal',
    )
    info = complementos.pop('C02')
    data['complementos']['ce']['propietario'] = {}
    for i, f in enumerate(fields):
        if not info[i]:
            continue
        data['complementos']['ce']['propietario'][f] = info[i]

    #~ CE Receptor
    fields = (
        'NumRegIdTrib',
        'Calle',
        'NumeroExterior',
        'NumeroInterior',
        'Colonia',
        'Localidad',
        'Referencia',
        'Municipio',
        'Estado',
        'Pais',
        'CodigoPostal',
    )
    info = complementos.pop('C03')
    data['complementos']['ce']['receptor'] = {}
    for i, f in enumerate(fields):
        if not info[i].strip():
            continue
        data['complementos']['ce']['receptor'][f] = info[i].strip()

    #~ CE Destinatario
    fields = (
        'NumRegIdTrib',
        'Nombre',
        'Calle',
        'NumeroExterior',
        'NumeroInterior',
        'Colonia',
        'Localidad',
        'Referencia',
        'Municipio',
        'Estado',
        'Pais',
        'CodigoPostal',
    )
    info = complementos.pop('C04')
    data['complementos']['ce']['destinatario'] = {}
    for i, f in enumerate(fields):
        # ~ print (i, f)
        value = info[i].strip()
        if not value:
            continue
        data['complementos']['ce']['destinatario'][f] = value

    #~ CE Conceptos
    fields = (
        'NoIdentificacion',
        'FraccionArancelaria',
        'CantidadAduana',
        'UnidadAduana',
        'ValorUnitarioAduana',
        'ValorDolares',
        'Marca',
        'Modelo',
        'SubModelo',
        'NumeroSerie',
    )
    data['complementos']['ce']['conceptos'] = []
    for c in conceptos2:
        concepto = {}
        for i, f in enumerate(fields):
            if not c[i]:
                continue
            concepto[f] = c[i]
        data['complementos']['ce']['conceptos'].append(concepto)
    return data


def load_cert(path):
    path_txt = join(path, NAME_CER.format('txt'))
    with open(path_txt, 'r') as f:
        data = f.read().replace('\n', '')
    return data


def get_path_info(path):
    path, filename = os.path.split(path)
    name, extension = os.path.splitext(filename)
    return path, filename, name, extension


def save_file(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        if isinstance(data, str):
            f.write(data)
        else:
            f.write(data.decode('utf-8'))
    return True


def validate_pem(path, pass_key):
    path_cer = join(path, NAME_CER.format('cer'))
    path_txt = join(path, NAME_CER.format('txt'))
    if not is_file(path_txt):
        make_cer_txt(path_cer, path_txt)

    path_pem = join(path, NAME_CER.format('key.pem'))
    if is_file(path_pem):
        return False, path_pem

    path_key = join(path, NAME_CER.format('key'))
    path_pem = make_cer_pem(path_key, pass_key)
    return True, path_pem


def make_cer_pem(path_key, pass_key):
    path, _, name, _ = get_path_info(path_key)
    path_pem = join(path, '{}.pem'.format(name))
    args = '"{}" pkcs8 -inform DER -in "{}" -out "{}" -passin pass:"{}"'.format(
        PATH_OPENSSL, path_key, path_pem, pass_key)
    try:
        call(args)
        return path_pem
    except Exception as e:
        log.error(e)
        return ''


def make_cer_txt(path_cer, path_txt):
    args = '"{}" enc -base64 -in {} | tr -d "\n" > {}'.format(
        PATH_OPENSSL, path_cer, path_txt)
    try:
        call(args)
        return True
    except Exception as e:
        log.error(e)
        return False


def get_cer_serie(path):
    path_cer = join(path, NAME_CER.format('cer'))
    print path_cer
    print "xdddddddddd"
    args = '"{}" x509 -inform DER -in {} -noout -serial'.format(
        PATH_OPENSSL, path_cer)
    try:
        serie = call(args)
        serie = serie.split('=')[1].split('\n')[0][1::2]
        return serie
    except Exception as e:
        log.error(e)
        return ''


def get_path_xlst(path_xml, folder_xslt):
    pre_cfdi = '{http://www.sat.gob.mx/cfd/3}'
    pre_nomina = '{http://www.sat.gob.mx/nomina12}'
    version_nomina = '1.2'
    try:
        tree = ET.parse(path_xml).getroot()
        version_cfdi = tree.attrib['Version']
        #~ node = tree.find('{}Complemento/{}Nomina'.format(pre_cfdi, pre_nomina))
        #~ if node is not None:
            #~ version_nomina = node.attrib['Version']
        path = folder_xslt.format(version_cfdi, version_nomina)
        if os.path.exists(path):
            return path
        else:
            log.debug(path)
            return ''
    except Exception as e:
        log.error(e)
        return ''


def _validate_num_cer(path_xml, path_cer):
    ns = get_name_space(path_xml)
    for k, v in ns.items():
        if v is None:
            v = ''
        ET.register_namespace(k, v)

    tree = ET.parse(path_xml).getroot()
    if 'NoCertificado' in tree.attrib:
        return

    tree.attrib['NoCertificado'] = get_cer_serie(path_cer)
    xml = ET.tostring(tree, encoding='utf-8')
    return save_file(path_xml, xml)


def get_sello(path_xml, path_xslt, path_pem, path_cer):
    

    _validate_num_cer(path_xml, path_cer)
    args = '"{3}" "{0}" "{1}" | "{4}" dgst -sha256 -sign "{2}" | ' \
        '"{4}" enc -base64 -A'.format(
        path_xslt, path_xml, path_pem, PATH_XSLTPROC, PATH_OPENSSL)
    #~ import OpenSSL.crypto as ct
    #~ import lxml.etree as ET
    #~ dom = ET.parse(xml_filename)
    #~ xslt = ET.parse(xsl_filename)
    #~ transform = ET.XSLT(xslt)
    #~ newdom = transform(dom)
    #~ print(ET.tostring(newdom, pretty_print=True))

    #~ args = '"{}" "{}" "{}"'.format(PATH_XSLTPROC, path_xslt, path_xml)
    #~ cadena = call(args)
    #~ with open(path_pem, 'rb') as f:
        #~ cert = ct.load_privatekey(ct.FILETYPE_PEM, f.read())
    #~ signature = ct.sign(cert, cadena, 'sha256')
    #~ sello = base64.b64encode(signature).decode()
    return call(args)


def get_name_space(file):
    events = ("start-ns",)
    ns = {}
    for event, elem in ET.iterparse(file, events):
        if event == "start-ns":
            if elem[0] in ns and ns[elem[0]] != elem[1]:
                raise KeyError("Duplicate prefix with different URI found.")
            ns[elem[0]] = elem[1]
    return ns


def _remove_addenda(root):
    addenda = ''
    node = root.find('Addenda')
    if not node is None:
        addenda = node.attrib['value']
        root.remove(node)

    return addenda


def _parse_addenda(root, xml, addenda):
    if not addenda:
        return xml

    data = json.loads(addenda)
    lotes = data.pop('lotes', [])
    partes = data.pop('partes', [])
    line11 = data.pop('11', '')
    data = data['datos'].split('|')

    if data[0] == '01':
        return _addenda_01(root, xml, data[1:], lotes)
    elif data[0] == '02':
        return _addenda_02(root, xml, data[1:], line11, partes)
    elif line11 !='||\n':
        return _addenda_sin_boveda(xml, line11, partes)

    return xml


def _addenda_sin_boveda(xml, line11, partes):
    a = """\t<!--
    <cfdi:Addenda>{}
"""
    addenda = a.format(_addenda_cliente(line11, partes))
    doc = xml.decode('utf-8')
    lines = doc.split('\n')
    lines[-1] = addenda + lines[-1].strip()
    return '\n'.join(lines)


def _partes01(partes):
    node = """\n\t\t\t<PMT:Parte posicion="{posicion}" numeroMaterial="{numero}" descripcionMaterial="{descripcion}" cantidadMaterial="{cantidad}" unidadMedida="{unidad}" precioUnitario="{precio}" montoLinea="{monto}">
                <PMT:Referencias ordenCompra="{orden_compra}"></PMT:Referencias>
            </PMT:Parte>"""
    nodes = ''
    for parte in partes:
        data = {
            'posicion': parte[0],
            'numero': parte[1],
            'descripcion': parte[2],
            'cantidad': parte[3],
            'unidad': parte[4],
            'precio': parte[5],
            'monto': parte[6],
            'orden_compra': parte[7],
        }
        nodes += node.format(**data)

    return nodes


def _partes02(partes):
    node = """\n\t\t\t<PSV:Parte posicion="{posicion}" numeroMaterial="{numero}" descripcionMaterial="{descripcion}" cantidadMaterial="{cantidad}" unidadMedida="{unidad}" precioUnitario="{precio}" montoLinea="{monto}" codigoImpuesto="{impuesto}">
                <PSV:Referencias ordenCompra="{orden_compra}" />
            </PSV:Parte>"""
    nodes = ''
    for parte in partes:
        data = {
            'posicion': parte[0],
            'numero': parte[1],
            'descripcion': parte[2],
            'cantidad': parte[3],
            'unidad': parte[4],
            'precio': parte[5],
            'monto': parte[6],
            'orden_compra': parte[7],
            'impuesto': parte[8],
        }
        nodes += node.format(**data)

    return nodes


def _partes04(partes):
    node = """\n\t\t\t<PMT:Parte posicion="{posicion}" numeroMaterial="{numero}" descripcionMaterial="{descripcion}">
                <PMT:Referencias ordenCompra="{orden_compra}" numeroASN="{numero_asn}" numeroPKN="{numero_pkn}" />
            </PMT:Parte>"""
    nodes = ''
    for parte in partes:
        data = {
            'posicion': parte[0],
            'numero': parte[1],
            'descripcion': parte[2],
            'orden_compra': parte[7],
            'numero_asn': parte[9],
            'numero_pkn': parte[8],

        }
        nodes += node.format(**data)

    return nodes


def _addenda_cliente(header, partes):
    header = header.split('|')
    a1 = """\n\t<PMT:Factura version="{version}" tipoDocumentoFiscal="{tipo_documento_fiscal}" tipoDocumentoVWM="{tipo_documento_vwm}" division="{division}" xmlns:PMT="http://www.vwnovedades.com/volkswagen/kanseilab/shcp/2009/Addenda/PMT">
        <PMT:Moneda tipoMoneda="{tipo_moneda}" tipoCambio="{tipo_cambio}" codigoImpuesto="{codigo_impuesto}"></PMT:Moneda>
        <PMT:Proveedor codigo="{codigo_proveedor}" nombre="{nombre_proveedor}"></PMT:Proveedor>
        <PMT:Destino codigo="{codigo_destino}"></PMT:Destino>
        <PMT:Referencias referenciaProveedor="{referencia_proveedor}" remision="{referencia_remision}"></PMT:Referencias>
        <PMT:Partes>{partes}
        </PMT:Partes>
    </PMT:Factura>
    </cfdi:Addenda>
    -->
"""

    a2 = """\n\t<PSV:Factura version="{version}" tipoDocumentoFiscal="{tipo_documento_fiscal}" tipoDocumentoVWM="{tipo_documento_vwm}" division="{division}" xmlns:PSV="http://www.vwnovedades.com/volkswagen/kanseilab/shcp/2009/Addenda/PSV">
        <PSV:Moneda tipoMoneda="{tipo_moneda}" tipoCambio="{tipo_cambio}" codigoImpuesto="{codigo_impuesto}"/>
        <PSV:Proveedor codigo="{codigo_proveedor}" nombre="{nombre_proveedor}" correoContacto="{correo_contacto}"/>
        <PSV:Origen codigo="{codigo_origen}"/>
        <PSV:Destino codigo="{codigo_destino}" naveReciboMaterial="{nave}"/>
        <PSV:Referencias referenciaProveedor="{referencia_proveedor}"/>
        <PSV:Solicitante correo="{correo_solicitante}"/>
        <PSV:Archivo datos="{archivo}" tipo="{tipo}"/>
        <PSV:Partes>{partes}
        </PSV:Partes>
    </PSV:Factura>
    </cfdi:Addenda>
    -->
"""

    a4 = """\n\t<PMT:Factura version="{version}" xmlns:PMT="http://www.sas-automative/en/locations/local-offices-and-plants/mexico/plant-puebla.html">
        <PMT:Moneda tipoMoneda="{tipo_moneda}" />
        <PMT:Proveedor codigo="{proveedor_codigo}" nombre="{proveedor_nombre}" />
        <PMT:Referencias referenciaProveedor="{proveedor_referencia}" />
        <PMT:Partes>{partes}
        </PMT:Partes>
    </PMT:Factura>
    </cfdi:Addenda>
    -->
"""

    if header[1] == '1':
        data = {
            'version': header[3],
            'tipo_documento_fiscal': header[4],
            'tipo_documento_vwm': header[5],
            'division': header[6],
            'tipo_moneda': header[7],
            'tipo_cambio': header[8],
            'codigo_impuesto': header[9],
            'codigo_proveedor': header[10],
            'nombre_proveedor': header[11],
            'codigo_destino': header[14],
            'referencia_proveedor': header[16],
            'referencia_remision': header[18],
            'partes': _partes01(partes),
        }
        return a1.format(**data)

    if header[1] == '2':
        data = {
            'version': header[3],
            'tipo_documento_fiscal': header[4],
            'tipo_documento_vwm': header[5],
            'division': header[6],
            'tipo_moneda': header[7],
            'tipo_cambio': header[8],
            'codigo_impuesto': header[9],
            'codigo_proveedor': header[10],
            'nombre_proveedor': header[11],
            'correo_contacto': header[12],
            'codigo_origen': header[13],
            'codigo_destino': header[14],
            'nave': header[15],
            'referencia_proveedor': header[16],
            'correo_solicitante': header[17],
            'archivo': header[20],
            'tipo': 'ZIP',
            'partes': _partes02(partes),
        }
        return a2.format(**data)

    if header[1] == '4':
        data = {
            'version': header[3],
            'tipo_moneda': header[7],
            'proveedor_codigo': header[10],
            'proveedor_nombre': header[11],
            'proveedor_referencia': header[16],
            'partes': _partes04(partes),
        }
        return a4.format(**data)

    ac = """
    </cfdi:Addenda>
    -->
"""
    return ac


def _addenda_02(root, xml, data, line11, partes):
    boveda = """\t<!--
    <cfdi:Addenda>
    <bovadd:BOVEDAFISCAL xsi:schemaLocation="http://kontender.mx/namespace/boveda http://kontender.mx/namespace/boveda/BOVEDAFISCAL.xsd http://kontender.mx/namespace http://kontender.mx/namespace/AddendaK.xsd" xmlns:bovadd="http://kontender.mx/namespace/boveda" xmlns:kon="http://kontender.mx/namespace">
{{}}
    </bovadd:BOVEDAFISCAL>{}
"""
    ac = """
    </cfdi:Addenda>
    -->
"""
    if line11:
        ac = _addenda_cliente(line11, partes)

    boveda = boveda.format(ac)

    doc = xml.decode('utf-8')
    fields = (
        'Razon_Social_destino',
        'Calle_Destino',
        'Colonia_Destino',
        'Ciudad_Destino',
        'Estado_Destino',
        'Pais_Destino',
        'CP_Destino_consigan',
        'RFC_Destino_consigna',
        'Telefono_Receptor',
        'Peso_Bruto',
        'Peso_Neto',
        'Incoterm',
        'leyenda_pie',
        'R.vto',
        'TIPO_CAMBIO_FACTURA',
        'R.cte',
        'RI_Solicitante',
        'R.fefa',
        'Razon_Social_facturado',
        'Calle_facturado',
        'Colonia_facturado',
        'RFC_destino',
        'Telefono_facturado',
        'NUMCTAPAGO',
    )
    node = ''
    for i, f in enumerate(fields):
        node += ' ' * 8 + '<bovadd:{0}>{1}</bovadd:{0}>\n'.format(f, data[i])

    addenda = boveda.format(node[:-1])

    lines = doc.split('\n')
    lines[-1] = addenda + lines[-1].strip()

    return '\n'.join(lines)


def _addenda_01(root, xml, data, lotes):
    boveda = """\t<!--
    <cfdi:Addenda>
    <bovadd:BOVEDAFISCAL xsi:schemaLocation="http://kontender.mx/namespace/boveda http://kontender.mx/namespace/boveda/BOVEDAFISCAL.xsd http://kontender.mx/namespace http://kontender.mx/namespace/AddendaK.xsd" xmlns:bovadd="http://kontender.mx/namespace/boveda" xmlns:kon="http://kontender.mx/namespace">
        <bovadd:ImporteLetra importe="{0[importe_letra]}" />
        <bovadd:UsoCFDI UsoCFDI="{0[uso_cfdi]}" />
        <bovadd:MetodosPago MetodoPagoSAT="{0[metodo_pago]}" />
        <bovadd:FormaPago FormaPagoSAT="{0[forma_pago]}" />
        <bovadd:TipoDoctoElectronico TipoDocumento="{0[tipo_documento]}" />
        <bovadd:BovedaFiscal
            almacen="{0[almacen]}"
            condicion="{0[condicion]}"
            correoEmisor="{0[correo_emisor]}"
            correoReceptor="{0[correo_receptor]}"
            numeroCliente="{0[numero_cliente]}"
            razonSocialCliente="{0[razon_social]}"
            tipo="{0[boveda_tipo]}" />
        <bovadd:DireccionEmisor
            Calle="{0[emisor_calle]}"
            CodigoPostal="{0[emisor_cp]}"
            Colonia="{0[emisor_colonia]}"
            Estado="{0[emisor_estado]}"
            Localidad="{0[emisor_localidad]}"
            Municipio="{0[emisor_municipio]}"
            NoExterior="{0[emisor_exterior]}"
            NoInterior="{0[emisor_interior]}"
            Pais="{0[emisor_pais]}"
            Referencia="{0[emisor_referencia]}"
            Telefono="{0[emisor_telefono]}" />
        <bovadd:DireccionSucursal
            Calle="{0[sucursal_calle]}"
            Ciudad="{0[sucursal_ciudad]}"
            CodigoPostal="{0[sucursal_cp]}"
            Colonia="{0[sucursal_colonia]}"
            Estado="{0[sucursal_estado]}"
            Localidad="{0[sucursal_localidad]}"
            Municipio="{0[sucursal_municipio]}"
            NoExterior="{0[sucursal_exterior]}"
            NoInterior="{0[sucursal_interior]}"
            Pais="{0[sucursal_pais]}"
            Referencia="{0[sucursal_referencia]}" />
        <bovadd:DireccionReceptor
            Calle="{0[receptor_calle]}"
            Ciudad="{0[receptor_ciudad]}"
            CodigoPostal="{0[receptor_cp]}"
            Colonia="{0[receptor_colonia]}"
            Delegacion="{0[receptor_delegacion]}"
            Estado="{0[receptor_estado]}"
            Localidad="{0[receptor_localidad]}"
            Municipio="{0[receptor_municipio]}"
            NoExterior="{0[receptor_exterior]}"
            NoInterior="{0[receptor_interior]}"
            Pais="{0[receptor_pais]}"
            Referencia="{0[receptor_referencia]}" />
        <bovadd:DireccionReceptorSucursal
            Nombre="{0[receptor_sucursal_nombre]}"
            Calle="{0[receptor_sucursal_calle]}"
            Ciudad="{0[receptor_sucursal_ciudad]}"
            CodigoPostal="{0[receptor_sucursal_cp]}"
            Estado="{0[receptor_sucursal_estado]}"
            Pais="{0[receptor_sucursal_pais]}"
            Comentario="{0[receptor_sucursal_comentario]}"
            Dato01="{0[receptor_dato01]}"
            Dato02="{0[receptor_dato02]}"
            Dato03="{0[receptor_dato03]}"
            Dato04="{0[receptor_dato04]}"
            Dato05="{0[receptor_dato05]}"
            Dato06="{0[receptor_dato06]}"
            Dato07="{0[receptor_dato07]}"
            Dato08="{0[receptor_dato08]}"
            Dato09="{0[receptor_dato09]}"
            Dato10="{0[receptor_dato10]}" />
        {0[lotes]}
        <bovadd:NombreComercial Nombre="{0[nombre_comercial]}" />
        <bovadd:ClaveTipoFolio clave="{0[tipo_folio]}" />
        <bovadd:TR transaccion="{0[transaccion]}" />
        <bovadd:OrdenCompra folio="{0[orden_compra]}" />
        <bovadd:NotaDeVenta folio="{0[nota_venta]}" />
    </bovadd:BOVEDAFISCAL>
    </cfdi:Addenda>
    -->
"""
    doc = xml.decode('utf-8')
    fields = (
        'emisor_nombre',
        'emisor_calle',
        'emisor_exterior',
        'emisor_interior',
        'emisor_colonia',
        'emisor_municipio',
        'emisor_estado',
        'emisor_pais',
        'emisor_cp',
        'emisor_rfc',
        'emisor_regimen',
        'sucursal_nombre',
        'sucursal_calle',
        'sucursal_interior',
        'sucursal_exterior',
        'sucursal_colonia',
        'sucursal_municipio',
        'sucursal_estado',
        'sucursal_pais',
        'sucursal_cp',
        'sucursal_rfc',
        'receptor_nombre',
        'receptor_rfc',
        'receptor_calle',
        'receptor_exterior',
        'receptor_interior',
        'receptor_cp',
        'receptor_ciudad',
        'receptor_pais',
        'receptor_sucursal_nombre',
        'receptor_sucursal_calle',
        'receptor_sucursal_ciudad',
        'receptor_sucursal_estado',
        'receptor_sucursal_pais',
        'receptor_sucursal_cp',
        'receptor_sucursal_comentario',
        'receptor_dato01',
        'receptor_dato02',
        'receptor_dato03',
        'receptor_dato04',
        'receptor_dato05',
        'receptor_dato06',
        'receptor_dato07',
        'receptor_dato08',
        'receptor_dato09',
        'receptor_dato10',
    )
    kwargs = dict(zip(fields, data))

    values = root.attrib.copy()
    total = float(values['Total'])
    currency = values['Moneda']

    kwargs['importe_letra'] = NumLet(total, currency).letras
    kwargs['metodo_pago'] = values['MetodoPago']
    kwargs['forma_pago'] = values['FormaPago']

    node = root.find('{http://www.sat.gob.mx/cfd/3}Receptor')
    if not node is None:
        kwargs['uso_cfdi'] = node.attrib['UsoCFDI']

    fields_lotes = (
        'IVM_InvoiceID',
        'POline',
        'NoIdentificacion',
        'Lote',
        'Cantidad',
        'Fecha')
    kwargs['lotes'] = '<bovadd:Lotes />'
    if lotes:
        node = '<bovadd:Lotes>\n'
        for lote in lotes:
            node += ' ' * 12 + '<bovadd:Lote>\n'
            for i, f in enumerate(fields_lotes):
                node += ' ' * 16 + '<bovadd:{0}>{1}</bovadd:{0}>\n'.format(f, lote[i])
            node += ' ' * 12 + '</bovadd:Lote>\n'
        node += '        </bovadd:Lotes>'
        kwargs['lotes'] = node

    addenda = boveda.format(defaultdict(str, kwargs))

    lines = doc.split('\n')
    lines[-1] = addenda + lines[-1].strip()

    return '\n'.join(lines)


def add_sello(path_xml, sello, cert_num, path_cer):
    ns = get_name_space(path_xml)
    for k, v in ns.items():
        if v is None:
            v = ''
        ET.register_namespace(k, v)

    if not DEBUG:
        cert_num = get_cer_serie(path_cer)

    tree = ET.parse(path_xml).getroot()

    tree.attrib['Sello'] = sello
    if not 'NoCertificado' in tree.attrib:
        tree.attrib['NoCertificado'] = cert_num
    if not 'Certificado' in tree.attrib:
        tree.attrib['Certificado'] = load_cert(path_cer)

    # ~ En revisión [0]
    tree.attrib['ABorrarxsi:schemaLocation'] = tree.attrib.pop(
        '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation')
    del tree.attrib['Version']

    addenda = _remove_addenda(tree)
    xml = ET.tostring(tree, encoding='utf-8')
    xml = _parse_addenda(tree, xml, addenda)

    # ~ En revisión [0]
    if isinstance(xml, str):
        xml = xml.replace('ABorrar', '')
        if 'ComercioExterior' in xml or 'Pagos' in xml:
            xml = xml.replace(' Certificado="', ' Version="3.3" Certificado="')
        else:
            xml = xml.replace(' Certificado="',
                ' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" Version="3.3" Certificado="')
    else:
        xml = xml.replace(b'ABorrar', b'')
        if b'ComercioExterior' in xml or b'Pagos' in xml:
            xml = xml.replace(b' Certificado="', b' Version="3.3" Certificado="')
        else:
            xml = xml.replace(b' Certificado="',
                b' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" Version="3.3" Certificado="')

    #return save_file(path_xml, xml)
    return xml


class NumLet(object):

    def __init__(self, value, moneda, **args):
        self._letras = self._letters(value, moneda)

    @property
    def letras(self):
        return self._letras.upper()

    def _letters(self, numero, moneda='peso'):
        texto_inicial = '-('
        texto_final = '/100 m.n.)-'
        fraccion_letras = False
        fraccion = ''

        enletras = texto_inicial
        numero = abs(numero)
        numtmp = '%015d' % numero

        if numero < 1:
            enletras += 'cero ' + self._plural(moneda) + ' '
        else:
            enletras += self._numlet(numero)
            if numero == 1 or numero < 2:
                enletras += moneda + ' '
            elif int(''.join(numtmp[3:])) == 0 or int(''.join(numtmp[9:])) == 0:
                enletras += 'de ' + self._plural(moneda) + ' '
            else:
                enletras += self._plural(moneda) + ' '

        decimal = '%0.2f' % numero
        decimal = decimal.split('.')[1]
        if fraccion_letras:
            if decimal == 0:
                enletras += 'con cero ' + self._plural(fraccion)
            elif decimal == 1:
                enletras += 'con un ' + fraccion
            else:
                enletras += 'con ' + self._numlet(int(decimal)) + self.plural(fraccion)
        else:
            enletras += decimal

        enletras += texto_final

        return enletras

    def _numlet(self, numero):
        numtmp = '%015d' % numero
        co1=0
        letras = ''
        leyenda = ''
        for co1 in range(0,5):
            inicio = co1*3
            cen = int(numtmp[inicio:inicio+1][0])
            dec = int(numtmp[inicio+1:inicio+2][0])
            uni = int(numtmp[inicio+2:inicio+3][0])
            letra3 = self.centena(uni, dec, cen)
            letra2 = self.decena(uni, dec)
            letra1 = self.unidad(uni, dec)

            if co1 == 0:
                if (cen+dec+uni) == 1:
                    leyenda = 'billon '
                elif (cen+dec+uni) > 1:
                    leyenda = 'billones '
            elif co1 == 1:
                if (cen+dec+uni) >= 1 and int(''.join(numtmp[6:9])) == 0:
                    leyenda = "mil millones "
                elif (cen+dec+uni) >= 1:
                    leyenda = "mil "
            elif co1 == 2:
                if (cen+dec) == 0 and uni == 1:
                    leyenda = 'millon '
                elif cen > 0 or dec > 0 or uni > 1:
                    leyenda = 'millones '
            elif co1 == 3:
                if (cen+dec+uni) >= 1:
                    leyenda = 'mil '
            elif co1 == 4:
                if (cen+dec+uni) >= 1:
                    leyenda = ''

            letras += letra3 + letra2 + letra1 + leyenda
            letra1 = ''
            letra2 = ''
            letra3 = ''
            leyenda = ''
        return letras

    def centena(self, uni, dec, cen):
        letras = ''
        numeros = ["","","doscientos ","trescientos ","cuatrocientos ","quinientos ","seiscientos ","setecientos ","ochocientos ","novecientos "]
        if cen == 1:
            if (dec+uni) == 0:
                letras = 'cien '
            else:
                letras = 'ciento '
        elif cen >= 2 and cen <= 9:
            letras = numeros[cen]
        return letras

    def decena(self, uni, dec):
        letras = ''
        numeros = ["diez ","once ","doce ","trece ","catorce ","quince ","dieci","dieci","dieci","dieci"]
        decenas = ["","","","treinta ","cuarenta ","cincuenta ","sesenta ","setenta ","ochenta ","noventa "]
        if dec == 1:
            letras = numeros[uni]
        elif dec == 2:
            if uni == 0:
                letras = 'veinte '
            elif uni > 0:
                letras = 'veinti'
        elif dec >= 3 and dec <= 9:
            letras = decenas[dec]
        if uni > 0 and dec > 2:
            letras = letras+'y '
        return letras

    def unidad(self, uni, dec):
        letras = ''
        numeros = ["","un ","dos ","tres ","cuatro ","cinco ","seis ","siete ","ocho ","nueve "]
        if dec != 1:
            if uni > 0 and uni <= 5:
                letras = numeros[uni]
        if uni >= 6 and uni <= 9:
            letras = numeros[uni]
        return letras

    def _plural(self, palabra):
        return palabra
        #~ if re.search('[aeiou]$', palabra):
            #~ return re.sub('$', 's', palabra)
        #~ else:
            #~ return palabra + 'es'
