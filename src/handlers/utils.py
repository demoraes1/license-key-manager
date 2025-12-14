from flask import render_template, request
from .. import database_api as DBAPI
import re
from time import time
from datetime import datetime
from binascii import unhexlify
from cryptography.hazmat.primitives import serialization
from base64 import standard_b64encode


def validateMultiple_Customer(name, email, phoneNumber):
    sequence = [(validateName, name), (validateEmail, email),
                (validatePhone, phoneNumber)]
    return validateSequence(sequence)


def validateMultiple_Admin(username, password, email):
    sequence = [(validateUsername, username),
                (validatePassword, password), (validateEmail, email)]
    return validateSequence(sequence)


def validateMultiple_License(clientID, maxDevices, expiryDate):
    sequence = [(validateClientID, clientID), (validateMaxDevices,
                                               maxDevices), (validateExpiryDate, expiryDate)]
    return validateSequence(sequence)


def validateSequence(sequence):
    messageErrors = ""
    for method, parameter in sequence:
        try:
            method(parameter)
        except Exception as failure:
            messageErrors += "\n" + str(failure)
    return messageErrors


# #######################################################################################
# ############## VALIDATIONS
# #######################################################################################

def validateUsername(username):
    if(len(username) == 0 or ' ' in str(username)):
        raise Exception("- Nome de usuário inválido")


def validatePassword(password):
    if(len(password) < 10):
        raise Exception("- Senha inválida")


def validateEmail(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if(not re.fullmatch(regex, email)):
        raise Exception("- E-mail inválido")


def validatePhone(phoneNumber):
    if phoneNumber is None:
        raise Exception("- Número de telefone inválido")
    # Aceita apenas 11 dígitos contínuos (DDD + 9 números)
    phone_str = str(phoneNumber).strip()
    if not phone_str.isnumeric() or len(phone_str) != 11:
        raise Exception("- Número de telefone inválido (deve ter 11 dígitos: DDD + 9 números)")


def validateName(name):
    if(not str(name).replace(' ', '').isalpha()):
        raise Exception("- Nome inválido")


def validateClientID(clientID):
    if((not str(clientID).isnumeric()) or DBAPI.getCustomerByID(clientID) is None):
        raise Exception("- ID do Cliente inválido (deve existir)")


def validateMaxDevices(maxDevices):
    if((not str(maxDevices).isnumeric()) or int(maxDevices) <= 0):
        raise Exception("- Número Máximo de Dispositivos inválido (deve ser >= 1)")


def validateExpiryDate(expiryDate):
    dtLowerBound = (datetime.fromtimestamp(int(time()) + 86400)
                    ).replace(hour=0, minute=0, second=0, microsecond=0)
    lowerBoundTimestamp = datetime.timestamp(dtLowerBound)
    if((not expiryDate == 0) and expiryDate <= lowerBoundTimestamp):
        raise Exception("- Data inválida (deve ser depois de " +
                        dtLowerBound.strftime("%d/%m") + ", inclusive).")


# #######################################################################################
# ############## MISC
# #######################################################################################

def render404(mainMessage=None, subMessage=None):
    mainMessage = "Page not found" if mainMessage is None else mainMessage
    subMessage = "Sorry, but the page you are looking for does not exist." if subMessage is None else subMessage

    return render_template('404.html', mode=request.cookies.get('mode'), main=mainMessage, sub=subMessage), 404


def PemToXML(pubkey):
    def long_to_bytes(val, endianness='big'):
        # one (1) hex digit per four (4) bits
        width = val.bit_length()
        # unhexlify wants an even multiple of eight (8) bits, but we don't
        # want more digits than we need (hence the ternary-ish 'or')
        width += 8 - ((width % 8) or 8)
        # format width specifier: four (4) bits per hex digit
        fmt = '%%0%dx' % (width // 4)  # pylint: disable=C0209
        # prepend zero (0) to the width, to zero-pad the output
        s = unhexlify(fmt % val)
        if endianness == 'little':
            # see http://stackoverflow.com/a/931095/309233
            s = s[::-1]
        return s

    pubk = serialization.load_pem_public_key(pubkey)
    pubKxml = '<RSAKeyValue>'
    pubKxml += '<Modulus>'
    pubKxml += standard_b64encode(
        long_to_bytes(pubk.public_numbers().n)).decode('utf-8')
    pubKxml += '</Modulus>'
    pubKxml += '<Exponent>'
    pubKxml += standard_b64encode(
        long_to_bytes(pubk.public_numbers().e)).decode('utf-8')
    pubKxml += '</Exponent>'
    pubKxml += '</RSAKeyValue>'

    return pubKxml
