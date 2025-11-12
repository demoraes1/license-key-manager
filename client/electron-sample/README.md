# License Manager para Electron

Este exemplo mostra como integrar a validação de licenças do License Key Manager em uma aplicação Electron.

## Pré-requisitos

1. **Node.js** instalado (versão 12 ou superior)
2. **Chave Pública do Produto** (formato PEM) - obtida no painel administrativo
3. **API Key do Produto** - obtida no painel administrativo
4. **Serial Key da Licença** - obtida quando você cria uma licença no painel

## Instalação

Não são necessárias dependências externas - o exemplo usa apenas módulos nativos do Node.js (`crypto`, `https`, `http`).

## Como Obter as Informações Necessárias

### 1. Public Key (Chave Pública)
- Acesse o painel administrativo
- Vá em **Products** e selecione seu produto
- Copie a **Public Key** (formato PEM)

### 2. API Key
- No mesmo painel do produto, copie a **API Key**

### 3. Serial Key
- Vá em **Products** → selecione o produto → crie uma licença
- Copie a **Serial Key** gerada

## Como Usar

### Exemplo Básico

```javascript
const LicenseManager = require('./license-manager');

const licenseManager = new LicenseManager(
    PUBLIC_KEY_PEM,  // Chave pública do produto
    API_KEY,         // API Key do produto
    'http://localhost:5000'  // URL do servidor
);

// Valida a licença
const result = await licenseManager.validate('SERIAL-KEY-AQUI');

if (result.success) {
    console.log('Licença válida!');
    // Permitir acesso à aplicação
} else {
    console.log('Licença inválida:', result.message);
    // Bloquear acesso à aplicação
}
```

### Integração no Electron

```javascript
// main.js ou preload.js
const { app, BrowserWindow } = require('electron');
const LicenseManager = require('./license-manager');

let licenseManager;
let isValidLicense = false;

app.whenReady().then(async () => {
    // Valida a licença antes de criar a janela
    licenseManager = new LicenseManager(PUBLIC_KEY_PEM, API_KEY, SERVER_URL);
    
    try {
        const result = await licenseManager.validate(SERIAL_KEY);
        isValidLicense = result.success;
        
        if (!isValidLicense) {
            app.quit();
            return;
        }
    } catch (error) {
        console.error('Erro ao validar licença:', error);
        app.quit();
        return;
    }
    
    // Cria a janela principal apenas se a licença for válida
    createWindow();
});

function createWindow() {
    const win = new BrowserWindow({
        width: 800,
        height: 600
    });
    
    win.loadFile('index.html');
}
```

### Validação Periódica

Você pode validar a licença periodicamente para garantir que ela ainda está válida:

```javascript
// Validar a cada hora
setInterval(async () => {
    try {
        const result = await licenseManager.validate(SERIAL_KEY);
        if (!result.success) {
            // Licença foi revogada ou expirou
            app.quit();
        }
    } catch (error) {
        console.error('Erro na validação periódica:', error);
    }
}, 3600000); // 1 hora em milissegundos
```

## Respostas da API

### Sucesso
```json
{
    "success": true,
    "code": "SUCCESS",
    "message": "SUCCESS :: Your registration was successful!",
    "httpCode": "201",
    "serialKey": "A2UV9-9HZYZ-UWFK8-SS71A",
    "hardwareID": "CPU0_BFEBFBFF000806C3_ToBeFilledByO.E.M.",
    "expirationDate": 1735689600
}
```

### Erro
```json
{
    "success": false,
    "code": "ERR_SERIAL_KEY",
    "message": "ERROR :: The Serial Key you have entered is invalid.",
    "httpCode": "401",
    "serialKey": null,
    "hardwareID": null,
    "expirationDate": -1
}
```

## Códigos de Resposta

- `SUCCESS` - Licença registrada com sucesso (primeira vez)
- `OKAY` - Licença válida e já registrada neste dispositivo
- `ERR_API_KEY` - API Key inválida
- `ERR_SERIAL_KEY` - Serial Key inválida
- `ERR_KEY_EXPIRED` - Licença expirada
- `ERR_KEY_REVOKED` - Licença revogada
- `ERR_KEY_DEVICES_FULL` - Limite de dispositivos atingido

## Hardware ID

O Hardware ID é gerado automaticamente baseado nas características do sistema. Para um ID mais estável e único, considere usar a biblioteca `node-machine-id`:

```bash
npm install node-machine-id
```

```javascript
const machineId = require('node-machine-id');
const hardwareID = machineId.machineIdSync();
```

## Segurança

- **Nunca** exponha a chave privada no código do cliente
- Use HTTPS em produção para proteger a comunicação
- Armazene a Serial Key de forma segura (ex: criptografada)
- Valide a licença periodicamente durante a execução da aplicação

## Troubleshooting

### Erro: "Invalid public key"
- Verifique se a chave pública está no formato PEM correto
- Certifique-se de que inclui os cabeçalhos `-----BEGIN PUBLIC KEY-----` e `-----END PUBLIC KEY-----`

### Erro: "Network error"
- Verifique se o servidor está rodando
- Verifique a URL do servidor
- Verifique se há firewall bloqueando a conexão

### Erro: "ERR_API_KEY"
- Verifique se a API Key está correta
- Certifique-se de que está usando a API Key do produto correto

### Erro: "ERR_SERIAL_KEY"
- Verifique se a Serial Key está correta
- Certifique-se de que a licença foi criada para o produto correto

