from flask_openapi3 import OpenAPI, Info, Tag
from flask import redirect
from urllib.parse import unquote
from sqlalchemy import extract
from sqlalchemy.exc import IntegrityError
from datetime import date, datetime, timedelta
import requests

from model import Session, Pessoa, Evento, RotinaPadrao
from logger import logger
from schemas import *
from flask_cors import CORS

info = Info(title="Comporta.io API Pessoa", version="1.0.0")
app = OpenAPI(__name__, info=info)
CORS(app)

# definindo tags
home_tag = Tag(name="Documentação", description="Seleção de documentação: Swagger, Redoc ou RapiDoc")
pessoa_tag = Tag(name="Pessoa", description="Adição, visualização e remoção de pessoas à base.")
evento_tag = Tag(name="Evento", description="Adição, visualização e remoção de eventos à base.")
rotinapadrao_tag = Tag(name="Rotina Padrão", description="Adição, visualização e remoção de rotina padrão à base.")


@app.get('/', tags=[home_tag])
def home():
    """Redireciona para /openapi, tela que permite a escolha do estilo de documentação.
    """
    return redirect('/openapi')


@app.post('/pessoa', tags=[pessoa_tag],
          responses={"200": PessoaViewSchema, "409": ErrorSchema, "400": ErrorSchema})
def add_pessoa(form: PessoaSchema):
    """Adiciona uma nova pessoa.

    Retorna uma representação das pessoas.
    """
    pessoa = Pessoa(nome=form.nome)
    logger.debug(f"Adicionando pessoa de nome: '{pessoa.nome}'")
    try:
        # criando conexão com a base
        session = Session()
        # adicionando pessoa
        session.add(pessoa)
        # efetivando o camando de adição de novo item na tabela
        session.commit()
        logger.debug(f"Adicionado pessoa de nome: '{pessoa.nome}'")
        return apresenta_pessoa(pessoa), 200

    except IntegrityError as e:
        # como a duplicidade do nome é a provável razão do IntegrityError
        error_msg = "Pessoa de mesmo nome já salvo na base :/"
        logger.warning(f"Erro ao adicionar pessoa '{pessoa.nome}', {error_msg}")
        return {"mesage": error_msg}, 409

    except Exception as e:
        # caso um erro fora do previsto
        error_msg = "Não foi possível salvar novo item :/"
        logger.warning(f"Erro ao adicionar pessoa '{pessoa.nome}', {error_msg}")
        return {"mesage": error_msg}, 400


@app.get('/pessoas', tags=[pessoa_tag],
         responses={"200": ListagemPessoasSchema, "404": ErrorSchema})
def get_pessoas():
    """Recupera todas as pessoas.

    Retorna uma representação da listagem de pessoas.
    """
    logger.debug(f"Coletando pessoas ")
    # criando conexão com a base
    session = Session()
    # fazendo a busca
    pessoas = session.query(Pessoa).all()
    if not pessoas:
        # se não há pessoas cadastradas
        return {"pessoas": []}, 200
    else:
        logger.debug(f"%d rodutos econtrados" % len(pessoas))
        # retorna a representação de pessoas
        return apresenta_pessoas(pessoas), 200


@app.get('/pessoa', tags=[pessoa_tag],
         responses={"200": PessoaViewSchema, "404": ErrorSchema})
def get_pessoa(query: PessoaBuscaIdSchema):
    """Recupera uma pessoa a partir do id.

    Retorna uma representação das pessoas.
    """
    pessoa_id = query.id
    logger.debug(f"Coletando dados sobre pessoa #{pessoa_id}")
    # criando conexão com a base
    session = Session()
    # fazendo a busca
    pessoa = session.query(Pessoa).filter(Pessoa.id == pessoa_id).first()
    if not pessoa:
        # se a pessoa não foi encontrada
        error_msg = "Pessoa não encontrada na base :/"
        logger.warning(f"Erro ao buscar pessoa '{pessoa_id}', {error_msg}")
        return {"mesage": error_msg}, 404
    else:
        logger.debug(f"Pessoa econtrada: '{pessoa.nome}'")
        # retorna a representação de pessoa
        return apresenta_pessoa(pessoa), 200


@app.delete('/pessoa', tags=[pessoa_tag],
            responses={"200": PessoaDelSchema, "404": ErrorSchema})
def del_pessoa(query: PessoaBuscaIdSchema):
    """Deleta uma pessoa a partir do id.

    Retorna uma mensagem de confirmação da remoção.
    """
    pessoa_id = query.id
    logger.debug(f"Deletando dados sobre pessoa #{pessoa_id}")
    # criando conexão com a base
    session = Session()
    # fazendo a remoção
    session.query(RotinaDia).filter(RotinaDia.id_pessoa == pessoa_id).delete()
    session.query(RotinaPadrao).filter(RotinaPadrao.id_pessoa == pessoa_id).delete()
    session.query(Evento).filter(Evento.pessoa == pessoa_id).delete()
    count = session.query(Pessoa).filter(Pessoa.id == pessoa_id).delete()
    session.commit()

    if count:
        # retorna a representação da mensagem de confirmação
        logger.debug(f"Deletado pessoa #{pessoa_id}")
        return {"mesage": "Pessoa removido", "id": pessoa_id}
    else:
        # se o pessoa não foi encontrado
        error_msg = "Pessoa não encontrada na base :/"
        logger.warning(f"Erro ao deletar pessoa #'{pessoa_id}', {error_msg}")
        return {"mesage": error_msg}, 404


@app.post('/evento', tags=[evento_tag],
          responses={"200": PessoaViewSchema, "404": ErrorSchema})
def add_evento(form: EventoSchema):
    """Adiciona um novo evento à uma pessoa.

    Retorna a pessoa com seus eventos cadastrados.
    """
    id_pessoa  = form.id_pessoa
    logger.debug(f"Adicionando eventos a pessoa #{id_pessoa}")
    # criando conexão com a base
    session = Session()
    # fazendo a busca pela pessoa
    pessoa = session.query(Pessoa).filter(Pessoa.id == id_pessoa).first()
    if not pessoa:
        # se pessoa não encontrado
        error_msg = "Pessoa não encontrada na base :/"
        logger.warning(f"Erro ao adicionar evento a pessoa '{id_pessoa}', {error_msg}")
        return {"mesage": error_msg}, 404

    # criando o evento
    nome = form.nome
    evento = Evento(nome)

    # adicionando o comentário ao produto
    pessoa.adiciona_evento(evento)
    session.commit()
    logger.debug(f"Adicionado evento a pessoa #{id_pessoa}")

    # retorna a representação de pessoa
    return apresenta_pessoa(pessoa), 200


@app.delete('/evento', tags=[evento_tag],
            responses={"200": EventoDelSchema, "404": ErrorSchema})
def del_evento(query: EventoBuscaIdSchema):
    """Deleta um evento a partir do id.

    Retorna uma mensagem de confirmação da remoção.
    """
    evento_id = query.id
    logger.debug(f"Deletando dados sobre evento #{evento_id}")
    # criando conexão com a base
    session = Session()
    # fazendo a remoção
    count = session.query(Evento).filter(Evento.id == evento_id).delete()
    session.commit()

    if count:
        # retorna a representação da mensagem de confirmação
        logger.debug(f"Deletado evento #{evento_id}")
        return {"mesage": "Evento removido", "id": evento_id}
    else:
        # se o evento não foi encontrado
        error_msg = "Evento não encontrada na base :/"
        logger.warning(f"Erro ao deletar evento #'{evento_id}', {error_msg}")
        return {"mesage": error_msg}, 404


@app.post('/rotinapadrao', tags=[rotinapadrao_tag],
          responses={"200": PessoaViewSchema, "404": ErrorSchema})
def add_rotinapadrao(form: RotinaPadraoSchema):
    """Adiciona uma nova rotina padrão à uma pessoa.

    Retorna uma representação das pessoas e rotinas padrao associados.
    """
    id_pessoa  = form.id_pessoa
    logger.debug(f"Adicionando rotinas padrao a pessoa #{id_pessoa}")
    # criando conexão com a base
    session = Session()
    # fazendo a busca pela pessoa
    pessoa = session.query(Pessoa).filter(Pessoa.id == id_pessoa).first()    
    if not pessoa:
        # se pessoa não encontrado
        error_msg = "Pessoa não encontrada na base :/"
        logger.warning(f"Erro ao adicionar evento a pessoa '{id_pessoa}', {error_msg}")
        return {"mesage": error_msg}, 404
    
    id_evento  = form.id_evento
    evento = session.query(Evento).filter(Evento.id == id_evento).first()
    if not evento:
        # se pessoa não encontrado
        error_msg = "Evento não encontrada na base :/"
        logger.warning(f"Erro ao adicionar evento a pessoa '{id_evento}', {error_msg}")
        return {"mesage": error_msg}, 404   
    
    diasArray = form.diassemana.split(",")
    rotinas = []

    for dia in diasArray:
        # criando a rotina padrão
        rotinaPadrao = RotinaPadrao(form.hora, dia, evento.id, pessoa.id)
        # adicionando a rotina padrão a pessoa
        rotinas.append(rotinaPadrao)
        
    session.add_all(rotinas)

    session.commit()
    logger.debug(f"Adicionado rotina padrao a pessoa #{id_pessoa}")

    # retorna a representação de pessoa
    return apresenta_pessoa(pessoa), 200


@app.delete('/rotinapadrao', tags=[rotinapadrao_tag],
            responses={"200": RotinaPadraoDelSchema, "404": ErrorSchema})
def del_rotinapadrao(query: RotinaPadraoBuscaIdSchema):
    """Deleta uma rotina padrão a partir do id.

    Retorna uma mensagem de confirmação da remoção.
    """
    rotinapadrao_id = query.id
    logger.debug(f"Deletando dados sobre rotina padrão #{rotinapadrao_id}")
    # criando conexão com a base
    session = Session()
    # fazendo a remoção
    count = session.query(RotinaPadrao).filter(RotinaPadrao.id == rotinapadrao_id).delete()
    session.commit()

    if count:
        # retorna a representação da mensagem de confirmação
        logger.debug(f"Deletado rotina padrão #{rotinapadrao_id}")
        return {"mesage": "Rotina Padrão removido", "id": rotinapadrao_id}
    else:
        # se a rotina padrão não foi encontrado
        error_msg = "Rotina Padrão não encontrada na base :/"
        logger.warning(f"Erro ao deletar rotina padrão #'{rotinapadrao_id}', {error_msg}")
        return {"mesage": error_msg}, 404


@app.get('/rotinaspadrao', tags=[rotinapadrao_tag],
         responses={"200": ListagemRotinasPadraoSchema, "404": ErrorSchema})
def get_rotinaspadrao(query: PessoaBuscaIdSchema):
    """Recupera todas as rotinas padrão a partir do id da pessoa.

    Retorna uma representação da listagem de pessoas.
    """
    logger.debug(f"Coletando pessoas ")
    # criando conexão com a base
    session = Session()
    id_pessoa = query.id
    # fazendo a busca
    rotinaspadrao = session.query(RotinaPadrao).filter(RotinaPadrao.id_pessoa == id_pessoa).all()
    if not rotinaspadrao:
        # se não há rotinas cadastradas
        return {"rotinaspadrao": []}, 200
    else:
        logger.debug(f"%d rotinas econtrados" % len(rotinaspadrao))
        # retorna a representação de rotinas
        print(rotinaspadrao)
        return apresenta_rotinaspadrao(rotinaspadrao), 200
