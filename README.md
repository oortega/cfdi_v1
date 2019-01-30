#CFDI

Generar xml, sellar y timbrar. Para timbrar la factura usamos Finkok

#Se genera el sello usando M2Crypto

#antes de instalar los requirements instalar esto:
sudo apt-get install python-dev  \
     build-essential libssl-dev libffi-dev \
     libxml2-dev libxslt1-dev zlib1g-dev \
     python-pip
#Instalar dependencias
pip install -r requirements.txt

#al momento de instalar si sale el error  Error compiling '/tmp/pip-build-pt9cezfl/zeep/zeep/asyncio/transport.py actualizar pip

pip install --upgrade pip
pip uninstall zeep
pip install zeep

#Formas timbrar
python generar_xml.py #timbra usando la clase Finkok
python generar_xml2.py #Timbra usando un ejemplo proporcionado por finkok
