* * *

# TS4 Mod Auto-Classifier

**Classificador automático de prioridade para mods de The Sims 4, orientado por impacto funcional e risco técnico.**

* * *

## 🧠 O que é este projeto

O **TS4 Mod Auto-Classifier** é uma ferramenta pessoal/produtiva criada para **reduzir a carga cognitiva** no gerenciamento de mods de _The Sims 4_.

Ele permite que você:

*   cole a URL de um mod
    
*   deixe o app **ler e interpretar** a página do mod
    
*   obtenha automaticamente uma **prioridade numérica confiável**
    
*   registre ou atualize o mod no **Notion**, sem duplicatas
    

O objetivo **não é catalogar mods bonitos**,  
é **economizar tempo e evitar retrabalho**, especialmente após patches.

* * *

## 🎯 Princípios de design

Este projeto segue princípios rígidos:

*   **Classificação não é opinativa**
    
*   **Notion não decide nada** (é destino, não fonte)
    
*   **A URL é ponto de entrada**, mas não a única chave
    
*   **Incerteza gera cautela**, nunca prioridade menor
    
*   **Categoria é natureza**, prioridade é risco
    
*   O sistema é **determinístico, auditável e modular**
    

Qualquer funcionalidade que não reduza tempo é considerada falha de design.

* * *

## 🧩 Como o sistema funciona (visão geral)

### Pipeline resumido

```java
URL do mod
→ leitura da página
→ inferência funcional (LLM)
→ cálculo matemático de score
→ prioridade numérica final
→ subclassificação temática
→ busca no Notion
→ update ou criação (sem duplicatas)
```

* * *

## 🔢 Prioridade vs Subclassificação

### Prioridade (campo `Priority` no Notion)

*   Tipo: **Select**
    
*   Valores permitidos:
    
    ```plain text
    0, 1, 2, 3, 4, 5
    ```
*   Representa **nível de risco / impacto técnico**
    

### Subclassificação (campo `Notes`)

*   Ex: `3C – Família & Relações Pontuais`
    
*   **Nunca vai para o campo Priority**
    
*   Sempre é **acrescentada** ao campo Notes
    
*   **Nunca sobrescreve conteúdo existente**
    

Formato padrão:

```mathematica
Subclassificação automática: 3C – Família & Relações Pontuais
```

* * *

## 🧠 Modelo de classificação

A prioridade é calculada pela equação:

```ini
Score = Remoção + Framework + Essencial
```

*   Valores podem ser **fracionários** (ex: 1.5, 2.5)
    
*   O score final é **sempre arredondado para cima**
    
*   O arredondamento segue o princípio de cautela
    

A **LLM não decide a prioridade**.  
Ela apenas estima as variáveis da equação.

* * *

## 🗂️ Categorias válidas (domínio fechado)

O sistema trabalha com um conjunto **fixo e fechado** de categorias, como:

*   `3E` — Objetos Funcionais
    
*   `4B` — Traços & Personalidade
    
*   `5D` — Fixes & Tweaks
    

Não existem combinações livres.  
Exemplos inválidos: `4E`, `5F`, `3G`.

A **natureza do mod limita o resultado possível**.

* * *

## 🔍 Integração com Notion

Antes de criar qualquer página, o app **sempre procura se o mod já existe**:

1.  Busca por **URL normalizada**
    
2.  Se falhar, busca por **Nome + Autor** (fuzzy search)
    

Isso evita duplicatas mesmo quando:

*   URLs mudam
    
*   plataformas usam links dinâmicos
    
*   o mod foi salvo manualmente no passado
    

### Comportamento ao encontrar um mod existente

*   Atualiza:
    
    *   `Priority`
        
    *   `Score` (se usado)
        
    *   data de classificação
        
*   Acrescenta:
    
    *   subclassificação no `Notes` (append-only)
        

* * *

## 🧱 Estrutura do projeto

```bash
.
├── streamlit_app.py      # UI e orquestração
├── extractor.py          # Leitura e extração da página do mod
├── classifier.py         # Equação + lógica de prioridade
├── notion_sync.py        # Busca e update/create no Notion
├── requirements.txt
└── README.md
```

Cada arquivo tem **uma responsabilidade clara**.  
Não há lógica misturada.

* * *

## 🔐 Segurança

*   O token do Notion **não é versionado**
    
*   Deve ser fornecido via variável de ambiente:
    
    *   `NOTION_TOKEN`
        
    *   `NOTION_DATABASE_ID`
        

* * *

## 🚧 Estado atual

Este projeto está em **MVP funcional**:

*   Estrutura sólida
    
*   Modelo mental fechado
    
*   Código-base pronto
    
*   Pontos de expansão claros (LLM, fuzzy matching refinado)
    

Não é um produto genérico.  
É uma **ferramenta de trabalho real**, feita para uso contínuo.

* * *

⚠️ Este projeto é governado pelo arquivo
[MODELO_CANONICO_TS4_MOD_AUTO_CLASSIFIER.md].
Qualquer código deve obedecer a esse modelo.

* * *

## ✍️ Autor

**Criado por Akin (@UnpaidSimmer), com Lovable.**

Tradutor de mods de _The Sims 4_ e autor de storyplays.  
Este projeto reflete um sistema pessoal de organização construído ao longo do uso real.

* * *
