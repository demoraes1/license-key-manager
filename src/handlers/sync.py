import os
import json
import time
from flask import request, render_template, send_from_directory, abort, jsonify
from .. import database_api as DBAPI
from ..keys import decrypt_data

SYNC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'sync')

def handleSync(requestData):
    # 1. Validar apiKey
    product = DBAPI.getProductThroughAPI(requestData.get('apiKey'))
    if not product:
        return jsonify({
            'HttpCode': '401',
            'Code': 'ERR_API_KEY',
            'Message': 'ERRO :: Chave de API inválida.'
        }), 401

    # 2. Descriptografar payload
    try:
        decryptedData = decrypt_data(requestData.get('payload'), product)
        serialKey = decryptedData[0]
        hardwareID = decryptedData[1]
    except Exception:
        return jsonify({
            'HttpCode': '401',
            'Code': 'ERR_PUB_PRIV_KEY',
            'Message': 'ERRO :: Falha na descriptografia.'
        }), 401

    # 3. Validar Licença e Registro
    keyObject = DBAPI.getKeysBySerialKey(serialKey, product.id)
    if not keyObject:
        return jsonify({
            'HttpCode': '401',
            'Code': 'ERR_SERIAL_KEY',
            'Message': 'ERRO :: Licença inválida.'
        }), 401

    registration = DBAPI.getRegistration(keyObject.id, hardwareID)
    if not registration:
        return jsonify({
            'HttpCode': '401',
            'Code': 'ERR_HWID',
            'Message': 'ERRO :: Dispositivo não registrado para esta licença.'
        }), 401

    # 4. Processar JSON recebido
    jsonData = requestData.get('jsonData')
    if not jsonData:
        return jsonify({
            'HttpCode': '400',
            'Code': 'ERR_NO_DATA',
            'Message': 'ERRO :: Nenhum dado JSON fornecido.'
        }), 400

    # 5. Salvar arquivo
    dest_path = os.path.join(SYNC_DIR, str(product.id), str(keyObject.id))
    os.makedirs(dest_path, exist_ok=True)
    
    filename = f"{int(time.time())}.json"
    file_full_path = os.path.join(dest_path, filename)
    
    with open(file_full_path, 'w', encoding='utf-8') as f:
        json.dump(jsonData, f, indent=4, ensure_ascii=False)

    return jsonify({
        'HttpCode': '200',
        'Code': 'SUCCESS',
        'Message': 'SUCESSO :: Dados sincronizados com sucesso.'
    }), 200

def displaySyncFiles():
    """Lista produtos e licenças que possuem arquivos sincronizados"""
    sync_data = []
    if os.path.exists(SYNC_DIR):
        for product_id in os.listdir(SYNC_DIR):
            prod_path = os.path.join(SYNC_DIR, product_id)
            if os.path.isdir(prod_path):
                product = DBAPI.getProductByID(product_id)
                product_name = product.name if product else f"Produto {product_id}"
                
                for license_id in os.listdir(prod_path):
                    lic_path = os.path.join(prod_path, license_id)
                    if os.path.isdir(lic_path):
                        files = [f for f in os.listdir(lic_path) if f.endswith('.json')]
                        if files:
                            sync_data.append({
                                'product_id': product_id,
                                'product_name': product_name,
                                'license_id': license_id,
                                'file_count': len(files)
                            })
    
    return render_template('sync_files.html', sync_data=sync_data, mode=request.cookies.get('mode'))

def listLicenseFiles(productid, licenseid):
    """Lista arquivos de uma licença específica"""
    lic_path = os.path.join(SYNC_DIR, str(productid), str(licenseid))
    if not os.path.exists(lic_path):
        abort(404)
    
    files = []
    for f in os.listdir(lic_path):
        if f.endswith('.json'):
            file_path = os.path.join(lic_path, f)
            files.append({
                'name': f,
                'timestamp': f.split('.')[0],
                'size': os.path.getsize(file_path)
            })
    
    # Ordenar por timestamp decrescente
    files.sort(key=lambda x: x['timestamp'], reverse=True)
    
    product = DBAPI.getProductByID(productid)
    key_data = DBAPI.getKeyData(licenseid)
    
    return render_template('sync_details.html', 
                          files=files, 
                          product=product, 
                          key=key_data, 
                          mode=request.cookies.get('mode'))

def downloadFile(productid, licenseid, filename):
    directory = os.path.join(SYNC_DIR, str(productid), str(licenseid))
    return send_from_directory(directory, filename, as_attachment=True)

def deleteFile(productid, licenseid, filename):
    file_path = os.path.join(SYNC_DIR, str(productid), str(licenseid), filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({'Code': 'SUCCESS', 'Message': 'Arquivo excluído com sucesso.'})
    return jsonify({'Code': 'ERROR', 'Message': 'Arquivo não encontrado.'}), 404
