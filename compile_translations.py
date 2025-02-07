import os
import polib

# Lista de idiomas (pasta de cada idioma)
languages = ['pt_BR','zh_CN', 'pt_BR2', 'en_US', 'es_ES']
base_path = 'locales'

for lang in languages:
    po_path = os.path.join(base_path, lang, 'LC_MESSAGES', 'bot.po')
    mo_path = os.path.join(base_path, lang, 'LC_MESSAGES', 'bot.mo')
    
    if os.path.exists(po_path):
        po = polib.pofile(po_path)
        po.save_as_mofile(mo_path)
        print(f"Compilado {po_path} para {mo_path}")
    else:
        print(f"Arquivo não encontrado: {po_path}")
