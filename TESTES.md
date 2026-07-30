# 🧪 TESTES.md — Cenários de Teste do Cofre Digital

Este documento descreve cenários de teste manuais para validar todas as funcionalidades do Cofre Digital de Documentos. Execute estes testes após concluir a implantação para garantir que tudo está funcionando corretamente.

---

## Índice

1. [Upload válido](#1-upload-válido)
2. [Upload com extensão inválida](#2-upload-com-extensão-inválida)
3. [Upload acima do limite de tamanho](#3-upload-acima-do-limite-de-tamanho)
4. [Listagem de documentos](#4-listagem-de-documentos)
5. [Download de documento Standard](#5-download-de-documento-standard)
6. [Download de documento em Glacier sem restauração](#6-download-de-documento-em-glacier-sem-restauração)
7. [Versionamento de documentos](#7-versionamento-de-documentos)
8. [Download de versão específica](#8-download-de-versão-específica)
9. [Evento S3 ObjectCreated](#9-evento-s3-objectcreated)
10. [Processamento de documento válido](#10-processamento-de-documento-válido)
11. [Processamento de documento rejeitado](#11-processamento-de-documento-rejeitado)
12. [URL pré-assinada expirada](#12-url-pré-assinada-expirada)
13. [Download de prefixo não autorizado](#13-download-de-prefixo-não-autorizado)
14. [Solicitação de restauração Glacier](#14-solicitação-de-restauração-glacier)
15. [Restauração já em andamento](#15-restauração-já-em-andamento)
16. [CORS — upload do domínio CloudFront](#16-cors--upload-do-domínio-cloudfront)
17. [Acesso via CloudFront](#17-acesso-via-cloudfront)
18. [Regras de Lifecycle](#18-regras-de-lifecycle)
19. [Logs no CloudWatch](#19-logs-no-cloudwatch)
20. [Upload com path traversal](#20-upload-com-path-traversal)

---

## 1. Upload válido

**Descrição:** Verificar que um arquivo com extensão permitida (PDF, PNG, JPG, JPEG, CSV, XLSX, TXT) é aceito pelo sistema e processado corretamente.

**Passos:**
1. Acesse o frontend via URL do CloudFront.
2. Na seção de upload, selecione um arquivo `.pdf` (tamanho < 20MB).
3. Escolha a categoria "contratos" no seletor.
4. Clique em "Enviar".
5. Aguarde a confirmação de upload.

**Resultado esperado:**
- O frontend exibe mensagem de sucesso.
- O arquivo aparece temporariamente no prefixo `entrada/contratos/` no bucket de documentos.
- Após poucos segundos, o Lambda `processar-documento` é acionado e move o arquivo para `processados/contratos/`.
- O arquivo aparece na listagem de documentos com as tags corretas (tipo-arquivo, data-processamento, categoria, status=processado).

**Como verificar:**
- No Console AWS → S3 → Bucket de documentos, verifique o prefixo `processados/contratos/`.
- Clique no objeto e confira as tags na aba "Properties" → "Tags".
- No frontend, clique em "Atualizar listagem" e confirme que o documento aparece na tabela.

---

## 2. Upload com extensão inválida

**Descrição:** Verificar que arquivos com extensões não permitidas (como .exe, .bat, .sh, .dll) são rejeitados antes do upload.

**Passos:**
1. Acesse o frontend via URL do CloudFront.
2. Selecione um arquivo com extensão `.exe` (ou `.bat`, `.sh`).
3. Escolha qualquer categoria.
4. Clique em "Enviar".

**Resultado esperado:**
- O frontend exibe mensagem de erro informando que a extensão não é permitida.
- A mensagem lista as extensões válidas: pdf, png, jpg, jpeg, csv, xlsx, txt.
- Nenhum arquivo é enviado para o S3.
- O prefixo `entrada/` permanece inalterado.

**Como verificar:**
- Observe a mensagem de erro no frontend.
- No Console AWS → S3, confirme que nenhum objeto novo foi criado no prefixo `entrada/`.
- No Console AWS → CloudWatch → Logs da Lambda `gerar-url-upload`, verifique que o log registra a rejeição.

---

## 3. Upload acima do limite de tamanho

**Descrição:** Verificar que arquivos com mais de 20MB são rejeitados.

**Passos:**
1. Crie um arquivo de teste com mais de 20MB (ex.: use `dd if=/dev/zero of=grande.pdf bs=1M count=25` ou qualquer arquivo grande renomeado com extensão válida).
2. Acesse o frontend e selecione este arquivo para upload.
3. Escolha uma categoria e clique em "Enviar".

**Resultado esperado:**
- A URL pré-assinada é gerada (pois a validação de tamanho no Lambda verifica o Content-Length declarado).
- Ao tentar enviar o arquivo via PUT para a URL pré-assinada, o S3 rejeita a requisição com erro de `EntityTooLarge` (status 400) se o Content-Length excede o limite configurado nas condições da URL.
- O frontend exibe mensagem de erro sobre tamanho excedido.

**Como verificar:**
- Observe a mensagem de erro no frontend.
- Abra as ferramentas de desenvolvedor do navegador (F12) → aba Network.
- Verifique que a requisição PUT para o S3 retorna status 400 ou 403.
- Confirme que nenhum objeto grande aparece no bucket.

---

## 4. Listagem de documentos

**Descrição:** Verificar que a listagem retorna todos os documentos processados com metadados corretos.

**Passos:**
1. Certifique-se de que existem documentos no prefixo `processados/` (execute testes de upload válido antes).
2. Acesse o frontend.
3. A listagem deve ser carregada automaticamente ao abrir a página.

**Resultado esperado:**
- A tabela de documentos exibe todos os documentos em `processados/`.
- Cada documento mostra: nome do arquivo, tamanho (formatado em KB/MB), data de modificação (formato brasileiro), classe de armazenamento e ações disponíveis.
- Se não houver documentos, uma mensagem informativa é exibida.

**Como verificar:**
- Compare a tabela do frontend com os objetos no Console AWS → S3 → prefixo `processados/`.
- Verifique que a quantidade de documentos confere.
- Confirme que os tamanhos e datas estão corretos.
- No Console AWS → CloudWatch → Logs da Lambda `listar-documentos`, verifique que a execução retornou status 200.

---

## 5. Download de documento Standard

**Descrição:** Verificar que é possível baixar um documento com classe de armazenamento Standard.

**Passos:**
1. Certifique-se de que há um documento em `processados/` com classe STANDARD.
2. No frontend, localize o documento na tabela.
3. Clique no botão "Download".

**Resultado esperado:**
- O sistema gera uma URL pré-assinada GET com expiração de 5 minutos.
- O navegador inicia o download do arquivo.
- O conteúdo baixado é idêntico ao arquivo original enviado.

**Como verificar:**
- Verifique que o download completa sem erros.
- Compare o hash (MD5/SHA256) do arquivo baixado com o original.
- Nas ferramentas de desenvolvedor, verifique que a requisição GET para `/download-url` retornou status 200 com a URL pré-assinada.

---

## 6. Download de documento em Glacier sem restauração

**Descrição:** Verificar que o sistema informa corretamente quando um documento está em Glacier e não pode ser baixado diretamente.

**Passos:**
1. No Console AWS, altere a classe de armazenamento de um objeto em `processados/` para Glacier Flexible Retrieval (ou use um objeto que já foi movido pelo Lifecycle).
2. No frontend, tente baixar este documento.

**Resultado esperado:**
- O frontend exibe mensagem de erro informando que o arquivo está em Glacier e que é necessário solicitar restauração.
- Nenhuma URL de download é gerada.
- O botão de restauração se torna disponível (ou a mensagem orienta o usuário a restaurar).

**Como verificar:**
- Observe a mensagem de erro no frontend — deve ser amigável e em português.
- No Console AWS → S3, confirme que o objeto está com StorageClass = GLACIER.
- No CloudWatch, verifique que a Lambda `gerar-url-download` logou a situação corretamente.

---

## 7. Versionamento de documentos

**Descrição:** Verificar que o versionamento registra múltiplas versões de um mesmo arquivo.

**Passos:**
1. Faça upload de um arquivo (ex.: `relatorio.pdf`) na categoria "relatorios".
2. Aguarde o processamento (arquivo aparece em `processados/relatorios/`).
3. Faça upload de uma nova versão do mesmo arquivo (mesmo nome, conteúdo diferente) na mesma categoria.
4. Aguarde o processamento novamente.

**Resultado esperado:**
- Ambas as versões existem no bucket com VersionIds diferentes.
- Na listagem, o documento aparece uma única vez (versão mais recente).
- Ao visualizar versões, ambas aparecem listadas com datas, tamanhos e VersionIds distintos.

**Como verificar:**
- No Console AWS → S3 → prefixo `processados/relatorios/`, ative "Show versions".
- Confirme que existem 2 (ou mais) versões do objeto.
- No frontend, clique em "Versões" no documento e confirme que ambas versões são listadas.

---

## 8. Download de versão específica

**Descrição:** Verificar que é possível baixar uma versão específica (não a mais recente) de um documento.

**Passos:**
1. Certifique-se de que um documento possui ao menos 2 versões (execute o teste 7 antes).
2. No frontend, abra a visualização de versões do documento.
3. Clique em "Download" na versão mais antiga (não a mais recente).

**Resultado esperado:**
- O sistema gera uma URL pré-assinada para a versão específica (com parâmetro `versionId`).
- O download retorna o conteúdo da versão selecionada, não da versão atual.
- O conteúdo baixado corresponde ao arquivo original daquela versão.

**Como verificar:**
- Compare o conteúdo/tamanho do arquivo baixado com a versão esperada.
- Nas ferramentas de desenvolvedor, confirme que a requisição a `/download-url` inclui o parâmetro `versionId`.
- No Console AWS, baixe a mesma versão manualmente e compare os arquivos.

---

## 9. Evento S3 ObjectCreated

**Descrição:** Verificar que o evento S3 é disparado corretamente quando um objeto é criado no prefixo `entrada/`.

**Passos:**
1. No Console AWS → S3 → Bucket de documentos → Properties → Event notifications, confirme que existe uma notificação configurada para o prefixo `entrada/`.
2. Faça upload de um arquivo via frontend (ou diretamente via Console no prefixo `entrada/`).
3. Aguarde 5-10 segundos.

**Resultado esperado:**
- A Lambda `processar-documento` é invocada automaticamente.
- O arquivo é movido de `entrada/` para `processados/` (se válido) ou `rejeitados/` (se inválido).
- O prefixo `entrada/` fica vazio após o processamento.

**Como verificar:**
- No Console AWS → Lambda → `cofre-processar-documento` → Monitor, verifique que houve uma invocação recente.
- No CloudWatch → Logs da Lambda, confirme os logs de processamento.
- No S3, verifique que o arquivo saiu de `entrada/` e foi para o destino correto.

---

## 10. Processamento de documento válido

**Descrição:** Verificar que um documento com extensão válida é corretamente processado, tagueado e movido para `processados/`.

**Passos:**
1. Faça upload de um arquivo `nota.pdf` na categoria "notas-fiscais".
2. Aguarde o processamento (5-10 segundos).
3. Verifique o prefixo `processados/notas-fiscais/` no Console AWS.

**Resultado esperado:**
- O arquivo `nota.pdf` está presente em `processados/notas-fiscais/`.
- O arquivo NÃO está mais em `entrada/notas-fiscais/`.
- O objeto possui as seguintes tags:
  - `tipo-arquivo`: pdf
  - `data-processamento`: data/hora ISO 8601
  - `categoria`: notas-fiscais
  - `status`: processado

**Como verificar:**
- No Console AWS → S3 → Bucket → prefixo `processados/notas-fiscais/`, clique no objeto.
- Vá até a aba "Properties" e confirme as tags.
- Confirme que `entrada/notas-fiscais/` não contém mais o arquivo.
- No CloudWatch, verifique os logs da Lambda com a mensagem de sucesso.

---

## 11. Processamento de documento rejeitado

**Descrição:** Verificar que um documento com extensão inválida enviado diretamente ao S3 (bypass do frontend) é rejeitado e movido para `rejeitados/`.

**Passos:**
1. No Console AWS → S3, faça upload manual de um arquivo `virus.exe` diretamente no prefixo `entrada/outros/`.
2. Aguarde o processamento (5-10 segundos).
3. Verifique os prefixos `rejeitados/` e `entrada/`.

**Resultado esperado:**
- O arquivo é movido para `rejeitados/virus.exe`.
- O arquivo NÃO está mais em `entrada/outros/`.
- O objeto em `rejeitados/` possui as tags:
  - `status`: rejeitado
  - `motivo-rejeicao`: extensão não permitida (ou mensagem similar)
  - `tipo-arquivo`: exe

**Como verificar:**
- No Console AWS → S3 → prefixo `rejeitados/`, confirme a presença do arquivo.
- Clique no objeto e verifique as tags na aba "Properties".
- No CloudWatch → Logs, confirme que a Lambda registrou a rejeição com o motivo.

---

## 12. URL pré-assinada expirada

**Descrição:** Verificar que uma URL pré-assinada não permite acesso após expirar (5 minutos).

**Passos:**
1. No frontend, solicite o download de um documento (isso gera uma URL pré-assinada).
2. Copie a URL pré-assinada (nas ferramentas de desenvolvedor → Network → copie a URL da requisição).
3. Aguarde mais de 5 minutos.
4. Cole a URL diretamente no navegador.

**Resultado esperado:**
- O navegador exibe erro XML do S3 com a mensagem `AccessDenied` ou `Request has expired`.
- A resposta inclui informação sobre a expiração.
- O documento NÃO é baixado.

**Como verificar:**
- Observe a resposta XML do S3 no navegador — procure por `<Code>AccessDenied</Code>` ou `<Code>ExpiredToken</Code>`.
- Compare com o comportamento antes da expiração (nos primeiros 5 minutos o download funciona normalmente).
- Gere uma nova URL e confirme que funciona imediatamente.

---

## 13. Download de prefixo não autorizado

**Descrição:** Verificar que o sistema bloqueia tentativas de download de objetos fora do prefixo `processados/`.

**Passos:**
1. Tente solicitar download com uma key que aponta para outro prefixo:
   - Via API diretamente: `GET /download-url?key=entrada/contratos/arquivo.pdf`
   - Ou: `GET /download-url?key=rejeitados/arquivo.exe`
2. Observe a resposta.

**Resultado esperado:**
- O sistema retorna erro 400 ou 403 informando que a key não é válida ou não está no prefixo permitido.
- Nenhuma URL pré-assinada é gerada para prefixos fora de `processados/`.

**Como verificar:**
- Use uma ferramenta como curl ou Postman para fazer a requisição diretamente:
  ```bash
  curl "https://{api-url}/download-url?key=entrada/contratos/arquivo.pdf"
  ```
- Confirme que a resposta contém mensagem de erro.
- Verifique no CloudWatch que a Lambda registrou a tentativa bloqueada.

---

## 14. Solicitação de restauração Glacier

**Descrição:** Verificar que é possível iniciar a restauração de um documento arquivado em Glacier.

**Passos:**
1. Certifique-se de que há um objeto em `processados/` com classe Glacier (altere manualmente via Console ou aguarde o Lifecycle).
2. No frontend, localize o documento e clique em "Restaurar".
3. Selecione o tier "Standard" (ou o disponível).
4. Confirme a restauração.

**Resultado esperado:**
- O sistema inicia o processo de restauração com sucesso.
- A mensagem informa que a restauração foi solicitada e pode levar de 3-5 horas (Standard) ou 5-12 horas (Bulk).
- No Console AWS, o objeto mostra "Restoration in progress" nos metadados.

**Como verificar:**
- No Console AWS → S3 → Selecione o objeto → aba "Properties", verifique o campo "Restore status": deve indicar que há uma restauração em andamento.
- No CloudWatch, confirme que a Lambda `restaurar-documento` executou com sucesso.
- Após o período de restauração, o objeto estará temporariamente disponível para download.

---

## 15. Restauração já em andamento

**Descrição:** Verificar o comportamento quando o usuário tenta restaurar um documento que já está sendo restaurado.

**Passos:**
1. Solicite a restauração de um documento em Glacier (teste 14).
2. Imediatamente (antes da restauração completar), tente restaurar o mesmo documento novamente.

**Resultado esperado:**
- O sistema retorna mensagem informando que já existe uma restauração em andamento para este documento.
- Nenhum erro inesperado ocorre.
- A restauração original continua normalmente.

**Como verificar:**
- Observe a mensagem no frontend — deve ser informativa, não um erro genérico.
- No CloudWatch, verifique que a Lambda tratou o caso `RestoreAlreadyInProgress` corretamente.
- O status da restauração original não é afetado.

---

## 16. CORS — upload do domínio CloudFront

**Descrição:** Verificar que as configurações CORS permitem que o frontend (servido via CloudFront) faça requisições ao bucket de documentos.

**Passos:**
1. Acesse o frontend via URL do CloudFront (não via localhost ou acesso direto ao S3).
2. Faça upload de um arquivo.
3. Observe as ferramentas de desenvolvedor (F12) → aba Console e Network.

**Resultado esperado:**
- O upload funciona sem erros de CORS.
- A requisição PUT para o S3 (via URL pré-assinada) inclui os headers CORS corretos.
- Não há erros "Access-Control-Allow-Origin" no console do navegador.

**Como verificar:**
- Nas ferramentas de desenvolvedor → Network, selecione a requisição PUT para o S3.
- Verifique os Response Headers:
  - `Access-Control-Allow-Origin` deve conter o domínio do CloudFront.
  - `Access-Control-Allow-Methods` deve incluir PUT e GET.
- Se houver uma requisição OPTIONS (preflight), ela deve retornar status 200.
- Teste também a partir de um domínio diferente (localhost) — neste caso, o CORS deve bloquear.

---

## 17. Acesso via CloudFront

**Descrição:** Verificar que o frontend é acessível via CloudFront e que o acesso direto ao bucket é bloqueado.

**Passos:**
1. Acesse a URL do CloudFront: `https://dXXXXXXXXXX.cloudfront.net`.
2. Tente acessar o bucket do frontend diretamente: `https://bucket-frontend.s3.amazonaws.com/index.html`.

**Resultado esperado:**
- Via CloudFront: a página carrega normalmente com HTML, CSS e JS.
- Via S3 direto: retorna `403 Forbidden` (AccessDenied).

**Como verificar:**
- Acesse a URL do CloudFront no navegador — a página deve carregar completa.
- Tente acessar o bucket diretamente — deve retornar XML de erro com `<Code>AccessDenied</Code>`.
- No Console AWS → S3 → Bucket frontend → Permissions, confirme que "Block all public access" está ativado.
- No Console AWS → CloudFront → Distribution, confirme que o OAC está configurado.

---

## 18. Regras de Lifecycle

**Descrição:** Verificar que as regras de ciclo de vida estão configuradas corretamente no bucket de documentos.

> **Nota importante:** As regras de Lifecycle não são executadas imediatamente. O S3 processa transições em lotes, geralmente dentro de 24-48 horas após o período configurado. Este teste verifica apenas a **configuração**, não a execução.

**Passos:**
1. No Console AWS → S3 → Bucket de documentos → Management → Lifecycle rules.
2. Verifique cada regra configurada.

**Resultado esperado:**
As seguintes regras devem estar presentes:

| Regra | Prefixo | Transições |
|-------|---------|------------|
| arquivar-documentos-processados | processados/ | Standard→IT (30d), →Glacier Flex (180d), →Deep Archive (365d), Expirar (730d) |
| excluir-arquivos-temporarios | temporarios/ | Expirar current (7d), Noncurrent (7d), Abort multipart (1d) |
| limpar-versoes-antigas | processados/ | Noncurrent expire (90d), Remove expired delete markers |

**Como verificar:**
- No Console AWS, abra cada regra e confirme os valores de dias e transições.
- Verifique que o status de cada regra é "Enabled".
- Após vários dias, verifique se objetos antigos mudaram de classe (use o Console → S3 → selecione objeto → verifique "Storage class").

---

## 19. Logs no CloudWatch

**Descrição:** Verificar que todas as funções Lambda estão gerando logs no CloudWatch.

**Passos:**
1. Execute qualquer operação no frontend (upload, listagem, download).
2. No Console AWS → CloudWatch → Log groups, procure os grupos:
   - `/aws/lambda/cofre-gerar-url-upload`
   - `/aws/lambda/cofre-processar-documento`
   - `/aws/lambda/cofre-listar-documentos`
   - `/aws/lambda/cofre-gerar-url-download`
   - `/aws/lambda/cofre-listar-versoes`
   - `/aws/lambda/cofre-restaurar-documento`

**Resultado esperado:**
- Cada grupo de log existe e contém log streams recentes.
- Os logs incluem: timestamp, request ID, informações da operação e resultado.
- Erros são logados com detalhes suficientes para diagnóstico.

**Como verificar:**
- Clique em cada log group e abra o log stream mais recente.
- Procure por entradas com as informações esperadas (key processada, status, etc.).
- Verifique que não há erros inesperados ou exceções não tratadas.
- Use a busca do CloudWatch com filtro `ERROR` para encontrar possíveis problemas.

---

## 20. Upload com path traversal

**Descrição:** Verificar que tentativas de travessia de caminho no nome do arquivo são sanitizadas.

**Passos:**
1. Use curl ou Postman para enviar uma requisição direta à API com nome de arquivo malicioso:
   ```bash
   curl -X POST "https://{api-url}/upload-url" \
     -H "Content-Type: application/json" \
     -d '{"filename": "../../../etc/passwd.pdf", "category": "contratos", "contentType": "application/pdf"}'
   ```
2. Observe a resposta.
3. Se a URL for gerada, verifique a key no S3.

**Resultado esperado:**
- O sistema sanitiza o nome do arquivo, removendo sequências `../`, `..\\` e similares.
- A key gerada NÃO contém componentes de travessia de caminho.
- O arquivo é armazenado dentro do prefixo correto (`entrada/contratos/`) com nome seguro (ex.: `passwd.pdf` ou `etc_passwd.pdf`).

**Como verificar:**
- Na resposta da API, examine o campo `key` — não deve conter `../` ou qualquer sequência de travessia.
- No Console AWS → S3, confirme que nenhum objeto foi criado fora da estrutura de prefixos esperada.
- Teste variações: `....//`, `..%2F`, `..%5C` para confirmar que todas são tratadas.
- No CloudWatch, verifique que a Lambda registrou a sanitização.

---

## Resumo dos Resultados

Use esta tabela para registrar os resultados dos seus testes:

| # | Cenário | Status | Observações |
|---|---------|--------|-------------|
| 1 | Upload válido | ⬜ | |
| 2 | Upload extensão inválida | ⬜ | |
| 3 | Upload > 20MB | ⬜ | |
| 4 | Listagem de documentos | ⬜ | |
| 5 | Download Standard | ⬜ | |
| 6 | Download Glacier (sem restore) | ⬜ | |
| 7 | Versionamento | ⬜ | |
| 8 | Download versão específica | ⬜ | |
| 9 | Evento S3 ObjectCreated | ⬜ | |
| 10 | Processamento válido | ⬜ | |
| 11 | Processamento rejeitado | ⬜ | |
| 12 | URL pré-assinada expirada | ⬜ | |
| 13 | Download prefixo não autorizado | ⬜ | |
| 14 | Restauração Glacier | ⬜ | |
| 15 | Restauração já em andamento | ⬜ | |
| 16 | CORS | ⬜ | |
| 17 | CloudFront | ⬜ | |
| 18 | Lifecycle | ⬜ | |
| 19 | Logs CloudWatch | ⬜ | |
| 20 | Path traversal | ⬜ | |

**Legenda:** ✅ Passou | ❌ Falhou | ⬜ Não testado
