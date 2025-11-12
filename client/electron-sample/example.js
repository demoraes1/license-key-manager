const LicenseManager = require('./license-manager');

/**
 * Exemplo de uso do License Manager em uma aplicação Electron
 */

async function main() {
    // CONFIGURAÇÕES - Obtenha estes valores do painel administrativo
    const PUBLIC_KEY_PEM = `-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEApLdNmLay94jt4bgJBtpu
OiGLRwJC7rWwAA4NpR/vjFMbRLT+52ugnqhv0Oej1T5D3Za7hRfrMQzSeXzmuhMP
V2fEPdqgizFjydTgrvxgluaWByCfDEMEEBpihihhZnkCx9YYoz3ig8C+I9nVZ3C7
ntfRaOqTslNVfDSqAR+6DulpmISkMxkFvHkJt09NlP2iqPlzSKC5mtFJjbLKt4cW
pMESNVBTFrnhqxvhxwgQ2KbH54XdBpzKhX2aYzQBNEG9toOJxBSqbG2iXKZ09n7s
uEVELXqVF+1+cEv2zaE6HFxBYuHOjcAXUXG/xLs+JKWuosozAQmUUpvx7pBPcHOr
nwIDAQAB
-----END PUBLIC KEY-----`;

    const API_KEY = '823c2011-cd0c-41db-a7c9-0906ec42e7aa'; // Substitua pela API Key do seu produto
    const SERIAL_KEY = 'A2UV9-9HZYZ-UWFK8-SS71A'; // Substitua pela Serial Key da licença
    const SERVER_URL = 'http://localhost:5000'; // URL do servidor de licenças

    // Cria uma instância do License Manager
    const licenseManager = new LicenseManager(PUBLIC_KEY_PEM, API_KEY, SERVER_URL);

    try {
        console.log('Validando licença...');
        console.log(`Serial Key: ${SERIAL_KEY}`);
        
        // Valida a licença
        const result = await licenseManager.validate(SERIAL_KEY);

        if (result.success) {
            console.log('\n✅ Licença válida!');
            console.log(`Código: ${result.code}`);
            console.log(`Mensagem: ${result.message}`);
            console.log(`Hardware ID: ${result.hardwareID}`);
            
            if (result.expirationDate !== -1) {
                const expirationDate = new Date(result.expirationDate * 1000);
                console.log(`Data de expiração: ${expirationDate.toLocaleString()}`);
            } else {
                console.log('Licença permanente (sem expiração)');
            }
            
            // Aqui você pode permitir o acesso à aplicação
            return true;
        } else {
            console.log('\n❌ Licença inválida!');
            console.log(`Código: ${result.code}`);
            console.log(`Mensagem: ${result.message}`);
            
            // Aqui você deve bloquear o acesso à aplicação
            return false;
        }
    } catch (error) {
        console.error('\n❌ Erro ao validar licença:');
        console.error(error.message);
        return false;
    }
}

// Executa o exemplo
if (require.main === module) {
    main().then(success => {
        process.exit(success ? 0 : 1);
    });
}

module.exports = { main };

