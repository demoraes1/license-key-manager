/**
 * Exemplo completo de integração com Electron
 * 
 * Este arquivo mostra como integrar a validação de licenças
 * no processo principal (main process) do Electron
 */

const { app, BrowserWindow, dialog } = require('electron');
const LicenseManager = require('./license-manager');
const path = require('path');
const fs = require('fs');

// Configurações da licença
const CONFIG_FILE = path.join(app.getPath('userData'), 'license-config.json');

class ElectronLicenseIntegration {
    constructor() {
        this.licenseManager = null;
        this.isValidLicense = false;
        this.serialKey = null;
        this.mainWindow = null;
    }

    /**
     * Carrega as configurações da licença
     */
    loadConfig() {
        try {
            if (fs.existsSync(CONFIG_FILE)) {
                const config = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
                return config;
            }
        } catch (error) {
            console.error('Erro ao carregar configurações:', error);
        }
        return null;
    }

    /**
     * Salva as configurações da licença
     */
    saveConfig(config) {
        try {
            fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
        } catch (error) {
            console.error('Erro ao salvar configurações:', error);
        }
    }

    /**
     * Solicita a Serial Key do usuário
     */
    async requestSerialKey() {
        return new Promise((resolve) => {
            // Em uma aplicação real, você criaria uma janela de diálogo
            // ou um formulário para o usuário inserir a Serial Key
            // Por enquanto, vamos usar um valor padrão ou variável de ambiente
            const serialKey = process.env.LICENSE_SERIAL_KEY || null;
            
            if (!serialKey) {
                // Exemplo: abrir uma janela de diálogo
                // dialog.showMessageBoxSync({
                //     type: 'info',
                //     message: 'Por favor, insira sua Serial Key'
                // });
                console.log('Serial Key não encontrada. Configure LICENSE_SERIAL_KEY ou implemente um diálogo.');
            }
            
            resolve(serialKey);
        });
    }

    /**
     * Valida a licença e retorna o resultado
     */
    async validateLicense(publicKey, apiKey, serverUrl, serialKey) {
        try {
            this.licenseManager = new LicenseManager(publicKey, apiKey, serverUrl);
            const result = await this.licenseManager.validate(serialKey);
            
            this.isValidLicense = result.success;
            this.serialKey = serialKey;
            
            // Salva a configuração se válida
            if (result.success) {
                this.saveConfig({
                    serialKey: serialKey,
                    publicKey: publicKey,
                    apiKey: apiKey,
                    serverUrl: serverUrl,
                    lastValidation: new Date().toISOString()
                });
            }
            
            return result;
        } catch (error) {
            console.error('Erro na validação:', error);
            return {
                success: false,
                message: error.message
            };
        }
    }

    /**
     * Cria a janela principal da aplicação
     */
    createMainWindow() {
        this.mainWindow = new BrowserWindow({
            width: 1200,
            height: 800,
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
                preload: path.join(__dirname, 'preload.js') // Se você tiver um preload script
            }
        });

        // Carrega a aplicação
        this.mainWindow.loadFile('index.html'); // ou loadURL se for uma URL

        // Validação periódica (a cada hora)
        setInterval(async () => {
            if (this.licenseManager && this.serialKey) {
                try {
                    const result = await this.licenseManager.validate(this.serialKey);
                    if (!result.success) {
                        dialog.showErrorBox(
                            'Licença Inválida',
                            `Sua licença foi revogada ou expirou: ${result.message}`
                        );
                        app.quit();
                    }
                } catch (error) {
                    console.error('Erro na validação periódica:', error);
                }
            }
        }, 3600000); // 1 hora
    }

    /**
     * Inicializa a aplicação
     */
    async initialize() {
        // Aguarda o Electron estar pronto
        await app.whenReady();

        // Carrega configurações salvas
        const config = this.loadConfig();
        
        // Configurações - em produção, estas devem vir de variáveis de ambiente ou arquivo de configuração
        const PUBLIC_KEY = process.env.LICENSE_PUBLIC_KEY || config?.publicKey || '';
        const API_KEY = process.env.LICENSE_API_KEY || config?.apiKey || '';
        const SERVER_URL = process.env.LICENSE_SERVER_URL || config?.serverUrl || 'http://localhost:5000';
        
        // Obtém a Serial Key
        let serialKey = process.env.LICENSE_SERIAL_KEY || config?.serialKey;
        
        if (!serialKey) {
            serialKey = await this.requestSerialKey();
        }

        if (!serialKey || !PUBLIC_KEY || !API_KEY) {
            dialog.showErrorBox(
                'Configuração Incompleta',
                'Por favor, configure as variáveis de ambiente:\n' +
                '- LICENSE_PUBLIC_KEY\n' +
                '- LICENSE_API_KEY\n' +
                '- LICENSE_SERIAL_KEY\n' +
                '- LICENSE_SERVER_URL (opcional)'
            );
            app.quit();
            return;
        }

        // Valida a licença
        console.log('Validando licença...');
        const validationResult = await this.validateLicense(
            PUBLIC_KEY,
            API_KEY,
            SERVER_URL,
            serialKey
        );

        if (!validationResult.success) {
            dialog.showErrorBox(
                'Licença Inválida',
                `Não foi possível validar a licença:\n${validationResult.message}\n\n` +
                `Código: ${validationResult.code || 'UNKNOWN'}`
            );
            app.quit();
            return;
        }

        console.log('Licença válida! Iniciando aplicação...');
        
        // Cria a janela principal
        this.createMainWindow();

        // Tratamento de fechamento da aplicação
        app.on('window-all-closed', () => {
            if (process.platform !== 'darwin') {
                app.quit();
            }
        });

        app.on('activate', () => {
            if (BrowserWindow.getAllWindows().length === 0) {
                this.createMainWindow();
            }
        });
    }
}

// Inicializa a aplicação
const licenseIntegration = new ElectronLicenseIntegration();
licenseIntegration.initialize().catch(error => {
    console.error('Erro fatal:', error);
    app.quit();
});

