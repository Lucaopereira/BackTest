import streamlit as st
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import date

st.title("Backtest de Carteira de Criptomoedas")

# Dicionário com as opções de criptomoedas e seus tickers
crypto_options = {
    "Bitcoin": "BTC-USD",
    "Ethereum": "ETH-USD",
    "Solana": "SOL-USD",
    "Monero": "XMR-USD",
    "Shiba Inu": "SHIB-USD",
    "Polkadot": "DOT-USD",
    "Chainlink": "LINK-USD",
    "Fetch.ai": "FET-USD",
    "Pendle": "PENDLE-USD"
}

with st.form("config_form"):
    start_date = st.date_input("Data Inicial", value=date(2021, 1, 1))
    end_date = st.date_input("Data Final", value=date(2024, 12, 31))
    monthly_investment = st.number_input("Valor do Aporte Mensal (R$)", value=3000.0, min_value=0.0, step=500.0)
    
    # Seletor de criptomoedas
    selected_cryptos = st.multiselect(
        "Escolha as Criptomoedas",
        options=list(crypto_options.keys()),
        default=["Bitcoin", "Ethereum", "Solana", "Monero"]
    )
    
    # Atualiza o session_state para remover inputs antigos se a seleção mudar
    if "old_cryptos" not in st.session_state:
        st.session_state["old_cryptos"] = selected_cryptos
    else:
        removed = set(st.session_state["old_cryptos"]) - set(selected_cryptos)
        for crypto in removed:
            st.session_state.pop(f"peso_{crypto}", None)
        st.session_state["old_cryptos"] = selected_cryptos

    # Entrada dos pesos para cada criptomoeda selecionada
    pesos_input = {}
    total_peso = 0.0
    if selected_cryptos:
        st.markdown("### Defina os pesos de alocação para cada criptomoeda (%)")
        for crypto in selected_cryptos:
            # Valor default: divisão igualitária
            default_peso = round(100.0 / len(selected_cryptos), 2)
            peso = st.number_input(
                f"Peso para {crypto} (%)",
                min_value=0.0,
                max_value=100.0,
                value=default_peso,
                step=0.1,
                key=f"peso_{crypto}"
            )
            pesos_input[crypto] = peso
            total_peso += peso
        st.write(f"**Total dos Pesos:** {total_peso}%")
    
    submit_button = st.form_submit_button("Processar Dados")

if submit_button:
    # Valida datas
    if start_date >= end_date:
        st.error("A Data Inicial deve ser anterior à Data Final!")
        st.stop()
    
    # Valida se pelo menos uma criptomoeda foi selecionada
    if not selected_cryptos:
        st.error("Selecione pelo menos uma criptomoeda!")
        st.stop()
    
    # Valida se a soma dos pesos é exatamente 100%
    if abs(total_peso - 100) > 1e-3:
        st.error("A soma dos pesos deve ser exatamente 100%. Ajuste os valores e tente novamente.")
        st.stop()
    
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    
    # Mapeia os nomes escolhidos para os respectivos tickers
    selected_tickers = [crypto_options[crypto] for crypto in selected_cryptos]
    
    # Cria dicionário de pesos (convertendo % para fração)
    pesos = {crypto_options[crypto]: pesos_input[crypto] / 100.0 for crypto in selected_cryptos}
    
    # Baixa os dados históricos (preço de fechamento) para cada criptomoeda selecionada
    data = {}
    for ticker in selected_tickers:
        df = yf.download(ticker, start=start_date_str, end=end_date_str)['Close']
        if not df.empty:
            data[ticker] = df
    
    if not data:
        st.error("Nenhum dado foi baixado para os ativos informados.")
        st.stop()
    
    # Combina os preços em um único DataFrame e remove datas com dados faltantes
    prices = pd.concat(data, axis=1)
    prices.columns = prices.columns.get_level_values(0)
    prices.dropna(inplace=True)
    if prices.empty:
        st.error("O DataFrame 'prices' ficou vazio após remover as linhas com dados faltantes.")
        st.stop()
    
    # Configurações da simulação
    capital_inicial = 3000      # Patrimônio inicial em reais
    aporte_mensal = monthly_investment  # Aporte mensal em reais
    
    # DataFrame para armazenar o valor de cada cripto ao longo do tempo
    crypto_values_df = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
    # Série para armazenar o valor total da carteira
    portfolio_val = pd.Series(index=prices.index, dtype=float)
    
    # Inicializa os holdings e registra o valor no dia inicial
    data_inicial = prices.index[0]
    holdings = {}
    for crypto in prices.columns:
        # Compra inicial: aloca capital proporcional ao peso definido
        holdings[crypto] = (capital_inicial * pesos[crypto]) / prices[crypto].loc[data_inicial]
        crypto_values_df.loc[data_inicial, crypto] = holdings[crypto] * prices[crypto].loc[data_inicial]
    portfolio_val.loc[data_inicial] = crypto_values_df.loc[data_inicial].sum()
    
    # Define as datas de aporte: primeiro dia útil de cada mês (exceto o dia inicial)
    aporte_dates = prices.resample('M').first().index
    aporte_dates = aporte_dates[aporte_dates > data_inicial]
    
    # Loop pelo período do backtest, atualizando holdings e registrando os valores
    for current_date in prices.index[1:]:
        if current_date in aporte_dates:
            for crypto in prices.columns:
                quantidade = (aporte_mensal * pesos[crypto]) / prices[crypto].loc[current_date]
                holdings[crypto] += quantidade
        for crypto in prices.columns:
            crypto_values_df.loc[current_date, crypto] = holdings[crypto] * prices[crypto].loc[current_date]
        portfolio_val.loc[current_date] = crypto_values_df.loc[current_date].sum()
    
    # Calcula o valor acumulado investido ao longo do tempo
    investido = pd.Series(index=portfolio_val.index, dtype=float)
    for dt in portfolio_val.index:
        num_aportes = (aporte_dates <= dt).sum()
        investido[dt] = capital_inicial + aporte_mensal * num_aportes
    
    # Gráfico 1: Valor da Carteira x Valor Acumulado Investido
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    ax1.plot(portfolio_val.index, portfolio_val, label='Valor da Carteira', linewidth=2)
    ax1.plot(investido.index, investido, color='red', linestyle='--', label='Valor Acumulado Investido', linewidth=2)
    ax1.set_xlabel('Data')
    ax1.set_ylabel('Valor (R$ simulados)')
    ax1.set_title('Backtest de Carteira de Criptomoedas - Sem Rebalanceamento')
    ax1.legend()
    ax1.grid(True)
    st.pyplot(fig1)
    
    # Cálculo da rentabilidade acumulada por cripto
    rentabilidade = {}
    for crypto in prices.columns:
        investido_crypto = investido * pesos[crypto]
        rentabilidade[crypto] = (crypto_values_df[crypto] / investido_crypto) - 1
    
    # Gráfico 2: Rentabilidade Acumulada por Criptomoeda
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    for crypto in prices.columns:
        ax2.plot(rentabilidade[crypto].index, rentabilidade[crypto] * 100, label=crypto, linewidth=2)
    ax2.axhline(0, color='black', linewidth=1, linestyle='--')
    ax2.set_xlabel('Data')
    ax2.set_ylabel('Rentabilidade (%)')
    ax2.set_title('Rentabilidade Acumulada por Criptomoeda')
    ax2.legend()
    ax2.grid(True)
    st.pyplot(fig2)
