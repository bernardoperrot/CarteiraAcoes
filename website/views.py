from flask import Blueprint, render_template, request, send_file
from sqlalchemy import desc
from flask_login import login_required, current_user
from .models import *
import timeit
from datetime import datetime, timedelta
import json
import pandas as pd

views = Blueprint('views',__name__)

#HOME
@views.route('/')
@login_required
def home():
    dolar = yf.Ticker("USDBRL=X")
    ibov = yf.Ticker("^BVSP")
    btc = yf.Ticker("BTC-USD")
    cotacao_dolar_abertura = round(dolar.history(period="1d")['Open'].iloc[0], 3)
    cotacao_ibov_abertura = round(ibov.history(period="1d")['Open'].iloc[0], 2)
    cotacao_btc_abertura = round(btc.history(period="1d")['Open'].iloc[0], 2)
    cotacao_dolar = round(dolar.history(period='1d')['Close'].iloc[0], 3)
    cotacao_ibov = round(ibov.history(period='1d')['Close'].iloc[0], 2)
    cotacao_btc = round(btc.history(period='1d')['Close'].iloc[0], 2)
    dif_dolar = round(((cotacao_dolar-cotacao_dolar_abertura)/cotacao_dolar_abertura)*100, 3)
    dif_ibov = round(((cotacao_ibov-cotacao_ibov_abertura)/cotacao_ibov_abertura)*100,2)
    dif_btc = round(((cotacao_btc-cotacao_btc_abertura)/cotacao_btc_abertura)*100, 2)
    print(f'IBOV: {cotacao_ibov}')
    print(f'Dolar: {cotacao_dolar}')
    print(cotacao_dolar_abertura)
    total_carteira = Carteira.query.filter_by(usuario_id=current_user.id).first()
    return render_template("home.html", usuario=current_user, 
                           total_carteira=total_carteira,
                           cotacao_dolar=cotacao_dolar,
                           cotacao_ibov=cotacao_ibov,
                           cotacao_btc=cotacao_btc,
                           dif_dolar=dif_dolar,
                           dif_ibov=dif_ibov,
                           dif_btc=dif_btc
                           )

@views.route('/carteira', methods=["GET","POST"])
@login_required
def carteira():
    acoes = Acao.query.filter_by(usuario_id=current_user.id).order_by(desc(Acao.peso))
    carteira = Carteira.query.filter_by(usuario_id=current_user.id).first()
    dividendos = Acao.query.filter_by(usuario_id=current_user.id).order_by(desc(Acao.total_dividendos)).filter(Acao.total_dividendos!=0)

    lista_acoes = []
    for acao in acoes:
        lista_acoes.append(acao)

    return render_template("Carteira/carteira.html",
                            usuario=current_user, 
                            acoes=acoes, 
                            carteira=carteira, 
                            dividendos=dividendos)

@views.route('/add-acao', methods=["GET","POST"])
@login_required
def add_acao():
    if request.method == "POST":
        ticker = request.form.get('ticker')
        preco_pago = float(request.form.get('preco_pago'))
        quantidade = int(request.form.get('quantidade'))
        data_compra_str = request.form.get('data_compra')
        descricao = request.form.get('descricao')
        Usuario.addAcao(current_user, ticker, preco_pago, quantidade, descricao, data_compra_str)
    return render_template("Carteira/add_acao.html", usuario=current_user)

@views.route('/rm-acao', methods=["GET","POST"])
@login_required
def rm_acao():
    if request.method == "POST":
        ticker = request.form.get('ticker')
        preco_venda = float(request.form.get('preco_venda'))
        quantidade = int(request.form.get('quantidade'))
        data_venda_str = request.form.get('data_venda')
        descricao = request.form.get('descricao')
        Usuario.removeAcao(current_user, ticker, preco_venda, quantidade, descricao, data_venda_str)
    return render_template("Carteira/remove_acao.html", usuario=current_user)

@views.route('/atualizar-carteira', methods=["GET","POST"])
@login_required
def atualizar_carteira():
    tempo_inicial = timeit.default_timer()
    Usuario.atualizarCarteira(current_user)
    tempo_final = timeit.default_timer()
    tempo = round(tempo_final-tempo_inicial, 2)
    flash(f"Valores atualizados em {tempo} segundos", category='success')
    return redirect(url_for('views.carteira'))

@views.route('/atualiza-dividendos', methods=['GET', 'POST'])
@login_required
def atualiza_dividendos():
    Usuario.atualizaDividendos(current_user)
    return redirect(url_for('views.carteira'))

@views.route('/hist-dividendos', methods=["GET","POST"])
@login_required
def dividendos():
    tickers = Acao.query.filter_by(usuario_id=current_user.id)
    acao = None
    carteira = None
    if request.method == 'POST':
        ticker_selecionado = request.form.get('ticker')
        dividendos = HistDividendos.query.filter_by(usuario_id=current_user.id, ticker=ticker_selecionado).all()
        acao = Acao.query.filter_by(usuario_id=current_user.id).filter_by(ticker=ticker_selecionado).first()
    else:    
        dividendos = HistDividendos.query.filter_by(usuario_id=current_user.id).order_by(desc(HistDividendos.data))
        carteira = Carteira.query.filter_by(usuario_id=current_user.id).first()
        
    return render_template('Carteira/dividendos.html', usuario=current_user, 
                           dividendos=dividendos, 
                           tickers=tickers, 
                           acao=acao, carteira=carteira)

@views.route('/historico', methods=['GET','POST'])
@login_required
def hist():
    # tickers = Historico.query.filter_by(usuario_id=current_user.id).distinct(Historico.ticker).all()
    tickers = db.session.query(Historico.ticker).filter_by(usuario_id=current_user.id).distinct().all()

    if request.method == 'POST':
        ticker_selecionado = request.form.get('ticker')
        ticker_selecionado = ticker_selecionado.upper()
        historico = Historico.query.filter_by(usuario_id=current_user.id).filter_by(ticker=ticker_selecionado).order_by(desc(Historico.data)) 
    else:
        historico = Historico.query.filter_by(usuario_id=current_user.id).order_by(desc(Historico.data))    

    return render_template('Carteira/historico.html',teste = 5, usuario=current_user, historico=historico, tickers=tickers)

@views.route('/preco-teto', methods=['GET','POST'])
@login_required
def preco_teto():
    anos = None
    ticker = None
    cotacao_ativo = None
    preco_teto = None
    total_dividendos = None
    cash_yield = None
    margem_seguranca = None
    link_grafico = None
    link_investidor10 = None
    cotacao_dolar = None
    preco_teto_dolar = None
    total_dividendos_dolar = None
    cash_yield_dolar = None
    margem_seguranca_dolar = None
    if request.method == 'POST':
        ticker = request.form.get('ticker')
        anos = int(request.form.get('anos'))
        dias = anos*365
        link_grafico = "https://www.tradingview.com/symbols/BMFBOVESPA-"+ticker+"/"
        link_investidor10 = "https://investidor10.com.br/acoes/"+ticker+"/"
        ticker = ticker.upper()
        ativo = yf.Ticker(ticker+".SA")
        dividend_info = ativo.dividends
        dolar = yf.Ticker("USDBRL=X")
        data_atual = datetime.now()
        data_um_ano_atras = data_atual - timedelta(days=dias)
        data_um_ano_atras_formatada = data_um_ano_atras.strftime("%Y-%m-%d")
        filtered_dividends = dividend_info[dividend_info.index >= data_um_ano_atras_formatada]
        total_dividendos_dolar = 0
        total_dividendos=0
        count = -1

        cotacao_ativo = round(ativo.history(period='1d')['Close'].iloc[0], 2)
        cotacao_dolar = round(dolar.history(period='1d')['Close'].iloc[0], 3)

        print('------------------')
        print(f'| Ticker: {ticker} |')
        print('------------------')

        for i in filtered_dividends:
            dividend_real = round(dividend_info.iloc[count], 4)
            total_dividendos = round(total_dividendos+dividend_real, 2)
            data = dividend_info.index[count]
            data_organizada = data.strftime("%d/%m/%Y")
            cotacao_data_dividendo = round(dolar.history(start=data, end=data)["Close"].iloc[0], 4)
            dividend_dolar = round(dividend_real/cotacao_data_dividendo, 4)
            total_dividendos_dolar = round(total_dividendos_dolar+dividend_dolar, 4)
            print(f'Cotação dolar na data do dividendo: ${cotacao_data_dividendo}')
            print(f'Dividendo em REAIS: R$ {dividend_real}')
            print(f'Dividendo em DOLAR: $ {dividend_dolar}')
            print(f'Data do dividendo: {data_organizada}')
            print("----------------------------------------")
            count = count-1
        total_dividendos = round(total_dividendos/anos, 3)
        total_dividendos_dolar = round(total_dividendos_dolar/anos, 3)
        cash_yield = round((total_dividendos/cotacao_ativo)*100, 2)
        preco_teto = round((total_dividendos*16.667), 2)
        if preco_teto < cotacao_ativo:
            margem_seguranca = round(((preco_teto-cotacao_ativo)/cotacao_ativo)*100, 2)
        else:
            margem_seguranca = round(((preco_teto-cotacao_ativo)/preco_teto)*100, 2)
        preco_teto_dolar = round((total_dividendos_dolar*16.667)*cotacao_dolar, 2)

        if preco_teto_dolar<cotacao_ativo:
            margem_seguranca_dolar = round(((preco_teto_dolar-cotacao_ativo)/cotacao_ativo)*100, 2)
        else:
            margem_seguranca_dolar = round(((preco_teto_dolar-cotacao_ativo)/preco_teto_dolar)*100)
        cash_yield_dolar = round(total_dividendos_dolar/(cotacao_ativo/cotacao_dolar)*100, 2)

        print(f'Total dividendos em DOLAR: $ {total_dividendos_dolar}')
        print(f'Preço teto em DOLAR: R$ {preco_teto_dolar}')
        


    return render_template('Bazin/bazin.html', 
                           usuario=current_user, 
                           ticker=ticker, 
                           cotacao_ativo=cotacao_ativo, 
                           cotacao_dolar=cotacao_dolar, 
                           total_dividendos=total_dividendos,
                           cash_yield=cash_yield,
                           preco_teto=preco_teto,
                           margem_seguranca=margem_seguranca, 
                           preco_teto_dolar=preco_teto_dolar, 
                           total_dividendos_dolar=total_dividendos_dolar, 
                           margem_seguranca_dolar=margem_seguranca_dolar, 
                           cash_yield_dolar=cash_yield_dolar,
                           link_grafico=link_grafico, link_investidor10=link_investidor10,
                           anos=anos
                           )

@views.route('/config', methods=['POST','GET'])
@login_required
def configuracao():
    tickers = Acao.query.filter_by(usuario_id=current_user.id)
    if request.method == "POST":
        tipo = request.form.get('tipo')
        ticker_selecionado = request.form.get('ticker')
        proporcao = int(request.form.get('proporcao'))
        Usuario.ajustaAcao(current_user, tipo, ticker_selecionado, proporcao)


    return render_template("Config/configuracoes.html", usuario=current_user, tickers=tickers)

@views.route('/cotacoes', methods=['POST','GET'])
@login_required
def cotacoes():
    tickers= Cotacao.query.filter_by(usuario_id=current_user.id)
    cotacoes_abertura = {}
    cotacoes = {}
    variacoes = {}
    for ativo in tickers:
        if ativo.mercado == "acao":
            dados_ticker = yf.Ticker(ativo.ticker+".SA")
        else:
            dados_ticker = yf.Ticker(ativo.ticker)
        historico = dados_ticker.history(period="2d")
        cotacao_atual = historico['Close'][-1]
        cotacao_fechamento = historico['Close'][-2]

        variacao = ((cotacao_atual - cotacao_fechamento)/ cotacao_fechamento)*100
        cotacoes[ativo.ticker] = round(cotacao_atual, 2)
        variacoes[ativo.ticker] = round(variacao, 2)
        print(cotacao_atual)
        print(cotacao_fechamento)
        print(variacao)

    if request.method == 'POST':
        ticker = request.form.get('ticker')
        ticker = ticker.upper()
        mercado = request.form.get('mercado')
        ativo_existente = Cotacao.query.filter_by(usuario_id=current_user.id, ticker=ticker).first()
        if ativo_existente:
            print("Esse ticker já está na lista")
        else:
            novo = Cotacao(ticker=ticker, mercado=mercado,usuario_id=current_user.id)
            db.session.add(novo)
            db.session.commit()
    return render_template('Cotacoes/cotacao.html', usuario=current_user, tickers=tickers, cotacoes=cotacoes, variacoes=variacoes)

@views.route('/exportar-excel')
@login_required
def exportar_para_excel():
    # Consulta todos os registros da tabela `Pessoas` para o usuário atual
    acoes = Acao.query.filter_by(usuario_id=current_user.id).all()
    
    # Criar uma lista de dicionários contendo os dados das pessoas
    dados = []
    for acao in acoes:
        dados.append({
            'Ticker': acao.ticker,
            'Preço médio': acao.preco_medio,
            'Quantidade': acao.quantidade,
            'Valor Pago': acao.valor_pago,
            'Data Compra': acao.data_compra_inicial,
            'Preço Atual': acao.preco_atual,
            'Valor Atual': acao.valor_atual,
            'Peso': acao.peso,
            'Lucro/ Prejuízo': acao.lucro_prejuizo,
            'Rentabiidade': acao.rentabilidade,
            'Total Dividendos': acao.total_dividendos,
            'Retorno Dividendos': acao.retorno_dividendos

        })
    
    # Converter a lista de dicionários em um DataFrame do pandas
    df = pd.DataFrame(dados)

    # Exportar o DataFrame para um arquivo Excel
    caminho_arquivo = '/home/bernardo/acoes.xlsx'
    df.to_excel(caminho_arquivo, index=False)  # Salva o arquivo sem a coluna de índices
    
    # Enviar o arquivo Excel como resposta para download
    return send_file(caminho_arquivo, as_attachment=True)
