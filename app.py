from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.config["SECRET_KEY"] = "segredo"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

ANALISTA_MASTER_KEY = "Sextafeira"

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Faça login para acessar o sistema."
login_manager.login_message_category = "warning"


# =========================
# MODELOS
# =========================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default="usuario")

    chamados_abertos = db.relationship(
        "Chamado",
        foreign_keys="Chamado.user_id",
        backref="solicitante",
        lazy=True
    )

    chamados_atendidos = db.relationship(
        "Chamado",
        foreign_keys="Chamado.analista_id",
        backref="analista",
        lazy=True
    )

    mensagens = db.relationship(
        "MensagemChamado",
        backref="autor",
        lazy=True
    )

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        try:
            return check_password_hash(self.password, raw_password)
        except Exception:
            return False


class Chamado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    protocolo = db.Column(db.String(30), unique=True, nullable=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    categoria = db.Column(db.String(50), nullable=False, default="Suporte")
    prioridade = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Aberto")

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    analista_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    data_atualizacao = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    mensagens = db.relationship(
        "MensagemChamado",
        backref="chamado",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="MensagemChamado.data_envio.asc()"
    )


class MensagemChamado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mensagem = db.Column(db.Text, nullable=False)
    data_envio = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    chamado_id = db.Column(db.Integer, db.ForeignKey("chamado.id"), nullable=False)
    autor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


# =========================
# LOGIN
# =========================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# =========================
# FUNÇÕES AUXILIARES
# =========================

def usuario_eh_analista():
    return current_user.is_authenticated and current_user.tipo == "analista"


def usuario_pode_ver_chamado(chamado):
    if current_user.tipo == "analista":
        return True
    return chamado.user_id == current_user.id


def gerar_protocolo():
    ano = datetime.utcnow().year
    ultimo_chamado = Chamado.query.order_by(Chamado.id.desc()).first()

    if ultimo_chamado and ultimo_chamado.protocolo:
        try:
            ultimo_numero = int(ultimo_chamado.protocolo.split("-")[-1])
        except (ValueError, IndexError):
            ultimo_numero = ultimo_chamado.id
    else:
        ultimo_numero = 0

    novo_numero = ultimo_numero + 1
    return f"CH-{ano}-{novo_numero:03d}"


# =========================
# ROTAS DE AUTENTICAÇÃO
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_redirect"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Preencha usuário e senha.", "danger")
            return redirect(url_for("login"))

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash("Login realizado com sucesso.", "success")
            return redirect(url_for("dashboard_redirect"))

        flash("Usuário ou senha inválidos.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard_redirect"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        tipo = request.form.get("tipo", "usuario").strip().lower()
        chave_analista = request.form.get("chave_analista", "").strip()

        if not username or not password:
            flash("Preencha todos os campos obrigatórios.", "danger")
            return redirect(url_for("register"))

        if len(username) < 3:
            flash("O usuário deve ter pelo menos 3 caracteres.", "warning")
            return redirect(url_for("register"))

        if len(password) < 4:
            flash("A senha deve ter pelo menos 4 caracteres.", "warning")
            return redirect(url_for("register"))

        if tipo not in ["usuario", "analista"]:
            tipo = "usuario"

        if tipo == "analista" and chave_analista != ANALISTA_MASTER_KEY:
            flash("Chave de validação de analista inválida.", "danger")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Esse usuário já existe.", "warning")
            return redirect(url_for("register"))

        novo_usuario = User(
            username=username,
            tipo=tipo
        )
        novo_usuario.set_password(password)

        db.session.add(novo_usuario)
        db.session.commit()

        flash("Conta criada com sucesso. Faça login para continuar.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu do sistema.", "success")
    return redirect(url_for("login"))


# =========================
# DASHBOARDS
# =========================

@app.route("/")
@login_required
def dashboard_redirect():
    if current_user.tipo == "analista":
        return redirect(url_for("dashboard_analista"))
    return redirect(url_for("dashboard_usuario"))


@app.route("/dashboard/usuario")
@login_required
def dashboard_usuario():
    if current_user.tipo != "usuario":
        return redirect(url_for("dashboard_analista"))

    chamados = (
        Chamado.query
        .filter_by(user_id=current_user.id)
        .order_by(Chamado.data_criacao.desc())
        .all()
    )

    total_aberto = Chamado.query.filter_by(user_id=current_user.id, status="Aberto").count()
    total_atendimento = Chamado.query.filter_by(user_id=current_user.id, status="Em atendimento").count()
    total_aguardando = Chamado.query.filter_by(user_id=current_user.id, status="Aguardando usuário").count()
    total_finalizado = Chamado.query.filter_by(user_id=current_user.id, status="Finalizado").count()

    return render_template(
        "dashboard_usuario.html",
        chamados=chamados,
        total_aberto=total_aberto,
        total_atendimento=total_atendimento,
        total_aguardando=total_aguardando,
        total_finalizado=total_finalizado
    )


@app.route("/dashboard/analista")
@login_required
def dashboard_analista():
    if current_user.tipo != "analista":
        return redirect(url_for("dashboard_usuario"))

    total_aberto = Chamado.query.filter_by(status="Aberto").count()
    total_atendimento = Chamado.query.filter_by(status="Em atendimento").count()
    total_aguardando = Chamado.query.filter_by(status="Aguardando usuário").count()
    total_finalizado = Chamado.query.filter_by(status="Finalizado").count()

    chamados_recentes = (
        Chamado.query
        .order_by(Chamado.data_criacao.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "dashboard_analista.html",
        total_aberto=total_aberto,
        total_atendimento=total_atendimento,
        total_aguardando=total_aguardando,
        total_finalizado=total_finalizado,
        chamados=chamados_recentes
    )


# =========================
# CHAMADOS
# =========================

@app.route("/chamados/novo", methods=["GET", "POST"])
@login_required
def novo_chamado():
    if current_user.tipo != "usuario":
        flash("Apenas usuários podem abrir chamados.", "warning")
        return redirect(url_for("dashboard_redirect"))

    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        descricao = request.form.get("descricao", "").strip()
        categoria = request.form.get("categoria", "").strip()
        prioridade = request.form.get("prioridade", "").strip()

        if not titulo or not descricao or not categoria or not prioridade:
            flash("Preencha todos os campos do chamado.", "danger")
            return redirect(url_for("novo_chamado"))

        chamado = Chamado(
            protocolo=gerar_protocolo(),
            titulo=titulo,
            descricao=descricao,
            categoria=categoria,
            prioridade=prioridade,
            status="Aberto",
            user_id=current_user.id
        )

        db.session.add(chamado)
        db.session.commit()

        flash("Chamado aberto com sucesso.", "success")
        return redirect(url_for("meus_chamados"))

    return render_template("novo_chamado.html")


@app.route("/chamados/meus")
@login_required
def meus_chamados():
    if current_user.tipo != "usuario":
        return redirect(url_for("fila_chamados"))

    chamados = (
        Chamado.query
        .filter_by(user_id=current_user.id)
        .order_by(Chamado.data_criacao.desc())
        .all()
    )

    return render_template("meus_chamados.html", chamados=chamados)


@app.route("/chamados/fila")
@login_required
def fila_chamados():
    if current_user.tipo != "analista":
        return redirect(url_for("meus_chamados"))

    chamados = Chamado.query.all()

    prioridade_peso = {
        "Alta": 0,
        "Média": 1,
        "Baixa": 2
    }

    chamados = sorted(
        chamados,
        key=lambda chamado: (
            0 if chamado.analista_id is None else 1,
            prioridade_peso.get(chamado.prioridade, 99),
            -(chamado.data_criacao.timestamp() if chamado.data_criacao else 0)
        )
    )

    return render_template("fila_chamados.html", chamados=chamados)


@app.route("/chamados/<int:id>")
@login_required
def detalhe_chamado(id):
    chamado = Chamado.query.get_or_404(id)

    if not usuario_pode_ver_chamado(chamado):
        flash("Você não tem permissão para acessar este chamado.", "danger")
        return redirect(url_for("dashboard_redirect"))

    mensagens = (
        MensagemChamado.query
        .filter_by(chamado_id=chamado.id)
        .order_by(MensagemChamado.data_envio.asc())
        .all()
    )

    return render_template(
        "detalhe_chamado.html",
        chamado=chamado,
        mensagens=mensagens
    )


@app.route("/chamados/<int:id>/assumir", methods=["POST"])
@login_required
def assumir_chamado(id):
    if not usuario_eh_analista():
        flash("Apenas analistas podem assumir chamados.", "danger")
        return redirect(url_for("dashboard_redirect"))

    chamado = Chamado.query.get_or_404(id)

    if chamado.analista_id is None:
        chamado.analista_id = current_user.id

        if chamado.status == "Aberto":
            chamado.status = "Em atendimento"

        db.session.commit()
        flash("Chamado assumido com sucesso.", "success")
    elif chamado.analista_id == current_user.id:
        flash("Você já é o responsável por este chamado.", "info")
    else:
        flash("Este chamado já está atribuído a outro analista.", "warning")

    return redirect(url_for("detalhe_chamado", id=id))


@app.route("/chamados/<int:id>/mensagem", methods=["POST"])
@login_required
def enviar_mensagem(id):
    chamado = Chamado.query.get_or_404(id)

    if not usuario_pode_ver_chamado(chamado):
        flash("Você não tem permissão para interagir com este chamado.", "danger")
        return redirect(url_for("dashboard_redirect"))

    if chamado.status == "Finalizado":
        flash("Este chamado já foi finalizado e não aceita novas mensagens.", "warning")
        return redirect(url_for("detalhe_chamado", id=id))

    texto = request.form.get("mensagem", "").strip()

    if not texto:
        flash("Digite uma mensagem antes de enviar.", "warning")
        return redirect(url_for("detalhe_chamado", id=id))

    nova_mensagem = MensagemChamado(
        mensagem=texto,
        chamado_id=chamado.id,
        autor_id=current_user.id
    )

    db.session.add(nova_mensagem)

    if current_user.tipo == "usuario" and chamado.status == "Aguardando usuário":
        chamado.status = "Em atendimento"

    if current_user.tipo == "analista" and chamado.analista_id is None:
        chamado.analista_id = current_user.id
        if chamado.status == "Aberto":
            chamado.status = "Em atendimento"

    db.session.commit()

    flash("Mensagem enviada com sucesso.", "success")
    return redirect(url_for("detalhe_chamado", id=id))


@app.route("/chamados/<int:id>/status", methods=["POST"])
@login_required
def alterar_status_chamado(id):
    if not usuario_eh_analista():
        flash("Apenas analistas podem alterar o status.", "danger")
        return redirect(url_for("dashboard_redirect"))

    chamado = Chamado.query.get_or_404(id)
    novo_status = request.form.get("status", "").strip()

    status_validos = ["Aberto", "Em atendimento", "Aguardando usuário", "Finalizado"]

    if novo_status not in status_validos:
        flash("Status inválido.", "warning")
        return redirect(url_for("detalhe_chamado", id=id))

    chamado.status = novo_status

    if chamado.analista_id is None:
        chamado.analista_id = current_user.id

    db.session.commit()

    flash("Status atualizado com sucesso.", "success")
    return redirect(url_for("detalhe_chamado", id=id))


# =========================
# INICIALIZAÇÃO
# =========================

with app.app_context():
    db.create_all()

    chamados_sem_protocolo = Chamado.query.filter(
        (Chamado.protocolo.is_(None)) | (Chamado.protocolo == "")
    ).order_by(Chamado.id.asc()).all()

    for chamado in chamados_sem_protocolo:
        ano = chamado.data_criacao.year if chamado.data_criacao else datetime.utcnow().year
        chamado.protocolo = f"CH-{ano}-{chamado.id:03d}"

    db.session.commit()


if __name__ == "__main__":
    app.run(debug=True)
