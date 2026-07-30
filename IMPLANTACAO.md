# Guia de Implantação — Cofre Digital de Documentos com Amazon S3

> **Documento passo a passo para criação de TODOS os recursos via Console AWS.**  
> Escrito para quem nunca usou o Console AWS antes. Cada etapa indica o serviço, menu, botão, campo, valor exato e resultado esperado.

---

## Placeholders Utilizados Neste Documento

| Placeholder | Descrição | Exemplo |
|-------------|-----------|---------|
| `<AWS_ACCOUNT_ID>` | ID numérico de 12 dígitos da sua conta AWS | `123456789012` |
| `<AWS_REGION>` | Região AWS selecionada (recomendado: `us-east-1`) | `us-east-1` |
| `<BUCKET_DOCUMENTOS>` | Nome do bucket de documentos | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` |
| `<BUCKET_FRONTEND>` | Nome do bucket do frontend | `cofre-documentos-frontend-<AWS_ACCOUNT_ID>` |
| `<DOMINIO_CLOUDFRONT>` | Domínio da distribuição CloudFront | `dXXXXXXXXXXXXX.cloudfront.net` |
| `<API_GATEWAY_URL>` | URL de invocação da API Gateway | `https://xxxxxxxxxx.execute-api.<AWS_REGION>.amazonaws.com` |
| `<DISTRIBUTION_ID>` | ID da distribuição CloudFront | `E1A2B3C4D5E6F7` |

> **Dica:** Antes de começar, abra um editor de texto (Notepad, VS Code, etc.) e crie um arquivo `meus-recursos.txt` para anotar cada ARN, URL e ID gerado durante a implantação.

---

## Pré-requisitos

### 1. Conta AWS Ativa

- Acesse [https://aws.amazon.com](https://aws.amazon.com)
- Se não possui conta, clique em **Criar uma conta da AWS** e siga o processo de cadastro
- Você precisará de: e-mail válido, cartão de crédito/débito (para verificação), número de telefone
- Após criação, aguarde a ativação (pode levar até 24h, mas geralmente é instantâneo)

### 2. Seleção de Região

- No canto superior direito do Console AWS, clique no nome da região atual
- Selecione **US East (N. Virginia) us-east-1** (recomendado por ter todos os serviços e menor latência para testes)
- **IMPORTANTE:** Mantenha a mesma região em TODAS as etapas. Trocar de região fará com que recursos fiquem invisíveis entre si

### 3. Usuário IAM com Acesso Administrativo

> Se você está usando a conta root (e-mail de cadastro), pule esta seção. Para produção, recomenda-se criar um usuário IAM.

- Acesse **IAM** (digite "IAM" na barra de busca superior e clique no serviço)
- No menu lateral esquerdo, clique em **Users** (Usuários)
- Clique no botão **Create user** (Criar usuário)
- **User name**: `admin-cofre-digital`
- Marque ✅ **Provide user access to the AWS Management Console**
- Selecione **I want to create an IAM user**
- **Console password**: Selecione **Custom password** e defina uma senha forte
- Desmarque ☐ **Users must create a new password at next sign-in**
- Clique em **Next**
- Na tela de permissões, selecione **Attach policies directly**
- Na busca, digite `AdministratorAccess` e marque ✅ a política **AdministratorAccess**
- Clique em **Next** → **Create user**
- **Anote** a URL de login do console (formato: `https://<AWS_ACCOUNT_ID>.signin.aws.amazon.com/console`)
- Faça logout da conta root e login com o usuário IAM criado

### 4. Obter o Account ID

- No canto superior direito, clique no nome do seu usuário/conta
- O **Account ID** (12 dígitos) aparece no menu dropdown
- **Anote** este número — será usado em todos os nomes de recursos como `<AWS_ACCOUNT_ID>`

---

## Etapa 1: Criar Bucket de Documentos

Este bucket armazenará todos os documentos do cofre digital (uploads, processados, rejeitados, temporários e laboratório).

### Passo a passo

1. Na barra de busca superior do Console AWS, digite **S3** e clique no serviço **S3**
2. Clique no botão laranja **Create bucket** (Criar bucket)
3. Preencha os campos conforme abaixo:

| Campo | Valor |
|-------|-------|
| **Bucket name** | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` (substitua pelo seu ID de 12 dígitos) |
| **AWS Region** | `US East (N. Virginia) us-east-1` (deve já estar selecionada) |

4. **Object Ownership**: Mantenha selecionado **ACLs disabled (recommended)** — Bucket owner enforced
   - Isso garante que apenas o dono do bucket controla acesso via políticas

5. **Block Public Access settings for this bucket**:
   - Mantenha ✅ marcado **Block *all* public access**
   - Este bucket NUNCA deve ser público — acesso será apenas via Lambda e URLs pré-assinadas

6. **Bucket Versioning**:
   - Selecione ✅ **Enable**
   - Isso permite manter histórico de versões dos documentos

7. **Tags** (opcional mas recomendado):
   - Clique em **Add tag**
   - Key: `projeto` | Value: `cofre-digital`
   - Clique em **Add tag** novamente
   - Key: `ambiente` | Value: `educacional`

8. **Default encryption**:
   - **Encryption type**: Selecione **Server-side encryption with Amazon S3 managed keys (SSE-S3)**
   - **Bucket Key**: Mantenha **Enable** selecionado (reduz custos de criptografia)

9. Clique no botão laranja **Create bucket** no final da página

### Verificação

- Você será redirecionado para a lista de buckets
- O bucket `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` deve aparecer na lista
- Clique no nome do bucket para abri-lo
- Verifique na aba **Properties**: Versioning está **Enabled**, Encryption mostra **SSE-S3**
- Verifique na aba **Permissions**: Block public access mostra **On** para todos os 4 itens

### Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| "Bucket name already exists" | Nomes de bucket são globais na AWS | Verifique se digitou seu Account ID corretamente |
| "Bucket name is not valid" | Caracteres inválidos no nome | Use apenas letras minúsculas, números e hífens |

### Anote

- **Nome do bucket**: `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>`
- **ARN do bucket**: `arn:aws:s3:::cofre-documentos-arquivos-<AWS_ACCOUNT_ID>`
- Estes valores serão usados nas políticas IAM (Etapa 5) e nas variáveis de ambiente das Lambdas (Etapa 7)

---

## Etapa 2: Configurar CORS do Bucket de Documentos

O CORS (Cross-Origin Resource Sharing) permite que o navegador do usuário envie e receba arquivos diretamente do S3 via URLs pré-assinadas. Sem esta configuração, o upload/download via navegador será bloqueado.

### Passo a passo

1. No Console S3, clique no bucket **cofre-documentos-arquivos-<AWS_ACCOUNT_ID>**
2. Clique na aba **Permissions** (Permissões)
3. Role a página até a seção **Cross-origin resource sharing (CORS)**
4. Clique no botão **Edit** (Editar)
5. Apague qualquer conteúdo existente no campo de texto
6. Cole o JSON abaixo (é o conteúdo do arquivo `s3/cors-documentos.json` deste repositório):

```json
[
    {
        "AllowedHeaders": [
            "*"
        ],
        "AllowedMethods": [
            "PUT",
            "GET",
            "HEAD"
        ],
        "AllowedOrigins": [
            "https://<DOMINIO_CLOUDFRONT>"
        ],
        "ExposeHeaders": [
            "ETag",
            "x-amz-version-id"
        ],
        "MaxAgeSeconds": 3000
    }
]
```

> **ATENÇÃO:** Neste momento, você ainda não tem o domínio CloudFront (será criado na Etapa 12). Por enquanto, use `"https://placeholder.cloudfront.net"` como valor temporário. Na **Etapa 14**, você voltará aqui para substituir pelo domínio real.

7. Clique no botão laranja **Save changes** (Salvar alterações)

### Explicação dos campos

| Campo | Significado |
|-------|-------------|
| `AllowedHeaders: ["*"]` | Aceita qualquer header na requisição (necessário para Content-Type e metadados) |
| `AllowedMethods: ["PUT", "GET", "HEAD"]` | Permite upload (PUT), download (GET) e verificação (HEAD) |
| `AllowedOrigins` | Domínio que pode fazer requisições — será o CloudFront do frontend |
| `ExposeHeaders: ["ETag", "x-amz-version-id"]` | Permite que o navegador leia esses headers da resposta do S3 |
| `MaxAgeSeconds: 3000` | Navegador pode cachear a resposta do preflight (OPTIONS) por 50 minutos |

### Verificação

- Após salvar, a seção CORS deve exibir o JSON configurado
- Se mostrar "No CORS configuration", algo deu errado — tente novamente

### Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| "MalformedXML" ou erro de parse | JSON com formato inválido | Verifique vírgulas, aspas e colchetes |
| CORS não aparece após salvar | Cache do navegador | Faça refresh (F5) na página |

---

## Etapa 3: Aplicar Bucket Policy (HTTPS Obrigatório)

Esta política nega qualquer operação S3 que não utilize HTTPS, garantindo que todo o tráfego seja criptografado em trânsito.

### Passo a passo

1. No Console S3, clique no bucket **cofre-documentos-arquivos-<AWS_ACCOUNT_ID>**
2. Clique na aba **Permissions** (Permissões)
3. Role até a seção **Bucket policy**
4. Clique no botão **Edit** (Editar)
5. Apague qualquer conteúdo existente no campo de texto
6. Cole o JSON abaixo (é o conteúdo do arquivo `s3/bucket-policy-documentos.json` deste repositório):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "DenyInsecureTransport",
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:*",
            "Resource": [
                "arn:aws:s3:::cofre-documentos-arquivos-<AWS_ACCOUNT_ID>",
                "arn:aws:s3:::cofre-documentos-arquivos-<AWS_ACCOUNT_ID>/*"
            ],
            "Condition": {
                "Bool": {
                    "aws:SecureTransport": "false"
                }
            }
        }
    ]
}
```

7. **IMPORTANTE:** Substitua `<AWS_ACCOUNT_ID>` pelo seu ID de 12 dígitos nos dois campos `Resource`
8. Clique no botão laranja **Save changes** (Salvar alterações)

### Explicação da política

| Elemento | Significado |
|----------|-------------|
| `Effect: Deny` | Nega a ação |
| `Principal: *` | Aplica a qualquer identidade (usuários, roles, serviços) |
| `Action: s3:*` | Qualquer operação S3 |
| `Resource` | O bucket e todos os objetos dentro dele (`/*`) |
| `Condition: aws:SecureTransport = false` | Aplica a condição apenas quando a requisição NÃO usa HTTPS |

**Resultado:** Qualquer tentativa de acessar o bucket via HTTP (sem TLS) será negada.

### Verificação

- Após salvar, a seção Bucket policy deve exibir o JSON da política
- O banner amarelo "Bucket and objects not public" deve continuar aparecendo (a política não torna público)

### Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| "Invalid principal in policy" | Erro de digitação no Principal | Deve ser exatamente `"*"` (com aspas) |
| "Policy has invalid resource" | ARN do bucket incorreto | Verifique que o nome do bucket está correto no Resource |
| "MalformedPolicy" | JSON inválido | Valide o JSON em [jsonlint.com](https://jsonlint.com) |

---

## Etapa 4: Criar Prefixos (Estrutura de Pastas)

No S3, "pastas" são na verdade prefixos de objetos. Vamos criar a estrutura organizacional do bucket criando objetos vazios com `/` no final (que o Console exibe como pastas).

### Passo a passo

1. No Console S3, clique no bucket **cofre-documentos-arquivos-<AWS_ACCOUNT_ID>**
2. Você está na aba **Objects** (Objetos)
3. Clique no botão **Create folder** (Criar pasta)

### Criar pasta: `entrada/`

4. No campo **Folder name**, digite: `entrada`
5. **Server-side encryption**: Mantenha **Do not specify an encryption key** (herda do bucket)
6. Clique em **Create folder**

### Criar subpastas dentro de `entrada/`

7. Clique na pasta **entrada/** que acabou de aparecer
8. Agora você está dentro de `entrada/`. Clique em **Create folder**
9. **Folder name**: `contratos` → Clique **Create folder**
10. Clique em **Create folder** novamente
11. **Folder name**: `notas-fiscais` → Clique **Create folder**
12. Repita para: `relatorios`, `comprovantes`, `outros`

### Criar pasta: `processados/`

13. Navegue de volta à raiz do bucket clicando no nome do bucket no breadcrumb (trilha de navegação no topo)
14. Clique em **Create folder**
15. **Folder name**: `processados` → Clique **Create folder**
16. Clique na pasta **processados/**
17. Crie as mesmas subpastas: `contratos`, `notas-fiscais`, `relatorios`, `comprovantes`, `outros`

### Criar pasta: `rejeitados/`

18. Volte à raiz do bucket
19. Clique em **Create folder**
20. **Folder name**: `rejeitados` → Clique **Create folder**

### Criar pasta: `temporarios/`

21. Clique em **Create folder**
22. **Folder name**: `temporarios` → Clique **Create folder**

### Criar pasta: `laboratorio/`

23. Clique em **Create folder**
24. **Folder name**: `laboratorio` → Clique **Create folder**
25. Clique na pasta **laboratorio/**
26. Crie as subpastas: `standard`, `intelligent-tiering`, `glacier-flexible`, `deep-archive`

### Estrutura final

Após concluir, a raiz do bucket deve mostrar:

```
entrada/
├── contratos/
├── notas-fiscais/
├── relatorios/
├── comprovantes/
└── outros/
processados/
├── contratos/
├── notas-fiscais/
├── relatorios/
├── comprovantes/
└── outros/
rejeitados/
temporarios/
laboratorio/
├── standard/
├── intelligent-tiering/
├── glacier-flexible/
└── deep-archive/
```

### Verificação

- Na raiz do bucket, você deve ver 5 "pastas": entrada/, processados/, rejeitados/, temporarios/, laboratorio/
- Clique em cada uma para verificar que as subpastas foram criadas corretamente

### Nota importante

> O S3 não possui "pastas" reais. Cada "pasta" é um objeto de 0 bytes com o nome terminando em `/`. Quando a Lambda cria objetos com prefixos como `processados/contratos/arquivo.pdf`, a "pasta" aparece automaticamente — mas criá-las antecipadamente ajuda na organização visual.

---

## Etapa 5: Criar Políticas IAM

Cada função Lambda terá sua própria política IAM com permissões mínimas (princípio do menor privilégio). Nesta etapa, criaremos 6 políticas customizadas.

### Passo a passo geral

1. Na barra de busca superior, digite **IAM** e clique no serviço **IAM**
2. No menu lateral esquerdo, clique em **Policies** (Políticas)
3. Clique no botão **Create policy** (Criar política)

---

### Política 1: `cofre-policy-gerar-url-upload`

4. Na tela de criação, clique na aba **JSON** (ao lado de Visual)
5. Apague o conteúdo padrão e cole o JSON abaixo (arquivo `iam/gerar-url-upload-policy.json`):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowPutObjectEntrada",
            "Effect": "Allow",
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::cofre-documentos-arquivos-<AWS_ACCOUNT_ID>/entrada/*"
        },
        {
            "Sid": "AllowCloudWatchLogs",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:<AWS_REGION>:<AWS_ACCOUNT_ID>:log-group:/aws/lambda/cofre-gerar-url-upload:*"
        }
    ]
}
```

6. **Substitua** `<AWS_ACCOUNT_ID>` pelo seu ID de 12 dígitos (aparece 2 vezes)
7. **Substitua** `<AWS_REGION>` por `us-east-1` (ou sua região escolhida)
8. Clique em **Next** (Próximo)
9. No campo **Policy name**: digite `cofre-policy-gerar-url-upload`
10. No campo **Description**: digite `Permite upload de objetos no prefixo entrada/ e logs no CloudWatch`
11. Em **Tags**, adicione: Key: `projeto` | Value: `cofre-digital`
12. Clique em **Create policy** (Criar política)

---

### Política 2: `cofre-policy-processar-documento`

13. Volte para **Policies** → **Create policy** → aba **JSON**
14. Cole o JSON (arquivo `iam/processar-documento-policy.json`):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowReadEntrada",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:GetObjectTagging",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::cofre-documentos-arquivos-<AWS_ACCOUNT_ID>/entrada/*"
        },
        {
            "Sid": "AllowWriteProcessados",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:PutObjectTagging"
            ],
            "Resource": "arn:aws:s3:::cofre-documentos-arquivos-<AWS_ACCOUNT_ID>/processados/*"
        },
        {
            "Sid": "AllowWriteRejeitados",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:PutObjectTagging"
            ],
            "Resource": "arn:aws:s3:::cofre-documentos-arquivos-<AWS_ACCOUNT_ID>/rejeitados/*"
        },
        {
            "Sid": "AllowCloudWatchLogs",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:<AWS_REGION>:<AWS_ACCOUNT_ID>:log-group:/aws/lambda/cofre-processar-documento:*"
        }
    ]
}
```

15. **Substitua** `<AWS_ACCOUNT_ID>` (aparece 4 vezes) e `<AWS_REGION>` (1 vez)
16. Clique em **Next**
17. **Policy name**: `cofre-policy-processar-documento`
18. **Description**: `Permite ler/deletar da entrada, escrever em processados e rejeitados, e logs`
19. Clique em **Create policy**

---

### Política 3: `cofre-policy-listar-documentos`

20. **Policies** → **Create policy** → aba **JSON**
21. Cole o JSON (arquivo `iam/listar-documentos-policy.json`):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowListBucket",
            "Effect": "Allow",
            "Action": "s3:ListBucket",
            "Resource": "arn:aws:s3:::cofre-documentos-arquivos-<AWS_ACCOUNT_ID>",
            "Condition": {
                "StringLike": {
                    "s3:prefix": "processados/*"
                }
            }
        },
        {
            "Sid": "AllowReadProcessados",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:GetObjectTagging"
            ],
            "Resource": "arn:aws:s3:::cofre-documentos-arquivos-<AWS_ACCOUNT_ID>/processados/*"
        },
        {
            "Sid": "AllowCloudWatchLogs",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:<AWS_REGION>:<AWS_ACCOUNT_ID>:log-group:/aws/lambda/cofre-listar-documentos:*"
        }
    ]
}
```

22. **Substitua** `<AWS_ACCOUNT_ID>` (3 vezes) e `<AWS_REGION>` (1 vez)
23. **Next** → **Policy name**: `cofre-policy-listar-documentos`
24. **Description**: `Permite listar bucket no prefixo processados/ e ler objetos e tags`
25. **Create policy**

---

### Política 4: `cofre-policy-gerar-url-download`

26. **Policies** → **Create policy** → aba **JSON**
27. Cole o JSON (arquivo `iam/gerar-url-download-policy.json`):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowGetObjectProcessados",
            "Effect": "Allow",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::cofre-documentos-arquivos-<AWS_ACCOUNT_ID>/processados/*"
        },
        {
            "Sid": "AllowCloudWatchLogs",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:<AWS_REGION>:<AWS_ACCOUNT_ID>:log-group:/aws/lambda/cofre-gerar-url-download:*"
        }
    ]
}
```

28. **Substitua** os placeholders
29. **Next** → **Policy name**: `cofre-policy-gerar-url-download`
30. **Description**: `Permite leitura de objetos em processados/ para geração de URL de download`
31. **Create policy**

---

### Política 5: `cofre-policy-listar-versoes`

32. **Policies** → **Create policy** → aba **JSON**
33. Cole o JSON (arquivo `iam/listar-versoes-policy.json`):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowListBucketVersions",
            "Effect": "Allow",
            "Action": "s3:ListBucketVersions",
            "Resource": "arn:aws:s3:::cofre-documentos-arquivos-<AWS_ACCOUNT_ID>",
            "Condition": {
                "StringLike": {
                    "s3:prefix": "processados/*"
                }
            }
        },
        {
            "Sid": "AllowGetObjectVersions",
            "Effect": "Allow",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::cofre-documentos-arquivos-<AWS_ACCOUNT_ID>/processados/*"
        },
        {
            "Sid": "AllowCloudWatchLogs",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:<AWS_REGION>:<AWS_ACCOUNT_ID>:log-group:/aws/lambda/cofre-listar-versoes:*"
        }
    ]
}
```

34. **Substitua** os placeholders
35. **Next** → **Policy name**: `cofre-policy-listar-versoes`
36. **Description**: `Permite listar versões de objetos em processados/`
37. **Create policy**

---

### Política 6: `cofre-policy-restaurar-documento`

38. **Policies** → **Create policy** → aba **JSON**
39. Cole o JSON (arquivo `iam/restaurar-documento-policy.json`):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowRestoreObject",
            "Effect": "Allow",
            "Action": [
                "s3:RestoreObject",
                "s3:GetObject"
            ],
            "Resource": "arn:aws:s3:::cofre-documentos-arquivos-<AWS_ACCOUNT_ID>/processados/*"
        },
        {
            "Sid": "AllowCloudWatchLogs",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:<AWS_REGION>:<AWS_ACCOUNT_ID>:log-group:/aws/lambda/cofre-restaurar-documento:*"
        }
    ]
}
```

40. **Substitua** os placeholders
41. **Next** → **Policy name**: `cofre-policy-restaurar-documento`
42. **Description**: `Permite restaurar objetos Glacier e ler objetos em processados/`
43. **Create policy**

### Verificação

- No menu **Policies**, use o filtro **Customer managed** (políticas gerenciadas pelo cliente)
- Você deve ver 6 políticas começando com `cofre-policy-`:
  1. `cofre-policy-gerar-url-upload`
  2. `cofre-policy-processar-documento`
  3. `cofre-policy-listar-documentos`
  4. `cofre-policy-gerar-url-download`
  5. `cofre-policy-listar-versoes`
  6. `cofre-policy-restaurar-documento`

### Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| "MalformedPolicyDocument" | JSON inválido | Valide em [jsonlint.com](https://jsonlint.com) |
| "A policy with this name already exists" | Nome duplicado | Verifique se não criou duas vezes |
| "Invalid ARN" | ARN mal formatado | Verifique que o Account ID tem 12 dígitos e a região está correta |

---

## Etapa 6: Criar Roles IAM

Cada função Lambda precisa de um IAM Role (papel) que define com qual identidade ela executa. O Role combina uma trust policy (quem pode assumir o papel) com as políticas de permissão criadas na Etapa 5.

### Passo a passo geral

1. No Console IAM, no menu lateral esquerdo, clique em **Roles** (Funções)
2. Clique no botão **Create role** (Criar função)

---

### Role 1: `cofre-role-gerar-url-upload`

3. **Select trusted entity** (Selecionar entidade confiável):
   - Tipo: Selecione **AWS service**
   - **Use case**: Na seção "Use cases for other AWS services", no dropdown, selecione **Lambda**
   - Clique em **Next**

4. **Add permissions** (Adicionar permissões):
   - Na barra de busca, digite `cofre-policy-gerar-url-upload`
   - Marque ✅ a política **cofre-policy-gerar-url-upload**
   - Clique em **Next**

5. **Name, review, and create**:
   - **Role name**: `cofre-role-gerar-url-upload`
   - **Description**: `Role para a Lambda que gera URLs pré-assinadas de upload`
   - Em **Tags**, adicione: Key: `projeto` | Value: `cofre-digital`
   - Clique em **Create role**

6. **Anote o ARN do role** (aparece na confirmação): `arn:aws:iam::<AWS_ACCOUNT_ID>:role/cofre-role-gerar-url-upload`

---

### Role 2: `cofre-role-processar-documento`

7. **Roles** → **Create role**
8. **Trusted entity**: AWS service → Lambda → **Next**
9. **Permissions**: Busque `cofre-policy-processar-documento` → Marque ✅ → **Next**
10. **Role name**: `cofre-role-processar-documento`
11. **Description**: `Role para a Lambda que processa documentos enviados`
12. **Create role**

---

### Role 3: `cofre-role-listar-documentos`

13. **Roles** → **Create role**
14. **Trusted entity**: AWS service → Lambda → **Next**
15. **Permissions**: Busque `cofre-policy-listar-documentos` → Marque ✅ → **Next**
16. **Role name**: `cofre-role-listar-documentos`
17. **Description**: `Role para a Lambda que lista documentos processados`
18. **Create role**

---

### Role 4: `cofre-role-gerar-url-download`

19. **Roles** → **Create role**
20. **Trusted entity**: AWS service → Lambda → **Next**
21. **Permissions**: Busque `cofre-policy-gerar-url-download` → Marque ✅ → **Next**
22. **Role name**: `cofre-role-gerar-url-download`
23. **Description**: `Role para a Lambda que gera URLs pré-assinadas de download`
24. **Create role**

---

### Role 5: `cofre-role-listar-versoes`

25. **Roles** → **Create role**
26. **Trusted entity**: AWS service → Lambda → **Next**
27. **Permissions**: Busque `cofre-policy-listar-versoes` → Marque ✅ → **Next**
28. **Role name**: `cofre-role-listar-versoes`
29. **Description**: `Role para a Lambda que lista versões de documentos`
30. **Create role**

---

### Role 6: `cofre-role-restaurar-documento`

31. **Roles** → **Create role**
32. **Trusted entity**: AWS service → Lambda → **Next**
33. **Permissions**: Busque `cofre-policy-restaurar-documento` → Marque ✅ → **Next**
34. **Role name**: `cofre-role-restaurar-documento`
35. **Description**: `Role para a Lambda que restaura documentos Glacier`
36. **Create role**

---

### Verificação

- No menu **Roles**, busque `cofre-role`
- Você deve ver 6 roles:
  1. `cofre-role-gerar-url-upload`
  2. `cofre-role-processar-documento`
  3. `cofre-role-listar-documentos`
  4. `cofre-role-gerar-url-download`
  5. `cofre-role-listar-versoes`
  6. `cofre-role-restaurar-documento`
- Clique em qualquer role e verifique:
  - Na aba **Trust relationships**: A trust policy deve mostrar `lambda.amazonaws.com`
  - Na aba **Permissions**: A política customizada deve estar listada

### Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| Política não aparece na busca | Nome digitado errado | Use o filtro "Customer managed" e busque novamente |
| "1 validation error detected" | Role name com caracteres inválidos | Use apenas letras, números e hífens |

---

## Etapa 7: Criar Funções Lambda

Nesta etapa, criaremos as 6 funções Lambda que compõem o backend do Cofre Digital. Cada função usa Python 3.12 e o código-fonte está no diretório `lambdas/` deste repositório.

### Estrutura dos arquivos Lambda no repositório

```
lambdas/
├── shared/                          ← Módulo compartilhado (copiar para cada Lambda)
│   ├── __init__.py
│   ├── validation.py
│   ├── key_builder.py
│   └── response.py
├── gerar_url_upload/
│   └── lambda_function.py
├── processar_documento/
│   └── lambda_function.py
├── listar_documentos/
│   └── lambda_function.py
├── gerar_url_download/
│   └── lambda_function.py
├── listar_versoes/
│   └── lambda_function.py
└── restaurar_documento/
│   └── lambda_function.py
```

> **IMPORTANTE:** Cada função Lambda precisa do módulo `shared/` junto com seu código. Ao fazer upload, você precisará incluir tanto o `lambda_function.py` quanto a pasta `shared/` em um arquivo ZIP.

### Como preparar o arquivo ZIP para cada Lambda

Para cada função Lambda, faça o seguinte no seu computador:

1. Crie uma pasta temporária (ex: `deploy-gerar-url-upload/`)
2. Copie o arquivo `lambdas/gerar_url_upload/lambda_function.py` para dentro dela
3. Copie a pasta `lambdas/shared/` inteira para dentro dela
4. Selecione **todos os arquivos dentro** da pasta (NÃO a pasta em si)
5. Crie um arquivo ZIP com esses itens (lambda_function.py + shared/)
6. O ZIP resultante deve ter esta estrutura:
   ```
   lambda_function.py
   shared/
   ├── __init__.py
   ├── validation.py
   ├── key_builder.py
   └── response.py
   ```

> **Dica no Windows:** Selecione os arquivos → Botão direito → Enviar para → Pasta compactada (zip)  
> **Dica no Mac/Linux:** `cd deploy-gerar-url-upload && zip -r ../gerar-url-upload.zip .`

---

### Lambda 1: `cofre-gerar-url-upload`

1. Na barra de busca superior, digite **Lambda** e clique no serviço **Lambda**
2. Verifique que a região no canto superior direito é **us-east-1**
3. Clique no botão **Create function** (Criar função)
4. Selecione **Author from scratch** (Criar do zero)
5. Preencha:

| Campo | Valor |
|-------|-------|
| **Function name** | `cofre-gerar-url-upload` |
| **Runtime** | `Python 3.12` |
| **Architecture** | `x86_64` |

6. Expanda a seção **Change default execution role** (Alterar role de execução padrão):
   - Selecione **Use an existing role** (Usar uma role existente)
   - No dropdown **Existing role**, selecione `cofre-role-gerar-url-upload`

7. Clique em **Create function**

8. Na página da função criada, na seção **Code source**:
   - Clique no dropdown **Upload from** (Carregar de)
   - Selecione **.zip file**
   - Clique em **Upload** e selecione o arquivo ZIP preparado (com lambda_function.py + shared/)
   - Clique em **Save**

9. Na aba **Configuration** (Configuração), clique em **Environment variables** (Variáveis de ambiente) no menu lateral:
   - Clique em **Edit** (Editar)
   - Clique em **Add environment variable** para cada variável abaixo:

| Key | Value |
|-----|-------|
| `DOCUMENT_BUCKET` | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` |
| `UPLOAD_PREFIX` | `entrada` |
| `URL_EXPIRATION_SECONDS` | `300` |
| `MAX_FILE_SIZE_MB` | `20` |

   - Clique em **Save**

10. Na aba **Configuration**, clique em **General configuration** (Configuração geral):
    - Clique em **Edit**
    - **Memory**: `128` MB
    - **Timeout**: `0` min `30` sec
    - Clique em **Save**

---

### Lambda 2: `cofre-processar-documento`

11. **Lambda** → **Create function** → **Author from scratch**
12. Preencha:

| Campo | Valor |
|-------|-------|
| **Function name** | `cofre-processar-documento` |
| **Runtime** | `Python 3.12` |
| **Architecture** | `x86_64` |
| **Existing role** | `cofre-role-processar-documento` |

13. **Create function**
14. Upload do ZIP (lambda_function.py da pasta `processar_documento` + shared/)
15. **Configuration** → **Environment variables** → **Edit**:

| Key | Value |
|-----|-------|
| `DOCUMENT_BUCKET` | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` |
| `SOURCE_PREFIX` | `entrada` |
| `PROCESSED_PREFIX` | `processados` |
| `REJECTED_PREFIX` | `rejeitados` |

16. **Save**
17. **General configuration** → Memory: `128` MB, Timeout: `30` sec → **Save**

---

### Lambda 3: `cofre-listar-documentos`

18. **Lambda** → **Create function** → **Author from scratch**
19. Preencha:

| Campo | Valor |
|-------|-------|
| **Function name** | `cofre-listar-documentos` |
| **Runtime** | `Python 3.12` |
| **Architecture** | `x86_64` |
| **Existing role** | `cofre-role-listar-documentos` |

20. **Create function**
21. Upload do ZIP (lambda_function.py da pasta `listar_documentos` + shared/)
22. **Configuration** → **Environment variables** → **Edit**:

| Key | Value |
|-----|-------|
| `DOCUMENT_BUCKET` | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` |
| `PROCESSED_PREFIX` | `processados` |

23. **Save**
24. **General configuration** → Memory: `128` MB, Timeout: `30` sec → **Save**

---

### Lambda 4: `cofre-gerar-url-download`

25. **Lambda** → **Create function** → **Author from scratch**
26. Preencha:

| Campo | Valor |
|-------|-------|
| **Function name** | `cofre-gerar-url-download` |
| **Runtime** | `Python 3.12` |
| **Architecture** | `x86_64` |
| **Existing role** | `cofre-role-gerar-url-download` |

27. **Create function**
28. Upload do ZIP (lambda_function.py da pasta `gerar_url_download` + shared/)
29. **Configuration** → **Environment variables** → **Edit**:

| Key | Value |
|-----|-------|
| `DOCUMENT_BUCKET` | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` |
| `PROCESSED_PREFIX` | `processados` |
| `URL_EXPIRATION_SECONDS` | `300` |

30. **Save**
31. **General configuration** → Memory: `128` MB, Timeout: `30` sec → **Save**

---

### Lambda 5: `cofre-listar-versoes`

32. **Lambda** → **Create function** → **Author from scratch**
33. Preencha:

| Campo | Valor |
|-------|-------|
| **Function name** | `cofre-listar-versoes` |
| **Runtime** | `Python 3.12` |
| **Architecture** | `x86_64` |
| **Existing role** | `cofre-role-listar-versoes` |

34. **Create function**
35. Upload do ZIP (lambda_function.py da pasta `listar_versoes` + shared/)
36. **Configuration** → **Environment variables** → **Edit**:

| Key | Value |
|-----|-------|
| `DOCUMENT_BUCKET` | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` |
| `PROCESSED_PREFIX` | `processados` |
| `URL_EXPIRATION_SECONDS` | `300` |

37. **Save**
38. **General configuration** → Memory: `128` MB, Timeout: `30` sec → **Save**

---

### Lambda 6: `cofre-restaurar-documento`

39. **Lambda** → **Create function** → **Author from scratch**
40. Preencha:

| Campo | Valor |
|-------|-------|
| **Function name** | `cofre-restaurar-documento` |
| **Runtime** | `Python 3.12` |
| **Architecture** | `x86_64` |
| **Existing role** | `cofre-role-restaurar-documento` |

41. **Create function**
42. Upload do ZIP (lambda_function.py da pasta `restaurar_documento` + shared/)
43. **Configuration** → **Environment variables** → **Edit**:

| Key | Value |
|-----|-------|
| `DOCUMENT_BUCKET` | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` |
| `PROCESSED_PREFIX` | `processados` |
| `DEFAULT_RESTORE_DAYS` | `2` |

44. **Save**
45. **General configuration** → Memory: `128` MB, Timeout: `30` sec → **Save**

---

### Verificação de cada Lambda

Para cada Lambda criada, faça um teste rápido:

1. Na página da função, clique na aba **Test**
2. **Event name**: `teste-basico`
3. Para as Lambdas de API (todas exceto processar-documento), use este evento de teste:

```json
{
    "version": "2.0",
    "requestContext": {
        "http": {
            "method": "GET",
            "path": "/test"
        }
    },
    "headers": {
        "content-type": "application/json"
    },
    "queryStringParameters": {},
    "body": null,
    "isBase64Encoded": false
}
```

4. Clique em **Test**
5. **Resultado esperado**: A função deve executar sem erro de importação (pode retornar erro de validação como "campo obrigatório", o que é normal — significa que o código carregou corretamente)

Para a Lambda `cofre-processar-documento`, use este evento de teste:

```json
{
    "Records": [
        {
            "s3": {
                "bucket": {
                    "name": "cofre-documentos-arquivos-<AWS_ACCOUNT_ID>"
                },
                "object": {
                    "key": "entrada/contratos/teste.pdf"
                }
            }
        }
    ]
}
```

> **Nota:** Este teste pode falhar com "Access Denied" se o arquivo não existir no bucket — isso é esperado. O importante é que não haja `ImportError` ou `ModuleNotFoundError`.

### Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| `ModuleNotFoundError: No module named 'shared'` | Pasta shared/ não incluída no ZIP | Refaça o ZIP incluindo a pasta shared/ na raiz |
| `Runtime.ImportModuleError` | Arquivo principal não se chama `lambda_function.py` | O handler padrão é `lambda_function.lambda_handler` — verifique o nome |
| Timeout | Timeout muito baixo | Verifique que está em 30 segundos |
| `Access Denied` no teste | Política IAM incorreta ou bucket name errado | Verifique variáveis de ambiente e políticas |

---

## Etapa 8: Configurar Trigger S3 → Lambda processar-documento

Este trigger faz com que o S3 invoque automaticamente a Lambda `cofre-processar-documento` sempre que um novo objeto é criado no prefixo `entrada/`.

### Passo a passo

1. Na barra de busca superior, digite **S3** e acesse o serviço
2. Clique no bucket **cofre-documentos-arquivos-<AWS_ACCOUNT_ID>**
3. Clique na aba **Properties** (Propriedades)
4. Role a página até a seção **Event notifications** (Notificações de eventos)
5. Clique no botão **Create event notification** (Criar notificação de evento)
6. Preencha:

| Campo | Valor |
|-------|-------|
| **Event name** | `trigger-processar-documento` |
| **Prefix** | `entrada/` |
| **Suffix** | *(deixe vazio)* |

7. Na seção **Event types** (Tipos de evento):
   - Expanda **Object creation** (Criação de objetos)
   - Marque ✅ **All object create events** (`s3:ObjectCreated:*`)

8. Na seção **Destination** (Destino):
   - Selecione **Lambda function**
   - No dropdown **Lambda function**, selecione `cofre-processar-documento`

9. Clique em **Save changes**

### O que acontece por trás

- O S3 adicionará automaticamente uma **resource-based policy** na função Lambda, permitindo que o S3 a invoque
- Isso é configurado automaticamente pelo Console — não precisa fazer manualmente

### Verificação

1. Volte à aba **Properties** do bucket
2. Na seção **Event notifications**, você deve ver `trigger-processar-documento` listado
3. **Teste prático:**
   - Vá para a aba **Objects** do bucket
   - Navegue até `entrada/contratos/`
   - Clique em **Upload** → **Add files** → Selecione um arquivo PDF pequeno → **Upload**
   - Aguarde 5-10 segundos
   - Navegue até `processados/contratos/` — o arquivo deve estar lá
   - O arquivo em `entrada/contratos/` deve ter desaparecido
4. Se o arquivo não apareceu em processados:
   - Acesse **Lambda** → `cofre-processar-documento` → **Monitor** → **View CloudWatch logs**
   - Verifique os logs para identificar o erro

### Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| "Unable to validate the following destination configurations" | Lambda não tem permissão para ser invocada pelo S3 | O Console geralmente resolve isso automaticamente; se persistir, vá na Lambda → Configuration → Permissions → Resource-based policy e adicione permissão para s3.amazonaws.com |
| Arquivo não é processado | Prefixo incorreto no evento | Verifique que o Prefix é exatamente `entrada/` (com barra) |
| Lambda executa mas dá erro | Variáveis de ambiente incorretas | Verifique DOCUMENT_BUCKET, SOURCE_PREFIX, PROCESSED_PREFIX, REJECTED_PREFIX |

---

## Etapa 9: Criar API Gateway HTTP API

A API Gateway expõe as funções Lambda como endpoints HTTP acessíveis pelo frontend. Usaremos uma HTTP API (mais simples e barata que REST API).

### Passo a passo

1. Na barra de busca superior, digite **API Gateway** e clique no serviço
2. Na página inicial, localize a seção **HTTP API** e clique no botão **Build** (Construir)

### Configurar a API

3. Na tela "Create an API":
   - Clique em **Add integration** (Adicionar integração)
   - **Integration type**: Lambda
   - **AWS Region**: `us-east-1` (sua região)
   - **Lambda function**: Selecione `cofre-gerar-url-upload`
   - Clique em **Add integration** novamente para adicionar as outras:
     - Lambda: `cofre-listar-documentos`
     - Lambda: `cofre-gerar-url-download`
     - Lambda: `cofre-listar-versoes`
     - Lambda: `cofre-restaurar-documento`
   
   > **Nota:** NÃO adicione `cofre-processar-documento` aqui — ela é acionada pelo S3, não pela API

   - **API name**: `cofre-digital-api`
   - Clique em **Next**

### Configurar Rotas

4. Na tela "Configure routes":
   - O Console pode ter criado rotas automaticamente. **Remova-as** clicando no X e configure manualmente:
   
   Clique em **Add route** para cada rota:

| Method | Resource path | Integration target |
|--------|--------------|-------------------|
| `POST` | `/upload-url` | `cofre-gerar-url-upload` |
| `GET` | `/documentos` | `cofre-listar-documentos` |
| `GET` | `/download-url` | `cofre-gerar-url-download` |
| `GET` | `/versoes` | `cofre-listar-versoes` |
| `POST` | `/restaurar` | `cofre-restaurar-documento` |

5. Clique em **Next**

### Configurar Stages

6. Na tela "Define stages":
   - **Stage name**: `$default`
   - **Auto-deploy**: Mantenha ✅ ativado
   - Clique em **Next**

### Revisar e Criar

7. Na tela "Review and create":
   - Verifique que todas as 5 rotas estão corretas
   - Verifique que cada rota aponta para a Lambda correta
   - Clique em **Create** (Criar)

### Copiar a URL de Invocação

8. Após a criação, você será levado à página da API
9. No menu lateral esquerdo, clique em **Stages** (se não estiver já visível)
10. Clique no stage **$default**
11. **Copie** a **Invoke URL** que aparece no topo (formato: `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com`)
12. **Anote esta URL** — ela será usada no config.js do frontend (Etapa 11) e na configuração CORS

> **IMPORTANTE:** A URL NÃO deve ter barra (`/`) no final. Se tiver, remova-a ao colar no config.js.

### Configurar CORS na API Gateway

13. No menu lateral esquerdo da API, clique em **CORS**
14. Clique em **Configure** (ou **Edit** se já existir configuração)
15. Preencha:

| Campo | Valor |
|-------|-------|
| **Access-Control-Allow-Origin** | `https://<DOMINIO_CLOUDFRONT>` |
| **Access-Control-Allow-Headers** | `content-type` |
| **Access-Control-Allow-Methods** | `GET, POST, OPTIONS` |
| **Access-Control-Max-Age** | `3600` |

> **ATENÇÃO:** Neste momento, você ainda não tem o domínio CloudFront (será criado na Etapa 12). Por enquanto, use `*` (asterisco) como origin para testes iniciais. Na **Etapa 14**, você voltará aqui para substituir pelo domínio real.

16. Clique em **Save**

### Verificação

1. Volte à página principal da API → **Routes**
2. Você deve ver 5 rotas configuradas
3. **Teste rápido via navegador:**
   - Abra uma nova aba e cole: `<API_GATEWAY_URL>/documentos`
   - Resultado esperado: Resposta JSON (pode ser lista vazia ou erro de bucket, dependendo de configuração)
4. **Teste com curl (terminal):**
   ```bash
   curl -X POST <API_GATEWAY_URL>/upload-url \
     -H "Content-Type: application/json" \
     -d '{"filename":"teste.pdf","category":"contratos","contentType":"application/pdf"}'
   ```
   - Resultado esperado: JSON com `uploadUrl`, `key` e `expiresIn`

### Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| "Internal Server Error" | Lambda retornou erro | Verifique CloudWatch Logs da Lambda |
| Rota retorna 404 | Rota não configurada ou método errado | Verifique routes e métodos (GET vs POST) |
| Erro CORS no navegador | CORS não configurado | Configure CORS conforme passo 13-16 |
| "Forbidden" 403 | Payload format version incompatível | HTTP API usa v2.0 por padrão (correto) |

---

## Etapa 10: Criar Bucket do Frontend

Este bucket armazenará os arquivos estáticos do frontend (HTML, CSS, JS). Será privado e acessível apenas via CloudFront.

### Passo a passo

1. Na barra de busca superior, digite **S3** e acesse o serviço
2. Clique em **Create bucket**
3. Preencha:

| Campo | Valor |
|-------|-------|
| **Bucket name** | `cofre-documentos-frontend-<AWS_ACCOUNT_ID>` |
| **AWS Region** | `US East (N. Virginia) us-east-1` |

4. **Object Ownership**: Mantenha **ACLs disabled (recommended)**

5. **Block Public Access settings**:
   - Mantenha ✅ **Block *all* public access**
   - O bucket será privado — acesso somente via CloudFront com OAC

6. **Bucket Versioning**: Mantenha **Disable** (não necessário para frontend)

7. **Default encryption**:
   - **Encryption type**: **Server-side encryption with Amazon S3 managed keys (SSE-S3)**
   - **Bucket Key**: **Enable**

8. Clique em **Create bucket**

### Upload dos arquivos do frontend

9. Clique no bucket **cofre-documentos-frontend-<AWS_ACCOUNT_ID>** que acabou de criar
10. Clique em **Upload**
11. Clique em **Add files** (Adicionar arquivos)
12. Selecione os 4 arquivos da pasta `frontend/` deste repositório:
    - `index.html`
    - `styles.css`
    - `app.js`
    - `config.js`
13. **IMPORTANTE:** Antes de clicar em Upload, expanda a seção **Properties** (Propriedades):
    - Na parte **Content type**, o S3 geralmente detecta automaticamente
    - Se não detectar, configure manualmente para cada arquivo:
      - `index.html` → `text/html`
      - `styles.css` → `text/css`
      - `app.js` → `application/javascript`
      - `config.js` → `application/javascript`
14. Clique em **Upload**
15. Aguarde a confirmação de que todos os 4 arquivos foram carregados com sucesso
16. Clique em **Close**

### Verificação

- Na aba **Objects** do bucket, você deve ver os 4 arquivos listados
- Clique em `index.html` → verifique que o Content type está como `text/html`
- **Neste momento, o bucket é privado** — tentar acessar via URL do S3 resultará em "Access Denied" (esperado)

### Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| "Bucket name already exists" | Nome já em uso globalmente | Verifique se Account ID está correto |
| Upload falha | Arquivo muito grande ou conexão instável | Frontend são arquivos pequenos (<1MB cada), tente novamente |

---

## Etapa 11: Atualizar config.js com a URL da API Gateway

O arquivo `config.js` contém a URL base que o frontend usa para chamar a API. Você precisa substituir o placeholder pela URL real obtida na Etapa 9.

### Passo a passo

1. No seu computador, abra o arquivo `frontend/config.js` em um editor de texto
2. Substitua `COLE_AQUI_A_URL_DA_API` pela URL de invocação da API Gateway (copiada na Etapa 9)
3. O arquivo final deve ficar assim:

```javascript
/**
 * Configuração do Cofre Digital de Documentos.
 * 
 * INSTRUÇÕES:
 * Substitua o valor de API_BASE_URL pela URL de invocação
 * da sua API Gateway HTTP API (sem barra final).
 * 
 * Exemplo: https://abc123def.execute-api.us-east-1.amazonaws.com
 */
window.APP_CONFIG = {
    API_BASE_URL: "https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com"
};
```

> **ATENÇÃO:** Não coloque barra `/` no final da URL. O código JavaScript já adiciona as rotas (ex: `/upload-url`, `/documentos`).

### Re-upload do config.js

4. Acesse o Console S3
5. Clique no bucket **cofre-documentos-frontend-<AWS_ACCOUNT_ID>**
6. Você verá o arquivo `config.js` existente na listagem
7. Clique em **Upload**
8. Clique em **Add files** e selecione o `config.js` atualizado do seu computador
9. Clique em **Upload**
10. O S3 substituirá o arquivo anterior automaticamente

### Verificação

- Clique no arquivo `config.js` no bucket
- Clique em **Open** (ou no URL do objeto — que retornará "Access Denied" pois o bucket é privado)
- Para verificar o conteúdo: selecione o arquivo → **Actions** → **Query with S3 Select** (ou baixe o arquivo para verificar localmente)

### Alternativa: Editar diretamente no Console

Se preferir não fazer re-upload:

1. No bucket frontend, clique no arquivo `config.js`
2. Na visualização do objeto, NÃO há editor inline no S3
3. A forma mais simples é fazer o re-upload conforme descrito acima

---

## Etapa 12: Criar Distribuição CloudFront

O CloudFront é a CDN (Content Delivery Network) que servirá o frontend para os usuários. Ele acessa o bucket privado do frontend usando Origin Access Control (OAC).

### Passo a passo

1. Na barra de busca superior, digite **CloudFront** e clique no serviço
2. Clique no botão **Create distribution** (Criar distribuição)

### Configurar Origin (Origem)

3. Preencha a seção **Origin**:

| Campo | Valor |
|-------|-------|
| **Origin domain** | Clique no campo e selecione o bucket `cofre-documentos-frontend-<AWS_ACCOUNT_ID>.s3.us-east-1.amazonaws.com` na lista dropdown |
| **Origin path** | *(deixe vazio)* |
| **Name** | Será preenchido automaticamente com o nome do bucket |
| **Origin access** | Selecione **Origin access control settings (recommended)** |

4. Após selecionar "Origin access control settings", clique no botão **Create new OAC** (Criar novo OAC):
   - **Name**: `cofre-frontend-oac` (ou aceite o nome sugerido)
   - **Description**: `OAC para acesso ao bucket frontend do cofre digital`
   - **Signing behavior**: Mantenha **Sign requests (recommended)**
   - **Origin type**: Mantenha **S3**
   - Clique em **Create**

5. O OAC criado será selecionado automaticamente

### Configurar Default Cache Behavior

6. Role até a seção **Default cache behavior**:

| Campo | Valor |
|-------|-------|
| **Compress objects automatically** | ✅ Yes |
| **Viewer protocol policy** | **Redirect HTTP to HTTPS** |
| **Allowed HTTP methods** | **GET, HEAD** |
| **Cache policy** | Selecione **CachingOptimized** (recomendado para estáticos) |

7. **Restrict viewer access**: Mantenha **No**

### Configurar Settings

8. Role até a seção **Settings** (no final da página):

| Campo | Valor |
|-------|-------|
| **Price class** | **Use all edge locations (best performance)** ou **Use only North America and Europe** (para economizar) |
| **AWS WAF** | **Do not enable security protections** (para projeto educacional) |
| **Alternate domain name (CNAME)** | *(deixe vazio — usaremos o domínio .cloudfront.net)* |
| **Custom SSL certificate** | *(deixe vazio)* |
| **Default root object** | `index.html` |
| **Description** | `Distribuição CloudFront para frontend do Cofre Digital` |

9. Clique no botão laranja **Create distribution**

### Copiar informações importantes

10. Após criar, você será levado à página da distribuição
11. **Copie e anote:**
    - **Distribution domain name**: `dXXXXXXXXXXXXX.cloudfront.net` — este é o `<DOMINIO_CLOUDFRONT>`
    - **Distribution ID**: `E1A2B3C4D5E6F7` — este é o `<DISTRIBUTION_ID>`
    - **ARN**: `arn:aws:cloudfront::<AWS_ACCOUNT_ID>:distribution/EXXXXXXXXXXXXXX`

12. **Status**: A distribuição levará **5-15 minutos** para ser implantada. O status mudará de "Deploying" para "Enabled"

### Banner de Bucket Policy

13. Logo após criar a distribuição, o Console exibirá um **banner azul** no topo dizendo:
    > "The S3 bucket policy needs to be updated"
    
14. Clique no botão **Copy policy** neste banner
15. **Guarde esta política copiada** — ela será usada na Etapa 13

> **Se o banner desapareceu:** Vá em CloudFront → sua distribuição → aba **Origins** → selecione a origin → **Edit** → Na seção "Origin access", o botão "Copy policy" estará disponível.

### Verificação

- Após 5-15 minutos, o Status deve mudar para **Enabled** (data de "Last modified" aparece)
- **Ainda não funcionará** — a bucket policy do frontend precisa ser atualizada (Etapa 13)

### Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| "Access Denied" ao acessar domínio CloudFront | Bucket policy não foi atualizada | Complete a Etapa 13 |
| Distribuição demora mais de 30 min | Normal em alguns casos | Aguarde; verifique se não há erro na configuração |
| "Default root object" não funciona | Campo não preenchido | Edite a distribuição e adicione `index.html` |

---

## Etapa 13: Aplicar Bucket Policy do Frontend

O CloudFront precisa de permissão para ler os objetos do bucket privado do frontend. A bucket policy gerada na Etapa 12 concede essa permissão via Origin Access Control (OAC).

### Passo a passo

1. Na barra de busca superior, digite **S3** e acesse o serviço
2. Clique no bucket **cofre-documentos-frontend-<AWS_ACCOUNT_ID>**
3. Clique na aba **Permissions** (Permissões)
4. Role até a seção **Bucket policy**
5. Clique em **Edit** (Editar)
6. Cole a política que você copiou do banner do CloudFront (Etapa 12, passo 14)

A política deve ser semelhante a esta (arquivo `s3/bucket-policy-frontend.json` do repositório):

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowCloudFrontServicePrincipal",
            "Effect": "Allow",
            "Principal": {
                "Service": "cloudfront.amazonaws.com"
            },
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::cofre-documentos-frontend-<AWS_ACCOUNT_ID>/*",
            "Condition": {
                "StringEquals": {
                    "AWS:SourceArn": "arn:aws:cloudfront::<AWS_ACCOUNT_ID>:distribution/<DISTRIBUTION_ID>"
                }
            }
        }
    ]
}
```

> **IMPORTANTE:** Use a política copiada diretamente do Console do CloudFront (passo 14 da Etapa 12), pois ela já contém os valores corretos do seu Distribution ID. Se estiver usando o template acima, substitua `<AWS_ACCOUNT_ID>`, `<DISTRIBUTION_ID>` e o nome do bucket.

7. Clique em **Save changes**

### Explicação da política

| Elemento | Significado |
|----------|-------------|
| `Principal: cloudfront.amazonaws.com` | Apenas o serviço CloudFront pode ler |
| `Action: s3:GetObject` | Permite apenas leitura de objetos |
| `Resource: .../*` | Aplica a todos os objetos no bucket |
| `Condition: AWS:SourceArn` | Restringe ao seu Distribution ID específico — outras distribuições CloudFront NÃO terão acesso |

### Verificação

1. Aguarde a distribuição CloudFront finalizar o deploy (Status: "Enabled")
2. Abra uma nova aba do navegador
3. Cole o domínio CloudFront: `https://dXXXXXXXXXXXXX.cloudfront.net`
4. **Resultado esperado:** A página do Cofre Digital deve carregar (HTML com estilos)
5. Se aparecer o erro "AccessDenied" em XML:
   - Verifique que a bucket policy foi salva corretamente
   - Verifique que o "Default root object" está como `index.html` na distribuição CloudFront
   - Aguarde mais alguns minutos para propagação

### Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| "Access Denied" persistente | Policy não foi salva ou Distribution ID está errado | Copie a policy novamente do CloudFront |
| Página em branco | index.html não foi carregado no bucket | Verifique os arquivos na Etapa 10 |
| CSS/JS não carrega | Content-Type incorreto nos arquivos | Faça re-upload com os Content-Types corretos |

---

## Etapa 14: Atualizar CORS com Domínio CloudFront Real

Agora que você tem o domínio real do CloudFront, é necessário atualizar o CORS do bucket de documentos e o CORS da API Gateway com o domínio correto.

### 14.1 — Atualizar CORS do Bucket de Documentos

1. No Console S3, clique no bucket **cofre-documentos-arquivos-<AWS_ACCOUNT_ID>**
2. Clique na aba **Permissions** (Permissões)
3. Role até **Cross-origin resource sharing (CORS)**
4. Clique em **Edit**
5. Substitua o valor de `AllowedOrigins` pelo domínio real:

```json
[
    {
        "AllowedHeaders": [
            "*"
        ],
        "AllowedMethods": [
            "PUT",
            "GET",
            "HEAD"
        ],
        "AllowedOrigins": [
            "https://dXXXXXXXXXXXXX.cloudfront.net"
        ],
        "ExposeHeaders": [
            "ETag",
            "x-amz-version-id"
        ],
        "MaxAgeSeconds": 3000
    }
]
```

6. **Substitua** `dXXXXXXXXXXXXX.cloudfront.net` pelo domínio real anotado na Etapa 12
7. Clique em **Save changes**

### 14.2 — Atualizar CORS da API Gateway

8. Na barra de busca, digite **API Gateway** e acesse o serviço
9. Clique na API **cofre-digital-api**
10. No menu lateral esquerdo, clique em **CORS**
11. Clique em **Edit** (se já configurou antes) ou **Configure**
12. Atualize:

| Campo | Valor |
|-------|-------|
| **Access-Control-Allow-Origin** | `https://dXXXXXXXXXXXXX.cloudfront.net` (seu domínio real) |
| **Access-Control-Allow-Headers** | `content-type` |
| **Access-Control-Allow-Methods** | `GET, POST, OPTIONS` |
| **Access-Control-Max-Age** | `3600` |

> **IMPORTANTE:** Se antes você colocou `*` (asterisco) como origin para testes, agora é hora de substituir pelo domínio real. Manter `*` funciona mas é menos seguro.

13. Clique em **Save**

### Verificação

1. Abra o DevTools do navegador (F12) → aba **Console**
2. Acesse `https://dXXXXXXXXXXXXX.cloudfront.net`
3. Tente fazer um upload no Cofre Digital
4. Se o CORS estiver correto, **não haverá erros CORS** no console do navegador
5. Se aparecer erro tipo `Access to fetch at '...' from origin '...' has been blocked by CORS policy`:
   - Verifique que o domínio no CORS do S3 **e** da API Gateway bate exatamente com o domínio do CloudFront
   - Inclua o protocolo `https://` no valor
   - **Não coloque barra `/` no final** do domínio

### Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| CORS error no upload | CORS do bucket S3 com domínio errado | Verifique AllowedOrigins no S3 |
| CORS error na listagem | CORS da API Gateway com domínio errado | Verifique Allow-Origin na API Gateway |
| "No 'Access-Control-Allow-Origin' header" | Domínio não bate exatamente | O domínio deve ser idêntico incluindo `https://` |

---

## Etapa 15: Criar Invalidação no CloudFront

Quando você atualiza arquivos no bucket do frontend (como o config.js), o CloudFront pode continuar servindo a versão antiga do cache. Uma invalidação força o CloudFront a buscar os arquivos mais recentes do S3.

### Passo a passo

1. Na barra de busca superior, digite **CloudFront** e acesse o serviço
2. Clique na sua distribuição (identificada pelo domínio `dXXXXXXXXXXXXX.cloudfront.net`)
3. Clique na aba **Invalidations** (Invalidações)
4. Clique no botão **Create invalidation** (Criar invalidação)
5. No campo **Object paths** (Caminhos dos objetos), digite:
   ```
   /*
   ```
   (barra asterisco — invalida TODOS os arquivos)
6. Clique em **Create invalidation**

### Explicação

| Path | Efeito |
|------|--------|
| `/*` | Invalida todos os arquivos em cache (mais simples) |
| `/config.js` | Invalida apenas o config.js (mais preciso) |
| `/index.html` | Invalida apenas o HTML |

> **Custo:** As primeiras 1.000 paths de invalidação por mês são gratuitas. Usar `/*` conta como 1 path.

### Quando usar invalidação

- Após atualizar `config.js` com a URL da API (Etapa 11)
- Após atualizar qualquer arquivo do frontend
- Se o navegador mostra uma versão antiga da página

### Verificação

1. O status da invalidação mudará de **In Progress** para **Completed** (leva 1-5 minutos)
2. Após completar, abra o site em uma janela anônima/privada: `https://dXXXXXXXXXXXXX.cloudfront.net`
3. O frontend deve carregar com a versão mais recente dos arquivos
4. Verifique no DevTools (F12 → aba Network) que os arquivos não estão vindo do cache antigo

### Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| Invalidação fica em "In Progress" muito tempo | Normal, pode levar até 15 min | Aguarde |
| Arquivo antigo ainda aparece | Cache do navegador local | Use Ctrl+Shift+R (hard refresh) ou janela anônima |

---

## Etapa 16: Configurar Regras de Lifecycle (Ciclo de Vida)

As regras de Lifecycle automatizam a transição de objetos entre classes de armazenamento e a expiração de objetos antigos. O S3 executa essas regras automaticamente (geralmente uma vez por dia).

### Passo a passo

1. No Console S3, clique no bucket **cofre-documentos-arquivos-<AWS_ACCOUNT_ID>**
2. Clique na aba **Management** (Gerenciamento)
3. Na seção **Lifecycle rules** (Regras de ciclo de vida), clique em **Create lifecycle rule**

---

### Regra 1: `arquivar-documentos-processados`

Esta regra transiciona documentos processados para classes mais baratas ao longo do tempo e os expira após 2 anos.

4. Preencha:

| Campo | Valor |
|-------|-------|
| **Lifecycle rule name** | `arquivar-documentos-processados` |
| **Choose a rule scope** | Selecione **Limit the scope of this rule using one or more filters** |
| **Prefix** | `processados/` |
| **Object size** | Marque ✅ **Specify minimum object size** → `128` KB (131072 bytes) |

> **Por que filtrar por tamanho?** Objetos muito pequenos (<128KB) não se beneficiam de transição para Glacier — o custo mínimo por objeto pode ser maior que a economia.

5. Na seção **Lifecycle rule actions**, marque ✅:
   - ✅ **Move current versions of objects between storage classes**
   - ✅ **Expire current versions of objects**

6. Na seção **Transition current versions of objects between storage classes**:
   - Clique em **Add transition**:
     - **Storage class**: `Intelligent-Tiering`
     - **Days after object creation**: `30`
   - Clique em **Add transition** novamente:
     - **Storage class**: `Glacier Flexible Retrieval`
     - **Days after object creation**: `180`
   - Clique em **Add transition** novamente:
     - **Storage class**: `Glacier Deep Archive`
     - **Days after object creation**: `365`

7. Na seção **Expire current versions of objects**:
   - **Days after object creation**: `730`

8. Marque ✅ **I acknowledge that this lifecycle rule will apply to all objects in the bucket matching the specified filter**

9. Clique em **Create rule**

---

### Regra 2: `excluir-arquivos-temporarios`

Esta regra expira automaticamente objetos temporários após 7 dias.

10. Clique em **Create lifecycle rule** novamente
11. Preencha:

| Campo | Valor |
|-------|-------|
| **Lifecycle rule name** | `excluir-arquivos-temporarios` |
| **Choose a rule scope** | **Limit the scope of this rule using one or more filters** |
| **Prefix** | `temporarios/` |

12. Na seção **Lifecycle rule actions**, marque ✅:
    - ✅ **Expire current versions of objects**
    - ✅ **Permanently delete noncurrent versions of objects**
    - ✅ **Delete expired object delete markers or incomplete multipart uploads**

13. Na seção **Expire current versions of objects**:
    - **Days after object creation**: `7`

14. Na seção **Permanently delete noncurrent versions of objects**:
    - **Days after objects become noncurrent**: `7`

15. Na seção **Delete expired object delete markers or incomplete multipart uploads**:
    - Marque ✅ **Delete incomplete multipart uploads**
    - **Number of days**: `1`

16. Marque ✅ o acknowledgment e clique em **Create rule**

---

### Regra 3: `limpar-versoes-antigas`

Esta regra remove versões não-correntes de documentos processados após 90 dias e limpa delete markers expirados.

17. Clique em **Create lifecycle rule** novamente
18. Preencha:

| Campo | Valor |
|-------|-------|
| **Lifecycle rule name** | `limpar-versoes-antigas` |
| **Choose a rule scope** | **Limit the scope of this rule using one or more filters** |
| **Prefix** | `processados/` |

19. Na seção **Lifecycle rule actions**, marque ✅:
    - ✅ **Permanently delete noncurrent versions of objects**
    - ✅ **Delete expired object delete markers or incomplete multipart uploads**

20. Na seção **Permanently delete noncurrent versions of objects**:
    - **Days after objects become noncurrent**: `90`

21. Na seção **Delete expired object delete markers or incomplete multipart uploads**:
    - Marque ✅ **Delete expired object delete markers**

22. Marque ✅ o acknowledgment e clique em **Create rule**

---

### Verificação

- Na aba **Management** do bucket, a seção **Lifecycle rules** deve listar 3 regras:
  1. `arquivar-documentos-processados` — Status: Enabled
  2. `excluir-arquivos-temporarios` — Status: Enabled
  3. `limpar-versoes-antigas` — Status: Enabled

### Nota importante sobre Lifecycle

> ⚠️ **As regras de Lifecycle NÃO são instantâneas.** O S3 executa as avaliações de Lifecycle aproximadamente uma vez por dia, em um horário não determinístico. Isso significa:
> - Após criar a regra, os objetos **não serão movidos/expirados imediatamente**
> - Pode levar até 48 horas para a primeira execução
> - Para testar transições de classe, use o método manual descrito na Etapa 18 (Laboratório)

### Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| "Overlapping lifecycle rules" (warning) | Duas regras no mesmo prefixo com ações conflitantes | Normal para regras 1 e 3 (uma transiciona, outra limpa versões) — pode ignorar |
| Transição não acontece | Lifecycle ainda não executou | Aguarde 24-48h |
| "Minimum days for transition" | Transição para Glacier requer mínimo 30 dias após Standard | Verifique a sequência de dias |

---

## Etapa 17: Testar o Projeto

Agora que todos os recursos estão criados e configurados, vamos validar o funcionamento completo do sistema.

### 17.1 — Acessar o Frontend

1. Abra o navegador e acesse: `https://<DOMINIO_CLOUDFRONT>`
2. **Resultado esperado:** A página do Cofre Digital carrega com:
   - Header "Cofre Digital de Documentos"
   - Área de upload (campo de arquivo, dropdown de categoria, botão enviar)
   - Tabela de documentos (pode estar vazia)
   - Cards educacionais sobre classes de armazenamento

3. Abra o DevTools (F12) → aba **Console**
4. **Não deve haver erros em vermelho.** Se houver erros CORS ou de rede, revise as Etapas 11 e 14

---

### 17.2 — Testar Upload de Documento

5. Na interface do Cofre Digital:
   - Clique em **Escolher arquivo** (ou "Browse")
   - Selecione um arquivo PDF pequeno (ou TXT, PNG — qualquer extensão válida)
   - No dropdown de **Categoria**, selecione `contratos`
   - Clique em **Enviar** (ou "Upload")

6. **Resultado esperado:**
   - Mensagem de sucesso aparece
   - O documento deve aparecer na tabela de documentos após alguns segundos
   - No DevTools → Network: você deve ver:
     - `POST /upload-url` → 200 (obtém URL pré-assinada)
     - `PUT https://...s3...amazonaws.com/entrada/contratos/...` → 200 (upload direto ao S3)

7. **Verificação no Console S3:**
   - Acesse o bucket de documentos no Console S3
   - Navegue até `processados/contratos/`
   - O arquivo deve estar lá (foi processado automaticamente pela Lambda)
   - `entrada/contratos/` deve estar vazio (arquivo foi movido)

---

### 17.3 — Verificar Logs no CloudWatch

8. Na barra de busca, digite **CloudWatch** e acesse o serviço
9. No menu lateral, clique em **Log groups** (Grupos de log)
10. Você deve ver grupos como:
    - `/aws/lambda/cofre-gerar-url-upload`
    - `/aws/lambda/cofre-processar-documento`
11. Clique em `/aws/lambda/cofre-processar-documento`
12. Clique no log stream mais recente
13. **Resultado esperado:** Logs mostrando:
    - "Processando objeto: bucket=..., key=entrada/contratos/..."
    - "Documento válido. Copiando..."
    - "Objeto copiado para: processados/contratos/..."
    - "Objeto original removido: entrada/contratos/..."

---

### 17.4 — Testar Download

14. Na interface do Cofre Digital, na tabela de documentos:
    - Localize o documento que você enviou
    - Clique no botão **Download** (ícone de download ou link)

15. **Resultado esperado:**
    - O download inicia automaticamente
    - O arquivo baixado deve ser idêntico ao original

16. **Verificação no DevTools:**
    - `GET /download-url?key=processados/contratos/...` → 200 (obtém URL pré-assinada)
    - Redirecionamento para URL do S3 → download do arquivo

---

### 17.5 — Testar Versionamento

17. Faça upload do **mesmo arquivo** novamente (mesmo nome, mesma categoria)
18. Na tabela de documentos, clique em **Versões** (botão de versões) ao lado do documento
19. **Resultado esperado:**
    - Aparece uma lista com 2 versões
    - Cada versão mostra: ID da versão, data, tamanho
    - A versão mais recente está marcada como "Atual" (isLatest: true)

20. **Verificação no Console S3:**
    - Clique no objeto em `processados/contratos/`
    - Clique na aba **Versions**
    - Deve haver 2 versões listadas com IDs diferentes

---

### 17.6 — Testar Upload Inválido

21. Tente fazer upload de um arquivo com extensão `.exe` ou `.bat`
22. **Resultado esperado:** Mensagem de erro: "Extensão não permitida. Extensões válidas: pdf, png, jpg, jpeg, csv, xlsx, txt"
23. O arquivo NÃO deve ser enviado ao S3

---

### 17.7 — Resumo da Validação

| Teste | Status Esperado |
|-------|----------------|
| Frontend carrega | ✅ Página exibe corretamente |
| Upload de arquivo válido | ✅ Arquivo aparece em processados/ |
| Processamento automático | ✅ Lambda move de entrada/ para processados/ |
| Listagem de documentos | ✅ Tabela mostra documentos com metadados |
| Download funciona | ✅ Arquivo baixa corretamente |
| Versionamento | ✅ Múltiplas versões são listadas |
| Upload inválido rejeitado | ✅ Erro amigável exibido ao usuário |
| Logs no CloudWatch | ✅ Execuções registradas sem erros |

---

## Etapa 18: Testar Classes de Armazenamento (Laboratório)

O prefixo `laboratorio/` existe para experimentar com classes de armazenamento S3 sem afetar os documentos reais. Aqui você aprenderá a fazer upload direto especificando a classe de armazenamento.

> **IMPORTANTE:** Transições via Lifecycle demoram até 48h. Para testar classes de armazenamento imediatamente, faremos upload direto com a classe desejada via Console S3.

---

### 18.1 — Upload com classe Standard (padrão)

1. No Console S3, acesse o bucket **cofre-documentos-arquivos-<AWS_ACCOUNT_ID>**
2. Navegue até `laboratorio/standard/`
3. Clique em **Upload**
4. Clique em **Add files** → Selecione um arquivo de teste (ex: `teste-standard.txt`)
5. **NÃO** precisa alterar nenhuma propriedade (Standard é o padrão)
6. Clique em **Upload**
7. **Verificação:** Clique no objeto → em **Properties**, o campo **Storage class** mostra `Standard`

---

### 18.2 — Upload com Intelligent-Tiering

8. Navegue até `laboratorio/intelligent-tiering/`
9. Clique em **Upload**
10. Clique em **Add files** → Selecione um arquivo de teste (ex: `teste-it.txt`)
11. Expanda a seção **Properties** (abaixo de "Add files")
12. Na parte **Storage class**, selecione **Intelligent-Tiering**
13. Clique em **Upload**
14. **Verificação:** Clique no objeto → **Properties** → Storage class mostra `Intelligent-Tiering`

> **Sobre Intelligent-Tiering:** O S3 move automaticamente objetos entre camadas de acesso (Frequent, Infrequent, Archive) baseado em padrões de acesso. Objetos acessados frequentemente ficam em Standard; os menos acessados são movidos automaticamente para camadas mais baratas.

---

### 18.3 — Upload com Glacier Flexible Retrieval

15. Navegue até `laboratorio/glacier-flexible/`
16. Clique em **Upload**
17. Clique em **Add files** → Selecione um arquivo de teste (ex: `teste-glacier.txt`)
18. Expanda a seção **Properties**
19. Na parte **Storage class**, selecione **Glacier Flexible Retrieval**
20. Clique em **Upload**
21. **Verificação:** Clique no objeto → **Properties** → Storage class mostra `Glacier Flexible Retrieval`

> **IMPORTANTE:** Após o upload para Glacier, o objeto **NÃO pode ser baixado diretamente**. Tentar baixar resultará em erro. É necessário fazer uma **restauração** primeiro (veja 18.5).

---

### 18.4 — Upload com Glacier Deep Archive

22. Navegue até `laboratorio/deep-archive/`
23. Clique em **Upload**
24. Clique em **Add files** → Selecione um arquivo de teste (ex: `teste-deep-archive.txt`)
25. Expanda a seção **Properties**
26. Na parte **Storage class**, selecione **Glacier Deep Archive**
27. Clique em **Upload**
28. **Verificação:** Clique no objeto → **Properties** → Storage class mostra `Glacier Deep Archive`

> **Sobre Deep Archive:** Classe mais barata para dados acessados muito raramente. A restauração leva de 12 a 48 horas (Standard tier). Ideal para backups de longo prazo e compliance.

---

### 18.5 — Testar Restauração de Objeto Glacier

Vamos restaurar o objeto enviado para Glacier Flexible Retrieval.

**Via Console S3:**

29. Navegue até `laboratorio/glacier-flexible/`
30. Selecione o checkbox ☐ ao lado de `teste-glacier.txt`
31. Clique no menu **Actions** (Ações) → **Initiate restore** (Iniciar restauração)
32. Preencha:

| Campo | Valor |
|-------|-------|
| **Number of days** | `2` (dias que o objeto ficará disponível após restauração) |
| **Retrieval tier** | **Standard** (3-5 horas para Glacier Flexible) |

33. Clique em **Initiate restore**

**Via Frontend (usando a API):**

34. Se o objeto estivesse em `processados/`, você poderia usar o botão "Restaurar" na interface do Cofre Digital, que chama a Lambda `cofre-restaurar-documento`

**Verificar status da restauração:**

35. Clique no objeto `teste-glacier.txt`
36. Na seção **Properties**, procure por **Restore status**:
    - `Restoration in progress` — Restauração em andamento (aguarde 3-5h para Glacier, 12-48h para Deep Archive)
    - `Restored until [data]` — Objeto temporariamente disponível até a data indicada

**Após restauração concluída:**

37. Quando o status mudar para "Restored until...", você poderá baixar o objeto normalmente
38. Após a data de expiração, o objeto voltará a ser inacessível (continua em Glacier)

---

### 18.6 — Tabela Comparativa de Classes

| Classe | Uso típico | Restauração | Custo (relativo) |
|--------|-----------|-------------|-----------------|
| Standard | Acesso frequente | Imediato | $$$ |
| Intelligent-Tiering | Padrão de acesso desconhecido | Imediato | $$-$$$ (automático) |
| Glacier Flexible | Arquivamento com acesso eventual | 1-12 horas | $ |
| Glacier Deep Archive | Arquivamento de longo prazo | 12-48 horas | ¢ |

### Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| "InvalidObjectState" ao baixar | Objeto em Glacier sem restauração | Inicie a restauração primeiro |
| Restauração demora demais | Normal para Deep Archive | Aguarde até 48h (Standard tier) |
| "RestoreAlreadyInProgress" | Restauração já foi solicitada | Aguarde a conclusão |

---

## Seção Opcional: Substituir SSE-S3 por SSE-KMS

Esta seção é **opcional** e destinada a quem deseja aprender sobre criptografia gerenciada pelo AWS KMS (Key Management Service). O SSE-S3 padrão já é suficiente para a maioria dos cenários.

### Quando usar SSE-KMS ao invés de SSE-S3?

| Cenário | Recomendação |
|---------|-------------|
| Projeto educacional ou pessoal | SSE-S3 (mais simples, sem custo adicional) |
| Requisito de auditoria de uso da chave | SSE-KMS (cada uso é registrado no CloudTrail) |
| Controle granular de quem pode descriptografar | SSE-KMS (policies na chave KMS) |
| Compliance (HIPAA, PCI-DSS) | SSE-KMS (rotação automática, segregação de acesso) |
| Multi-conta (cross-account access) | SSE-KMS (permite compartilhar chave entre contas) |

### Diferenças principais

| Característica | SSE-S3 | SSE-KMS |
|---------------|--------|---------|
| Gerenciamento da chave | AWS gerencia tudo | Você controla ou AWS gerencia |
| Custo da chave | Gratuito | $1/mês por chave + $0.03 por 10.000 requisições |
| Auditoria | Básica | Completa via CloudTrail |
| Rotação | Automática (interna) | Automática anual (configurável) |
| Limite de requisições | Sem limite | Cota de API KMS (5.500-30.000 req/s por região) |

---

### Passo 1: Criar uma Chave KMS

1. Na barra de busca superior, digite **KMS** e clique em **Key Management Service**
2. No menu lateral, clique em **Customer managed keys** (Chaves gerenciadas pelo cliente)
3. Verifique que a região é `us-east-1`
4. Clique em **Create key** (Criar chave)
5. Preencha:

| Campo | Valor |
|-------|-------|
| **Key type** | `Symmetric` (Simétrica) |
| **Key usage** | `Encrypt and decrypt` |

6. Clique em **Next**
7. Na tela "Add labels":

| Campo | Valor |
|-------|-------|
| **Alias** | `cofre-digital-kms-key` |
| **Description** | `Chave KMS para criptografia dos documentos do Cofre Digital` |
| **Tags** | Key: `projeto` → Value: `cofre-digital` |

8. Clique em **Next**
9. Na tela "Define key administrative permissions":
   - Selecione seu usuário IAM (admin-cofre-digital ou o usuário logado)
   - Clique em **Next**
10. Na tela "Define key usage permissions":
    - Selecione os roles das Lambdas que precisam descriptografar:
      - `cofre-role-processar-documento`
      - `cofre-role-listar-documentos`
      - `cofre-role-gerar-url-download`
      - `cofre-role-listar-versoes`
      - `cofre-role-restaurar-documento`
      - `cofre-role-gerar-url-upload`
    - Clique em **Next**
11. Revise a key policy e clique em **Finish** (Concluir)
12. **Anote o ARN da chave**: `arn:aws:kms:us-east-1:<AWS_ACCOUNT_ID>:key/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

---

### Passo 2: Alterar criptografia do Bucket de Documentos

13. No Console S3, clique no bucket **cofre-documentos-arquivos-<AWS_ACCOUNT_ID>**
14. Clique na aba **Properties** (Propriedades)
15. Role até **Default encryption** (Criptografia padrão)
16. Clique em **Edit**
17. Altere:

| Campo | Valor |
|-------|-------|
| **Encryption type** | **Server-side encryption with AWS Key Management Service keys (SSE-KMS)** |
| **AWS KMS key** | Selecione **Choose from your AWS KMS keys** |
| **AWS KMS key** | Selecione `cofre-digital-kms-key` na lista |
| **Bucket Key** | Mantenha **Enable** (reduz chamadas ao KMS e custos) |

18. Clique em **Save changes**

---

### Passo 3: Atualizar políticas IAM das Lambdas

Para que as Lambdas possam ler/escrever objetos criptografados com KMS, adicione a seguinte permissão a TODAS as 6 políticas IAM (Etapa 5):

```json
{
    "Sid": "AllowKMSDecryptEncrypt",
    "Effect": "Allow",
    "Action": [
        "kms:Decrypt",
        "kms:GenerateDataKey"
    ],
    "Resource": "arn:aws:kms:<AWS_REGION>:<AWS_ACCOUNT_ID>:key/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
}
```

**Para cada política:**

19. Acesse **IAM** → **Policies** → Clique na política (ex: `cofre-policy-gerar-url-upload`)
20. Clique em **Edit** (Editar)
21. Na aba JSON, adicione o statement acima dentro do array `Statement`
22. Substitua o ARN da chave pelo valor real anotado no Passo 1
23. Clique em **Next** → **Save changes**
24. Repita para todas as 6 políticas

---

### Verificação

1. Faça upload de um novo arquivo via o Cofre Digital
2. No Console S3, clique no objeto carregado
3. Na aba **Properties**, a seção **Server-side encryption** deve mostrar:
   - **Encryption type**: `aws:kms`
   - **AWS KMS key ARN**: O ARN da sua chave
4. O download deve funcionar normalmente (descriptografia é transparente se a Lambda tem permissão)

### Possíveis erros

| Erro | Causa | Solução |
|------|-------|---------|
| "Access Denied" ao ler objetos | Lambda não tem permissão kms:Decrypt | Adicione permissão KMS na política IAM |
| "KMS.AccessDeniedException" | Role não está na key policy | Adicione o role na key usage permissions do KMS |
| Upload falha com "KMS" | Lambda não tem kms:GenerateDataKey | Adicione à política IAM |

---

## Resumo de Recursos Criados

Ao final deste guia, você terá criado os seguintes recursos na AWS:

| # | Serviço | Recurso | Nome/Identificador |
|---|---------|---------|-------------------|
| 1 | S3 | Bucket de documentos | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` |
| 2 | S3 | Bucket do frontend | `cofre-documentos-frontend-<AWS_ACCOUNT_ID>` |
| 3 | S3 | CORS (bucket documentos) | Configuração no bucket |
| 4 | S3 | Bucket Policy HTTPS (documentos) | Configuração no bucket |
| 5 | S3 | Bucket Policy CloudFront (frontend) | Configuração no bucket |
| 6 | S3 | Prefixos (entrada, processados, etc.) | Objetos vazios |
| 7 | S3 | 3 regras de Lifecycle | No bucket de documentos |
| 8 | S3 | Event Notification | `trigger-processar-documento` |
| 9 | IAM | 6 políticas customizadas | `cofre-policy-*` |
| 10 | IAM | 6 roles | `cofre-role-*` |
| 11 | Lambda | 6 funções | `cofre-gerar-url-upload`, `cofre-processar-documento`, `cofre-listar-documentos`, `cofre-gerar-url-download`, `cofre-listar-versoes`, `cofre-restaurar-documento` |
| 12 | API Gateway | HTTP API | `cofre-digital-api` |
| 13 | API Gateway | 5 rotas | POST /upload-url, GET /documentos, GET /download-url, GET /versoes, POST /restaurar |
| 14 | CloudFront | Distribuição | `dXXXXXXXXXXXXX.cloudfront.net` |
| 15 | CloudFront | OAC | `cofre-frontend-oac` |
| 16 | CloudWatch | 6 Log Groups | `/aws/lambda/cofre-*` (criados automaticamente) |

---

## Ordem Recomendada em Caso de Problemas

Se algo não funcionar, verifique nesta ordem:

1. **Variáveis de ambiente** das Lambdas (nome do bucket está correto?)
2. **Políticas IAM** (a Lambda tem permissão para a operação S3 necessária?)
3. **CORS** (domínio do CloudFront está correto tanto no S3 quanto na API Gateway?)
4. **Bucket Policy** (frontend bucket tem policy do CloudFront?)
5. **Event Notification** (prefixo `entrada/` está correto?)
6. **CloudWatch Logs** (verifique erros detalhados)

---

## Próximos Passos

Após completar a implantação:

1. 📖 Leia `TESTES.md` para cenários de teste detalhados
2. 🔍 Consulte `TROUBLESHOOTING.md` se encontrar problemas
3. 💰 Leia `CUSTOS.md` para entender os custos envolvidos
4. 🧹 Quando terminar os estudos, siga `LIMPEZA.md` para remover todos os recursos e evitar cobranças

---

> **Parabéns!** 🎉 Se todos os testes da Etapa 17 passaram, seu Cofre Digital de Documentos está totalmente funcional. Explore, experimente e aprenda!
