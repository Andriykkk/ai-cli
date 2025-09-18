class AICliApp {
    constructor() {
        this.currentProject = null;
        this.messages = [];
        this.conversationState = 'idle'; // idle, generating, tool_approval, tool_executing
        this.abortController = null;
        this.serverUrl = localStorage.getItem('serverUrl') || 'http://localhost:8000';

        // Input management
        this.commandHistory = JSON.parse(localStorage.getItem('commandHistory') || '[]');
        this.historyIndex = -1;
        this.currentInput = '';

        // Settings management
        this.globalSettings = {};
        this.projectSettings = {};
        this.settingsType = 'global'; // 'global' or 'project'
        this.settingsPath = []; // navigation path in settings
        this.currentEditSetting = null;
        this.settingsPreviousScreen = 'project-selection'; // where to go back from settings

        // Project management
        this.contextMenuProject = null; // project for context menu actions
        this.editingProject = null; // project being edited (null = creating new)

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadProjects();
        this.setupInputField();
    }

    setupEventListeners() {
        // Helper function to safely add event listeners
        const safeAddEventListener = (id, event, handler) => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener(event, handler);
            } else {
                console.warn(`Element with id '${id}' not found`);
            }
        };

        // Navigation
        safeAddEventListener('home-btn', 'click', () => this.showProjectSelection());
        safeAddEventListener('settings-btn', 'click', () => this.showSettingsFromHeader());
        safeAddEventListener('new-project-btn', 'click', () => this.showProjectModal());
        safeAddEventListener('refresh-projects-btn', 'click', () => this.loadProjects());

        // Settings
        safeAddEventListener('global-settings-btn', 'click', () => this.switchToGlobalSettings());
        safeAddEventListener('project-settings-btn', 'click', () => this.switchToProjectSettings());
        safeAddEventListener('reset-settings-btn', 'click', () => this.resetSettings());
        safeAddEventListener('back-settings-btn', 'click', () => this.goBackFromSettings());

        // Setting editor
        safeAddEventListener('save-setting-btn', 'click', () => this.saveCurrentSetting());
        safeAddEventListener('cancel-setting-btn', 'click', () => this.cancelSettingEdit());

        // Project modal
        safeAddEventListener('cancel-project-btn', 'click', () => this.hideProjectModal());
        const projectForm = document.getElementById('project-form');
        if (projectForm) {
            projectForm.addEventListener('submit', (e) => this.createProject(e));
        }

        // Project context menu
        safeAddEventListener('edit-project-menu', 'click', () => this.editProject());
        safeAddEventListener('duplicate-project-menu', 'click', () => this.duplicateProject());
        safeAddEventListener('delete-project-menu', 'click', () => this.deleteProject());

        // Error toast
        const errorClose = document.querySelector('.error-close');
        if (errorClose) {
            errorClose.addEventListener('click', () => this.hideError());
        }

        // Global keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleGlobalKeydown(e));

        // Hide context menu on click outside
        document.addEventListener('click', (e) => this.hideContextMenuIfClickedOutside(e));
    }

    setupInputField() {
        const inputField = document.getElementById('input-field');
        const inputContainer = document.querySelector('.input-container');

        if (!inputField) {
            console.warn('Input field not found - chat interface may not be available');
            return;
        }

        inputField.addEventListener('keydown', (e) => this.handleInputKeydown(e));
        inputField.addEventListener('input', () => this.handleInputChange());
        inputField.addEventListener('paste', () => this.handleInputChange());

        // Handle focus and blur for better UX
        if (inputContainer) {
            inputField.addEventListener('focus', () => {
                inputContainer.classList.add('focused');
            });

            inputField.addEventListener('blur', () => {
                inputContainer.classList.remove('focused');
            });
        }
    }

    handleInputKeydown(e) {
        if (this.conversationState !== 'idle') {
            if (e.key === 'Escape') {
                this.cancelCurrentRequest();
            }
            return;
        }

        const inputField = e.target;

        switch (e.key) {
            case 'Enter':
                if (e.shiftKey) {
                    // Allow new line
                    return;
                }
                e.preventDefault();
                this.submitMessage();
                break;

            case 'ArrowUp':
                if (this.isAtFirstLine(inputField) || this.isEmpty(inputField)) {
                    e.preventDefault();
                    this.navigateHistoryUp();
                }
                break;

            case 'ArrowDown':
                if (this.isAtLastLine(inputField) || this.isEmpty(inputField)) {
                    e.preventDefault();
                    this.navigateHistoryDown();
                }
                break;

            case 'Escape':
                e.preventDefault();
                if (this.currentProject) {
                    this.showProjectSelection();
                }
                break;

            case 'l':
                if (e.ctrlKey) {
                    e.preventDefault();
                    this.clearMessages();
                }
                break;
        }
    }

    handleInputChange() {
        const inputField = document.getElementById('input-field');
        this.currentInput = inputField.textContent;

        // Reset history index when typing
        if (this.historyIndex !== -1) {
            this.historyIndex = -1;
        }
    }

    handleGlobalKeydown(e) {
        // Global shortcuts that work regardless of focus
        if (e.key === 'Escape') {
            e.preventDefault();
            this.handleGlobalEscape();
        } else if (e.ctrlKey && e.key === 's') {
            e.preventDefault();
            this.showSettingsFromHeader();
        } else if (e.ctrlKey && e.key === 'h') {
            e.preventDefault();
            this.showProjectSelection();
        }
    }

    handleGlobalEscape() {
        // Handle escape key globally based on current context

        // Close any open modals first
        if (!document.getElementById('project-modal').classList.contains('hidden')) {
            this.hideProjectModal();
            return;
        }

        if (!document.getElementById('setting-editor').classList.contains('hidden')) {
            this.cancelSettingEdit();
            return;
        }

        if (!document.getElementById('error-toast').classList.contains('hidden')) {
            this.hideError();
            return;
        }

        if (!document.getElementById('project-context-menu').classList.contains('hidden')) {
            this.hideContextMenu();
            return;
        }

        // Navigate between screens
        const currentScreen = this.getCurrentScreen();

        switch (currentScreen) {
            case 'settings-screen':
                if (this.settingsPath.length > 0) {
                    this.navigateBack();
                } else {
                    this.goBackFromSettings();
                }
                break;

            case 'chat-interface':
                if (this.conversationState !== 'idle') {
                    this.cancelCurrentRequest();
                } else {
                    this.showProjectSelection();
                }
                break;

            case 'project-selection':
                // Already at root, do nothing or could close app
                break;

            default:
                this.showProjectSelection();
                break;
        }
    }

    getCurrentScreen() {
        const screens = document.querySelectorAll('.screen');
        for (const screen of screens) {
            if (!screen.classList.contains('hidden')) {
                return screen.id;
            }
        }
        return 'project-selection'; // fallback
    }

    isAtFirstLine(element) {
        const selection = window.getSelection();
        if (selection.rangeCount === 0) return true;

        const range = selection.getRangeAt(0);
        const tempRange = document.createRange();
        tempRange.selectNodeContents(element);
        tempRange.setEnd(range.startContainer, range.startOffset);

        const text = tempRange.toString();
        return !text.includes('\n');
    }

    isAtLastLine(element) {
        const selection = window.getSelection();
        if (selection.rangeCount === 0) return true;

        const range = selection.getRangeAt(0);
        const tempRange = document.createRange();
        tempRange.selectNodeContents(element);
        tempRange.setStart(range.endContainer, range.endOffset);

        const text = tempRange.toString();
        return !text.includes('\n');
    }

    isEmpty(element) {
        return element.textContent.trim().length === 0;
    }

    navigateHistoryUp() {
        if (this.commandHistory.length === 0) return;

        if (this.historyIndex === -1) {
            this.historyIndex = 0;
        } else if (this.historyIndex < this.commandHistory.length - 1) {
            this.historyIndex++;
        } else {
            return; // Already at oldest
        }

        const command = this.commandHistory[this.commandHistory.length - 1 - this.historyIndex];
        this.setInputText(command);
    }

    navigateHistoryDown() {
        if (this.historyIndex === -1) return;

        this.historyIndex--;

        if (this.historyIndex === -1) {
            this.setInputText('');
        } else {
            const command = this.commandHistory[this.commandHistory.length - 1 - this.historyIndex];
            this.setInputText(command);
        }
    }

    setInputText(text) {
        const inputField = document.getElementById('input-field');
        inputField.textContent = text;

        // Set cursor to end
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(inputField);
        range.collapse(false);
        selection.removeAllRanges();
        selection.addRange(range);

        this.currentInput = text;
    }

    addToHistory(command) {
        if (!command.trim()) return;

        // Remove duplicate if exists
        const index = this.commandHistory.indexOf(command);
        if (index !== -1) {
            this.commandHistory.splice(index, 1);
        }

        // Add to beginning and limit to 50 commands
        this.commandHistory.unshift(command);
        this.commandHistory = this.commandHistory.slice(0, 50);

        // Save to localStorage
        localStorage.setItem('commandHistory', JSON.stringify(this.commandHistory));

        // Reset index
        this.historyIndex = -1;
    }

    async submitMessage() {
        const inputField = document.getElementById('input-field');
        const message = inputField.textContent.trim();

        if (!message || !this.currentProject) return;

        // Add to history
        this.addToHistory(message);

        // Clear input
        inputField.textContent = '';
        this.currentInput = '';

        // Add user message
        this.addMessage('user', message);

        // Set generating state
        this.setConversationState('generating');

        try {
            await this.sendMessage(message);
        } catch (error) {
            this.showError('Failed to send message: ' + error.message);
            this.setConversationState('idle');
        }
    }

    async sendMessage(message) {
        const controller = new AbortController();
        this.abortController = controller;

        try {
            const response = await fetch(`${this.serverUrl}/chat/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    project_id: this.currentProject.id
                }),
                signal: controller.signal
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            await this.handleStreamResponse(response);

        } catch (error) {
            if (error.name === 'AbortError') {
                this.addMessage('assistant', 'Request cancelled by user.');
            } else {
                throw error;
            }
        } finally {
            this.abortController = null;
            this.setConversationState('idle');
        }
    }

    async handleStreamResponse(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        try {
            while (true) {
                const { done, value } = await reader.read();

                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            await this.handleStreamData(data);
                        } catch (e) {
                            console.warn('Failed to parse stream data:', line);
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
    }

    async handleStreamData(data) {
        switch (data.state) {
            case 'generating':
                this.setConversationState('generating');
                break;

            case 'tool_approval':
                this.setConversationState('tool_approval');
                // For simplicity, auto-approve all tools in web version
                await this.approveTools(data.tool_calls || []);
                break;

            case 'tool_executing':
                this.setConversationState('tool_executing');
                break;

            case 'completed':
                if (data.error) {
                    this.addMessage('assistant', `Error: ${data.error}`);
                } else if (data.content) {
                    this.addMessage('assistant', data.content);
                }
                this.setConversationState('idle');
                break;
        }
    }

    async approveTools(toolCalls) {
        try {
            const response = await fetch(`${this.serverUrl}/chat/tool-approval`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    project_id: this.currentProject.id,
                    approved_tools: toolCalls.map(t => t.id),
                    denied_tools: []
                })
            });

            if (!response.ok) {
                throw new Error(`Tool approval failed: ${response.statusText}`);
            }

            await this.handleStreamResponse(response);

        } catch (error) {
            this.showError('Tool approval failed: ' + error.message);
            this.setConversationState('idle');
        }
    }

    cancelCurrentRequest() {
        if (this.abortController) {
            this.abortController.abort();
            this.abortController = null;
        }
        this.setConversationState('idle');
    }

    setConversationState(state) {
        this.conversationState = state;
        const inputContainer = document.querySelector('.input-container');
        const inputField = document.getElementById('input-field');
        const statusElement = document.getElementById('input-status');

        // Update visual state
        inputContainer.className = 'input-container';
        if (state !== 'idle') {
            inputContainer.classList.add(state);
        }

        // Update input field
        if (state === 'idle') {
            inputField.classList.remove('disabled');
            inputField.contentEditable = true;
        } else {
            inputField.classList.add('disabled');
            inputField.contentEditable = false;
        }

        // Update status text
        switch (state) {
            case 'idle':
                statusElement.textContent = 'Type your message and press Enter • ↑↓ History • Ctrl+L Clear • Esc Back';
                break;
            case 'generating':
                statusElement.textContent = 'AI is thinking... Press Esc to cancel';
                break;
            case 'tool_approval':
                statusElement.textContent = 'Auto-approving tools...';
                break;
            case 'tool_executing':
                statusElement.textContent = 'Executing tools... Press Esc to cancel';
                break;
        }
    }

    addMessage(type, content) {
        const message = {
            id: Date.now().toString(),
            type: type,
            content: content,
            timestamp: new Date().toISOString()
        };

        this.messages.push(message);
        this.renderMessage(message);
        this.scrollToBottom();
    }

    renderMessage(message) {
        const messagesContainer = document.getElementById('messages');
        const messageElement = document.createElement('div');
        messageElement.className = `message ${message.type}`;
        messageElement.dataset.id = message.id;

        const header = document.createElement('div');
        header.className = 'message-header';
        header.innerHTML = `
            <span>${message.type === 'user' ? '👤 You' : '🤖 AI Assistant'}</span>
            <span>${this.formatTime(message.timestamp)}</span>
        `;

        const content = document.createElement('div');
        content.className = 'message-content';
        content.textContent = message.content;

        messageElement.appendChild(header);
        messageElement.appendChild(content);
        messagesContainer.appendChild(messageElement);
    }

    formatTime(timestamp) {
        return new Date(timestamp).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    scrollToBottom() {
        const messagesContainer = document.getElementById('messages');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    clearMessages() {
        this.messages = [];
        document.getElementById('messages').innerHTML = '';
    }

    // Screen Management
    showScreen(screenId) {
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.add('hidden');
        });
        document.getElementById(screenId).classList.remove('hidden');
    }

    showProjectSelection() {
        this.showScreen('project-selection');
        this.currentProject = null;
        document.getElementById('project-name').textContent = 'No Project Selected';
    }

    showChatInterface() {
        this.showScreen('chat-interface');
        // Focus input field
        setTimeout(() => {
            document.getElementById('input-field').focus();
        }, 100);
    }

    showSettingsFromHeader() {
        // Called from header settings button
        this.settingsPreviousScreen = this.currentProject ? 'chat-interface' : 'project-selection';
        this.showSettings();
    }

    async showSettings() {
        this.showScreen('settings-screen');
        await this.loadAllSettings();
        this.settingsPath = [];
        this.renderSettings();
    }

    goBackFromSettings() {
        if (this.settingsPreviousScreen === 'chat-interface') {
            this.showChatInterface();
        } else {
            this.showProjectSelection();
        }
    }

    async loadAllSettings() {
        this.showLoading(true);
        try {
            // Load global settings
            const globalResponse = await fetch(`${this.serverUrl}/settings/global`);
            if (globalResponse.ok) {
                this.globalSettings = await globalResponse.json();
            }

            // Load project settings if project is selected
            if (this.currentProject) {
                const projectResponse = await fetch(`${this.serverUrl}/settings/projects/${this.currentProject.id}`);
                if (projectResponse.ok) {
                    this.projectSettings = await projectResponse.json();
                }
            }
        } catch (error) {
            this.showError('Failed to load settings: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    switchToGlobalSettings() {
        this.settingsType = 'global';
        this.settingsPath = [];
        this.updateSettingsTypeButtons();
        this.renderSettings();
    }

    switchToProjectSettings() {
        if (!this.currentProject) {
            this.showError('No project selected. Please select a project first.');
            return;
        }
        this.settingsType = 'project';
        this.settingsPath = [];
        this.updateSettingsTypeButtons();
        this.renderSettings();
    }

    updateSettingsTypeButtons() {
        const globalBtn = document.getElementById('global-settings-btn');
        const projectBtn = document.getElementById('project-settings-btn');

        globalBtn.classList.toggle('active', this.settingsType === 'global');
        projectBtn.classList.toggle('active', this.settingsType === 'project');

        // Disable project settings if no project selected
        projectBtn.disabled = !this.currentProject;
        if (!this.currentProject) {
            projectBtn.textContent = 'Project Settings (no project selected)';
        } else {
            projectBtn.textContent = `Project Settings (${this.currentProject.name})`;
        }
    }

    renderSettings() {
        const settings = this.settingsType === 'global' ? this.globalSettings : this.projectSettings;
        const navigation = document.getElementById('settings-navigation');
        const breadcrumb = document.getElementById('settings-breadcrumb');

        // Update breadcrumb
        let breadcrumbText = this.settingsType === 'global' ? 'Global Settings' : `Project Settings (${this.currentProject?.name || 'none'})`;
        if (this.settingsPath.length > 0) {
            breadcrumbText += ' > ' + this.settingsPath.map(p => p.replace('_', ' ')).join(' > ');
        }
        breadcrumb.textContent = breadcrumbText;

        // Get current section
        let currentSection = settings;
        for (const path of this.settingsPath) {
            currentSection = currentSection[path];
        }

        // Render items
        navigation.innerHTML = '';

        if (!currentSection) {
            navigation.innerHTML = '<div class="setting-item">No settings available</div>';
            return;
        }

        Object.keys(currentSection).forEach(key => {
            const item = currentSection[key];
            const settingElement = document.createElement('div');
            settingElement.className = 'setting-item';

            if (typeof item === 'object' && item.type) {
                // This is a setting value
                settingElement.innerHTML = `
                    <div>
                        <span class="setting-label">${key.replace('_', ' ')}</span>
                        <span class="setting-type">(${item.type})</span>
                    </div>
                    <div class="setting-value">${this.formatSettingValue(item)}</div>
                `;
                settingElement.addEventListener('click', () => this.editSetting(key, item));
            } else {
                // This is a category
                settingElement.classList.add('category');
                settingElement.innerHTML = `
                    <div class="setting-label">${key.replace('_', ' ')}</div>
                    <div class="setting-value">→</div>
                `;
                settingElement.addEventListener('click', () => this.navigateToCategory(key));
            }

            navigation.appendChild(settingElement);
        });

        // Add back button if not at root
        if (this.settingsPath.length > 0) {
            const backElement = document.createElement('div');
            backElement.className = 'setting-item category';
            backElement.innerHTML = `
                <div class="setting-label">← Back</div>
                <div class="setting-value"></div>
            `;
            backElement.addEventListener('click', () => this.navigateBack());
            navigation.insertBefore(backElement, navigation.firstChild);
        }
    }

    formatSettingValue(item) {
        if (item.type === 'boolean') {
            return item.value ? '✓ Enabled' : '✗ Disabled';
        } else if (item.masked && item.value) {
            return '●●●●●●●●';
        } else if (item.type === 'selector') {
            return item.value || '(not set)';
        } else if (item.type === 'number') {
            return String(item.value);
        } else {
            return item.value || '(empty)';
        }
    }

    navigateToCategory(category) {
        this.settingsPath.push(category);
        this.renderSettings();
    }

    navigateBack() {
        this.settingsPath.pop();
        this.renderSettings();
    }

    editSetting(key, item) {
        this.currentEditSetting = { key, ...item, path: [...this.settingsPath] };
        this.showSettingEditor();
    }

    showSettingEditor() {
        if (!this.currentEditSetting) return;

        const editor = document.getElementById('setting-editor');
        const title = document.getElementById('setting-editor-title');
        const fields = document.getElementById('setting-editor-fields');

        title.textContent = `Edit: ${this.currentEditSetting.key.replace('_', ' ')}`;

        // Render appropriate input based on type
        fields.innerHTML = '';

        if (this.currentEditSetting.type === 'boolean') {
            fields.innerHTML = `
                <div class="setting-editor-field">
                    <label>Value:</label>
                    <div class="boolean-toggle" id="boolean-toggle">
                        <div class="toggle-switch ${this.currentEditSetting.value ? 'active' : ''}" id="toggle-switch">
                            <div class="toggle-slider"></div>
                        </div>
                        <span>${this.currentEditSetting.value ? 'Enabled' : 'Disabled'}</span>
                    </div>
                </div>
            `;

            document.getElementById('boolean-toggle').addEventListener('click', () => {
                this.currentEditSetting.value = !this.currentEditSetting.value;
                this.showSettingEditor(); // Re-render
            });
        } else if (this.currentEditSetting.type === 'selector') {
            const options = this.currentEditSetting.options || [];
            const optionsHtml = options.map(opt =>
                `<option value="${opt}" ${opt === this.currentEditSetting.value ? 'selected' : ''}>${opt}</option>`
            ).join('');

            fields.innerHTML = `
                <div class="setting-editor-field">
                    <label>Value:</label>
                    <select id="selector-input">
                        ${optionsHtml}
                    </select>
                </div>
            `;
        } else if (this.currentEditSetting.type === 'number') {
            fields.innerHTML = `
                <div class="setting-editor-field">
                    <label>Value:</label>
                    <div class="number-input-container">
                        <input type="number" 
                               id="number-input" 
                               value="${this.currentEditSetting.value}"
                               min="${this.currentEditSetting.min || ''}"
                               max="${this.currentEditSetting.max || ''}"
                               step="${this.currentEditSetting.step || 1}"
                               class="number-value">
                        ${this.currentEditSetting.min !== undefined && this.currentEditSetting.max !== undefined ? `
                            <input type="range" 
                                   id="number-range"
                                   value="${this.currentEditSetting.value}"
                                   min="${this.currentEditSetting.min}"
                                   max="${this.currentEditSetting.max}"
                                   step="${this.currentEditSetting.step || 1}"
                                   class="number-range">
                        ` : ''}
                    </div>
                    ${this.currentEditSetting.min !== undefined ? `<small>Min: ${this.currentEditSetting.min}</small>` : ''}
                    ${this.currentEditSetting.max !== undefined ? `<small>Max: ${this.currentEditSetting.max}</small>` : ''}
                </div>
            `;

            // Sync number input and range
            const numberInput = document.getElementById('number-input');
            const rangeInput = document.getElementById('number-range');

            if (rangeInput) {
                numberInput.addEventListener('input', () => {
                    rangeInput.value = numberInput.value;
                });
                rangeInput.addEventListener('input', () => {
                    numberInput.value = rangeInput.value;
                });
            }
        } else {
            // Text input
            fields.innerHTML = `
                <div class="setting-editor-field">
                    <label>Value:</label>
                    <input type="${this.currentEditSetting.masked ? 'password' : 'text'}" 
                           id="text-input" 
                           value="${this.currentEditSetting.masked ? '' : this.currentEditSetting.value}"
                           placeholder="${this.currentEditSetting.masked ? 'Enter new value' : 'Enter value'}">
                    ${this.currentEditSetting.optional ? '<small>This field is optional</small>' : ''}
                </div>
            `;
        }

        editor.classList.remove('hidden');
    }

    async saveCurrentSetting() {
        if (!this.currentEditSetting) return;

        let newValue = this.currentEditSetting.value;

        // Get value from input
        if (this.currentEditSetting.type === 'boolean') {
            // Value already updated in toggle
        } else if (this.currentEditSetting.type === 'selector') {
            newValue = document.getElementById('selector-input').value;
        } else if (this.currentEditSetting.type === 'number') {
            newValue = parseFloat(document.getElementById('number-input').value);
        } else {
            newValue = document.getElementById('text-input').value;
        }

        // Update settings object
        const settings = this.settingsType === 'global' ? this.globalSettings : this.projectSettings;
        let currentSection = settings;
        for (const path of this.currentEditSetting.path) {
            currentSection = currentSection[path];
        }
        currentSection[this.currentEditSetting.key].value = newValue;

        // Save to server
        try {
            this.showLoading(true);

            if (this.settingsType === 'global') {
                await fetch(`${this.serverUrl}/settings/global`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        config_name: 'global',
                        config_data: this.globalSettings
                    })
                });
            } else {
                await fetch(`${this.serverUrl}/settings/projects/${this.currentProject.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        project_id: this.currentProject.id,
                        config_data: this.projectSettings
                    })
                });
            }

            this.cancelSettingEdit();
            this.renderSettings();

        } catch (error) {
            this.showError('Failed to save setting: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    cancelSettingEdit() {
        document.getElementById('setting-editor').classList.add('hidden');
        this.currentEditSetting = null;
    }

    async resetSettings() {
        if (!confirm(`Reset ${this.settingsType} settings to defaults? This cannot be undone.`)) {
            return;
        }

        try {
            this.showLoading(true);

            if (this.settingsType === 'global') {
                await fetch(`${this.serverUrl}/settings/global/reset`, { method: 'POST' });
            } else if (this.currentProject) {
                await fetch(`${this.serverUrl}/settings/projects/${this.currentProject.id}/reset`, { method: 'POST' });
            }

            await this.loadAllSettings();
            this.renderSettings();

        } catch (error) {
            this.showError('Failed to reset settings: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    // Project Management
    async loadProjects() {
        this.showLoading(true);
        try {
            const response = await fetch(`${this.serverUrl}/projects`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const projects = await response.json();
            this.renderProjects(projects);
        } catch (error) {
            this.showError('Failed to load projects: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    renderProjects(projects) {
        const projectList = document.getElementById('project-list');
        projectList.innerHTML = '';

        if (projects.length === 0) {
            projectList.innerHTML = '<div style="padding: 1rem; text-align: center; color: #888;">No projects found. Create your first project!</div>';
            return;
        }

        projects.forEach(project => {
            const projectItem = document.createElement('div');
            projectItem.className = 'project-item';

            const description = project.description ? `<div class="project-description">${project.description}</div>` : '';

            projectItem.innerHTML = `
                <div class="project-content">
                    <div class="project-name">${project.name}</div>
                    ${description}
                    <div class="project-details">${project.model_provider || 'Not configured'}/${project.model_name || 'Not set'} • ${project.path}</div>
                </div>
                <div class="project-actions">
                    <button class="project-menu-btn" title="Project menu">⋮</button>
                </div>
            `;

            // Add click handler for project content (not the menu button)
            const projectContent = projectItem.querySelector('.project-content');
            projectContent.addEventListener('click', () => this.selectProject(project));

            // Add click handler for menu button
            const menuBtn = projectItem.querySelector('.project-menu-btn');
            menuBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.showProjectContextMenu(e, project);
            });

            projectList.appendChild(projectItem);
        });
    }

    async selectProject(project) {
        this.currentProject = project;
        document.getElementById('project-name').textContent = project.name;

        // Load chat history
        await this.loadChatHistory();

        this.showChatInterface();
    }

    async loadChatHistory() {
        try {
            const response = await fetch(`${this.serverUrl}/chat/history/${this.currentProject.id}?limit=50`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.messages = [];
            document.getElementById('messages').innerHTML = '';

            // Convert history to messages
            data.messages.forEach(histMsg => {
                this.addMessage('user', histMsg.message);
                this.addMessage('assistant', histMsg.response);
            });

        } catch (error) {
            console.warn('Failed to load chat history:', error);
            // Show welcome message if history fails
            this.addMessage('assistant', `Welcome to ${this.currentProject.name}!\n\nI'm ready to help with your ${this.currentProject.model_provider}/${this.currentProject.model_name} project.`);
        }
    }

    showProjectModal() {
        document.getElementById('project-modal').classList.remove('hidden');
        document.getElementById('project-name-input').focus();
    }

    hideProjectModal() {
        document.getElementById('project-modal').classList.add('hidden');
        document.getElementById('project-form').reset();

        // Reset form to creation mode
        document.querySelector('#project-modal h3').textContent = 'Create New Project';
        document.querySelector('#project-form button[type="submit"]').textContent = 'Create';
        this.editingProject = null;
    }

    async createProject(e) {
        e.preventDefault();

        const project = {
            name: document.getElementById('project-name-input').value,
            path: document.getElementById('project-path-input').value,
            description: document.getElementById('project-description-input').value || '',
            memory_enabled: true,
            tools_enabled: true
        };

        this.showLoading(true);
        try {
            let response;
            let resultProject;

            if (this.editingProject) {
                // Editing existing project
                response = await fetch(`${this.serverUrl}/projects/${this.editingProject.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(project)
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                resultProject = await response.json();
                this.hideProjectModal();

                // Update current project if it's the one being edited
                if (this.currentProject && this.currentProject.id === this.editingProject.id) {
                    this.currentProject = resultProject;
                    document.getElementById('project-name').textContent = resultProject.name;
                }

                // Reload project list
                await this.loadProjects();

            } else {
                // Creating new project
                response = await fetch(`${this.serverUrl}/projects`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(project)
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                resultProject = await response.json();
                this.hideProjectModal();

                // Set the new project as current and go to project settings
                this.currentProject = resultProject;
                document.getElementById('project-name').textContent = resultProject.name;

                // Load project settings and show them
                this.settingsPreviousScreen = 'chat-interface'; // After settings, go to chat
                await this.loadAllSettings();
                this.settingsType = 'project';
                this.settingsPath = [];
                this.showSettings();
            }

        } catch (error) {
            this.showError(`Failed to ${this.editingProject ? 'update' : 'create'} project: ` + error.message);
        } finally {
            this.showLoading(false);
        }
    }


    // UI Helpers
    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (show) {
            overlay.classList.remove('hidden');
        } else {
            overlay.classList.add('hidden');
        }
    }

    showError(message) {
        const toast = document.getElementById('error-toast');
        const messageElement = toast.querySelector('.error-message');
        messageElement.textContent = message;
        toast.classList.remove('hidden');

        // Auto-hide after 5 seconds
        setTimeout(() => this.hideError(), 5000);
    }

    hideError() {
        document.getElementById('error-toast').classList.add('hidden');
    }

    // Project Context Menu Methods
    showProjectContextMenu(event, project) {
        console.log('Setting contextMenuProject to:', project);
        this.contextMenuProject = project;
        const contextMenu = document.getElementById('project-context-menu');

        if (!project) {
            console.error('No project provided to showProjectContextMenu');
            return;
        }

        // Position the menu near the click point
        const rect = event.target.getBoundingClientRect();
        let menuX = rect.right + 5;
        let menuY = rect.top;

        // Show menu first to get its dimensions
        contextMenu.classList.remove('hidden');
        contextMenu.style.left = menuX + 'px';
        contextMenu.style.top = menuY + 'px';

        // Adjust position if menu would go off screen
        const menuRect = contextMenu.getBoundingClientRect();
        if (menuRect.right > window.innerWidth) {
            menuX = rect.left - menuRect.width - 5;
        }
        if (menuRect.bottom > window.innerHeight) {
            menuY = rect.bottom - menuRect.height;
        }

        // Apply final position
        contextMenu.style.left = Math.max(5, menuX) + 'px';
        contextMenu.style.top = Math.max(5, menuY) + 'px';
    }

    hideContextMenuIfClickedOutside(event) {
        const contextMenu = document.getElementById('project-context-menu');
        if (!contextMenu.classList.contains('hidden') &&
            !contextMenu.contains(event.target) &&
            !event.target.classList.contains('project-menu-btn')) {
            this.hideContextMenu();
        }
    }

    hideContextMenu() {
        document.getElementById('project-context-menu').classList.add('hidden');
        this.contextMenuProject = null;
    }

    editProject() {
        console.log('editProject called, contextMenuProject:', this.contextMenuProject);
        if (!this.contextMenuProject) {
            console.warn('No project selected for editing');
            return;
        }

        // Store the project reference before hiding the context menu
        const projectToEdit = this.contextMenuProject;
        this.hideContextMenu();

        // Pre-fill the project form with existing data
        document.getElementById('project-name-input').value = projectToEdit.name || '';
        document.getElementById('project-path-input').value = projectToEdit.path || '';
        document.getElementById('project-description-input').value = projectToEdit.description || '';

        // Change form title and button text to indicate editing
        document.querySelector('#project-modal h3').textContent = 'Edit Project';
        document.querySelector('#project-form button[type="submit"]').textContent = 'Save Changes';

        // Store that we're editing (not creating)
        this.editingProject = projectToEdit;

        this.showProjectModal();
    }

    duplicateProject() {
        if (!this.contextMenuProject) {
            console.warn('No project selected for duplication');
            return;
        }

        // Store the project reference before hiding the context menu
        const projectToDuplicate = this.contextMenuProject;
        this.hideContextMenu();

        // Pre-fill the project form with existing data but modify name
        document.getElementById('project-name-input').value = (projectToDuplicate.name || 'Untitled') + ' (Copy)';
        document.getElementById('project-path-input').value = projectToDuplicate.path || '';
        document.getElementById('project-description-input').value = projectToDuplicate.description || '';

        // Reset form to creation mode
        document.querySelector('#project-modal h3').textContent = 'Create New Project';
        document.querySelector('#project-form button[type="submit"]').textContent = 'Create';
        this.editingProject = null;

        this.showProjectModal();
    }

    async deleteProject() {
        if (!this.contextMenuProject) {
            console.warn('No project selected for deletion');
            return;
        }

        // Store the project reference before hiding the context menu
        const projectToDelete = this.contextMenuProject;
        this.hideContextMenu();

        const projectName = projectToDelete.name || 'Untitled Project';
        if (!confirm(`Are you sure you want to delete the project "${projectName}"?\n\nThis action cannot be undone and will delete all chat history for this project.`)) {
            return;
        }

        this.showLoading(true);
        try {
            const response = await fetch(`${this.serverUrl}/projects/${projectToDelete.id}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // If we deleted the current project, clear it
            if (this.currentProject && this.currentProject.id === projectToDelete.id) {
                this.currentProject = null;
                document.getElementById('project-name').textContent = 'No Project Selected';
            }

            // Reload the project list
            await this.loadProjects();

        } catch (error) {
            this.showError('Failed to delete project: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }
}

// Initialize the app when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.app = new AICliApp();
});