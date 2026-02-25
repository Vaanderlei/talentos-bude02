from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
from app import app, db, mail
from models import Usuario, Vaga, Candidato
from flask_mail import Message
from functools import wraps
import os
import uuid
import re

# Configuração de upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def verificar_admin():
    return 'usuario_id' in session and session.get('tipo') in ['admin', 'master', 'rh']

def verificar_master():
    return 'usuario_id' in session and session.get('tipo') == 'master'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not verificar_admin():
            if 'usuario_id' not in session:
                flash('Sua sessão expirou. Faça login novamente.', 'error')
            else:
                flash('Você não tem permissão para acessar esta página.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Sanitização de entrada
def sanitize_input(text):
    """Remove caracteres perigosos de entrada"""
    if not text:
        return ''
    # Remove tags HTML/JS
    text = re.sub(r'<[^>]+>', '', str(text))
    return text.strip()

# Página inicial
@app.route('/')
def index():
    return render_template('index.html')

# Login - SEM rate limiting para permitir múltiplos usuários
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = sanitize_input(request.form['email'])
        senha = request.form['senha']
        
        # Validar formato de email
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            flash('Email inválido.', 'error')
            return render_template('login.html')
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and usuario.verificar_senha(senha) and usuario.ativo:
            session.permanent = True
            session['usuario_id'] = usuario.id
            session['usuario_nome'] = usuario.nome
            session['tipo'] = usuario.tipo
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Email ou senha incorretos.', 'error')
    
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Logout realizado com sucesso!', 'success')
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    vagas = Vaga.query.order_by(Vaga.data_criacao.desc()).all()
    candidatos = Candidato.query.order_by(Candidato.data_candidatura.desc()).all()
    usuarios = Usuario.query.all()
    
    # Estatísticas
    total_vagas = len(vagas)
    vagas_ativas = len([v for v in vagas if v.status == 'ativa'])
    total_candidatos = len(candidatos)
    candidatos_pendentes = len([c for c in candidatos if c.status == 'pendente'])
    banco_talentos = len([c for c in candidatos if c.status == 'banco_talentos'])
    
    return render_template('dashboard.html', 
                         vagas=vagas, 
                         candidatos=candidatos,
                         usuarios=usuarios,
                         total_vagas=total_vagas,
                         vagas_ativas=vagas_ativas,
                         total_candidatos=total_candidatos,
                         candidatos_pendentes=candidatos_pendentes,
                         banco_talentos=banco_talentos)

# ===== GESTÃO DE USUÁRIOS =====

@app.route('/usuarios')
@login_required
def listar_usuarios():
    usuarios = Usuario.query.order_by(Usuario.data_criacao.desc()).all()
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/usuarios/cadastrar', methods=['GET', 'POST'])
@login_required
def cadastrar_usuario():
    if request.method == 'POST':
        nome = sanitize_input(request.form['nome'])
        email = sanitize_input(request.form['email'])
        senha = request.form['senha']
        tipo = request.form['tipo']
        
        if Usuario.query.filter_by(email=email).first():
            flash('Email já cadastrado.', 'error')
            return redirect(url_for('cadastrar_usuario'))
        
        usuario = Usuario(nome=nome, email=email, tipo=tipo)
        usuario.set_senha(senha)
        
        db.session.add(usuario)
        db.session.commit()
        
        flash('Usuário cadastrado com sucesso!', 'success')
        return redirect(url_for('listar_usuarios'))
    
    return render_template('cadastrar_usuario.html')

@app.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    
    if request.method == 'POST':
        usuario.nome = sanitize_input(request.form['nome'])
        usuario.email = sanitize_input(request.form['email'])
        usuario.tipo = request.form['tipo']
        usuario.ativo = 'ativo' in request.form
        
        if request.form['senha']:
            usuario.set_senha(request.form['senha'])
        
        db.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('listar_usuarios'))
    
    return render_template('editar_usuario.html', usuario=usuario)

@app.route('/usuarios/excluir/<int:id>')
@login_required
def excluir_usuario(id):
    if not verificar_master():
        flash('Acesso restrito ao usuário master.', 'error')
        return redirect(url_for('login'))
    
    usuario = Usuario.query.get_or_404(id)
    
    if usuario.id == session.get('usuario_id'):
        flash('Não é possível excluir seu próprio usuário.', 'error')
        return redirect(url_for('listar_usuarios'))
    
    db.session.delete(usuario)
    db.session.commit()
    flash('Usuário excluído com sucesso!', 'success')
    return redirect(url_for('listar_usuarios'))

# ===== GESTÃO DE VAGAS =====

@app.route('/vagas')
@login_required
def listar_vagas():
    vagas = Vaga.query.order_by(Vaga.data_criacao.desc()).all()
    return render_template('vagas.html', vagas=vagas)

@app.route('/vagas/criar', methods=['GET', 'POST'])
@login_required
def criar_vaga():
    if request.method == 'POST':
        titulo = sanitize_input(request.form['titulo'])
        descricao = sanitize_input(request.form['descricao'])
        requisitos = sanitize_input(request.form.get('requisitos', ''))
        localizacao = sanitize_input(request.form.get('localizacao', ''))
        
        # Gerar link único para inscrição
        link = str(uuid.uuid4())[:8]
        
        vaga = Vaga(
            titulo=titulo,
            descricao=descricao,
            requisitos=requisitos,
            localizacao=localizacao,
            link_inscricao=link
        )
        
        db.session.add(vaga)
        db.session.commit()
        
        flash('Vaga criada com sucesso!', 'success')
        return redirect(url_for('listar_vagas'))
    
    return render_template('criar_vaga.html')

@app.route('/vagas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_vaga(id):
    vaga = Vaga.query.get_or_404(id)
    
    if request.method == 'POST':
        vaga.titulo = sanitize_input(request.form['titulo'])
        vaga.descricao = sanitize_input(request.form['descricao'])
        vaga.requisitos = sanitize_input(request.form.get('requisitos', ''))
        vaga.localizacao = sanitize_input(request.form.get('localizacao', ''))
        vaga.status = request.form['status']
        
        db.session.commit()
        flash('Vaga atualizada com sucesso!', 'success')
        return redirect(url_for('listar_vagas'))
    
    return render_template('editar_vaga.html', vaga=vaga)

@app.route('/vagas/excluir/<int:id>')
@login_required
def excluir_vaga(id):
    vaga = Vaga.query.get_or_404(id)
    
    # Excluir candidatos relacionados
    Candidato.query.filter_by(vaga_id=id).delete()
    db.session.delete(vaga)
    db.session.commit()
    
    flash('Vaga excluída com sucesso!', 'success')
    return redirect(url_for('listar_vagas'))

# ===== INSCRIÇÃO PÚBLICA =====

@app.route('/inscrever/<link>')
def pagina_inscricao(link):
    vaga = Vaga.query.filter_by(link_inscricao=link, status='ativa').first()
    
    if not vaga:
        flash('Vaga não encontrada ou encerrada.', 'error')
        return redirect(url_for('index'))
    
    return render_template('inscricao.html', vaga=vaga)

@app.route('/inscrever/<link>', methods=['POST'])
def processar_inscricao(link):
    vaga = Vaga.query.filter_by(link_inscricao=link, status='ativa').first()
    
    if not vaga:
        flash('Vaga não encontrada ou encerrada.', 'error')
        return redirect(url_for('index'))
    
    # Sanitizar entradas
    nome = sanitize_input(request.form['nome'])
    email = sanitize_input(request.form['email'])
    telefone = sanitize_input(request.form.get('telefone', ''))
    linkedin = sanitize_input(request.form.get('linkedin', ''))
    expectativa_salario = sanitize_input(request.form.get('expectativa_salario', ''))
    
    # Validar email
    if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
        flash('Email inválido.', 'error')
        return render_template('inscricao.html', vaga=vaga)
    
    # Validar nome
    if len(nome) < 3:
        flash('Nome inválido.', 'error')
        return render_template('inscricao.html', vaga=vaga)
    
    # Processar upload do currículo
    arquivo = request.files['curriculo']
    nome_arquivo = ''
    
    if arquivo and allowed_file(arquivo.filename):
        ext = arquivo.filename.rsplit('.', 1)[1].lower()
        nome_arquivo = f"{nome.replace(' ', '_')}_{vaga.id}_{uuid.uuid4().hex[:6]}.{ext}"
        arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_arquivo))
    
    candidato = Candidato(
        nome=nome,
        email=email,
        telefone=telefone,
        linkedin=linkedin,
        arquivo_curriculo=nome_arquivo,
        expectativa_salario=expectativa_salario,
        vaga_id=vaga.id,
        status='pendente'
    )
    
    db.session.add(candidato)
    db.session.commit()
    
    # Enviar email de confirmação
    try:
        msg = Message(
            subject=f"Confirmação de Candidatura - {vaga.titulo}",
            recipients=[email],
            body=f"""Olá {nome}!

Obrigado por se candidatar à vaga de {vaga.titulo} na Talentos Budel.

Recebemos sua inscrição com sucesso! Nossa equipe de Recursos Humanos analisará seu currículo e entrará em contato em breve.

Atenciosamente,
Equipe Talentos Budel
"""
        )
        mail.send(msg)
    except:
        pass  # Se email falhar, continua normalmente
    
    flash('Candidatura realizada com sucesso! Verifique seu email para confirmação.', 'success')
    return render_template('inscricao_sucesso.html', vaga=vaga)

# ===== GESTÃO DE CANDIDATOS =====

@app.route('/candidatos/vaga/<int:vaga_id>')
@login_required
def candidatos_por_vaga(vaga_id):
    vaga = Vaga.query.get_or_404(vaga_id)
    candidatos = Candidato.query.filter_by(vaga_id=vaga_id).order_by(Candidato.data_candidatura.desc()).all()
    
    return render_template('candidatos_vaga.html', vaga=vaga, candidatos=candidatos)

@app.route('/candidatos/status/<int:id>', methods=['POST'])
@login_required
def atualizar_status_candidato(id):
    candidato = Candidato.query.get_or_404(id)
    candidato.status = request.form['status']
    candidato.observacoes = sanitize_input(request.form.get('observacoes', ''))
    
    db.session.commit()
    flash('Status atualizado com sucesso!', 'success')
    
    return redirect(url_for('candidatos_por_vaga', vaga_id=candidato.vaga_id))

@app.route('/banco-talentos')
@login_required
def banco_talentos():
    busca = sanitize_input(request.args.get('busca', ''))
    status_filter = request.args.get('status', '')
    
    query = Candidato.query
    
    if busca:
        query = query.filter(
            (Candidato.nome.contains(busca)) | 
            (Candidato.vaga.has(Vaga.titulo.contains(busca)))
        )
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    candidatos = query.order_by(Candidato.data_candidatura.desc()).all()
    
    stats = {
        'pendente': Candidato.query.filter_by(status='pendente').count(),
        'em_analise': Candidato.query.filter_by(status='em_analise').count(),
        'aprovado': Candidato.query.filter_by(status='aprovado').count(),
        'reprovado': Candidato.query.filter_by(status='reprovado').count(),
        'banco_talentos': Candidato.query.filter_by(status='banco_talentos').count()
    }
    
    return render_template('banco_talentos.html', candidatos=candidatos, stats=stats)

@app.route('/candidatos/ver/<int:id>')
@login_required
def ver_candidato(id):
    candidato = Candidato.query.get_or_404(id)
    return render_template('ver_candidato.html', candidato=candidato)

@app.route('/download/<nome_arquivo>')
@login_required
def download_curriculo(nome_arquivo):
    # Validar nome do arquivo para evitar path traversal
    nome_arquivo = os.path.basename(nome_arquivo)
    return send_from_directory(app.config['UPLOAD_FOLDER'], nome_arquivo, as_attachment=True)

# ===== MANUTENÇÃO (MASTER) =====

@app.route('/manutencao')
@login_required
def manutencao():
    if not verificar_master():
        flash('Acesso restrito ao usuário master.', 'error')
        return redirect(url_for('login'))
    
    return render_template('manutencao.html')

@app.route('/manutencao/backup')
@login_required
def backup_banco():
    if not verificar_master():
        flash('Acesso restrito ao usuário master.', 'error')
        return redirect(url_for('login'))
    
    import shutil
    from datetime import datetime
    
    if not os.path.exists('backups'):
        os.makedirs('backups')
    
    backup_name = f"backup_talentos_budel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy('talentos_budel.db', f"backups/{backup_name}")
    
    flash(f'Backup realizado: {backup_name}', 'success')
    return redirect(url_for('manutencao'))

@app.route('/manutencao/logs')
@login_required
def ver_logs():
    if not verificar_master():
        flash('Acesso restrito ao usuário master.', 'error')
        return redirect(url_for('login'))
    
    logs = [
        {'data': '2024-01-15 10:30:00', 'acao': 'Login', 'usuario': 'admin@budel.com.br'},
        {'data': '2024-01-15 10:35:00', 'acao': 'Criar vaga', 'usuario': 'admin@budel.com.br'},
        {'data': '2024-01-15 11:00:00', 'acao': 'Candidatura', 'usuario': 'João Silva'},
        {'data': '2024-01-15 11:15:00', 'acao': 'Atualizar status', 'usuario': 'rh@budel.com.br'},
    ]
    
    return render_template('logs.html', logs=logs)
