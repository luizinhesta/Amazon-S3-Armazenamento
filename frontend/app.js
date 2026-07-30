/**
 * Cofre Digital de Documentos — Lógica da Aplicação
 * 
 * Gerencia upload, listagem, download, versões e restauração
 * de documentos via API Gateway + Lambda + S3.
 */

// ============================================
// Configuração e Estado
// ============================================

const API_URL = window.APP_CONFIG ? window.APP_CONFIG.API_BASE_URL : '';
let currentPageToken = null;
let allDocuments = [];

// ============================================
// Inicialização
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    listDocuments();
});

function initEventListeners() {
    // Upload
    document.getElementById('upload-form').addEventListener('submit', handleUpload);
    document.getElementById('doc-file').addEventListener('change', showFileInfo);

    // Listagem
    document.getElementById('btn-refresh').addEventListener('click', () => listDocuments());
    document.getElementById('filter-category').addEventListener('change', () => listDocuments());
    document.getElementById('btn-next-page').addEventListener('click', loadNextPage);

    // Versões
    document.getElementById('btn-close-versions').addEventListener('click', closeVersions);
}

// ============================================
// Upload de Documentos
// ============================================

async function handleUpload(e) {
    e.preventDefault();

    const docName = document.getElementById('doc-name').value.trim();
    const docType = document.getElementById('doc-type').value;
    const description = document.getElementById('doc-description').value.trim();
    const fileInput = document.getElementById('doc-file');
    const file = fileInput.files[0];

    if (!file) {
        showMessage('upload-message', 'Selecione um arquivo', 'error');
        return;
    }

    const btn = document.getElementById('btn-upload');
    btn.disabled = true;
    btn.textContent = 'Enviando...';
    hideMessage('upload-message');

    try {
        // 1. Solicita URL pré-assinada
        const response = await fetch(`${API_URL}/upload-url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename: file.name,
                category: docType,
                contentType: file.type || 'application/octet-stream',
                documentName: docName,
                documentType: docType,
                description: description,
                fileSize: file.size,
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Erro ao solicitar URL de upload');
        }

        // 2. Envia arquivo diretamente ao S3
        showProgress(0);
        await uploadFileToS3(data.uploadUrl, file, data.headers || {});

        showMessage('upload-message', 'Documento enviado com sucesso!', 'success');
        document.getElementById('upload-form').reset();
        hideFileInfo();
        hideProgress();

        // 3. Atualiza lista após breve delay (processamento Lambda)
        setTimeout(() => listDocuments(), 3000);

    } catch (error) {
        showMessage('upload-message', tratarErro(error), 'error');
        hideProgress();
    } finally {
        btn.disabled = false;
        btn.textContent = 'Enviar documento';
    }
}

function uploadFileToS3(url, file, headers) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('PUT', url);

        // Define headers necessários
        xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream');

        // Adiciona metadados como headers (x-amz-meta-*)
        Object.entries(headers).forEach(([key, value]) => {
            if (key.startsWith('x-amz-meta-')) {
                xhr.setRequestHeader(key, value);
            }
        });

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                showProgress(percent);
            }
        };

        xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve();
            } else {
                reject(new Error('Falha no upload do arquivo'));
            }
        };

        xhr.onerror = () => reject(new Error('Erro de conexão ao enviar arquivo'));
        xhr.send(file);
    });
}

// ============================================
// Listagem de Documentos
// ============================================

async function listDocuments(pageToken) {
    const category = document.getElementById('filter-category').value;
    const tbody = document.getElementById('documents-body');

    if (!pageToken) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">Carregando...</td></tr>';
        allDocuments = [];
    }

    try {
        let url = `${API_URL}/documentos?`;
        if (category) url += `prefix=${category}&`;
        if (pageToken) url += `page_token=${pageToken}`;

        const response = await fetch(url);
        const data = await response.json();

        if (!response.ok) throw new Error(data.error || 'Erro ao listar documentos');

        allDocuments = pageToken ? [...allDocuments, ...data.documents] : data.documents;
        currentPageToken = data.nextPageToken || null;

        renderDocuments(allDocuments);

        // Paginação
        const pagination = document.getElementById('pagination');
        if (currentPageToken) {
            pagination.classList.remove('hidden');
        } else {
            pagination.classList.add('hidden');
        }

    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="7" class="empty-state">${tratarErro(error)}</td></tr>`;
    }
}

function loadNextPage() {
    if (currentPageToken) listDocuments(currentPageToken);
}

function renderDocuments(documents) {
    const tbody = document.getElementById('documents-body');

    if (!documents || documents.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="empty-state">Nenhum documento encontrado</td></tr>';
        return;
    }

    tbody.innerHTML = documents.map(doc => `
        <tr>
            <td title="${doc.key}">${doc.name}</td>
            <td>${formatCategory(doc.category)}</td>
            <td>${formatSize(doc.size)}</td>
            <td>${formatStorageClass(doc.storageClass)}</td>
            <td>${formatDate(doc.lastModified)}</td>
            <td>${formatRestoreStatus(doc.restoreStatus)}</td>
            <td class="actions">
                <button class="btn btn-small btn-primary" onclick="downloadDocument('${doc.key}')">⬇️</button>
                <button class="btn btn-small btn-secondary" onclick="showVersions('${doc.key}', '${doc.name}')">📋</button>
                ${needsRestore(doc.storageClass) ? `<button class="btn btn-small btn-danger" onclick="restoreDocument('${doc.key}')">🔄</button>` : ''}
            </td>
        </tr>
    `).join('');
}

// ============================================
// Download de Documentos
// ============================================

async function downloadDocument(key, versionId) {
    try {
        let url = `${API_URL}/download-url?key=${encodeURIComponent(key)}`;
        if (versionId) url += `&versionId=${encodeURIComponent(versionId)}`;

        const response = await fetch(url);
        const data = await response.json();

        if (!response.ok) {
            alert(data.error || 'Erro ao gerar URL de download');
            return;
        }

        // Abre download em nova aba
        window.open(data.downloadUrl, '_blank');

    } catch (error) {
        alert(tratarErro(error));
    }
}

// ============================================
// Versões de Documentos
// ============================================

async function showVersions(key, name) {
    const section = document.getElementById('versions-section');
    const tbody = document.getElementById('versions-body');

    document.getElementById('versions-doc-name').textContent = `Versões de: ${name}`;
    section.classList.remove('hidden');
    tbody.innerHTML = '<tr><td colspan="5" class="empty-state">Carregando...</td></tr>';

    try {
        const response = await fetch(`${API_URL}/versoes?key=${encodeURIComponent(key)}`);
        const data = await response.json();

        if (!response.ok) throw new Error(data.error || 'Erro ao listar versões');

        if (!data.versions || data.versions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">Nenhuma versão encontrada</td></tr>';
            return;
        }

        tbody.innerHTML = data.versions.map(v => `
            <tr>
                <td><code>${v.versionId.substring(0, 12)}...</code></td>
                <td>${formatDate(v.lastModified)}</td>
                <td>${formatSize(v.size)}</td>
                <td>${v.isLatest ? '<span class="badge badge-standard">Atual</span>' : 'Anterior'}</td>
                <td><button class="btn btn-small btn-primary" onclick="downloadDocument('${key}', '${v.versionId}')">⬇️</button></td>
            </tr>
        `).join('');

        // Mostra delete markers se existirem
        if (data.deleteMarkers && data.deleteMarkers.length > 0) {
            const markersHtml = data.deleteMarkers.map(m => `
                <tr style="opacity: 0.6">
                    <td><code>${m.versionId.substring(0, 12)}...</code></td>
                    <td>${formatDate(m.lastModified)}</td>
                    <td>—</td>
                    <td><span class="badge badge-glacier">Delete Marker</span></td>
                    <td>—</td>
                </tr>
            `).join('');
            tbody.innerHTML += markersHtml;
        }

    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty-state">${tratarErro(error)}</td></tr>`;
    }
}

function closeVersions() {
    document.getElementById('versions-section').classList.add('hidden');
}

// ============================================
// Restauração Glacier
// ============================================

async function restoreDocument(key) {
    const tier = prompt(
        'Selecione o tier de restauração:\n\n' +
        '• Standard (3-5 horas para Glacier, 12h para Deep Archive)\n' +
        '• Bulk (5-12 horas para Glacier, 48h para Deep Archive)\n' +
        '• Expedited (1-5 minutos, apenas Glacier)\n\n' +
        'Digite: Standard, Bulk ou Expedited',
        'Standard'
    );

    if (!tier) return;

    const validTiers = ['Standard', 'Bulk', 'Expedited'];
    if (!validTiers.includes(tier)) {
        alert('Tier inválido. Use: Standard, Bulk ou Expedited');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/restaurar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key, tier, days: 2 }),
        });

        const data = await response.json();

        if (!response.ok) {
            alert(data.error || 'Erro ao restaurar documento');
            return;
        }

        alert(data.message || 'Restauração iniciada com sucesso!');
        listDocuments();

    } catch (error) {
        alert(tratarErro(error));
    }
}

// ============================================
// Funções Auxiliares
// ============================================

function formatSize(bytes) {
    if (!bytes) return '—';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

function formatDate(isoDate) {
    if (!isoDate) return '—';
    try {
        const date = new Date(isoDate);
        return date.toLocaleDateString('pt-BR') + ' ' + date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    } catch {
        return isoDate;
    }
}

function formatCategory(category) {
    const names = {
        'contratos': 'Contrato',
        'notas-fiscais': 'Nota Fiscal',
        'relatorios': 'Relatório',
        'comprovantes': 'Comprovante',
        'outros': 'Outro',
    };
    return names[category] || category || '—';
}

function formatStorageClass(cls) {
    const badges = {
        'STANDARD': '<span class="badge badge-standard">Standard</span>',
        'INTELLIGENT_TIERING': '<span class="badge badge-it">Intelligent-Tiering</span>',
        'GLACIER': '<span class="badge badge-glacier">Glacier</span>',
        'DEEP_ARCHIVE': '<span class="badge badge-deep">Deep Archive</span>',
    };
    return badges[cls] || `<span class="badge">${cls || 'Standard'}</span>`;
}

function formatRestoreStatus(status) {
    if (!status) return '—';
    if (status.includes('ongoing-request="true"')) {
        return '<span class="badge badge-restoring">Restaurando...</span>';
    }
    if (status.includes('ongoing-request="false"')) {
        return '<span class="badge badge-standard">Disponível</span>';
    }
    return '—';
}

function needsRestore(storageClass) {
    return ['GLACIER', 'DEEP_ARCHIVE'].includes(storageClass);
}

function showFileInfo() {
    const file = document.getElementById('doc-file').files[0];
    const info = document.getElementById('file-info');
    if (file) {
        info.textContent = `📎 ${file.name} — ${formatSize(file.size)} — ${file.type || 'tipo desconhecido'}`;
        info.classList.remove('hidden');
    }
}

function hideFileInfo() {
    document.getElementById('file-info').classList.add('hidden');
}

function showProgress(percent) {
    const container = document.getElementById('progress-container');
    const fill = document.getElementById('progress-fill');
    const text = document.getElementById('progress-text');
    container.classList.remove('hidden');
    fill.style.width = percent + '%';
    text.textContent = percent + '%';
}

function hideProgress() {
    document.getElementById('progress-container').classList.add('hidden');
    document.getElementById('progress-fill').style.width = '0%';
}

function showMessage(elementId, text, type) {
    const el = document.getElementById(elementId);
    el.textContent = text;
    el.className = `message message-${type}`;
    el.classList.remove('hidden');
}

function hideMessage(elementId) {
    document.getElementById(elementId).classList.add('hidden');
}

function tratarErro(error) {
    // Mensagens amigáveis em português
    if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
        return 'Erro de conexão. Verifique sua internet e tente novamente.';
    }
    if (error.message.includes('CORS')) {
        return 'Erro de permissão de acesso. Entre em contato com o administrador.';
    }
    // Retorna a mensagem da API se disponível
    return error.message || 'Ocorreu um erro inesperado. Tente novamente.';
}
