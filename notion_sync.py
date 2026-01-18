# Integração com Notion
# Busca por URL + fallback Nome + Autor (fuzzy)
# Priority = número
# Subclassificação = append-only em Notes

import os
from notion_client import Client
from datetime import datetime

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

notion = Client(auth=NOTION_TOKEN)

def upsert_mod(mod_data: dict, result: dict):
    subclass_line = (
        f"Subclassificação automática: "
        f"{result['code']} - {result['label']}"
    )

    # LÓGICA A IMPLEMENTAR:
    # 1. Normalizar URL
    # 2. Buscar no Notion por URL
    # 3. Se não achar, fuzzy search por (title + author)
    # 4. Se achar:
    #    - atualizar Priority (select numérico)
    #    - append subclass_line ao Notes (nova linha)
    # 5. Se não achar:
    #    - criar página com Notes iniciando com subclass_line

    # IMPORTANTE:
    # - Nunca sobrescrever Notes
    # - Nunca gravar letras em Priority
    # - Nunca criar duplicata silenciosa

    return True
