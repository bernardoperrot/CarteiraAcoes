from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, g, send_file
from flask_login import login_required, current_user
import json
from website import db
from .models import *
from datetime import datetime, timedelta
from sqlalchemy.sql import func
from sqlalchemy import desc
import yfinance as yf
import timeit


views = Blueprint('views',__name__)

@views.before_request
def before_request():
    dolar = yf.Ticker("USDBRL=X")
    ibov = yf.Ticker("^BVSP")
    btc = yf.Ticker("BTC-USD")
    g.cotacao_dolar_abertura = round(dolar.history(period="1d")['Open'].iloc[0], 3)
    g.cotacao_ibov_abertura = round(ibov.history(period="1d")['Open'].iloc[0], 2)
    g.cotacao_btc_abertura = round(btc.history(period="1d")['Open'].iloc[0], 2)
    g.cotacao_dolar = round(dolar.history(period='1d')['Close'].iloc[0], 3)
    g.cotacao_ibov = round(ibov.history(period='1d')['Close'].iloc[0], 2)
    g.cotacao_btc= round(btc.history(period='1d')['Close'].iloc[0], 2)
    g.dif_dolar = round(((g.cotacao_dolar-g.cotacao_dolar_abertura)/g.cotacao_dolar_abertura)*100, 3)
    g.dif_ibov = round(((g.cotacao_ibov-g.cotacao_ibov_abertura)/g.cotacao_ibov_abertura)*100,2)
    g.dif_btc = round(((g.cotacao_btc-g.cotacao_btc_abertura)/g.cotacao_btc_abertura)*100, 2)
    print(f'IBOV: {g.cotacao_ibov}')
    print(f'Dolar: {g.cotacao_dolar}')
    print(g.cotacao_dolar_abertura)

#HOME
@views.route('/')
@login_required
def home():
    carteira_acoes = CarteiraAcoes.query.filter_by(usuario_id = current_user.id).first()
    carteira_criptos = CarteiraCripto.query.filter_by(usuario_id = current_user.id).first()
    total_acoes = round(carteira_acoes.valor_atual_total, 2)
    total_dividendos = round(carteira_acoes.total_dividendos, 2)
    total_cripto = round(carteira_criptos.valor_atual_total, 2)
    total_cripto_real = round(total_cripto * g.cotacao_dolar, 2)
    carteira_stock = CarteiraStock.query.filter_by(usuario_id=current_user.id).first()
    total_carteira_stock = round(carteira_stock.valor_atual_total, 2)
    total_carteira_stock_real = round(total_carteira_stock*g.cotacao_dolar)
    total = round(total_acoes+total_cripto_real+total_carteira_stock_real, 2)
    return render_template("home.html", usuario=current_user, total_carteira_stock=total_carteira_stock, total=total, total_cripto_real=total_cripto_real, total_acoes=total_acoes, total_dividendos=total_dividendos, total_cripto=total_cripto)


#ACAO
@views.route('/watch-list', methods=['GET', 'POST'])
@login_required
def watch_list():
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        codigo = codigo.upper()
        watch_list = WatchList.query.filter_by(usuario_id=current_user.id).filter_by(ticker=codigo).first()
        #print(watch_list)
        if watch_list:
            flash(f"{codigo} já está na sua watch list!", category="error")
        else:
            link_trading_view = "https://www.tradingview.com/symbols/BMFBOVESPA-"+codigo+"/"
            link_investidor10 = "https://investidor10.com.br/acoes/"+codigo+"/"
            ticker = codigo+".SA"
            acao = yf.Ticker(ticker)
            preco = round(acao.history(period='1d')['Close'].iloc[0], 2)
            preco_abertura = round(acao.history(period='1d')['Open'].iloc[0], 2)
            dif_por = round(((preco-preco_abertura)/preco_abertura)*100, 2)
            novo_item = WatchList(ticker=codigo, preco=preco, preco_abertura=preco_abertura, dif_por=dif_por, link_trading_view=link_trading_view, link_investidor10=link_investidor10, usuario_id=current_user.id)
            db.session.add(novo_item)
            db.session.commit()
            flash(f"{codigo} adicionado a sua watch list!", category="success")
    
    # watch_list = WatchList.query.filter_by(usuario_id=current_user.id)
    # db.session.delete(watchList)
    watch_list_ordenada = WatchList.query.filter_by(usuario_id=current_user.id).order_by(WatchList.ticker)
    return render_template('acao/watch-list.html', usuario=current_user, watch_list_ordenada=watch_list_ordenada)

@views.route('/atualiza-watch-list', methods=['GET','POST'])
@login_required
def atualizacao_watch_list():
    tempo_inicial = timeit.default_timer()
    watch_list = WatchList.query.filter_by(usuario_id=current_user.id)
    for acao in watch_list:
        ativo = yf.Ticker(acao.ticker+".SA")
        acao.preco = round(ativo.history(period='1d')['Close'].iloc[0], 2)
        acao.preco_abertura = round(ativo.history(period='1d')['Open'].iloc[0], 2)
        acao.dif_por = round(((acao.preco-acao.preco_abertura)/acao.preco_abertura)*100, 2)
        db.session.commit()
    tempo_final = timeit.default_timer()
    tempo = round(tempo_final-tempo_inicial, 2)
    flash(f"Valores atualizados em {tempo} segundos", category='success')
    return redirect(url_for('views.watch_list'))
        

@views.route('/remove-watch-list', methods = ['POST'])
@login_required
def remover_watch_list():
    data = json.loads(request.data)
    watch_list_id = data["watchlistId"]
    watch_list = Acao.query.get(watch_list_id)
    if watch_list:
        if watch_list.usuario_id == current_user.id:
            db.session.delete(watch_list)
            db.session.commit()
            flash("Ação removida da carteira!", category='success')
    return jsonify({})

#TABELA AÇÃO
@views.route('/acoes', methods= ['GET','POST'])
@login_required
def acoes():
    acoes = Acao.query.filter_by(usuario_id=current_user.id).order_by(desc(Acao.peso))
    dividendos = Acao.query.filter_by(usuario_id=current_user.id).filter(Acao.last_dividend!=0).order_by(desc(Acao.total_dividends))
    return render_template('acao/acoes.html', usuario = current_user, acoes=acoes, dividendos = dividendos)

#CRIA AÇÃO
@views.route('/add-acao', methods= ['GET', 'POST'])
@login_required
def add_acao():
    if request.method == 'POST':
        codigo = request.form.get('ticker')
        preco_pago = float(request.form.get('preco_pago'))
        quantidade = int(request.form.get('quantidade'))
        data_compra_str = request.form.get('dataCompra')
        descricao = request.form.get('descricao')
        codigo = codigo.upper()
        link = "https://www.tradingview.com/symbols/BMFBOVESPA-"+codigo+"/"
        ticker = codigo+".SA"
        ativo = Acao.query.filter_by(ticker=codigo).filter_by(usuario_id=current_user.id).first()
        if ativo:
            #CASO TENHA A ACAO
            # RECEBE O TICKER
            acao = yf.Ticker(ticker)
            # PRECO ATUAL
            preco_atual = round(acao.history(period='1d')['Close'].iloc[0], 2)
            # VALORES PARA A ACAO
            # VALOR PAGO
            valor_pago = round(preco_pago*quantidade, 2)
            
            # RECEBE A QUANTIDADE DA NOVA COMPRA
            ativo.quantidade = ativo.quantidade + quantidade
            # PRECO MEDIO
            ativo.preco_medio = round((ativo.valor_pago+valor_pago)/(ativo.quantidade), 2)
            ativo.valor_pago = round(ativo.valor_pago + valor_pago, 2)
            # VALOR ATUAL
            ativo.valor_atual = round(preco_atual*ativo.quantidade, 2)
            #LUCRO / PREJUIZO
            ativo.lucro_prejuizo = round(ativo.valor_atual - ativo.valor_pago, 2)
            # RENTABILIDADE
            ativo.rentabilidade = round(ativo.lucro_prejuizo/ativo.valor_pago*100, 2)
            # COR
            if ativo.rentabilidade > 0:
                ativo.status = "lucro"
            elif ativo.rentabilidade == 0:
                ativo.status = "zero"
            else:
                ativo.status = "prejuizo"
            db.session.commit()
            # VALORES PARA COMPRAACAO
            # VALOR ATUAL
            valor_atual = round(preco_atual*quantidade, 2)
            # LUCRO / PREJUIZO
            lucro_prejuizo = round(valor_atual-valor_pago, 2)
            # RENTABILIDADE
            rentabilidade = round(lucro_prejuizo/valor_pago*100, 2)
            # DATA COMPRA
            data_compra = datetime.strptime(data_compra_str, '%Y-%m-%d')
            # COR
            if rentabilidade > 0:
                status = "lucro"
            elif rentabilidade == 0:
                status = "zero"
            else:
                status = "prejuizo"
            # INSERINDO NOVA ACAO NO DB
            nova_compra = CompraAcao(ticker = codigo, preco_pago = preco_pago, quantidade = quantidade, valor_pago = valor_pago, preco_atual = preco_atual, valor_atual= valor_atual,rentabilidade= rentabilidade, lucro_prejuizo=lucro_prejuizo, data_compra = data_compra, status = status, usuario_id = current_user.id, link=link)
            # INSERINDO NO HISTORICO
            hist_acao = HistAcao(usuario_id = current_user.id, ticker=codigo, descricao=descricao, quantidade=quantidade, preco = preco_pago, valor = valor_pago, tipo = "compra", data = data_compra)
            db.session.add(nova_compra)
            db.session.add(hist_acao)
            db.session.commit()
            flash(f"Mais {quantidade} acoes foram adicionadas a {ativo.ticker}")
            return redirect(url_for('views.add_acao'))
        else:
            #CASO NAO TENHA A ACAO
            link_investidor10 = "https://investidor10.com.br/acoes/"+codigo+"/"
            valor_pago = round(preco_pago*quantidade, 2)
            acao = yf.Ticker(ticker)
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
            nova_compra = CompraAcao(ticker = codigo, preco_pago = preco_pago, quantidade = quantidade, valor_pago = valor_pago, preco_atual = preco_atual, valor_atual= valor_atual,rentabilidade= rentabilidade, lucro_prejuizo=lucro_prejuizo, data_compra = data_compra, status = status, usuario_id = current_user.id, link=link)
            acao = Acao(ticker = codigo, preco_medio = preco_pago, quantidade = quantidade, valor_pago = valor_pago, preco_atual = preco_atual, valor_atual= valor_atual,rentabilidade = rentabilidade, lucro_prejuizo=lucro_prejuizo, data_compra_inicial = data_compra, status = status, usuario_id = current_user.id, link=link, link_investidor10=link_investidor10)
            hist_acao = HistAcao(usuario_id = current_user.id, ticker=codigo, descricao=descricao, quantidade=quantidade, preco = preco_pago, valor = valor_pago, tipo = "compra", data = data_compra)
            db.session.add(hist_acao)
            db.session.add(acao)
            db.session.add(nova_compra)
            db.session.commit()
            flash(f"{ticker} adicionada a carteira", category='success')
            return redirect(url_for('views.add_acao'))
        
    return render_template('acao/add_acao.html', usuario=current_user)

#REMOVE AÇÃO
@views.route('/remove-Acao', methods = ['POST'])
@login_required
def remover_acao():
    data = json.loads(request.data)
    acao_id = data["acaoId"]
    acao = Acao.query.get(acao_id)
    if acao:
        if acao.usuario_id == current_user.id:
            db.session.delete(acao)
            db.session.commit()
            flash("Ação removida da carteira!", category='success')
    return jsonify({})

#VENDE ACAO
@views.route('/rm-acao', methods=['POST','GET'])
@login_required
def rm_acao():
    #try:
    if request.method == 'POST':
        ticker = request.form.get('ticker_venda')
        preco = float(request.form.get('preco_venda'))
        quantidade = int(request.form.get('quantidade_venda'))
        descricao = request.form.get('descricao_venda')
        data_str = request.form.get('dataVenda')
        codigo = ticker.upper()
        data_venda = datetime.strptime(data_str, '%Y-%m-%d')
        qry_acao = Acao.query.filter_by(ticker=codigo).filter_by(usuario_id=current_user.id).first()
        qry_compraAcao = CompraAcao.query.filter_by(ticker=codigo).filter_by(usuario_id=current_user.id).first()
        print(qry_acao)
        if qry_acao:
            hist = HistAcao(usuario_id = current_user.id, ticker = codigo, descricao=descricao, preco= preco, quantidade=quantidade, valor = round(preco*quantidade, 2), tipo="venda", data = data_venda)
            db.session.add(hist)
            db.session.delete(qry_acao)
            db.session.delete(qry_compraAcao)
            db.session.commit()
            flash(f'{codigo} removida da carteira e adiconada ao histórico!', category="success")
        else: 
            flash("Ação ou quantidade não foram encontradas", category='error')
        
    #except:
    #    flash('Não foi possível!', category='error')
    return render_template('acao/rm_acao.html', usuario= current_user)

#ATUALIZA AÇÃO
@views.route('/atualiza-Acoes', methods = ['POST', 'GET'])
@login_required
def atualiza_acao():
    current_time = datetime.now()
    tempo_inicial = timeit.default_timer()
    acoes = Acao.query.filter_by(usuario_id=current_user.id)
    carteira = CarteiraAcoes.query.filter_by(usuario_id=current_user.id).first()
    for acao in acoes:
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
        acao.peso = round((acao.valor_atual/carteira.valor_atual_total)*100, 2)
        db.session.commit()
        print(f'Ação: {acao.ticker}, peso: {acao.peso}')
    qry = db.session.query(func.sum(Acao.valor_pago).label("valor_pago"),
                        func.sum(Acao.valor_atual).label("preco_atual")).filter_by(usuario_id=current_user.id)
    valores = qry.first()
    ValorPago = valores[0]
    ValorAtual = valores[1]
    carteira.valor_pago_total = round(ValorPago, 2)
    carteira.valor_atual_total = round(ValorAtual, 2)
    carteira.lucro_prejuizo = round(ValorAtual - ValorPago, 2)
    carteira.rentabilidade_total = round(carteira.lucro_prejuizo/ValorPago*100, 2)
    if carteira.rentabilidade_total > 0:
        carteira.status = "lucro"
    elif carteira.rentabilidade_total == 0:
        acao.status = "zero"
    else:
        carteira.status = "prejuizo"
    carteira.last_update = current_time
    db.session.commit()
    tempo_final = timeit.default_timer()
    tempo = round(tempo_final-tempo_inicial, 2)
    flash(f"Valores atualizados em {tempo} segundos", category='success')
    return redirect(url_for('views.acoes'))
    # except:
    #     flash("Não foi possível!", category="error")
    #     return redirect(url_for('views.acoes'))

#DIVIDENDOS
@views.route('/atualiza-Dividendos', methods = ['POST', 'GET'])
@login_required
def atualiza_dividendos():
    # try:
    tempo_inicial = timeit.default_timer()
    precoMedio = Acao.query.filter_by(usuario_id = current_user.id)
    for acao in precoMedio:
        compra_acoes = CompraAcao.query.filter_by(ticker=acao.ticker).filter_by(usuario_id = current_user.id)
        for compra in compra_acoes:
            print(f'Ação: {compra.ticker}, quantidade: {compra.quantidade}')
            ativo = yf.Ticker(compra.ticker+".SA")
            dividend_info = ativo.dividends
            data_compra_str = compra.data_compra.strftime("%Y-%m-%d")
            filtered_dividends = dividend_info[dividend_info.index >= data_compra_str]
            try:
                if filtered_dividends.iloc[-1] != 0:
                    compra.last_dividend = filtered_dividends.iloc[-1]
                    data_last_dividend = filtered_dividends.index[-1]
                    print(data_last_dividend)
                    print(compra.last_dividend)
                else:
                    compra.last_dividend = 0
            except:
                compra.last_dividend = 0
            total = 0
            count = -1  
            for i in filtered_dividends:
                dividend = dividend_info.iloc[count]
                data = dividend_info.index[count]
                print(f'R$ {dividend}')
                print(f'Data: {data}')
                print("=========")
                total = total + dividend
                count = count -1
            print(f'Total de dividendos por compra: {total*compra.quantidade}')   
            compra.total_dividends = round(total * compra.quantidade, 2)
            retorno = round(total * acao.quantidade, 2)
            compra.yield_total = round((retorno/compra.valor_pago) * 100, 2)
            db.session.commit()

        query = db.session.query(func.sum(CompraAcao.total_dividends).label("total_dividends")).filter_by(usuario_id=current_user.id).filter_by(ticker=acao.ticker)
        total_dividendos_acao= query.first()
        acao.total_dividends = round(total_dividendos_acao[0], 2)    
        query1 = db.session.query(func.sum(CompraAcao.last_dividend).label("total_dividends")).filter_by(usuario_id=current_user.id).filter_by(ticker=acao.ticker)
        print(f'Total de dividendos por {acao.ticker}: R$ {acao.total_dividends}')
        ultimo_dividendo = query1.first()
        acao.last_dividend = round(ultimo_dividendo[0]*acao.quantidade, 2)
        acao.yield_total = round((acao.total_dividends/acao.valor_pago)*100, 2)
        # data_last_dividend2 = data_last_dividend.strftime("%d/%m/%Y")
        acao.data_ultimo_provento = data_last_dividend
    qry = db.session.query(func.sum(CompraAcao.total_dividends).label("total_dividends")).filter_by(usuario_id=current_user.id)
    valores = qry.first()
    carteira = CarteiraAcoes.query.filter_by(usuario_id=current_user.id).first()
    TotalDividendos = valores[0]
    carteira.total_dividendos = round(TotalDividendos, 2)
    carteira.retorno_dividendos = round((TotalDividendos/carteira.valor_pago_total)*100, 2)
    db.session.commit()
    tempo_final = timeit.default_timer()
    tempo = round(tempo_final-tempo_inicial, 2)
    flash(f"Dividendos atualizados em {tempo} segundos", category='success')
    return redirect(url_for('views.acoes'))
    # except:
    #     flash("Não foi possível!", category="error")
    #     return redirect(url_for('views.acoes'))

#HIST_ACAO
@views.route("/hist-acao", methods=["GET","POST"])
@login_required
def hist_acao():
    hist = HistAcao.query.filter_by(usuario_id=current_user.id).order_by(desc(HistAcao.data))
    return render_template("acao/hist_acao.html", usuario=current_user, hist=hist)

@views.route("/view-dividendos", methods=["POST", "GET"])
@login_required
def view_div():
    codigo = None
    preco= None
    dividendos = []
    datas_dividendos = []
    yields = []
    link = None
    link_investidor10 = None
    preco_teto = None
    yield_total = None
    total = None
    margem = None
    data_atual = datetime.now()
    data_um_ano_atras = data_atual - timedelta(days=365)
    data_um_ano_atras_formatada = data_um_ano_atras.strftime("%Y-%m-%d")

    if request.method == 'POST':
        codigo = request.form.get('ticker')
        codigo = codigo.upper()
        link = "https://www.tradingview.com/symbols/BMFBOVESPA-"+codigo+"/"
        link_investidor10 = "https://investidor10.com.br/acoes/"+codigo+"/"
        ativo = yf.Ticker(codigo+".SA")
        # ativo = yf.Ticker(codigo)
        dividend_info = ativo.dividends
        filtered_dividends = dividend_info[dividend_info.index >= data_um_ano_atras_formatada]
        total = 0
        count = -1
        index = 0

        preco = round(ativo.history(period='1d')['Close'].iloc[0], 2)

        for i in filtered_dividends:
            dividend = dividend_info.iloc[count]
            dividendos.append(dividend)
            cash_yield = round((dividend/preco)*100, 3)
            yields.append(cash_yield)
            data = dividend_info.index[count]
            index = index + 1
            data_organizada = data.strftime("%d/%m/%Y")
            datas_dividendos.append(data_organizada)
            total = round(total + dividend, 4)
            count = count -1
        preco_teto = round(total*16.6, 3)
        yield_total = round((total/preco)*100, 3)
        margem = round(((preco_teto-preco)/preco_teto)*100, 2)

    return render_template("acao/view_div.html", usuario=current_user, codigo=codigo, link=link, link_investidor10=link_investidor10, preco=preco, dividendos=dividendos, datas_dividendos=datas_dividendos, yields=yields, preco_teto=preco_teto, yield_total=yield_total, total=total, margem=margem)


#CRIPTO

#CRYPTO
@views.route('/cryptos', methods = ['GET', 'POST'])
@login_required
def cryptos():
    criptos = Crypto.query.filter_by(usuario_id=current_user.id).order_by(desc(Crypto.peso))
    return render_template("cripto/crypto.html", usuario = current_user, criptos=criptos)

#REMOVE CRYPTO
@views.route('/remove-Crypto', methods = ['POST'])
@login_required
def remover_crypto():
    data = json.loads(request.data)
    crypto_id = data["cryptoId"]
    crypto = Crypto.query.get(crypto_id)
    if crypto:
        if crypto.usuario_id == current_user.id:
            ticker_excluido = crypto.ticker
            db.session.delete(crypto)
            db.session.commit()
            flash(f"Crypto {ticker_excluido} removida da carteira!", category='success')
    return jsonify({})

#ATUALIZAR CRYPTOS
@views.route('/atualiza-Crypto', methods = ['POST', 'GET'])
@login_required
def atualiza_crypto():
    current_time = datetime.now()
    try:
        tempo_inicial = timeit.default_timer()
        cryptos = Crypto.query.filter_by(usuario_id=current_user.id)
        carteira = CarteiraCripto.query.filter_by(usuario_id=current_user.id).first()
        for crypto in cryptos:
            ativo = yf.Ticker(crypto.ticker+"-USD")
            crypto.preco_atual = round(ativo.history(period='1d')['Close'].iloc[0], 3)
            crypto.valor_atual = round(crypto.preco_atual*crypto.quantidade, 2)
            crypto.lucro_prejuizo = round(crypto.valor_atual-crypto.valor_pago, 2)
            crypto.rentabilidade = round(crypto.lucro_prejuizo/crypto.valor_pago*100, 2)
            if crypto.rentabilidade > 0:
                crypto.status = "lucro"
            elif crypto.rentabilidade == 0:
                crypto.status = "zero"
            else:
                crypto.status = "prejuizo"
            crypto.peso = round((crypto.valor_atual/carteira.valor_atual_total)*100)
            db.session.commit()
        qry = db.session.query(func.sum(Crypto.valor_pago).label("valor_pago"),
                            func.sum(Crypto.valor_atual).label("preco_atual")).filter_by(usuario_id=current_user.id)
        valores = qry.first()
        carteira = CarteiraCripto.query.filter_by(usuario_id=current_user.id).first()
        ValorPago = valores[0]
        ValorAtual = valores[1]
        carteira.valor_pago_total = round(ValorPago, 2)
        carteira.valor_atual_total = round(ValorAtual, 2)
        carteira.lucro_prejuizo = round(ValorAtual - ValorPago, 2)
        carteira.rentabilidade_total = round(carteira.lucro_prejuizo/ValorPago*100, 2)
        if carteira.rentabilidade_total > 0:
            carteira.status = "lucro"
        elif carteira.rentabilidade_total == 0:
            carteira.status = "zero"
        else:
            carteira.status = "prejuizo"
        carteira.last_update = current_time
        db.session.commit()
        tempo_final = timeit.default_timer()
        tempo = round(tempo_final-tempo_inicial, 2)
        flash(f"Valores atualizados em {tempo} segundos", category='success')
        return redirect(url_for('views.cryptos'))          
    except:
        flash("Não foi possível", category='error')
        return redirect(url_for('views.cryptos'))
    
#HIST CRIPTOS
@views.route('/hist-cripto', methods=['POST', 'GET'])
@login_required
def hist_cripto():
    hist = HistCripto.query.filter_by(usuario_id=current_user.id).order_by(HistCripto.data)
    return render_template("cripto/hist_cripto.html", usuario=current_user)

#CRIAR CRIPTO
@views.route('add-cripto', methods=['GET','POST'])
@login_required
def add_cripto():
    try:
        if request.method == "POST":
            codigo = request.form.get('ticker_crypto')
            preco_pago = float(request.form.get('preco_pago_crypto'))
            quantidade = float(request.form.get('quantidade_crypto'))
            descricao = request.form.get('descricao_crypto')
            data_compra_str = request.form.get('dataCompra_crypto')
            codigo = codigo.upper()
            link = "https://www.tradingview.com/symbols/"+codigo+"USDT/"
            ticker = codigo+"-USD"
            ativo = Crypto.query.filter_by(ticker=codigo).filter_by(usuario_id=current_user.id).first()
            data_compra = datetime.strptime(data_compra_str, '%Y-%m-%d')
            print(ativo)
            if ativo:
                valor_pago = round(preco_pago*quantidade, 2)
                ativo.quantidade = ativo.quantidade + quantidade
                ativo.preco_pago = round((ativo.valor_pago+valor_pago)/(ativo.quantidade), 3)
                ativo.valor_pago = round(ativo.valor_pago+valor_pago , 2)
                ativo.valor_atual = round(ativo.preco_atual*ativo.quantidade, 2)
                ativo.lucro_prejuizo = round(ativo.valor_atual - ativo.valor_pago, 2)
                ativo.rentabilidade = round(ativo.lucro_prejuizo/ativo.valor_pago*100, 2)
                if ativo.rentabilidade > 0:
                    ativo.status = "lucro"
                elif ativo.rentabilidade == 0:
                    ativo.status = "zero"
                else:
                    ativo.status = "prejuizo"
                db.session.commit()
                flash(f"Mais {quantidade} criptos foram adicionadas a {ativo.ticker}")
                hist = HistCripto(usuario_id=current_user.id, ticker = codigo, descricao=descricao, preco = preco_pago, quantidade=quantidade, valor=preco_pago*quantidade, tipo="compra", data=data_compra)
                db.session.add(hist)
                db.session.commit()
            else:
                valor_pago = round(preco_pago*quantidade, 2)
                acao = yf.Ticker(ticker)
                preco_atual = round(acao.history(period='1d')['Close'][0], 5)
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
                hist = HistCripto(usuario_id=current_user.id, ticker = codigo, descricao=descricao, preco = preco_pago, quantidade=quantidade, valor=preco_pago*quantidade, tipo="compra", data=data_compra)
                nova_crypto = Crypto(ticker = codigo, preco_pago = preco_pago, quantidade = quantidade, valor_pago = valor_pago, preco_atual = preco_atual, valor_atual= valor_atual,rentabilidade= rentabilidade, lucro_prejuizo=lucro_prejuizo, data_compra = data_compra, status = status, usuario_id = current_user.id, link = link)
                db.session.add(hist)
                db.session.add(nova_crypto)
                db.session.commit()
                
                flash(f"{ticker} adicionada a carteira", category='success')
                return redirect(url_for('views.cryptos'))
            
    except:
        flash("Não foi possível!", category="error")
    return render_template("cripto/add_cripto.html", usuario = current_user)

#REMOVE CRIPTO
@views.route('/rm-cripto', methods= ['GET', 'POST'])
@login_required
def rm_cripto():
    try:
        if request.method == 'POST':
            ticker = request.form.get('ticker_venda')
            preco = float(request.form.get('preco_venda'))
            quantidade = int(request.form.get('quantidade_venda'))
            descricao = request.form.get('descricao_venda')
            data_str = request.form.get('dataVenda')    
            codigo = ticker.upper()
            data_venda = datetime.strptime(data_str, '%Y-%m-%d')
            qry = Crypto.query.filter_by(ticker=codigo).filter_by(usuario_id=current_user.id).first()
            if qry:
                qry.valor_pago = qry.valor_pago-(quantidade*qry.preco_pago)
                qry.quantidade = qry.quantidade-quantidade
                hist = HistCripto(usuario_id = current_user.id, ticker = codigo, descricao=descricao, preco= preco, quantidade=quantidade, valor = preco*quantidade, tipo="venda", data = data_venda)
                db.session.add(hist)
                db.session.commit()
                flash(f'{codigo} removida da carteira e adiconada ao histórico!', category="success")
            else: 
                flash("Cripto ou quantidade não foram encontradas", category='error')
        
    except:
        flash('Não foi possível!', category='error')
    return render_template('cripto/rm_cripto.html', usuario = current_user)

@views.route('/stock', methods= ['GET','POST'])
@login_required
def stock():
    acoes = Stock.query.filter_by(usuario_id=current_user.id).order_by(desc(Stock.peso))
    dividendos = Stock.query.filter_by(usuario_id=current_user.id).filter(Stock.last_dividend!=0).order_by(desc(Stock.total_dividends))
    return render_template('stock/stock.html', usuario = current_user, acoes=acoes, dividendos = dividendos)

#CRIA AÇÃO
@views.route('/add-stock', methods= ['GET', 'POST'])
@login_required
def add_stock():
    if request.method == 'POST':
        codigo = request.form.get('ticker')
        preco_pago = float(request.form.get('preco_pago'))
        quantidade = int(request.form.get('quantidade'))
        data_compra_str = request.form.get('dataCompra')
        descricao = request.form.get('descricao')
        codigo= codigo.upper()
        ticker = codigo
        ativo = Stock.query.filter_by(ticker=codigo).filter_by(usuario_id=current_user.id).first()
        if ativo:
            #CASO TENHA A ACAO
            # RECEBE O TICKER
            acao = yf.Ticker(ticker)
            # PRECO ATUAL
            preco_atual = round(acao.history(period='1d')['Close'].iloc[0], 2)
            # VALORES PARA A ACAO
            # VALOR PAGO
            valor_pago = round(preco_pago*quantidade, 2)
            
            # RECEBE A QUANTIDADE DA NOVA COMPRA
            ativo.quantidade = ativo.quantidade + quantidade
            # PRECO MEDIO
            ativo.preco_medio = round((ativo.valor_pago+valor_pago)/(ativo.quantidade), 2)
            ativo.valor_pago = round(ativo.valor_pago + valor_pago, 2)
            # VALOR ATUAL
            ativo.valor_atual = round(preco_atual*ativo.quantidade, 2)
            #LUCRO / PREJUIZO
            ativo.lucro_prejuizo = round(ativo.valor_atual - ativo.valor_pago, 2)
            # RENTABILIDADE
            ativo.rentabilidade = round(ativo.lucro_prejuizo/ativo.valor_pago*100, 2)
            # COR
            if ativo.rentabilidade > 0:
                ativo.status = "lucro"
            elif ativo.rentabilidade == 0:
                ativo.status = "zero"
            else:
                ativo.status = "prejuizo"
            db.session.commit()
            # VALORES PARA COMPRAACAO
            # VALOR ATUAL
            valor_atual = round(preco_atual*quantidade, 2)
            # LUCRO / PREJUIZO
            lucro_prejuizo = round(valor_atual-valor_pago, 2)
            # RENTABILIDADE
            rentabilidade = round(lucro_prejuizo/valor_pago*100, 2)
            # DATA COMPRA
            data_compra = datetime.strptime(data_compra_str, '%Y-%m-%d')
            # COR
            if rentabilidade > 0:
                status = "lucro"
            elif rentabilidade == 0:
                status = "zero"
            else:
                status = "prejuizo"
            # INSERINDO NOVA ACAO NO DB
            nova_compra = CompraStock(ticker = codigo, preco_pago = preco_pago, quantidade = quantidade, valor_pago = valor_pago, preco_atual = preco_atual, valor_atual= valor_atual,rentabilidade= rentabilidade, lucro_prejuizo=lucro_prejuizo, data_compra = data_compra, status = status, usuario_id = current_user.id)
            # INSERINDO NO HISTORICO
            hist_acao = HistStock(usuario_id = current_user.id, ticker=codigo, descricao=descricao, quantidade=quantidade, preco = preco_pago, valor = valor_pago, tipo = "compra", data = data_compra)
            db.session.add(nova_compra)
            db.session.add(hist_acao)
            db.session.commit()
            flash(f"Mais {quantidade} stocks foram adicionadas a {ativo.ticker}")
            return redirect(url_for('views.add_stock'))
        else:
            #CASO NAO TENHA A ACAO
            valor_pago = round(preco_pago*quantidade, 2)
            acao = yf.Ticker(ticker)
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
            nova_compra = CompraStock(ticker = codigo, preco_pago = preco_pago, quantidade = quantidade, valor_pago = valor_pago, preco_atual = preco_atual, valor_atual= valor_atual,rentabilidade= rentabilidade, lucro_prejuizo=lucro_prejuizo, data_compra = data_compra, status = status, usuario_id = current_user.id)
            acao = Stock(ticker = codigo, preco_medio = preco_pago, quantidade = quantidade, valor_pago = valor_pago, preco_atual = preco_atual, valor_atual= valor_atual,rentabilidade = rentabilidade, lucro_prejuizo=lucro_prejuizo, data_compra_inicial = data_compra, status = status, usuario_id = current_user.id)
            hist_acao = HistStock(usuario_id = current_user.id, ticker=codigo, descricao=descricao, quantidade=quantidade, preco = preco_pago, valor = valor_pago, tipo = "compra", data = data_compra)
            db.session.add(hist_acao)
            db.session.add(acao)
            db.session.add(nova_compra)
            db.session.commit()
            flash(f"{ticker} adicionada a carteira", category='success')
            return redirect(url_for('views.add_stock'))
        
    return render_template('stock/add_stock.html', usuario=current_user)

#VENDE ACAO
@views.route('/rm-stock', methods=['POST','GET'])
@login_required
def rm_stock():
    #try:
    if request.method == 'POST':
        ticker = request.form.get('ticker_venda')
        preco = float(request.form.get('preco_venda'))
        quantidade = int(request.form.get('quantidade_venda'))
        descricao = request.form.get('descricao_venda')
        data_str = request.form.get('dataVenda')
        codigo = ticker.upper()
        data_venda = datetime.strptime(data_str, '%Y-%m-%d')
        qry_acao = Stock.query.filter_by(ticker=codigo).filter_by(usuario_id=current_user.id).first()
        qry_compraAcao = CompraStock.query.filter_by(ticker=codigo).filter_by(usuario_id=current_user.id).first()
        print(qry_acao)
        if qry_acao:
            hist = HistStock(usuario_id = current_user.id, ticker = codigo, descricao=descricao, preco= preco, quantidade=quantidade, valor = round(preco*quantidade, 2), tipo="venda", data = data_venda)
            db.session.add(hist)
            db.session.delete(qry_acao)
            db.session.delete(qry_compraAcao)
            db.session.commit()
            flash(f'{codigo} removida da carteira e adiconada ao histórico!', category="success")
        else: 
            flash("Ação ou quantidade não foram encontradas", category='error')
        
    #except:
    #    flash('Não foi possível!', category='error')
    return render_template('acao/rm_acao.html', usuario= current_user)

#ATUALIZA AÇÃO
@views.route('/atualiza-stock', methods = ['POST', 'GET'])
@login_required
def atualiza_stock():
    current_time = datetime.now()
    tempo_inicial = timeit.default_timer()
    acoes = Stock.query.filter_by(usuario_id=current_user.id)
    carteira = CarteiraStock.query.filter_by(usuario_id=current_user.id).first()
    for acao in acoes:
        ativo = yf.Ticker(acao.ticker)
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
        acao.peso = round((acao.valor_atual/carteira.valor_atual_total)*100, 2)
        db.session.commit()
        print(f'Ação: {acao.ticker}, peso: {acao.peso}')
    qry = db.session.query(func.sum(Stock.valor_pago).label("valor_pago"),
                        func.sum(Stock.valor_atual).label("preco_atual")).filter_by(usuario_id=current_user.id)
    valores = qry.first()
    ValorPago = valores[0]
    ValorAtual = valores[1]
    carteira.valor_pago_total = round(ValorPago, 2)
    carteira.valor_atual_total = round(ValorAtual, 2)
    carteira.lucro_prejuizo = round(ValorAtual - ValorPago, 2)
    carteira.rentabilidade_total = round(carteira.lucro_prejuizo/ValorPago*100, 2)
    if carteira.rentabilidade_total > 0:
        carteira.status = "lucro"
    elif carteira.rentabilidade_total == 0:
        acao.status = "zero"
    else:
        carteira.status = "prejuizo"
    carteira.last_update = current_time
    db.session.commit()
    tempo_final = timeit.default_timer()
    tempo = round(tempo_final-tempo_inicial, 2)
    flash(f"Valores atualizados em {tempo} segundos", category='success')
    return redirect(url_for('views.stock'))

#DIVIDENDOS
@views.route('/atualiza-Dividend', methods = ['POST', 'GET'])
@login_required
def atualiza_dividends():
    # try:
    tempo_inicial = timeit.default_timer()
    precoMedio = Stock.query.filter_by(usuario_id = current_user.id)
    for acao in precoMedio:
        compra_acoes = CompraStock.query.filter_by(ticker=acao.ticker).filter_by(usuario_id = current_user.id)
        for compra in compra_acoes:
            print(f'Ação: {compra.ticker}, quantidade: {compra.quantidade}')
            ativo = yf.Ticker(compra.ticker+".SA")
            dividend_info = ativo.dividends
            data_compra_str = compra.data_compra.strftime("%Y-%m-%d")
            filtered_dividends = dividend_info[dividend_info.index >= data_compra_str]
            try:
                if filtered_dividends.iloc[-1] != 0:
                    compra.last_dividend = filtered_dividends.iloc[-1]
                    data_last_dividend = filtered_dividends.index[-1]
                    print(compra.last_dividend)
                else:
                    compra.last_dividend = 0
            except:
                compra.last_dividend = 0
            total = 0
            count = -1  
            for i in filtered_dividends:
                dividend = dividend_info.iloc[count]
                data = dividend_info.index[count]
                print(f'R$ {dividend}')
                print(f'Data: {data}')
                print("=========")
                total = total + dividend
                count = count -1
            print(f'Total de dividendos por compra: {total*compra.quantidade}')   
            compra.total_dividends = round(total * compra.quantidade, 2)
            retorno = round(total * acao.quantidade, 2)
            compra.yield_total = round((retorno/compra.valor_pago) * 100, 2)
            db.session.commit()

        query = db.session.query(func.sum(CompraStock.total_dividends).label("total_dividends")).filter_by(usuario_id=current_user.id).filter_by(ticker=acao.ticker)
        total_dividendos_acao= query.first()
        acao.total_dividends = round(total_dividendos_acao[0], 2)    
        query1 = db.session.query(func.sum(CompraStock.last_dividend).label("total_dividends")).filter_by(usuario_id=current_user.id).filter_by(ticker=acao.ticker)
        print(f'Total de dividendos por {acao.ticker}: R$ {acao.total_dividends}')
        ultimo_dividendo = query1.first()
        acao.last_dividend = round(ultimo_dividendo[0]*acao.quantidade, 2)
        acao.yield_total = round((acao.total_dividends/acao.valor_pago)*100, 2)
        acao.data_ultimo_provento = data_last_dividend
    qry = db.session.query(func.sum(CompraStock.total_dividends).label("total_dividends")).filter_by(usuario_id=current_user.id)
    valores = qry.first()
    carteira = CarteiraStock.query.filter_by(usuario_id=current_user.id).first()
    TotalDividendos = valores[0]
    carteira.total_dividendos = round(TotalDividendos, 2)
    carteira.retorno_dividendos = round((TotalDividendos/carteira.valor_pago_total)*100, 2)
    db.session.commit()
    tempo_final = timeit.default_timer()
    tempo = round(tempo_final-tempo_inicial, 2)
    flash(f"Dividendos atualizados em {tempo} segundos", category='success')
    return redirect(url_for('views.stock'))

#HIST_ACAO
@views.route("/hist-stock", methods=["GET","POST"])
@login_required
def hist_stock():
    hist = HistStock.query.filter_by(usuario_id=current_user.id).order_by(desc(HistStock.data))
    return render_template("stock/hist_stock.html", usuario=current_user, hist=hist)