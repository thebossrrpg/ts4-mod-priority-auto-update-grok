
# CONTRATO TÉCNICO — FASE 3
**TS4 Mod Analyzer — v3.4.0**

## 1. Princípios Invioláveis

1. **Notion é a base canônica**
   - A IA não cria, não corrige, não inventa dados.
   - A IA não escreve no Notion.
   - Toda escrita ocorre apenas sob ação humana explícita.

2. **A IA nunca decide**
   - Toda decisão final é do código.
   - Outputs da IA são estruturas simples, interpretadas pelo app.

3. **A IA só é chamada quando a Fase 2 falha**
   - Falha definida como:
     - Nenhum match encontrado
     - Informações insuficientes para nova busca confiável.

## 2. Condições para Chamada da IA

A IA só pode ser chamada se:
- Nenhuma duplicata foi encontrada na Fase 2
- O slug é lixo **OU** o domínio foi marcado como bloqueado

Caso contrário, a IA não é acionada.

## 3. Contexto Permitido

- Máximo absoluto: 5 entradas do Notion
- Cada entrada contém apenas:
  - Filename
  - URL

## 4. Funções Permitidas da IA

- Avaliar matching com contexto
- Classificar se identidade é utilizável ou lixo

A IA nunca:
- Cria dados
- Decide ações
- Escreve no Notion

## 5. Modelos e Fallback

- Modelo primário: mais barato disponível
- Fallback: modelo 3.5-like, UMA vez
- Temperature = 0
- Máximo de chamadas por mod: 2

## 6. Uso do Resultado

- match = false → output hardcoded do app
- match = true → nome hyperlinkado

## 7. Objetivo

Reduzir falsos negativos sem aumentar automação.

---
Contrato congelado para v3.4.0
