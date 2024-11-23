from flask import flash, redirect, url_for
from . import db
from sqlalchemy.sql import func
from flask_login import UserMixin
from flask_admin.contrib.sqla import ModelView
from . import admin
from sqlalchemy import desc
import yfinance as yf  
from datetime import datetime

class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True)
    senha = db.Column(db.String(150))
    nome = db.Column(db.String(150))
    compra_acao = db.relationship('CompraAcao', cascade='all, delete-orphan', backref='usuario')
    acao = db.relationship('Acao', cascade='all, delete-orphan', backref='usuario')
    carteira = db.relationship('Carteira', cascade='all, delete-orphan', backref='usuario')
    hist = db.relationship('Historico', cascade='all, delete-orphan', backref='usuario')
    hist_oper = db.relationship('HistOperacoes', cascade='all, delete-orphan', backref='usuario')
    hist_div = db.relationship('HistDividendos', cascade='all, delete-orphan', backref='usuario')
    cotacoes = db.relationship('Cotacao')

    def addAcao(self, ticker, preco_pago, quantidade, descricao, data_compra_str):
        ticker = ticker.upper()
        acao_query = Acao.query.filter_by(ticker=ticker).filter_by(usuario_id=self.id).first()
        if acao_query:
            ativo = yf.Ticker(ticker+".SA")
            preco_atual = round(ativo.history(period='1d')['Close'].iloc[0], 2)
            valor_pago = round(preco_pago*quantidade, 2)
            acao_query.quantidade = acao_query.quantidade + quantidade
            acao_query.preco_medio = round((acao_query.valor_pago+valor_pago)/(acao_query.quantidade), 2)
            acao_query.valor_pago = round(acao_query.valor_pago + valor_pago, 2)
            acao_query.valor_atual = round(preco_atual*acao_query.quantidade, 2)
            acao_query.lucro_prejuizo = round(acao_query.valor_atual - acao_query.valor_pago, 2)
            acao_query.rentabilidade = round(acao_query.lucro_prejuizo/acao_query.valor_pago*100, 2)
            if acao_query.rentabilidade > 0:
                acao_query.status = "lucro"
            elif acao_query.rentabilidade == 0:
                acao_query.status = "zero"
            else:
                acao_query.status = "prejuizo"
            data_compra = datetime.strptime(data_compra_str, '%Y-%m-%d')
            Usuario.addDividendosCompraAcao(self, ticker, acao_query.quantidade, data_compra, acao_query.preco_medio)
            db.session.commit()
            nova_compra = CompraAcao(ticker = ticker, 
                                     preco_pago = preco_pago, 
                                     quantidade = quantidade, 
                                     valor_pago = valor_pago, 
                                     data_compra = data_compra, 
                                     usuario_id = self.id)
            hist_acao = Historico(usuario_id = self.id, 
                                  ticker=ticker, 
                                  descricao=descricao, 
                                  quantidade=quantidade, 
                                  preco = preco_pago, 
                                  valor = valor_pago, 
                                  tipo = "compra", 
                                  data = data_compra)
            
            db.session.add(nova_compra)
            db.session.add(hist_acao)
            db.session.commit()
            flash(f"Mais {quantidade} ações foram adicionadas a {ticker}")
            return redirect(url_for('views.add_acao'))
        else:
            data_compra = datetime.strptime(data_compra_str, '%Y-%m-%d')
            valor_pago = round(preco_pago*quantidade, 2)
            acao = yf.Ticker(ticker+".SA")
            preco_atual = round(acao.history(period='1d')['Close'].iloc[0], 2)
            valor_atual = round(preco_atual*quantidade, 2)
            lucro_prejuizo = round(valor_atual-valor_pago, 2)
            rentabilidade = round(lucro_prejuizo/valor_pago*100, 2)
            data_compra = datetime.strptime(data_compra_str, '%Y-%m-%d')
            if rentabilidade > 0:
                status = "lucro"
            elif rentabilidade == 0:
                status = "zero"
            else:
                status = "prejuizo"
            data_ultimo_dividendo = Usuario.addDividendosAcao(self, ticker, quantidade, data_compra, preco_pago)
            print(type(data_ultimo_dividendo))
            nova_compra = CompraAcao(ticker = ticker,
                                     preco_pago = preco_pago,
                                     quantidade = quantidade,
                                     valor_pago = valor_pago, 
                                     data_compra = data_compra, 
                                     usuario_id = self.id
                                     )
            acao = Acao(ticker = ticker, 
                        preco_medio = preco_pago, 
                        quantidade = quantidade, 
                        valor_pago = valor_pago, 
                        data_compra_inicial=data_compra, 
                        preco_atual = preco_atual, 
                        valor_atual= valor_atual,
                        rentabilidade = rentabilidade, 
                        lucro_prejuizo=lucro_prejuizo, 
                        status = status,
                        data_ultimo_dividendo=data_ultimo_dividendo,
                        usuario_id = self.id)
            hist_acao = Historico(usuario_id = self.id, 
                                  ticker=ticker, descricao=descricao, 
                                  quantidade=quantidade, 
                                  preco = preco_pago, 
                                  valor = valor_pago, 
                                  tipo = "compra", 
                                  data = data_compra)
            db.session.add(hist_acao)
            db.session.add(acao)
            db.session.add(nova_compra)
            db.session.commit()
            flash(f"{ticker} adicionada a carteira", category='success')
            return redirect(url_for('views.add_acao'))

    def atualizarCarteira(self):
        acoes_query = Acao.query.filter_by(usuario_id=self.id)
        carteira_query = Carteira.query.filter_by(usuario_id=self.id).first()
        for acao in acoes_query:
            ativo = yf.Ticker(acao.ticker+".SA")
            acao.preco_atual = round(ativo.history(period='1d')['Close'].iloc[0], 2)
            acao.valor_atual = round(acao.preco_atual*acao.quantidade, 2)
            acao.lucro_prejuizo = round(acao.valor_atual-acao.valor_pago, 2)
            acao.rentabilidade = round(acao.lucro_prejuizo/acao.valor_pago*100, 2)
            if acao.rentabilidade > 0:
                acao.status = "lucro"
            elif acao.rentabilidade == 0:
                acao.status = "zero"
            else:
                acao.status = "prejuizo"
            acao.peso = round((acao.valor_atual/carteira_query.valor_atual)*100, 2)
            db.session.commit()
            print(f'Ação: {acao.ticker}, peso: {acao.peso}')
        qry_sum = db.session.query(func.sum(Acao.valor_pago).label("valor_pago"),
                        func.sum(Acao.valor_atual).label("preco_atual")).filter_by(usuario_id=self.id)
        valores = qry_sum.first()
        ValorPago = valores[0]
        ValorAtual = valores[1]
        print(ValorAtual)
        print(ValorPago)
        carteira_query.valor_pago = round(ValorPago, 2)
        carteira_query.valor_atual = round(ValorAtual, 2)
        carteira_query.lucro_prejuizo = round(ValorAtual - ValorPago, 2)
        carteira_query.rentabilidade = round(carteira_query.lucro_prejuizo/ValorPago*100, 2)
        if carteira_query.rentabilidade > 0:
            carteira_query.status = "lucro"
        elif carteira_query.rentabilidade == 0:
            carteira_query.status = "zero"
        else:
            carteira_query.status = "prejuizo"
        db.session.commit()
      
    def removeAcao(self, ticker, preco_venda, quantidade, descricao, data):
        ticker = ticker.upper()
        data = datetime.strptime(data, '%Y-%m-%d')
        self.atualizaDividendos()
        acao = Acao.query.filter_by(usuario_id=self.id).filter_by(ticker=ticker).first()
        print(acao.ticker)
        print(acao.quantidade)
        if quantidade > acao.quantidade:
            return
        elif quantidade == acao.quantidade:
            hist = Historico(usuario_id=self.id, 
                             ticker=ticker, 
                             preco=preco_venda, 
                             quantidade=quantidade, 
                             valor=preco_venda*quantidade, 
                             descricao=descricao,
                             tipo="venda",
                             data=data)
            hist_op = HistOperacoes(usuario_id=self.id,
                                    ticker=ticker,
                                    preco_compra=acao.preco_medio,
                                    quantidade_compra=acao.quantidade,
                                    valor_compra= acao.valor_pago,
                                    preco_venda=preco_venda,
                                    quantidade_venda=quantidade,
                                    lucro_prejuizo=hist.valor-acao.valor_pago,
                                    rentabilidade=(hist.valor-acao.valor_pago)/acao.valor_pago)
            # db.session.add(hist_op)
            db.session.add(hist)            
            db.session.delete(acao)
            db.session.commit()

        elif quantidade < acao.quantidade:
            hist = Historico(usuario_id=self.id, 
                             ticker=ticker, 
                             preco=preco_venda, 
                             quantidade=quantidade, 
                             valor=preco_venda*quantidade, 
                             descricao=descricao,
                             tipo="venda",
                             data=data)
            acao.quantidade = acao.quantidade - quantidade
            acao.valor_pago = acao.preco_medio *acao.quantidade
            db.session.add(hist)
            db.session.commit()
        print(f'ticker: {ticker}, quantidade: {quantidade}, data: {data}, preco venda: {preco_venda}')

    def atualizaDividendos(self):
        print("Atualiza Dividendos")
        acoes = Acao.query.filter_by(usuario_id=self.id)
        for acao in acoes:
            ativo = yf.Ticker(acao.ticker+".SA")
            dividend_info = ativo.dividends
            print(type(acao.data_ultimo_dividendo))
            print(acao.data_ultimo_dividendo)
            data_ultimo_div_organizada = datetime.strptime(dividend_info.index[-1].strftime("%Y-%m-%d"), "%Y-%m-%d").date()
            if acao.data_ultimo_dividendo == data_ultimo_div_organizada:
                print(f"Não tem dividendos a atualizar! Data do último dividendo: {data_ultimo_div_organizada}")
            else:
                print("Tem dividendos a atualizar")
                if acao.data_ultimo_dividendo == None:
                    acao.data_ultimo_dividendo = acao.data_compra_inicial
                    print("aqui")
                print(f"Ticker: {acao.ticker}")
                data_partida = acao.data_ultimo_dividendo
                data_partida_formatada = data_partida.strftime("%Y-%m-%d")
                filtered_dividends = dividend_info[dividend_info.index > data_partida_formatada]
                if not filtered_dividends.empty:
                    acao.data_ultimo_dividendo = filtered_dividends.index[-1]
                    count = -1
                    for i in filtered_dividends:
                        dividendo = round(dividend_info.iloc[count], 4)
                        data_div = dividend_info.index[count]
                        data_div_organizada = datetime.strptime(data_div.strftime("%Y-%m-%d"), "%Y-%m-%d").date()
                        print(data_div_organizada)
                        cash_yield = round((dividendo/acao.preco_medio)*100, 2)
                        count = count - 1
                        valor = round(dividendo*acao.quantidade,2)
                        novo_dividendo = HistDividendos(usuario_id=self.id, 
                                                        ticker=acao.ticker, 
                                                        quantidade=acao.quantidade, 
                                                        valor_por_acao=dividendo, 
                                                        valor=valor, 
                                                        data=data_div_organizada, 
                                                        cash_yield=cash_yield)
                        db.session.add(novo_dividendo)
                    db.session.commit()
                    print('Funcionou')
            qry_sum_div = db.session.query(func.sum(HistDividendos.valor).label("valor")).filter_by(usuario_id=self.id).filter_by(ticker=acao.ticker)
            soma_div = qry_sum_div.first()
            acao.total_dividendos = round(soma_div[0] if soma_div[0] is not None else 0, 2)
            print(acao.total_dividendos)
            print(acao.valor_pago)
            print(acao.total_dividendos)
            acao.retorno_dividendos = round((acao.total_dividendos/acao.valor_pago)*100, 2)
        carteira = Carteira.query.filter_by(usuario_id=self.id).first()
        qry_sum = db.session.query(func.sum(HistDividendos.valor).label("valor")).filter_by(usuario_id=self.id)
        valores = qry_sum.first()
        carteira.total_dividendos = round(valores[0],2)
        carteira.retorno_dividendos = round((carteira.total_dividendos/carteira.valor_pago)*100, 2)
        db.session.commit()
        flash('Dividendos Atualizados', category="success")

    def addDividendosAcao(self, ticker, quantidade, data, preco_pago):
        ativo = yf.Ticker(ticker+".SA")
        dividend_info = ativo.dividends
        data_formatada = data.strftime("%Y-%m-%d")
        filtered_dividends = dividend_info[dividend_info.index >= data_formatada]
        count = -1
        total_dividendos = 0
        data_ultimo_provento = dividend_info.index[-1]
        # data_ultimo_provento_organizada = data_ultimo_provento.strptime("%Y-%m-%d")
        if not filtered_dividends.empty:
            for i in filtered_dividends:
                dividendo = round(dividend_info.iloc[count], 4)
                total_dividendos = round(total_dividendos + dividendo, 2)
                data_div = dividend_info.index[count]
                data_div_organizada = datetime.strptime(data_div.strftime("%Y-%m-%d"), "%Y-%m-%d").date()
                cash_yield = round((dividendo/preco_pago)*100, 2)
                count = count - 1
                valor = round(dividendo*quantidade,2)
                novo_dividendo = HistDividendos(usuario_id=self.id, 
                                                ticker=ticker, 
                                                quantidade=quantidade, 
                                                valor_por_acao=dividendo, 
                                                valor=valor, 
                                                data=data_div_organizada, 
                                                cash_yield=cash_yield)
                db.session.add(novo_dividendo)
                db.session.commit()
                print('Sucesso')
            return data_ultimo_provento

    def addDividendosCompraAcao(self, ticker, quantidade, data, preco_medio):
        ativo = yf.Ticker(ticker+".SA")
        dividend_info = ativo.dividends
        data_formatada = data.strftime("%Y-%m-%d")
        filtered_dividends = dividend_info[dividend_info.index >= data_formatada]
        count = -1
        total_dividendos = 0
        if not filtered_dividends.empty:
            for i in filtered_dividends:
                dividendo = round(dividend_info.iloc[count], 4)
                total_dividendos = round(dividendo + total_dividendos, 2)
                data_div = dividend_info.index[count]
                hist_div = HistDividendos.query.filter_by(usuario_id=self.id).filter_by(ticker=ticker).filter_by(data=data_div).first()
                hist_div.valor = round(hist_div.valor_por_acao * quantidade, 2)
                hist_div.quantidade = quantidade
                hist_div.cash_yield = round((hist_div.valor_por_acao/preco_medio)*100, 2)
                count = count - 1
                db.session.commit()
        
    def ajustaAcao(self, tipo, ticker, proporcao):
        acao = Acao.query.filter_by(usuario_id=self.id).filter_by(ticker=ticker).first()
        if tipo == "desdobramento":
            acao.quantidade = acao.quantidade*proporcao
            acao.preco_medio = round(acao.preco_medio/proporcao, 2)
        elif tipo == "grupamento":
            acao.quantidade = round(acao.quantidade/proporcao, 0)
            acao.preco_medio = round(acao.preco_medio * proporcao, 2)
        db.session.commit()
        flash(f"O {tipo} foi feito em {acao.ticker}")

class Carteira(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    valor_pago = db.Column(db.Float, default=0.0)
    valor_atual = db.Column(db.Float, default=0.0)
    lucro_prejuizo = db.Column(db.Float, default=0.0)
    rentabilidade = db.Column(db.Float, default=0.0)
    total_dividendos = db.Column(db.Float, default=0.0)
    retorno_dividendos = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(8), default="zero")

class Acao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    ticker = db.Column(db.String(10))
    preco_medio = db.Column(db.Float)
    quantidade = db.Column(db.Integer)
    valor_pago = db.Column(db.Float)
    data_compra_inicial = db.Column(db.Date)
    preco_atual = db.Column(db.Float)
    valor_atual = db.Column(db.Float)
    peso = db.Column(db.Float)
    lucro_prejuizo = db.Column(db.Float)
    rentabilidade = db.Column(db.Float)
    status = db.Column(db.String(10))
    investidor10 = db.Column(db.String)
    trading_view = db.Column(db.String)
    total_dividendos = db.Column(db.Float, default=0.0)
    retorno_dividendos = db.Column(db.Float, default=0.0)
    data_ultimo_dividendo = db.Column(db.Date)
            
class CompraAcao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    ticker = db.Column(db.String(10))
    preco_pago = db.Column(db.Float)
    quantidade = db.Column(db.Integer)
    valor_pago = db.Column(db.Float)
    descricao = db.String(db.String)
    data_compra = db.Column(db.Date)
    data_ultimo_dividendo = db.Column(db.Date)

class Historico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    ticker = db.Column(db.String(10))
    preco = db.Column(db.Float)
    quantidade = db.Column(db.Integer)
    valor = db.Column(db.Float)
    descricao = db.Column(db.String)
    tipo = db.Column(db.String)
    data = db.Column(db.Date)

class HistOperacoes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    ticker = db.Column(db.String(10))
    preco_compra = db.Column(db.Float)
    quantidade_compra = db.Column(db.Integer)
    valor_compra = db.Column(db.Float)
    preco_venda = db.Column(db.Float)
    quantidade_venda = db.Column(db.Integer)
    lucro_prejuizo = db.Column(db.Float)
    rentabilidade = db.Column(db.Float)
    
class HistDividendos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    ticker = db.Column(db.String(10))
    quantidade = db.Column(db.Integer)
    valor_por_acao = db.Column(db.Float)
    valor = db.Column(db.Float)
    data = db.Column(db.Date)
    cash_yield = db.Column(db.Float)

class Cotacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'),nullable=False )
    ticker = db.Column(db.String(10))
    mercado = db.Column(db.String)

admin.add_view(ModelView(Usuario, db.session))
admin.add_view(ModelView(Carteira, db.session))
admin.add_view(ModelView(Acao, db.session))
admin.add_view(ModelView(CompraAcao, db.session))
admin.add_view(ModelView(Historico, db.session))
admin.add_view(ModelView(HistOperacoes, db.session))
admin.add_view(ModelView(HistDividendos, db.session))

