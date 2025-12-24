from flask import Blueprint, render_template, request, Response
from flask_httpauth import HTTPTokenAuth
from flask_login import login_required
from . import database_api as DBAPI

from .handlers import admins as AdminHandler, customers as CustomerHandler, logs as LogHandler, products as ProductHandler, licenses as LicenseHandler, validation as ValidationHandler, sync as SyncHandler

main = Blueprint('main', __name__)
auth = HTTPTokenAuth(scheme='Bearer')


@main.route('/')
def index():
    return render_template('index.html', mode=request.cookies.get('mode'))


@main.route('/healthcheck')
def health():
    return Response(status=204)


@main.route('/tutorial')
@login_required
def tutorial():
    return render_template('tutorial.html', mode=request.cookies.get('mode'))


@main.route('/dashboard')
@login_required
def cpanel():
    activated, awaitingApproval = DBAPI.getKeyStatistics()
    successfulV, unsuccessfulV = DBAPI.queryValidationsStats()
    if(activated == 0 and awaitingApproval == 0):
        ratio = 100
    else:
        ratio = (activated / (activated + awaitingApproval)) * 100
    return render_template('cpanel.html', products=DBAPI.getProductCount(), activated=activated, awaitingApproval=awaitingApproval, ratio=round(ratio), mode=request.cookies.get('mode'), successV=successfulV, unsuccessV=unsuccessfulV)


###########################################################################
# PRODUCT HANDLING
###########################################################################
@main.route('/products')
@login_required
def products():
    return ProductHandler.displayProductList()


@main.route('/products/id/<productid>')
@login_required
def productDisplay(productid):
    return ProductHandler.displayProduct(productid)


@main.route('/products/create', methods=['POST'])
@login_required
def createProduct():
    return ProductHandler.createProduct(request.get_json())


@main.route('/products/edit', methods=['POST'])
@login_required
def editProduct():
    return ProductHandler.editProduct(request.get_json())


@main.route('/products/delete/<productid>', methods=['POST'])
@login_required
def deleteProduct(productid):
    return ProductHandler.deleteProduct(productid)


@main.route('/clearcheck/<productid>')
@login_required
def clearProductCheck(productid):
    # DEBUG ROUTE - No need to remove as it doesn't affect the state of the application.
    DBAPI.resetProductCheck(productid)
    return "DONE! Next time the product page of the indicated product is loaded, the server will check for expired keys."


###########################################################################
# CUSTOMER HANDLING
###########################################################################
@main.route('/customers')
@login_required
def customers():
    return CustomerHandler.displayCustomers()


@main.route('/customers/create', methods=['POST'])
@login_required
def createCustomer():
    return CustomerHandler.createCustomer(request.get_json())


@main.route('/customers/edit/<customerid>', methods=['POST'])
@login_required
def modifyCustomer(customerid):
    return CustomerHandler.editCustomer(customerid, request.get_json())


@main.route('/customers/delete/<customerid>', methods=['POST'])
@login_required
def deleteCustomer(customerid):
    return CustomerHandler.deleteCustomer(customerid)


###########################################################################
# LICENSE KEY HANDLING
###########################################################################
@main.route('/product/<productid>/createlicense', methods=['POST'])
@login_required
def createLicense(productid):
    return LicenseHandler.createLicense(productid, request.get_json())


@main.route('/licenses/<licenseid>')
@login_required
def licenseDisplay(licenseid):
    return LicenseHandler.displayLicense(licenseid)


@main.route('/licenses/editkeys', methods=['POST'])
@login_required
def updateKeyState():
    return LicenseHandler.changeLicenseState(request.get_json())


@main.route('/licenses/<keyid>/removedevice', methods=['POST'])
@login_required
def hardwareIDRemove(keyid):
    return LicenseHandler.unlinkHardwareDevice(keyid, request.get_json().get('hardwareID'))


@main.route('/product/<productid>/bulk-action', methods=['POST'])
@login_required
def bulkLicenseAction(productid):
    return LicenseHandler.bulkAction(productid, request.get_json())


@main.route('/product/<productid>/delete-expired', methods=['POST'])
@login_required
def deleteExpiredLicenses(productid):
    return LicenseHandler.deleteExpiredLicenses(productid)


###########################################################################
# CHANGELOG HANDLING
###########################################################################
@main.route('/logs/changes')
@login_required
def changelogs():
    return LogHandler.displayChangelog()


@main.route('/logs/changes/query')
@login_required
def getchangelog():
    return LogHandler.queryLogs(request.args.to_dict())


###########################################################################
# VALIDATION LOG HANDLING
###########################################################################
@main.route('/logs/validations')
@login_required
def validationlogs():
    return LogHandler.displayValidationLog()


@main.route('/logs/validations/query')
@login_required
def getvalidationlogs():
    return LogHandler.queryValidationLogs(request.args.to_dict())


###########################################################################
# LICENSE VALIDATION
###########################################################################
@main.route('/api/validate', methods=['POST'])
@main.route('/validate', methods=['POST'])
@main.route('/api/v1/validate', methods=['POST'])
def validate_license():
    try:
        data = request.get_json(force=True, silent=True)
        if data is None:
            # Fallback para tentar ler de form-data se JSON falhar
            if request.form:
                data = request.form.to_dict()
            
        if data is None:
            from flask import jsonify
            print("DEBUG: Nenhum dado recebido ou JSON inválido.", flush=True)
            return jsonify({
                'HttpCode': '400',
                'Code': 'ERR_INVALID_JSON',
                'Message': 'ERRO :: O corpo da requisição deve ser um JSON válido.'
            }), 400
        
        print(f"DEBUG: Dados recebidos p/ validação: {data}", flush=True)
        apiKey = data.get('apiKey')
        print(f"DEBUG: Buscando produto com API Key: '{apiKey}'", flush=True)
        
        product = DBAPI.getProductThroughAPI(apiKey)
        if product:
            print(f"DEBUG: Produto encontrado: {product.name} (ID: {product.id})", flush=True)
        else:
            print(f"DEBUG: Produto NÃO encontrado para a chave fornecida.", flush=True)
            # Listar todas as chaves do banco para comparação (Debug extremo)
            all_products = DBAPI.getProduct('_ALL_')
            print("DEBUG: Chaves disponíveis no banco:", flush=True)
            for p in all_products:
                print(f" - ID: {p.id} | Nome: {p.name} | Key: '{p.apiK}'", flush=True)

        # O handler retorna uma string JSON, então precisamos criar uma Response com o mimetype correto
        response_content = ValidationHandler.handleValidation(data)
        return Response(response_content, mimetype='application/json')
    except Exception as e:
        print(f"DEBUG: Exception in validate_license: {e}", flush=True)
        from flask import jsonify
        return jsonify({
            'HttpCode': '500',
            'Code': 'ERR_INTERNAL',
            'Message': f'ERRO INTERNO :: {str(e)}'
        }), 500


###########################################################################
# ADMINISTRATOR ACCOUNTS - HANDLING
###########################################################################
@main.route('/admins')
@login_required
def adminsDisplay():
    return AdminHandler.displayAdminPage()


@main.route('/admins/create', methods=['POST'])
@login_required
def adminCreate():
    return AdminHandler.createAdmin(request.get_json())


@main.route('/admins/<userid>/edit', methods=['POST'])
@login_required
def adminEdit(userid):
    return AdminHandler.editAdmin(userid, request.get_json())


@main.route('/admins/<userid>/togglestatus', methods=['POST'])
@login_required
def adminToggleStatus(userid):
    return AdminHandler.toggleAdminStatus(userid)



###########################################################################
# SYNC AND DATA MANAGEMENT
###########################################################################
@main.route('/api/v1/sync', methods=['POST'])
def sync_data():
    data = request.get_json(force=True, silent=True)
    if data is None:
        from flask import jsonify
        return jsonify({
            'HttpCode': '400',
            'Code': 'ERR_INVALID_JSON',
            'Message': 'ERRO :: O corpo da requisição deve ser um JSON válido.'
        }), 400
    return SyncHandler.handleSync(data)


@main.route('/sync-files')
@login_required
def sync_files():
    return SyncHandler.displaySyncFiles()


@main.route('/sync-files/<productid>/<licenseid>')
@login_required
def sync_details(productid, licenseid):
    return SyncHandler.listLicenseFiles(productid, licenseid)


@main.route('/sync-files/download/<productid>/<licenseid>/<hardwareid>/<filename>')
@login_required
def sync_download(productid, licenseid, hardwareid, filename):
    return SyncHandler.downloadFile(productid, licenseid, hardwareid, filename)


@main.route('/sync-files/delete/<productid>/<licenseid>/<hardwareid>/<filename>', methods=['POST'])
@login_required
def sync_delete(productid, licenseid, hardwareid, filename):
    return SyncHandler.deleteFile(productid, licenseid, hardwareid, filename)
