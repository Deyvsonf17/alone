from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import html
import sqlite3

# Configuração inicial do banco de dados
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()

# Criar tabelas caso não existam
cursor.execute('''
CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    media_type TEXT,
    media_file_id TEXT,
    caption TEXT,
    status TEXT DEFAULT 'pending',
    rejection_reason TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS bot_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    is_active INTEGER DEFAULT 1
)
''')

# Inserir valor padrão na tabela bot_status (se não existir)
cursor.execute("INSERT OR IGNORE INTO bot_status (id, is_active) VALUES (1, 1)")
conn.commit()

# IDs fixos
ADMIN_ID = 6460184219
GROUP_ID = -1002424564273
BOT_USERNAME = "Anonimas175_bot"  # Substituir pelo username do seu bot (sem @)

# Função para tratar caracteres de forma segura
def safe_escape(text):
    if text:
        return html.escape(text).encode("utf-16", "surrogatepass").decode("utf-16")
    return ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "👋 <b>Bem-vindo!</b>\n\n"
        "📋 <b>Como funciona:</b>\n"
        "1️⃣ Envie uma única mídia (foto ou vídeo) por vez.\n"
        "2️⃣ A mídia será analisada por um administrador.\n"
        "3️⃣ Após aprovação, será enviada ao grupo.\n\n"
        "🔒 <b>Todos os envios são 100% anônimos!</b> Ninguém saberá quem enviou a mídia.\n\n"
        "📜 <b>Regras adicionais:</b>\n\n"
        "📷 <b>Fotos ou vídeos com crianças:</b>\n"
        "• É permitido apenas se acompanhadas por um adulto, com o <b>foco principal no adulto</b>.\n"
        "• Mídias que mostrem crianças menores de 15 anos sozinhas <b>não serão aprovadas</b>.\n"
        "• <b>Não será aceito conteúdo inadequado ou ilegal envolvendo menores de idade</b> (CP ou qualquer outro tipo).\n\n"
        "💡 <b>Atenção:</b> O foco da mídia deve ser sempre o adulto, <b>não o menor de idade</b>.\n\n"
        "🔞 <b>Sobre conteúdos adultos:</b>\n"
        "• <b>Pornografia explícita será barrada</b>.\n"
        "• <b>Nudes estão permitidos</b>, mas passarão por avaliação dos administradores.\n\n"
        "📝 <b>Envio de mídias de menores de idade:</b>\n"
        "• Caso a mídia contenha um menor de idade sozinho, informe a idade na legenda para avaliação.\n"
        "• Mídias que desrespeitem essa regra <b>não serão aceitas</b>.\n"
    )
    await update.message.reply_text(welcome_message, parse_mode="HTML")


# Função para ligar o bot
async def ligar_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("UPDATE bot_status SET is_active = 1 WHERE id = 1")
    conn.commit()
    await context.bot.send_message(
        GROUP_ID, 
        "🚦 O bot foi <b>ligado</b>. O envio de mídias está habilitado!", 
        parse_mode="HTML"
    )
    await update.message.reply_text("✅ O bot foi ligado com sucesso!")

# Função para desligar o bot
async def desligar_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("UPDATE bot_status SET is_active = 0 WHERE id = 1")
    conn.commit()
    await context.bot.send_message(
        GROUP_ID, 
        "🚦 O bot foi <b>desligado</b>. O envio de mídias está temporariamente desabilitado!", 
        parse_mode="HTML"
    )
    await update.message.reply_text("✅ O bot foi desligado com sucesso!")

# Receber mídias enviadas pelo usuário
async def receber_midia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Verificar se a mensagem é de um chat privado
    if update.message.chat.type != "private":
        return  # Ignorar mensagens que não sejam de chat privado

    cursor.execute("SELECT is_active FROM bot_status WHERE id = 1")
    is_active = cursor.fetchone()[0]

    if not is_active:
        await update.message.reply_text("⚠️ O envio de mídias está temporariamente desabilitado. Tente novamente mais tarde.")
        return

    user_id = update.message.chat_id
    username = safe_escape(update.message.from_user.username or "Usuário sem username")
    first_name = safe_escape(update.message.from_user.first_name or "Usuário sem nome")
    caption = safe_escape(update.message.caption or "")

    # Verificar se é foto ou vídeo
    if update.message.photo:
        media_type = "photo"
        media_file_id = update.message.photo[-1].file_id
    elif update.message.video:
        media_type = "video"
        media_file_id = update.message.video.file_id
    else:
        await update.message.reply_text("Por favor, envie uma foto ou vídeo válido.")
        return

    # Salvar a mídia no banco de dados
    cursor.execute(
        "INSERT INTO media (user_id, username, media_type, media_file_id, caption) VALUES (?, ?, ?, ?, ?)",
        (user_id, username, media_type, media_file_id, caption),
    )
    conn.commit()
    media_id = cursor.lastrowid

    # Enviar informações ao administrador
    await context.bot.send_message(
        ADMIN_ID,
        text=(
            f"📩 <b>Nova mídia recebida para análise (envio anônimo):</b>\n\n"
            f"🔑 <b>UserID:</b> <code>{user_id}</code>\n"
            f"👤 <b>Username:</b> @{username}\n"
            f"🖋️ <b>Nome:</b> {first_name}\n"
            f"🔗 <b>Mídia ID:</b> <code>{media_id}</code>\n"
            f"{f'📝 <b>Legenda:</b> {caption}' if caption else ''}\n"
            "⚠️ <b>Envio anônimo:</b> Ninguém saberá quem enviou."
        ),
        parse_mode="HTML",
    )
# Criar botões de aprovação/reprovação
buttons = [
    [
        InlineKeyboardButton("✅ Aprovar", callback_data=f"aprovar_{media_id}"),
        InlineKeyboardButton("❌ Reprovar", callback_data=f"reprovar_{media_id}")
    ]
]

# Enviar a mídia para o administrador
if media_type == "photo":
    await context.bot.send_photo(
        ADMIN_ID,
        media_file_id,
        caption=f"📷 <b>Foto enviada para análise</b>\n\n{f'📝 <b>Legenda:</b> {caption}' if caption else ''}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
elif media_type == "video":
    await context.bot.send_video(
        ADMIN_ID,
        media_file_id,
        caption=f"🎥 <b>Vídeo enviada para análise</b>\n\n{f'📝 <b>Legenda:</b> {caption}' if caption else ''}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# Informar ao usuário que a mídia foi enviada
await update.message.reply_text("Sua mídia foi enviada para análise. O envio é anônimo e ninguém saberá quem a enviou.")

# Função para lidar com callbacks de aprovação/reprovação
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("aprovar_"):
        media_id = int(data.split("_")[1])
        cursor.execute("SELECT user_id, media_file_id, media_type, caption FROM media WHERE id = ?", (media_id,))
        media = cursor.fetchone()

        if media:
            user_id, media_file_id, media_type, caption = media

            # Construir a legenda final para o grupo
            group_caption = f"{safe_escape(caption)}\n\n📷 #envioanonimo\n @{BOT_USERNAME}" if caption else f"📷 #envioanonimo\n @{BOT_USERNAME}"

            # Enviar a mídia para o grupo com a legenda final
            if media_type == "photo":
                await context.bot.send_photo(GROUP_ID, media_file_id, caption=group_caption, parse_mode="HTML")
            elif media_type == "video":
                await context.bot.send_video(GROUP_ID, media_file_id, caption=group_caption, parse_mode="HTML")

            # Atualizar status no banco de dados
            cursor.execute("UPDATE media SET status = 'approved' WHERE id = ?", (media_id,))
            conn.commit()

            # Informar ao administrador
            await query.message.reply_text("✅ Aprovado: A mídia foi enviada ao grupo.")

            # Notificar o usuário
            await context.bot.send_message(
                user_id,
                "✅ Sua mídia foi aprovada e enviada ao grupo. O envio foi anônimo e ninguém saberá quem a enviou.",
            )

    elif data.startswith("reprovar_"):
        media_id = int(data.split("_")[1])
        context.user_data["awaiting_reason"] = media_id
        await query.message.reply_text("❌ Envie o motivo da reprovação agora como uma mensagem de texto.")

# Receber motivo de reprovação
async def receber_motivo_reprovacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ignorar mensagens que não sejam do administrador ou não estejam no contexto de reprovação
    if update.message is None or update.message.chat_id != ADMIN_ID or "awaiting_reason" not in context.user_data:
        return

    # Recuperar o ID da mídia que está aguardando um motivo de reprovação
    media_id = context.user_data.get("awaiting_reason")

    if not media_id:
        await update.message.reply_text("⚠️ Nenhuma mídia está aguardando um motivo de reprovação.")
        return

    motivo = safe_escape(update.message.text)
    cursor.execute("SELECT user_id FROM media WHERE id = ?", (media_id,))
    media = cursor.fetchone()

    if media:
        user_id = media[0]
        # Atualizar o status da mídia no banco de dados com o motivo
        cursor.execute("UPDATE media SET status = 'rejected', rejection_reason = ? WHERE id = ?", (motivo, media_id))
        conn.commit()

        # Informar ao administrador que a reprovação foi registrada
        await update.message.reply_text("❌ Rejeição registrada e enviada ao usuário.")

        # Notificar o usuário que a mídia foi reprovada
        await context.bot.send_message(
            user_id,
            f"❌ Sua mídia foi reprovada.\n\n📝 <b>Motivo:</b> {motivo}\n\n⚠️ <b>Envio Anônimo:</b> Ninguém sabe quem enviou.",
            parse_mode="HTML",
        )

        # Limpar o estado para a próxima reprovação
        del context.user_data["awaiting_reason"]
    else:
        await update.message.reply_text("⚠️ Mídia não encontrada para registrar o motivo.")



def main():
    print("Inicializando o bot...")
    application = Application.builder().token("7702255202:AAHcxWp63HOFJgJpkYEtiGxHmFvx08nBpmY").build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ligar", ligar_bot, filters.User(ADMIN_ID)))
    application.add_handler(CommandHandler("desligar", desligar_bot, filters.User(ADMIN_ID)))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, receber_midia))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_texto))  # Handler para mensagens genéricas
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_motivo_reprovacao))  # Handler para motivo
    application.add_handler(CallbackQueryHandler(callback_query_handler))

    # Iniciar bot
    application.run_polling()

if __name__ == "__main__":
    main()

