# ------------------------------
# Importações
# ------------------------------
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
import gettext  # Para internacionalização
from pathlib import Path  # Para manipulação de caminhos de arquivos

# ------------------------------
# Configuração de Internacionalização (i18n)
# ------------------------------
LOCALES_DIR = Path(__file__).parent / "locales"  # Diretório das traduções

def setup_locale(context: ContextTypes.DEFAULT_TYPE, lang_code: str = None) -> callable:
    """
    Configura o idioma do bot com base no contexto do usuário.
    """
    lang = lang_code or 'pt_BR'  # Usa o idioma fornecido ou o padrão
    if context and 'lang' in context.user_data:
        lang = context.user_data['lang']
    
    try:
        translation = gettext.translation(
            'bot',
            localedir=LOCALES_DIR,
            languages=[lang],
            fallback=True
        )
        translation.install()
        return translation.gettext
    except Exception as e:
        logger.error(f"Erro ao carregar tradução: {e}")
        return gettext.gettext

# ------------------------------
# Configurações do Bot
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
    """
    Escapa caracteres especiais no texto.
    """
    try:
        return html.escape(text).encode("utf-16", "surrogatepass").decode("utf-16") if text else ""
    except Exception as e:
        logger.error(f"Erro ao escapar texto: {e}")
        return "[Conteúdo não legível]"

async def notificar_erro(context: ContextTypes.DEFAULT_TYPE, error: Exception, user_id: int = None) -> None:
    """
    Notifica o administrador sobre erros.
    """
    _ = setup_locale(context)  # Carrega o idioma do usuário
    error_message = _("error_detected").format(error=error, user_id=user_id or 'Desconhecido')
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=error_message, parse_mode="HTML")
    except Exception as e:
        logger.critical(f"Erro ao notificar o admin: {e}")

async def enviar_info_usuario(user_id: int, user_name: str, username: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Envia informações do usuário para o administrador.
    """
    _ = setup_locale(context)  # Carrega o idioma do usuário
    user_info = _("user_interaction").format(user_id=user_id, user_name=user_name, username=username)
    await context.bot.send_message(chat_id=ADMIN_ID, text=user_info, parse_mode="HTML")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Manipula erros não tratados.
    """
    logger.error("Exceção não tratada:", exc_info=context.error)
    _ = setup_locale(context)  # Carrega o idioma do usuário
    error_msg = _("unexpected_error")
    if update and isinstance(update, Update):
        await update.effective_message.reply_text(error_msg)
    await notificar_erro(context, context.error)

# ------------------------------
# Handlers de Mensagens
# ------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler do comando /start.
    Exibe um menu de seleção de idioma e envia informações do usuário para o administrador.
    """
    user = update.message.from_user

    # Define o idioma padrão (se ainda não estiver definido)
    if 'lang' not in context.user_data:
        context.user_data['lang'] = 'pt_BR'  # Idioma padrão

    # Carrega o idioma do usuário
    _ = setup_locale(context)

    # Envia informações do usuário para o administrador
    user_id = user.id
    user_name = user.first_name or "N/A"
    username = user.username or "N/A"
    await enviar_info_usuario(user_id, user_name, username, context)

    # Exibe o menu de seleção de idioma
    keyboard = [
        [
            InlineKeyboardButton("🇧🇷 Português", callback_data="lang_zh_CN"),
            InlineKeyboardButton("🇺🇸 English", callback_data="lang_en_US"),
        ],
        [
            InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es_ES")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Mensagem de boas-vindas com instruções para escolher o idioma
    welcome_message = _("welcome_message")
    welcome_msg = await update.message.reply_text(welcome_message, parse_mode="HTML")
    await update.message.reply_text(_("select_language"), reply_markup=reply_markup)

    # Armazenar o ID da mensagem de boas-vindas para edição posterior
    context.user_data['welcome_msg_id'] = welcome_msg.message_id

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para escolher o idioma.
    """
    _ = setup_locale(context)  # Carrega o idioma do usuário
    keyboard = [
        [
            InlineKeyboardButton("🇧🇷 Português", callback_data="lang_zh_CN"),
            InlineKeyboardButton("🇺🇸 English", callback_data="lang_en_US"),
        ],
        [
            InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es_ES")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(_("select_language"), reply_markup=reply_markup)

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para processar a escolha de idioma.
    """
    query = update.callback_query
    lang_code = query.data.split("_")[1]
    
    # Armazena o idioma escolhido no contexto do usuário
    context.user_data['lang'] = lang_code
    
    # Carrega o idioma específico para este usuário
    _ = setup_locale(context, lang_code)
    
    # Confirma a mudança de idioma
    await query.answer()

    # Apaga a mensagem de boas-vindas original
    if 'welcome_msg_id' in context.user_data:
        welcome_msg_id = context.user_data['welcome_msg_id']
        await context.bot.delete_message(chat_id=query.message.chat_id, message_id=welcome_msg_id)
        
        # Mensagem de boas-vindas no idioma escolhido
        welcome_message = _("welcome_message")
        await query.edit_message_text(welcome_message, parse_mode="HTML")

async def receber_texto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Processa mensagens de texto.
    """
    _ = setup_locale(context)  # Carrega o idioma do usuário
    user_id = update.message.chat_id
    try:
        user_name = update.message.from_user.first_name or "N/A"
        username = update.message.from_user.username or "N/A"
        mensagem = update.message.text

        mensagem_info = _("new_message_received").format(
            user_id=user_id,
            user_name=user_name,
            username=username,
            message=safe_escape(mensagem)
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=mensagem_info, parse_mode="HTML")
        await update.message.reply_text(mensagem)
    except Exception as e:
        await notificar_erro(context, e, user_id=user_id)

async def receber_midia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Processa mídias (fotos, vídeos, GIFs).
    """
    _ = setup_locale(context)  # Carrega o idioma do usuário
    user_id = update.message.chat_id
    try:
        user_albums = context.user_data.setdefault("albums", {})
        album = user_albums.setdefault(user_id, {
            "media": [],
            "original_captions": [],
            "timer": None,
            "user_info_sent": False,
            "waiting_for_caption": False,
            "question_sent": False,
            "user_name": None,
            "username": None,
        })

        if album["user_name"] is None:
            album["user_name"] = update.message.from_user.first_name or "N/A"
        if album["username"] is None:
            album["username"] = update.message.from_user.username or "N/A"

        if update.message.photo:
            media = InputMediaPhoto(media=update.message.photo[-1].file_id)
        elif update.message.video:
            media = InputMediaVideo(media=update.message.video.file_id)
        elif update.message.animation:
            media = InputMediaAnimation(media=update.message.animation.file_id)
        else:
            await update.message.reply_text(_("unsupported_format"))
            return

        album["media"].append(media)
        album["waiting_for_caption"] = False

        if not album["question_sent"]:
            await update.message.reply_text(_("caption_warning"))
            await asyncio.sleep(1)
            await update.message.reply_text(_("caption_info"))
            await asyncio.sleep(0.5)

            keyboard = [
                [InlineKeyboardButton(_("yes_add_caption"), callback_data=f"add_caption_{user_id}")],
                [InlineKeyboardButton(_("no_add_caption"), callback_data=f"no_caption_{user_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(_("ask_caption"), reply_markup=reply_markup)
            album["question_sent"] = True

    except Exception as e:
        await notificar_erro(context, e, user_id=user_id)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Processa callbacks de botões.
    """
    _ = setup_locale(context)  # Carrega o idioma do usuário
    query = update.callback_query
    user_id = query.message.chat_id
    callback_data = query.data

    album = context.user_data.get("albums", {}).get(user_id)
    if not album:
        await query.message.edit_text(_("callback_error"))
        return

    if f"add_caption_{user_id}" in callback_data:
        album["waiting_for_caption"] = True
        new_text = _("send_caption")
    elif f"no_caption_{user_id}" in callback_data:
        new_text = _("no_caption_selected")
        await enviar_album(user_id, album, context, None)

    await query.message.edit_text(new_text)

async def receber_texto_unificado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler unificado para mensagens de texto.
    """
    _ = setup_locale(context)  # Carrega o idioma do usuário
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
    Envia o álbum de mídias para o usuário e o administrador.
    """
    _ = setup_locale(context)  # Carrega o idioma do usuário
    await asyncio.sleep(3)

    if not album["media"]:
        return

    try:
        group_media = []
        individual_gifs = []

        user_info = _("new_media_received").format(
            user_id=user_id,
            user_name=album['user_name'],
            username=album['username']
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=user_info, parse_mode="HTML")

        for media in album["media"]:
            if isinstance(media, (InputMediaPhoto, InputMediaVideo)):
                group_media.append(media)
            elif isinstance(media, InputMediaAnimation):
                individual_gifs.append(media)

        for i in range(0, len(group_media), 10):
            chunk = group_media[i:i+10]
            if caption:
                chunk[0] = InputMediaPhoto(media=chunk[0].media, caption=caption, parse_mode="HTML") if isinstance(chunk[0], InputMediaPhoto) else \
                           InputMediaVideo(media=chunk[0].media, caption=caption, parse_mode="HTML")

            await context.bot.send_media_group(chat_id=user_id, media=chunk)
            await context.bot.send_media_group(chat_id=ADMIN_ID, media=chunk)

        for gif in individual_gifs:
            await context.bot.send_animation(chat_id=user_id, animation=gif.media, caption=caption, parse_mode="HTML")
            await context.bot.send_animation(chat_id=ADMIN_ID, animation=gif.media, caption=caption, parse_mode="HTML")

        # Envia a mensagem "Você já pode encaminhar..." ou equivalente
        forward_message = _("forward_media_message")
        await context.bot.send_message(chat_id=user_id, text=forward_message, parse_mode="HTML")

    except Exception as e:
        await notificar_erro(context, e, user_id=user_id)
    finally:
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
    Inicializa o bot.
    """
    logger.info("🤖 Bot Anônimo Iniciado")
    app = Application.builder().token(BOT_TOKEN).build()

    # Registra os handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("language", set_language))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION, receber_midia))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_texto_unificado))
    
    app.add_error_handler(error_handler)

    # Inicia o bot
    app.run_polling()

if __name__ == "__main__":
    main()