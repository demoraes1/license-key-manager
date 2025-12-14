from ..keys import create_product_keys
from flask import render_template, request
from flask_login import current_user
from .. import database_api as DBAPI
from . import utils as Utils
import json


def displayProductList():
    products = DBAPI.getProduct('_ALL_')
    return render_template('products.html', products=products, mode=request.cookies.get('mode'))


def displayProduct(productID):
    if(not str(productID).isnumeric()):
        return Utils.render404("Produto não encontrado", "Desculpe, mas o produto informado é inválido ...")

    productContent = DBAPI.getProductByID(productID)
    if(productContent == None):
        return Utils.render404("Produto não encontrado", "Desculpe, mas o produto informado ainda não existe ...")

    DBAPI.updateKeyStatesFromProduct(productID)

    licenses = DBAPI.getKeys(productID)
    customers = DBAPI.getCustomer('_ALL_')
    clientcount = DBAPI.getDistinctClients(productID)

    return render_template('product.html', licenses=licenses, clients=clientcount, product=productContent, pubKey=productContent.publicK.decode('utf-8'), pubKeyXML=Utils.PemToXML(productContent.publicK), customers=customers, mode=request.cookies.get('mode'))


def createProduct(requestData):
    adminAcc = current_user

    # ################# Storage Data ####################
    name = requestData.get('name')
    category = requestData.get('category')
    image = requestData.get('image')
    details = requestData.get('details')
    # ###################################################

    product_keys = create_product_keys()
    newProduct = DBAPI.createProduct(
        name, category, image, details, product_keys[0], product_keys[1], product_keys[2])
    DBAPI.submitLog(None, adminAcc.id, 'EditedProduct', '$$' +
                    str(adminAcc.name) + '$$ created product #' + str(newProduct.id))
    return "SUCCESS"


def editProduct(requestData):
    adminAcc = current_user

    # ################# Storage Data ####################
    id = requestData.get('id')
    name = requestData.get('name')
    category = requestData.get('category')
    image = requestData.get('image')
    details = requestData.get('details')
    # ###################################################

    if(DBAPI.getProductByID(int(id)) is None):
        return Utils.render404("Produto não encontrado", "Desculpe, mas o produto informado ainda não existe ...")

    DBAPI.editProduct(int(id), name, category, image, details)
    DBAPI.submitLog(None, adminAcc.id, 'EditedProduct', '$$' +
                    str(adminAcc.name) + '$$ modified the data details of product #' + str(id))
    return "SUCCESS"


def deleteProduct(productid):
    adminAcc = current_user
    
    product = DBAPI.getProductByID(productid)
    if product is None:
        return Utils.render404("Produto não encontrado", "Desculpe, mas o produto que você indicou não existe...")
    
    try:
        productName = product.name
        DBAPI.deleteProduct(productid)
        DBAPI.submitLog(None, adminAcc.id, 'DeletedProduct', '$$' +
                        str(adminAcc.name) + '$$ excluiu o produto "' + str(productName) + '" (ID: #' + str(productid) + ')')
        return "SUCCESS"
    except Exception as e:
        return json.dumps({'code': "ERROR", 'message': f'Erro ao excluir produto: {str(e)}'}), 500