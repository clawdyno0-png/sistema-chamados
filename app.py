from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.config["SECRET_KEY"] = "segredo"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Faça login para acessar o sistema."
login_manager.login_message_category = "warning"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    chamados = db.relationship("Chamado", backref="usuario", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Chamado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.String(500), nullable=True)
    prioridade = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="Novo")

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/")
@login_required
def index():
    chamados = (
        Chamado.query
        .filter_by(user_id=current_user.id)
        .order_by(Chamado.id.desc())
        .all()
    )

    total_novo = Chamado.query.filter_by(user_id=current_user.id, status="Novo").count()
    total_andamento = Chamado.query.filter_by(user_id=current_user.id, status="Em andamento").count()
    total_resolvido = Chamado.query.filter_by(user_id=current_user.id, status="Resolvido").count()

    return render_template(
        "index.html",
        chamados=chamados,
        total_novo=total_novo,
        total_andamento=total_andamento,
        total_resolvido=total_resolvido
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

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
            return redirect(url_for("index"))

        flash("Usuário ou senha inválidos.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Preencha todos os campos.", "danger")
            return redirect(url_for("register"))

        if len(username) < 3:
            flash("O usuário deve ter pelo menos 3 caracteres.", "warning")
            return redirect(url_for("register"))

        if len(password) < 4:
            flash("A senha deve ter pelo menos 4 caracteres.", "warning")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Esse usuário já existe. Escolha outro.", "warning")
            return redirect(url_for("register"))

        new_user = User(username=username)
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash("Conta criada com sucesso. Faça login para continuar.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/novo", methods=["POST"])
@login_required
def novo():
    titulo = request.form.get("titulo", "").strip()
    descricao = request.form.get("descricao", "").strip()
    prioridade = request.form.get("prioridade", "").strip()

    if not titulo or not prioridade:
        flash("Preencha os campos obrigatórios do chamado.", "danger")
        return redirect(url_for("index"))

    chamado = Chamado(
        titulo=titulo,
        descricao=descricao,
        prioridade=prioridade,
        status="Novo",
        user_id=current_user.id
    )

    db.session.add(chamado)
    db.session.commit()

    flash("Chamado criado com sucesso.", "success")
    return redirect(url_for("index"))


@app.route("/andamento/<int:id>")
@login_required
def andamento(id):
    chamado = Chamado.query.get_or_404(id)

    if chamado.user_id != current_user.id:
        flash("Você não tem permissão para alterar este chamado.", "danger")
        return redirect(url_for("index"))

    if chamado.status == "Novo":
        chamado.status = "Em andamento"
        db.session.commit()
        flash("Chamado movido para Em andamento.", "success")
    else:
        flash("Esse chamado não pode ser movido para Em andamento.", "warning")

    return redirect(url_for("index"))


@app.route("/resolver/<int:id>")
@login_required
def resolver(id):
    chamado = Chamado.query.get_or_404(id)

    if chamado.user_id != current_user.id:
        flash("Você não tem permissão para alterar este chamado.", "danger")
        return redirect(url_for("index"))

    chamado.status = "Resolvido"
    db.session.commit()

    flash("Chamado resolvido com sucesso.", "success")
    return redirect(url_for("index"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu do sistema.", "success")
    return redirect(url_for("login"))


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
