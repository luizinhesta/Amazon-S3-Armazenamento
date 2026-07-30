# Capturas de Tela

Esta pasta deve conter as capturas de tela feitas durante a implantação do projeto.

## Capturas recomendadas

### Buckets S3
- Bucket de documentos criado (visão geral)
- Configuração de versionamento habilitado
- Configuração de criptografia SSE-S3
- Configuração CORS do bucket de documentos
- Bucket policy aplicada (deny HTTP)
- Estrutura de prefixos (entrada/, processados/, etc.)
- Bucket do frontend criado

### IAM
- Política IAM de cada Lambda (JSON)
- Role criada com trust policy
- Permissões anexadas à role

### Lambda
- Cada função Lambda criada (visão geral)
- Variáveis de ambiente configuradas
- Trigger S3 na Lambda processar-documento
- Logs de execução no CloudWatch

### API Gateway
- HTTP API criada
- Rotas configuradas
- Integrações com Lambda
- Configuração de CORS
- URL de invocação (Invoke URL)

### CloudFront
- Distribuição criada
- Origin Access Control configurado
- Bucket policy do frontend (gerada pelo CloudFront)
- Default root object: index.html

### Testes
- Upload bem-sucedido (resposta 200)
- Objeto no prefixo processados/ com tags
- Listagem de documentos no frontend
- Versões de um documento
- Objeto em classe Glacier
- Restauração iniciada
- Regras de Lifecycle configuradas

### Segurança
- Block Public Access habilitado (ambos os buckets)
- Nenhuma ACL configurada
- Teste de acesso direto ao bucket (deve negar)

## Formato

- Salvar como PNG ou JPG
- Nomear descritivamente: `01-bucket-documentos-criado.png`
- Numerar na ordem da implantação
- Ocultar informações sensíveis (Account ID parcial é aceitável)
