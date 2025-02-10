# ------------------------------
# Importações
# ------------------------------
import asyncio
import logging
import html
from telegram import (
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaAnimation,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Update
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler
)
import httpx
from httpx import TimeoutException, ReadTimeout

import gettext  # Para internacionalização
from pathlib import Path  # Para manipulação de caminhos de arquivos

# ------------------------------
# Configuração de Internacionalização (i18n)
# ------------------------------
LOCALES_DIR = Path(__file__).parent / "locales"  # Diretório das traduções


def setup_locale(context: ContextTypes.DEFAULT_TYPE, lang_code: str = None, force_lang: bool = False) -> callable:
    """ 
    Configura o idioma do bot com base no contexto do usuário.
    Se force_lang for True, sempre retorna 'pt_BR' (português).
    """
    lang = 'pt_BR' if force_lang else (lang_code or 'pt_BR')  # Garante que admin recebe sempre em português

    if context and 'lang' in context.user_data and not force_lang:
        lang = context.user_data['lang']
    
    try:
        translation = gettext.translation(
            'bot',
            localedir=LOCALES_DIR,
            languages=[lang],
            fallback=True
        )
        translation.install()
        logger.info(f"Idioma carregado: {lang}")
        return translation.gettext
    except Exception as e:
        logger.error(f"Erro ao carregar tradução: {e}")
        return gettext.gettext
    

# ------------------------------
# Configurações do Bot
# ------------------------------
BOT_TOKEN = "6333929876:AAHVBeNeA3w4a0mc0U5K1HZ3OlwDazMfecw"
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

async def fazer_requisicao_com_retry(url: str, method: str = "GET", data=None, headers=None, max_retries: int = 3) -> httpx.Response:
    """
    Realiza uma requisição HTTP com tentativas de repetição em caso de erro de leitura.
    """
    attempt = 0
    while attempt < max_retries:
        try:
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(url, headers=headers, timeout=10)
                elif method == "POST":
                    response = await client.post(url, data=data, headers=headers, timeout=10)
                else:
                    raise ValueError("Método HTTP não suportado.")
                
                response.raise_for_status()  # Lança uma exceção se o status não for 2xx
                return response
        except (httpx.ReadTimeout, httpx.TimeoutException, httpx.RequestError) as e:
            attempt += 1
            logger.warning(f"Tentativa {attempt} de {max_retries} falhou: {e}")
            await asyncio.sleep(2)  # Aguarda 2 segundos antes de tentar novamente
        except Exception as e:
            logger.error(f"Erro inesperado durante a requisição: {e}")
            break
    raise httpx.ReadError(f"Todas as {max_retries} tentativas falharam.")

async def notificar_erro(context: ContextTypes.DEFAULT_TYPE, error: Exception, user_id: int = None) -> None:
    """
    Notifica o administrador sobre erros.
    """
    _ = setup_locale(context, force_lang=True)  # Força português
    error_message = _("error_detected").format(error=error, user_id=user_id or 'Desconhecido')
    try:
        await fazer_requisicao_com_retry(
            url=f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            method="POST",
            data={
                "chat_id": ADMIN_ID,
                "text": error_message,
                "parse_mode": "HTML"
            }
        )
    except httpx.ReadError as e:
        logger.critical(f"Falha ao notificar o admin após várias tentativas: {e}")

async def enviar_info_usuario(user_id: int, user_name: str, username: str, context: ContextTypes.DEFAULT_TYPE, tipo_interacao: str) -> None:
    """
    Envia informações do usuário para o administrador.
    """
    _ = setup_locale(context)  # Carrega o idioma do usuário
    if tipo_interacao == "start":
        user_info = _("user_interaction").format(user_id=user_id, user_name=user_name, username=username)
    elif tipo_interacao == "midia":
        user_info = _("new_media_received").format(user_id=user_id, user_name=user_name, username=username)
    elif tipo_interacao == "feedback":
        user_info = _("new_feedback_received").format(user_id=user_id, user_name=user_name, username=username, feedback="Aguardando feedback...")
    else:
        user_info = _("unexpected_error")

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
    await enviar_info_usuario(user_id, user_name, username, context, tipo_interacao="start")

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
    Processa todos os tipos de mídia (fotos, vídeos, GIFs, figurinhas, documentos, áudios, voz, videonotes).
    """
    _ = setup_locale(context)  # Carrega o idioma do usuário
    user_id = update.message.chat_id
    try:
        user_albums = context.user_data.setdefault("albums", {})
        album = user_albums.setdefault(user_id, {
            "media": [],  # Armazena mídias que suportam legendas
            "media_sem_legenda": [],  # Armazena mídias que não suportam legendas
            "user_info_sent": False,
            "waiting_for_caption": False,
            "question_sent": False,
            "user_name": None,
            "username": None,
        })

        # Atualiza as informações do usuário no álbum
        if album["user_name"] is None:
            album["user_name"] = update.message.from_user.first_name or "N/A"
        if album["username"] is None:
            album["username"] = update.message.from_user.username or "N/A"

        # Envia informações do usuário para o administrador
        if not album["user_info_sent"]:
            await enviar_info_usuario(
                user_id=user_id,
                user_name=album['user_name'],
                username=album['username'],
                context=context,
                tipo_interacao="midia"
            )
            album["user_info_sent"] = True  # Marca como enviado

        # Processa diferentes tipos de mídia
        if update.message.photo:
            media = InputMediaPhoto(media=update.message.photo[-1].file_id)
            album["media"].append(media)  # Fotos suportam legendas
        elif update.message.video:
            media = InputMediaVideo(media=update.message.video.file_id)
            album["media"].append(media)  # Vídeos suportam legendas
        elif update.message.animation:  # GIFs são tratados como animações
            media = InputMediaAnimation(media=update.message.animation.file_id)
            album["media"].append(media)  # GIFs suportam legendas
        elif update.message.sticker:
            media = InputMediaAnimation(media=update.message.sticker.file_id)  # Figurinhas são tratadas como animações
            album["media_sem_legenda"].append(media)  # Figurinhas não suportam legendas
        elif update.message.document:
            # Verifica se o documento é um GIF
            if update.message.document.mime_type == "image/gif":
                media = InputMediaAnimation(media=update.message.document.file_id)  # Trata GIFs como animações
                album["media"].append(media)  # GIFs suportam legendas
            else:
                media = InputMediaDocument(media=update.message.document.file_id)  # Outros documentos
                album["media_sem_legenda"].append(media)  # Documentos não suportam legendas
        elif update.message.audio:
            media = InputMediaAudio(media=update.message.audio.file_id)
            album["media_sem_legenda"].append(media)  # Áudios não suportam legendas
        elif update.message.voice:
            media = InputMediaAudio(media=update.message.voice.file_id)  # Áudio de voz é tratado como áudio
            album["media_sem_legenda"].append(media)  # Áudios de voz não suportam legendas
        elif update.message.video_note:
            media = InputMediaVideo(media=update.message.video_note.file_id)  # Videonotes são tratados como vídeos
            album["media_sem_legenda"].append(media)  # Videonotes não suportam legendas
        else:
            await update.message.reply_text(_("unsupported_format"))
            return

        # Envia mídias que não suportam legendas imediatamente
        if album["media_sem_legenda"]:
            for media in album["media_sem_legenda"]:
                if isinstance(media, InputMediaAudio):
                    await context.bot.send_audio(chat_id=user_id, audio=media.media)
                    await context.bot.send_audio(chat_id=ADMIN_ID, audio=media.media)
                elif isinstance(media, InputMediaAnimation) and media.media.startswith("CAAC"):  # Figurinhas
                    await context.bot.send_sticker(chat_id=user_id, sticker=media.media)
                    await context.bot.send_sticker(chat_id=ADMIN_ID, sticker=media.media)
                elif isinstance(media, InputMediaVideo) and hasattr(update.message, 'video_note') and update.message.video_note:  # Videonotes
                    await context.bot.send_video_note(chat_id=user_id, video_note=media.media)
                    await context.bot.send_video_note(chat_id=ADMIN_ID, video_note=media.media)
                elif isinstance(media, InputMediaDocument):
                    await context.bot.send_document(chat_id=user_id, document=media.media)
                    await context.bot.send_document(chat_id=ADMIN_ID, document=media.media)
            album["media_sem_legenda"].clear()  # Limpa a lista após o envio

        # Se houver mídias que suportam legendas, pergunta sobre a legenda no final
        if album["media"] and not album["question_sent"]:
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















async def enviar_album(user_id: int, album: dict, context: ContextTypes.DEFAULT_TYPE, caption: str, update: Update = None) -> None:
    """
    Envia o álbum de mídias que suportam legendas.
    Fotos e vídeos são agrupados (em lotes de até 10), enquanto GIFs são enviados separadamente.
    A legenda é aplicada à primeira mídia de cada lote.
    """
    _ = setup_locale(context)  # Carrega o idioma do usuário
    await asyncio.sleep(3)

    if not album["media"]:
        return

    try:
        # Separa as mídias em duas listas:
        # - midias_agrupadas: Fotos e vídeos (podem ser enviados em grupo)
        # - midias_isoladas: GIFs (devem ser enviados separadamente)
        midias_agrupadas = []
        midias_isoladas = []

        for media in album["media"]:
            if isinstance(media, InputMediaAnimation):  # GIFs
                midias_isoladas.append(media)
            else:  # Fotos e vídeos
                midias_agrupadas.append(media)

        # Envia mídias agrupadas (fotos e vídeos) em lotes de até 10
        if midias_agrupadas:
            # Divide as mídias em lotes de 10
            for i in range(0, len(midias_agrupadas), 10):
                lote = midias_agrupadas[i:i + 10]

                # Adiciona a legenda à primeira mídia de cada lote
                if caption:
                    if isinstance(lote[0], InputMediaPhoto):
                        lote[0] = InputMediaPhoto(media=lote[0].media, caption=caption)
                    elif isinstance(lote[0], InputMediaVideo):
                        lote[0] = InputMediaVideo(media=lote[0].media, caption=caption)

                # Envia o lote de mídias para o usuário e o administrador
                await context.bot.send_media_group(chat_id=user_id, media=lote)
                await context.bot.send_media_group(chat_id=ADMIN_ID, media=lote)

        # Envia mídias isoladas (GIFs)
        if midias_isoladas:
            for media in midias_isoladas:
                if isinstance(media, InputMediaAnimation):
                    await context.bot.send_animation(
                        chat_id=user_id,
                        animation=media.media,
                        caption=caption if caption else None
                    )
                    await context.bot.send_animation(
                        chat_id=ADMIN_ID,
                        animation=media.media,
                        caption=caption if caption else None
                    )

        # Solicita feedback após o envio de todas as mídias
        await solicitar_feedback(user_id, context)

    except Exception as e:
        await notificar_erro(context, e, user_id=user_id)
    finally:
        # Limpa os dados do usuário após o envio
        album["media"].clear()
        album["waiting_for_caption"] = False
        album["question_sent"] = False
        # Remove o álbum do contexto do usuário se não for mais necessário
        if user_id in context.user_data.get("albums", {}):
            del context.user_data["albums"][user_id]





















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
        # Define o estado para esperar a legenda
        album["waiting_for_caption"] = True
        new_text = _("send_caption")
    elif f"no_caption_{user_id}" in callback_data:
        # Envia as mídias sem legenda e limpa o estado
        new_text = _("no_caption_selected")
        await enviar_album(user_id, album, context, None, update)
        album["waiting_for_caption"] = False  # Limpa o estado

    await query.message.edit_text(new_text)

async def receber_texto_unificado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler unificado para mensagens de texto.
    Se o bot estiver aguardando feedback, trata a mensagem como feedback;
    caso contrário, processa normalmente (por exemplo, como legenda ou mensagem comum).
    """
    _ = setup_locale(context)  # Carrega o idioma do usuário
    user_id = update.message.chat_id

    # Se o bot estiver aguardando feedback, processa essa mensagem como feedback
    if context.user_data.get("waiting_for_feedback", False):
        await receber_feedback(update, context)
        return

    # Verifica se há um álbum esperando por legenda
    album = context.user_data.get("albums", {}).get(user_id)
    if album and album.get("waiting_for_caption"):
        caption = update.message.text
        await enviar_album(user_id, album, context, caption, update)
        album["waiting_for_caption"] = False  # Limpa o estado após enviar a legenda
    else:
        await receber_texto(update, context)

# ------------------------------
# Sistema de Feedback (Flaskank)
# ------------------------------

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler para o comando /feedback.
    """
    _ = setup_locale(context)
    user_id = update.message.chat_id
    
    # Marca que o feedback foi solicitado via comando
    context.user_data["feedback_via_command"] = True
    
    await update.message.reply_text(_("send_feedback"))
    context.user_data["waiting_for_feedback"] = True
    
async def solicitar_feedback(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = setup_locale(context)  # Carrega o idioma do usuário
    
    # Define o teclado com as opções de feedback
    keyboard = [
        [InlineKeyboardButton(_("yes_feedback"), callback_data="feedback_yes")],
        [InlineKeyboardButton(_("no_feedback"), callback_data="feedback_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Envia a mensagem de solicitação de feedback diretamente para o chat do usuário
    await context.bot.send_message(chat_id=user_id, text=_("ask_feedback"), reply_markup=reply_markup)
    
    # Armazena o estado de feedback no contexto do usuário
    context.user_data["waiting_for_feedback"] = True

async def processar_feedback_escolha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Processa a escolha do usuário sobre fornecer feedback.
    """
    _ = setup_locale(context)  # Carrega o idioma do usuário
    query = update.callback_query
    await query.answer()  # Confirma o recebimento da callback
    callback_data = query.data

    if callback_data == "feedback_yes":
        # Solicita que o usuário digite o feedback
        await query.message.edit_text(_("send_feedback"))
        context.user_data["waiting_for_feedback"] = True
    elif callback_data == "feedback_no":
        # Exibe uma mensagem específica para quando o usuário optar por não enviar feedback
        await query.message.edit_text(_("feedback_declined"))
        await query.message.reply_text(_("forward_media_message"))  # Informa que pode encaminhar as mídias
        context.user_data["waiting_for_feedback"] = False
        
async def receber_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Processa o feedback enviado pelo usuário.
    """
    _ = setup_locale(context)
    user_id = update.message.chat_id
    feedback_text = update.message.text

    if not context.user_data.get("waiting_for_feedback", False):
        return

    try:
        user_name = update.message.from_user.first_name or "N/A"
        username = update.message.from_user.username or "N/A"

        feedback_info = _("new_feedback_received").format(
            user_id=user_id,
            user_name=user_name,
            username=username,
            feedback=safe_escape(feedback_text)
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=feedback_info, parse_mode="HTML")
        
        # Verifica se foi solicitado via comando
        if context.user_data.get("feedback_via_command"):
            await update.message.reply_text(_("feedback_thanks"))  # Apenas esta mensagem
        else:
            await update.message.reply_text(_("feedback_thanks"))
            await update.message.reply_text(_("forward_media_message"))  # Mantém para fluxo normal

    except Exception as e:
        await notificar_erro(context, e, user_id=user_id)
    finally:
        # Limpa os estados
        context.user_data["waiting_for_feedback"] = False
        context.user_data.pop("feedback_via_command", None)  # Remove a flag
        
        # ------------------------------
# Função Principal
# ------------------------------
def main() -> None:
    """
    Inicializa o bot.
    """
    logger.info("🤖 Bot Anônimo Iniciado")
    app = Application.builder().token(BOT_TOKEN).build()

    # Registra os handlers de comandos e mensagens
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("language", set_language))
    app.add_handler(CommandHandler("feedback", feedback_command))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))

    # Adiciona handlers para todos os tipos de mídia
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.Sticker.ALL |
        filters.Document.ALL | filters.AUDIO | filters.VOICE | filters.VIDEO_NOTE,
        receber_midia
    ))

    # Registra callbacks específicos:
    app.add_handler(CallbackQueryHandler(callback_handler, pattern="^(add_caption_|no_caption_)"))
    app.add_handler(CallbackQueryHandler(processar_feedback_escolha, pattern="^feedback_"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_texto_unificado))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/feedback.*$"), receber_feedback))

    app.add_error_handler(error_handler)

    # Inicia o bot
    app.run_polling()

if __name__ == "__main__":
    main()