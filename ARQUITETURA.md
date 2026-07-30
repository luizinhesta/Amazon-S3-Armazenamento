# Arquitetura — Cofre Digital de Documentos com Amazon S3

Este documento detalha a arquitetura do Cofre Digital, incluindo diagramas de infraestrutura, fluxos de dados, decisões de segurança e explicação de cada componente AWS utilizado.

> **Nota:** Toda a infraestrutura é criada manualmente via Console AWS. Este documento serve como referência visual e conceitual para entender como os serviços se conectam.

---

## 1. Diagrama Geral da Infraestrutura

```mermaid
graph TB
    subgraph "Usuário"
        Browser[🌐 Navegador do Usuário]
    end

    subgraph "AWS Cloud"
        subgraph "Camada de Distribuição"
            CF[☁️ CloudFront Distribution]
        end

        subgraph "Armazenamento Frontend"
            S3F[📦 S3 Bucket Frontend<br/>Privado + SSE-S3]
        end

        subgraph "Camada de API"
            APIGW[🔌 API Gateway HTTP API<br/>5 rotas, payload v2.0]
        end

        subgraph "Camada de Processamento"
            L1[⚡ gerar-url-upload]
            L2[⚡ processar-documento]
            L3[⚡ listar-documentos]
            L4[⚡ gerar-url-download]
            L5[⚡ listar-versoes]
            L6[⚡ restaurar-documento]
        end

        subgraph "Armazenamento de Documentos"
            S3D[📦 S3 Bucket Documentos<br/>Privado + Versionamento + SSE-S3]
        end

        subgraph "Observabilidade"
            CW[📊 CloudWatch Logs]
        end

        subgraph "Segurança"
            IAM[🔐 IAM Roles e Policies<br/>Privilégio Mínimo]
        end
    end

    %% Conexões do Navegador
    Browser -->|"HTTPS (páginas)"| CF
    Browser -->|"HTTPS (API calls)"| APIGW
    Browser -->|"Pre-signed PUT (upload)"| S3D
    Browser -->|"Pre-signed GET (download)"| S3D

    %% CloudFront para Frontend
    CF -->|"OAC (Origin Access Control)"| S3F

    %% API Gateway para Lambdas
    APIGW -->|"POST /upload-url"| L1
    APIGW -->|"GET /documentos"| L3
    APIGW -->|"GET /download-url"| L4
    APIGW -->|"GET /versoes"| L5
    APIGW -->|"POST /restaurar"| L6

    %% S3 Event Notification
    S3D -->|"S3 Event<br/>ObjectCreated entrada/"| L2

    %% Lambdas para S3 Documentos
    L1 -->|"generate_presigned_url"| S3D
    L2 -->|"get, copy, delete, tag"| S3D
    L3 -->|"list, get_tagging"| S3D
    L4 -->|"head, generate_presigned_url"| S3D
    L5 -->|"list_object_versions"| S3D
    L6 -->|"head, restore_object"| S3D

    %% Lambdas para CloudWatch
    L1 --> CW
    L2 --> CW
    L3 --> CW
    L4 --> CW
    L5 --> CW
    L6 --> CW

    %% IAM
    IAM -.->|"assume role"| L1
    IAM -.->|"assume role"| L2
    IAM -.->|"assume role"| L3
    IAM -.->|"assume role"| L4
    IAM -.->|"assume role"| L5
    IAM -.->|"assume role"| L6
```

---

## 2. Diagrama de Upload

O upload utiliza URLs pré-assinadas para que o arquivo vá diretamente do navegador para o S3, sem trafegar pelo Lambda ou API Gateway. Isso reduz custos e latência.

```mermaid
sequenceDiagram
    participant U as 👤 Usuário
    participant FE as 🖥️ Frontend
    participant API as 🔌 API Gateway
    participant L1 as ⚡ gerar-url-upload
    participant S3 as 📦 S3 Documentos
    participant L2 as ⚡ processar-documento

    U->>FE: Seleciona arquivo + categoria
    FE->>FE: Valida extensão no client-side
    FE->>API: POST /upload-url<br/>{filename, category, contentType}
    API->>L1: Invoca Lambda (payload v2.0)
    
    Note over L1: Validação server-side
    L1->>L1: Valida extensão permitida
    L1->>L1: Valida campos obrigatórios
    L1->>L1: Sanitiza nome do arquivo
    L1->>L1: Constrói key: entrada/{category}/{filename}
    
    L1->>S3: generate_presigned_url(PUT)<br/>Expiração: 5 min, Limite: 20MB
    S3-->>L1: URL pré-assinada
    L1-->>API: {uploadUrl, key, expiresIn: 300}
    API-->>FE: Resposta JSON

    FE->>S3: PUT arquivo via URL pré-assinada<br/>(upload direto, sem passar pelo backend)
    S3-->>FE: 200 OK

    Note over S3,L2: Processamento assíncrono automático
    S3->>L2: S3 Event Notification<br/>(ObjectCreated em entrada/)
    L2->>S3: GetObject — lê o arquivo
    L2->>L2: Valida extensão do objeto
    
    alt Extensão válida
        L2->>S3: PutObjectTagging (tags de processamento)
        L2->>S3: CopyObject para processados/{category}/{filename}
        L2->>S3: DeleteObject de entrada/{category}/{filename}
    else Extensão inválida
        L2->>S3: CopyObject para rejeitados/{filename}
        L2->>S3: DeleteObject de entrada/{category}/{filename}
    end
```

---

## 3. Diagrama de Processamento

O Lambda `processar-documento` é invocado automaticamente quando um objeto é criado no prefixo `entrada/`. Ele classifica e roteia o documento.

```mermaid
flowchart TD
    A[📨 S3 Event: ObjectCreated] --> B{Key começa com<br/>entrada/?}
    B -->|Não| C[🚫 Ignorar evento<br/>Prevenção de loop]
    B -->|Sim| D[📖 Ler metadados do objeto]
    D --> E{Extensão é válida?<br/>pdf, png, jpg, jpeg,<br/>csv, xlsx, txt}
    
    E -->|✅ Válida| F[🏷️ Adicionar tags ao objeto]
    F --> G[Tags: tipo-arquivo, data-processamento,<br/>categoria, status=processado]
    G --> H[📋 Copiar para processados/categoria/arquivo]
    H --> I[🗑️ Deletar original de entrada/]
    I --> J[✅ Documento processado com sucesso]

    E -->|❌ Inválida| K[🏷️ Adicionar tags de rejeição]
    K --> L[Tags: status=rejeitado,<br/>motivo-rejeicao=extensão inválida]
    L --> M[📋 Copiar para rejeitados/arquivo]
    M --> N[🗑️ Deletar original de entrada/]
    N --> O[⚠️ Documento rejeitado]

    style J fill:#d4edda,stroke:#28a745
    style O fill:#f8d7da,stroke:#dc3545
    style C fill:#fff3cd,stroke:#ffc107
```

### Prevenção de Loop

O diagrama acima mostra a **guard clause** que impede processamento infinito:

1. O S3 Event Notification já filtra por prefixo `entrada/` (primeira barreira)
2. O Lambda verifica novamente se a key começa com `entrada/` (defesa em profundidade)
3. Objetos em `processados/`, `rejeitados/`, `temporarios/` ou `laboratorio/` são ignorados

---

## 4. Diagrama de Download

O download verifica a classe de armazenamento antes de gerar a URL. Objetos em Glacier não podem ser baixados diretamente.

```mermaid
sequenceDiagram
    participant U as 👤 Usuário
    participant FE as 🖥️ Frontend
    participant API as 🔌 API Gateway
    participant L4 as ⚡ gerar-url-download
    participant S3 as 📦 S3 Documentos

    U->>FE: Clica em "Download"
    FE->>API: GET /download-url?key=processados/contratos/doc.pdf
    API->>L4: Invoca Lambda

    L4->>S3: head_object(key)<br/>Verifica StorageClass e Restore
    S3-->>L4: Metadados do objeto

    alt StorageClass = STANDARD ou INTELLIGENT_TIERING
        Note over L4: Acesso imediato disponível
        L4->>S3: generate_presigned_url(GET)<br/>Expiração: 5 min
        S3-->>L4: URL pré-assinada
        L4-->>API: {downloadUrl, expiresIn: 300}
        API-->>FE: Resposta JSON
        FE->>S3: GET via URL pré-assinada
        S3-->>FE: Arquivo (download direto)
    
    else StorageClass = GLACIER/DEEP_ARCHIVE sem restauração
        Note over L4: Arquivo arquivado, indisponível
        L4-->>API: {error: "Arquivo em Glacier",<br/>code: "GLACIER_UNAVAILABLE"}
        API-->>FE: Erro 409
        FE->>U: "Documento arquivado.<br/>Inicie uma restauração primeiro."

    else Restauração em andamento (ongoing-request=true)
        Note over L4: Restore solicitado, aguardando
        L4-->>API: {error: "Restauração em andamento",<br/>code: "RESTORE_IN_PROGRESS"}
        API-->>FE: Erro 409
        FE->>U: "Restauração em progresso.<br/>Tente novamente em algumas horas."

    else Restauração concluída (ongoing-request=false, expiry-date presente)
        Note over L4: Cópia temporária disponível
        L4->>S3: generate_presigned_url(GET)
        S3-->>L4: URL pré-assinada
        L4-->>API: {downloadUrl, expiresIn: 300}
        API-->>FE: Resposta JSON
        FE->>S3: GET via URL pré-assinada
        S3-->>FE: Arquivo (download direto)
    end
```

---

## 5. Diagrama de Versionamento

O S3 mantém todas as versões de um objeto quando o versionamento está habilitado. Isso permite recuperar versões anteriores.

```mermaid
sequenceDiagram
    participant U as 👤 Usuário
    participant S3 as 📦 S3 (Versionamento Habilitado)
    participant FE as 🖥️ Frontend
    participant API as 🔌 API Gateway
    participant L5 as ⚡ listar-versoes

    Note over U,S3: Upload da primeira versão
    U->>S3: PUT contrato.pdf (via pre-signed URL)
    S3->>S3: Armazena como Version ID: v1abc
    S3-->>U: 200 OK (x-amz-version-id: v1abc)

    Note over U,S3: Upload de nova versão (mesmo nome)
    U->>S3: PUT contrato.pdf (conteúdo atualizado)
    S3->>S3: Armazena como Version ID: v2def<br/>v1abc permanece como versão anterior
    S3-->>U: 200 OK (x-amz-version-id: v2def)

    Note over U,L5: Consultar versões disponíveis
    U->>FE: Clica em "Ver Versões"
    FE->>API: GET /versoes?key=processados/contratos/contrato.pdf
    API->>L5: Invoca Lambda
    L5->>S3: list_object_versions(Prefix=key)
    S3-->>L5: Lista de versões
    L5->>L5: Filtra delete markers
    L5-->>API: {versions: [{versionId: v2def, isLatest: true},<br/>{versionId: v1abc, isLatest: false}]}
    API-->>FE: Resposta JSON
    FE->>U: Exibe tabela de versões

    Note over U,S3: Download de versão específica
    U->>FE: Clica download na versão v1abc
    FE->>API: GET /download-url?key=...&versionId=v1abc
    API->>L5: Gera URL com versionId
    L5->>S3: generate_presigned_url(GET, VersionId=v1abc)
    S3-->>L5: URL pré-assinada para v1abc
    L5-->>FE: {downloadUrl}
    FE->>S3: GET versão anterior
    S3-->>FE: Conteúdo da versão v1abc
```

### Como o Versionamento Funciona no S3

| Conceito | Descrição |
|----------|-----------|
| **Version ID** | Identificador único gerado pelo S3 para cada versão de um objeto |
| **Versão atual** | A versão mais recente do objeto (retornada por GET sem versionId) |
| **Versão não-corrente** | Versões anteriores que ainda existem no bucket |
| **Delete Marker** | Marcador inserido ao "deletar" um objeto versionado (não apaga versões) |
| **Lifecycle** | Versões não-correntes podem ser expiradas automaticamente (ex: após 90 dias) |

---

## 6. Diagrama de Restauração Glacier

Objetos em classes Glacier não podem ser acessados diretamente. É necessário iniciar um processo de restauração que pode levar horas ou dias.

```mermaid
sequenceDiagram
    participant U as 👤 Usuário
    participant FE as 🖥️ Frontend
    participant API as 🔌 API Gateway
    participant L6 as ⚡ restaurar-documento
    participant S3 as 📦 S3 Documentos

    U->>FE: Clica "Restaurar" em documento Glacier
    FE->>API: POST /restaurar<br/>{key, tier: "Standard", days: 2}
    API->>L6: Invoca Lambda

    L6->>S3: head_object(key)
    S3-->>L6: StorageClass, Restore status

    alt StorageClass NÃO é Glacier/Deep Archive
        L6-->>FE: "Restauração não é necessária.<br/>Documento já está acessível."
    
    else Restauração já em andamento
        Note over L6: Header Restore: ongoing-request="true"
        L6-->>FE: "Restauração já em andamento.<br/>Aguarde a conclusão."

    else Documento em Glacier, sem restauração ativa
        L6->>S3: restore_object(<br/>  Key=key,<br/>  RestoreRequest={<br/>    Days: 2,<br/>    GlacierJobParameters: {Tier: "Standard"}<br/>  })
        S3-->>L6: 202 Accepted
        L6-->>API: {message: "Restauração iniciada",<br/>tier: "Standard", days: 2}
        API-->>FE: Resposta JSON
        FE->>U: "Restauração iniciada!<br/>Disponível em algumas horas."
    end

    Note over S3: ⏳ Tempo de restauração varia por tier
    Note over S3: Standard: 3-5h | Bulk: 5-12h | Expedited: 1-5min

    Note over U,S3: Após restauração concluída
    U->>FE: Tenta download novamente
    FE->>API: GET /download-url?key=...
    API->>L6: Verifica status
    L6->>S3: head_object(key)
    S3-->>L6: Restore: ongoing-request="false", expiry-date="..."
    Note over L6: Cópia temporária disponível por 2 dias
    L6->>S3: generate_presigned_url(GET)
    S3-->>L6: URL pré-assinada
    L6-->>FE: {downloadUrl}
    FE->>S3: Download do arquivo restaurado
```

### Tiers de Restauração

| Tier | Tempo de Recuperação | Custo | Caso de Uso |
|------|---------------------|-------|-------------|
| **Expedited** | 1–5 minutos | Alto | Urgências |
| **Standard** | 3–5 horas | Médio | Uso regular |
| **Bulk** | 5–12 horas | Baixo | Restaurações em lote |

> **Nota:** Expedited não está disponível para Deep Archive. A restauração deixa o objeto disponível temporariamente (padrão: 2 dias) sem alterar sua classe de armazenamento.

---

## 7. Diagrama de Lifecycle (Ciclo de Vida)

As regras de ciclo de vida automatizam a transição de objetos entre classes de armazenamento e sua expiração, otimizando custos.

```mermaid
timeline
    title Ciclo de Vida dos Documentos em processados/
    section Dia 0
        Upload : Documento armazenado em Standard
                : Acesso imediato, baixa latência
                : Custo mais alto por GB
    section Dia 30
        Transição 1 : Movido para Intelligent-Tiering
                    : S3 otimiza automaticamente
                    : Custo reduzido para acessos infrequentes
    section Dia 180
        Transição 2 : Movido para Glacier Flexible Retrieval
                    : Restauração necessária para acesso
                    : Custo muito baixo por GB
    section Dia 365
        Transição 3 : Movido para Glacier Deep Archive
                    : Menor custo de armazenamento
                    : Restauração leva horas
    section Dia 730
        Expiração : Objeto deletado permanentemente
                  : Versões não-correntes já expiradas (90 dias)
                  : Liberação total do espaço
```

### Regras Configuradas no Bucket

```mermaid
flowchart LR
    subgraph "Regra 1: arquivar-documentos-processados"
        direction LR
        A1[Standard] -->|30 dias| B1[Intelligent-Tiering]
        B1 -->|180 dias| C1[Glacier Flexible]
        C1 -->|365 dias| D1[Deep Archive]
        D1 -->|730 dias| E1[🗑️ Expirar]
    end

    subgraph "Regra 2: excluir-arquivos-temporarios"
        direction LR
        A2[temporarios/] -->|7 dias| B2[🗑️ Expirar versão atual]
        A2 -->|7 dias| C2[🗑️ Expirar não-correntes]
        A2 -->|1 dia| D2[🗑️ Abortar multipart]
    end

    subgraph "Regra 3: limpar-versoes-antigas"
        direction LR
        A3[processados/<br/>não-correntes] -->|90 dias| B3[🗑️ Expirar]
        A3 --> C3[🧹 Limpar delete markers expirados]
    end
```

| Regra | Prefixo | Ação | Dias |
|-------|---------|------|------|
| arquivar-documentos-processados | processados/ | Standard → IT | 30 |
| arquivar-documentos-processados | processados/ | IT → Glacier Flexible | 180 |
| arquivar-documentos-processados | processados/ | Glacier → Deep Archive | 365 |
| arquivar-documentos-processados | processados/ | Expirar objeto | 730 |
| excluir-arquivos-temporarios | temporarios/ | Expirar corrente | 7 |
| excluir-arquivos-temporarios | temporarios/ | Expirar não-corrente | 7 |
| excluir-arquivos-temporarios | temporarios/ | Abortar multipart | 1 |
| limpar-versoes-antigas | processados/ | Expirar não-correntes | 90 |
| limpar-versoes-antigas | processados/ | Limpar delete markers | — |

---

## 8. Explicação de Cada Componente

### 8.1 CloudFront + OAC (Origin Access Control)

**O que é:** CloudFront é a CDN (Content Delivery Network) da AWS. OAC é o mecanismo que permite ao CloudFront acessar buckets S3 privados sem torná-los públicos.

**Papel na arquitetura:**
- Serve o frontend estático (HTML, CSS, JS) globalmente com baixa latência
- É o único ponto de acesso ao Bucket Frontend (o bucket não aceita acesso direto)
- Redireciona HTTP para HTTPS automaticamente
- Faz cache dos arquivos estáticos para reduzir custos e latência

**Configuração principal:**
- Origin: Bucket Frontend com OAC
- Default Root Object: `index.html`
- Viewer Protocol Policy: Redirect HTTP to HTTPS
- Cache Policy: CachingOptimized

**Por que OAC e não OAI (Origin Access Identity)?**
OAC é a recomendação atual da AWS, substituindo OAI. Oferece suporte a SSE-KMS, funciona com todos os tipos de bucket e segue o modelo de permissões baseado em resource policy.

---

### 8.2 S3 Bucket Frontend

**O que é:** Bucket S3 dedicado a hospedar os arquivos estáticos da aplicação web.

**Papel na arquitetura:**
- Armazena `index.html`, `styles.css`, `app.js` e `config.js`
- Acesso exclusivamente via CloudFront (OAC)
- Nunca exposto diretamente à internet

**Configuração:**
| Propriedade | Valor |
|-------------|-------|
| Acesso público | ❌ Bloqueado (Block All Public Access) |
| Criptografia | SSE-S3 (AES-256) |
| Versionamento | Não necessário |
| Static Hosting | Desabilitado (CloudFront usa OAC, não website endpoint) |
| Bucket Policy | Permite apenas `s3:GetObject` do CloudFront via OAC |

---

### 8.3 S3 Bucket Documentos

**O que é:** Bucket principal que armazena todos os documentos do cofre digital, com versionamento habilitado e regras de ciclo de vida.

**Papel na arquitetura:**
- Armazena documentos em diferentes estágios (entrada, processados, rejeitados)
- Mantém histórico de versões de cada documento
- Aplica transições automáticas de classe de armazenamento
- Recebe uploads diretos via URLs pré-assinadas
- Emite eventos para processamento automático

**Configuração:**
| Propriedade | Valor |
|-------------|-------|
| Acesso público | ❌ Bloqueado (Block All Public Access) |
| Criptografia | SSE-S3 (AES-256) padrão |
| Versionamento | ✅ Habilitado |
| CORS | Configurado para domínio CloudFront |
| Bucket Policy | Deny se `aws:SecureTransport = false` |
| Event Notifications | ObjectCreated em `entrada/` → Lambda |
| Lifecycle Rules | 3 regras (ver seção 7) |

---

### 8.4 API Gateway HTTP API

**O que é:** Serviço gerenciado da AWS que expõe endpoints HTTP para invocar funções Lambda. Usamos HTTP API (não REST API) por ser mais simples, barata e adequada para este projeto.

**Papel na arquitetura:**
- Ponto de entrada para todas as operações do backend
- Roteia requisições para a Lambda correta
- Gerencia CORS automaticamente
- Não requer autenticação (projeto educacional)

**Rotas configuradas:**

| Método | Rota | Lambda Destino | Descrição |
|--------|------|----------------|-----------|
| POST | `/upload-url` | gerar-url-upload | Solicita URL para upload |
| GET | `/documentos` | listar-documentos | Lista documentos processados |
| GET | `/download-url` | gerar-url-download | Solicita URL para download |
| GET | `/versoes` | listar-versoes | Lista versões de um documento |
| POST | `/restaurar` | restaurar-documento | Inicia restauração Glacier |

**Configuração importante:**
- **Tipo:** HTTP API (v2) — mais leve que REST API
- **Payload Format Version:** 2.0 — formato simplificado do evento Lambda
- **Stage:** `$default` com auto-deploy habilitado
- **CORS:** Origin = `https://{cloudfront-domain}`, Methods = GET/POST/OPTIONS

---

### 8.5 Lambda Functions (6 funções)

**O que são:** Funções serverless que executam a lógica de negócio. Cada função tem uma responsabilidade única.

**Runtime:** Python 3.12 com boto3 (SDK AWS incluído nativamente no runtime Lambda)

| Função | Trigger | Operações S3 | Descrição |
|--------|---------|--------------|-----------|
| `gerar-url-upload` | API Gateway | PutObject (pre-signed) | Valida e gera URL para upload |
| `processar-documento` | S3 Event | Get, Copy, Delete, Tag | Classifica e roteia documentos |
| `listar-documentos` | API Gateway | ListObjects, GetTagging | Lista com metadados e tags |
| `gerar-url-download` | API Gateway | HeadObject, GetObject (pre-signed) | Verifica classe e gera URL |
| `listar-versoes` | API Gateway | ListObjectVersions | Retorna histórico de versões |
| `restaurar-documento` | API Gateway | HeadObject, RestoreObject | Inicia restauração Glacier |

**Módulos compartilhados** (em `lambdas/shared/`):
- `validation.py` — Validação de extensões, campos e sanitização
- `key_builder.py` — Construção e parsing de keys S3
- `response.py` — Formatação de respostas HTTP padronizadas

**Configuração de cada Lambda:**
- Memória: 128 MB (suficiente, não processa arquivos grandes)
- Timeout: 30 segundos
- Variáveis de ambiente: específicas por função (ver design.md)

---

### 8.6 IAM (Identity and Access Management)

**O que é:** Serviço que controla quem pode fazer o quê na AWS. Cada Lambda tem seu próprio Role com políticas de privilégio mínimo.

**Papel na arquitetura:**
- Garante que cada Lambda acesse apenas os recursos necessários
- Impede que uma Lambda comprometa operações de outra
- Trust Policy permite apenas `lambda.amazonaws.com` assumir o role

**Princípio de privilégio mínimo aplicado:**

| Lambda | Permissões S3 concedidas | Recurso restrito a |
|--------|--------------------------|-------------------|
| gerar-url-upload | `s3:PutObject` | `BUCKET/entrada/*` |
| processar-documento | `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:GetObjectTagging`, `s3:PutObjectTagging` | `BUCKET/entrada/*`, `BUCKET/processados/*`, `BUCKET/rejeitados/*` |
| listar-documentos | `s3:ListBucket`, `s3:GetObject`, `s3:GetObjectTagging` | `BUCKET` (list), `BUCKET/processados/*` |
| gerar-url-download | `s3:GetObject` | `BUCKET/processados/*` |
| listar-versoes | `s3:ListBucketVersions`, `s3:GetObject` | `BUCKET` |
| restaurar-documento | `s3:RestoreObject`, `s3:GetObject` | `BUCKET/processados/*` |

**Todas as Lambdas também possuem:**
- `logs:CreateLogGroup`
- `logs:CreateLogStream`
- `logs:PutLogEvents`

---

### 8.7 CloudWatch

**O que é:** Serviço de monitoramento e observabilidade da AWS. Recebe logs automaticamente de todas as funções Lambda.

**Papel na arquitetura:**
- Armazena logs de execução de todas as 6 Lambdas
- Permite debugar erros de processamento
- Registra request IDs para rastreabilidade
- Mantém métricas de invocação, duração e erros

**Logs gerados:**
- Início e fim de cada invocação
- Erros de validação (400)
- Erros de recurso não encontrado (404)
- Erros internos com stack trace (500)
- Key/filename envolvido em cada operação

**Log Groups criados automaticamente:**
- `/aws/lambda/gerar-url-upload`
- `/aws/lambda/processar-documento`
- `/aws/lambda/listar-documentos`
- `/aws/lambda/gerar-url-download`
- `/aws/lambda/listar-versoes`
- `/aws/lambda/restaurar-documento`

---

### 8.8 S3 Event Notifications

**O que é:** Mecanismo do S3 que dispara ações quando objetos são criados, deletados ou modificados.

**Papel na arquitetura:**
- Conecta o upload de documentos ao processamento automático
- Elimina necessidade de polling ou verificações manuais
- Garante processamento assíncrono e desacoplado

**Configuração:**
| Propriedade | Valor |
|-------------|-------|
| Tipo de evento | `s3:ObjectCreated:*` |
| Filtro de prefixo | `entrada/` |
| Destino | Lambda `processar-documento` |
| Tipo de destino | Lambda function |

**Importante:** O filtro de prefixo `entrada/` é a primeira barreira contra loops. Apenas objetos criados neste prefixo disparam o Lambda. Objetos copiados para `processados/` ou `rejeitados/` não geram eventos.

---

## 9. Estrutura de Prefixos do Bucket Documentos

> **Conceito importante:** O S3 não possui pastas ou diretórios reais. Ele é um armazenamento de objetos flat (plano). O que chamamos de "pastas" são prefixos no nome da key do objeto. O caractere `/` no nome da key é apenas uma convenção visual — para o S3, `processados/contratos/doc.pdf` é simplesmente uma key de texto.

### Tabela de Prefixos

| Prefixo | Propósito | Lifecycle | Quem escreve | Quem lê |
|---------|-----------|-----------|--------------|---------|
| `entrada/` | Área de recebimento de uploads | — (transitório) | gerar-url-upload (pre-signed) | processar-documento |
| `entrada/{categoria}/` | Subcategorias de upload | — | gerar-url-upload | processar-documento |
| `processados/` | Documentos validados e classificados | Standard→IT→Glacier→Deep→Expira | processar-documento | listar-documentos, gerar-url-download |
| `processados/{categoria}/` | Subcategorias processadas | Mesma regra do pai | processar-documento | listar-documentos |
| `rejeitados/` | Documentos com extensão inválida | — | processar-documento | (admin manual) |
| `temporarios/` | Arquivos efêmeros | Expira em 7 dias | (uso manual/lab) | — |
| `laboratorio/` | Área para prática educacional | — | (uso manual) | — |
| `laboratorio/standard/` | Demonstração classe Standard | — | (uso manual) | — |
| `laboratorio/intelligent-tiering/` | Demonstração IT | — | (uso manual) | — |
| `laboratorio/glacier-flexible/` | Demonstração Glacier | — | (uso manual) | — |
| `laboratorio/deep-archive/` | Demonstração Deep Archive | — | (uso manual) | — |

### Categorias Disponíveis

| Categoria | Exemplo de Key Completa |
|-----------|------------------------|
| `contratos` | `processados/contratos/contrato-locacao-2024.pdf` |
| `notas-fiscais` | `processados/notas-fiscais/nf-001234.pdf` |
| `relatorios` | `processados/relatorios/relatorio-mensal-jan.xlsx` |
| `comprovantes` | `processados/comprovantes/comprovante-pgto.png` |
| `outros` | `processados/outros/documento-geral.txt` |

### Como o S3 "Simula" Pastas

```
# Para o S3, estes são simplesmente nomes de objetos (keys):
processados/contratos/contrato.pdf      ← key completa do objeto
processados/contratos/aditivo.pdf       ← outro objeto independente
processados/notas-fiscais/nf-001.pdf    ← não tem relação hierárquica real

# O Console AWS e o list_objects_v2 com Delimiter="/" 
# apresentam como se fossem pastas, mas é apenas filtragem por prefixo.
```

---

## 10. Decisões de Segurança

### Por que OAC (Origin Access Control)?

| Aspecto | Decisão | Justificativa |
|---------|---------|---------------|
| Método | OAC em vez de OAI | OAI é legado (deprecated). OAC é a recomendação atual da AWS, suporta SSE-KMS, e funciona com Resource Policy padrão |
| Acesso ao bucket | Block All Public Access + Bucket Policy | O bucket frontend nunca é acessado diretamente. Mesmo se alguém descobrir o nome, não consegue acessar |
| Benefício educacional | Demonstra o padrão moderno | Estudantes aprendem a configuração recomendada desde o início |

### Por que URLs Pré-Assinadas?

| Aspecto | Decisão | Justificativa |
|---------|---------|---------------|
| Upload | Pre-signed PUT em vez de passar pelo Lambda | Arquivos de até 20MB não trafegam pelo API Gateway (limite de 10MB) nem pelo Lambda. Vai direto ao S3 |
| Download | Pre-signed GET em vez de proxy | Evita consumo de memória/banda do Lambda. O navegador baixa diretamente do S3 |
| Expiração | 5 minutos (300s) | Tempo suficiente para upload/download, mas curto para reduzir risco se URL vazar |
| Segurança | URL é temporária e específica | Cada URL funciona apenas para um objeto específico, com método específico, por tempo limitado |
| Sem credenciais expostas | Navegador não conhece access keys | As credenciais AWS ficam apenas no Lambda. O navegador usa a URL temporária |

### Por que SSE-S3 (Server-Side Encryption com S3-Managed Keys)?

| Aspecto | Decisão | Justificativa |
|---------|---------|---------------|
| Tipo | SSE-S3 em vez de SSE-KMS | SSE-S3 não tem custo adicional, não requer gerenciamento de chaves KMS, e atende requisitos de compliance básicos |
| Transparência | Criptografia automática | Não requer alteração no código. S3 criptografa ao gravar e descriptografa ao ler, transparente para as Lambdas |
| Simplicidade | Sem complexidade de KMS | Para um projeto educacional, SSE-S3 demonstra o conceito de encryption at rest sem overhead operacional |
| Padrão AWS | Default para novos buckets | Desde janeiro 2023, a AWS aplica SSE-S3 por padrão em todos os novos buckets |

### Por que Deny HTTP (Apenas HTTPS)?

| Aspecto | Decisão | Justificativa |
|---------|---------|---------------|
| Bucket Policy | Deny quando `aws:SecureTransport = false` | Garante que toda comunicação com o bucket é criptografada em trânsito |
| Proteção | Encryption in transit | Previne interceptação de dados (man-in-the-middle) e URLs pré-assinadas transmitidas em texto plano |
| Compliance | Boa prática de segurança | Recomendação AWS Well-Architected Framework e requisito em diversos frameworks de compliance |
| Implementação | Condition na Bucket Policy | Simples de implementar, aplica-se a todas as operações sem exceção |

### Resumo: Defesa em Profundidade

```mermaid
graph LR
    subgraph "Camadas de Segurança"
        A[🔒 Block Public Access<br/>Nenhum acesso público] --> B[🔒 Bucket Policy<br/>Deny HTTP]
        B --> C[🔒 OAC<br/>Só CloudFront acessa frontend]
        C --> D[🔒 Pre-signed URLs<br/>Acesso temporário e específico]
        D --> E[🔒 IAM Least Privilege<br/>Cada Lambda com mínimo]
        E --> F[🔒 SSE-S3<br/>Criptografia em repouso]
        F --> G[🔒 CORS<br/>Só domínio autorizado]
    end
```

Cada camada protege contra um vetor de ataque diferente. Se uma falha, as demais continuam protegendo:

1. **Block Public Access** — Impede qualquer configuração acidental de acesso público
2. **Bucket Policy (HTTPS only)** — Garante criptografia em trânsito
3. **OAC** — Restringe acesso ao frontend exclusivamente via CloudFront
4. **Pre-signed URLs** — Limita operações por tempo, método e objeto
5. **IAM Least Privilege** — Minimiza impacto se uma Lambda for comprometida
6. **SSE-S3** — Protege dados em repouso no disco
7. **CORS** — Impede requisições de origens não autorizadas

---

## Referências

- [AWS S3 User Guide](https://docs.aws.amazon.com/AmazonS3/latest/userguide/)
- [CloudFront OAC](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)
- [S3 Pre-signed URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)
- [S3 Lifecycle Configuration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- [AWS Well-Architected Framework — Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/)
