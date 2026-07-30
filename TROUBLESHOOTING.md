# 🔧 TROUBLESHOOTING.md — Resolução de Problemas do Cofre Digital

Guia de resolução para problemas comuns encontrados durante a implantação e uso do Cofre Digital de Documentos.

---

## Índice

1. [AccessDenied no upload](#1-accessdenied-no-upload)
2. [SignatureDoesNotMatch na URL pré-assinada](#2-signaturedoesnotmatch-na-url-pré-assinada)
3. [CORS bloqueado pelo navegador](#3-cors-bloqueado-pelo-navegador)
4. [Arquivo não processado (permanece em entrada/)](#4-arquivo-não-processado-permanece-em-entrada)
5. [Lambda não acionada (sem evento)](#5-lambda-não-acionada-sem-evento)
6. [Lambda entrando em loop](#6-lambda-entrando-em-loop)
7. [Objeto não aparece na listagem](#7-objeto-não-aparece-na-listagem)
8. [Download retorna AccessDenied](#8-download-retorna-accessdenied)
9. [Glacier não permite download](#9-glacier-não-permite-download)
10. [RestoreAlreadyInProgress](#10-restorealreadyinprogress)
11. [Lifecycle não movimentou o arquivo](#11-lifecycle-não-movimentou-o-arquivo)
12. [Arquivo menor que 128KB não transicionado](#12-arquivo-menor-que-128kb-não-transicionado)
13. [CloudFront mostra versão antiga](#13-cloudfront-mostra-versão-antiga)
14. [Bucket policy inválida](#14-bucket-policy-inválida)
15. [Permissão IAM insuficiente](#15-permissão-iam-insuficiente)
16. [Content-Type diferente do assinado na URL](#16-content-type-diferente-do-assinado-na-url)

---

## 1. AccessDenied no upload

**Sintoma:** Ao tentar fazer upload via URL pré-assinada, o S3 retorna `403 AccessDenied`.
