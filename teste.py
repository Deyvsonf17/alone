import os
import magic
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext

# Insira seu token do Telegram aqui
TOKEN = "6333929876:AAHVBeNeA3w4a0mc0U5K1HZ3OlwDazMfecw"

# Função para obter o tipo de arquivo usando python-magic
def get_file_type(file_path):
    mime = magic.Magic(mime=True)
    return mime.from_file(file_path)

# Função principal para lidar com arquivos recebidos (função assíncrona)
async def handle_files(update: Update, context: CallbackContext):
    file = None
    file_type = "Desconhecido"
    
    # Verifica o tipo de arquivo recebido e aguarda o get_file()
    if update.message.document:
        file = await update.message.document.get_file()
        file_type = update.message.document.mime_type
    elif update.message.photo:
        file = await update.message.photo[-1].get_file()
        file_type = "image/jpeg"  # Fotos do Telegram geralmente são JPEG
    elif update.message.video:
        file = await update.message.video.get_file()
        file_type = update.message.video.mime_type
    elif update.message.audio:
        file = await update.message.audio.get_file()
        file_type = update.message.audio.mime_type
    elif update.message.voice:
        file = await update.message.voice.get_file()
        file_type = "audio/ogg"  # Vozes do Telegram geralmente são OGG
    elif update.message.sticker:
        file = await update.message.sticker.get_file()
        file_type = "sticker"

    if file:
        # Cria o diretório temporário, se não existir
        os.makedirs("temp", exist_ok=True)
        file_path = f"temp/{file.file_unique_id}"
        
        # Baixa o arquivo para o caminho especificado
        await file.download_to_drive(file_path)
        
        # Detecta o tipo real do arquivo usando python-magic
        detected_type = get_file_type(file_path)
        os.remove(file_path)  # Remove o arquivo após a análise

        await update.message.reply_text(
            f"📂 Tipo de arquivo recebido: {file_type}\n🔍 Detecção real: {detected_type}"
        )
    else:
        await update.message.reply_text("❌ Não consegui identificar o arquivo.")

# Função principal para iniciar o bot
def main():
    app = Application.builder().token(TOKEN).build()
    
    # Adiciona um manipulador para arquivos e mídias
    app.add_handler(MessageHandler(filters.ALL, handle_files))

    app.run_polling()

if __name__ == "__main__":
    main()




