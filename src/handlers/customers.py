from flask import render_template, request
from flask_login import current_user
from .. import database_api as DBAPI
from . import utils as Utils
import json


def displayCustomers():
    customers = DBAPI.getCustomer('_ALL_')
    return render_template('customers.html', customers=customers, mode=request.cookies.get('mode'))


def createCustomer(requestData):
    adminAcc = current_user
    # ################# Storage Data ####################
    name = requestData.get('name')
    email = requestData.get('email')
    phone = requestData.get('phone')
    country = requestData.get('country')
    # ###################################################

    validationR = Utils.validateMultiple_Customer(name, email, phone)
    if not validationR == "":
        return json.dumps({'code': "ERROR", 'message': "Alguns campos estão incorretos: \n" + str(validationR)}), 500

    try:
        DBAPI.createCustomer(name, email, phone, country)
        DBAPI.submitLog(None, adminAcc.id, 'CreatedCustomer', '$$' +
                        str(adminAcc.name) + "$$ has registered the customer '" + str(name) + "'.")
    except Exception:
        return json.dumps({'code': "ERROR", 'message': 'O banco de dados falhou ao criar o cliente - #ERRO DESCONHECIDO'}), 500

    return json.dumps({'code': "OKAY"})


def editCustomer(customerid, requestData):
    adminAcc = current_user
    # ################# Storage Data ####################
    name = requestData.get('name')
    email = requestData.get('email')
    phone = requestData.get('phone')
    country = requestData.get('country')
    # ###################################################

    validationR = Utils.validateMultiple_Customer(name, email, phone)
    if not validationR == "":
        return json.dumps({'code': "ERROR", 'message': "Entrada incorreta: \n" + str(validationR)}), 500

    try:
        DBAPI.modifyCustomer(customerid, name, email, phone, country)
        DBAPI.submitLog(None, adminAcc.id, 'EditedCustomer', '$$' + str(adminAcc.name) +
                        "$$ has modified the data of customer '" + str(name) + "'.")
    except Exception:
        return json.dumps({'code': "ERROR", 'message': 'O banco de dados falhou ao editar os dados do cliente - #ERRO DESCONHECIDO'}), 500

    return json.dumps({'code': "OKAY"})


def deleteCustomer(customerid):
    try:
        DBAPI.deleteCustomer(customerid)
    except Exception:
        return json.dumps({'code': "ERROR", 'message': 'O banco de dados falhou ao excluir o cliente - #ERRO DESCONHECIDO'}), 500

    return json.dumps({'code': "OKAY"})
