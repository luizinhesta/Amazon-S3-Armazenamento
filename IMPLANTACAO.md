# Guia de ImplantaÃ§Ã£o â€” Cofre Digital de Arquivos com Amazon S3

> **Documento passo a passo para criaÃ§Ã£o de TODOS os recursos via Console AWS.**  
> Escrito para quem nunca usou o Console AWS antes. Cada etapa indica o serviÃ§o, menu, botÃ£o, campo, valor exato e resultado esperado.

---

## Placeholders Utilizados Neste Documento

| Placeholder | DescriÃ§Ã£o | Exemplo |
|-------------|-----------|---------|
| `<AWS_ACCOUNT_ID>` | ID numÃ©rico de 12 dÃ­gitos da sua conta AWS | `123456789012` |
| `<AWS_REGION>` | RegiÃ£o AWS selecionada (recomendado: `us-east-1`) | `us-east-1` |
| `<BUCKET_DOCUMENTOS>` | Nome do bucket de documentos | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` |
| `<BUCKET_FRONTEND>` | Nome do bucket do frontend | `cofre-documentos-frontend-<AWS_ACCOUNT_ID>` |
| `<DOMINIO_CLOUDFRONT>` | DomÃ­nio da distribuiÃ§Ã£o CloudFront | `dXXXXXXXXXXXXX.cloudfront.net` |
| `<API_GATEWAY_URL>` | URL de invocaÃ§Ã£o da API Gateway | `https://xxxxxxxxxx.execute-api.<AWS_REGION>.amazonaws.com` |
| `<DISTRIBUTION_ID>` | ID da distribuiÃ§Ã£o CloudFront | `E1A2B3C4D5E6F7` |

> **Dica:** Antes de comeÃ§ar, abra um editor de texto (Notepad, VS Code, etc.) e crie um arquivo `meus-recursos.txt` para anotar cada ARN, URL e ID gerado durante a implantaÃ§Ã£o.

---

## PrÃ©-requisitos

### 1. Conta AWS Ativa

- Acesse [https://aws.amazon.com](https://aws.amazon.com)
- Se nÃ£o possui conta, clique em **Criar uma conta da AWS** e siga o processo de cadastro
- VocÃª precisarÃ¡ de: e-mail vÃ¡lido, cartÃ£o de crÃ©dito/dÃ©bito (para verificaÃ§Ã£o), nÃºmero de telefone
- ApÃ³s criaÃ§Ã£o, aguarde a ativaÃ§Ã£o (pode levar atÃ© 24h, mas geralmente Ã© instantÃ¢neo)

### 2. SeleÃ§Ã£o de RegiÃ£o

- No canto superior direito do Console AWS, clique no nome da regiÃ£o atual
- Selecione **US East (N. Virginia) us-east-1** (recomendado por ter todos os serviÃ§os e menor latÃªncia para testes)
- **IMPORTANTE:** Mantenha a mesma regiÃ£o em TODAS as etapas. Trocar de regiÃ£o farÃ¡ com que recursos fiquem invisÃ­veis entre si

### 3. UsuÃ¡rio IAM com Acesso Administrativo

> Se vocÃª estÃ¡ usando a conta root (e-mail de cadastro), pule esta seÃ§Ã£o. Para produÃ§Ã£o, recomenda-se criar um usuÃ¡rio IAM.

- Acesse **IAM** (digite "IAM" na barra de busca superior e clique no serviÃ§o)
- No menu lateral esquerdo, clique em **Users** (UsuÃ¡rios)
- Clique no botÃ£o **Create user** (Criar usuÃ¡rio)
- **User name**: `admin-cofre-digital`
- Marque âœ… **Provide user access to the AWS Management Console**
- Selecione **I want to create an IAM user**
- **Console password**: Selecione **Custom password** e defina uma senha forte
- Desmarque â˜ **Users must create a new password at next sign-in**
- Clique em **Next**
- Na tela de permissÃµes, selecione **Attach policies directly**
- Na busca, digite `AdministratorAccess` e marque âœ… a polÃ­tica **AdministratorAccess**
- Clique em **Next** â†’ **Create user**
- **Anote** a URL de login do console (formato: `https://<AWS_ACCOUNT_ID>.signin.aws.amazon.com/console`)
- FaÃ§a logout da conta root e login com o usuÃ¡rio IAM criado

### 4. Obter o Account ID

- No canto superior direito, clique no nome do seu usuÃ¡rio/conta
- O **Account ID** (12 dÃ­gitos) aparece no menu dropdown
- **Anote** este nÃºmero â€” serÃ¡ usado em todos os nomes de recursos como `<AWS_ACCOUNT_ID>`

---

## Etapa 1: Criar Bucket de Documentos

Este bucket armazenarÃ¡ todos os documentos do cofre digital (uploads, processados, rejeitados e temporÃ¡rios).

### Passo a passo

1. Na barra de busca superior do Console AWS, digite **S3** e clique no serviÃ§o **S3**
2. Clique no botÃ£o laranja **Create bucket** (Criar bucket)
3. Preencha os campos conforme abaixo:

| Campo | Valor |
|-------|-------|
| **Bucket name** | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` (substitua pelo seu ID de 12 dÃ­gitos) |
| **AWS Region** | `US East (N. Virginia) us-east-1` (deve jÃ¡ estar selecionada) |

4. **Object Ownership**: Mantenha selecionado **ACLs disabled (recommended)** â€” Bucket owner enforced
   - Isso garante que apenas o dono do bucket controla acesso via polÃ­ticas

5. **Block Public Access settings for this bucket**:
   - Mantenha âœ… marcado **Block *all* public access**
   - Este bucket NUNCA deve ser pÃºblico â€” acesso serÃ¡ apenas via Lambda e URLs prÃ©-assinadas

6. **Bucket Versioning**:
   - Selecione âœ… **Enable**
   - Isso permite manter histÃ³rico de versÃµes dos documentos

7. **Tags** (opcional mas recomendado):
   - Clique em **Add tag**
   - Key: `projeto` | Value: `cofre-digital`
   - Clique em **Add tag** novamente
   - Key: `ambiente` | Value: `producao`

8. **Default encryption**:
   - **Encryption type**: Selecione **Server-side encryption with Amazon S3 managed keys (SSE-S3)**
   - **Bucket Key**: Mantenha **Enable** selecionado (reduz custos de criptografia)

9. Clique no botÃ£o laranja **Create bucket** no final da pÃ¡gina

### VerificaÃ§Ã£o

- VocÃª serÃ¡ redirecionado para a lista de buckets
- O bucket `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` deve aparecer na lista
- Clique no nome do bucket para abri-lo
- Verifique na aba **Properties**: Versioning estÃ¡ **Enabled**, Encryption mostra **SSE-S3**
- Verifique na aba **Permissions**: Block public access mostra **On** para todos os 4 itens

### Anote

- **Nome do bucket**: `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>`
- **ARN do bucket**: `arn:aws:s3:::cofre-documentos-arquivos-<AWS_ACCOUNT_ID>`
- Estes valores serÃ£o usados nas polÃ­ticas IAM (Etapa 5) e nas variÃ¡veis de ambiente das Lambdas (Etapa 7)

---

## Etapa 2: Configurar CORS do Bucket de Documentos

O CORS (Cross-Origin Resource Sharing) permite que o navegador do usuÃ¡rio envie e receba arquivos diretamente do S3 via URLs prÃ©-assinadas. Sem esta configuraÃ§Ã£o, o upload/download via navegador serÃ¡ bloqueado.

### Passo a passo

1. No Console S3, clique no bucket **cofre-documentos-arquivos-<AWS_ACCOUNT_ID>**
2. Clique na aba **Permissions** (PermissÃµes)
3. Role a pÃ¡gina atÃ© a seÃ§Ã£o **Cross-origin resource sharing (CORS)**
4. Clique no botÃ£o **Edit** (Editar)
5. Apague qualquer conteÃºdo existente no campo de texto
6. Cole o JSON abaixo (Ã© o conteÃºdo do arquivo `s3/cors-documentos.json` deste repositÃ³rio):

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

> **ATENÃ‡ÃƒO:** Neste momento, vocÃª ainda nÃ£o tem o domÃ­nio CloudFront (serÃ¡ criado na Etapa 12). Por enquanto, use `"https://placeholder.cloudfront.net"` como valor temporÃ¡rio. Na **Etapa 14**, vocÃª voltarÃ¡ aqui para substituir pelo domÃ­nio real.

7. Clique no botÃ£o laranja **Save changes** (Salvar alteraÃ§Ãµes)

### ExplicaÃ§Ã£o dos campos

| Campo | Significado |
|-------|-------------|
| `AllowedHeaders: ["*"]` | Aceita qualquer header na requisiÃ§Ã£o (necessÃ¡rio para Content-Type e metadados) |
| `AllowedMethods: ["PUT", "GET", "HEAD"]` | Permite upload (PUT), download (GET) e verificaÃ§Ã£o (HEAD) |
| `AllowedOrigins` | DomÃ­nio que pode fazer requisiÃ§Ãµes â€” serÃ¡ o CloudFront do frontend |
| `ExposeHeaders: ["ETag", "x-amz-version-id"]` | Permite que o navegador leia esses headers da resposta do S3 |
| `MaxAgeSeconds: 3000` | Navegador pode cachear a resposta do preflight (OPTIONS) por 50 minutos |

### VerificaÃ§Ã£o

- ApÃ³s salvar, a seÃ§Ã£o CORS deve exibir o JSON configurado
- Se mostrar "No CORS configuration", algo deu errado â€” tente novamente

---

## Etapa 3: Aplicar Bucket Policy (HTTPS ObrigatÃ³rio)

Esta polÃ­tica nega qualquer operaÃ§Ã£o S3 que nÃ£o utilize HTTPS, garantindo que todo o trÃ¡fego seja criptografado em trÃ¢nsito.

### Passo a passo

1. No Console S3, clique no bucket **cofre-documentos-arquivos-<AWS_ACCOUNT_ID>**
2. Clique na aba **Permissions** (PermissÃµes)
3. Role atÃ© a seÃ§Ã£o **Bucket policy**
4. Clique no botÃ£o **Edit** (Editar)
5. Apague qualquer conteÃºdo existente no campo de texto
6. Cole o JSON abaixo (Ã© o conteÃºdo do arquivo `s3/bucket-policy-documentos.json` deste repositÃ³rio):

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

7. **IMPORTANTE:** Substitua `<AWS_ACCOUNT_ID>` pelo seu ID de 12 dÃ­gitos nos dois campos `Resource`
8. Clique no botÃ£o laranja **Save changes** (Salvar alteraÃ§Ãµes)

### ExplicaÃ§Ã£o da polÃ­tica

| Elemento | Significado |
|----------|-------------|
| `Effect: Deny` | Nega a aÃ§Ã£o |
| `Principal: *` | Aplica a qualquer identidade (usuÃ¡rios, roles, serviÃ§os) |
| `Action: s3:*` | Qualquer operaÃ§Ã£o S3 |
| `Resource` | O bucket e todos os objetos dentro dele (`/*`) |
| `Condition: aws:SecureTransport = false` | Aplica a condiÃ§Ã£o apenas quando a requisiÃ§Ã£o NÃƒO usa HTTPS |

**Resultado:** Qualquer tentativa de acessar o bucket via HTTP (sem TLS) serÃ¡ negada.

### VerificaÃ§Ã£o

- ApÃ³s salvar, a seÃ§Ã£o Bucket policy deve exibir o JSON da polÃ­tica
- O banner amarelo "Bucket and objects not public" deve continuar aparecendo (a polÃ­tica nÃ£o torna pÃºblico)

---

## Etapa 4: Criar Prefixos (Estrutura de Pastas)

No S3, "pastas" sÃ£o na verdade prefixos de objetos. Vamos criar a estrutura organizacional do bucket criando objetos vazios com `/` no final (que o Console exibe como pastas).

### Passo a passo

1. No Console S3, clique no bucket **cofre-documentos-arquivos-<AWS_ACCOUNT_ID>**
2. VocÃª estÃ¡ na aba **Objects** (Objetos)
3. Clique no botÃ£o **Create folder** (Criar pasta)

### Criar pasta: `entrada/`

4. No campo **Folder name**, digite: `entrada`
5. **Server-side encryption**: Mantenha **Do not specify an encryption key** (herda do bucket)
6. Clique em **Create folder**

### Criar subpastas dentro de `entrada/`

7. Clique na pasta **entrada/** que acabou de aparecer
8. Agora vocÃª estÃ¡ dentro de `entrada/`. Clique em **Create folder**
9. **Folder name**: `contratos` â†’ Clique **Create folder**
10. Clique em **Create folder** novamente
11. **Folder name**: `notas-fiscais` â†’ Clique **Create folder**
12. Repita para: `relatorios`, `comprovantes`, `outros`

### Criar pasta: `processados/`

13. Navegue de volta Ã  raiz do bucket clicando no nome do bucket no breadcrumb (trilha de navegaÃ§Ã£o no topo)
14. Clique em **Create folder**
15. **Folder name**: `processados` â†’ Clique **Create folder**
16. Clique na pasta **processados/**
17. Crie as mesmas subpastas: `contratos`, `notas-fiscais`, `relatorios`, `comprovantes`, `outros`

### Criar pasta: `rejeitados/`

18. Volte Ã  raiz do bucket
19. Clique em **Create folder**
20. **Folder name**: `rejeitados` â†’ Clique **Create folder**

### Criar pasta: `temporarios/`

21. Clique em **Create folder**
22. **Folder name**: `temporarios` â†’ Clique **Create folder**

### Criar pasta: `laboratorio/`

23. Clique em **Create folder**
24. **Folder name**: `laboratorio` â†’ Clique **Create folder**
25. Clique na pasta **laboratorio/**
26. Crie as subpastas: `standard`, `intelligent-tiering`, `glacier-flexible`, `deep-archive`

### Estrutura final

ApÃ³s concluir, a raiz do bucket deve mostrar:

```
entrada/
â”œâ”€â”€ contratos/
â”œâ”€â”€ notas-fiscais/
â”œâ”€â”€ relatorios/
â”œâ”€â”€ comprovantes/
â””â”€â”€ outros/
processados/
â”œâ”€â”€ contratos/
â”œâ”€â”€ notas-fiscais/
â”œâ”€â”€ relatorios/
â”œâ”€â”€ comprovantes/
â””â”€â”€ outros/
rejeitados/
temporarios/
laboratorio/
â”œâ”€â”€ standard/
â”œâ”€â”€ intelligent-tiering/
â”œâ”€â”€ glacier-flexible/
â””â”€â”€ deep-archive/
```

### VerificaÃ§Ã£o

- Na raiz do bucket, vocÃª deve ver 5 "pastas": entrada/, processados/, rejeitados/, temporarios/, laboratorio/
- Clique em cada uma para verificar que as subpastas foram criadas corretamente

### Nota importante

> O S3 nÃ£o possui "pastas" reais. Cada "pasta" Ã© um objeto de 0 bytes com o nome terminando em `/`. Quando a Lambda cria objetos com prefixos como `processados/contratos/arquivo.pdf`, a "pasta" aparece automaticamente â€” mas criÃ¡-las antecipadamente ajuda na organizaÃ§Ã£o visual.

---

## Etapa 5: Criar PolÃ­ticas IAM

Cada funÃ§Ã£o Lambda terÃ¡ sua prÃ³pria polÃ­tica IAM com permissÃµes mÃ­nimas (princÃ­pio do menor privilÃ©gio). Nesta etapa, criaremos 6 polÃ­ticas customizadas.

### Passo a passo geral

1. Na barra de busca superior, digite **IAM** e clique no serviÃ§o **IAM**
2. No menu lateral esquerdo, clique em **Policies** (PolÃ­ticas)
3. Clique no botÃ£o **Create policy** (Criar polÃ­tica)

---

### PolÃ­tica 1: `cofre-policy-gerar-url-upload`

4. Na tela de criaÃ§Ã£o, clique na aba **JSON** (ao lado de Visual)
5. Apague o conteÃºdo padrÃ£o e cole o JSON abaixo (arquivo `iam/gerar-url-upload-policy.json`):

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

6. **Substitua** `<AWS_ACCOUNT_ID>` pelo seu ID de 12 dÃ­gitos (aparece 2 vezes)
7. **Substitua** `<AWS_REGION>` por `us-east-1` (ou sua regiÃ£o escolhida)
8. Clique em **Next** (PrÃ³ximo)
9. No campo **Policy name**: digite `cofre-policy-gerar-url-upload`
10. No campo **Description**: digite `Permite upload de objetos no prefixo entrada/ e logs no CloudWatch`
11. Em **Tags**, adicione: Key: `projeto` | Value: `cofre-digital`
12. Clique em **Create policy** (Criar polÃ­tica)

---

### PolÃ­tica 2: `cofre-policy-processar-documento`

13. Volte para **Policies** â†’ **Create policy** â†’ aba **JSON**
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

### PolÃ­tica 3: `cofre-policy-listar-documentos`

20. **Policies** â†’ **Create policy** â†’ aba **JSON**
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
23. **Next** â†’ **Policy name**: `cofre-policy-listar-documentos`
24. **Description**: `Permite listar bucket no prefixo processados/ e ler objetos e tags`
25. **Create policy**

---

### PolÃ­tica 4: `cofre-policy-gerar-url-download`

26. **Policies** â†’ **Create policy** â†’ aba **JSON**
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
29. **Next** â†’ **Policy name**: `cofre-policy-gerar-url-download`
30. **Description**: `Permite leitura de objetos em processados/ para geraÃ§Ã£o de URL de download`
31. **Create policy**

---

### PolÃ­tica 5: `cofre-policy-listar-versoes`

32. **Policies** â†’ **Create policy** â†’ aba **JSON**
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
35. **Next** â†’ **Policy name**: `cofre-policy-listar-versoes`
36. **Description**: `Permite listar versÃµes de objetos em processados/`
37. **Create policy**

---

### PolÃ­tica 6: `cofre-policy-restaurar-documento`

38. **Policies** â†’ **Create policy** â†’ aba **JSON**
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
41. **Next** â†’ **Policy name**: `cofre-policy-restaurar-documento`
42. **Description**: `Permite restaurar objetos Glacier e ler objetos em processados/`
43. **Create policy**

### VerificaÃ§Ã£o

- No menu **Policies**, use o filtro **Customer managed** (polÃ­ticas gerenciadas pelo cliente)
- VocÃª deve ver 6 polÃ­ticas comeÃ§ando com `cofre-policy-`:
  1. `cofre-policy-gerar-url-upload`
  2. `cofre-policy-processar-documento`
  3. `cofre-policy-listar-documentos`
  4. `cofre-policy-gerar-url-download`
  5. `cofre-policy-listar-versoes`
  6. `cofre-policy-restaurar-documento`

---

## Etapa 6: Criar Roles IAM

Cada funÃ§Ã£o Lambda precisa de um IAM Role (papel) que define com qual identidade ela executa. O Role combina uma trust policy (quem pode assumir o papel) com as polÃ­ticas de permissÃ£o criadas na Etapa 5.

### Passo a passo geral

1. No Console IAM, no menu lateral esquerdo, clique em **Roles** (FunÃ§Ãµes)
2. Clique no botÃ£o **Create role** (Criar funÃ§Ã£o)

---

### Role 1: `cofre-role-gerar-url-upload`

3. **Select trusted entity** (Selecionar entidade confiÃ¡vel):
   - Tipo: Selecione **AWS service**
   - **Use case**: Na seÃ§Ã£o "Use cases for other AWS services", no dropdown, selecione **Lambda**
   - Clique em **Next**

4. **Add permissions** (Adicionar permissÃµes):
   - Na barra de busca, digite `cofre-policy-gerar-url-upload`
   - Marque âœ… a polÃ­tica **cofre-policy-gerar-url-upload**
   - Clique em **Next**

5. **Name, review, and create**:
   - **Role name**: `cofre-role-gerar-url-upload`
   - **Description**: `Role para a Lambda que gera URLs prÃ©-assinadas de upload`
   - Em **Tags**, adicione: Key: `projeto` | Value: `cofre-digital`
   - Clique em **Create role**

6. **Anote o ARN do role** (aparece na confirmaÃ§Ã£o): `arn:aws:iam::<AWS_ACCOUNT_ID>:role/cofre-role-gerar-url-upload`

---

### Role 2: `cofre-role-processar-documento`

7. **Roles** â†’ **Create role**
8. **Trusted entity**: AWS service â†’ Lambda â†’ **Next**
9. **Permissions**: Busque `cofre-policy-processar-documento` â†’ Marque âœ… â†’ **Next**
10. **Role name**: `cofre-role-processar-documento`
11. **Description**: `Role para a Lambda que processa documentos enviados`
12. **Create role**

---

### Role 3: `cofre-role-listar-documentos`

13. **Roles** â†’ **Create role**
14. **Trusted entity**: AWS service â†’ Lambda â†’ **Next**
15. **Permissions**: Busque `cofre-policy-listar-documentos` â†’ Marque âœ… â†’ **Next**
16. **Role name**: `cofre-role-listar-documentos`
17. **Description**: `Role para a Lambda que lista documentos processados`
18. **Create role**

---

### Role 4: `cofre-role-gerar-url-download`

19. **Roles** â†’ **Create role**
20. **Trusted entity**: AWS service â†’ Lambda â†’ **Next**
21. **Permissions**: Busque `cofre-policy-gerar-url-download` â†’ Marque âœ… â†’ **Next**
22. **Role name**: `cofre-role-gerar-url-download`
23. **Description**: `Role para a Lambda que gera URLs prÃ©-assinadas de download`
24. **Create role**

---

### Role 5: `cofre-role-listar-versoes`

25. **Roles** â†’ **Create role**
26. **Trusted entity**: AWS service â†’ Lambda â†’ **Next**
27. **Permissions**: Busque `cofre-policy-listar-versoes` â†’ Marque âœ… â†’ **Next**
28. **Role name**: `cofre-role-listar-versoes`
29. **Description**: `Role para a Lambda que lista versÃµes de documentos`
30. **Create role**

---

### Role 6: `cofre-role-restaurar-documento`

31. **Roles** â†’ **Create role**
32. **Trusted entity**: AWS service â†’ Lambda â†’ **Next**
33. **Permissions**: Busque `cofre-policy-restaurar-documento` â†’ Marque âœ… â†’ **Next**
34. **Role name**: `cofre-role-restaurar-documento`
35. **Description**: `Role para a Lambda que restaura documentos Glacier`
36. **Create role**

---

### VerificaÃ§Ã£o

- No menu **Roles**, busque `cofre-role`
- VocÃª deve ver 6 roles:
  1. `cofre-role-gerar-url-upload`
  2. `cofre-role-processar-documento`
  3. `cofre-role-listar-documentos`
  4. `cofre-role-gerar-url-download`
  5. `cofre-role-listar-versoes`
  6. `cofre-role-restaurar-documento`
- Clique em qualquer role e verifique:
  - Na aba **Trust relationships**: A trust policy deve mostrar `lambda.amazonaws.com`
  - Na aba **Permissions**: A polÃ­tica customizada deve estar listada

---

## Etapa 7: Criar FunÃ§Ãµes Lambda

Nesta etapa, criaremos as 6 funÃ§Ãµes Lambda que compÃµem o backend do Cofre Digital. Cada funÃ§Ã£o usa Python 3.12 e o cÃ³digo-fonte estÃ¡ no diretÃ³rio `lambdas/` deste repositÃ³rio.

### Estrutura dos arquivos Lambda no repositÃ³rio

```
lambdas/
â”œâ”€â”€ shared/                          â† MÃ³dulo compartilhado (copiar para cada Lambda)
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ validation.py
â”‚   â”œâ”€â”€ key_builder.py
â”‚   â””â”€â”€ response.py
â”œâ”€â”€ gerar_url_upload/
â”‚   â””â”€â”€ lambda_function.py
â”œâ”€â”€ processar_documento/
â”‚   â””â”€â”€ lambda_function.py
â”œâ”€â”€ listar_documentos/
â”‚   â””â”€â”€ lambda_function.py
â”œâ”€â”€ gerar_url_download/
â”‚   â””â”€â”€ lambda_function.py
â”œâ”€â”€ listar_versoes/
â”‚   â””â”€â”€ lambda_function.py
â””â”€â”€ restaurar_documento/
â”‚   â””â”€â”€ lambda_function.py
```

> **IMPORTANTE:** Cada funÃ§Ã£o Lambda precisa do mÃ³dulo `shared/` junto com seu cÃ³digo. Ao fazer upload, vocÃª precisarÃ¡ incluir tanto o `lambda_function.py` quanto a pasta `shared/` em um arquivo ZIP.

### Como preparar o arquivo ZIP para cada Lambda

Para cada funÃ§Ã£o Lambda, faÃ§a o seguinte no seu computador:

1. Crie uma pasta temporÃ¡ria (ex: `deploy-gerar-url-upload/`)
2. Copie o arquivo `lambdas/gerar_url_upload/lambda_function.py` para dentro dela
3. Copie a pasta `lambdas/shared/` inteira para dentro dela
4. Selecione **todos os arquivos dentro** da pasta (NÃƒO a pasta em si)
5. Crie um arquivo ZIP com esses itens (lambda_function.py + shared/)
6. O ZIP resultante deve ter esta estrutura:
   ```
   lambda_function.py
   shared/
   â”œâ”€â”€ __init__.py
   â”œâ”€â”€ validation.py
   â”œâ”€â”€ key_builder.py
   â””â”€â”€ response.py
   ```

> **Dica no Windows:** Selecione os arquivos â†’ BotÃ£o direito â†’ Enviar para â†’ Pasta compactada (zip)  
> **Dica no Mac/Linux:** `cd deploy-gerar-url-upload && zip -r ../gerar-url-upload.zip .`

---

### Lambda 1: `cofre-gerar-url-upload`

1. Na barra de busca superior, digite **Lambda** e clique no serviÃ§o **Lambda**
2. Verifique que a regiÃ£o no canto superior direito Ã© **us-east-1**
3. Clique no botÃ£o **Create function** (Criar funÃ§Ã£o)
4. Selecione **Author from scratch** (Criar do zero)
5. Preencha:

| Campo | Valor |
|-------|-------|
| **Function name** | `cofre-gerar-url-upload` |
| **Runtime** | `Python 3.12` |
| **Architecture** | `x86_64` |

6. Expanda a seÃ§Ã£o **Change default execution role** (Alterar role de execuÃ§Ã£o padrÃ£o):
   - Selecione **Use an existing role** (Usar uma role existente)
   - No dropdown **Existing role**, selecione `cofre-role-gerar-url-upload`

7. Clique em **Create function**

8. Na pÃ¡gina da funÃ§Ã£o criada, na seÃ§Ã£o **Code source**:
   - Clique no dropdown **Upload from** (Carregar de)
   - Selecione **.zip file**
   - Clique em **Upload** e selecione o arquivo ZIP preparado (com lambda_function.py + shared/)
   - Clique em **Save**

9. Na aba **Configuration** (ConfiguraÃ§Ã£o), clique em **Environment variables** (VariÃ¡veis de ambiente) no menu lateral:
   - Clique em **Edit** (Editar)
   - Clique em **Add environment variable** para cada variÃ¡vel abaixo:

| Key | Value |
|-----|-------|
| `DOCUMENT_BUCKET` | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` |
| `UPLOAD_PREFIX` | `entrada` |
| `URL_EXPIRATION_SECONDS` | `300` |
| `MAX_FILE_SIZE_MB` | `20` |

   - Clique em **Save**

10. Na aba **Configuration**, clique em **General configuration** (ConfiguraÃ§Ã£o geral):
    - Clique em **Edit**
    - **Memory**: `128` MB
    - **Timeout**: `0` min `30` sec
    - Clique em **Save**

---

### Lambda 2: `cofre-processar-documento`

11. **Lambda** â†’ **Create function** â†’ **Author from scratch**
12. Preencha:

| Campo | Valor |
|-------|-------|
| **Function name** | `cofre-processar-documento` |
| **Runtime** | `Python 3.12` |
| **Architecture** | `x86_64` |
| **Existing role** | `cofre-role-processar-documento` |

13. **Create function**
14. Upload do ZIP (lambda_function.py da pasta `processar_documento` + shared/)
15. **Configuration** â†’ **Environment variables** â†’ **Edit**:

| Key | Value |
|-----|-------|
| `DOCUMENT_BUCKET` | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` |
| `SOURCE_PREFIX` | `entrada` |
| `PROCESSED_PREFIX` | `processados` |
| `REJECTED_PREFIX` | `rejeitados` |

16. **Save**
17. **General configuration** â†’ Memory: `128` MB, Timeout: `30` sec â†’ **Save**

---

### Lambda 3: `cofre-listar-documentos`

18. **Lambda** â†’ **Create function** â†’ **Author from scratch**
19. Preencha:

| Campo | Valor |
|-------|-------|
| **Function name** | `cofre-listar-documentos` |
| **Runtime** | `Python 3.12` |
| **Architecture** | `x86_64` |
| **Existing role** | `cofre-role-listar-documentos` |

20. **Create function**
21. Upload do ZIP (lambda_function.py da pasta `listar_documentos` + shared/)
22. **Configuration** â†’ **Environment variables** â†’ **Edit**:

| Key | Value |
|-----|-------|
| `DOCUMENT_BUCKET` | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` |
| `PROCESSED_PREFIX` | `processados` |

23. **Save**
24. **General configuration** â†’ Memory: `128` MB, Timeout: `30` sec â†’ **Save**

---

### Lambda 4: `cofre-gerar-url-download`

25. **Lambda** â†’ **Create function** â†’ **Author from scratch**
26. Preencha:

| Campo | Valor |
|-------|-------|
| **Function name** | `cofre-gerar-url-download` |
| **Runtime** | `Python 3.12` |
| **Architecture** | `x86_64` |
| **Existing role** | `cofre-role-gerar-url-download` |

27. **Create function**
28. Upload do ZIP (lambda_function.py da pasta `gerar_url_download` + shared/)
29. **Configuration** â†’ **Environment variables** â†’ **Edit**:

| Key | Value |
|-----|-------|
| `DOCUMENT_BUCKET` | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` |
| `PROCESSED_PREFIX` | `processados` |
| `URL_EXPIRATION_SECONDS` | `300` |

30. **Save**
31. **General configuration** â†’ Memory: `128` MB, Timeout: `30` sec â†’ **Save**

---

### Lambda 5: `cofre-listar-versoes`

32. **Lambda** â†’ **Create function** â†’ **Author from scratch**
33. Preencha:

| Campo | Valor |
|-------|-------|
| **Function name** | `cofre-listar-versoes` |
| **Runtime** | `Python 3.12` |
| **Architecture** | `x86_64` |
| **Existing role** | `cofre-role-listar-versoes` |

34. **Create function**
35. Upload do ZIP (lambda_function.py da pasta `listar_versoes` + shared/)
36. **Configuration** â†’ **Environment variables** â†’ **Edit**:

| Key | Value |
|-----|-------|
| `DOCUMENT_BUCKET` | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` |
| `PROCESSED_PREFIX` | `processados` |
| `URL_EXPIRATION_SECONDS` | `300` |

37. **Save**
38. **General configuration** â†’ Memory: `128` MB, Timeout: `30` sec â†’ **Save**

---

### Lambda 6: `cofre-restaurar-documento`

39. **Lambda** â†’ **Create function** â†’ **Author from scratch**
40. Preencha:

| Campo | Valor |
|-------|-------|
| **Function name** | `cofre-restaurar-documento` |
| **Runtime** | `Python 3.12` |
| **Architecture** | `x86_64` |
| **Existing role** | `cofre-role-restaurar-documento` |

41. **Create function**
42. Upload do ZIP (lambda_function.py da pasta `restaurar_documento` + shared/)
43. **Configuration** â†’ **Environment variables** â†’ **Edit**:

| Key | Value |
|-----|-------|
| `DOCUMENT_BUCKET` | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` |
| `PROCESSED_PREFIX` | `processados` |
| `DEFAULT_RESTORE_DAYS` | `2` |

44. **Save**
45. **General configuration** â†’ Memory: `128` MB, Timeout: `30` sec â†’ **Save**

---

### VerificaÃ§Ã£o de cada Lambda

Para cada Lambda criada, faÃ§a um teste rÃ¡pido:

1. Na pÃ¡gina da funÃ§Ã£o, clique na aba **Test**
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
5. **Resultado esperado**: A funÃ§Ã£o deve executar sem erro de importaÃ§Ã£o (pode retornar erro de validaÃ§Ã£o como "campo obrigatÃ³rio", o que Ã© normal â€” significa que o cÃ³digo carregou corretamente)

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

> **Nota:** Este teste pode falhar com "Access Denied" se o arquivo nÃ£o existir no bucket â€” isso Ã© esperado. O importante Ã© que nÃ£o haja `ImportError` ou `ModuleNotFoundError`.

---

## Etapa 8: Configurar Trigger S3 â†’ Lambda processar-documento

Este trigger faz com que o S3 invoque automaticamente a Lambda `cofre-processar-documento` sempre que um novo objeto Ã© criado no prefixo `entrada/`.

### Passo a passo

1. Na barra de busca superior, digite **S3** e acesse o serviÃ§o
2. Clique no bucket **cofre-documentos-arquivos-<AWS_ACCOUNT_ID>**
3. Clique na aba **Properties** (Propriedades)
4. Role a pÃ¡gina atÃ© a seÃ§Ã£o **Event notifications** (NotificaÃ§Ãµes de eventos)
5. Clique no botÃ£o **Create event notification** (Criar notificaÃ§Ã£o de evento)
6. Preencha:

| Campo | Valor |
|-------|-------|
| **Event name** | `trigger-processar-documento` |
| **Prefix** | `entrada/` |
| **Suffix** | *(deixe vazio)* |

7. Na seÃ§Ã£o **Event types** (Tipos de evento):
   - Expanda **Object creation** (CriaÃ§Ã£o de objetos)
   - Marque âœ… **All object create events** (`s3:ObjectCreated:*`)

8. Na seÃ§Ã£o **Destination** (Destino):
   - Selecione **Lambda function**
   - No dropdown **Lambda function**, selecione `cofre-processar-documento`

9. Clique em **Save changes**

### O que acontece por trÃ¡s

- O S3 adicionarÃ¡ automaticamente uma **resource-based policy** na funÃ§Ã£o Lambda, permitindo que o S3 a invoque
- Isso Ã© configurado automaticamente pelo Console â€” nÃ£o precisa fazer manualmente

### VerificaÃ§Ã£o

1. Volte Ã  aba **Properties** do bucket
2. Na seÃ§Ã£o **Event notifications**, vocÃª deve ver `trigger-processar-documento` listado
3. **Teste prÃ¡tico:**
   - VÃ¡ para a aba **Objects** do bucket
   - Navegue atÃ© `entrada/contratos/`
   - Clique em **Upload** â†’ **Add files** â†’ Selecione um arquivo PDF pequeno â†’ **Upload**
   - Aguarde 5-10 segundos
   - Navegue atÃ© `processados/contratos/` â€” o arquivo deve estar lÃ¡
   - O arquivo em `entrada/contratos/` deve ter desaparecido
4. Se o arquivo nÃ£o apareceu em processados:
   - Acesse **Lambda** â†’ `cofre-processar-documento` â†’ **Monitor** â†’ **View CloudWatch logs**
   - Verifique os logs para identificar o erro

---

## Etapa 9: Criar API Gateway HTTP API

A API Gateway expÃµe as funÃ§Ãµes Lambda como endpoints HTTP acessÃ­veis pelo frontend. Usaremos uma HTTP API (mais simples e barata que REST API).

### Passo a passo

1. Na barra de busca superior, digite **API Gateway** e clique no serviÃ§o
2. Na pÃ¡gina inicial, localize a seÃ§Ã£o **HTTP API** e clique no botÃ£o **Build** (Construir)

### Configurar a API

3. Na tela "Create an API":
   - Clique em **Add integration** (Adicionar integraÃ§Ã£o)
   - **Integration type**: Lambda
   - **AWS Region**: `us-east-1` (sua regiÃ£o)
   - **Lambda function**: Selecione `cofre-gerar-url-upload`
   - Clique em **Add integration** novamente para adicionar as outras:
     - Lambda: `cofre-listar-documentos`
     - Lambda: `cofre-gerar-url-download`
     - Lambda: `cofre-listar-versoes`
     - Lambda: `cofre-restaurar-documento`
   
   > **Nota:** NÃƒO adicione `cofre-processar-documento` aqui â€” ela Ã© acionada pelo S3, nÃ£o pela API

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
   - **Auto-deploy**: Mantenha âœ… ativado
   - Clique em **Next**

### Revisar e Criar

7. Na tela "Review and create":
   - Verifique que todas as 5 rotas estÃ£o corretas
   - Verifique que cada rota aponta para a Lambda correta
   - Clique em **Create** (Criar)

### Copiar a URL de InvocaÃ§Ã£o

8. ApÃ³s a criaÃ§Ã£o, vocÃª serÃ¡ levado Ã  pÃ¡gina da API
9. No menu lateral esquerdo, clique em **Stages** (se nÃ£o estiver jÃ¡ visÃ­vel)
10. Clique no stage **$default**
11. **Copie** a **Invoke URL** que aparece no topo (formato: `https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com`)
12. **Anote esta URL** â€” ela serÃ¡ usada no config.js do frontend (Etapa 11) e na configuraÃ§Ã£o CORS

> **IMPORTANTE:** A URL NÃƒO deve ter barra (`/`) no final. Se tiver, remova-a ao colar no config.js.

### Configurar CORS na API Gateway

13. No menu lateral esquerdo da API, clique em **CORS**
14. Clique em **Configure** (ou **Edit** se jÃ¡ existir configuraÃ§Ã£o)
15. Preencha:

| Campo | Valor |
|-------|-------|
| **Access-Control-Allow-Origin** | `https://<DOMINIO_CLOUDFRONT>` |
| **Access-Control-Allow-Headers** | `content-type` |
| **Access-Control-Allow-Methods** | `GET, POST, OPTIONS` |
| **Access-Control-Max-Age** | `3600` |

> **ATENÃ‡ÃƒO:** Neste momento, vocÃª ainda nÃ£o tem o domÃ­nio CloudFront (serÃ¡ criado na Etapa 12). Por enquanto, use `*` (asterisco) como origin para testes iniciais. Na **Etapa 14**, vocÃª voltarÃ¡ aqui para substituir pelo domÃ­nio real.

16. Clique em **Save**

### VerificaÃ§Ã£o

1. Volte Ã  pÃ¡gina principal da API â†’ **Routes**
2. VocÃª deve ver 5 rotas configuradas
3. **Teste rÃ¡pido via navegador:**
   - Abra uma nova aba e cole: `<API_GATEWAY_URL>/documentos`
   - Resultado esperado: Resposta JSON (pode ser lista vazia ou erro de bucket, dependendo de configuraÃ§Ã£o)
4. **Teste com curl (terminal):**
   ```bash
   curl -X POST <API_GATEWAY_URL>/upload-url \
     -H "Content-Type: application/json" \
     -d '{"filename":"teste.pdf","category":"contratos","contentType":"application/pdf"}'
   ```
   - Resultado esperado: JSON com `uploadUrl`, `key` e `expiresIn`

---

## Etapa 10: Criar Bucket do Frontend

Este bucket armazenarÃ¡ os arquivos estÃ¡ticos do frontend (HTML, CSS, JS). SerÃ¡ privado e acessÃ­vel apenas via CloudFront.

### Passo a passo

1. Na barra de busca superior, digite **S3** e acesse o serviÃ§o
2. Clique em **Create bucket**
3. Preencha:

| Campo | Valor |
|-------|-------|
| **Bucket name** | `cofre-documentos-frontend-<AWS_ACCOUNT_ID>` |
| **AWS Region** | `US East (N. Virginia) us-east-1` |

4. **Object Ownership**: Mantenha **ACLs disabled (recommended)**

5. **Block Public Access settings**:
   - Mantenha âœ… **Block *all* public access**
   - O bucket serÃ¡ privado â€” acesso somente via CloudFront com OAC

6. **Bucket Versioning**: Mantenha **Disable** (nÃ£o necessÃ¡rio para frontend)

7. **Default encryption**:
   - **Encryption type**: **Server-side encryption with Amazon S3 managed keys (SSE-S3)**
   - **Bucket Key**: **Enable**

8. Clique em **Create bucket**

### Upload dos arquivos do frontend

9. Clique no bucket **cofre-documentos-frontend-<AWS_ACCOUNT_ID>** que acabou de criar
10. Clique em **Upload**
11. Clique em **Add files** (Adicionar arquivos)
12. Selecione os 4 arquivos da pasta `frontend/` deste repositÃ³rio:
    - `index.html`
    - `styles.css`
    - `app.js`
    - `config.js`
13. **IMPORTANTE:** Antes de clicar em Upload, expanda a seÃ§Ã£o **Properties** (Propriedades):
    - Na parte **Content type**, o S3 geralmente detecta automaticamente
    - Se nÃ£o detectar, configure manualmente para cada arquivo:
      - `index.html` â†’ `text/html`
      - `styles.css` â†’ `text/css`
      - `app.js` â†’ `application/javascript`
      - `config.js` â†’ `application/javascript`
14. Clique em **Upload**
15. Aguarde a confirmaÃ§Ã£o de que todos os 4 arquivos foram carregados com sucesso
16. Clique em **Close**

### VerificaÃ§Ã£o

- Na aba **Objects** do bucket, vocÃª deve ver os 4 arquivos listados
- Clique em `index.html` â†’ verifique que o Content type estÃ¡ como `text/html`
- **Neste momento, o bucket Ã© privado** â€” tentar acessar via URL do S3 resultarÃ¡ em "Access Denied" (esperado)

---

## Etapa 11: Atualizar config.js com a URL da API Gateway

O arquivo `config.js` contÃ©m a URL base que o frontend usa para chamar a API. VocÃª precisa substituir o placeholder pela URL real obtida na Etapa 9.

### Passo a passo

1. No seu computador, abra o arquivo `frontend/config.js` em um editor de texto
2. Substitua `COLE_AQUI_A_URL_DA_API` pela URL de invocaÃ§Ã£o da API Gateway (copiada na Etapa 9)
3. O arquivo final deve ficar assim:

```javascript
/**
 * ConfiguraÃ§Ã£o do Cofre Digital de Arquivos.
 * 
 * INSTRUÃ‡Ã•ES:
 * Substitua o valor de API_BASE_URL pela URL de invocaÃ§Ã£o
 * da sua API Gateway HTTP API (sem barra final).
 * 
 * Exemplo: https://abc123def.execute-api.us-east-1.amazonaws.com
 */
window.APP_CONFIG = {
    API_BASE_URL: "https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com"
};
```

> **ATENÃ‡ÃƒO:** NÃ£o coloque barra `/` no final da URL. O cÃ³digo JavaScript jÃ¡ adiciona as rotas (ex: `/upload-url`, `/documentos`).

### Re-upload do config.js

4. Acesse o Console S3
5. Clique no bucket **cofre-documentos-frontend-<AWS_ACCOUNT_ID>**
6. VocÃª verÃ¡ o arquivo `config.js` existente na listagem
7. Clique em **Upload**
8. Clique em **Add files** e selecione o `config.js` atualizado do seu computador
9. Clique em **Upload**
10. O S3 substituirÃ¡ o arquivo anterior automaticamente

### VerificaÃ§Ã£o

- Clique no arquivo `config.js` no bucket
- Clique em **Open** (ou no URL do objeto â€” que retornarÃ¡ "Access Denied" pois o bucket Ã© privado)
- Para verificar o conteÃºdo: selecione o arquivo â†’ **Actions** â†’ **Query with S3 Select** (ou baixe o arquivo para verificar localmente)

### Alternativa: Editar diretamente no Console

Se preferir nÃ£o fazer re-upload:

1. No bucket frontend, clique no arquivo `config.js`
2. Na visualizaÃ§Ã£o do objeto, NÃƒO hÃ¡ editor inline no S3
3. A forma mais simples Ã© fazer o re-upload conforme descrito acima

---

## Etapa 12: Criar DistribuiÃ§Ã£o CloudFront

O CloudFront Ã© a CDN (Content Delivery Network) que servirÃ¡ o frontend para os usuÃ¡rios. Ele acessa o bucket privado do frontend usando Origin Access Control (OAC).

### Passo a passo

1. Na barra de busca superior, digite **CloudFront** e clique no serviÃ§o
2. Clique no botÃ£o **Create distribution** (Criar distribuiÃ§Ã£o)

### Configurar Origin (Origem)

3. Preencha a seÃ§Ã£o **Origin**:

| Campo | Valor |
|-------|-------|
| **Origin domain** | Clique no campo e selecione o bucket `cofre-documentos-frontend-<AWS_ACCOUNT_ID>.s3.us-east-1.amazonaws.com` na lista dropdown |
| **Origin path** | *(deixe vazio)* |
| **Name** | SerÃ¡ preenchido automaticamente com o nome do bucket |
| **Origin access** | Selecione **Origin access control settings (recommended)** |

4. ApÃ³s selecionar "Origin access control settings", clique no botÃ£o **Create new OAC** (Criar novo OAC):
   - **Name**: `cofre-frontend-oac` (ou aceite o nome sugerido)
   - **Description**: `OAC para acesso ao bucket frontend do cofre digital`
   - **Signing behavior**: Mantenha **Sign requests (recommended)**
   - **Origin type**: Mantenha **S3**
   - Clique em **Create**

5. O OAC criado serÃ¡ selecionado automaticamente

### Configurar Default Cache Behavior

6. Role atÃ© a seÃ§Ã£o **Default cache behavior**:

| Campo | Valor |
|-------|-------|
| **Compress objects automatically** | âœ… Yes |
| **Viewer protocol policy** | **Redirect HTTP to HTTPS** |
| **Allowed HTTP methods** | **GET, HEAD** |
| **Cache policy** | Selecione **CachingOptimized** (recomendado para estÃ¡ticos) |

7. **Restrict viewer access**: Mantenha **No**

### Configurar Settings

8. Role atÃ© a seÃ§Ã£o **Settings** (no final da pÃ¡gina):

| Campo | Valor |
|-------|-------|
| **Price class** | **Use all edge locations (best performance)** ou **Use only North America and Europe** (para economizar) |
| **AWS WAF** | **Do not enable security protections** (pode ser habilitado posteriormente) |
| **Alternate domain name (CNAME)** | *(deixe vazio â€” usaremos o domÃ­nio .cloudfront.net)* |
| **Custom SSL certificate** | *(deixe vazio)* |
| **Default root object** | `index.html` |
| **Description** | `DistribuiÃ§Ã£o CloudFront para frontend do Cofre Digital` |

9. Clique no botÃ£o laranja **Create distribution**

### Copiar informaÃ§Ãµes importantes

10. ApÃ³s criar, vocÃª serÃ¡ levado Ã  pÃ¡gina da distribuiÃ§Ã£o
11. **Copie e anote:**
    - **Distribution domain name**: `dXXXXXXXXXXXXX.cloudfront.net` â€” este Ã© o `<DOMINIO_CLOUDFRONT>`
    - **Distribution ID**: `E1A2B3C4D5E6F7` â€” este Ã© o `<DISTRIBUTION_ID>`
    - **ARN**: `arn:aws:cloudfront::<AWS_ACCOUNT_ID>:distribution/EXXXXXXXXXXXXXX`

12. **Status**: A distribuiÃ§Ã£o levarÃ¡ **5-15 minutos** para ser implantada. O status mudarÃ¡ de "Deploying" para "Enabled"

### Banner de Bucket Policy

13. Logo apÃ³s criar a distribuiÃ§Ã£o, o Console exibirÃ¡ um **banner azul** no topo dizendo:
    > "The S3 bucket policy needs to be updated"
    
14. Clique no botÃ£o **Copy policy** neste banner
15. **Guarde esta polÃ­tica copiada** â€” ela serÃ¡ usada na Etapa 13

> **Se o banner desapareceu:** VÃ¡ em CloudFront â†’ sua distribuiÃ§Ã£o â†’ aba **Origins** â†’ selecione a origin â†’ **Edit** â†’ Na seÃ§Ã£o "Origin access", o botÃ£o "Copy policy" estarÃ¡ disponÃ­vel.

### VerificaÃ§Ã£o

- ApÃ³s 5-15 minutos, o Status deve mudar para **Enabled** (data de "Last modified" aparece)
- **Ainda nÃ£o funcionarÃ¡** â€” a bucket policy do frontend precisa ser atualizada (Etapa 13)

---

## Etapa 13: Aplicar Bucket Policy do Frontend

O CloudFront precisa de permissÃ£o para ler os objetos do bucket privado do frontend. A bucket policy gerada na Etapa 12 concede essa permissÃ£o via Origin Access Control (OAC).

### Passo a passo

1. Na barra de busca superior, digite **S3** e acesse o serviÃ§o
2. Clique no bucket **cofre-documentos-frontend-<AWS_ACCOUNT_ID>**
3. Clique na aba **Permissions** (PermissÃµes)
4. Role atÃ© a seÃ§Ã£o **Bucket policy**
5. Clique em **Edit** (Editar)
6. Cole a polÃ­tica que vocÃª copiou do banner do CloudFront (Etapa 12, passo 14)

A polÃ­tica deve ser semelhante a esta (arquivo `s3/bucket-policy-frontend.json` do repositÃ³rio):

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

> **IMPORTANTE:** Use a polÃ­tica copiada diretamente do Console do CloudFront (passo 14 da Etapa 12), pois ela jÃ¡ contÃ©m os valores corretos do seu Distribution ID. Se estiver usando o template acima, substitua `<AWS_ACCOUNT_ID>`, `<DISTRIBUTION_ID>` e o nome do bucket.

7. Clique em **Save changes**

### ExplicaÃ§Ã£o da polÃ­tica

| Elemento | Significado |
|----------|-------------|
| `Principal: cloudfront.amazonaws.com` | Apenas o serviÃ§o CloudFront pode ler |
| `Action: s3:GetObject` | Permite apenas leitura de objetos |
| `Resource: .../*` | Aplica a todos os objetos no bucket |
| `Condition: AWS:SourceArn` | Restringe ao seu Distribution ID especÃ­fico â€” outras distribuiÃ§Ãµes CloudFront NÃƒO terÃ£o acesso |

### VerificaÃ§Ã£o

1. Aguarde a distribuiÃ§Ã£o CloudFront finalizar o deploy (Status: "Enabled")
2. Abra uma nova aba do navegador
3. Cole o domÃ­nio CloudFront: `https://dXXXXXXXXXXXXX.cloudfront.net`
4. **Resultado esperado:** A pÃ¡gina do Cofre Digital deve carregar (HTML com estilos)
5. Se aparecer o erro "AccessDenied" em XML:
   - Verifique que a bucket policy foi salva corretamente
   - Verifique que o "Default root object" estÃ¡ como `index.html` na distribuiÃ§Ã£o CloudFront
   - Aguarde mais alguns minutos para propagaÃ§Ã£o

---

## Etapa 14: Atualizar CORS com DomÃ­nio CloudFront Real

Agora que vocÃª tem o domÃ­nio real do CloudFront, Ã© necessÃ¡rio atualizar o CORS do bucket de documentos e o CORS da API Gateway com o domÃ­nio correto.

### 14.1 â€” Atualizar CORS do Bucket de Documentos

1. No Console S3, clique no bucket **cofre-documentos-arquivos-<AWS_ACCOUNT_ID>**
2. Clique na aba **Permissions** (PermissÃµes)
3. Role atÃ© **Cross-origin resource sharing (CORS)**
4. Clique em **Edit**
5. Substitua o valor de `AllowedOrigins` pelo domÃ­nio real:

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

6. **Substitua** `dXXXXXXXXXXXXX.cloudfront.net` pelo domÃ­nio real anotado na Etapa 12
7. Clique em **Save changes**

### 14.2 â€” Atualizar CORS da API Gateway

8. Na barra de busca, digite **API Gateway** e acesse o serviÃ§o
9. Clique na API **cofre-digital-api**
10. No menu lateral esquerdo, clique em **CORS**
11. Clique em **Edit** (se jÃ¡ configurou antes) ou **Configure**
12. Atualize:

| Campo | Valor |
|-------|-------|
| **Access-Control-Allow-Origin** | `https://dXXXXXXXXXXXXX.cloudfront.net` (seu domÃ­nio real) |
| **Access-Control-Allow-Headers** | `content-type` |
| **Access-Control-Allow-Methods** | `GET, POST, OPTIONS` |
| **Access-Control-Max-Age** | `3600` |

> **IMPORTANTE:** Se antes vocÃª colocou `*` (asterisco) como origin para testes, agora Ã© hora de substituir pelo domÃ­nio real. Manter `*` funciona mas Ã© menos seguro.

13. Clique em **Save**

### VerificaÃ§Ã£o

1. Abra o DevTools do navegador (F12) â†’ aba **Console**
2. Acesse `https://dXXXXXXXXXXXXX.cloudfront.net`
3. Tente fazer um upload no Cofre Digital
4. Se o CORS estiver correto, **nÃ£o haverÃ¡ erros CORS** no console do navegador
5. Se aparecer erro tipo `Access to fetch at '...' from origin '...' has been blocked by CORS policy`:
   - Verifique que o domÃ­nio no CORS do S3 **e** da API Gateway bate exatamente com o domÃ­nio do CloudFront
   - Inclua o protocolo `https://` no valor
   - **NÃ£o coloque barra `/` no final** do domÃ­nio

---

## Etapa 15: Criar InvalidaÃ§Ã£o no CloudFront

Quando vocÃª atualiza arquivos no bucket do frontend (como o config.js), o CloudFront pode continuar servindo a versÃ£o antiga do cache. Uma invalidaÃ§Ã£o forÃ§a o CloudFront a buscar os arquivos mais recentes do S3.

### Passo a passo

1. Na barra de busca superior, digite **CloudFront** e acesse o serviÃ§o
2. Clique na sua distribuiÃ§Ã£o (identificada pelo domÃ­nio `dXXXXXXXXXXXXX.cloudfront.net`)
3. Clique na aba **Invalidations** (InvalidaÃ§Ãµes)
4. Clique no botÃ£o **Create invalidation** (Criar invalidaÃ§Ã£o)
5. No campo **Object paths** (Caminhos dos objetos), digite:
   ```
   /*
   ```
   (barra asterisco â€” invalida TODOS os arquivos)
6. Clique em **Create invalidation**

### ExplicaÃ§Ã£o

| Path | Efeito |
|------|--------|
| `/*` | Invalida todos os arquivos em cache (mais simples) |
| `/config.js` | Invalida apenas o config.js (mais preciso) |
| `/index.html` | Invalida apenas o HTML |

> **Custo:** As primeiras 1.000 paths de invalidaÃ§Ã£o por mÃªs sÃ£o gratuitas. Usar `/*` conta como 1 path.

### Quando usar invalidaÃ§Ã£o

- ApÃ³s atualizar `config.js` com a URL da API (Etapa 11)
- ApÃ³s atualizar qualquer arquivo do frontend
- Se o navegador mostra uma versÃ£o antiga da pÃ¡gina

### VerificaÃ§Ã£o

1. O status da invalidaÃ§Ã£o mudarÃ¡ de **In Progress** para **Completed** (leva 1-5 minutos)
2. ApÃ³s completar, abra o site em uma janela anÃ´nima/privada: `https://dXXXXXXXXXXXXX.cloudfront.net`
3. O frontend deve carregar com a versÃ£o mais recente dos arquivos
4. Verifique no DevTools (F12 â†’ aba Network) que os arquivos nÃ£o estÃ£o vindo do cache antigo

---

## Etapa 16: Configurar Regras de Lifecycle (Ciclo de Vida)

As regras de Lifecycle automatizam a transiÃ§Ã£o de objetos entre classes de armazenamento e a expiraÃ§Ã£o de objetos antigos. O S3 executa essas regras automaticamente (geralmente uma vez por dia).

### Passo a passo

1. No Console S3, clique no bucket **cofre-documentos-arquivos-<AWS_ACCOUNT_ID>**
2. Clique na aba **Management** (Gerenciamento)
3. Na seÃ§Ã£o **Lifecycle rules** (Regras de ciclo de vida), clique em **Create lifecycle rule**

---

### Regra 1: `arquivar-documentos-processados`

Esta regra transiciona documentos processados para classes mais baratas ao longo do tempo e os expira apÃ³s 2 anos.

4. Preencha:

| Campo | Valor |
|-------|-------|
| **Lifecycle rule name** | `arquivar-documentos-processados` |
| **Choose a rule scope** | Selecione **Limit the scope of this rule using one or more filters** |
| **Prefix** | `processados/` |
| **Object size** | Marque âœ… **Specify minimum object size** â†’ `128` KB (131072 bytes) |

> **Por que filtrar por tamanho?** Objetos muito pequenos (<128KB) nÃ£o se beneficiam de transiÃ§Ã£o para Glacier â€” o custo mÃ­nimo por objeto pode ser maior que a economia.

5. Na seÃ§Ã£o **Lifecycle rule actions**, marque âœ…:
   - âœ… **Move current versions of objects between storage classes**
   - âœ… **Expire current versions of objects**

6. Na seÃ§Ã£o **Transition current versions of objects between storage classes**:
   - Clique em **Add transition**:
     - **Storage class**: `Intelligent-Tiering`
     - **Days after object creation**: `30`
   - Clique em **Add transition** novamente:
     - **Storage class**: `Glacier Flexible Retrieval`
     - **Days after object creation**: `180`
   - Clique em **Add transition** novamente:
     - **Storage class**: `Glacier Deep Archive`
     - **Days after object creation**: `365`

7. Na seÃ§Ã£o **Expire current versions of objects**:
   - **Days after object creation**: `730`

8. Marque âœ… **I acknowledge that this lifecycle rule will apply to all objects in the bucket matching the specified filter**

9. Clique em **Create rule**

---

### Regra 2: `excluir-arquivos-temporarios`

Esta regra expira automaticamente objetos temporÃ¡rios apÃ³s 7 dias.

10. Clique em **Create lifecycle rule** novamente
11. Preencha:

| Campo | Valor |
|-------|-------|
| **Lifecycle rule name** | `excluir-arquivos-temporarios` |
| **Choose a rule scope** | **Limit the scope of this rule using one or more filters** |
| **Prefix** | `temporarios/` |

12. Na seÃ§Ã£o **Lifecycle rule actions**, marque âœ…:
    - âœ… **Expire current versions of objects**
    - âœ… **Permanently delete noncurrent versions of objects**
    - âœ… **Delete expired object delete markers or incomplete multipart uploads**

13. Na seÃ§Ã£o **Expire current versions of objects**:
    - **Days after object creation**: `7`

14. Na seÃ§Ã£o **Permanently delete noncurrent versions of objects**:
    - **Days after objects become noncurrent**: `7`

15. Na seÃ§Ã£o **Delete expired object delete markers or incomplete multipart uploads**:
    - Marque âœ… **Delete incomplete multipart uploads**
    - **Number of days**: `1`

16. Marque âœ… o acknowledgment e clique em **Create rule**

---

### Regra 3: `limpar-versoes-antigas`

Esta regra remove versÃµes nÃ£o-correntes de documentos processados apÃ³s 90 dias e limpa delete markers expirados.

17. Clique em **Create lifecycle rule** novamente
18. Preencha:

| Campo | Valor |
|-------|-------|
| **Lifecycle rule name** | `limpar-versoes-antigas` |
| **Choose a rule scope** | **Limit the scope of this rule using one or more filters** |
| **Prefix** | `processados/` |

19. Na seÃ§Ã£o **Lifecycle rule actions**, marque âœ…:
    - âœ… **Permanently delete noncurrent versions of objects**
    - âœ… **Delete expired object delete markers or incomplete multipart uploads**

20. Na seÃ§Ã£o **Permanently delete noncurrent versions of objects**:
    - **Days after objects become noncurrent**: `90`

21. Na seÃ§Ã£o **Delete expired object delete markers or incomplete multipart uploads**:
    - Marque âœ… **Delete expired object delete markers**

22. Marque âœ… o acknowledgment e clique em **Create rule**

---

### VerificaÃ§Ã£o

- Na aba **Management** do bucket, a seÃ§Ã£o **Lifecycle rules** deve listar 3 regras:
  1. `arquivar-documentos-processados` â€” Status: Enabled
  2. `excluir-arquivos-temporarios` â€” Status: Enabled
  3. `limpar-versoes-antigas` â€” Status: Enabled

### Nota importante sobre Lifecycle

> âš ï¸ **As regras de Lifecycle NÃƒO sÃ£o instantÃ¢neas.** O S3 executa as avaliaÃ§Ãµes de Lifecycle aproximadamente uma vez por dia, em um horÃ¡rio nÃ£o determinÃ­stico. Isso significa:
> - ApÃ³s criar a regra, os objetos **nÃ£o serÃ£o movidos/expirados imediatamente**
> - Pode levar atÃ© 48 horas para a primeira execuÃ§Ã£o
> - Para testar transiÃ§Ãµes de classe, use o mÃ©todo manual descrito na Etapa 18 (Classes de Armazenamento)

---

## Etapa 17: Testar o Projeto

Agora que todos os recursos estÃ£o criados e configurados, vamos validar o funcionamento completo do sistema.

### 17.1 â€” Acessar o Frontend

1. Abra o navegador e acesse: `https://<DOMINIO_CLOUDFRONT>`
2. **Resultado esperado:** A pÃ¡gina do Cofre Digital carrega com:
   - Header "Cofre Digital de Arquivos"
   - Ãrea de upload (campo de arquivo, dropdown de categoria, botÃ£o enviar)
   - Tabela de documentos (pode estar vazia)
   - Cards educacionais sobre classes de armazenamento

3. Abra o DevTools (F12) â†’ aba **Console**
4. **NÃ£o deve haver erros em vermelho.** Se houver erros CORS ou de rede, revise as Etapas 11 e 14

---

### 17.2 â€” Testar Upload de Documento

5. Na interface do Cofre Digital:
   - Clique em **Escolher arquivo** (ou "Browse")
   - Selecione um arquivo PDF pequeno (ou TXT, PNG â€” qualquer extensÃ£o vÃ¡lida)
   - No dropdown de **Categoria**, selecione `contratos`
   - Clique em **Enviar** (ou "Upload")

6. **Resultado esperado:**
   - Mensagem de sucesso aparece
   - O documento deve aparecer na tabela de documentos apÃ³s alguns segundos
   - No DevTools â†’ Network: vocÃª deve ver:
     - `POST /upload-url` â†’ 200 (obtÃ©m URL prÃ©-assinada)
     - `PUT https://...s3...amazonaws.com/entrada/contratos/...` â†’ 200 (upload direto ao S3)

7. **VerificaÃ§Ã£o no Console S3:**
   - Acesse o bucket de documentos no Console S3
   - Navegue atÃ© `processados/contratos/`
   - O arquivo deve estar lÃ¡ (foi processado automaticamente pela Lambda)
   - `entrada/contratos/` deve estar vazio (arquivo foi movido)

---

### 17.3 â€” Verificar Logs no CloudWatch

8. Na barra de busca, digite **CloudWatch** e acesse o serviÃ§o
9. No menu lateral, clique em **Log groups** (Grupos de log)
10. VocÃª deve ver grupos como:
    - `/aws/lambda/cofre-gerar-url-upload`
    - `/aws/lambda/cofre-processar-documento`
11. Clique em `/aws/lambda/cofre-processar-documento`
12. Clique no log stream mais recente
13. **Resultado esperado:** Logs mostrando:
    - "Processando objeto: bucket=..., key=entrada/contratos/..."
    - "Documento vÃ¡lido. Copiando..."
    - "Objeto copiado para: processados/contratos/..."
    - "Objeto original removido: entrada/contratos/..."

---

### 17.4 â€” Testar Download

14. Na interface do Cofre Digital, na tabela de documentos:
    - Localize o documento que vocÃª enviou
    - Clique no botÃ£o **Download** (Ã­cone de download ou link)

15. **Resultado esperado:**
    - O download inicia automaticamente
    - O arquivo baixado deve ser idÃªntico ao original

16. **VerificaÃ§Ã£o no DevTools:**
    - `GET /download-url?key=processados/contratos/...` â†’ 200 (obtÃ©m URL prÃ©-assinada)
    - Redirecionamento para URL do S3 â†’ download do arquivo

---

### 17.5 â€” Testar Versionamento

17. FaÃ§a upload do **mesmo arquivo** novamente (mesmo nome, mesma categoria)
18. Na tabela de documentos, clique em **VersÃµes** (botÃ£o de versÃµes) ao lado do documento
19. **Resultado esperado:**
    - Aparece uma lista com 2 versÃµes
    - Cada versÃ£o mostra: ID da versÃ£o, data, tamanho
    - A versÃ£o mais recente estÃ¡ marcada como "Atual" (isLatest: true)

20. **VerificaÃ§Ã£o no Console S3:**
    - Clique no objeto em `processados/contratos/`
    - Clique na aba **Versions**
    - Deve haver 2 versÃµes listadas com IDs diferentes

---

### 17.6 â€” Testar Upload InvÃ¡lido

21. Tente fazer upload de um arquivo com extensÃ£o `.exe` ou `.bat`
22. **Resultado esperado:** Mensagem de erro: "ExtensÃ£o nÃ£o permitida. ExtensÃµes vÃ¡lidas: pdf, png, jpg, jpeg, csv, xlsx, txt"
23. O arquivo NÃƒO deve ser enviado ao S3

---

### 17.7 â€” Resumo da ValidaÃ§Ã£o

| Teste | Status Esperado |
|-------|----------------|
| Frontend carrega | âœ… PÃ¡gina exibe corretamente |
| Upload de arquivo vÃ¡lido | âœ… Arquivo aparece em processados/ |
| Processamento automÃ¡tico | âœ… Lambda move de entrada/ para processados/ |
| Listagem de documentos | âœ… Tabela mostra documentos com metadados |
| Download funciona | âœ… Arquivo baixa corretamente |
| Versionamento | âœ… MÃºltiplas versÃµes sÃ£o listadas |
| Upload invÃ¡lido rejeitado | âœ… Erro amigÃ¡vel exibido ao usuÃ¡rio |
| Logs no CloudWatch | âœ… ExecuÃ§Ãµes registradas sem erros |

---

## Etapa 18: Testar Classes de Armazenamento

O prefixo `laboratorio/` existe para experimentar com classes de armazenamento S3 sem afetar os documentos reais. Aqui vocÃª farÃ¡ upload direto especificando a classe de armazenamento desejada.

> **IMPORTANTE:** TransiÃ§Ãµes via Lifecycle demoram atÃ© 48h. Para testar classes de armazenamento imediatamente, faremos upload direto com a classe desejada via Console S3.

---

### 18.1 â€” Upload com classe Standard (padrÃ£o)

1. No Console S3, acesse o bucket **cofre-documentos-arquivos-<AWS_ACCOUNT_ID>**
2. Navegue atÃ© `laboratorio/standard/`
3. Clique em **Upload**
4. Clique em **Add files** â†’ Selecione um arquivo de teste (ex: `teste-standard.txt`)
5. **NÃƒO** precisa alterar nenhuma propriedade (Standard Ã© o padrÃ£o)
6. Clique em **Upload**
7. **VerificaÃ§Ã£o:** Clique no objeto â†’ em **Properties**, o campo **Storage class** mostra `Standard`

---

### 18.2 â€” Upload com Intelligent-Tiering

8. Navegue atÃ© `laboratorio/intelligent-tiering/`
9. Clique em **Upload**
10. Clique em **Add files** â†’ Selecione um arquivo de teste (ex: `teste-it.txt`)
11. Expanda a seÃ§Ã£o **Properties** (abaixo de "Add files")
12. Na parte **Storage class**, selecione **Intelligent-Tiering**
13. Clique em **Upload**
14. **VerificaÃ§Ã£o:** Clique no objeto â†’ **Properties** â†’ Storage class mostra `Intelligent-Tiering`

> **Sobre Intelligent-Tiering:** O S3 move automaticamente objetos entre camadas de acesso (Frequent, Infrequent, Archive) baseado em padrÃµes de acesso. Objetos acessados frequentemente ficam em Standard; os menos acessados sÃ£o movidos automaticamente para camadas mais baratas.

---

### 18.3 â€” Upload com Glacier Flexible Retrieval

15. Navegue atÃ© `laboratorio/glacier-flexible/`
16. Clique em **Upload**
17. Clique em **Add files** â†’ Selecione um arquivo de teste (ex: `teste-glacier.txt`)
18. Expanda a seÃ§Ã£o **Properties**
19. Na parte **Storage class**, selecione **Glacier Flexible Retrieval**
20. Clique em **Upload**
21. **VerificaÃ§Ã£o:** Clique no objeto â†’ **Properties** â†’ Storage class mostra `Glacier Flexible Retrieval`

> **IMPORTANTE:** ApÃ³s o upload para Glacier, o objeto **NÃƒO pode ser baixado diretamente**. Tentar baixar resultarÃ¡ em erro. Ã‰ necessÃ¡rio fazer uma **restauraÃ§Ã£o** primeiro (veja 18.5).

---

### 18.4 â€” Upload com Glacier Deep Archive

22. Navegue atÃ© `laboratorio/deep-archive/`
23. Clique em **Upload**
24. Clique em **Add files** â†’ Selecione um arquivo de teste (ex: `teste-deep-archive.txt`)
25. Expanda a seÃ§Ã£o **Properties**
26. Na parte **Storage class**, selecione **Glacier Deep Archive**
27. Clique em **Upload**
28. **VerificaÃ§Ã£o:** Clique no objeto â†’ **Properties** â†’ Storage class mostra `Glacier Deep Archive`

> **Sobre Deep Archive:** Classe mais barata para dados acessados muito raramente. A restauraÃ§Ã£o leva de 12 a 48 horas (Standard tier). Ideal para backups de longo prazo e compliance.

---

### 18.5 â€” Testar RestauraÃ§Ã£o de Objeto Glacier

Vamos restaurar o objeto enviado para Glacier Flexible Retrieval.

**Via Console S3:**

29. Navegue atÃ© `laboratorio/glacier-flexible/`
30. Selecione o checkbox â˜ ao lado de `teste-glacier.txt`
31. Clique no menu **Actions** (AÃ§Ãµes) â†’ **Initiate restore** (Iniciar restauraÃ§Ã£o)
32. Preencha:

| Campo | Valor |
|-------|-------|
| **Number of days** | `2` (dias que o objeto ficarÃ¡ disponÃ­vel apÃ³s restauraÃ§Ã£o) |
| **Retrieval tier** | **Standard** (3-5 horas para Glacier Flexible) |

33. Clique em **Initiate restore**

**Via Frontend (usando a API):**

34. Se o objeto estivesse em `processados/`, vocÃª poderia usar o botÃ£o "Restaurar" na interface do Cofre Digital, que chama a Lambda `cofre-restaurar-documento`

**Verificar status da restauraÃ§Ã£o:**

35. Clique no objeto `teste-glacier.txt`
36. Na seÃ§Ã£o **Properties**, procure por **Restore status**:
    - `Restoration in progress` â€” RestauraÃ§Ã£o em andamento (aguarde 3-5h para Glacier, 12-48h para Deep Archive)
    - `Restored until [data]` â€” Objeto temporariamente disponÃ­vel atÃ© a data indicada

**ApÃ³s restauraÃ§Ã£o concluÃ­da:**

37. Quando o status mudar para "Restored until...", vocÃª poderÃ¡ baixar o objeto normalmente
38. ApÃ³s a data de expiraÃ§Ã£o, o objeto voltarÃ¡ a ser inacessÃ­vel (continua em Glacier)

---

### 18.6 â€” Tabela Comparativa de Classes

| Classe | Uso tÃ­pico | RestauraÃ§Ã£o | Custo (relativo) |
|--------|-----------|-------------|-----------------|
| Standard | Acesso frequente | Imediato | $$$ |
| Intelligent-Tiering | PadrÃ£o de acesso desconhecido | Imediato | $$-$$$ (automÃ¡tico) |
| Glacier Flexible | Arquivamento com acesso eventual | 1-12 horas | $ |
| Glacier Deep Archive | Arquivamento de longo prazo | 12-48 horas | Â¢ |

---

## SeÃ§Ã£o Opcional: Substituir SSE-S3 por SSE-KMS

Esta seÃ§Ã£o Ã© **opcional** e destinada a quem deseja aprender sobre criptografia gerenciada pelo AWS KMS (Key Management Service). O SSE-S3 padrÃ£o jÃ¡ Ã© suficiente para a maioria dos cenÃ¡rios.

### Quando usar SSE-KMS ao invÃ©s de SSE-S3?

| CenÃ¡rio | RecomendaÃ§Ã£o |
|---------|-------------|
| Projeto pessoal ou de baixo risco | SSE-S3 (mais simples, sem custo adicional) |
| Requisito de auditoria de uso da chave | SSE-KMS (cada uso Ã© registrado no CloudTrail) |
| Controle granular de quem pode descriptografar | SSE-KMS (policies na chave KMS) |
| Compliance (HIPAA, PCI-DSS) | SSE-KMS (rotaÃ§Ã£o automÃ¡tica, segregaÃ§Ã£o de acesso) |
| Multi-conta (cross-account access) | SSE-KMS (permite compartilhar chave entre contas) |

### DiferenÃ§as principais

| CaracterÃ­stica | SSE-S3 | SSE-KMS |
|---------------|--------|---------|
| Gerenciamento da chave | AWS gerencia tudo | VocÃª controla ou AWS gerencia |
| Custo da chave | Gratuito | $1/mÃªs por chave + $0.03 por 10.000 requisiÃ§Ãµes |
| Auditoria | BÃ¡sica | Completa via CloudTrail |
| RotaÃ§Ã£o | AutomÃ¡tica (interna) | AutomÃ¡tica anual (configurÃ¡vel) |
| Limite de requisiÃ§Ãµes | Sem limite | Cota de API KMS (5.500-30.000 req/s por regiÃ£o) |

---

### Passo 1: Criar uma Chave KMS

1. Na barra de busca superior, digite **KMS** e clique em **Key Management Service**
2. No menu lateral, clique em **Customer managed keys** (Chaves gerenciadas pelo cliente)
3. Verifique que a regiÃ£o Ã© `us-east-1`
4. Clique em **Create key** (Criar chave)
5. Preencha:

| Campo | Valor |
|-------|-------|
| **Key type** | `Symmetric` (SimÃ©trica) |
| **Key usage** | `Encrypt and decrypt` |

6. Clique em **Next**
7. Na tela "Add labels":

| Campo | Valor |
|-------|-------|
| **Alias** | `cofre-digital-kms-key` |
| **Description** | `Chave KMS para criptografia dos documentos do Cofre Digital` |
| **Tags** | Key: `projeto` â†’ Value: `cofre-digital` |

8. Clique em **Next**
9. Na tela "Define key administrative permissions":
   - Selecione seu usuÃ¡rio IAM (admin-cofre-digital ou o usuÃ¡rio logado)
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
15. Role atÃ© **Default encryption** (Criptografia padrÃ£o)
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

### Passo 3: Atualizar polÃ­ticas IAM das Lambdas

Para que as Lambdas possam ler/escrever objetos criptografados com KMS, adicione a seguinte permissÃ£o a TODAS as 6 polÃ­ticas IAM (Etapa 5):

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

**Para cada polÃ­tica:**

19. Acesse **IAM** â†’ **Policies** â†’ Clique na polÃ­tica (ex: `cofre-policy-gerar-url-upload`)
20. Clique em **Edit** (Editar)
21. Na aba JSON, adicione o statement acima dentro do array `Statement`
22. Substitua o ARN da chave pelo valor real anotado no Passo 1
23. Clique em **Next** â†’ **Save changes**
24. Repita para todas as 6 polÃ­ticas

---

### VerificaÃ§Ã£o

1. FaÃ§a upload de um novo arquivo via o Cofre Digital
2. No Console S3, clique no objeto carregado
3. Na aba **Properties**, a seÃ§Ã£o **Server-side encryption** deve mostrar:
   - **Encryption type**: `aws:kms`
   - **AWS KMS key ARN**: O ARN da sua chave
4. O download deve funcionar normalmente (descriptografia Ã© transparente se a Lambda tem permissÃ£o)

---

## Resumo de Recursos Criados

Ao final deste guia, vocÃª terÃ¡ criado os seguintes recursos na AWS:

| # | ServiÃ§o | Recurso | Nome/Identificador |
|---|---------|---------|-------------------|
| 1 | S3 | Bucket de documentos | `cofre-documentos-arquivos-<AWS_ACCOUNT_ID>` |
| 2 | S3 | Bucket do frontend | `cofre-documentos-frontend-<AWS_ACCOUNT_ID>` |
| 3 | S3 | CORS (bucket documentos) | ConfiguraÃ§Ã£o no bucket |
| 4 | S3 | Bucket Policy HTTPS (documentos) | ConfiguraÃ§Ã£o no bucket |
| 5 | S3 | Bucket Policy CloudFront (frontend) | ConfiguraÃ§Ã£o no bucket |
| 6 | S3 | Prefixos (entrada, processados, etc.) | Objetos vazios |
| 7 | S3 | 3 regras de Lifecycle | No bucket de documentos |
| 8 | S3 | Event Notification | `trigger-processar-documento` |
| 9 | IAM | 6 polÃ­ticas customizadas | `cofre-policy-*` |
| 10 | IAM | 6 roles | `cofre-role-*` |
| 11 | Lambda | 6 funÃ§Ãµes | `cofre-gerar-url-upload`, `cofre-processar-documento`, `cofre-listar-documentos`, `cofre-gerar-url-download`, `cofre-listar-versoes`, `cofre-restaurar-documento` |
| 12 | API Gateway | HTTP API | `cofre-digital-api` |
| 13 | API Gateway | 5 rotas | POST /upload-url, GET /documentos, GET /download-url, GET /versoes, POST /restaurar |
| 14 | CloudFront | DistribuiÃ§Ã£o | `dXXXXXXXXXXXXX.cloudfront.net` |
| 15 | CloudFront | OAC | `cofre-frontend-oac` |
| 16 | CloudWatch | 6 Log Groups | `/aws/lambda/cofre-*` (criados automaticamente) |

---

## Ordem Recomendada em Caso de Problemas

Se algo nÃ£o funcionar, verifique nesta ordem:

1. **VariÃ¡veis de ambiente** das Lambdas (nome do bucket estÃ¡ correto?)
2. **PolÃ­ticas IAM** (a Lambda tem permissÃ£o para a operaÃ§Ã£o S3 necessÃ¡ria?)
3. **CORS** (domÃ­nio do CloudFront estÃ¡ correto tanto no S3 quanto na API Gateway?)
4. **Bucket Policy** (frontend bucket tem policy do CloudFront?)
5. **Event Notification** (prefixo `entrada/` estÃ¡ correto?)
6. **CloudWatch Logs** (verifique erros detalhados)

---

## PrÃ³ximos Passos

ApÃ³s completar a implantaÃ§Ã£o:

1. ðŸ“– Leia `TESTES.md` para cenÃ¡rios de teste detalhados
2. ðŸ” Consulte `TROUBLESHOOTING.md` se encontrar problemas
3. ðŸ’° Leia `CUSTOS.md` para entender os custos envolvidos
4. ðŸ§¹ Quando terminar os estudos, siga `LIMPEZA.md` para remover todos os recursos e evitar cobranÃ§as

---

> **ParabÃ©ns!** ðŸŽ‰ Se todos os testes da Etapa 17 passaram, seu Cofre Digital de Arquivos estÃ¡ totalmente funcional.
