from .. import database_api as DBAPI
from ..keys import decrypt_data
from flask import request
import json
import math
import time


def handleValidation(requestData):
    response = validate(requestData)
    generateLogContents(requestData, response)
    return json.dumps(response)


def validate(requestData):
    # STEP 1 :: Validate the existence of an API Key
    product = DBAPI.getProductThroughAPI(requestData.get('apiKey'))
    if(product is None or product == []):
        return responseMessage(401, 'ERR_API_KEY', 'ERRO :: A chave de API informada é inválida. A requisição de validação não foi processada.')
    # ##############################################################################

    # STEP 2 :: Extract the descrypted data (fail if it is invalid)
    try:
        decryptedData = decrypt_data(requestData.get('payload'), product)
    except Exception:
        return responseMessage(401, 'ERR_PUB_PRIV_KEY', 'ERRO :: A descriptografia falhou. Sua chave pode ser inválida.')

    # The data in the decryptedData section is organized as:
    # decryptedData[0] - Serial Key
    # decryptedData[1] - Hardware ID
    # ##############################################################################

    # STEP 3 :: Validate the Serial Key by matching it to an existing License object
    keyObject = DBAPI.getKeysBySerialKey(decryptedData[0], product.id)
    if(keyObject is None or keyObject == []):
        return responseMessage(401, 'ERR_SERIAL_KEY', 'ERRO :: A chave serial informada é inválida. A requisição de validação foi processada mas foi rejeitada.', decryptedData)
    # ##############################################################################

    if(DBAPI.getRegistration(keyObject.id, decryptedData[1]) is None):
        return handleNonExistingState(keyObject, decryptedData)
    else:
        return handleExistingState(keyObject, decryptedData)


def handleExistingState(keyObject, decryptedData):
    """
        Handles the situation where a device is already linked to the specified license. 
        In this situation, the method merely checks whether or not the license is still valid.
    """
    expiryType = getattr(keyObject, 'expirytype', 0)
    expiryDays = getattr(keyObject, 'expirydays', None)
    activationDate = getattr(keyObject, 'activationdate', None)
    
    if(validateExpirationDate(keyObject.expirydate, expiryType, expiryDays, activationDate)):
        return responseMessage(200, 'OKAY', 'SUCESSO :: Este dispositivo ainda está registrado e tudo está funcionando corretamente.', decryptedData, keyObject.expirydate)
    else:
        DBAPI.applyExpirationState(keyObject.id)
        return responseMessage(400, 'ERR_KEY_EXPIRED', 'ERRO :: Esta licença não é mais válida.', decryptedData, keyObject.expirydate)


def handleNonExistingState(keyObject, decryptedData):
    """
        Handles the situation where a device is not yet linked to the specified license. 
        Multiple checks are done before the license is authorized for validation.
    """

    # STEP 1 :: Validate the status of the License (if it's revoked/disabled, then interrupt the validation with an error)
    if(keyObject.status == 2):
        return responseMessage(403, 'ERR_KEY_REVOKED', 'ERRO :: A chave foi revogada. Sua requisição foi válida mas a licença está desativada até segunda ordem.', decryptedData, keyObject.expirydate)

    # STEP 2 :: Check if the License has expired. If that's the case, then the validation should be interrupted with an error.
    expiryType = getattr(keyObject, 'expirytype', 0)
    expiryDays = getattr(keyObject, 'expirydays', None)
    activationDate = getattr(keyObject, 'activationdate', None)
    
    if(not validateExpirationDate(keyObject.expirydate, expiryType, expiryDays, activationDate)):
        DBAPI.applyExpirationState(keyObject.id)
        return responseMessage(400, 'ERR_KEY_EXPIRED', 'ERRO :: Esta licença não é mais válida e não aceitará novos dispositivos.', decryptedData, keyObject.expirydate)

    # STEP 3 :: Check if the License's device list can hold more devices.
    if(keyObject.devices == keyObject.maxdevices):
        return responseMessage(400, 'ERR_KEY_DEVICES_FULL', 'ERRO :: O número máximo de dispositivos para esta chave de licença foi atingido.', decryptedData, keyObject.expirydate)

    # If all steps above go through, then we accept the validation
    DBAPI.addRegistration(keyObject.id, decryptedData[1], keyObject)
    return responseMessage(201, 'SUCCESS', 'SUCESSO :: Seu registro foi realizado com sucesso!', decryptedData, keyObject.expirydate)


# Utility Functions
def responseMessage(HTTPCode=200, ResponseCode='OKAY', Message='Tudo está funcionando corretamente (RESPOSTA PADRÃO)', decryptedData=None, expirationDate=None):
    """
        Creates a JSON string that contains all the individual components of a standard response.
    """
    if(decryptedData is None):
        decryptedData = [None, None]
    return {
        'HttpCode': str(HTTPCode),
        'Message': str(Message),
        'Code': str(ResponseCode),
        'SerialKey': decryptedData[0],
        'HardwareID': decryptedData[1],
        'ExpirationDate': int(-1) if expirationDate is None else int(expirationDate)
    }


def generateLogContents(requestData, responseMsg):
    # ################################################# SET-UP DATABASE FIELDS
    result = 'ERROR' if ('ERR' in responseMsg['Code']) else 'SUCCESS'
    code = str(responseMsg['Code'])
    apiKey = str(requestData.get('apiKey'))
    serialKey = str(str(responseMsg['SerialKey']))
    hardwareID = str(responseMsg['HardwareID'])
    ipaddress = str(request.access_route[-1])
    # ########################################################################
    DBAPI.submitValidationLog(result, code, ipaddress,
                              apiKey, serialKey, hardwareID)


# MERELY AUXILIARY FUNCTIONS
def validateExpirationDate(expiryDate, expiryType=0, expiryDays=None, activationDate=None):
    """
        Verifies the state of the current expiration date. 
        If the license is still valid, the method returns True. Otherwise, it returns false.
        expiryType: 0 = data fixa, 1 = dias a partir da ativação
    """
    if(expiryDate == 0):
        return True
    
    # Modelo de dias a partir da ativação
    if expiryType == 1 and expiryDays is not None:
        # Se ainda não foi ativada, não expirou
        if activationDate is None:
            return True
        # Calcular data de expiração baseada na ativação
        calculatedExpiry = activationDate + (expiryDays * 86400)
        if(math.floor(time.time()) > int(calculatedExpiry)):
            return False
        return True
    
    # Modelo de data fixa (comportamento original)
    if(math.floor(time.time()) > int(expiryDate)):
        return False
    return True
