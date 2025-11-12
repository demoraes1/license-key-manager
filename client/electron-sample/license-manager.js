const crypto = require('crypto');
const https = require('https');
const http = require('http');

/**
 * License Manager para aplicações Electron
 * 
 * Como usar:
 * 1. Obtenha a Public Key do produto (formato PEM) do painel administrativo
 * 2. Obtenha a API Key do produto do painel administrativo
 * 3. Obtenha a Serial Key da licença criada
 * 4. Gere um Hardware ID único para o dispositivo
 */

class LicenseManager {
    constructor(publicKeyPEM, apiKey, serverUrl = 'http://localhost:5000') {
        this.publicKeyPEM = publicKeyPEM;
        this.apiKey = apiKey;
        this.serverUrl = serverUrl;
        this.endpoint = '/api/v1/validate';
    }

    /**
     * Gera um Hardware ID único baseado nas características do sistema
     * Você pode usar node-machine-id ou criar seu próprio método
     */
    async getHardwareID() {
        // Exemplo usando informações do sistema
        // Em produção, use uma biblioteca como 'node-machine-id' para um ID mais estável
        const os = require('os');
        const networkInterfaces = os.networkInterfaces();
        
        // Pega o primeiro MAC address disponível
        let macAddress = '';
        for (const interfaceName in networkInterfaces) {
            const interfaces = networkInterfaces[interfaceName];
            for (const iface of interfaces) {
                if (!iface.internal && iface.mac !== '00:00:00:00:00:00') {
                    macAddress = iface.mac;
                    break;
                }
            }
            if (macAddress) break;
        }
        
        // Combina informações do sistema para criar um ID único
        const systemInfo = `${os.platform()}_${os.arch()}_${macAddress}`;
        return systemInfo;
    }

    /**
     * Criptografa o payload usando RSA-OAEP com SHA-256
     */
    encryptPayload(serialKey, hardwareID) {
        try {
            // Formato do payload: "serialKey:hardwareID"
            const plaintext = `${serialKey}:${hardwareID}`;
            
            // Carrega a chave pública
            const publicKey = crypto.createPublicKey({
                key: this.publicKeyPEM,
                format: 'pem'
            });

            // Criptografa usando RSA-OAEP com SHA-256
            const encrypted = crypto.publicEncrypt(
                {
                    key: publicKey,
                    padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,
                    oaepHash: 'sha256'
                },
                Buffer.from(plaintext, 'utf8')
            );

            // Codifica em base64
            return encrypted.toString('base64');
        } catch (error) {
            throw new Error(`Erro ao criptografar payload: ${error.message}`);
        }
    }

    /**
     * Valida a licença no servidor
     */
    async validate(serialKey, hardwareID = null) {
        try {
            // Se não fornecido, gera um Hardware ID
            if (!hardwareID) {
                hardwareID = await this.getHardwareID();
            }

            // Criptografa o payload
            const payload = this.encryptPayload(serialKey, hardwareID);

            // Prepara a requisição
            const requestData = JSON.stringify({
                apiKey: this.apiKey,
                payload: payload
            });

            // Faz a requisição HTTP
            return new Promise((resolve, reject) => {
                const url = new URL(this.endpoint, this.serverUrl);
                const isHttps = url.protocol === 'https:';
                const client = isHttps ? https : http;

                const options = {
                    hostname: url.hostname,
                    port: url.port || (isHttps ? 443 : 80),
                    path: url.pathname,
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Content-Length': Buffer.byteLength(requestData)
                    }
                };

                const req = client.request(options, (res) => {
                    let data = '';

                    res.on('data', (chunk) => {
                        data += chunk;
                    });

                    res.on('end', () => {
                        try {
                            const response = JSON.parse(data);
                            
                            // Verifica se a validação foi bem-sucedida
                            const successCodes = ['OKAY', 'SUCCESS'];
                            const isSuccess = successCodes.includes(response.Code);

                            resolve({
                                success: isSuccess,
                                code: response.Code,
                                message: response.Message,
                                httpCode: response.HttpCode,
                                serialKey: response.SerialKey,
                                hardwareID: response.HardwareID,
                                expirationDate: response.ExpirationDate
                            });
                        } catch (error) {
                            reject(new Error(`Erro ao processar resposta: ${error.message}`));
                        }
                    });
                });

                req.on('error', (error) => {
                    reject(new Error(`Erro na requisição: ${error.message}`));
                });

                req.write(requestData);
                req.end();
            });
        } catch (error) {
            throw new Error(`Erro na validação: ${error.message}`);
        }
    }
}

module.exports = LicenseManager;

