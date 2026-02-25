from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Modelo de Usuário
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='rh')  # admin, master, rh
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)
    
    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'tipo': self.tipo,
            'ativo': self.ativo,
            'data_criacao': self.data_criacao.strftime('%Y-%m-%d %H:%M')
        }

# Modelo de Vaga
class Vaga(db.Model):
    __tablename__ = 'vagas'
    
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    requisitos = db.Column(db.Text)
    localizacao = db.Column(db.String(100))
    status = db.Column(db.String(20), default='ativa')  # ativa, inativa, encerrada
    link_inscricao = db.Column(db.String(200), unique=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_encerramento = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'titulo': self.titulo,
            'descricao': self.descricao,
            'requisitos': self.requisitos,
            'localizacao': self.localizacao,
            'status': self.status,
            'link_inscricao': self.link_inscricao,
            'data_criacao': self.data_criacao.strftime('%Y-%m-%d'),
            'candidatos_count': len(self.candidatos)
        }

# Modelo de Candidato
class Candidato(db.Model):
    __tablename__ = 'candidatos'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    telefone = db.Column(db.String(20))
    linkedin = db.Column(db.String(200))
    arquivo_curriculo = db.Column(db.String(200))  # Nome do arquivo
    expectativa_salario = db.Column(db.String(50))  # Expectativa salarial
    vaga_id = db.Column(db.Integer, db.ForeignKey('vagas.id'))
    status = db.Column(db.String(30), default='pendente')  # pendente, em_analise, aprovado, reprovado, banco_talentos
    observacoes = db.Column(db.Text)
    data_candidatura = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    vaga = db.relationship('Vaga', backref='candidatos')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'telefone': self.telefone,
            'linkedin': self.linkedin,
            'arquivo_curriculo': self.arquivo_curriculo,
            'expectativa_salario': self.expectativa_salario,
            'vaga_id': self.vaga_id,
            'vaga_titulo': self.vaga.titulo if self.vaga else '',
            'status': self.status,
            'observacoes': self.observacoes,
            'data_candidatura': self.data_candidatura.strftime('%Y-%m-%d %H:%M'),
            'data_atualizacao': self.data_atualizacao.strftime('%Y-%m-%d %H:%M')
        }
