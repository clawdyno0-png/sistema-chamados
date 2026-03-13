from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'segredo'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)


class Chamado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.String(500))
    prioridade = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default="Novo")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username, password=password).first()

        if user:
            login_user(user)
            return redirect(url_for('index'))

    return render_template("login.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return redirect(url_for('login'))

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template("register.html")


@app.route('/')
@login_required
def index():
    chamados = Chamado.query.all()

    total_novo = Chamado.query.filter_by(status="Novo").count()
    total_andamento = Chamado.query.filter_by(status="Em andamento").count()
    total_resolvido = Chamado.query.filter_by(status="Resolvido").count()

    return render_template(
        "index.html",
        chamados=chamados,
        total_novo=total_novo,
        total_andamento=total_andamento,
        total_resolvido=total_resolvido
    )


@app.route('/novo', methods=['POST'])
@login_required
def novo():
    titulo = request.form['titulo']
    descricao = request.form['descricao']
    prioridade = request.form['prioridade']

    chamado = Chamado(
        titulo=titulo,
        descricao=descricao,
        prioridade=prioridade,
        user_id=current_user.id
    )

    db.session.add(chamado)
    db.session.commit()

    return redirect(url_for('index'))


@app.route('/resolver/<int:id>')
@login_required
def resolver(id):
    chamado = Chamado.query.get_or_404(id)
    chamado.status = "Resolvido"
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
