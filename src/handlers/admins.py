from flask import render_template, request
from flask_login import current_user as adminAcc
from .. import database_api as DBAPI
from . import utils as Utils
import json


def displayAdminPage():
    if(not adminAcc.owner):
        return 'Acesso não autorizado', 401
    userList = DBAPI.obtainUser('_ALL_')
    return render_template('users.html', users=userList, mode=request.cookies.get('mode'))


def createAdmin(requestData):
    if(not adminAcc.owner):
        return 'Acesso não autorizado', 401
    email = requestData.get('email')
    username = requestData.get('username')
    password = requestData.get('password')
    validationR = Utils.validateMultiple_Admin(username, password, email)
    if not validationR == "":
        return json.dumps({'code': "ERROR", 'message': "Alguns campos estão incorretos: \n" + str(validationR)})
    try:
        DBAPI.createUser(requestData.get('email'), requestData.get(
            'username'), requestData.get('password'))
    except Exception:
        return json.dumps({'code': "ERROR", 'message': 'O banco de dados falhou ao criar a conta de administrador - #ERRO DESCONHECIDO'})

    return json.dumps({'code': "OKAY"})


def editAdmin(adminID, requestData):
    if(not adminAcc.owner):
        return 'Acesso não autorizado', 401
    password = requestData.get('password')
    try:
        Utils.validatePassword(password)
    except Exception:
        return json.dumps({'code': "ERROR", 'message': "Alguns campos estão incorretos: \n- Senha Inválida"})
    try:
        DBAPI.changeUserPassword(adminID, requestData.get('password'))
    except Exception:
        return json.dumps({'code': "ERROR", 'message': 'O banco de dados falhou ao editar a senha da conta - #ERRO DESCONHECIDO'})
    return json.dumps({'code': "OKAY"})


def toggleAdminStatus(adminID):
    if(not adminAcc.owner):
        return 'Acesso não autorizado', 401
    try:
        DBAPI.toggleUserStatus(adminID)
    except Exception:
        return json.dumps({'code': "ERROR", 'message': 'O banco de dados falhou ao desabilitar/habilitar a conta - #ERRO DESCONHECIDO'})
    return json.dumps({'code': "OKAY"})
