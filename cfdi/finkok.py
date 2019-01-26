# -*- coding: utf-8 -*-

import datetime
import re
from io import BytesIO
from xml.sax.saxutils import unescape

import lxml.etree as ET
from zeep import Client
from zeep.plugins import Plugin
from zeep.cache import SqliteCache
from zeep.transports import Transport
from zeep.exceptions import Fault, TransportError
from requests.exceptions import ConnectionError



TIMEOUT = 10
DEBUG_SOAP = True

FINKOK = {
    'AUTH': {
        'USER': 'pruebas-finkok@correolibre.net',
        'PASS': '5c9a88da105bff9a8c430cb713f6d35269f51674bdc5963c1501b7316366',
    },
    'RESELLER': {
        'USER': '',
        'PASS': ''
    },
    'WS': 'http://demo-facturacion.finkok.com/servicios/soap/{}.wsdl',
}



class DebugPlugin(Plugin):

    def _to_string(self, envelope):
        if DEBUG_SOAP:
            data = ET.tostring(envelope, pretty_print=True, encoding='utf-8').decode()
            print(data)
        return

    def egress(self, envelope, http_headers, operation, binding_options):
        self._to_string(envelope)
        return envelope, http_headers

    def ingress(self, envelope, http_headers, operation):
        self._to_string(envelope)
        return envelope, http_headers


class PACFinkok(object):
    URL = {
        'quick_stamp': False,
        'timbra': FINKOK['WS'].format('stamp'),
        'cancel': FINKOK['WS'].format('cancel'),
        'client': FINKOK['WS'].format('registration'),
        'util': FINKOK['WS'].format('utilities'),
    }
    CODE = {
        '200': 'Comprobante timbrado satisfactoriamente',
        '205': 'No Encontrado',
        '307': 'Comprobante timbrado previamente',
        '702': 'No se encontro el RFC del emisor',
    }

    def __init__(self):
        self.error = ''
        self._transport = Transport(cache=SqliteCache(), timeout=TIMEOUT)
        self._plugins = [DebugPlugin()]

    def _validate_result(self, result):
        ce = result.CodEstatus
        if ce:
            if self.CODE['200'] != ce:
                print('CodEstatus\n', type(ce), ce)
            return result

        if result.Incidencias:
            fault = result.Incidencias.Incidencia[0]
            cod_error = fault.CodigoError
            msg_error = fault.MensajeIncidencia
            error = 'Error: {}\n{}'.format(cod_error, msg_error)
            self.error = self.CODE.get(cod_error, error)
        return {}

    def _get_result(self, client, method, args):
        self.error = ''
        try:
            result = getattr(client.service, method)(**args)
        except Fault as e:
            self.error = str(e)
            return {}
        except TransportError as e:
            if '413' in str(e):
                self.error = '413<BR><BR><b>Documento muy grande para timbrar</b>'
            else:
                self.error = str(e)
            return {}
        except ConnectionError as e:
            msg = '502 - Error de conexión'
            self.error = msg
            return {}

        return self._validate_result(result)

    def cfdi_stamp(self, cfdi, auth={}):
        if not auth:
            auth = FINKOK['AUTH']

        method = 'timbra'
        client = Client(
            self.URL[method], transport=self._transport, plugins=self._plugins)
        args = {
            'username': auth['USER'],
            'password': auth['PASS'],
            'xml': cfdi,
        }

        result = self._get_result(client, 'stamp', args)
        if self.error:
            return {}

        data = {
            'xml': self._to_string(result.xml),
            'uuid': result.UUID,
            'fecha': result.Fecha,
        }
        return data

    # ToDo

    def client_add(self, rfc, type_user=False):
        """Agrega un nuevo cliente para timbrado.
        Se requiere cuenta de reseller para usar este método

        Args:
            rfc (str): El RFC del nuevo cliente

        Kwargs:
            type_user (bool): False == 'P' == Prepago or True == 'O' == On demand

        Returns:
            True or False

            origin PAC
                'message':
                    'Account Created successfully'
                    'Account Already exists'
                'success': True or False
        """
        auth = FINKOK['RESELLER']
        tu = {True: 'O', False: 'P'}

        method = 'client'
        client = Client(
            self.URL[method], transport=self._transport, plugins=self._plugins)

        args = {
            'reseller_username': auth['USER'],
            'reseller_password': auth['PASS'],
            'taxpayer_id': rfc,
            'type_user': tu[type_user],
            'added': datetime.datetime.now().isoformat()[:19],
        }

        try:
            self.result = client.service.add(**args)
        except Fault as e:
            self.error = str(e)
            return False
        except TransportError as e:
            self.error = str(e)
            return False
        except ConnectionError:
            self.error = 'Verifica la conexión a internet'
            return False

        if not self.result.success:
            self.error = self.result.message
            return False

        # ~ PAC success debería ser False
        msg = 'Account Already exists'
        if self.result.message == msg:
            self.error = msg
            return False

        return self.result.success

    def client_add_token(self, rfc, email):
        """Agrega un nuevo token al cliente para timbrado.
        Se requiere cuenta de reseller para usar este método

        Args:
            rfc (str): El RFC del cliente, ya debe existir
            email (str): El correo del cliente, funciona como USER al timbrar

        Returns:
            token (str)

            origin PAC
            dict
                'username': 'username',
                'status': True or False
                'name': 'name',
                'success': True or False
                'token': 'Token de timbrado',
                'message': None
        """
        auth = FINKOK['RESELLER']

        method = 'util'
        client = Client(
            self.URL[method], transport=self._transport, plugins=self._plugins)
        args = {
            'username': auth['USER'],
            'password': auth['PASS'],
            'name': rfc,
            'token_username': email,
            'taxpayer_id': rfc,
            'status': True,
        }
        try:
            self.result = client.service.add_token(**args)
        except Fault as e:
            self._debug(args)
            self.error = str(e)
            return ''
        except TransportError as e:
            self.error = str(e)
            return ''
        except ConnectionError:
            self.error = 'Verifica la conexión a internet'
            return ''

        if not self.result.success:
            self.error = self.result.message
            return ''

        return self.result.token

    def client_add_timbres(self, rfc, credit):
        """Agregar credito a un emisor

        Se requiere cuenta de reseller

        Args:
            rfc (str): El RFC del emisor, debe existir
            credit (int): Cantidad de folios a agregar

        Returns:
            dict
                'success': True or False,
                'credit': nuevo credito despues de agregar or None
                'message':
                    'Success, added {credit} of credit to {RFC}.'
                    'RFC no encontrado'
        """
        auth = FINKOK['RESELLER']

        if not isinstance(credit, int):
            self.error = 'El credito debe ser un entero'
            return 0

        method = 'client'
        client = Client(
            self.URL[method], transport=self._transport, plugins=self._plugins)
        args = {
            'username': auth['USER'],
            'password': auth['PASS'],
            'taxpayer_id': rfc,
            'credit': credit,
        }
        try:
            self.result = client.service.assign(**args)
        except Fault as e:
            self.error = str(e)
            return 0
        except TransportError as e:
            self.error = str(e)
            return 0
        except ConnectionError:
            self.error = 'Verifica la conexión a internet'
            return 0

        if not self.result.success:
            self.error = self.result.message
            return 0

        return self.result.credit

    def client_edit(self, rfc, status='A'):
        """Edita el estatus (Activo o Suspendido) de un cliente
        Se requiere cuenta de reseller para usar este método

        Args:
            rfc (str): El RFC del cliente

        Kwargs:
            status (bool): True == 'A' == Activo or False == 'S' == Suspendido

        Returns:
            dict
                'message':
                    'Account Created successfully'
                    'Account Already exists'
                'success': True or False
        """
        auth = FINKOK['RESELLER']

        method = 'client'
        client = Client(
            self.URL[method], transport=self._transport, plugins=self._plugins)

        args = {
            'reseller_username': auth['USER'],
            'reseller_password': auth['PASS'],
            'taxpayer_id': rfc,
            'status': status,
        }

        try:
            self.result = client.service.edit(**args)
        except Fault as e:
            self.error = str(e)
            return ''
        except TransportError as e:
            self.error = str(e)
            return ''
        except ConnectionError:
            self.error = 'Verifica la conexión a internet'
            return ''

        if not self.result.success:
            self.error = self.result.message
            return ''

        return status

    def client_get(self, rfc):
        """Regresa el estatus del cliente
        Se requiere cuenta de reseller para usar este método

        Args:
            rfc (str): El RFC del emisor

        Returns:
            dict
                'message': None,
                'users': {
                    'ResellerUser': [
                        {
                            'status': 'A',
                            'counter': 0,
                            'taxpayer_id': '',
                            'credit': 0
                        }
                    ]
                } or None si no existe
        """
        auth = FINKOK['RESELLER']

        method = 'client'
        client = Client(
            self.URL[method], transport=self._transport, plugins=self._plugins)

        args = {
            'reseller_username': auth['USER'],
            'reseller_password': auth['PASS'],
            'taxpayer_id': rfc,
        }

        try:
            self.result = client.service.get(**args)
        except Fault as e:
            self.error = str(e)
            return {}
        except TransportError as e:
            self.error = str(e)
            return {}
        except ConnectionError:
            self.error = 'Verifica la conexión a internet'
            return {}

        success = bool(self.result.users)
        if not success:
            self.error = self.result.message or 'RFC no existe'
            return {}

        data = self.result.users.ResellerUser[0]
        client = {
            'status': data.status,
            'counter': data.counter,
            'credit': data.credit,
        }
        return client

    def client_get_timbres(self, rfc, auth={}):
        """Regresa los timbres restantes del cliente
        Se pueden usar las credenciales de relleser o las credenciales del emisor

        Args:
            rfc (str): El RFC del emisor

        Kwargs:
            auth (dict): Credenciales del emisor

        Returns:
            int Cantidad de timbres restantes
        """

        if not auth:
            auth = FINKOK['RESELLER']

        method = 'client'
        client = Client(
            self.URL[method], transport=self._transport, plugins=self._plugins)
        args = {
            'reseller_username': auth['USER'],
            'reseller_password': auth['PASS'],
            'taxpayer_id': rfc,
        }

        try:
            self.result = client.service.get(**args)
        except Fault as e:
            self.error = str(e)
            return 0
        except TransportError as e:
            self.error = str(e)
            return 0
        except ConnectionError:
            self.error = 'Verifica la conexión a internet'
            return 0

        success = bool(self.result.users)
        if not success:
            self.error = self.result.message or 'RFC no existe'
            return 0

        return self.result.users.ResellerUser[0].credit

    def get_server_datetime(self):
        """Regresa la fecha y hora del servidor de timbrado del PAC
        """
        auth = FINKOK['RESELLER']

        method = 'util'
        client = Client(
            self.URL[method], transport=self._transport, plugins=self._plugins)
        try:
            self.result = client.service.datetime(auth['USER'], auth['PASS'])
        except Fault as e:
            self.error = str(e)
            return None
        except TransportError as e:
            self.error = str(e)
            return None
        except ConnectionError:
            self.error = 'Verifica la conexión a internet'
            return None

        try:
            dt = datetime.datetime.strptime(
                self.result.datetime, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            self.error = 'Error al obtener la fecha'
            return None

        return dt

    def get_report_credit(self, rfc):
        """Obtiene un reporte de los timbres agregados
        """
        auth = FINKOK['RESELLER']

        args = {
            'username': auth['USER'],
            'password': auth['PASS'],
            'taxpayer_id': rfc,
        }

        method = 'util'
        client = Client(
            self.URL[method], transport=self._transport, plugins=self._plugins)
        try:
            self.result = client.service.report_credit(**args)
        except Fault as e:
            self.error = str(e)
            return []
        except TransportError as e:
            self.error = str(e)
            return []
        except ConnectionError:
            self.error = 'Verifica la conexión a internet'
            return []

        if self.result.result is None:
            # ~ PAC - Debería regresar RFC inexistente o sin registros
            self.error = 'RFC no existe o no tiene registros'
            return []

        return self.result.result.ReportTotalCredit

    def get_report_total(self, rfc, date_from, date_to, invoice_type='I'):
        """Obtiene un reporte del total de facturas timbradas
        """
        auth = FINKOK['RESELLER']

        args = {
            'username': auth['USER'],
            'password': auth['PASS'],
            'taxpayer_id': rfc,
            'date_from': date_from,
            'date_to': date_to,
            'invoice_type': invoice_type,
        }

        method = 'util'
        client = Client(
            self.URL[method], transport=self._transport, plugins=self._plugins)
        try:
            self.result = client.service.report_total(**args)
        except Fault as e:
            self.error = str(e)
            return 0
        except TransportError as e:
            self.error = str(e)
            return 0
        except ConnectionError:
            self.error = 'Verifica la conexión a internet'
            return 0

        if self.result.result is None:
            # ~ PAC - Debería regresar RFC inexistente o sin registros
            self.error = 'RFC no existe o no tiene registros'
            return 0

        return self.result.result.ReportTotal[0].total or 0

    def get_report_uuid(self, rfc, date_from, date_to, invoice_type='I'):
        """Obtiene un reporte de los CFDI timbrados
        """
        auth = FINKOK['RESELLER']

        args = {
            'username': auth['USER'],
            'password': auth['PASS'],
            'taxpayer_id': rfc,
            'date_from': date_from,
            'date_to': date_to,
            'invoice_type': invoice_type,
        }

        method = 'util'
        client = Client(
            self.URL[method], transport=self._transport, plugins=self._plugins)
        try:
            self.result = client.service.report_uuid(**args)
        except Fault as e:
            self.error = str(e)
            return []
        except TransportError as e:
            self.error = str(e)
            return []
        except ConnectionError:
            self.error = 'Verifica la conexión a internet'
            return []

        if self.result.invoices is None:
            # ~ PAC - Debería regresar RFC inexistente o sin registros
            self.error = 'RFC no existe o no tiene registros'
            return []

        return self.result.invoices.ReportUUID

    def _to_string(self, data):
        root = ET.parse(BytesIO(data.encode())).getroot()
        xml = ET.tostring(root,
            pretty_print=True, xml_declaration=True, encoding='utf-8')
        return xml.decode('utf-8')

    def cfdi_get_by_xml(self, xml, auth):
        if not auth:
            auth = FINKOK['AUTH']

        method = 'timbra'
        client = Client(
            self.URL[method], transport=self._transport, plugins=self._plugins)
        args = {
            'username': auth['USER'],
            'password': auth['PASS'],
            'xml': xml,
        }

        try:
            result = client.service.stamped(**args)
        except Fault as e:
            self.error = str(e)
            return {}
        except TransportError as e:
            self.error = str(e)
            return {}
        except ConnectionError as e:
            msg = '502 - Error de conexión'
            self.error = msg
            return {}

        print(result)

        error = 'Error: {}\n{}'.format(code_error, msg_error)
        self.error = self.CODE.get(code_error, error)
        return {}

    def cfdi_get_by_uuid(self, uuid, rfc, invoice_type='I', auth={}):
        if not auth:
            auth = FINKOK['AUTH']

        method = 'util'
        client = Client(
            URL[method], transport=self._transport, plugins=self._plugins)

        args = {
            'username': auth['USER'],
            'password': auth['PASS'],
            'uuid': uuid,
            'taxpayer_id': rfc,
            'invoice_type': invoice_type,
        }
        try:
            result = client.service.get_xml(**args)
        except Fault as e:
            self.error = str(e)
            return {}
        except TransportError as e:
            self.error = str(e)
            return {}
        except ConnectionError as e:
            msg = '502 - Error de conexión'
            self.error = msg
            return {}

        print(result)

        error = 'Error: {}\n{}'.format(code_error, msg_error)
        self.error = self.CODE.get(code_error, error)
        return {}

    def cfdi_status(self, uuid, auth={}):
        if not auth:
            auth = FINKOK['AUTH']

        method = 'timbra'
        client = Client(
            self.URL[method], transport=self._transport, plugins=self._plugins)
        args = {
            'username': auth['USER'],
            'password': auth['PASS'],
            'uuid': uuid,
        }

        try:
            result = client.service.query_pending(**args)
        except Fault as e:
            self.error = str(e)
            return {}
        except TransportError as e:
            self.error = str(e)
            return {}
        except ConnectionError as e:
            msg = '502 - Error de conexión'
            self.error = msg
            return {}

        STATUS = {
            'S': 'Timbrado, aún no eviado al SAT',
            'F': 'Timbrado y enviado al SAT',
        }

        data = {
            'status': STATUS[result.status],
            'xml': self._to_string(unescape(result.xml)),
        }

        return data


