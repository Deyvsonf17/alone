import asyncio
import logging
import html
import httpx
from telegram import (
    Update,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaAnimation,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler
)

# ------------------------------
# Configurações
# ------------------------------
BOT_TOKEN = "7036731628:AAGbON5-PPN6vYi656Mcoo0oCgGZMS0oYRs"
ADMIN_ID = 6460184219

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------------------
# Funções Auxiliares
# ------------------------------
def safe_escape(text: str) -> str:
    try:
        return html.escape(text).encode("utf-16", "surrogatepass").decode("utf-16") if text else ""
    except Exception as e:
        logger.error(f"Erro ao escapar texto: {e}")
        return "[Conteúdo não legível]"

async def notificar_erro(context: ContextTypes.DEFAULT_TYPE, error: Exception, user_id: int = None) -> None:
    error_message = (
        f"❌ <b>Erro Detectado:</b>\n\n"
        f"<b>Detalhes:</b> {error}\n"
        f"<b>Usuário:</b> {user_id or 'Desconhecido'}"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=error_message, parse_mode="HTML")
    except Exception as e:
        logger.critical(f"Erro ao notificar o admin: {e}")

async def enviar_info_usuario(user_id: int, user_name: str, username: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_info = (
        f"👤 <b>Nova interação:</b>\n\n"
        f"🔹 <b>ID do Usuário:</b> <code>{user_id}</code>\n"
        f"🔹 <b>Nome:</b> {user_name}\n"
        f"🔹 <b>Username:</b> @{username if username != 'N/A' else 'N/A'}"
    )
    await context.bot.send_message(chat_id=ADMIN_ID, text=user_info, parse_mode="HTML")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exceção não tratada:", exc_info=context.error)
    error_msg = "⚠️ Ocorreu um erro inesperado. Tente novamente mais tarde."
    if update and isinstance(update, Update):
        await update.effective_message.reply_text(error_msg)
    await notificar_erro(context, context.error)

# ------------------------------
# Handlers de Mensagens
# ------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    # Para chats privados, chat_id é igual ao user.id
    user_id = update.message.chat_id  
    user_name = user.first_name or "N/A"
    username = user.username or "N/A"
    
    info_message = (
        f"👤 <b>Nova interação via /start:</b>\n\n"
        f"🔹 <b>ID do Usuário:</b> <code>{user_id}</code>\n"
        f"🔹 <b>Nome:</b> {user_name}\n"
        f"🔹 <b>Username:</b> @{username}"
    )
    # Envia as informações para o ADM
    await context.bot.send_message(chat_id=ADMIN_ID, text=info_message, parse_mode="HTML")
    
    welcome_message = (
    "✨ <b>Bem-vindo!</b> ✨\n\n"
    "📩 <b>Envie mensagens ou mídias</b> (📷 fotos, 🎥 vídeos ou 🎞️ GIFs), e o bot os reenviará para você **sem exibir sua identidade**.\n\n"
    "🔄 O nome original do encaminhamento será <b>removido</b> e substituído pelo nome do bot, garantindo **total anonimato**.\n\n"
    "🔒 <b>Sua privacidade é nossa prioridade!</b>\n\n"
    "⚠️ <i>Observação:</i>\n"
    "❌ Botões e legendas serão <b>automaticamente removidos</b>.\n\n"
    "👉 <b>Experimente agora!</b>"
)

    await update.message.reply_text(welcome_message, parse_mode="HTML")

async def receber_texto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Processa mensagens de texto normais (quando o bot não está aguardando legenda).
    """
    user_id = update.message.chat_id
    try:
        user_name = update.message.from_user.first_name or "N/A"
        username = update.message.from_user.username or "N/A"
        mensagem = update.message.text

        mensagem_info = (
            f"📩 <b>Nova mensagem recebida:</b>\n\n"
            f"🔹 <b>ID do Usuário:</b> <code>{user_id}</code>\n"
            f"🔹 <b>Nome:</b> {user_name}\n"
            f"🔹 <b>Username:</b> @{username}\n\n"
            f"💬 <b>Mensagem:</b>\n{safe_escape(mensagem)}"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=mensagem_info, parse_mode="HTML")
        await update.message.reply_text(mensagem)
    except Exception as e:
        await notificar_erro(context, e, user_id=user_id)



import asyncio

async def receber_midia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Processa mídias (foto, vídeo, GIF) e pergunta se o usuário deseja adicionar legenda.
    Se o usuário enviar um álbum (múltiplas mídias) de uma só vez, a pergunta será feita apenas uma vez.
    """
    user_id = update.message.chat_id
    try:
        # Obtém ou inicializa o álbum do usuário (armazenado em context.user_data["albums"])
        user_albums = context.user_data.setdefault("albums", {})
        album = user_albums.setdefault(user_id, {
            "media": [],
            "original_captions": [],
            "timer": None,
            "user_info_sent": False,
            "waiting_for_caption": False,
            "question_sent": False,  # flag para enviar a pergunta apenas uma vez
            "user_name": None,
            "username": None,
        })

        # Armazena as informações do usuário (caso ainda não estejam armazenadas)
        if album["user_name"] is None:
            album["user_name"] = update.message.from_user.first_name or "N/A"
        if album["username"] is None:
            album["username"] = update.message.from_user.username or "N/A"

        # Cria o objeto InputMedia de acordo com o tipo de mídia
        if update.message.photo:
            media = InputMediaPhoto(media=update.message.photo[-1].file_id)
        elif update.message.video:
            media = InputMediaVideo(media=update.message.video.file_id)
        elif update.message.animation:
            # Trata animações (GIFs) como InputMediaAnimation
            media = InputMediaAnimation(media=update.message.animation.file_id)
        else:
            await update.message.reply_text("⚠️ Formato não suportado!")
            return

        # Adiciona a mídia ao álbum do usuário
        album["media"].append(media)
        album["waiting_for_caption"] = False  # garante que o flag esteja zerado

        # Se ainda não foi enviada a pergunta para este álbum, envia os textos com intervalo
        if not album["question_sent"]:
            await update.message.reply_text("ℹ️ A legenda original ou botões da mídia serão removidos antes de reenviar.")
            await asyncio.sleep(1)  # Pausa de 2 segundos entre mensagens
            
            await update.message.reply_text("ℹ️ A legenda será aplicada a todas as mídias enviadas de uma vez. Caso não queira adicionar uma legenda, clique em 'Não'.")
            await asyncio.sleep(2)  # Pausa de 2 segundos entre mensagens

            # Adiciona os botões
            keyboard = [
                [InlineKeyboardButton("✅ Sim, adicionar legenda", callback_data=f"add_caption_{user_id}")],
                [InlineKeyboardButton("❌ Não, enviar sem legenda", callback_data=f"no_caption_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("📝 Deseja adicionar uma legenda à(s) mídia(s)?", reply_markup=reply_markup)
            




            album["question_sent"] = True

    except Exception as e:
        await notificar_erro(context, e, user_id=user_id)



async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Processa a resposta do usuário sobre adicionar ou não legenda e substitui os botões pela escolha feita.
    """
    query = update.callback_query
    user_id = query.message.chat_id
    callback_data = query.data

    # Obtém o álbum do usuário
    album = context.user_data.get("albums", {}).get(user_id)
    if not album:
        await query.message.edit_text("⚠️ Ocorreu um erro ao processar sua resposta. Tente novamente.")
        return

    # Define o texto que substituirá os botões
    if f"add_caption_{user_id}" in callback_data:
        album["waiting_for_caption"] = True
        new_text = "📝✍️  envie a legenda que deseja adicionar:"
    elif f"no_caption_{user_id}" in callback_data:
        new_text = "❌ Você optou por enviar sem legenda."
        await enviar_album(user_id, album, context, None)  # Envia as mídias sem legenda

    # Substitui a mensagem com botões pelo novo texto
    await query.message.edit_text(new_text)






async def receber_texto_unificado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler unificado para mensagens de texto:
      - Se o bot estiver aguardando legenda, trata a mensagem como legenda.
      - Caso contrário, trata como mensagem de texto normal.
    """
    user_id = update.message.chat_id
    album = context.user_data.get("albums", {}).get(user_id)
    if album and album.get("waiting_for_caption"):
        caption = update.message.text
        await enviar_album(user_id, album, context, caption)
        album["waiting_for_caption"] = False
    else:
        await receber_texto(update, context)

async def enviar_album(user_id: int, album: dict, context: ContextTypes.DEFAULT_TYPE, caption: str) -> None:
    """
    Envia as mídias para o administrador e para o usuário conforme as regras:
    - O ADMIN recebe primeiro as informações do usuário e depois as mídias.
    - O USUÁRIO recebe apenas as mídias, com a legenda se ele adicionou.
    """
    await asyncio.sleep(3)  # Aguarda um tempo para agregar todas as mídias

    if not album["media"]:
        return  # Se não houver mídias, sai da função

    try:
        group_media = []      # Lista para fotos e vídeos agrupáveis
        individual_gifs = []  # Lista para animações (GIFs) que devem ser enviadas separadamente

        # Informações do usuário para o administrador
        user_info = (
            f"👤 <b>Nova mídia recebida:</b>\n\n"
            f"🔹 <b>ID do Usuário:</b> <code>{user_id}</code>\n"
            f"🔹 <b>Nome:</b> {album['user_name']}\n"
            f"🔹 <b>Username:</b> @{album['username'] if album['username'] != 'N/A' else 'N/A'}\n"
        )

        # Primeiro, envia as informações do usuário para o ADMIN
        await context.bot.send_message(chat_id=ADMIN_ID, text=user_info, parse_mode="HTML")

        # Processa cada mídia e separa por tipo
        for media in album["media"]:
            if isinstance(media, (InputMediaPhoto, InputMediaVideo)):
                group_media.append(media)
            elif isinstance(media, InputMediaAnimation):
                individual_gifs.append(media)  # Armazena os GIFs para envio individual

        # Envia fotos e vídeos em grupos de até 10 itens
        for i in range(0, len(group_media), 10):
            chunk = group_media[i:i+10]

            # Define a legenda apenas para a primeira mídia do grupo (Telegram só permite uma legenda por grupo)
            if caption:
                chunk[0] = InputMediaPhoto(media=chunk[0].media, caption=caption, parse_mode="HTML") if isinstance(chunk[0], InputMediaPhoto) else \
                           InputMediaVideo(media=chunk[0].media, caption=caption, parse_mode="HTML")

            await context.bot.send_media_group(chat_id=user_id, media=chunk)  # Para o usuário (sem informações)
            await context.bot.send_media_group(chat_id=ADMIN_ID, media=chunk)  # Para o administrador

        # Envia os GIFs individualmente, garantindo que todos tenham a legenda
        for gif in individual_gifs:
            await context.bot.send_animation(chat_id=user_id, animation=gif.media, caption=caption, parse_mode="HTML")
            await context.bot.send_animation(chat_id=ADMIN_ID, animation=gif.media, caption=caption, parse_mode="HTML") 

    except Exception as e:
        await notificar_erro(context, e, user_id=user_id)
    finally:
        # Limpa o álbum para permitir novos envios
        album["media"].clear()
        album["original_captions"].clear()
        album["user_info_sent"] = False
        album["waiting_for_caption"] = False
        album["question_sent"] = False
# ------------------------------
# Função Principal
# ------------------------------
def main() -> None:
    """
    Configuração e inicialização do bot.
    """
    logger.info("🤖 Bot Anônimo Iniciado")
    app = Application.builder().token(BOT_TOKEN).build()

    # Registrando handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION, receber_midia))
    app.add_handler(CallbackQueryHandler(callback_handler))
    # Handler unificado para mensagens de texto (para legenda ou mensagem normal)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_texto_unificado))
    
    app.add_error_handler(error_handler)

    # Inicia o polling
    app.run_polling()

if __name__ == "__main__":
    main()
