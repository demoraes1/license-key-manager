from ..keys import generateSerialKey
from flask import render_template, request
from flask_login import current_user
from .. import database_api as DBAPI
from . import utils as Utils
import json
from time import time


def displayLicense(licenseID):
    """
        Renders the display page of the License based on the indicated 'licenseID'.
        If an error occurs in any of the rendering steps, a 404-code page will be returned, indicating that the input is invalid or that a component does not exist.
    """
    if(not str(licenseID).isnumeric()):
        return Utils.render404("License not found", "Sorry, but the license you have entered is invalid ...")

    try:
        licenseEntry = DBAPI.getKeyAndClient(licenseID)
        # Verificar expiração considerando o tipo
        expiryType = getattr(licenseEntry, 'expirytype', 0)
        expiryDays = getattr(licenseEntry, 'expirydays', None)
        activationDate = getattr(licenseEntry, 'activationdate', None)
        
        if licenseEntry.expirydate != 0 and licenseEntry.status != 3:
            from .validation import validateExpirationDate
            if not validateExpirationDate(licenseEntry.expirydate, expiryType, expiryDays, activationDate):
                licenseEntry = DBAPI.applyExpirationState(licenseEntry.id)
        changelog = DBAPI.getKeyLogs(licenseID)
        changelog.reverse()
        devices = DBAPI.getKeyHWIDs(licenseID)
    except Exception:
        return Utils.render404("Unknown Error", "Sorry, but there was an error acquiring the data from the database ...")

    if(licenseEntry is None):
        return Utils.render404("License not found", "Sorry, but the license you have entered does not exist ...")
    return render_template('license.html', license=licenseEntry, changelog=changelog, devices=devices, mode=request.cookies.get('mode'))


def createLicense(productID, requestData):
    """
        Creates a license for the indicated productID and validates the data sent by the request (JSON format).
        The return comes in a JSON format, made out of a 'code' field and a 'message' field. The function will always return an error as a 'code' if the productID is invalid or does not exist, if the request data is also invalid or if an error occurs while handling the Database. 
    """
    adminAcc = current_user
    if((not str(productID).isnumeric()) or DBAPI.getProductByID(productID) is None):
        return json.dumps({'code': "ERROR", 'message': "O produto indicado é inválido ou não existe."}), 500

    client = requestData.get('idclient')
    maxDevices = requestData.get('maxdevices')
    expiryDate = requestData.get('expirydate')
    expiryType = int(requestData.get('expirytype', 0))  # 0 = data fixa, 1 = dias
    expiryDays = requestData.get('expirydays', None)

    # Validação baseada no tipo de expiração
    if expiryType == 1:
        # Modelo de dias: validar dias e não data
        if expiryDays is None or not str(expiryDays).isnumeric() or int(expiryDays) <= 0:
            return json.dumps({'code': "ERROR", 'message': "Entrada incorreta: \n- Dias de Validade inválidos (deve ser >= 1)"}), 500
        expiryDays = int(expiryDays)
        expiryDate = 0  # Para modelo de dias, expirydate será calculado na ativação
    else:
        # Modelo de data fixa: validar data normalmente
        # Garantir que expiryDate seja um número válido ou 0
        if expiryDate is None:
            expiryDate = 0
        else:
            try:
                expiryDate = int(float(expiryDate))  # Converte float para int se necessário
            except (ValueError, TypeError):
                expiryDate = 0
        
        validationR = Utils.validateMultiple_License(
            client, maxDevices, expiryDate)
        if not validationR == "":
            return json.dumps({'code': "ERROR", 'message': "Entrada incorreta: \n" + str(validationR)}), 500

    try:
        serialKey = generateSerialKey(20)
        keyId = DBAPI.createKey(productID, int(
            client), serialKey, int(maxDevices), expiryDate, int(expiryType), expiryDays)
        DBAPI.submitLog(keyId, adminAcc.id, 'CreatedKey', '$$' + str(adminAcc.name) +
                        '$$ created license #' + str(keyId) + ' for product #' + str(productID))
    except Exception as exp:
        print(exp)
        return json.dumps({'code': "ERROR", 'message': "Ocorreu um erro ao armazenar a Licença no banco de dados - #ERRO DESCONHECIDO!"}), 500

    return json.dumps({'code': "OKAY"}), 200


def changeLicenseState(requestData):
    adminAcc = current_user
    licenseID = requestData.get('licenseID')
    action = requestData.get('action')
    if(not str(licenseID).isnumeric() or (action != 'SWITCHSTATE' and action != 'DELETE' and action != 'RESET')):
        return json.dumps({'code': "ERROR", 'message': "A licença e/ou a ação solicitada é inválida ..."}), 500

    licenseObject = DBAPI.getKeyData(licenseID)
    if(licenseObject is None):
        return json.dumps({'code': "ERROR", 'message': "A licença indicada não existe ..."}), 500

    try:
        if action == 'SWITCHSTATE':
            if licenseObject.status != 2:
                DBAPI.setKeyState(licenseID, 2)
                DBAPI.submitLog(licenseID, adminAcc.id, 'RevokedKey', '$$' +
                                str(adminAcc.name) + '$$ revoked license #' + str(licenseID))
            else:
                DBAPI.setKeyState(licenseID, getStatus(licenseObject.devices))
                DBAPI.submitLog(licenseID, adminAcc.id, 'ReactivatedKey', '$$' +
                                str(adminAcc.name) + '$$ reactivated license #' + str(licenseID))

        if action == 'DELETE':
            DBAPI.deleteKey(licenseID)
            DBAPI.submitLog(None, adminAcc.id, 'DeletedKey', '$$' + str(adminAcc.name) +
                            '$$ deleted the pre-existing license #' + str(licenseID))

        if action == 'RESET':
            DBAPI.resetKey(licenseID)
            DBAPI.submitLog(licenseID, adminAcc.id, 'ResetKey', '$$' +
                            str(adminAcc.name) + '$$ reset license #' + str(licenseID))
    except Exception:
        return json.dumps({'code': "ERROR", 'message': "Ocorreu um erro ao gerenciar o estado da licença - #ERRO DESCONHECIDO"}), 500

    return json.dumps({'code': "OKAY"})


def unlinkHardwareDevice(licenseID, hardwareID):
    adminAcc = current_user
    if(not str(licenseID).isnumeric()):
        return json.dumps({'code': "ERROR", 'message': "A licença informada é inválida ..."}), 500

    try:
        DBAPI.deleteRegistrationOfHWID(licenseID, hardwareID)
        print(licenseID+"-"+hardwareID)
        DBAPI.submitLog(licenseID, adminAcc.id, 'UnlinkedHWID$$$' + hardwareID, '$$' + str(
            adminAcc.name) + '$$ removed Hardware ' + str(hardwareID) + ' from license #' + str(licenseID))
    except Exception:
        return json.dumps({'code': "ERROR", 'message': "Ocorreu um erro ao gerenciar o estado da licença - #ERRO DESCONHECIDO"}), 500

    return json.dumps({'code': "OKAY"})

# Auxiliary Method


def getStatus(activeDevices):
    if(activeDevices > 0):
        return 1
    return 0


def bulkAction(productID, requestData):
    """
        Executa ações em massa nas licenças selecionadas.
        Ações suportadas: REVOKE, RESET, DELETE
    """
    adminAcc = current_user
    licenseIDs = requestData.get('licenseIDs', [])
    action = requestData.get('action')
    
    if not licenseIDs or len(licenseIDs) == 0:
        return json.dumps({'code': "ERROR", 'message': "Nenhuma licença selecionada."}), 500
    
    if action not in ['REVOKE', 'REACTIVATE', 'RESET', 'DELETE']:
        return json.dumps({'code': "ERROR", 'message': "Ação inválida."}), 500
    
    success_count = 0
    error_count = 0
    
    for licenseID in licenseIDs:
        try:
            licenseObject = DBAPI.getKeyData(licenseID)
            if licenseObject is None:
                error_count += 1
                continue
                
            if action == 'REVOKE':
                if licenseObject.status != 2 and licenseObject.status != 3:
                    DBAPI.setKeyState(licenseID, 2)
                    DBAPI.submitLog(licenseID, adminAcc.id, 'RevokedKey', '$$' +
                                    str(adminAcc.name) + '$$ revogou licença #' + str(licenseID) + ' (ação em massa)')
                    success_count += 1
                else:
                    error_count += 1

            elif action == 'REACTIVATE':
                if licenseObject.status == 2:  # Apenas reativa se estiver revogada
                    new_status = 1 if licenseObject.devices > 0 else 0
                    DBAPI.setKeyState(licenseID, new_status)
                    DBAPI.submitLog(licenseID, adminAcc.id, 'ReactivatedKey', '$$' +
                                    str(adminAcc.name) + '$$ reativou licença #' + str(licenseID) + ' (ação em massa)')
                    success_count += 1
                else:
                    error_count += 1
                    
            elif action == 'RESET':
                DBAPI.resetKey(licenseID)
                DBAPI.submitLog(licenseID, adminAcc.id, 'ResetKey', '$$' +
                                str(adminAcc.name) + '$$ resetou licença #' + str(licenseID) + ' (ação em massa)')
                success_count += 1
                
            elif action == 'DELETE':
                DBAPI.deleteKey(licenseID)
                DBAPI.submitLog(None, adminAcc.id, 'DeletedKey', '$$' + str(adminAcc.name) +
                                '$$ excluiu licença #' + str(licenseID) + ' (ação em massa)')
                success_count += 1
                
        except Exception:
            error_count += 1
    
    return json.dumps({
        'code': "OKAY",
        'success': success_count,
        'errors': error_count,
        'message': f"{success_count} licença(s) processada(s) com sucesso. {error_count} erro(s)."
    })


def deleteExpiredLicenses(productID):
    """
        Exclui todas as licenças expiradas de um produto.
    """
    adminAcc = current_user
    
    if (not str(productID).isnumeric()) or DBAPI.getProductByID(productID) is None:
        return json.dumps({'code': "ERROR", 'message': "O produto indicado é inválido ou não existe."}), 500
    
    try:
        # Buscar todas as licenças do produto
        licenses = DBAPI.getKeys(productID)
        deleted_count = 0
        
        for license in licenses:
            # Status 3 = Expirada
            if license.status == 3:
                DBAPI.deleteKey(license.id)
                DBAPI.submitLog(None, adminAcc.id, 'DeletedKey', '$$' + str(adminAcc.name) +
                                '$$ excluiu licença expirada #' + str(license.id))
                deleted_count += 1
        
        return json.dumps({
            'code': "OKAY",
            'deleted': deleted_count,
            'message': f"{deleted_count} licença(s) expirada(s) excluída(s)."
        })
        
    except Exception as exp:
        print(exp)
        return json.dumps({'code': "ERROR", 'message': "Ocorreu um erro ao excluir as licenças expiradas - #ERRO DESCONHECIDO"}), 500
