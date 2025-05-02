import discord
from discord.ext import commands
from discord import app_commands, ui
import asyncio
import os
import pymysql
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
import asyncio
import pytz

# Cargar variables de entorno
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Variables de entorno para MySQL en Railway
DB_HOST = os.getenv('MYSQLHOST', 'localhost')
DB_USER = os.getenv('MYSQLUSER', 'root')
DB_PASSWORD = os.getenv('MYSQLPASSWORD', '')
DB_NAME = os.getenv('MYSQLDATABASE', 'railway')
DB_PORT = int(os.getenv('MYSQLPORT', '3306'))

# Configuración del bot con intenciones
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# =============================================
# BASE DE DATOS
# =============================================
def get_db_connection():
    """Obtener conexión a la base de datos MySQL."""
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except pymysql.Error as e:
        print(f"Error al conectar a MySQL: {e}")
        raise

def init_db():
    """Inicializar la base de datos MySQL para sanciones y calificaciones."""
    print("Inicializando base de datos MySQL en Railway...")
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Tabla de sanciones
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sanciones (
                    sanction_id VARCHAR(36) PRIMARY KEY,
                    user_id BIGINT,
                    username VARCHAR(255),
                    reason TEXT,
                    sanction_type VARCHAR(50),
                    proof_url TEXT,
                    admin_id BIGINT,
                    admin_name VARCHAR(255),
                    date DATETIME,
                    active BOOLEAN
                )
            ''')
            # Tabla de calificaciones
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS calificaciones (
                    rating_id VARCHAR(36) PRIMARY KEY,
                    staff_id BIGINT,
                    staff_name VARCHAR(255),
                    rating INT,
                    comment TEXT,
                    user_id BIGINT,
                    user_name VARCHAR(255),
                    date DATETIME
                )
            ''')
            conn.commit()
            print("Tablas 'sanciones' y 'calificaciones' creadas o verificadas correctamente.")
    except pymysql.Error as e:
        print(f"Error al inicializar la base de datos: {e}")
    finally:
        if conn:
            conn.close()
            print("Conexión a la base de datos cerrada.")

# Inicializar base de datos al inicio
init_db()

# =============================================
# CONSTANTES Y CONFIGURACIÓN
# =============================================
class Colors:
    PRIMARY = 0x5865F2  # Discord blurple
    SUCCESS = 0x57F287  # Discord green
    WARNING = 0xFEE75C  # Discord yellow
    DANGER = 0xED4245   # Discord red
    INFO = 0xEB459E     # Discord pink
    MUNICIPALITY = 0xF1C40F
    APPEALS = 0xE67E22
    REPORTS = 0xE74C3C
    ILLEGAL = 0x992D22
    LEGAL = 0x1ABC9C

class Channels:
    TICKETS = 1339386616405561403
    TICKET_LOGS = 1364099901813690419
    CONTROL_PANEL = 1364100260363898890
    ANNOUNCEMENTS = 1354927711306645696
    LOGS = 1364100505990729780
    SANCTIONS = 1339386616405561395
    SANCTION_LOGS = 1367390263743348848
    VIEW_SANCTIONS = 1344075561689026722
    RATINGS = 1339386616405561398  
    JOB_APPLICATIONS = 1365153550816116797  # Channel where /postular-trabajo is used
    JOB_REVIEW = 1365158553412964433  # Channel where staff review applications

class Roles:
    STAFF = [1339386615247798362, 1346545514492985486, 1339386615222767662, 1347803116741066834, 1339386615235346439]
    WARN_1 = 1341459151913746503
    WARN_2 = 1341459663232696416
    WARN_3 = 1341459796846579834
    WARN_4 = 1358226550046326895
    WARN_5 = 1358226564629926060
    MEGANOTICIAS = 1348164800445808661
    BARBERO = 1348163657086799892
    TAXISTA = 1348163838905946122
    BASURERO = 1348163889619144764
    CARTERO = 1348163951921201152
    CAFETERIA = 1348163986230607902
    BANQUERO = 1348164352020185098
    RAPPI = 1348164456814874644
    MECANICO = 1348164518760546314
    COPEC = 1348164577426149419
    TIENDA_ROPA = 1348164652390940714
    GRANJERO = 1348164695621898321
    DOCTOR = 1348164862538416231
    CONSTRUCTOR = 1348164938287419453
    BURGERKING = 1348164981027508295
    JOYERIA = 1348165001579593830
    RESTAURANT_RJ = 1348165107145773096
    PASTELERIA = 1348165182685319169
    AGENCIA_VEHICULOS = 1348165259625631775
    TIENDA_APPLE = 1348165319088144425
    TACOS = 1348165379410890843
    DRAGONES_CHINA = 1348165483878416384
    SUELDO = 1346556183586148514

TICKET_CATEGORIES = {
    "general_help": {
        "id": 1364101565538893924,
        "emoji": "🧩",
        "color": Colors.PRIMARY,
        "title": "Ayuda General",
        "description": "Para cualquier duda o problema general del servidor"
    },
    "municipality": {
        "id": 1364101710431125545,
        "emoji": "🏛️",
        "color": Colors.MUNICIPALITY,
        "title": "Municipalidad",
        "description": "Trámites municipales, licencias, propiedades"
    },
    "purchases": {
        "id": 1364101786734039052,
        "emoji": "🛍️",
        "color": Colors.SUCCESS,
        "title": "Compras",
        "description": "Problemas con compras, beneficios o paquetes VIP"
    },
    "benefits": {
        "id": 1364101877847031858,
        "emoji": "🎁",
        "color": Colors.INFO,
        "title": "Beneficios",
        "description": "Reclamos o consultas sobre beneficios especiales"
    },
    "alliances": {
        "id": 1364101958142660681,
        "emoji": "🤝",
        "color": Colors.PRIMARY,
        "title": "Alianzas",
        "description": "Solicitudes de alianzas entre facciones/empresas"
    },
    "doubts": {
        "id": 1364102041961758770,
        "emoji": "💭",
        "color": Colors.WARNING,
        "title": "Dudas",
        "description": "Consultas sobre reglas, mecánicas o funcionamiento"
    },
    "appeals": {
        "id": 1364102108894199911,
        "emoji": "📜",
        "color": Colors.APPEALS,
        "title": "Apelaciones",
        "description": "Apelar sanciones, baneos o advertencias"
    },
    "reports": {
        "id": 1364102219393142866,
        "emoji": "⚠️",
        "color": Colors.REPORTS,
        "title": "Reportes",
        "description": "Reportar jugadores, bugs o problemas graves"
    },
    "illegal_faction": {
        "id": 1364102328470212748,
        "emoji": "🕵️",
        "color": Colors.ILLEGAL,
        "title": "Facción Ilegal",
        "description": "Registro o consultas de facciones ilegales"
    },
    "robbery_claim": {
        "id": 1364102435425091695,
        "emoji": "🚔",
        "color": Colors.DANGER,
        "title": "Reclamo Robo",
        "description": "Reportar robos o pérdida de items/vehículos"
    },
    "business_creation": {
        "id": 1364102590123479122,
        "emoji": "🏢",
        "color": Colors.LEGAL,
        "title": "Creación Empresa",
        "description": "Solicitud para crear una empresa legal"
    },
    "ck_request": {
        "id": 1364102678816358420,
        "emoji": "💀",
        "color": Colors.DANGER,
        "title": "Solicitud CK",
        "description": "Solicitar Character Kill (muerte permanente)"
    }
}

server_status = "indefinido"

JOB_ROLES = {
    "meganoticias": {"name": "Meganoticias", "role_id": Roles.MEGANOTICIAS},
    "barbero": {"name": "Barbero", "role_id": Roles.BARBERO},
    "taxista": {"name": "Taxista", "role_id": Roles.TAXISTA},
    "basurero": {"name": "Basurero", "role_id": Roles.BASURERO},
    "cartero": {"name": "Cartero", "role_id": Roles.CARTERO},
    "cafeteria": {"name": "Cafetería", "role_id": Roles.CAFETERIA},
    "banquero": {"name": "Banquero", "role_id": Roles.BANQUERO},
    "rappi": {"name": "Rappi", "role_id": Roles.RAPPI},
    "mecanico": {"name": "Mecánico", "role_id": Roles.MECANICO},
    "copec": {"name": "Copec", "role_id": Roles.COPEC},
    "tienda_ropa": {"name": "Tienda de Ropa", "role_id": Roles.TIENDA_ROPA},
    "granjero": {"name": "Granjero", "role_id": Roles.GRANJERO},
    "doctor": {"name": "Doctor", "role_id": Roles.DOCTOR},
    "constructor": {"name": "Constructor", "role_id": Roles.CONSTRUCTOR},
    "burgerking": {"name": "Burger King", "role_id": Roles.BURGERKING},
    "joyeria": {"name": "Joyería", "role_id": Roles.JOYERIA},
    "restaurant_rj": {"name": "Restaurante R&J", "role_id": Roles.RESTAURANT_RJ},
    "pasteleria": {"name": "Pastelería", "role_id": Roles.PASTELERIA},
    "agencia_vehiculos": {"name": "Agencia de Vehículos", "role_id": Roles.AGENCIA_VEHICULOS},
    "tienda_apple": {"name": "Tienda Apple", "role_id": Roles.TIENDA_APPLE},
    "tacos": {"name": "Tacos", "role_id": Roles.TACOS},
    "dragones_china": {"name": "Dragones China", "role_id": Roles.DRAGONES_CHINA}
}

# =============================================
# HELPERS
# =============================================
def create_embed(title: str, description: str, color: int, user: discord.Member = None, thumbnail: str = None) -> discord.Embed:
    """Crear un embed profesional y consistente."""
    embed = discord.Embed(
        title=f"🌟 {title}",
        description=description,
        color=color,
        timestamp=datetime.now()
    )
    embed.set_footer(text="Santiago RP | Sistema Automatizado")
    if user:
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    return embed

# =============================================
# FUNCIONES DE SANCIONES
# =============================================
def save_sanction(user_id: int, username: str, reason: str, sanction_type: str, proof_url: str, admin_id: int, admin_name: str):
    """Guardar una sanción en la base de datos."""
    sanction_id = str(uuid.uuid4())
    date = datetime.now()
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Insertar la sanción
            cursor.execute('''
                INSERT INTO sanciones (sanction_id, user_id, username, reason, sanction_type, proof_url, admin_id, admin_name, date, active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (sanction_id, user_id, username, reason, sanction_type, proof_url, admin_id, admin_name, date, True))
            conn.commit()
            print(f"Sanción {sanction_id} guardada correctamente.")
            return sanction_id
    except pymysql.Error as e:
        print(f"Error al guardar sanción: {e}")
        raise
    finally:
        if conn:
            conn.close()

def count_active_sanctions(user_id: int) -> int:
    """Contar sanciones activas de un usuario."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) as count FROM sanciones WHERE user_id = %s AND active = %s', (user_id, True))
            result = cursor.fetchone()
            count = result['count']
            return count
    except pymysql.Error as e:
        print(f"Error al contar sanciones: {e}")
        raise
    finally:
        if conn:
            conn.close()

def get_user_sanctions(user_id: int) -> list:
    """Obtener todas las sanciones activas de un usuario."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT sanction_id, reason, sanction_type, proof_url, admin_name, date
                FROM sanciones
                WHERE user_id = %s AND active = %s
                ORDER BY date DESC
            ''', (user_id, True))
            sanctions = cursor.fetchall()
            # Convertir a formato de tupla para mantener compatibilidad
            result = [(s['sanction_id'], s['reason'], s['sanction_type'], s['proof_url'], s['admin_name'], s['date'].isoformat()) for s in sanctions]
            return result
    except pymysql.Error as e:
        print(f"Error al obtener sanciones: {e}")
        raise
    finally:
        if conn:
            conn.close()

def delete_user_sanctions(user_id: int) -> int:
    """Marcar todas las sanciones activas de un usuario como inactivas."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('UPDATE sanciones SET active = %s WHERE user_id = %s AND active = %s', (False, user_id, True))
            conn.commit()
            affected_rows = cursor.rowcount
            return affected_rows
    except pymysql.Error as e:
        print(f"Error al borrar sanciones: {e}")
        raise
    finally:
        if conn:
            conn.close()

# =============================================
# AUTOCOMPLETE PARA SANCIONES
# =============================================
async def sanction_type_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Autocompletar tipos de sanción."""
    sanction_types = [
        {"name": "Advertencia 1", "role_id": Roles.WARN_1},
        {"name": "Advertencia 2", "role_id": Roles.WARN_2},
        {"name": "Advertencia 3", "role_id": Roles.WARN_3}
    ]
    return [
        app_commands.Choice(name=sanction["name"], value=sanction["name"])
        for sanction in sanction_types
        if current.lower() in sanction["name"].lower()
    ]

# =============================================
# FUNCIONES DE CALIFICACIONES
# =============================================
def save_rating(staff_id: int, staff_name: str, rating: int, comment: str, user_id: int, user_name: str):
    """Guardar una calificación en la base de datos."""
    rating_id = str(uuid.uuid4())
    date = datetime.now()
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('''
                INSERT INTO calificaciones (rating_id, staff_id, staff_name, rating, comment, user_id, user_name, date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (rating_id, staff_id, staff_name, rating, comment, user_id, user_name, date))
            conn.commit()
            return rating_id
    except pymysql.Error as e:
        print(f"Error al guardar calificación: {e}")
        raise
    finally:
        if conn:
            conn.close()

def get_top_staff() -> tuple:
    """Obtener el staff con mejor promedio de calificación (mínimo 3 calificaciones)."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('''
                SELECT staff_id, staff_name, AVG(rating) as avg_rating, COUNT(rating) as count_rating
                FROM calificaciones
                GROUP BY staff_id
                HAVING COUNT(rating) >= 3
                ORDER BY AVG(rating) DESC
                LIMIT 1
            ''')
            result = cursor.fetchone()
            if result:
                return (result['staff_id'], result['staff_name'], result['avg_rating'], result['count_rating'])
            return None
    except pymysql.Error as e:
        print(f"Error al obtener top staff: {e}")
        raise
    finally:
        if conn:
            conn.close()

def clear_ratings():
    """Borrar todas las calificaciones de la base de datos."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('DELETE FROM calificaciones')
            conn.commit()
    except pymysql.Error as e:
        print(f"Error al borrar calificaciones: {e}")
        raise
    finally:
        if conn:
            conn.close()

# =============================================
# AUTOCOMPLETE
# =============================================
async def sanction_type_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Autocompletar tipos de sanción."""
    sanction_types = [
        {"name": "Advertencia 1", "role_id": Roles.WARN_1},
        {"name": "Advertencia 2", "role_id": Roles.WARN_2},
        {"name": "Advertencia 3", "role_id": Roles.WARN_3}
    ]
    return [
        app_commands.Choice(name=sanction["name"], value=sanction["name"])
        for sanction in sanction_types
        if current.lower() in sanction["name"].lower()
    ]

async def rating_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Autocompletar calificaciones con estrellas (1 a 5)."""
    ratings = [
        {"value": "1", "name": "🌟 1 Estrella"},
        {"value": "2", "name": "🌟🌟 2 Estrellas"},
        {"value": "3", "name": "🌟🌟🌟 3 Estrellas"},
        {"value": "4", "name": "🌟🌟🌟🌟 4 Estrellas"},
        {"value": "5", "name": "🌟🌟🌟🌟🌟 5 Estrellas"}
    ]
    return [
        app_commands.Choice(name=rating["name"], value=rating["value"])
        for rating in ratings
        if current.lower() in rating["name"].lower() or not current
    ]

# =============================================
# COMPONENTES UI PERSONALIZADOS
# =============================================
class CloseServerModal(ui.Modal, title="🔒 Cerrar Servidor"):
    reason = ui.TextInput(
        label="Razón del cierre",
        placeholder="Ejemplo: Mantenimiento programado, falta de jugadores...",
        style=discord.TextStyle.long,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class GradientButton(ui.Button):
    """Botón con efecto de gradiente personalizado y cooldown."""
    cooldowns = {}  # Diccionario para rastrear cooldowns: {user_id: {button_id: timestamp}}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.original_label = self.label
        self.original_style = self.style
        self.original_emoji = self.emoji
        
    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        button_id = self.custom_id

        # Verificar cooldown
        if user_id in self.cooldowns and button_id in self.cooldowns[user_id]:
            last_used = self.cooldowns[user_id][button_id]
            time_since_last = time.time() - last_used
            if time_since_last < 60:  # Cooldown de 60 segundos
                remaining = int(60 - time_since_last)
                await interaction.response.send_message(embed=create_embed(
                    title="⏳ En Cooldown",
                    description=f"Por favor, espera {remaining} segundos antes de usar este botón nuevamente.",
                    color=Colors.WARNING
                ), ephemeral=True)
                return

        # Actualizar cooldown
        if user_id not in self.cooldowns:
            self.cooldowns[user_id] = {}
        self.cooldowns[user_id][button_id] = time.time()

        self.style = discord.ButtonStyle.grey
        self.label = "⌛ Procesando..."
        self.emoji = None
        try:
            await interaction.message.edit(view=self.view)
        except discord.errors.NotFound:
            print(f"⚠️ No se pudo editar el mensaje: canal no encontrado.")
            return
        except discord.errors.HTTPException as e:
            print(f"⚠️ Error HTTP al editar mensaje: {e}")
            return
        
        try:
            if self.custom_id == "ticket_claim":
                await handle_ticket_claim(interaction)
            elif self.custom_id == "ticket_close":
                await handle_ticket_close(interaction)
            elif self.custom_id == "ticket_add_user":
                await handle_ticket_add_user(interaction)
            elif self.custom_id == "start_server":
                await handle_server_start(interaction)
            elif self.custom_id == "start_vote":
                await handle_vote_start(interaction)
            elif self.custom_id == "close_server":
                await handle_server_close(interaction)
        except Exception as e:
            print(f"Error en botón {self.custom_id}: {e}")
            try:
                await interaction.followup.send(embed=create_embed(
                    title="❌ Error",
                    description="Ocurrió un error al procesar tu acción. Por favor, intenta de nuevo.",
                    color=Colors.DANGER
                ), ephemeral=True)
            except (discord.errors.NotFound, discord.errors.InteractionResponded) as followup_error:
                print(f"⚠️ No se pudo enviar mensaje de error: {followup_error}")
        finally:
            self.style = self.original_style
            self.label = self.original_label
            self.emoji = self.original_emoji
            try:
                await interaction.message.edit(view=self.view)
            except discord.errors.NotFound:
                print(f"⚠️ No se pudo restaurar el mensaje: canal no encontrado.")
            except discord.errors.HTTPException as e:
                print(f"⚠️ Error HTTP al restaurar mensaje: {e}")

class VoteStartModal(ui.Modal, title="🗳️ Iniciar Votación"):
    votes_required = ui.TextInput(
        label="Número de votos requeridos",
        placeholder="Ejemplo: 6",
        style=discord.TextStyle.short,
        required=True
    )
    
    authorized_by = ui.TextInput(
        label="Autorizado por (nombre sin @)",
        placeholder="Ejemplo: Nicolas",
        style=discord.TextStyle.short,
        required=True
    )
    
    authorized_by_id = ui.TextInput(
        label="ID de Discord de quien autorizó",
        placeholder="Ejemplo: 123456789012345678",
        style=discord.TextStyle.short,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class GeneralHelpModal(ui.Modal, title="🧩 Solicitud de Ayuda"):
    roblox_username = ui.TextInput(
        label="Tu nombre en Roblox",
        placeholder="Ejemplo: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    issue = ui.TextInput(
        label="Describe tu problema",
        style=discord.TextStyle.long,
        placeholder="Por favor, detalla tu problema para que podamos ayudarte...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class MunicipalityModal(ui.Modal, title="🏛️ Trámite Municipal"):
    roblox_username = ui.TextInput(
        label="Tu nombre en Roblox",
        placeholder="Ejemplo: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    procedure = ui.TextInput(
        label="¿Qué trámite necesitas?",
        style=discord.TextStyle.long,
        placeholder="Ejemplo: Licencia de conducir, registro de vehículo, propiedad...",
        required=True
    )
    
    details = ui.TextInput(
        label="Detalles adicionales",
        style=discord.TextStyle.long,
        placeholder="Proporciona cualquier información adicional relevante...",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class IllegalFactionModal(ui.Modal, title="🕵️ Creación de Facción Ilegal"):
    faction_name = ui.TextInput(
        label="Nombre de la Facción",
        placeholder="Ejemplo: Cartel del Noroeste",
        required=True
    )
    
    owners = ui.TextInput(
        label="Dueño(s) (Roblox)",
        placeholder="Ejemplo: Player1, Player2, Player3",
        style=discord.TextStyle.long,
        required=True
    )
    
    description = ui.TextInput(
        label="Descripción de la Facción",
        style=discord.TextStyle.long,
        placeholder="Describe los objetivos y actividades de tu facción...",
        required=True
    )
    
    discord_link = ui.TextInput(
        label="Link de Discord de la facción",
        placeholder="Ejemplo: https://discord.gg/abcdef",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class CloseTicketModal(ui.Modal, title="🔒 Cerrar Ticket"):
    reason = ui.TextInput(
        label="Razón del cierre",
        placeholder="Ejemplo: Problema resuelto, usuario inactivo...",
        style=discord.TextStyle.long,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class PurchasesModal(ui.Modal, title="🛍️ Ticket de Compras"):
    roblox_username = ui.TextInput(
        label="Tu nombre en Roblox",
        placeholder="Ejemplo: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    issue = ui.TextInput(
        label="Razón del ticket",
        style=discord.TextStyle.long,
        placeholder="Describe el problema con tu compra en detalle...",
        required=True
    )
    
    payment_proof = ui.TextInput(
        label="Link del comprobante de pago (opcional)",
        style=discord.TextStyle.short,
        placeholder="Ejemplo: https://imgur.com/abcdef",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class BenefitsModal(ui.Modal, title="🎁 Reclamo de Beneficios"):
    roblox_username = ui.TextInput(
        label="Tu nombre en Roblox",
        placeholder="Ejemplo: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    benefits = ui.TextInput(
        label="Beneficios a reclamar",
        style=discord.TextStyle.long,
        placeholder="Detalla los beneficios que deseas reclamar...",
        required=True
    )
    
    proof_link = ui.TextInput(
        label="Link de pruebas (opcional)",
        style=discord.TextStyle.short,
        placeholder="Ejemplo: https://imgur.com/abcdef",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class AlliancesModal(ui.Modal, title="🤝 Solicitud de Alianza"):
    server_name = ui.TextInput(
        label="Nombre del servidor",
        placeholder="Ejemplo: Los Santos RP",
        style=discord.TextStyle.short,
        required=True
    )
    
    owner_name = ui.TextInput(
        label="Nombre de Discord del dueño",
        placeholder="Ejemplo: Username#1234",
        style=discord.TextStyle.short,
        required=True
    )
    
    server_link = ui.TextInput(
        label="Link del servidor",
        placeholder="Ejemplo: https://discord.gg/abcdef",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class AppealsModal(ui.Modal, title="📜 Apelación"):
    roblox_username = ui.TextInput(
        label="Tu nombre en Roblox",
        placeholder="Ejemplo: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    appeal_type = ui.TextInput(
        label="Tipo de apelación",
        placeholder="Ejemplo: Sanción, Baneo, Advertencia",
        style=discord.TextStyle.short,
        required=True
    )
    
    appeal_reason = ui.TextInput(
        label="Razón de la apelación",
        style=discord.TextStyle.long,
        placeholder="Explica por qué deberías ser despenalizado...",
        required=True
    )
    
    proof_link = ui.TextInput(
        label="Link de pruebas (opcional)",
        style=discord.TextStyle.short,
        placeholder="Ejemplo: https://imgur.com/abcdef",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class ReportsModal(ui.Modal, title="⚠️ Reporte"):
    reported_name = ui.TextInput(
        label="Nombre de la persona a reportar",
        placeholder="Ejemplo: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    report_type = ui.TextInput(
        label="Tipo de reporte",
        placeholder="Ejemplo: Usuario, Staff",
        style=discord.TextStyle.short,
        required=True
    )
    
    report_reason = ui.TextInput(
        label="Razón del reporte",
        style=discord.TextStyle.long,
        placeholder="Describe detalladamente el problema encontrado...",
        required=True
    )
    
    proof_link = ui.TextInput(
        label="Link de pruebas (opcional)",
        style=discord.TextStyle.short,
        placeholder="Ejemplo: https://imgur.com/abcdef",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class RobberyClaimModal(ui.Modal, title="🚔 Reclamo de Robo"):
    roblox_username = ui.TextInput(
        label="Tu nombre en Roblox",
        placeholder="Ejemplo: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    involved_players = ui.TextInput(
        label="Nombres de personas involucradas",
        style=discord.TextStyle.long,
        placeholder="Lista los nombres de Roblox de todos los involucrados...",
        required=True
    )
    
    proof_link = ui.TextInput(
        label="Link de pruebas (opcional)",
        style=discord.TextStyle.short,
        placeholder="Ejemplo: https://imgur.com/abcdef",
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class BusinessCreationModal(ui.Modal, title="🏢 Creación de Empresa"):
    roblox_username = ui.TextInput(
        label="Nombre(s) de Roblox del/los dueño(s)",
        style=discord.TextStyle.long,
        placeholder="Ejemplo: SantiagoRP_Player, OtroJugador...",
        required=True
    )
    
    business_description = ui.TextInput(
        label="Descripción de la empresa",
        style=discord.TextStyle.long,
        placeholder="Describe el propósito y servicios de la empresa...",
        required=True
    )
    
    business_type = ui.TextInput(
        label="Tipo de empresa",
        placeholder="Ejemplo: Restaurante, Taller, Tienda...",
        style=discord.TextStyle.short,
        required=True
    )
    
    discord_link = ui.TextInput(
        label="Link de Discord de la empresa",
        placeholder="Ejemplo: https://discord.gg/abcdef",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class CKRequestModal(ui.Modal, title="💀 Solicitud de CK"):
    target_name = ui.TextInput(
        label="Nombre de la persona para CK",
        placeholder="Ejemplo: SantiagoRP_Player",
        style=discord.TextStyle.short,
        required=True
    )
    
    ck_reason = ui.TextInput(
        label="Razón del CK",
        style=discord.TextStyle.long,
        placeholder="Explica detalladamente por qué solicitas el CK...",
        required=True
    )
    
    proof_link = ui.TextInput(
        label="Link de pruebas",
        style=discord.TextStyle.short,
        placeholder="Ejemplo: https://imgur.com/abcdef",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class AddUserModal(ui.Modal, title="➕ Agregar Usuario al Ticket"):
    username = ui.TextInput(
        label="Nombre de usuario de Discord",
        placeholder="Ejemplo: Jrsmile22 (sin @)",
        style=discord.TextStyle.short,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

# =============================================
# VISTAS INTERACTIVAS
# =============================================
class ControlPanelView(ui.View):
    """Panel de control administrativo con botones interactivos."""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GradientButton(
            style=discord.ButtonStyle.success,
            label="Abrir Servidor",
            emoji="🚀",
            custom_id="start_server"
        ))
        self.add_item(GradientButton(
            style=discord.ButtonStyle.primary,
            label="Iniciar Votación",
            emoji="🗳️",
            custom_id="start_vote"
        ))
        self.add_item(GradientButton(
            style=discord.ButtonStyle.red,
            label="Cerrar Servidor",
            emoji="🔒",
            custom_id="close_server"
        ))

class TicketActionsView(ui.View):
    """Acciones para tickets con validación de roles."""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GradientButton(
            style=discord.ButtonStyle.green,
            label="Atender Ticket",
            emoji="🛎️",
            custom_id="ticket_claim"
        ))
        self.add_item(GradientButton(
            style=discord.ButtonStyle.red,
            label="Cerrar Ticket",
            emoji="🔒",
            custom_id="ticket_close"
        ))
        self.add_item(GradientButton(
            style=discord.ButtonStyle.blurple,
            label="Añadir Usuario",
            emoji="➕",
            custom_id="ticket_add_user"
        ))
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verificar que el usuario tenga permisos de staff."""
        if not any(role.id in Roles.STAFF for role in interaction.user.roles):
            await interaction.response.send_message(embed=create_embed(
                title="❌ Acceso Denegado",
                description="No tienes permisos para realizar esta acción.",
                color=Colors.DANGER
            ), ephemeral=True)
            return False
        return True

class SupportButton(ui.Button):
    """Botón que dirige al canal de soporte o reglas."""
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.blurple,
            label="📚 Ver Reglas",
            emoji="📜",
            custom_id="support_button"
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=create_embed(
            title="📚 Reglas del Servidor",
            description=(
                "Por favor, lee las reglas del servidor en el canal correspondiente antes de abrir un ticket.\n"
                "Abrir tickets sin motivo válido resultará en **sanciones**.\n"
                "Si necesitas ayuda, visita nuestro canal de soporte o consulta las reglas en <#1339386615688335397>."
            ),
            color=Colors.INFO
        ), ephemeral=True)

class TicketCreationView(ui.View):
    """Sistema de tickets interactivo con menú desplegable y botón de soporte."""
    def __init__(self):
        super().__init__(timeout=None)
        options = [
            discord.SelectOption(
                label=f"{data['emoji']} {data['title']}",
                value=ticket_type,
                description=data["description"][:100],
                emoji=data["emoji"]
            )
            for ticket_type, data in TICKET_CATEGORIES.items()
        ]
        
        self.select = ui.Select(
            placeholder="🎟️ Elige el tipo de ticket que necesitas...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_select"
        )
        self.select.callback = self.on_select
        self.add_item(self.select)
        self.add_item(SupportButton())
    
    async def on_select(self, interaction: discord.Interaction):
        """Manejar selección de categoría de ticket."""
        category = self.select.values[0]
        modal_classes = {
            "general_help": GeneralHelpModal,
            "municipality": MunicipalityModal,
            "illegal_faction": IllegalFactionModal,
            "purchases": PurchasesModal,
            "benefits": BenefitsModal,
            "alliances": AlliancesModal,
            "doubts": GeneralHelpModal,
            "appeals": AppealsModal,
            "reports": ReportsModal,
            "robbery_claim": RobberyClaimModal,
            "business_creation": BusinessCreationModal,
            "ck_request": CKRequestModal
        }
        
        modal_class = modal_classes.get(category, GeneralHelpModal)
        modal = modal_class(title=f"{TICKET_CATEGORIES[category]['emoji']} {TICKET_CATEGORIES[category]['title']}")
        
        await interaction.response.send_modal(modal)
        
        timed_out = await modal.wait()
        if timed_out:
            return await interaction.followup.send(embed=create_embed(
                title="⌛ Tiempo Agotado",
                description="El tiempo para completar el formulario ha expirado. Por favor, intenta nuevamente.",
                color=Colors.WARNING
            ), ephemeral=True)
        
        data = {child.label: child.value for child in modal.children if isinstance(child, ui.TextInput)}
        await create_ticket_channel(interaction=modal.interaction, category=category, data=data)

# =============================================
# FUNCIONES PRINCIPALES
# =============================================
async def create_ticket_channel(interaction: discord.Interaction, category: str, data: dict):
    """Crear un canal de ticket profesional."""
    try:
        category_info = TICKET_CATEGORIES.get(category, {})
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        for role_id in Roles.STAFF:
            role = interaction.guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_messages=True
                )
        
        ticket_num = len([c for c in interaction.guild.get_channel(category_info["id"]).channels 
                         if c.name.startswith(f"{category}-")]) + 1
        channel_name = f"{category}-{ticket_num:03d}-{interaction.user.name}"[:100]
        
        ticket_channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=discord.Object(id=category_info["id"]),
            overwrites=overwrites
        )
        
        embed = create_embed(
            title=f"{category_info['emoji']} Ticket: {category_info['title']}",
            description=f"**Usuario:** {interaction.user.mention}\n**Categoría:** {category_info['title']}\n\nPor favor, espera la atención de nuestro equipo.",
            color=category_info["color"],
            user=interaction.user
        )
        
        for field, value in data.items():
            embed.add_field(name=field, value=value or "No especificado", inline=False)
        
        view = TicketActionsView()
        message = await ticket_channel.send(
            content=f"🎟️ {interaction.user.mention} | ¡Gracias por crear un ticket!",
            embed=embed,
            view=view
        )
        await message.pin()
        
        confirm_embed = create_embed(
            title="✅ Ticket Creado",
            description=(
                f"Tu ticket ha sido creado en {ticket_channel.mention}. Un miembro del staff lo atenderá pronto.\n\n"
                "**⚠️ Advertencia:** Abrir tickets sin motivo válido resultará en **sanciones**. Asegúrate de proporcionar información clara y relevante."
            ),
            color=Colors.SUCCESS,
            user=interaction.user
        )
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)
        
        log_channel = bot.get_channel(Channels.TICKET_LOGS)
        if log_channel:
            log_embed = create_embed(
                title=f"{category_info['emoji']} Nuevo Ticket",
                description=f"**Tipo:** {category_info['title']}\n**Usuario:** {interaction.user.mention}\n**Canal:** {ticket_channel.mention}",
                color=category_info["color"]
            )
            await log_channel.send(embed=log_embed)
        
    except Exception as e:
        print(f"Error al crear ticket: {e}")
        await interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="No pudimos crear tu ticket. Por favor, intenta de nuevo o contacta a un administrador.",
            color=Colors.DANGER
        ), ephemeral=True)

async def handle_ticket_claim(interaction: discord.Interaction):
    """Manejar reclamación de ticket por parte del staff."""
    if not any(role.id in Roles.STAFF for role in interaction.user.roles):
        return await interaction.response.send_message(embed=create_embed(
            title="❌ Acceso Denegado",
            description="Solo el staff puede atender tickets.",
            color=Colors.DANGER
        ), ephemeral=True)
    
    embed = interaction.message.embeds[0]
    for field in embed.fields:
        if field.name == "🛎️ Atendido por":
            return await interaction.response.send_message(embed=create_embed(
                title="❌ Ticket Ya Atendido",
                description="Este ticket ya ha sido reclamado por otro miembro del staff.",
                color=Colors.DANGER
            ), ephemeral=True)
    
    embed.add_field(name="🛎️ Atendido por", value=interaction.user.mention, inline=False)
    
    new_view = TicketActionsView()
    for child in new_view.children:
        if child.custom_id == "ticket_claim":
            child.disabled = True
            child.label = "Atendido"
            child.style = discord.ButtonStyle.grey
    
    await interaction.response.send_message(embed=create_embed(
        title="✅ Ticket Atendido",
        description="Has reclamado este ticket con éxito.",
        color=Colors.SUCCESS
    ), ephemeral=True)
    
    await interaction.message.edit(embed=embed, view=new_view)
    
    attention_embed = create_embed(
        title="🛎️ Ticket en Atención",
        description=f"¡Tu ticket está siendo atendido por {interaction.user.mention}!\nPor favor, ten paciencia mientras revisamos tu caso.",
        color=Colors.SUCCESS,
        user=interaction.user
    )
    await interaction.channel.send(embed=attention_embed)

async def handle_ticket_close(interaction: discord.Interaction):
    """Manejar cierre de ticket con confirmación."""
    modal = CloseTicketModal()
    await interaction.response.send_modal(modal)
    
    timed_out = await modal.wait()
    if timed_out:
        return
    
    view = TicketActionsView()
    for child in view.children:
        child.disabled = True
    try:
        await interaction.message.edit(view=view)
    except discord.errors.NotFound:
        print(f"⚠️ No se pudo editar el mensaje al cerrar ticket: canal no encontrado.")
        return
    
    closing_embed = create_embed(
        title="🔒 Cerrando Ticket",
        description=f"Este ticket se cerrará en 5 segundos.\n**Razón:** {modal.reason.value}",
        color=Colors.DANGER
    )
    await modal.interaction.followup.send(embed=closing_embed)
    
    log_channel = bot.get_channel(Channels.TICKET_LOGS)
    if log_channel:
        log_embed = create_embed(
            title="📌 Ticket Cerrado",
            description=f"**Canal:** {interaction.channel.name}\n**Cerrado por:** {interaction.user.mention}\n**Razón:** {modal.reason.value}",
            color=Colors.DANGER,
            user=interaction.user
        )
        await log_channel.send(embed=log_embed)
    
    await asyncio.sleep(5)
    try:
        await interaction.channel.delete(reason=f"Cerrado por {interaction.user}. Razón: {modal.reason.value}")
    except discord.errors.NotFound:
        print(f"⚠️ No se pudo eliminar el canal: ya no existe.")
    except Exception as e:
        print(f"Error al eliminar canal: {e}")
        await modal.interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="No se pudo cerrar el canal. Por favor, ciérralo manualmente.",
            color=Colors.DANGER
        ), ephemeral=True)

async def handle_ticket_add_user(interaction: discord.Interaction):
    """Manejar agregar usuario a ticket."""
    modal = AddUserModal()
    await interaction.response.send_modal(modal)
    
    timed_out = await modal.wait()
    if timed_out:
        return
    
    username = modal.username.value
    member = None
    
    for guild_member in interaction.guild.members:
        if guild_member.name.lower() == username.lower():
            member = guild_member
            break
    
    if not member:
        return await modal.interaction.followup.send(embed=create_embed(
            title="❌ Usuario no Encontrado",
            description=f"No se encontró al usuario '{username}' en el servidor.",
            color=Colors.DANGER
        ), ephemeral=True)
    
    try:
        await interaction.channel.set_permissions(
            member,
            read_messages=True,
            send_messages=True,
            view_channel=True
        )
    except discord.errors.NotFound:
        print(f"⚠️ No se pudo modificar permisos: canal no encontrado.")
        await modal.interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="El canal ya no existe. No se pudo agregar al usuario.",
            color=Colors.DANGER
        ), ephemeral=True)
        return
    
    await modal.interaction.followup.send(embed=create_embed(
        title="✅ Usuario Agregado",
        description=f"Se ha agregado a {member.mention} al ticket.",
        color=Colors.SUCCESS
    ), ephemeral=True)
    
    ticket_embed = create_embed(
        title="➕ Usuario Agregado",
        description=f"{member.mention} ha sido agregado al ticket por {interaction.user.mention}.",
        color=Colors.SUCCESS
    )
    try:
        await interaction.channel.send(embed=ticket_embed)
    except discord.errors.NotFound:
        print(f"⚠️ No se pudo enviar mensaje: canal no encontrado.")

async def handle_server_start(interaction: discord.Interaction):
    """Manejar inicio del servidor."""
    global server_status
    
    if not any(role.id in Roles.STAFF for role in interaction.user.roles):
        return await interaction.response.send_message(embed=create_embed(
            title="❌ Acceso Denegado",
            description="No tienes permisos para abrir el servidor.",
            color=Colors.DANGER
        ), ephemeral=True)
    
    server_status = "abierto"
    
    embed = create_embed(
        title="🚀 ¡Santiago RP Abierto! 🎉",
        description=(
            "🎮 **¡El servidor está listo para la acción!** 🎉\n"
            "¡Únete ahora y vive la experiencia de rol más intensa en Santiago RP! 🚨\n\n"
            "**📢 Cómo Unirte:**\n"
            "🔸 **Lista de servidores**: Busca 'S SANTIAGO RP | ESTRICTO | SPANISH' en ERLC.\n"
            "🔸 **Código de servidor**: Usa **STRPP** en ajustes.\n"
            "🔸 **Enlace directo (PC)**: [Unirse ahora](https://policeroleplay.community/join?code=STRPP)\n\n"
            "🙌 ¡Nos vemos en el servidor!"
        ),
        color=Colors.SUCCESS,
        user=interaction.user
    )
    embed.set_image(url="https://media.discordapp.net/attachments/1340184960379781191/1363350692651335903/RobloxScreenShot20250416_193740099_1.jpg")
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
    embed.set_footer(text="Santiago RP | ¡La aventura comienza! | Creado por Smile")
    
    channel = bot.get_channel(Channels.ANNOUNCEMENTS)
    try:
        await channel.purge(limit=3)  # Reducido de 5 a 3
        message = await channel.send(embed=embed)
        
        # Enviar dos mensajes de mención con @everyone
        mention1 = await channel.send("@everyone")
        mention2 = await channel.send("@everyone")
        
        # Programar eliminación de los mensajes de mención después de 30 segundos
        await asyncio.sleep(30)
        await mention1.delete()
        await mention2.delete()
        
        print(f"✅ Anuncio enviado al canal {Channels.ANNOUNCEMENTS}")
    except discord.errors.Forbidden:
        print(f"❌ Error: El bot no tiene permisos para gestionar el canal {Channels.ANNOUNCEMENTS} o enviar mensajes")
        await interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="No se pudo enviar el anuncio. Verifica los permisos del bot.",
            color=Colors.DANGER
        ), ephemeral=True)
        return
    except discord.errors.NotFound:
        print(f"❌ Error: No se encontró el canal con ID {Channels.ANNOUNCEMENTS}")
        await interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="No se encontró el canal de anuncios. Contacta a un administrador.",
            color=Colors.DANGER
        ), ephemeral=True)
        return
    except Exception as e:
        print(f"❌ Error al enviar anuncio: {e}")
        await interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="Ocurrió un error al procesar la acción. Por favor, intenta de nuevo.",
            color=Colors.DANGER
        ), ephemeral=True)
        return
    
    await interaction.response.send_message(embed=create_embed(
        title="✅ Éxito",
        description="El servidor ha sido abierto correctamente.",
        color=Colors.SUCCESS
    ), ephemeral=True)

async def handle_server_close(interaction: discord.Interaction):
    """Manejar cierre del servidor con modal para razón."""
    global server_status
    
    if not any(role.id in Roles.STAFF for role in interaction.user.roles):
        return await interaction.response.send_message(embed=create_embed(
            title="❌ Acceso Denegado",
            description="No tienes permisos para cerrar el servidor.",
            color=Colors.DANGER
        ), ephemeral=True)
    
    # Mostrar modal para la razón del cierre
    modal = CloseServerModal()
    await interaction.response.send_modal(modal)
    
    timed_out = await modal.wait()
    if timed_out:
        return
    
    server_status = "cerrado"
    reason = modal.reason.value
    
    # Crear embed moderno y atractivo
    embed = create_embed(
        title="🔒 ¡Santiago RP Cerrado! 😔",
        description=(
            "🎮 **El servidor ha sido cerrado temporalmente.**\n"
            "No te preocupes, ¡volveremos pronto con más acción y rol! 🚨\n\n"
            "**📢 Información Importante:**\n"
            f"🔸 **Razón del cierre:** {reason}\n"
            "🔸 El servidor ya no está disponible para unirse.\n"
            "🔸 Mantente atento a este canal para la próxima apertura.\n"
            "🔸 Únete a nuestro Discord para actualizaciones: **[Santiago RP](https://discord.gg/santiagorp)**\n\n"
            "🙌 ¡Gracias por ser parte de nuestra comunidad!"
        ),
        color=Colors.DANGER,
        user=interaction.user
    )
    embed.set_image(url="https://media.discordapp.net/attachments/1340184960379781191/1364072022837170247/RobloxScreenShot20250413_175238971.jpg")
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
    embed.set_footer(text="Santiago RP | ¡Volveremos pronto! | Creado por Smile")
    
    channel = bot.get_channel(Channels.ANNOUNCEMENTS)
    try:
        await channel.purge(limit=3)  # Reducido de 5 a 3
        message = await channel.send(embed=embed)
        await message.add_reaction("😔")  # Añadir reacción para interacción
        
        # Enviar dos mensajes de mención con @everyone
        mention1 = await channel.send("@everyone")
        mention2 = await channel.send("@everyone")
        
        # Programar eliminación de los mensajes de mención después de 30 segundos
        await asyncio.sleep(30)
        await mention1.delete()
        await mention2.delete()
        
        print(f"✅ Anuncio enviado al canal {Channels.ANNOUNCEMENTS}")
    except discord.errors.Forbidden:
        print(f"❌ Error: El bot no tiene permisos para gestionar el canal {Channels.ANNOUNCEMENTS} o enviar mensajes")
        await modal.interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="No se pudo enviar el anuncio. Verifica los permisos del bot.",
            color=Colors.DANGER
        ), ephemeral=True)
        return
    except discord.errors.NotFound:
        print(f"❌ Error: No se encontró el canal con ID {Channels.ANNOUNCEMENTS}")
        await modal.interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="No se encontró el canal de anuncios. Contacta a un administrador.",
            color=Colors.DANGER
        ), ephemeral=True)
        return
    except Exception as e:
        print(f"❌ Error al enviar anuncio: {e}")
        await modal.interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="Ocurrió un error al procesar la acción. Por favor, intenta de nuevo.",
            color=Colors.DANGER
        ), ephemeral=True)
        return
    
    await modal.interaction.followup.send(embed=create_embed(
        title="✅ Éxito",
        description=f"El servidor ha sido cerrado correctamente.\n**Razón:** {reason}",
        color=Colors.SUCCESS
    ), ephemeral=True)

async def handle_vote_start(interaction: discord.Interaction):
    """Manejar inicio de votación para abrir el servidor."""
    global server_status
    
    if not any(role.id in Roles.STAFF for role in interaction.user.roles):
        return await interaction.response.send_message(embed=create_embed(
            title="❌ Acceso Denegado",
            description="No tienes permisos para iniciar una votación.",
            color=Colors.DANGER
        ), ephemeral=True)
    
    modal = VoteStartModal()
    await interaction.response.send_modal(modal)
    
    timed_out = await modal.wait()
    if timed_out:
        return
    
    server_status = "votacion"
    
    authorized_user = None
    authorized_mention = f"@{modal.authorized_by.value}"
    
    if modal.authorized_by_id.value:
        try:
            authorized_user = await interaction.guild.fetch_member(int(modal.authorized_by_id.value))
            if authorized_user:
                authorized_mention = authorized_user.mention
        except:
            pass
    
    if not authorized_user:
        for member in interaction.guild.members:
            if member.name.lower() == modal.authorized_by.value.lower():
                authorized_user = member
                authorized_mention = member.mention
                break
    
    embed = create_embed(
        title="🗳️ ¡Encuesta Iniciada! 📢",
        description=(
            "🎮 **¡Es hora de decidir!** 🗳️\n"
            "Hemos iniciado una encuesta para votar la apertura del servidor Santiago RP.\n\n"
            "**📜 Reglas para Votar:**\n"
            "🔸 Comprométete a participar activamente en el rol.\n"
            "🔸 Evita el antirol y cumple las normativas.\n"
            "🔸 No participes en facciones sin rol correspondiente.\n"
            f"🔸 **Votos requeridos:** {modal.votes_required.value}\n\n"
            "👍 **Vota a favor** | 👎 **Vota en contra**"
        ),
        color=Colors.WARNING,
        user=interaction.user
    )
    embed.set_image(url="https://media.discordapp.net/attachments/1360714101327663135/1360762037495529672/Screenshot_20250412_194212_CapCut.jpg")
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
    embed.add_field(name="Autorizado por", value=authorized_mention, inline=True)
    embed.set_footer(text="Santiago RP | ¡Tu voto cuenta! | Creado por Smile")
    
    channel = bot.get_channel(Channels.ANNOUNCEMENTS)
    try:
        await channel.purge(limit=3)  # Reducido de 5 a 3
        message = await channel.send(embed=embed)
        await message.add_reaction("👍")
        await message.add_reaction("👎")
        
        # Enviar dos mensajes de mención con @everyone
        mention1 = await channel.send("@everyone")
        mention2 = await channel.send("@everyone")
        
        # Programar eliminación de los mensajes de mención después de 30 segundos
        await asyncio.sleep(30)
        await mention1.delete()
        await mention2.delete()
        
        print(f"✅ Anuncio enviado al canal {Channels.ANNOUNCEMENTS}")
    except discord.errors.Forbidden:
        print(f"❌ Error: El bot no tiene permisos para gestionar el canal {Channels.ANNOUNCEMENTS} o enviar mensajes")
        await modal.interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="No se pudo enviar el anuncio. Verifica los permisos del bot.",
            color=Colors.DANGER
        ), ephemeral=True)
        return
    except discord.errors.NotFound:
        print(f"❌ Error: No se encontró el canal con ID {Channels.ANNOUNCEMENTS}")
        await modal.interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="No se encontró el canal de anuncios. Contacta a un administrador.",
            color=Colors.DANGER
        ), ephemeral=True)
        return
    except Exception as e:
        print(f"❌ Error al enviar anuncio: {e}")
        await modal.interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="Ocurrió un error al procesar la acción. Por favor, intenta de nuevo.",
            color=Colors.DANGER
        ), ephemeral=True)
        return
    
    await modal.interaction.followup.send(embed=create_embed(
        title="✅ Éxito",
        description="La votación ha sido iniciada correctamente.",
        color=Colors.SUCCESS
    ), ephemeral=True)

def is_ratings_channel():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.channel_id != Channels.RATINGS:
            await interaction.response.send_message(embed=create_embed(
                title="❌ Canal Incorrecto",
                description=f"Este comando solo puede usarse en <#{Channels.RATINGS}>.",
                color=Colors.DANGER
            ), ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

# =============================================
# COMANDOS Y EVENTOS
# =============================================

# =============================
# FLUJO DE VERIFICACIÓN POR DM
# =============================

# Start the verification questionnaire
async def iniciar_cuestionario_verificacion(interaction: discord.Interaction, bot):
    preguntas = [
        "🎮 ¿Cuál es tu nombre de usuario de Roblox?",
        "🔍 ¿Qué buscas en el server?",
        "⚔️ ¿Cuál es la diferencia entre MG2 y MG?",
        "💥 ¿Qué es RK?",
        "🗡️ ¿Qué es CK?",
        "📜 ¿Qué es OCC y IC?",
        "🛡️ ¿Qué es ZZ?",
        "🌐 ¿Cómo conociste el servidor?",
        "⭐ ¿Del 1/10 qué tan bien crees que roleas?",
        "🎭 ¿Sabes de rol?",
        "📖 ¿Sabes las normas del servidor y del rol?"
    ]
    respuestas = []

    # Guardar el guild desde la interacción inicial
    guild = interaction.guild

    # Confirmation step
    confirm_embed = discord.Embed(
        title="🌟 ¡Bienvenido a la Verificación de SantiagoRP! 🌟",
        description=(
            "Estás a punto de comenzar el cuestionario de verificación. "
            "Asegúrate de tener tus DMs abiertos y responde con seriedad.\n\n"
            "📋 **Preguntas**: 11\n"
            "⏳ **Tiempo por pregunta**: 3 minutos\n"
            "✅ Presiona el botón para empezar."
        ),
        color=Colors.PRIMARY,
        timestamp=datetime.now()
    )
    confirm_embed.set_footer(text="Santiago RP | Verificación")
    confirm_embed.set_thumbnail(url=guild.icon.url if guild and guild.icon else None)

    view = ui.View()
    confirm_button = ui.Button(label="Iniciar Verificación", style=discord.ButtonStyle.primary, emoji="🚀")
    
    async def confirm_callback(interaction_btn: discord.Interaction):
        if interaction_btn.user.id != interaction.user.id:
            await interaction_btn.response.send_message("❌ Solo el usuario que inició puede confirmar.", ephemeral=True)
            return
        await interaction_btn.response.send_message("✅ ¡Cuestionario iniciado! Revisa tus DMs.", ephemeral=True)
        await start_questionnaire(interaction_btn, guild)  # Pasar el guild
    
    confirm_button.callback = confirm_callback
    view.add_item(confirm_button)

    try:
        await interaction.user.send(embed=confirm_embed, view=view)
        await interaction.response.send_message("📩 Te he enviado un mensaje privado para iniciar la verificación. ¡Revisa tus DMs!", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("🚫 No puedo enviarte mensajes privados. Habilita tus DMs y vuelve a intentarlo.", ephemeral=True)
        return

    async def start_questionnaire(interaction_btn, guild):  # Añadir guild como parámetro
        welcome_embed = discord.Embed(
            title="🎉 ¡Cuestionario de Verificación Iniciado! 🎉",
            description=(
                "Responde cada pregunta con claridad y seriedad. "
                "Tienes **3 minutos** por pregunta. ¡Buena suerte! 🍀"
            ),
            color=Colors.PRIMARY
        )
        welcome_embed.set_footer(text="Santiago RP | Verificación")
        welcome_embed.set_thumbnail(url=guild.icon.url if guild and guild.icon else None)  # Usar el guild pasado

        await interaction_btn.user.send(embed=welcome_embed)

        def check(m):
            return m.author.id == interaction_btn.user.id and isinstance(m.channel, discord.DMChannel)

        for i, pregunta in enumerate(preguntas, 1):
            question_embed = discord.Embed(
                title=f"Pregunta {i}/{len(preguntas)}",
                description=pregunta,
                color=Colors.PRIMARY
            )
            question_embed.set_footer(text="Tiempo restante: 3 minutos")
            question_embed.set_thumbnail(url=guild.icon.url if guild and guild.icon else None)
            await interaction_btn.user.send(embed=question_embed)
            try:
                mensaje = await bot.wait_for('message', check=check, timeout=180)
                respuestas.append(mensaje.content)
            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    title="⏰ ¡Tiempo Agotado!",
                    description="No respondiste a tiempo. Usa el botón de verificación para intentarlo de nuevo.",
                    color=Colors.WARNING
                )
                await interaction_btn.user.send(embed=timeout_embed)
                return

        # Create the staff embed with responses
        embed = discord.Embed(
            title="📝 Nueva Solicitud de Verificación",
            description=f"**Usuario:** {interaction_btn.user.mention} ({interaction_btn.user.id})\n"
                        f"**Nombre en Roblox:** {respuestas[0]}",
            color=Colors.PRIMARY,
            timestamp=datetime.now()
        )
        for i, pregunta in enumerate(preguntas):
            embed.add_field(name=pregunta, value=respuestas[i] or "Sin respuesta", inline=False)
        embed.set_footer(text="Santiago RP | Sistema de Verificación")
        embed.set_thumbnail(url=guild.icon.url if guild and guild.icon else None)
        embed.set_author(name="SantiagoRP Verificación", icon_url=guild.icon.url if guild and guild.icon else None)

        # Attach the staff verification view
        view = VerificacionStaffView(interaction_btn.user, respuestas[0])
        
        canal_staff = guild.get_channel(1356740696798924951)
        if canal_staff:
            await canal_staff.send(embed=embed, view=view)
        else:
            await interaction_btn.user.send("⚠️ Error: No se encontró el canal de staff. Contacta a un administrador.")
            return

        completion_embed = discord.Embed(
            title="✅ ¡Solicitud Enviada!",
            description="Tu solicitud de verificación ha sido enviada al staff. "
                        "Recibirás una respuesta por DM en **24-48 horas**. ¡Gracias por tu paciencia!",
            color=Colors.SUCCESS
        )
        completion_embed.set_footer(text="Santiago RP | Verificación")
        await interaction_btn.user.send(embed=completion_embed)

        def check(m):
            return m.author.id == interaction_btn.user.id and isinstance(m.channel, discord.DMChannel)

        for i, pregunta in enumerate(preguntas, 1):
            question_embed = discord.Embed(
                title=f"Pregunta {i}/{len(preguntas)}",
                description=pregunta,
                color=Colors.PRIMARY
            )
            question_embed.set_footer(text="Tiempo restante: 3 minutos")
            await interaction_btn.user.send(embed=question_embed)
            try:
                mensaje = await bot.wait_for('message', check=check, timeout=180)
                respuestas.append(mensaje.content)
            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    title="⏰ ¡Tiempo Agotado!",
                    description="No respondiste a tiempo. Usa el botón de verificación para intentarlo de nuevo.",
                    color=Colors.WARNING
                )
                await interaction_btn.user.send(embed=timeout_embed)
                return

        # Create the staff embed with responses
        embed = discord.Embed(
            title="📝 Nueva Solicitud de Verificación",
            description=f"**Usuario:** {interaction_btn.user.mention} ({interaction_btn.user.id})\n"
                        f"**Nombre en Roblox:** {respuestas[0]}",
            color=Colors.PRIMARY,
            timestamp=datetime.now()
        )
        for i, pregunta in enumerate(preguntas):
            embed.add_field(name=pregunta, value=respuestas[i] or "Sin respuesta", inline=False)
        embed.set_footer(text="Santiago RP | Sistema de Verificación")
        embed.set_thumbnail(url=interaction_btn.guild.icon.url if interaction_btn.guild.icon else None)
        embed.set_author(name="SantiagoRP Verificación", icon_url=interaction_btn.guild.icon.url if interaction_btn.guild.icon else None)

        # Attach the staff verification view
        view = VerificacionStaffView(interaction_btn.user, respuestas[0])
        
        canal_staff = interaction_btn.guild.get_channel(1356740696798924951)
        if canal_staff:
            await canal_staff.send(embed=embed, view=view)  # Ensure the view is sent with the embed
        else:
            await interaction_btn.user.send("⚠️ Error: No se encontró el canal de staff. Contacta a un administrador.")
            return

        completion_embed = discord.Embed(
            title="✅ ¡Solicitud Enviada!",
            description="Tu solicitud de verificación ha sido enviada al staff. "
                        "Recibirás una respuesta por DM en **24-48 horas**. ¡Gracias por tu paciencia!",
            color=Colors.SUCCESS
        )
        completion_embed.set_footer(text="Santiago RP | Verificación")
        await interaction_btn.user.send(embed=completion_embed)

# Staff verification view with Accept/Deny buttons
class VerificacionStaffView(ui.View):
    def __init__(self, usuario, roblox_name):
        super().__init__(timeout=None)
        self.usuario = usuario
        self.roblox_name = roblox_name

    @ui.button(label="Aceptar", style=discord.ButtonStyle.success, emoji="✅")
    async def aceptar(self, interaction: discord.Interaction, button: ui.Button):
        if not any(role.id in Roles.STAFF for role in interaction.user.roles):
            await interaction.response.send_message("❌ Solo el staff puede usar este botón.", ephemeral=True)
            return
        modal = RazonStaffModal(self.usuario, self.roblox_name, True)
        await interaction.response.send_modal(modal)

    @ui.button(label="Denegar", style=discord.ButtonStyle.danger, emoji="❌")
    async def denegar(self, interaction: discord.Interaction, button: ui.Button):
        if not any(role.id in Roles.STAFF for role in interaction.user.roles):
            await interaction.response.send_message("❌ Solo el staff puede usar este botón.", ephemeral=True)
            return
        modal = RazonStaffModal(self.usuario, self.roblox_name, False)
        await interaction.response.send_modal(modal)

# Modal for staff to provide reason
class RazonStaffModal(ui.Modal, title="Motivo de la Decisión"):
    razon = ui.TextInput(label="Motivo", required=True, style=discord.TextStyle.long)

    def __init__(self, usuario, roblox_name, aceptar):
        super().__init__()
        self.usuario = usuario
        self.roblox_name = roblox_name
        self.aceptar = aceptar

    async def on_submit(self, interaction: discord.Interaction):
        try:
            miembro = await interaction.guild.fetch_member(self.usuario.id)
        except Exception:
            await interaction.response.send_message("🚫 No se pudo encontrar al usuario.", ephemeral=True)
            return

        if self.aceptar:
            # Add roles
            roles_a_agregar = [
                1339386615189209153, 1339386615189209150, 1339386615176630297,
                1360333071571878231, 1339386615159722121, 1339386615159722120
            ]
            for role_id in roles_a_agregar:
                rol = interaction.guild.get_role(role_id)
                if rol:
                    await miembro.add_roles(rol)
            # Remove unverified role
            rol_noverificado = interaction.guild.get_role(1339386615159722119)
            if rol_noverificado:
                await miembro.remove_roles(rol_noverificado)
            # Change nickname
            try:
                await miembro.edit(nick=f"{miembro.display_name} ({self.roblox_name})")
            except Exception:
                pass
            # Send DM
            try:
                await miembro.send(
                    embed=discord.Embed(
                        title="✅ ¡Verificación Aceptada!",
                        description=f"¡Felicidades! Has sido verificado para rolear en SantiagoRP.\n\n**Motivo del staff:** {self.razon.value}",
                        color=Colors.SUCCESS,
                        timestamp=datetime.now()
                    ).set_footer(text="Santiago RP | Verificación")
                )
            except Exception:
                pass
            await interaction.response.send_message("✅ Usuario verificado y notificado por DM.", ephemeral=True)
        else:
            # Denied
            try:
                await self.usuario.send(
                    embed=discord.Embed(
                        title="❌ Verificación Denegada",
                        description=f"Tu verificación fue denegada por el staff.\n\n**Motivo:** {self.razon.value}",
                        color=Colors.DANGER,
                        timestamp=datetime.now()
                    ).set_footer(text="Santiago RP | Verificación")
                )
            except Exception:
                pass
            await interaction.response.send_message("❌ Usuario notificado de la denegación por DM.", ephemeral=True)

# Command to send verification panel
@bot.tree.command(name="panel-verificacion", description="Enviar panel de verificación (solo staff).")
async def panel_verificacion(interaction: discord.Interaction):
    if interaction.channel_id != 1339386615688335395:
        await interaction.response.send_message("❌ Solo puedes usar este comando en el canal de verificación.", ephemeral=True)
        return
    if not any(role.id in Roles.STAFF for role in interaction.user.roles):
        await interaction.response.send_message("❌ Solo el staff puede usar este comando.", ephemeral=True)
        return

    descripcion_panel = (
        "🌟 **¡Bienvenido al Sistema de Verificación de SantiagoRP!** 🌟\n\n"
        "Para unirte a nuestra comunidad de rol serio, completa el cuestionario de verificación. "
        "Responde con **honestidad y detalle** siguiendo las normativas del servidor.\n\n"
        "⏰ **Tiempo de respuesta**: 24-48 horas\n"
        "⚠️ **Advertencia**: El mal uso del sistema o respuestas inadecuadas pueden resultar en un **baneo** o suspensión.\n\n"
        "¡Demuestra tu compromiso y comienza tu aventura en SantiagoRP! 🚀"
    )
    embed = discord.Embed(
        title="🎮 Panel de Verificación",
        description=descripcion_panel,
        color=Colors.PRIMARY,
        timestamp=datetime.now()
    )
    embed.set_footer(text="Santiago RP | Sistema de Verificación")
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.set_author(name="SantiagoRP", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

    view = ui.View()
    view.add_item(ui.Button(label="Verificarme", style=discord.ButtonStyle.primary, custom_id="verificarme_btn", emoji="✅"))

    async def verificarme_callback(interaction_btn: discord.Interaction):
        await iniciar_cuestionario_verificacion(interaction_btn, bot)

    view.children[0].callback = verificarme_callback

    await interaction.response.send_message(embed=embed, view=view)
    
@bot.tree.command(name="advertir-a", description="Advertir a un usuario sobre posibles sanciones.")
@app_commands.describe(
    usuario="Usuario a advertir",
    razon="Razón de la advertencia",
    prueba="URL de la prueba (opcional)"
)
async def advertir_a(interaction: discord.Interaction, usuario: discord.Member, razon: str, prueba: str = None):
    """Comando para advertir a un usuario sobre posibles sanciones."""
    # Verificar canal
    if interaction.channel_id != 1358216083953291467:
        await interaction.response.send_message(
            "❌ Este comando solo puede usarse en el canal autorizado.", ephemeral=True
        )
        return

    # Verificar roles de staff
    staff_roles = set(Roles.STAFF)
    user_roles = set([role.id for role in interaction.user.roles])
    if not staff_roles.intersection(user_roles):
        await interaction.response.send_message(
            "❌ Solo el staff puede usar este comando.", ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)
    admin = interaction.user

    # Crear embed llamativo para el usuario advertido
    advertencia_embed = discord.Embed(
        title="⚠️ ¡Advertencia emitida!",
        description=(
            f"**👤 Usuario advertido:** {usuario.mention} ({usuario.id})\n"
            f"**🛡️ Staff:** {admin.mention} ({admin.id})\n"
            f"**📄 Razón:** {razon}\n"
            f"{f'**📎 Prueba:** {prueba}\n' if prueba else ''}"
            "\n\n🔔 **Recuerda:** Puedes recibir una sanción de los grados existentes (**Advertencia 1, 2, 3**), aislamiento o incluso un **baneo** si reincides o la falta es grave.\n"
            "Por favor, toma en serio esta advertencia y mejora tu comportamiento en el servidor."
        ),
        color=Colors.WARNING,
        timestamp=datetime.now()
    )
    advertencia_embed.set_footer(text="Santiago RP | Sistema de Advertencias")
    advertencia_embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/564/564619.png")

    dm_ok = True
    try:
        await usuario.send(embed=advertencia_embed)
    except Exception as e:
        dm_ok = False

    # Enviar embed público en el canal donde se ejecutó el comando (NO efímero)
    await interaction.channel.send(embed=advertencia_embed)

    # Log en canal específico
    log_channel_id = 1367389708597858314
    log_channel = interaction.guild.get_channel(log_channel_id)
    if log_channel:
        await log_channel.send(embed=create_embed(
            title="Usuario Advertido",
            description=(
                f"**Usuario:** {usuario.mention} ({usuario.id})\n"
                f"**Staff:** {admin.mention} ({admin.id})\n"
                f"**Razón:** {razon}\n"
                f"{f'**Prueba:** {prueba}' if prueba else ''}\n"
                f"**DM enviado:** {'Sí' if dm_ok else 'No (no se pudo enviar)'}"
            ),
            color=Colors.WARNING,
            user=admin
        ))

    # Respuesta al staff (efímera)
    await interaction.followup.send(
        embed=create_embed(
            title="Usuario Advertido",
            description=f"El usuario {usuario.mention} ha sido advertido correctamente." if dm_ok else f"No se pudo enviar DM a {usuario.mention}, pero la advertencia fue registrada.",
            color=Colors.SUCCESS if dm_ok else Colors.DANGER,
            user=admin
        ),
        ephemeral=True
    )

async def weekly_top_staff_announcement():
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now(pytz.timezone("America/Santiago"))
        # Ejecutar solo el domingo a las 23:59
        if now.weekday() == 6 and now.hour == 23 and now.minute == 59:
            top_staff = get_top_staff()
            channel = bot.get_channel(Channels.RATINGS)  # Cambia por el canal que prefieras
            if top_staff and channel:
                staff_id, staff_name, avg_rating, count_rating = top_staff
                embed = create_embed(
                    title="🏆 ¡Staff Destacado de la Semana!",
                    description=(
                        f"🎉 **{staff_name}** ha sido el staff mejor calificado esta semana con un promedio de **{avg_rating:.2f} estrellas** "
                        f"en {count_rating} calificaciones.\n\n"
                        "¡Felicidades y sigue así!\n\n"
                        "🔄 **Las calificaciones han sido reiniciadas para la próxima semana.**"
                    ),
                    color=Colors.SUCCESS
                )
                await channel.send(embed=embed)
            elif channel:
                await channel.send(embed=create_embed(
                    title="🏆 Staff Destacado de la Semana",
                    description="No hubo suficientes calificaciones esta semana para destacar a un staff.\n🔄 **Las calificaciones han sido reiniciadas para la próxima semana.**",
                    color=Colors.WARNING
                ))
            clear_ratings()
            # Esperar 61 segundos para evitar múltiples ejecuciones en el mismo minuto
            await asyncio.sleep(61)
        else:
            # Revisar cada minuto
            await asyncio.sleep(60)

@bot.event
async def on_ready():
    print(f'✨ {bot.user.name} está listo!')
    try:
        # Sincronizar comandos
        synced = await bot.tree.sync()
        print(f"🔁 Comandos sincronizados: {', '.join([cmd.name for cmd in synced])}")
        # Calcular el número de miembros sin bots
        guild = bot.get_guild(1339386615147266108)  # Reemplaza con el ID de tu servidor
        if guild:
            member_count = sum(1 for member in guild.members if not member.bot)
            # Establecer actividad personalizada
            activity = discord.Activity(
                type=discord.ActivityType.playing,
                name=f"🌟 Creado por Smile | SantiagoRP | 👥 {member_count} Miembros"
            )
            await bot.change_presence(activity=activity)
            print(f"🎮 Actividad establecida: {activity.name}")
        else:
            print("❌ No se encontró el servidor. Verifica el ID del servidor.")
        # Actualizar canal de conteo de miembros al iniciar
        for guild in bot.guilds:
            await actualizar_canal_conteo_miembros(guild)
    except Exception as e:
        print(f"❌ Error en on_ready: {e}")
    # Inicia la tarea de fondo para el staff destacado semanal
    bot.loop.create_task(weekly_top_staff_announcement())

@bot.tree.command(name="panel", description="Despliega el panel de control administrativo")
@app_commands.checks.has_any_role(*Roles.STAFF)
async def control_panel(interaction: discord.Interaction):
    """Comando para mostrar el panel de control."""
    embed = create_embed(
        title="⚙️ Panel de Control Santiago RP",
        description="Gestiona el servidor con las siguientes opciones:",
        color=Colors.PRIMARY,
        user=interaction.user
    )
    embed.add_field(name="🚀 Abrir Servidor", value="Abre el servidor para todos los jugadores.", inline=True)
    embed.add_field(name="🗳️ Iniciar Votación", value="Inicia una votación para abrir el servidor.", inline=True)
    embed.add_field(name="🔒 Cerrar Servidor", value="Cierra el servidor y notifica a los jugadores.", inline=True)
    
    await interaction.response.send_message(embed=embed, view=ControlPanelView())

def is_tickets_channel():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.channel_id != Channels.TICKETS:
            await interaction.response.send_message(embed=create_embed(
                title="❌ Canal Incorrecto",
                description=f"Este comando solo puede usarse en <#{Channels.TICKETS}>.",
                color=Colors.DANGER
            ), ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

@bot.tree.command(name="tickets", description="Abre el sistema de tickets interactivo")
@is_tickets_channel()
async def setup_tickets(interaction: discord.Interaction):
    """Comando para configurar el sistema de tickets."""
    embed = create_embed(
        title="🎫 Sistema de Tickets Santiago RP",
        description=(
            "¡Bienvenido al sistema de tickets de **Santiago RP**! 🎉\n"
            "Selecciona la categoría que mejor se ajuste a tu necesidad usando el menú desplegable.\n\n"
            "**⚠️ IMPORTANTE:**\n"
            "- Asegúrate de abrir tickets con un motivo válido.\n"
            "- Los tickets sin justificación pueden resultar en **sanciones**.\n"
            "- Lee las reglas del servidor antes de crear un ticket."
        ),
        color=Colors.INFO,
        user=interaction.user
    )
    
    embed.add_field(
        name="🧩 Asistencia General",
        value=(
            "🔹 **Ayuda General**: Resuelve dudas o problemas generales.\n"
            "🔹 **Dudas**: Consulta sobre reglas o mecánicas del servidor."
        ),
        inline=False
    )
    embed.add_field(
        name="🏛️ Trámites Oficiales",
        value=(
            "🔹 **Municipalidad**: Licencias, propiedades, registros.\n"
            "🔹 **Creación Empresa**: Solicita crear una empresa legal.\n"
            "🔹 **Facción Ilegal**: Registro de facciones ilegales."
        ),
        inline=False
    )
    embed.add_field(
        name="⚠️ Reportes y Reclamos",
        value=(
            "🔹 **Compras**: Problemas con paquetes VIP o compras.\n"
            "🔹 **Beneficios**: Reclamos de beneficios especiales.\n"
            "🔹 **Reportes**: Denuncia jugadores o bugs.\n"
            "🔹 **Reclamo Robo**: Reporta pérdidas por robos.\n"
            "🔹 **Apelaciones**: Apela sanciones o baneos."
        ),
        inline=False
    )
    embed.add_field(
        name="🤝 Otros Servicios",
        value=(
            "🔹 **Alianzas**: Solicita alianzas entre facciones.\n"
            "🔹 **Solicitud CK**: Pide un Character Kill (muerte permanente)."
        ),
        inline=False
    )
    
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
    embed.set_footer(text="Santiago RP | Sistema Automatizado | Creado por Smile")
    
    await interaction.response.send_message(embed=embed, view=TicketCreationView())

def is_sanctions_channel():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.channel_id != Channels.SANCTIONS:
            await interaction.response.send_message(embed=create_embed(
                title="❌ Canal Incorrecto",
                description=f"Este comando solo puede usarse en <#{Channels.SANCTIONS}>.",
                color=Colors.DANGER
            ), ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

@bot.tree.command(name="sancionar-a", description="Aplica una sanción a un usuario")
@app_commands.checks.has_any_role(*Roles.STAFF)
@is_sanctions_channel()
@app_commands.autocomplete(tipo_sancion=sanction_type_autocomplete)
@app_commands.describe(
    usuario="Selecciona el usuario a sancionar",
    motivo="Explica por qué se sanciona al usuario",
    tipo_sancion="Elige el tipo de sanción (Advertencia 1, 2 o 3)",
    pruebas="Enlace a las pruebas de la sanción (ej. https://imgur.com/abc)"
)
async def sancionar_a(interaction: discord.Interaction, usuario: discord.Member, motivo: str, tipo_sancion: str, pruebas: str):
    """Comando para sancionar a un usuario."""
    await interaction.response.defer()

    # Validar tipo de sanción
    sanction_roles = {
        "Advertencia 1": Roles.WARN_1,
        "Advertencia 2": Roles.WARN_2,
        "Advertencia 3": Roles.WARN_3,
        "Advertencia 4": Roles.WARN_4,
        "Advertencia 5": Roles.WARN_5,
    }
    
    if tipo_sancion not in sanction_roles:
        return await interaction.followup.send(embed=create_embed(
            title="❌ Tipo de Sanción Inválido",
            description="Por favor, selecciona un tipo de sanción válido (Advertencia 1, Advertencia 2, Advertencia 3).",
            color=Colors.DANGER
        ))

    # Guardar sanción en la base de datos
    sanction_id = save_sanction(
        user_id=usuario.id,
        username=usuario.name,
        reason=motivo,
        sanction_type=tipo_sancion,
        proof_url=pruebas,
        admin_id=interaction.user.id,
        admin_name=interaction.user.name
    )

    # Asignar rol correspondiente
    role_id = sanction_roles[tipo_sancion]
    role = interaction.guild.get_role(role_id)
    try:
        await usuario.add_roles(role, reason=f"Sanción {tipo_sancion} aplicada por {interaction.user.name}")
    except Exception as e:
        print(f"Error al asignar rol: {e}")
        await interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="No se pudo asignar el rol de sanción. Por favor, verifica los permisos del bot.",
            color=Colors.DANGER
        ))
        return

    # Verificar cantidad de sanciones para ban automático
    sanction_count = count_active_sanctions(usuario.id)
    is_banned = False
    ban_reason = None

    if sanction_count >= 3:
        try:
            ban_reason = f"Acumulación de {sanction_count} sanciones activas"
            await interaction.guild.ban(
                usuario,
                reason=ban_reason,
                delete_message_days=0
            )
            is_banned = True
            # Programar desbaneo automático después de 7 días
            await asyncio.sleep(7 * 24 * 60 * 60)  # 7 días en segundos
            await interaction.guild.unban(usuario, reason="Fin de baneo temporal por acumulación de sanciones")
        except Exception as e:
            print(f"Error al banear usuario: {e}")
            await interaction.followup.send(embed=create_embed(
                title="❌ Error",
                description="No se pudo aplicar el baneo automático. Por favor, verifica los permisos del bot.",
                color=Colors.DANGER
            ))
        return

    # Crear embed para respuesta en el canal
    sanction_embed = create_embed(
        title="⚖️ Sanción Aplicada",
        description=f"Se ha sancionado a {usuario.mention} con éxito.",
        color=Colors.DANGER,
        user=interaction.user
    )
    sanction_embed.add_field(name="🆔 ID de Sanción", value=sanction_id, inline=False)
    sanction_embed.add_field(name="👤 Usuario", value=usuario.mention, inline=True)
    sanction_embed.add_field(name="📝 Motivo", value=motivo, inline=True)
    sanction_embed.add_field(name="⚠️ Tipo de Sanción", value=tipo_sancion, inline=True)
    sanction_embed.add_field(name="📸 Pruebas", value=pruebas, inline=False)
    sanction_embed.add_field(name="👮 Aplicada por", value=interaction.user.mention, inline=True)
    if is_banned:
        sanction_embed.add_field(name="🚫 Baneo Temporal", value="7 días por acumulación de sanciones", inline=False)

    await interaction.followup.send(embed=sanction_embed)

    # Enviar notificación al usuario sancionado
    dm_embed = create_embed(
        title="⚖️ Has Recibido una Sanción",
        description=(
            f"Has sido sancionado en **Santiago RP**. Aquí están los detalles:\n\n"
            f"**🆔 ID de Sanción:** {sanction_id}\n"
            f"**📝 Motivo:** {motivo}\n"
            f"**⚠️ Tipo de Sanción:** {tipo_sancion}\n"
            f"**📸 Pruebas:** {pruebas}\n"
            f"**👮 Aplicada por:** {interaction.user.mention}\n"
        ),
        color=Colors.DANGER
    )
    if is_banned:
        dm_embed.add_field(
            name="🚫 Baneo Temporal",
            value="Has sido baneado temporalmente por 7 días debido a la acumulación de sanciones.",
            inline=False
        )
    dm_embed.add_field(
        name="📜 ¿Cómo apelar?",
        value=(
            f"Puedes apelar esta sanción abriendo un ticket en <#{Channels.TICKETS}> seleccionando la categoría **Apelaciones**. "
            f"Asegúrate de incluir el **ID de Sanción** ({sanction_id}) y pruebas que respalden tu caso."
        ),
        inline=False
    )

    try:
        await usuario.send(embed=dm_embed)
    except discord.errors.Forbidden:
        await interaction.followup.send(embed=create_embed(
            title="⚠️ Advertencia",
            description=f"No se pudo enviar el mensaje directo a {usuario.mention}. Es posible que tenga los DMs cerrados.",
            color=Colors.WARNING
        ))

    # Enviar log al canal de sanciones
    log_channel = bot.get_channel(Channels.SANCTION_LOGS)
    if log_channel:
        log_embed = create_embed(
            title="📜 Registro de Sanción",
            description=f"Se ha registrado una nueva sanción en el servidor.",
            color=Colors.DANGER,
            user=interaction.user
        )
        log_embed.add_field(name="🆔 ID de Sanción", value=sanction_id, inline=False)
        log_embed.add_field(name="👤 Usuario", value=usuario.mention, inline=True)
        log_embed.add_field(name="📝 Motivo", value=motivo, inline=True)
        log_embed.add_field(name="⚠️ Tipo de Sanción", value=tipo_sancion, inline=True)
        log_embed.add_field(name="📸 Pruebas", value=pruebas, inline=False)
        log_embed.add_field(name="👮 Aplicada por", value=interaction.user.mention, inline=True)
        if is_banned:
            log_embed.add_field(name="🚫 Baneo Temporal", value="7 días por acumulación de sanciones", inline=False)
        
        await log_channel.send(embed=log_embed)

def is_view_sanctions_channel():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.channel_id != Channels.VIEW_SANCTIONS:
            await interaction.response.send_message(embed=create_embed(
                title="❌ Canal Incorrecto",
                description=f"Este comando solo puede usarse en <#{Channels.VIEW_SANCTIONS}>.",
                color=Colors.DANGER
            ), ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

@bot.tree.command(name="ver-sanciones", description="Muestra las sanciones activas de un usuario")
@is_view_sanctions_channel()
@app_commands.describe(
    usuario="Selecciona un usuario para ver sus sanciones (opcional, por defecto muestra las tuyas)"
)
async def ver_sanciones(interaction: discord.Interaction, usuario: discord.Member = None):
    """Comando para ver las sanciones activas de un usuario."""
    await interaction.response.defer(ephemeral=True)

    # Si no se especifica un usuario, usar el que ejecuta el comando
    target_user = usuario if usuario else interaction.user

    # Obtener sanciones del usuario
    sanctions = get_user_sanctions(target_user.id)

    # Crear embed para mostrar sanciones
    embed = create_embed(
        title="📜 Sanciones Activas",
        description=f"Lista de sanciones activas para {target_user.mention}.",
        color=Colors.INFO,
        user=target_user
    )

    if not sanctions:
        embed.add_field(
            name="✅ Sin Sanciones",
            value="Este usuario no tiene sanciones activas actualmente.",
            inline=False
        )
    else:
        for sanction in sanctions:
            sanction_id, reason, sanction_type, proof_url, admin_name, date = sanction
            embed.add_field(
                name=f"🆔 Sanción {sanction_id[:8]}...",
                value=(
                    f"**Motivo:** {reason}\n"
                    f"**Tipo:** {sanction_type}\n"
                    f"**Pruebas:** {proof_url}\n"
                    f"**Aplicada por:** {admin_name}\n"
                    f"**Fecha:** {datetime.fromisoformat(date).strftime('%d/%m/%Y %H:%M')}"
                ),
                inline=False
            )

    embed.add_field(
        name="📝 ¿Tienes una sanción injusta?",
        value=(
            f"Si crees que alguna sanción es injusta, abre un ticket en <#{Channels.TICKETS}> "
            "seleccionando la categoría **Apelaciones**. Incluye el **ID de Sanción** y pruebas que respalden tu caso."
        ),
        inline=False
    )

    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="borrar-sanciones", description="Borra todas las sanciones activas de un usuario")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    usuario="Selecciona el usuario cuyas sanciones quieres borrar"
)
async def borrar_sanciones(interaction: discord.Interaction, usuario: discord.Member):
    """Comando para borrar todas las sanciones activas de un usuario."""
    await interaction.response.defer(ephemeral=True)

    # Contar sanciones activas antes de borrar
    sanction_count = count_active_sanctions(usuario.id)
    if sanction_count == 0:
        await interaction.followup.send(embed=create_embed(
            title="ℹ️ Sin Sanciones",
            description=f"{usuario.mention} no tiene sanciones activas para borrar.",
            color=Colors.INFO,
            user=interaction.user
        ), ephemeral=True)
        return

    # Marcar sanciones como inactivas
    try:
        affected_rows = delete_user_sanctions(usuario.id)
    except Exception as e:
        print(f"Error al borrar sanciones: {e}")
        await interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="No se pudieron borrar las sanciones. Por favor, intenta de nuevo o contacta a soporte técnico.",
            color=Colors.DANGER,
            user=interaction.user
        ), ephemeral=True)
        return

    # Verificar si se borraron sanciones
    if affected_rows == 0:
        await interaction.followup.send(embed=create_embed(
            title="ℹ️ Sin Cambios",
            description=f"No se encontraron sanciones activas para {usuario.mention}.",
            color=Colors.INFO,
            user=interaction.user
        ), ephemeral=True)
        return

    # Remover roles de advertencia del usuario
    sanction_roles = [Roles.WARN_1, Roles.WARN_2, Roles.WARN_3]
    roles_to_remove = [interaction.guild.get_role(role_id) for role_id in sanction_roles if interaction.guild.get_role(role_id)]
    try:
        await usuario.remove_roles(*roles_to_remove, reason=f"Sanciones borradas por {interaction.user.name}")
    except Exception as e:
        print(f"Error al remover roles: {e}")
        await interaction.followup.send(embed=create_embed(
            title="⚠️ Advertencia",
            description=f"Las sanciones de {usuario.mention} fueron borradas, pero no se pudieron remover los roles de advertencia. Por favor, verifica los permisos del bot.",
            color=Colors.WARNING,
            user=interaction.user
        ), ephemeral=True)
        return

    # Enviar respuesta al administrador
    response_embed = create_embed(
        title="✅ Sanciones Borradas",
        description=f"Se han borrado **{affected_rows}** sanciones activas de {usuario.mention}.",
        color=Colors.SUCCESS,
        user=interaction.user
    )
    response_embed.add_field(name="👤 Usuario", value=usuario.mention, inline=True)
    response_embed.add_field(name="👮 Borradas por", value=interaction.user.mention, inline=True)
    await interaction.followup.send(embed=response_embed, ephemeral=True)

    # Enviar notificación al usuario
    dm_embed = create_embed(
        title="🔔 Sanciones Eliminadas",
        description=(
            f"Todas tus sanciones activas en **Santiago RP** han sido eliminadas.\n\n"
            f"**Total eliminadas:** {affected_rows}\n"
            f"**Eliminadas por:** {interaction.user.mention}\n\n"
            "Asegúrate de seguir las reglas del servidor para evitar futuras sanciones."
        ),
        color=Colors.SUCCESS
    )
    try:
        await usuario.send(embed=dm_embed)
    except discord.errors.Forbidden:
        response_embed.add_field(
            name="⚠️ Advertencia",
            value=f"No se pudo enviar un mensaje directo a {usuario.mention}. Es posible que tenga los DMs cerrados.",
            inline=False
        )
        await interaction.followup.send(embed=response_embed, ephemeral=True)

    # Enviar log al canal de sanciones
    log_channel = bot.get_channel(Channels.SANCTION_LOGS)
    if log_channel:
        log_embed = create_embed(
            title="🗑️ Sanciones Borradas",
            description=f"Se han eliminado sanciones activas del servidor.",
            color=Colors.SUCCESS,
            user=interaction.user
        )
        log_embed.add_field(name="👤 Usuario", value=usuario.mention, inline=True)
        log_embed.add_field(name="📉 Sanciones eliminadas", value=str(affected_rows), inline=True)
        log_embed.add_field(name="👮 Borradas por", value=interaction.user.mention, inline=True)
        await log_channel.send(embed=log_embed)

@bot.tree.command(name="banear-a", description="Aplica un baneo a un usuario")
@app_commands.checks.has_any_role(*Roles.STAFF)
@app_commands.describe(
    usuario="Selecciona el usuario a banear",
    motivo="Explica por qué se banea al usuario",
    pruebas="Enlace a las pruebas del baneo (ej. https://imgur.com/abc)"
)
async def banear_a(interaction: discord.Interaction, usuario: discord.Member, motivo: str, pruebas: str):
    """Comando para banear a un usuario."""
    # Verificar canal correcto
    if interaction.channel_id != 1357151556926963748:
        await interaction.response.send_message(embed=create_embed(
            title="❌ Canal Incorrecto",
            description=f"Este comando solo puede usarse en <#{1357151556926963748}>.",
            color=Colors.DANGER
        ), ephemeral=True)
        return

    await interaction.response.defer()

    # Guardar baneo en la base de datos
    sanction_id = save_sanction(
        user_id=usuario.id,
        username=usuario.name,
        reason=motivo,
        sanction_type="Baneo",
        proof_url=pruebas,
        admin_id=interaction.user.id,
        admin_name=interaction.user.name
    )

    # Aplicar baneo
    try:
        await interaction.guild.ban(
            usuario,
            reason=f"Baneo aplicado por {interaction.user.name}: {motivo}",
            delete_message_days=0
        )
    except Exception as e:
        print(f"Error al banear usuario: {e}")
        await interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="No se pudo aplicar el baneo. Por favor, verifica los permisos del bot.",
            color=Colors.DANGER
        ))
        return

    # Crear embed para respuesta en el canal
    ban_embed = create_embed(
        title="🚫 Baneo Aplicado",
        description=f"Se ha baneado a {usuario.mention} con éxito.",
        color=Colors.DANGER,
        user=interaction.user
    )
    ban_embed.add_field(name="🆔 ID de Baneo", value=sanction_id, inline=False)
    ban_embed.add_field(name="👤 Usuario", value=usuario.mention, inline=True)
    ban_embed.add_field(name="📝 Motivo", value=motivo, inline=True)
    ban_embed.add_field(name="📸 Pruebas", value=pruebas, inline=False)
    ban_embed.add_field(name="👮 Aplicado por", value=interaction.user.mention, inline=True)

    await interaction.followup.send(embed=ban_embed)

    # Enviar notificación al usuario baneado
    dm_embed = create_embed(
        title="🚫 Has Sido Baneado",
        description=(
            f"Has sido baneado en **Santiago RP**. Aquí están los detalles:\n\n"
            f"**🆔 ID de Baneo:** {sanction_id}\n"
            f"**📝 Motivo:** {motivo}\n"
            f"**📸 Pruebas:** {pruebas}\n"
            f"**👮 Aplicado por:** {interaction.user.mention}\n"
        ),
        color=Colors.DANGER
    )
    dm_embed.add_field(
        name="📜 ¿Cómo apelar?",
        value=(
            f"Puedes apelar este baneo abriendo un ticket en <#{Channels.TICKETS}> seleccionando la categoría **Apelaciones**. "
            f"Asegúrate de incluir el **ID de Baneo** ({sanction_id}) y pruebas que respalden tu caso."
        ),
        inline=False
    )

    try:
        await usuario.send(embed=dm_embed)
    except discord.errors.Forbidden:
        await interaction.followup.send(embed=create_embed(
            title="⚠️ Advertencia",
            description=f"No se pudo enviar el mensaje directo a {usuario.mention}. Es posible que tenga los DMs cerrados.",
            color=Colors.WARNING
        ))

    # Enviar log al canal de sanciones
    log_channel = bot.get_channel(Channels.SANCTION_LOGS)
    if log_channel:
        log_embed = create_embed(
            title="📜 Registro de Baneo",
            description=f"Se ha registrado un nuevo baneo en el servidor.",
            color=Colors.DANGER,
            user=interaction.user
        )
        log_embed.add_field(name="🆔 ID de Baneo", value=sanction_id, inline=False)
        log_embed.add_field(name="👤 Usuario", value=usuario.mention, inline=True)
        log_embed.add_field(name="📝 Motivo", value=motivo, inline=True)
        log_embed.add_field(name="📸 Pruebas", value=pruebas, inline=False)
        log_embed.add_field(name="👮 Aplicado por", value=interaction.user.mention, inline=True)
        
        await log_channel.send(embed=log_embed)

async def weekly_top_staff():
    """Tarea semanal para anunciar el mejor staff y reiniciar calificaciones."""
    while True:
        now = datetime.now(pytz.UTC)
        next_monday = now + timedelta(days=(7 - now.weekday()) % 7)
        next_monday = next_monday.replace(hour=0, minute=0, second=0, microsecond=0)
        if now.weekday() == 0 and now.hour == 0:  # Si ya es lunes 00:00
            next_monday += timedelta(days=7)
        seconds_until_monday = (next_monday - now).total_seconds()

        await asyncio.sleep(seconds_until_monday)

        channel = bot.get_channel(Channels.RATINGS)
        if not channel:
            print("⚠️ Canal de calificaciones no encontrado.")
            continue

        top_staff = get_top_staff()
        if top_staff:
            staff_id, staff_name, avg_rating, count = top_staff
            embed = create_embed(
                title="🏆 Staff de la Semana",
                description=(
                    f"¡Felicidades a <@{staff_id}> por ser el **Staff de la Semana**! 🎉\n\n"
                    f"**Promedio:** {avg_rating:.2f}/5 🌟\n"
                    f"**Calificaciones recibidas:** {count}\n\n"
                    "Las calificaciones han sido reiniciadas. ¡Sigue apoyando a nuestro equipo!"
                ),
                color=Colors.SUCCESS
            )
            embed.set_thumbnail(url=bot.get_user(staff_id).display_avatar.url if bot.get_user(staff_id) else None)
            await channel.send(embed=embed)

            # Notificar al staff ganador
            staff_member = bot.get_user(staff_id)
            if staff_member:
                try:
                    dm_embed = create_embed(
                        title="🎉 ¡Eres el Staff de la Semana!",
                        description=(
                            f"¡Felicidades, {staff_name}! Has sido elegido como el **Staff de la Semana** en **Santiago RP**.\n\n"
                            f"**Promedio:** {avg_rating:.2f}/5 🌟\n"
                            f"**Calificaciones recibidas:** {count}\n\n"
                            "Gracias por tu excelente trabajo. ¡Sigue así!"
                        ),
                        color=Colors.SUCCESS
                    )
                    await staff_member.send(embed=dm_embed)
                except discord.errors.Forbidden:
                    print(f"⚠️ No se pudo enviar DM a {staff_name} (DMs cerrados).")

        else:
            embed = create_embed(
                title="📊 Calificaciones Semanales",
                description="No hay suficientes calificaciones esta semana (mínimo 3 por staff). ¡Sigue calificando a nuestro equipo!",
                color=Colors.INFO
            )
            await channel.send(embed=embed)

        # Borrar calificaciones
        clear_ratings()

        # Log en SANCTION_LOGS
        log_channel = bot.get_channel(Channels.SANCTION_LOGS)
        if log_channel:
            log_embed = create_embed(
                title="🔄 Reinicio de Calificaciones",
                description="Se han reiniciado las calificaciones semanales.",
                color=Colors.INFO
            )
            if top_staff:
                log_embed.add_field(name="🏆 Staff de la Semana", value=f"<@{staff_id}> ({avg_rating:.2f}/5)", inline=True)
            await log_channel.send(embed=log_embed)

@bot.tree.command(name="calificar-staff", description="Califica a un miembro del staff")
@is_ratings_channel()
@app_commands.autocomplete(calificacion=rating_autocomplete)
@app_commands.describe(
    usuario="Selecciona el miembro del staff a calificar",
    calificacion="Elige una calificación de 1 a 5 estrellas",
    comentario="Explica por qué das esta calificación"
)
async def calificar_staff(interaction: discord.Interaction, usuario: discord.Member, calificacion: str, comentario: str):
    """Comando para calificar a un miembro del staff."""
    # Verificar que el usuario tiene un rol de STAFF
    if not any(role.id in Roles.STAFF for role in usuario.roles):
        await interaction.response.send_message(embed=create_embed(
            title="❌ Usuario No Válido",
            description=f"{usuario.mention} no es miembro del staff.",
            color=Colors.DANGER
        ), ephemeral=True)
        return

    # Validar calificación
    try:
        rating = int(calificacion)
        if rating < 1 or rating > 5:
            raise ValueError
    except ValueError:
        await interaction.response.send_message(embed=create_embed(
            title="❌ Calificación Inválida",
            description="Por favor, selecciona una calificación entre 1 y 5 estrellas.",
            color=Colors.DANGER
        ), ephemeral=True)
        return

    await interaction.response.defer()

    # Guardar calificación en la base de datos
    rating_id = save_rating(
        staff_id=usuario.id,
        staff_name=usuario.name,
        rating=rating,
        comment=comentario,
        user_id=interaction.user.id,
        user_name=interaction.user.name
    )

    # Crear embed para respuesta en el canal
    rating_embed = create_embed(
        title="🌟 Calificación Registrada",
        description=f"Se ha registrado tu calificación para {usuario.mention}.",
        color=Colors.SUCCESS,
        user=interaction.user
    )
    rating_embed.add_field(name="🆔 ID de Calificación", value=rating_id, inline=False)
    rating_embed.add_field(name="👤 Staff", value=usuario.mention, inline=True)
    rating_embed.add_field(name="🌟 Calificación", value="🌟" * rating, inline=True)
    rating_embed.add_field(name="💬 Comentario", value=comentario, inline=False)
    rating_embed.add_field(name="👥 Calificado por", value=interaction.user.mention, inline=True)

    await interaction.followup.send(embed=rating_embed)

    # Enviar notificación al staff calificado
    dm_embed = create_embed(
        title="🌟 Nueva Calificación Recibida",
        description=(
            f"Has recibido una calificación en **Santiago RP**. Aquí están los detalles:\n\n"
            f"**🆔 ID de Calificación:** {rating_id}\n"
            f"**🌟 Calificación:** {'🌟' * rating} ({rating}/5)\n"
            f"**💬 Comentario:** {comentario}\n"
            f"**👥 Calificado por:** {interaction.user.mention}"
        ),
        color=Colors.SUCCESS
    )

    try:
        await usuario.send(embed=dm_embed)
    except discord.errors.Forbidden:
        await interaction.followup.send(embed=create_embed(
            title="⚠️ Advertencia",
            description=f"No se pudo enviar el mensaje directo a {usuario.mention}. Es posible que tenga los DMs cerrados.",
            color=Colors.WARNING
        ))

    # Enviar log al canal de sanciones
    log_channel = bot.get_channel(Channels.SANCTION_LOGS)
    if log_channel:
        log_embed = create_embed(
            title="📜 Registro de Calificación",
            description=f"Se ha registrado una nueva calificación para un miembro del staff.",
            color=Colors.SUCCESS,
            user=interaction.user
        )
        log_embed.add_field(name="🆔 ID de Calificación", value=rating_id, inline=False)
        log_embed.add_field(name="👤 Staff", value=usuario.mention, inline=True)
        log_embed.add_field(name="🌟 Calificación", value=f"{'🌟' * rating} ({rating}/5)", inline=True)
        log_embed.add_field(name="💬 Comentario", value=comentario, inline=False)
        log_embed.add_field(name="👥 Calificado por", value=interaction.user.mention, inline=True)
        
        await log_channel.send(embed=log_embed)

def is_view_sanctions_channel():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.channel_id != Channels.VIEW_SANCTIONS:
            await interaction.response.send_message(embed=create_embed(
                title="❌ Canal Incorrecto",
                description=f"Este comando solo puede usarse en <#{Channels.VIEW_SANCTIONS}>.",
                color=Colors.DANGER
            ), ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

@bot.tree.command(name="ayuda", description="Muestra todos los comandos disponibles del bot")
async def ayuda(interaction: discord.Interaction):
    """Comando para mostrar la lista de todos los comandos disponibles."""
    await interaction.response.defer(ephemeral=True)

    embed = create_embed(
        title="📖 Guía de Comandos de Santiago RP",
        description=(
            "¡Bienvenido a la guía de comandos de **Santiago RP**! 🎉\n"
            "A continuación, encontrarás todos los comandos disponibles, qué hacen, dónde usarlos y quiénes pueden ejecutarlos."
        ),
        color=Colors.INFO,
        user=interaction.user
    )

    # Lista de comandos con sus detalles
    commands_list = [
        {
            "name": "panel",
            "emoji": "⚙️",
            "description": "Despliega el panel de control para gestionar el servidor (abrir servidor, iniciar votación).",
            "channel": f"Cualquier canal",
            "permissions": "Staff (roles: <@&1357151555916271624>, <@&1357151555916271622>, etc.)"
        },
        {
            "name": "tickets",
            "emoji": "🎫",
            "description": "Abre el sistema interactivo de tickets para reportes, apelaciones, etc.",
            "channel": f"<#{Channels.TICKETS}>",
            "permissions": "Todos"
        },
        {
            "name": "sancionar-a",
            "emoji": "⚖️",
            "description": "Aplica una sanción (Advertencia 1, 2 o 3) a un usuario con motivo y pruebas.",
            "channel": f"<#{Channels.SANCTIONS}>",
            "permissions": "Staff (roles: <@&1357151555916271624>, <@&1357151555916271622>, etc.)"
        },
        {
            "name": "ver-sanciones",
            "emoji": "📜",
            "description": "Muestra las sanciones activas de un usuario (tuyas o de otro).",
            "channel": f"<#{Channels.VIEW_SANCTIONS}>",
            "permissions": "Todos"
        },
        {
            "name": "borrar-sanciones",
            "emoji": "🗑️",
            "description": "Elimina todas las sanciones activas de un usuario.",
            "channel": "Cualquier canal",
            "permissions": "Administradores (permiso: Administrador)"
        },
        {
            "name": "banear-a",
            "emoji": "🚫",
            "description": "Banea a un usuario con motivo y pruebas.",
            "channel": f"<#1357151556926963748>",
            "permissions": "Staff (roles: <@&1357151555916271624>, <@&1357151555916271622>, etc.)"
        },
        {
            "name": "calificar-staff",
            "emoji": "🌟",
            "description": "Califica a un miembro del staff con estrellas (1 a 5) y un comentario.",
            "channel": f"<#{Channels.RATINGS}>",
            "permissions": "Todos"
        },
        {
            "name": "postular-trabajo",
            "emoji": "💼",
            "description": "Postula a un trabajo en Santiago RP (Meganoticias, Taxista, etc.).",
            "channel": f"<#{Channels.JOB_APPLICATIONS}>",
            "permissions": "Todos"
        }
    ]

    # Añadir cada comando como un campo en el embed
    for cmd in commands_list:
        embed.add_field(
            name=f"{cmd['emoji']} /{cmd['name']}",
            value=(
                f"**Descripción:** {cmd['description']}\n"
                f"**Canal:** {cmd['channel']}\n"
                f"**Permisos:** {cmd['permissions']}"
            ),
            inline=False
        )

    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
    embed.set_footer(text="Santiago RP | Sistema Automatizado | Creado por Smile")

    await interaction.followup.send(embed=embed, ephemeral=True)

async def job_role_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    """Autocompletar trabajos disponibles."""
    return [
        app_commands.Choice(name=job["name"], value=job_key)
        for job_key, job in JOB_ROLES.items()
        if current.lower() in job["name"].lower()
    ]

class AcceptJobModal(ui.Modal, title="✅ Aceptar Postulación"):
    reason = ui.TextInput(
        label="Razón de la aceptación",
        placeholder="Explica por qué se aceptó la postulación (mínimo 10 palabras)...",
        style=discord.TextStyle.long,
        required=True,
        min_length=50  # Approximate minimum for 10 words
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class DenyJobModal(ui.Modal, title="❌ Denegar Postulación"):
    reason = ui.TextInput(
        label="Razón de la denegación",
        placeholder="Explica por qué se denegó la postulación (mínimo 10 palabras)...",
        style=discord.TextStyle.long,
        required=True,
        min_length=50  # Approximate minimum for 10 words
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        self.interaction = interaction

class JobApplicationView(ui.View):
    """Vista con botones para aceptar o denegar postulaciones."""
    def __init__(self, applicant: discord.Member, job_key: str, reason: str):
        super().__init__(timeout=None)
        self.applicant = applicant
        self.job_key = job_key
        self.reason = reason
        self.custom_id = f"job_application_{applicant.id}_{job_key}"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verificar que el usuario tenga permisos de staff."""
        if not any(role.id in Roles.STAFF for role in interaction.user.roles):
            await interaction.response.send_message(embed=create_embed(
                title="❌ Acceso Denegado",
                description="Solo el staff puede aceptar o denegar postulaciones.",
                color=Colors.DANGER
            ), ephemeral=True)
            return False
        return True

    @ui.button(label="Aceptar", style=discord.ButtonStyle.green, emoji="✅", custom_id="job_accept")
    async def accept_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = AcceptJobModal()
        await interaction.response.send_modal(modal)
        
        timed_out = await modal.wait()
        if timed_out:
            return

        # Validate reason length
        reason_words = modal.reason.value.split()
        if len(reason_words) < 10:
            await modal.interaction.followup.send(embed=create_embed(
                title="❌ Razón Inválida",
                description="La razón debe tener al menos 10 palabras.",
                color=Colors.DANGER
            ), ephemeral=True)
            return

        # Update embed to green (accepted)
        embed = interaction.message.embeds[0]
        embed.color = Colors.SUCCESS
        embed.set_field_at(
            index=len(embed.fields) - 1,
            name="📋 Estado",
            value=f"**Aceptada** por {interaction.user.mention}\n**Razón:** {modal.reason.value}",
            inline=False
        )
        
        # Disable buttons
        self.children[0].disabled = True
        self.children[1].disabled = True
        await interaction.message.edit(embed=embed, view=self)

        # Assign job role and sueldo role
        job_role = interaction.guild.get_role(JOB_ROLES[self.job_key]["role_id"])
        sueldo_role = interaction.guild.get_role(Roles.SUELDO)
        try:
            await self.applicant.add_roles(job_role, sueldo_role, reason=f"Postulación aceptada por {interaction.user.name}")
        except Exception as e:
            print(f"Error al asignar roles: {e}")
            await modal.interaction.followup.send(embed=create_embed(
                title="❌ Error",
                description="No se pudieron asignar los roles. Verifica los permisos del bot.",
                color=Colors.DANGER
            ), ephemeral=True)
            return

        # Send notification to job applications channel
        job_channel = bot.get_channel(Channels.JOB_APPLICATIONS)
        if job_channel:
            await job_channel.send(
                content=f"🎉 {self.applicant.mention}, ¡tu postulación al trabajo **{JOB_ROLES[self.job_key]['name']}** ha sido **aceptada**! Se te ha asignado un sueldo de **550,000 CLP**.",
                embed=create_embed(
                    title="✅ Postulación Aceptada",
                    description=(
                        f"**Usuario:** {self.applicant.mention}\n"
                        f"**Trabajo:** {JOB_ROLES[self.job_key]['name']}\n"
                        f"**Razón de aceptación:** {modal.reason.value}\n"
                        f"**Aprobado por:** {interaction.user.mention}"
                    ),
                    color=Colors.SUCCESS,
                    user=interaction.user
                )
            )

        # Send DM to applicant
        dm_embed = create_embed(
            title="🎉 ¡Postulación Aceptada!",
            description=(
                f"¡Felicidades, {self.applicant.mention}! Tu postulación al trabajo **{JOB_ROLES[self.job_key]['name']}** en **Santiago RP** ha sido **aceptada**.\n\n"
                f"**Razón de aceptación:** {modal.reason.value}\n"
                f"**Sueldo asignado:** 550,000 CLP\n"
                f"**Aprobado por:** {interaction.user.mention}\n\n"
                "¡Prepárate para comenzar tu nuevo rol! Contacta al staff si necesitas orientación."
            ),
            color=Colors.SUCCESS
        )
        try:
            await self.applicant.send(embed=dm_embed)
        except discord.errors.Forbidden:
            await modal.interaction.followup.send(embed=create_embed(
                title="⚠️ Advertencia",
                description=f"No se pudo enviar el mensaje directo a {self.applicant.mention}. Es posible que tenga los DMs cerrados.",
                color=Colors.WARNING
            ), ephemeral=True)

        # Send log to sanction logs
        log_channel = bot.get_channel(Channels.SANCTION_LOGS)
        if log_channel:
            log_embed = create_embed(
                title="📜 Postulación Aceptada",
                description=f"Se ha aceptado una postulación al trabajo {JOB_ROLES[self.job_key]['name']}.",
                color=Colors.SUCCESS,
                user=interaction.user
            )
            log_embed.add_field(name="👤 Usuario", value=self.applicant.mention, inline=True)
            log_embed.add_field(name="💼 Trabajo", value=JOB_ROLES[self.job_key]['name'], inline=True)
            log_embed.add_field(name="📝 Razón de aceptación", value=modal.reason.value, inline=False)
            log_embed.add_field(name="👮 Aprobado por", value=interaction.user.mention, inline=True)
            await log_channel.send(embed=log_embed)

        await modal.interaction.followup.send(embed=create_embed(
            title="✅ Acción Completada",
            description=f"La postulación de {self.applicant.mention} al trabajo {JOB_ROLES[self.job_key]['name']} ha sido aceptada.",
            color=Colors.SUCCESS
        ), ephemeral=True)

    @ui.button(label="Denegar", style=discord.ButtonStyle.red, emoji="❌", custom_id="job_deny")
    async def deny_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = DenyJobModal()
        await interaction.response.send_modal(modal)
        
        timed_out = await modal.wait()
        if timed_out:
            return

        # Validate reason length
        reason_words = modal.reason.value.split()
        if len(reason_words) < 10:
            await modal.interaction.followup.send(embed=create_embed(
                title="❌ Razón Inválida",
                description="La razón debe tener al menos 10 palabras.",
                color=Colors.DANGER
            ), ephemeral=True)
            return

        # Update embed to red (denied)
        embed = interaction.message.embeds[0]
        embed.color = Colors.DANGER
        embed.set_field_at(
            index=len(embed.fields) - 1,
            name="📋 Estado",
            value=f"**Denegada** por {interaction.user.mention}\n**Razón:** {modal.reason.value}",
            inline=False
        )
        
        # Disable buttons
        self.children[0].disabled = True
        self.children[1].disabled = True
        await interaction.message.edit(embed=embed, view=self)

        # Send notification to job applications channel
        job_channel = bot.get_channel(Channels.JOB_APPLICATIONS)
        if job_channel:
            await job_channel.send(
                content=f"😔 {self.applicant.mention}, tu postulación al trabajo **{JOB_ROLES[self.job_key]['name']}** ha sido **denegada**.",
                embed=create_embed(
                    title="❌ Postulación Denegada",
                    description=(
                        f"**Usuario:** {self.applicant.mention}\n"
                        f"**Trabajo:** {JOB_ROLES[self.job_key]['name']}\n"
                        f"**Razón de denegación:** {modal.reason.value}\n"
                        f"**Denegado por:** {interaction.user.mention}"
                    ),
                    color=Colors.DANGER,
                    user=interaction.user
                )
            )

        # Send DM to applicant
        dm_embed = create_embed(
            title="😔 Postulación Denegada",
            description=(
                f"Lo sentimos, {self.applicant.mention}. Tu postulación al trabajo **{JOB_ROLES[self.job_key]['name']}** en **Santiago RP** ha sido **denegada**.\n\n"
                f"**Razón de denegación:** {modal.reason.value}\n"
                f"**Denegado por:** {interaction.user.mention}\n\n"
                "Puedes intentar postular nuevamente en el futuro. Si tienes dudas, abre un ticket en el canal de soporte."
            ),
            color=Colors.DANGER
        )
        try:
            await self.applicant.send(embed=dm_embed)
        except discord.errors.Forbidden:
            await modal.interaction.followup.send(embed=create_embed(
                title="⚠️ Advertencia",
                description=f"No se pudo enviar el mensaje directo a {self.applicant.mention}. Es posible que tenga los DMs cerrados.",
                color=Colors.WARNING
            ), ephemeral=True)

        # Send log to sanction logs
        log_channel = bot.get_channel(Channels.SANCTION_LOGS)
        if log_channel:
            log_embed = create_embed(
                title="📜 Postulación Denegada",
                description=f"Se ha denegado una postulación al trabajo {JOB_ROLES[self.job_key]['name']}.",
                color=Colors.DANGER,
                user=interaction.user
            )
            log_embed.add_field(name="👤 Usuario", value=self.applicant.mention, inline=True)
            log_embed.add_field(name="💼 Trabajo", value=JOB_ROLES[self.job_key]['name'], inline=True)
            log_embed.add_field(name="📝 Razón de denegación", value=modal.reason.value, inline=False)
            log_embed.add_field(name="👮 Denegado por", value=interaction.user.mention, inline=True)
            await log_channel.send(embed=log_embed)

        await modal.interaction.followup.send(embed=create_embed(
            title="✅ Acción Completada",
            description=f"La postulación de {self.applicant.mention} al trabajo {JOB_ROLES[self.job_key]['name']} ha sido denegada.",
            color=Colors.SUCCESS
        ), ephemeral=True)

def is_job_applications_channel():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.channel_id != Channels.JOB_APPLICATIONS:
            await interaction.response.send_message(embed=create_embed(
                title="❌ Canal Incorrecto",
                description=f"Este comando solo puede usarse en <#{Channels.JOB_APPLICATIONS}>.",
                color=Colors.DANGER
            ), ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

class JobApplicationView(ui.View):
    """Vista con botones para aceptar o denegar postulaciones."""
    def __init__(self, applicant: discord.Member, job_key: str, reason: str):
        super().__init__(timeout=None)
        self.applicant = applicant
        self.job_key = job_key
        self.reason = reason
        self.custom_id = f"job_application_{applicant.id}_{job_key}"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Verificar que el usuario tenga permisos de staff."""
        if not any(role.id in Roles.STAFF for role in interaction.user.roles):
            await interaction.response.send_message(embed=create_embed(
                title="❌ Acceso Denegado",
                description="Solo el staff puede aceptar o denegar postulaciones.",
                color=Colors.DANGER
            ), ephemeral=True)
            return False
        return True

    @ui.button(label="Aceptar", style=discord.ButtonStyle.green, emoji="✅", custom_id="job_accept")
    async def accept_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = AcceptJobModal()
        await interaction.response.send_modal(modal)
        
        timed_out = await modal.wait()
        if timed_out:
            return

        # Validate reason length
        reason_words = modal.reason.value.split()
        if len(reason_words) < 10:
            await modal.interaction.followup.send(embed=create_embed(
                title="❌ Razón Inválida",
                description="La razón debe tener al menos 10 palabras.",
                color=Colors.DANGER
            ), ephemeral=True)
            return

        # Update embed to green (accepted)
        embed = interaction.message.embeds[0]
        embed.color = Colors.SUCCESS
        embed.set_field_at(
            index=len(embed.fields) - 1,
            name="📋 Estado",
            value=f"**Aceptada** por {interaction.user.mention}\n**Razón:** {modal.reason.value}",
            inline=False
        )
        
        # Disable buttons
        self.children[0].disabled = True
        self.children[1].disabled = True
        await interaction.message.edit(embed=embed, view=self)

        # Assign job role and sueldo role
        job_role = interaction.guild.get_role(JOB_ROLES[self.job_key]["role_id"])
        sueldo_role = interaction.guild.get_role(Roles.SUELDO)
        try:
            await self.applicant.add_roles(job_role, sueldo_role, reason=f"Postulación aceptada por {interaction.user.name}")
        except Exception as e:
            print(f"Error al asignar roles: {e}")
            await modal.interaction.followup.send(embed=create_embed(
                title="❌ Error",
                description="No se pudieron asignar los roles. Verifica los permisos del bot.",
                color=Colors.DANGER
            ), ephemeral=True)
            return

        # Send notification to job applications channel
        job_channel = bot.get_channel(Channels.JOB_APPLICATIONS)
        if job_channel:
            await job_channel.send(
                content=f"🎉 {self.applicant.mention}, ¡tu postulación al trabajo **{JOB_ROLES[self.job_key]['name']}** ha sido **aceptada**! Se te ha asignado un sueldo de **550,000 CLP**.",
                embed=create_embed(
                    title="✅ Postulación Aceptada",
                    description=(
                        f"**Usuario:** {self.applicant.mention}\n"
                        f"**Trabajo:** {JOB_ROLES[self.job_key]['name']}\n"
                        f"**Razón de aceptación:** {modal.reason.value}\n"
                        f"**Aprobado por:** {interaction.user.mention}"
                    ),
                    color=Colors.SUCCESS,
                    user=interaction.user
                )
            )

        # Send DM to applicant
        dm_embed = create_embed(
            title="🎉 ¡Postulación Aceptada!",
            description=(
                f"¡Felicidades, {self.applicant.mention}! Tu postulación al trabajo **{JOB_ROLES[self.job_key]['name']}** en **Santiago RP** ha sido **aceptada**.\n\n"
                f"**Razón de aceptación:** {modal.reason.value}\n"
                f"**Sueldo asignado:** 550,000 CLP\n"
                f"**Aprobado por:** {interaction.user.mention}\n\n"
                "¡Prepárate para comenzar tu nuevo rol! Contacta al staff si necesitas orientación."
            ),
            color=Colors.SUCCESS
        )
        try:
            await self.applicant.send(embed=dm_embed)
        except discord.errors.Forbidden:
            await modal.interaction.followup.send(embed=create_embed(
                title="⚠️ Advertencia",
                description=f"No se pudo enviar el mensaje directo a {self.applicant.mention}. Es posible que tenga los DMs cerrados.",
                color=Colors.WARNING
            ), ephemeral=True)

        # Send log to job logs channel (changed from SANCTION_LOGS to JOB_LOGS)
        log_channel = bot.get_channel(Channels.JOB_LOGS)
        if log_channel:
            log_embed = create_embed(
                title="📜 Postulación Aceptada",
                description=f"Se ha aceptado una postulación al trabajo {JOB_ROLES[self.job_key]['name']}.",
                color=Colors.SUCCESS,
                user=interaction.user
            )
            log_embed.add_field(name="👤 Usuario", value=self.applicant.mention, inline=True)
            log_embed.add_field(name="💼 Trabajo", value=JOB_ROLES[self.job_key]['name'], inline=True)
            log_embed.add_field(name="📝 Razón de aceptación", value=modal.reason.value, inline=False)
            log_embed.add_field(name="👮 Aprobado por", value=interaction.user.mention, inline=True)
            await log_channel.send(embed=log_embed)

        await modal.interaction.followup.send(embed=create_embed(
            title="✅ Acción Completada",
            description=f"La postulación de {self.applicant.mention} al trabajo {JOB_ROLES[self.job_key]['name']} ha sido aceptada.",
            color=Colors.SUCCESS
        ), ephemeral=True)

    @ui.button(label="Denegar", style=discord.ButtonStyle.red, emoji="❌", custom_id="job_deny")
    async def deny_button(self, interaction: discord.Interaction, button: ui.Button):
        modal = DenyJobModal()
        await interaction.response.send_modal(modal)
        
        timed_out = await modal.wait()
        if timed_out:
            return

        # Validate reason length
        reason_words = modal.reason.value.split()
        if len(reason_words) < 10:
            await modal.interaction.followup.send(embed=create_embed(
                title="❌ Razón Inválida",
                description="La razón debe tener al menos 10 palabras.",
                color=Colors.DANGER
            ), ephemeral=True)
            return

        # Update embed to red (denied)
        embed = interaction.message.embeds[0]
        embed.color = Colors.DANGER
        embed.set_field_at(
            index=len(embed.fields) - 1,
            name="📋 Estado",
            value=f"**Denegada** por {interaction.user.mention}\n**Razón:** {modal.reason.value}",
            inline=False
        )
        
        # Disable buttons
        self.children[0].disabled = True
        self.children[1].disabled = True
        await interaction.message.edit(embed=embed, view=self)

        # Send notification to job applications channel
        job_channel = bot.get_channel(Channels.JOB_APPLICATIONS)
        if job_channel:
            await job_channel.send(
                content=f"😔 {self.applicant.mention}, tu postulación al trabajo **{JOB_ROLES[self.job_key]['name']}** ha sido **denegada**.",
                embed=create_embed(
                    title="❌ Postulación Denegada",
                    description=(
                        f"**Usuario:** {self.applicant.mention}\n"
                        f"**Trabajo:** {JOB_ROLES[self.job_key]['name']}\n"
                        f"**Razón de denegación:** {modal.reason.value}\n"
                        f"**Denegado por:** {interaction.user.mention}"
                    ),
                    color=Colors.DANGER,
                    user=interaction.user
                )
            )

        # Send DM to applicant
        dm_embed = create_embed(
            title="😔 Postulación Denegada",
            description=(
                f"Lo sentimos, {self.applicant.mention}. Tu postulación al trabajo **{JOB_ROLES[self.job_key]['name']}** en **Santiago RP** ha sido **denegada**.\n\n"
                f"**Razón de denegación:** {modal.reason.value}\n"
                f"**Denegado por:** {interaction.user.mention}\n\n"
                "Puedes intentar postular nuevamente en el futuro. Si tienes dudas, abre un ticket en el canal de soporte."
            ),
            color=Colors.DANGER
        )
        try:
            await self.applicant.send(embed=dm_embed)
        except discord.errors.Forbidden:
            await modal.interaction.followup.send(embed=create_embed(
                title="⚠️ Advertencia",
                description=f"No se pudo enviar el mensaje directo a {self.applicant.mention}. Es posible que tenga los DMs cerrados.",
                color=Colors.WARNING
            ), ephemeral=True)

        # Send log to job logs channel (changed from SANCTION_LOGS to JOB_LOGS)
        log_channel = bot.get_channel(Channels.JOB_LOGS)
        if log_channel:
            log_embed = create_embed(
                title="📜 Postulación Denegada",
                description=f"Se ha denegado una postulación al trabajo {JOB_ROLES[self.job_key]['name']}.",
                color=Colors.DANGER,
                user=interaction.user
            )
            log_embed.add_field(name="👤 Usuario", value=self.applicant.mention, inline=True)
            log_embed.add_field(name="💼 Trabajo", value=JOB_ROLES[self.job_key]['name'], inline=True)
            log_embed.add_field(name="📝 Razón de denegación", value=modal.reason.value, inline=False)
            log_embed.add_field(name="👮 Denegado por", value=interaction.user.mention, inline=True)
            await log_channel.send(embed=log_embed)

        await modal.interaction.followup.send(embed=create_embed(
            title="✅ Acción Completada",
            description=f"La postulación de {self.applicant.mention} al trabajo {JOB_ROLES[self.job_key]['name']} ha sido denegada.",
            color=Colors.SUCCESS
        ), ephemeral=True)

@bot.tree.command(name="postular-trabajo", description="Postula a un trabajo en Santiago RP")
@is_job_applications_channel()
@app_commands.autocomplete(trabajo=job_role_autocomplete)
@app_commands.describe(
    trabajo="Selecciona el trabajo al que deseas postular",
    razon="Explica por qué quieres postular a este trabajo (mínimo 10 palabras)"
)
async def postular_trabajo(interaction: discord.Interaction, trabajo: str, razon: str):
    """Comando para postular a un trabajo."""
    await interaction.response.defer(ephemeral=True)

    # Validate job selection
    if trabajo not in JOB_ROLES:
        await interaction.followup.send(embed=create_embed(
            title="❌ Trabajo Inválido",
            description="Por favor, selecciona un trabajo válido de la lista.",
            color=Colors.DANGER
        ), ephemeral=True)
        return

    # Validate reason length
    reason_words = razon.split()
    if len(reason_words) < 10:
        await interaction.followup.send(embed=create_embed(
            title="❌ Razón Inválida",
            description="La razón debe tener al menos 10 palabras. Por favor, proporciona más detalles.",
            color=Colors.DANGER
        ), ephemeral=True)
        return

    # Send ephemeral confirmation to user
    confirmation_embed = create_embed(
        title="✅ Postulación Enviada",
        description=(
            f"Tu postulación al trabajo **{JOB_ROLES[trabajo]['name']}** ha sido enviada con éxito.\n\n"
            "Por favor, espera la revisión del staff. Recibirás una respuesta en un plazo mínimo de **24 horas**.\n"
            "**Nota:** Asegúrate de tener los DMs abiertos para recibir la notificación."
        ),
        color=Colors.SUCCESS,
        user=interaction.user
    )
    confirmation_embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else "")
    await interaction.followup.send(embed=confirmation_embed, ephemeral=True)

    # Send application to staff review channel
    review_channel = bot.get_channel(Channels.JOB_REVIEW)
    if not review_channel:
        print(f"❌ Error: No se encontró el canal con ID {Channels.JOB_REVIEW}")
        await interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="No se pudo enviar la postulación. Contacta a un administrador.",
            color=Colors.DANGER
        ), ephemeral=True)
        return

    application_embed = create_embed(
        title="💼 Nueva Postulación a Trabajo",
        description=f"Se ha recibido una nueva postulación para el trabajo **{JOB_ROLES[trabajo]['name']}**.",
        color=Colors.WARNING,
        user=interaction.user
    )
    application_embed.add_field(name="👤 Postulante", value=interaction.user.mention, inline=True)
    application_embed.add_field(name="💼 Trabajo", value=JOB_ROLES[trabajo]['name'], inline=True)
    application_embed.add_field(name="📝 Razón", value=razon, inline=False)
    application_embed.add_field(name="🕒 Fecha", value=datetime.now().strftime('%d/%m/%Y %H:%M'), inline=True)
    application_embed.add_field(name="📋 Estado", value="**Pendiente**", inline=False)
    application_embed.set_thumbnail(url=interaction.user.display_avatar.url)

    view = JobApplicationView(applicant=interaction.user, job_key=trabajo, reason=razon)
    try:
        await review_channel.send(embed=application_embed, view=view)
    except discord.errors.Forbidden:
        print(f"❌ Error: El bot no tiene permisos para enviar mensajes en {Channels.JOB_REVIEW}")
        await interaction.followup.send(embed=create_embed(
            title="❌ Error",
            description="No se pudo enviar la postulación. Verifica los permisos del bot.",
            color=Colors.DANGER
        ), ephemeral=True)
        return

    # Log to job logs channel (changed from SANCTION_LOGS to JOB_LOGS)
    log_channel = bot.get_channel(Channels.JOB_LOGS)
    if log_channel:
        log_embed = create_embed(
            title="📜 Nueva Postulación Registrada",
            description=f"Se ha registrado una nueva postulación al trabajo {JOB_ROLES[trabajo]['name']}.",
            color=Colors.WARNING,
            user=interaction.user
        )
        log_embed.add_field(name="👤 Postulante", value=interaction.user.mention, inline=True)
        log_embed.add_field(name="💼 Trabajo", value=JOB_ROLES[trabajo]['name'], inline=True)
        log_embed.add_field(name="📝 Razón", value=razon, inline=False)
        await log_channel.send(embed=log_embed)

# =============================================
# ACTUALIZAR CANAL DE CONTEO DE USUARIOS
# =============================================
@bot.event
async def on_member_join(member):
    if member.bot:
        return
    await actualizar_canal_conteo_miembros(member.guild)

@bot.event
async def on_member_remove(member):
    if member.bot:
        return
    await actualizar_canal_conteo_miembros(member.guild)

async def actualizar_canal_conteo_miembros(guild):
    canal_id = 1367394876479766580  # ID del canal a actualizar
    canal = guild.get_channel(canal_id)
    if canal:
        conteo = sum(1 for m in guild.members if not m.bot)
        nuevo_nombre = f"👥 Usuarios: {conteo}"
        try:
            await canal.edit(name=nuevo_nombre)
        except Exception as e:
            print(f"Error al actualizar el nombre del canal: {e}")

# =============================================
# INICIAR BOT
# =============================================
if __name__ == "__main__":
    bot.run(TOKEN)
