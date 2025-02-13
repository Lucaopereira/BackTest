import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import date

st.title("Backtest de Carteira de Criptomoedas")

# Caixa para inserir as datas (usando um formulário)
with st.form("config_dates"):
    start_date = st.date_input("Data Inicial", value=date(2021, 1, 1))
    end_date = st.date_input("Data Final", value=date(2024, 12, 31))
    submit_button = st.form_submit_button("Processar Dados")

if submit_button:
    # Validação das datas
    if start_date >= end_date:
        st.error("A Data Inicial deve ser anterior à Data Final!")
        st.stop()

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    # Lista de criptomoedas
    cryptos = ['BTC-USD', 'XMR-USD', 'SOL-USD']

    # Baixa os dados históricos (preço de fechamento)
    data = {}
    for crypto in cryptos:
        df = yf.download(crypto, start=start_date_str, end=end_date_str)['Close']
        if not df.empty:
            data[crypto] = df

    if not data:
        st.error("Nenhum dado foi baixado para os ativos informados.")
        st.stop()

    # Combina os preços em um único DataFrame
    prices = pd.concat(data, axis=1)
    prices.columns = prices.columns.get_level_values(0)
    prices.dropna(inplace=True)
    if prices.empty:
        st.error("O DataFrame 'prices' ficou vazio após remover as linhas com dados faltantes.")
        st.stop()

    # Configurações da simulação
    capital_inicial = 3000      # Patrimônio inicial em reais
    aporte_mensal = 3000        # Aporte mensal em reais

    # Pesos desejados: 35% BTC, 35% XMR e 30% SOL (total = 100%)
    pesos_desejados = {'BTC-USD': 35, 'XMR-USD': 35, 'SOL-USD': 30}
    soma_pesos = sum(pesos_desejados.values())
    pesos = {ativo: peso / soma_pesos for ativo, peso in pesos_desejados.items()}

    # Série para armazenar o valor do portfólio ao longo do tempo
    portfolio_val = pd.Series(index=prices.index, dtype=float)

    # Dicionário para armazenar a quantidade (holdings) de cada ativo
    holdings = {crypto: 0 for crypto in prices.columns}

    # Compra inicial com o capital inicial
    data_inicial = prices.index[0]
    for crypto in prices.columns:
        quantidade = (capital_inicial * pesos[crypto]) / prices[crypto].loc[data_inicial]
        holdings[crypto] += quantidade

    valor_inicial = sum(holdings[crypto] * prices[crypto].loc[data_inicial] for crypto in prices.columns)
    portfolio_val.loc[data_inicial] = valor_inicial

    # Define as datas de aporte: primeiro dia útil de cada mês, exceto a data inicial
    aporte_dates = prices.resample('M').first().index
    aporte_dates = aporte_dates[aporte_dates > data_inicial]

    # Loop pelo período do backtest
    for current_date in prices.index[1:]:
        # Realiza aporte se for data de aporte
        if current_date in aporte_dates:
            for crypto in prices.columns:
                quantidade = (aporte_mensal * pesos[crypto]) / prices[crypto].loc[current_date]
                holdings[crypto] += quantidade

        # Atualiza o valor da carteira
        valor_carteira = sum(holdings[crypto] * prices[crypto].loc[current_date] for crypto in prices.columns)
        portfolio_val.loc[current_date] = valor_carteira

    # Calcula o valor acumulado investido ao longo do tempo
    investido = pd.Series(index=portfolio_val.index, dtype=float)
    for dt in portfolio_val.index:
        num_aportes = (aporte_dates <= dt).sum()
        investido[dt] = capital_inicial + aporte_mensal * num_aportes

    # Cria o gráfico
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(portfolio_val.index, portfolio_val, label='Valor da Carteira')
    ax.plot(investido.index, investido, color='red', linestyle='--', label='Valor Acumulado Investido')
    ax.set_xlabel('Data')
    ax.set_ylabel('Valor (R$ simulados)')
    ax.set_title('Backtest de Carteira de Criptomoedas - Sem Rebalanceamento')
    ax.legend()
    ax.grid(True)

    # Exibe o gráfico
    st.pyplot(fig)
