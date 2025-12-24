import requests
import base64
import json
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization

# CONFIGURAÇÕES (AJUSTE CONFORME NECESSÁRIO)
BASE_URL = "http://localhost:8000"
API_KEY = "SUA_API_KEY_AQUI"
PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
SUA_CHAVE_PUBLICA_AQUI
-----END PUBLIC KEY-----"""
SERIAL_KEY = "SUA_SERIAL_KEY_AQUI"
HARDWARE_ID = "DISPOSITIVO_TESTE_01"

def test_sync():
    # 1. Preparar Payload Criptografado
    public_key = serialization.load_pem_public_key(PUBLIC_KEY_PEM.encode())
    plaintext = f"{SERIAL_KEY}:{HARDWARE_ID}".encode('utf-8')
    
    encrypted_payload = public_key.encrypt(
        plaintext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    payload_b64 = base64.b64encode(encrypted_payload).decode('utf-8')

    # 2. Dados JSON para Enviar
    json_data = {
        "user_settings": {
            "theme": "dark",
            "language": "pt-BR"
        },
        "app_state": "active",
        "last_sync": "2023-10-27T10:00:00Z"
    }

    # 3. Montar Requisição
    request_body = {
        "apiKey": API_KEY,
        "payload": payload_b64,
        "jsonData": json_data
    }

    # 4. Enviar
    print(f"Enviando para {BASE_URL}/api/v1/sync...")
    try:
        response = requests.post(f"{BASE_URL}/api/v1/sync", json=request_body)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Erro na requisição: {e}")

if __name__ == "__main__":
    print("Este script requer que o servidor esteja rodando e que as chaves/IDs sejam válidos.")
    # test_sync() # Descomente para rodar após configurar
