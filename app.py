"""
=============================================================================
INVESTMENT TOOLKIT - Dashboard Streamlit
=============================================================================
Executar:  streamlit run app.py
Deploy:    Streamlit Cloud (gratuito) via GitHub

Abas:
  1. Screener de Ações (Fórmula Mágica + Multi-Factor)
  2. Painel Macro (séries BCB + Focus, gráficos interativos)
  3. Notícias (BR + US via RSS)
=============================================================================
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import feedparser
import warnings
import numpy as np

warnings.filterwarnings("ignore")

# ─── CONFIG ──────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Investment Toolkit",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CUSTOM CSS ──────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Clean light theme */
    .stApp {
        background-color: #f8f9fb;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e5ea;
        border-radius: 12px;
        padding: 18px 22px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    div[data-testid="stMetric"] label {
        color: #6b7280 !important;
        font-size: 0.78rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 600 !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.7rem !important;
        font-weight: 700 !important;
        color: #111827 !important;
    }

    /* Dataframe */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #e5e7eb;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #eef0f4;
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        color: #374151;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #111827 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e5e7eb;
    }
    section[data-testid="stSidebar"] .stMarkdown h2 {
        color: #111827;
    }
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #374151;
    }

    /* Headings */
    h1 { color: #111827 !important; font-weight: 800 !important; }
    h2 { color: #1f2937 !important; }
    h3 { color: #374151 !important; }
    h4 { color: #374151 !important; }
    p, span, label { color: #374151; }

    /* Links in news */
    a.news-link {
        color: #2563eb !important;
        text-decoration: none;
        font-weight: 600;
    }
    a.news-link:hover {
        color: #1d4ed8 !important;
        text-decoration: underline;
    }

    /* News cards */
    .news-card {
        padding: 14px 0;
        border-bottom: 1px solid #e5e7eb;
    }
    .news-card p {
        margin: 0;
    }
    .news-date { color: #6b7280; font-size: 0.8rem; margin: 4px 0 2px 0; }
    .news-summary { color: #4b5563; font-size: 0.85rem; }

    /* Success/info banners */
    .stSuccess, .stAlert { border-radius: 8px; }

    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Download button */
    .stDownloadButton button {
        background-color: #2563eb !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    .stDownloadButton button:hover {
        background-color: #1d4ed8 !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# FUNÇÕES DE DADOS: NOTÍCIAS
# =============================================================================

RSS_FEEDS_SECTIONED = {
    "🇧🇷 Brasil": {
        "InfoMoney": {
            "Últimas":       "https://www.infomoney.com.br/feed/",
            "Mercados":      "https://www.infomoney.com.br/mercados/feed/",
            "Economia":      "https://www.infomoney.com.br/economia/feed/",
            "Onde Investir":  "https://www.infomoney.com.br/onde-investir/feed/",
            "Business":      "https://www.infomoney.com.br/business/feed/",
            "Finanças":      "https://www.infomoney.com.br/minhas-financas/feed/",
            "Mundo":         "https://www.infomoney.com.br/mundo/feed/",
            "Política":      "https://www.infomoney.com.br/brasil/feed/",
        },
        "Valor Econômico": {
            "Geral": "https://pox.globo.com/rss/valor/",
        },
        "Investing BR": {
            "Geral": "https://br.investing.com/rss/news.rss",
        },
        "Money Times": {
            "Mercados": "https://www.moneytimes.com.br/mercados/feed/",
        },
    },
    "🇺🇸 US / Global": {
        "CNBC": {
            "Top News":    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
            "Markets":     "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147",
            "Investing":   "https://www.cnbc.com/id/10000664/device/rss/rss.html",
            "Economy":     "https://www.cnbc.com/id/20910258/device/rss/rss.html",
            "Technology":  "https://www.cnbc.com/id/19854910/device/rss/rss.html",
            "Real Estate": "https://www.cnbc.com/id/10000115/device/rss/rss.html",
        },
        "MarketWatch": {
            "Top Stories":   "https://feeds.marketwatch.com/marketwatch/topstories/",
            "Markets":       "https://feeds.marketwatch.com/marketwatch/marketpulse/",
        },
        "Yahoo Finance": {
            "Geral": "https://finance.yahoo.com/news/rssindex",
        },
        "Reuters": {
            "Business":  "https://feeds.reuters.com/reuters/businessNews",
        },
        "Investing.com": {
            "Geral": "https://www.investing.com/rss/news.rss",
        },
    },
}


@st.cache_data(ttl=900, show_spinner=False)
def fetch_rss_feed(url, max_items=15):
    """Busca e parseia um feed RSS."""
    try:
        feed = feedparser.parse(url)
        items = []
        for entry in feed.entries[:max_items]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            published = entry.get("published", entry.get("updated", ""))
            summary = entry.get("summary", "")
            # Limpar HTML do summary
            if summary:
                summary = BeautifulSoup(summary, "html.parser").get_text()[:200]
            items.append({
                "title": title,
                "link": link,
                "published": published,
                "summary": summary,
            })
        return items
    except Exception:
        return []


# =============================================================================
# UI: SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown("## 📊 Investment Toolkit")
    st.markdown("##### Análise & Internacional")
    st.markdown("---")

    page = st.radio(
        "Navegação",
        ["📋 Análise CVM", "🏢 CRE Lending", "📰 Notícias"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("[🎯 Mercado & Macro →](https://investment-toolkit-mwfierprsfd37mejekcx6q.streamlit.app)", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#6b7280; font-size:0.75rem;'>"
        "Dados: CVM, FRED, RSS<br>"
        "⚠️ Não é recomendação de investimento"
        "</p>",
        unsafe_allow_html=True,
    )



# =============================================================================
# PAGE: ANÁLISE CVM
# =============================================================================

if page == "📋 Análise CVM":

    st.markdown("# 📋 Análise de Empresas — Dados CVM")
    st.markdown("DFP (anual) e ITR (trimestral) direto do Portal de Dados Abertos da CVM")

    import zipfile, io
    from pathlib import Path

    CVM_BASE_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC"
    CVM_CACHE = Path("cvm_cache")
    CVM_ENCODING = "ISO-8859-1"

    CONTAS_CHAVE = {
        "3.01": "Receita Líquida", "3.02": "CPV", "3.03": "Resultado Bruto",
        "3.04": "Despesas Operacionais", "3.05": "EBIT",
        "3.06": "Resultado Financeiro", "3.06.01": "Receitas Financeiras",
        "3.06.02": "Despesas Financeiras", "3.07": "EBT",
        "3.08": "IR/CSLL", "3.09": "Lucro Líquido Op. Continuadas",
        "3.11": "Lucro/Prejuízo Consolidado",
        "1": "Ativo Total", "1.01": "Ativo Circulante",
        "1.01.01": "Caixa e Equivalentes", "1.01.02": "Aplicações Fin. CP",
        "1.01.03": "Contas a Receber", "1.01.04": "Estoques",
        "1.02": "Ativo Não Circulante", "1.02.03": "Imobilizado", "1.02.04": "Intangível",
        "2": "Passivo Total", "2.01": "Passivo Circulante",
        "2.01.04": "Empréstimos CP", "2.02": "Passivo Não Circulante",
        "2.02.01": "Empréstimos LP", "2.03": "Patrimônio Líquido",
        "6.01": "FCO", "6.02": "Caixa Investimentos", "6.03": "Caixa Financiamentos",
        "6.05": "Variação de Caixa",
    }

    @st.cache_data(ttl=86400, show_spinner=False)
    def cvm_download(doc_type, year):
        url = f"{CVM_BASE_URL}/{doc_type}/DADOS/{doc_type.lower()}_cia_aberta_{year}.zip"
        CVM_CACHE.mkdir(exist_ok=True)
        cache = CVM_CACHE / f"{doc_type.lower()}_{year}.zip"
        if cache.exists():
            return cache.read_bytes()
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
        if r.status_code != 200:
            return None
        cache.write_bytes(r.content)
        return r.content

    def cvm_read_csv(zb, filename):
        with zipfile.ZipFile(io.BytesIO(zb)) as zf:
            with zf.open(filename) as f:
                return pd.read_csv(f, sep=";", encoding=CVM_ENCODING,
                                   dtype={"CD_CVM": str, "CNPJ_CIA": str, "CD_CONTA": str},
                                   on_bad_lines="skip")

    def cvm_load(doc_type, year, file_type, consolidado=True):
        zb = cvm_download(doc_type, year)
        if zb is None:
            return pd.DataFrame()
        with zipfile.ZipFile(io.BytesIO(zb)) as zf:
            names = zf.namelist()
        tc = "con" if consolidado else "ind"
        prefix = f"{doc_type.lower()}_cia_aberta_{file_type}_{tc}_{year}"
        target = next((f for f in names if prefix.lower() in f.lower()), None)
        if not target:
            target = next((f for f in names if file_type.lower() in f.lower() and tc in f.lower()), None)
        if not target:
            return pd.DataFrame()
        df = cvm_read_csv(zb, target)
        if "VL_CONTA" in df.columns:
            df["VL_CONTA"] = pd.to_numeric(df["VL_CONTA"], errors="coerce")
        for c in ["DT_REFER", "DT_INI_EXERC", "DT_FIM_EXERC"]:
            if c in df.columns:
                df[c] = pd.to_datetime(df[c], errors="coerce")
        if "ESCALA_MOEDA" in df.columns:
            mask = df["ESCALA_MOEDA"] == "MIL"
            df.loc[mask, "VL_CONTA"] = df.loc[mask, "VL_CONTA"] * 1000
        return df

    def cvm_empresa(df, query):
        if query.isdigit():
            r = df[df["CD_CVM"] == query]
            if len(r) > 0: return r
        if "DENOM_CIA" in df.columns:
            r = df[df["DENOM_CIA"].str.contains(query, case=False, na=False)]
            if len(r) > 0: return r
        return pd.DataFrame()

    def cvm_indicadores(nome, year, doc_type="DFP"):
        indicadores = {}
        for ft in ["DRE", "BPA", "BPP", "DFC_MI"]:
            try:
                df = cvm_load(doc_type, year, ft)
                if df.empty: continue
                df = cvm_empresa(df, nome)
                if "ORDEM_EXERC" in df.columns:
                    df = df[df["ORDEM_EXERC"] == "ÚLTIMO"]
                if "VERSAO" in df.columns:
                    idx = df.groupby(["CD_CVM", "DT_REFER", "CD_CONTA"])["VERSAO"].idxmax()
                    df = df.loc[idx]
                df = df[df["CD_CONTA"].isin(CONTAS_CHAVE.keys())].copy()
                df["CONTA_DESCR"] = df["CD_CONTA"].map(CONTAS_CHAVE)
                for _, row in df.iterrows():
                    indicadores[row["CD_CONTA"]] = {
                        "Código": row["CD_CONTA"],
                        "Conta": row["CONTA_DESCR"],
                        "Valor": row["VL_CONTA"],
                        "Demo": ft,
                    }
            except Exception:
                pass
        return pd.DataFrame(indicadores.values()) if indicadores else pd.DataFrame()

    def cvm_metricas(ind):
        def v(cd):
            r = ind[ind["Código"] == cd]
            return r.iloc[0]["Valor"] if len(r) > 0 else None
        m = {}
        rec = v("3.01"); ebit = v("3.05"); lucro = v("3.11") or v("3.09")
        rb = v("3.03"); pl = v("2.03"); at = v("1")
        ac = v("1.01"); pc = v("2.01"); caixa = v("1.01.01"); aplic = v("1.01.02")
        emp_cp = v("2.01.04"); emp_lp = v("2.02.01"); fco = v("6.01")

        if rec and rec != 0:
            m["Receita Líquida (R$ mi)"] = rec / 1e6
            if rb: m["Margem Bruta (%)"] = (rb / rec) * 100
            if ebit: m["Margem EBIT (%)"] = (ebit / rec) * 100
            if lucro: m["Margem Líquida (%)"] = (lucro / rec) * 100
        if ebit: m["EBIT (R$ mi)"] = ebit / 1e6
        if lucro: m["Lucro Líquido (R$ mi)"] = lucro / 1e6
        if at: m["Ativo Total (R$ mi)"] = at / 1e6
        if pl: m["Patrimônio Líquido (R$ mi)"] = pl / 1e6

        db = None
        if emp_cp is not None and emp_lp is not None:
            db = abs(emp_cp) + abs(emp_lp)
            m["Dívida Bruta (R$ mi)"] = db / 1e6
        cx = (caixa or 0) + (aplic or 0)
        m["Caixa + Aplic. (R$ mi)"] = cx / 1e6
        if db is not None:
            m["Dívida Líquida (R$ mi)"] = (db - cx) / 1e6
        if ac and pc:
            m["Capital de Giro (R$ mi)"] = (ac - abs(pc)) / 1e6
            if pc != 0: m["Liquidez Corrente"] = ac / abs(pc)
        if lucro and pl and pl != 0: m["ROE (%)"] = (lucro / pl) * 100
        if lucro and at and at != 0: m["ROA (%)"] = (lucro / at) * 100
        if ebit and pl and db is not None:
            ci = pl + db
            if ci != 0: m["ROIC (%)"] = (ebit / ci) * 100
        if db is not None and pl and pl != 0: m["Dívida Bruta / PL"] = db / pl
        if fco: m["FCO (R$ mi)"] = fco / 1e6
        return m

    @st.cache_data(ttl=86400, show_spinner=False)
    def cvm_listar_empresas(year):
        df = cvm_load("DFP", year, "DRE")
        if df.empty: return pd.DataFrame()
        return df[["CD_CVM", "DENOM_CIA"]].drop_duplicates().sort_values("DENOM_CIA").reset_index(drop=True)

    # ─── Sidebar controls ────────────────────────────────────────────────

    with st.sidebar:
        st.markdown("### 🔎 Empresa")
        empresa_input = st.text_input("Nome da empresa (parcial)", value="PETROBRAS", key="cvm_emp")
        doc_type = st.selectbox("Tipo", ["DFP", "ITR"], key="cvm_doc")
        ano_atual = datetime.now().year
        anos_disp = list(range(ano_atual, 2019, -1))
        ano_sel = st.selectbox("Ano", anos_disp, key="cvm_ano")
        st.markdown("### 📊 Série Histórica")
        anos_hist = st.multiselect("Anos", anos_disp, default=anos_disp[:5], key="cvm_hist_anos")

    # ─── Tabs ────────────────────────────────────────────────────────────

    tab_indicadores, tab_serie, tab_comparacao, tab_raw = st.tabs([
        "📊 Indicadores",
        "📈 Série Histórica",
        "⚖️ Comparação",
        "🗂️ Dados Brutos",
    ])

    with tab_indicadores:
        st.markdown(f"### {empresa_input} — {doc_type} {ano_sel}")

        with st.spinner(f"Carregando {doc_type} {ano_sel}..."):
            ind = cvm_indicadores(empresa_input, ano_sel, doc_type)

        if ind.empty:
            st.warning(f"Empresa '{empresa_input}' não encontrada no {doc_type} {ano_sel}.")
            st.caption("Tente o nome como aparece na CVM (ex: 'PETROBRAS', 'VALE', 'WEG')")
        else:
            metricas = cvm_metricas(ind)

            # Cards de métricas principais
            row1 = st.columns(4)
            keys_row1 = ["Receita Líquida (R$ mi)", "EBIT (R$ mi)", "Lucro Líquido (R$ mi)", "FCO (R$ mi)"]
            for i, k in enumerate(keys_row1):
                with row1[i]:
                    v = metricas.get(k)
                    st.metric(k.replace(" (R$ mi)", ""), f"R$ {v:,.0f} mi" if v else "—")

            row2 = st.columns(4)
            keys_row2 = ["Margem EBIT (%)", "ROE (%)", "ROIC (%)", "Dívida Bruta / PL"]
            for i, k in enumerate(keys_row2):
                with row2[i]:
                    v = metricas.get(k)
                    if v is not None:
                        fmt = f"{v:.1f}%" if "%" in k else f"{v:.2f}x"
                        st.metric(k.replace(" (%)", ""), fmt)
                    else:
                        st.metric(k, "—")

            row3 = st.columns(4)
            keys_row3 = ["Dívida Líquida (R$ mi)", "Caixa + Aplic. (R$ mi)", "Liquidez Corrente", "Capital de Giro (R$ mi)"]
            for i, k in enumerate(keys_row3):
                with row3[i]:
                    v = metricas.get(k)
                    if v is not None:
                        if "R$ mi" in k:
                            st.metric(k.replace(" (R$ mi)", ""), f"R$ {v:,.0f} mi")
                        else:
                            st.metric(k, f"{v:.2f}")
                    else:
                        st.metric(k, "—")

            # Tabela completa
            st.markdown("#### Todas as métricas")
            met_df = pd.DataFrame(list(metricas.items()), columns=["Métrica", "Valor"])
            met_df["Valor"] = met_df.apply(
                lambda r: f"{r['Valor']:.1f}%" if "%" in r["Métrica"]
                else f"{r['Valor']:,.0f}" if "R$ mi" in r["Métrica"]
                else f"{r['Valor']:.2f}", axis=1
            )
            st.dataframe(met_df, use_container_width=True, hide_index=True)

            # Indicadores brutos CVM
            with st.expander("Ver contas CVM detalhadas"):
                display_ind = ind.copy()
                display_ind["Valor (R$ mil)"] = display_ind["Valor"].apply(
                    lambda x: f"{x/1e3:,.0f}" if pd.notna(x) else "—"
                )
                st.dataframe(display_ind[["Código", "Conta", "Valor (R$ mil)", "Demo"]],
                             use_container_width=True, hide_index=True)

    with tab_serie:
        st.markdown(f"### Série Histórica — {empresa_input}")

        if not anos_hist:
            st.info("Selecione os anos no sidebar.")
        else:
            all_met = {}
            progress = st.progress(0)
            for i, ano in enumerate(sorted(anos_hist)):
                try:
                    ind = cvm_indicadores(empresa_input, ano, doc_type)
                    if not ind.empty:
                        all_met[ano] = cvm_metricas(ind)
                except Exception:
                    pass
                progress.progress((i + 1) / len(anos_hist))
            progress.empty()

            if all_met:
                serie_df = pd.DataFrame(all_met)
                serie_df.index.name = "Métrica"

                # Tabela formatada
                display_serie = serie_df.copy()
                for col in display_serie.columns:
                    display_serie[col] = display_serie[col].apply(
                        lambda x: f"{x:,.1f}" if pd.notna(x) else "—"
                    )
                st.dataframe(display_serie, use_container_width=True)

                # Helper: add Y-axis padding to charts
                def add_y_padding(fig):
                    """Adds 15% padding above max value to prevent text cutoff."""
                    all_y = []
                    for trace in fig.data:
                        if hasattr(trace, 'y') and trace.y is not None:
                            all_y.extend([v for v in trace.y if v is not None])
                    if all_y:
                        y_min = min(all_y)
                        y_max = max(all_y)
                        rng = y_max - y_min if y_max != y_min else abs(y_max) * 0.2
                        pad = rng * 0.2
                        fig.update_yaxes(range=[y_min - pad * 0.3, y_max + pad])

                # ─── Gráficos de LINHA: Margens ─────────────────────────────
                st.markdown("#### Evolução de Margens")
                margin_metrics = ["Margem Bruta (%)", "Margem EBIT (%)", "Margem Líquida (%)"]
                avail_margins = [m for m in margin_metrics if m in serie_df.index]

                if avail_margins:
                    fig_margins = go.Figure()
                    m_colors = ["#2563eb", "#ea580c", "#16a34a"]
                    for i, metric in enumerate(avail_margins):
                        row = serie_df.loc[metric].dropna()
                        if len(row) > 0:
                            fig_margins.add_trace(go.Scatter(
                                x=[str(y) for y in row.index], y=row.values,
                                mode="lines+markers+text", name=metric.replace(" (%)", ""),
                                line=dict(color=m_colors[i], width=2.5),
                                marker=dict(size=8),
                                text=[f"{v:.1f}%" for v in row.values],
                                textposition="top center", textfont=dict(size=10),
                            ))
                    add_y_padding(fig_margins)
                    fig_margins.update_layout(
                        title=dict(text="Margens (%)", font=dict(size=15, color="#111827")),
                        template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="#ffffff", height=420,
                        xaxis=dict(gridcolor="#e5e7eb"), yaxis=dict(gridcolor="#e5e7eb", title="%"),
                        hovermode="x unified", legend=dict(orientation="h", y=1.15),
                    )
                    st.plotly_chart(fig_margins, use_container_width=True)
                    st.caption("Margem Bruta = (Receita − CPV) / Receita  •  "
                               "Margem EBIT = EBIT / Receita  •  "
                               "Margem Líquida = Lucro Líquido / Receita")

                # ─── Gráficos de LINHA: Retornos ────────────────────────────
                st.markdown("#### Evolução de Retornos")
                return_metrics = ["ROE (%)", "ROIC (%)", "ROA (%)"]
                avail_returns = [m for m in return_metrics if m in serie_df.index]

                if avail_returns:
                    fig_returns = go.Figure()
                    r_colors = ["#9333ea", "#dc2626", "#eab308"]
                    for i, metric in enumerate(avail_returns):
                        row = serie_df.loc[metric].dropna()
                        if len(row) > 0:
                            fig_returns.add_trace(go.Scatter(
                                x=[str(y) for y in row.index], y=row.values,
                                mode="lines+markers+text", name=metric.replace(" (%)", ""),
                                line=dict(color=r_colors[i], width=2.5),
                                marker=dict(size=8),
                                text=[f"{v:.1f}%" for v in row.values],
                                textposition="top center", textfont=dict(size=10),
                            ))
                    add_y_padding(fig_returns)
                    fig_returns.update_layout(
                        title=dict(text="Retornos (%)", font=dict(size=15, color="#111827")),
                        template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="#ffffff", height=420,
                        xaxis=dict(gridcolor="#e5e7eb"), yaxis=dict(gridcolor="#e5e7eb", title="%"),
                        hovermode="x unified", legend=dict(orientation="h", y=1.15),
                    )
                    st.plotly_chart(fig_returns, use_container_width=True)
                    st.caption("ROE = Lucro Líquido / Patrimônio Líquido  •  "
                               "ROIC = EBIT / (PL + Dívida Bruta)  •  "
                               "ROA = Lucro Líquido / Ativo Total")

                # ─── Gráfico de LINHA: Endividamento ────────────────────────
                st.markdown("#### Evolução do Endividamento")
                debt_metrics = ["Dívida Bruta (R$ mi)", "Dívida Líquida (R$ mi)",
                                "Caixa + Aplic. (R$ mi)", "Dívida Bruta / PL"]
                avail_debt = [m for m in debt_metrics if m in serie_df.index]

                if avail_debt:
                    abs_debt = [m for m in avail_debt if "R$ mi" in m]
                    ratio_debt = [m for m in avail_debt if "R$ mi" not in m]

                    if abs_debt:
                        fig_debt = go.Figure()
                        debt_colors = ["#dc2626", "#ea580c", "#16a34a"]
                        for i, metric in enumerate(abs_debt):
                            row = serie_df.loc[metric].dropna()
                            if len(row) > 0:
                                fig_debt.add_trace(go.Scatter(
                                    x=[str(y) for y in row.index], y=row.values,
                                    mode="lines+markers+text", name=metric.replace(" (R$ mi)", ""),
                                    line=dict(color=debt_colors[i % len(debt_colors)], width=2.5),
                                    marker=dict(size=8),
                                    text=[f"{v:,.0f}" for v in row.values],
                                    textposition="top center", textfont=dict(size=9),
                                ))
                        fig_debt.add_hline(y=0, line_dash="dash", line_color="#6b7280", opacity=0.5)
                        add_y_padding(fig_debt)
                        fig_debt.update_layout(
                            title=dict(text="Endividamento (R$ mi)", font=dict(size=15, color="#111827")),
                            template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="#ffffff", height=450,
                            xaxis=dict(gridcolor="#e5e7eb"), yaxis=dict(gridcolor="#e5e7eb", title="R$ milhões"),
                            hovermode="x unified", legend=dict(orientation="h", y=1.15),
                        )
                        st.plotly_chart(fig_debt, use_container_width=True)
                        st.caption("Dívida Bruta = Empréstimos CP + LP  •  "
                                   "Dívida Líquida = Dívida Bruta − Caixa − Aplicações Financeiras")

                    if ratio_debt:
                        fig_ratio = go.Figure()
                        for metric in ratio_debt:
                            row = serie_df.loc[metric].dropna()
                            if len(row) > 0:
                                fig_ratio.add_trace(go.Bar(
                                    x=[str(y) for y in row.index], y=row.values,
                                    name=metric, marker_color="#ea580c",
                                    text=[f"{v:.2f}x" for v in row.values], textposition="outside",
                                ))
                        add_y_padding(fig_ratio)
                        fig_ratio.update_layout(
                            title=dict(text="Alavancagem — Dívida Bruta / Patrimônio Líquido",
                                       font=dict(size=15, color="#111827")),
                            template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="#ffffff", height=380,
                            xaxis=dict(gridcolor="#e5e7eb"), yaxis=dict(gridcolor="#e5e7eb", title="x"),
                        )
                        st.plotly_chart(fig_ratio, use_container_width=True)
                        st.caption("Alavancagem = Dívida Bruta (Empréstimos CP + LP) / Patrimônio Líquido.  "
                                   "Valores > 1.0x indicam que a empresa deve mais do que seu patrimônio próprio.")

                # Gráficos de BARRA para valores absolutos (receita, EBIT, lucro, FCO)
                st.markdown("#### Receita, Lucro e Caixa")
                bar_metrics = ["Receita Líquida (R$ mi)", "EBIT (R$ mi)",
                               "Lucro Líquido (R$ mi)", "FCO (R$ mi)"]
                avail_bar = [m for m in bar_metrics if m in serie_df.index]
                sel_bar = st.multiselect("Métricas (barras)", avail_bar,
                                         default=avail_bar[:3], key="cvm_bar_sel")

                for metric in sel_bar:
                    row = serie_df.loc[metric].dropna()
                    if len(row) == 0:
                        continue
                    fig = go.Figure()
                    colors = ["#16a34a" if v >= 0 else "#dc2626" for v in row.values]
                    fig.add_trace(go.Bar(
                        x=[str(y) for y in row.index], y=row.values,
                        marker_color=colors, text=[f"{v:,.0f}" for v in row.values],
                        textposition="outside",
                    ))
                    add_y_padding(fig)
                    fig.update_layout(
                        title=dict(text=metric, font=dict(size=15, color="#111827")),
                        template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="#ffffff", height=350,
                        xaxis=dict(gridcolor="#e5e7eb"), yaxis=dict(gridcolor="#e5e7eb"),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Download
                csv = serie_df.to_csv(sep=";")
                st.download_button("📥 Baixar série histórica", csv,
                                    f"cvm_{empresa_input}_{doc_type}.csv", "text/csv", key="dl_cvm_serie")
            else:
                st.warning("Nenhum dado encontrado para os anos selecionados.")

    with tab_comparacao:
        st.markdown("### Comparação entre empresas")

        empresas_comp = st.text_input(
            "Empresas (separadas por vírgula)",
            value="PETROBRAS, VALE, WEG",
            key="cvm_comp_input",
        )
        nomes = [e.strip() for e in empresas_comp.split(",") if e.strip()]

        sub_tab_snap, sub_tab_evo = st.tabs(["📊 Snapshot (1 ano)", "📈 Evolução Multi-Ano"])

        with sub_tab_snap:
            ano_comp = st.selectbox("Ano", anos_disp, key="cvm_comp_ano")

            if st.button("Comparar", key="cvm_comp_btn"):
                comp_data = {}
                progress = st.progress(0)
                for i, nome in enumerate(nomes):
                    try:
                        ind = cvm_indicadores(nome, ano_comp, doc_type)
                        if not ind.empty:
                            comp_data[nome] = cvm_metricas(ind)
                    except Exception:
                        st.caption(f"⚠️ {nome}: não encontrado")
                    progress.progress((i + 1) / len(nomes))
                progress.empty()

                if comp_data:
                    comp_df = pd.DataFrame(comp_data)
                    comp_df.index.name = "Métrica"

                    display_comp = comp_df.copy()
                    for col in display_comp.columns:
                        display_comp[col] = display_comp[col].apply(
                            lambda x: f"{x:,.1f}" if pd.notna(x) else "—"
                        )
                    st.dataframe(display_comp, use_container_width=True)

                    comp_metrics = ["Margem Bruta (%)", "Margem EBIT (%)", "Margem Líquida (%)",
                                    "ROE (%)", "ROIC (%)", "Dívida Bruta / PL", "Liquidez Corrente"]
                    available = [m for m in comp_metrics if m in comp_df.index]

                    if available:
                        metric_sel = st.selectbox("Métrica para gráfico", available, key="cvm_comp_metric")
                        row = comp_df.loc[metric_sel].dropna()
                        fig = go.Figure()
                        bar_colors = ["#2563eb", "#ea580c", "#16a34a", "#9333ea", "#dc2626"]
                        fig.add_trace(go.Bar(
                            x=list(row.index), y=list(row.values),
                            marker_color=bar_colors[:len(row)],
                            text=[f"{v:.1f}" for v in row.values], textposition="outside",
                        ))
                        # Linha de média
                        avg = row.mean()
                        fig.add_hline(y=avg, line_dash="dash", line_color="#6b7280",
                                      annotation_text=f"Média: {avg:.1f}", annotation_position="top left")
                        fig.update_layout(
                            title=dict(text=f"{metric_sel} — {ano_comp}", font=dict(size=15, color="#111827")),
                            template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="#ffffff", height=400,
                            yaxis=dict(gridcolor="#e5e7eb"),
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    csv = comp_df.to_csv(sep=";")
                    st.download_button("📥 Baixar comparação", csv,
                                        f"cvm_comparacao_{ano_comp}.csv", "text/csv", key="dl_cvm_comp")
                else:
                    st.warning("Nenhuma empresa encontrada.")

        with sub_tab_evo:
            st.markdown("#### Evolução comparativa ao longo dos anos")
            st.caption("Compara ROE, ROIC, margens de múltiplas empresas ao longo do tempo")

            anos_evo = st.multiselect("Anos", anos_disp, default=anos_disp[:5], key="cvm_evo_anos")
            metric_evo = st.selectbox("Métrica", [
                "ROE (%)", "ROIC (%)", "Margem EBIT (%)", "Margem Líquida (%)",
                "Margem Bruta (%)", "Dívida Bruta / PL", "Receita Líquida (R$ mi)",
                "Lucro Líquido (R$ mi)", "Dívida Líquida (R$ mi)", "FCO (R$ mi)",
            ], key="cvm_evo_metric")

            if st.button("Gerar evolução", key="cvm_evo_btn") and nomes and anos_evo:
                evo_data = {}  # {empresa: {ano: valor}}
                progress = st.progress(0)
                total = len(nomes) * len(anos_evo)
                count = 0

                for nome in nomes:
                    evo_data[nome] = {}
                    for ano in sorted(anos_evo):
                        try:
                            ind = cvm_indicadores(nome, ano, doc_type)
                            if not ind.empty:
                                met = cvm_metricas(ind)
                                if metric_evo in met:
                                    evo_data[nome][ano] = met[metric_evo]
                        except Exception:
                            pass
                        count += 1
                        progress.progress(count / total)
                progress.empty()

                # Plotar
                fig_evo = go.Figure()
                evo_colors = ["#2563eb", "#ea580c", "#16a34a", "#9333ea", "#dc2626",
                              "#eab308", "#06b6d4", "#ec4899"]

                has_data = False
                all_values = []
                for i, (nome, values) in enumerate(evo_data.items()):
                    if not values:
                        continue
                    has_data = True
                    anos_sorted = sorted(values.keys())
                    vals = [values[a] for a in anos_sorted]
                    all_values.extend(vals)
                    fig_evo.add_trace(go.Scatter(
                        x=[str(a) for a in anos_sorted], y=vals,
                        mode="lines+markers+text", name=nome,
                        line=dict(color=evo_colors[i % len(evo_colors)], width=2.5),
                        marker=dict(size=8),
                        text=[f"{v:.1f}" if "%" in metric_evo or "/" in metric_evo
                              else f"{v:,.0f}" for v in vals],
                        textposition="top center", textfont=dict(size=9),
                    ))

                if has_data:
                    # Média das empresas selecionadas
                    avg_by_year = {}
                    for nome, values in evo_data.items():
                        for ano, val in values.items():
                            avg_by_year.setdefault(ano, []).append(val)
                    avg_anos = sorted(avg_by_year.keys())
                    avg_vals = [sum(avg_by_year[a]) / len(avg_by_year[a]) for a in avg_anos]
                    fig_evo.add_trace(go.Scatter(
                        x=[str(a) for a in avg_anos], y=avg_vals,
                        mode="lines", name="Média (selecionadas)",
                        line=dict(color="#6b7280", width=2, dash="dash"),
                    ))

                    fig_evo.update_layout(
                        title=dict(text=f"{metric_evo} — Evolução Comparativa",
                                   font=dict(size=16, color="#111827")),
                        template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="#ffffff", height=500,
                        xaxis=dict(gridcolor="#e5e7eb"),
                        yaxis=dict(gridcolor="#e5e7eb",
                                   title="%" if "%" in metric_evo else "x" if "/" in metric_evo else "R$ mi"),
                        hovermode="x unified",
                        legend=dict(orientation="h", y=1.15),
                    )
                    st.plotly_chart(fig_evo, use_container_width=True)
                    st.caption("⚠️ A linha tracejada 'Média (selecionadas)' é a média aritmética das empresas que você digitou acima, "
                               "não a média do setor. Para comparação setorial, inclua as principais empresas do setor.")

                    # Tabela
                    evo_table = pd.DataFrame(evo_data).T
                    evo_table.index.name = "Empresa"
                    display_evo = evo_table.copy()
                    for col in display_evo.columns:
                        display_evo[col] = display_evo[col].apply(
                            lambda x: f"{x:,.1f}" if pd.notna(x) else "—"
                        )
                    st.dataframe(display_evo, use_container_width=True)
                else:
                    st.warning("Nenhum dado encontrado.")

    with tab_raw:
        st.markdown("### Dados brutos da CVM")

        col1, col2, col3 = st.columns(3)
        with col1:
            raw_type = st.selectbox("Demonstrativo", ["DRE", "BPA", "BPP", "DFC_MI", "DVA"], key="cvm_raw_type")
        with col2:
            raw_year = st.selectbox("Ano", anos_disp, key="cvm_raw_year")
        with col3:
            raw_cons = st.checkbox("Consolidado", value=True, key="cvm_raw_cons")

        if st.button("Carregar", key="cvm_raw_btn"):
            with st.spinner("Baixando..."):
                df_raw = cvm_load(doc_type, raw_year, raw_type, raw_cons)

            if df_raw.empty:
                st.warning("Arquivo não encontrado.")
            else:
                st.success(f"✅ {len(df_raw)} linhas carregadas")

                # Filtro por empresa
                raw_emp = st.text_input("Filtrar por empresa (opcional)", key="cvm_raw_emp")
                if raw_emp:
                    df_raw = cvm_empresa(df_raw, raw_emp)

                # Filtro por conta
                raw_conta = st.text_input("Filtrar por código de conta (ex: 3.01)", key="cvm_raw_conta")
                if raw_conta:
                    df_raw = df_raw[df_raw["CD_CONTA"] == raw_conta]

                st.dataframe(df_raw.head(500), use_container_width=True, hide_index=True)

                csv = df_raw.to_csv(index=False, sep=";")
                st.download_button("📥 Baixar dados brutos", csv,
                                    f"cvm_{raw_type}_{raw_year}.csv", "text/csv", key="dl_cvm_raw")

        # Listar empresas
        with st.expander("📋 Listar todas as empresas disponíveis"):
            emp_year = st.selectbox("Ano", anos_disp, key="cvm_emp_list_year")
            if st.button("Listar", key="cvm_emp_list_btn"):
                with st.spinner("Carregando..."):
                    empresas_list = cvm_listar_empresas(emp_year)
                if not empresas_list.empty:
                    st.success(f"✅ {len(empresas_list)} empresas")
                    st.dataframe(empresas_list, use_container_width=True, hide_index=True, height=400)
                else:
                    st.warning("Dados não disponíveis para este ano.")



# =============================================================================
# PAGE: CRE LENDING
# =============================================================================

elif page == "🏢 CRE Lending":

    st.markdown("# 🏢 CRE Lending Dashboard")
    st.markdown("Dados macro e de crédito imobiliário essenciais para gestores e analistas")

    # ─── FRED Data (via fredapi or manual URL) ───────────────────────────

    FRED_CRE_SERIES = {
        # Delinquency & Credit Quality
        "CRE Delinquency Rate (%)": "DRCRELEXFACBS",
        "Residential Mortgage Delinquency (%)": "DRSFRMACBS",
        "All Loans Delinquency (%)": "DRALACBS",
        "CRE Charge-Off Rate (%)": "CORERELEXFACBS",

        # Lending Volume & Rates
        "CRE Loans Outstanding ($B)": "CREACBM027NBOG",
        "30Y Mortgage Rate (%)": "MORTGAGE30US",
        "10Y Treasury (%)": "DGS10",
        "2Y Treasury (%)": "DGS2",
        "Fed Funds Rate (%)": "FEDFUNDS",
        "BAA Corporate Spread (%)": "BAA10Y",

        # Real Estate Market
        "Case-Shiller US Home Price Index": "CSUSHPINSA",
        "Housing Starts (thousands)": "HOUST",
        "Building Permits (thousands)": "PERMIT",
        "CPI Shelter (%)": "CUSR0000SAH1",

        # Economic Context
        "Real GDP Growth (%)": "A191RL1Q225SBEA",
        "Unemployment Rate (%)": "UNRATE",
        "CPI All Items (%)": "CPIAUCSL",
    }

    @st.cache_data(ttl=7200, show_spinner=False)
    def get_fred_series(series_dict, start="2010-01-01"):
        """Fetch FRED series. Tries pandas_datareader first, then CSV fallback."""
        frames = {}
        errors = []

        # Method 1: pandas_datareader (most reliable)
        try:
            import pandas_datareader.data as web
            from datetime import datetime as dt
            start_dt = dt.strptime(start, "%Y-%m-%d")
            for name, code in series_dict.items():
                try:
                    df = web.DataReader(code, "fred", start_dt)
                    frames[name] = df.iloc[:, 0]
                except Exception as e:
                    errors.append(f"{name}: {e}")
            if frames:
                return pd.DataFrame(frames), errors
        except ImportError:
            errors.append("pandas_datareader não instalado, tentando CSV...")

        # Method 2: FRED CSV (fallback)
        for name, code in series_dict.items():
            if name in frames:
                continue
            try:
                url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}&cosd={start}"
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(url, headers=headers, timeout=15)
                resp.raise_for_status()
                from io import StringIO
                df = pd.read_csv(StringIO(resp.text), parse_dates=[0], index_col=0)
                df.columns = [name]
                df[name] = pd.to_numeric(df[name], errors="coerce")
                frames[name] = df[name].dropna()
            except Exception as e:
                errors.append(f"{name} (CSV): {e}")

        # Method 3: FRED text files (last resort)
        for name, code in series_dict.items():
            if name in frames:
                continue
            try:
                url = f"https://fred.stlouisfed.org/data/{code}.txt"
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                lines = resp.text.strip().split("\n")
                # Find where data starts (after header lines)
                data_start = 0
                for i, line in enumerate(lines):
                    if line.strip() and line[0].isdigit():
                        data_start = i
                        break
                data_lines = lines[data_start:]
                records = []
                for line in data_lines:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        try:
                            date = pd.to_datetime(parts[0])
                            val = float(parts[1]) if parts[1] != "." else float("nan")
                            records.append((date, val))
                        except (ValueError, IndexError):
                            pass
                if records:
                    s = pd.Series(
                        [r[1] for r in records],
                        index=pd.DatetimeIndex([r[0] for r in records]),
                        name=name,
                    )
                    s = s[s.index >= start]
                    frames[name] = s.dropna()
            except Exception as e:
                errors.append(f"{name} (TXT): {e}")

        return pd.DataFrame(frames) if frames else pd.DataFrame(), errors

    with st.sidebar:
        st.markdown("### 📅 Período CRE")
        cre_start = st.slider("Ano inicial", 2005, 2025, 2015, key="cre_start")

    # Tabs internas
    tab_credit, tab_rates, tab_market, tab_resources = st.tabs([
        "📊 Crédito & Delinquência",
        "📈 Taxas & Spreads",
        "🏠 Mercado Imobiliário",
        "📚 Recursos & Referências",
    ])

    if st.button("📊 Carregar dados CRE", key="load_cre"):
        with st.spinner("Carregando dados do FRED..."):
            result = get_fred_series(FRED_CRE_SERIES, f"{cre_start}-01-01")
            if isinstance(result, tuple):
                st.session_state["data_cre"] = result[0]
                st.session_state["cre_errors"] = result[1]
            else:
                st.session_state["data_cre"] = result
                st.session_state["cre_errors"] = []

    df_cre = st.session_state.get("data_cre", pd.DataFrame())
    cre_errors = st.session_state.get("cre_errors", [])

    if df_cre.empty:
        if "data_cre" in st.session_state:
            st.error("Não foi possível carregar dados do FRED.")
            if cre_errors:
                with st.expander("Ver erros"):
                    for e in cre_errors[:10]:
                        st.text(e)
    else:
        st.success(f"✅ {len(df_cre.columns)} séries carregadas do FRED")

    def cre_chart(col, title, color="#2563eb"):
        if col not in df_cre.columns:
            return None
        serie = df_cre[col].dropna()
        if len(serie) == 0:
            return None
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=serie.index, y=serie.values, mode="lines",
            name=col, line=dict(color=color, width=2.5),
            hovertemplate="%{x|%b %Y}<br>%{y:.2f}<extra></extra>",
        ))
        last = serie.iloc[-1]
        fig.add_annotation(
            x=serie.index[-1], y=last,
            text=f"<b>{last:.2f}</b>", showarrow=True, arrowhead=2,
            arrowcolor=color, font=dict(size=12, color="#fff"),
            bgcolor=color, bordercolor=color, ax=40, ay=-25,
        )
        fig.update_layout(
            title=dict(text=title, font=dict(size=15, color="#111827")),
            template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="#ffffff", height=380,
            margin=dict(l=50, r=50, t=50, b=40), hovermode="x unified",
            xaxis=dict(gridcolor="#e5e7eb", linecolor="#d1d5db"),
            yaxis=dict(gridcolor="#e5e7eb", linecolor="#d1d5db"),
        )
        return fig

    with tab_credit:
        st.markdown("### Qualidade de Crédito CRE")

        if df_cre.empty:
            st.info("⏳ Clique em \"Carregar dados CRE\" acima para visualizar.")
        else:
            # Métricas
            metrics_credit = [
                ("CRE Delinquency Rate (%)", "CRE Delinq."),
                ("Residential Mortgage Delinquency (%)", "Resid. Delinq."),
                ("All Loans Delinquency (%)", "All Loans Delinq."),
            ]
            cols_m = st.columns(len(metrics_credit))
            for i, (col_name, label) in enumerate(metrics_credit):
                if col_name in df_cre.columns:
                    s = df_cre[col_name].dropna()
                    if len(s) > 1:
                        val, prev = s.iloc[-1], s.iloc[-2]
                        delta = f"{val - prev:+.2f} pp"
                        with cols_m[i]:
                            st.metric(label, f"{val:.2f}%", delta=delta)

            for col_name in ["CRE Delinquency Rate (%)", "CRE Charge-Off Rate (%)", "CRE Loans Outstanding ($B)"]:
                fig = cre_chart(col_name, col_name, "#dc2626" if "Delinq" in col_name or "Charge" in col_name else "#2563eb")
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

    with tab_rates:
        st.markdown("### Taxas de Juros & Spreads")

        if df_cre.empty:
            st.info("⏳ Clique em \"Carregar dados CRE\" acima para visualizar.")
        else:
            metrics_rates = [
                ("30Y Mortgage Rate (%)", "Mortgage 30Y"),
                ("10Y Treasury (%)", "UST 10Y"),
                ("Fed Funds Rate (%)", "Fed Funds"),
                ("BAA Corporate Spread (%)", "BAA Spread"),
            ]
            cols_r = st.columns(len(metrics_rates))
            for i, (col_name, label) in enumerate(metrics_rates):
                if col_name in df_cre.columns:
                    s = df_cre[col_name].dropna()
                    if len(s) > 0:
                        with cols_r[i]:
                            st.metric(label, f"{s.iloc[-1]:.2f}%")

            # Yield curve proxy
            if "10Y Treasury (%)" in df_cre.columns and "2Y Treasury (%)" in df_cre.columns:
                spread = (df_cre["10Y Treasury (%)"] - df_cre["2Y Treasury (%)"]).dropna()
                fig_spread = go.Figure()
                fig_spread.add_trace(go.Scatter(
                    x=spread.index, y=spread.values, mode="lines",
                    fill="tozeroy", line=dict(color="#2563eb", width=2),
                    fillcolor="rgba(37,99,235,0.1)",
                    hovertemplate="%{x|%b %Y}<br>Spread: %{y:.2f}%<extra></extra>",
                ))
                fig_spread.add_hline(y=0, line_dash="dash", line_color="#dc2626", opacity=0.7)
                last_sp = spread.iloc[-1]
                fig_spread.add_annotation(
                    x=spread.index[-1], y=last_sp,
                    text=f"<b>{last_sp:.2f}%</b>", showarrow=True, arrowhead=2,
                    arrowcolor="#2563eb", font=dict(size=12, color="#fff"),
                    bgcolor="#2563eb", ax=40, ay=-25,
                )
                fig_spread.update_layout(
                    title=dict(text="Yield Curve Spread (10Y - 2Y)", font=dict(size=15, color="#111827")),
                    template="plotly_white", paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="#ffffff", height=380,
                    margin=dict(l=50, r=50, t=50, b=40),
                    xaxis=dict(gridcolor="#e5e7eb"), yaxis=dict(gridcolor="#e5e7eb", title="Spread (%)"),
                )
                st.plotly_chart(fig_spread, use_container_width=True)

            for col_name in ["30Y Mortgage Rate (%)", "10Y Treasury (%)", "BAA Corporate Spread (%)"]:
                fig = cre_chart(col_name, col_name, "#ea580c" if "Spread" in col_name else "#2563eb")
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

    with tab_market:
        st.markdown("### Indicadores do Mercado Imobiliário")

        if df_cre.empty:
            st.info("⏳ Clique em \"Carregar dados CRE\" acima para visualizar.")
        else:
            for col_name in ["Case-Shiller US Home Price Index", "Housing Starts (thousands)", "Building Permits (thousands)", "CPI Shelter (%)"]:
                fig = cre_chart(col_name, col_name, "#16a34a")
                if fig:
                    st.plotly_chart(fig, use_container_width=True)

    with tab_resources:
        st.markdown("### 📚 Recursos para CRE Lending")

        st.markdown("""
        #### 🔗 Fontes de Dados Gratuitas

        **Macro & Crédito (séries FRED usadas acima)**
        - [FRED - CRE Series](https://fred.stlouisfed.org/tags/series?t=commercial%3Breal+estate) — 277 séries de commercial real estate
        - [Fed Charge-Off & Delinquency Rates](https://www.federalreserve.gov/releases/chargeoff/) — dados trimestrais por tipo de loan
        - [MBA CREF Research](https://www.mba.org/news-and-research/research-and-economics/commercial-multifamily-research) — delinquency reports por capital source

        **Mercado & Transações**
        - [NCREIF](https://www.ncreif.org/) — property index, cap rates por tipo de ativo
        - [Real Capital Analytics / MSCI](https://www.msci.com/real-capital-analytics) — transaction volume, pricing trends
        - [CoStar / LoopNet](https://www.costar.com/) — listagens e analytics (parcialmente grátis)
        - [Reonomy](https://www.reonomy.com/) — ownership, debt, property data

        **CMBS & Structured**
        - [CREFC](https://www.crefc.org/) — CMBS market standards, Investor Reporting Package
        - [Trepp](https://www.trepp.com/) — CMBS delinquency, surveillance (reports grátis)
        - [KBRA](https://www.kbra.com/) — ratings e research de CMBS

        **Research & Análise**
        - [Green Street](https://www.greenstreet.com/) — setor analysis, cap rate forecasts
        - [CBRE Research](https://www.cbre.com/insights) — market outlook, cap rate surveys
        - [JLL Research](https://www.jll.com/en/trends-and-insights) — office, industrial, retail trends
        - [Cushman & Wakefield](https://www.cushmanwakefield.com/en/insights) — market reports

        ---

        #### 📰 News Feeds Essenciais para CRE

        - [Commercial Observer](https://commercialobserver.com/) — deals, lending, NYC/national
        - [The Real Deal](https://therealdeal.com/) — transactions, development, finance
        - [Bisnow](https://www.bisnow.com/) — CRE news por mercado e setor
        - [CRE Daily](https://www.credaily.com/) — newsletter diária CRE
        - [GlobeSt](https://www.globest.com/) — CRE finance, investment, development
        - [Mortgage Bankers Association](https://www.mba.org/news-and-research/newsroom) — policy, origination data

        ---

        #### 🐍 Repositórios & Tools

        - [`fredapi`](https://github.com/mortada/fredapi) — Python wrapper para FRED API (precisa de key gratuita)
        - [`pandas-datareader`](https://github.com/pydata/pandas-datareader) — pull direto do FRED, World Bank, etc.
        - [`OpenBB`](https://github.com/OpenBB-finance/OpenBB) — inclui módulos de economia e real estate
        - [ATTOM API](https://www.attomdata.com/) — property data API (freemium)
        - [Zillow API / ZTRAX](https://www.zillow.com/research/) — research data downloads grátis

        ---

        #### 📖 Leituras Chave

        - *"Real Estate Finance and Investments"* — Brueggeman & Fisher (textbook padrão)
        - *"Commercial Real Estate Analysis and Investments"* — Geltner, Miller et al.
        - *"The Handbook of Commercial Mortgage-Backed Securities"* — Fabozzi & Jacob
        - Fed Financial Stability Reports — seção de CRE sempre relevante
        - FDIC Quarterly Banking Profile — exposição bancária a CRE
        """)

    # ─── CRE News ────────────────────────────────────────────────────────

    st.markdown("---")
    st.markdown("### 📰 Notícias CRE")

    CRE_RSS = {
        "Commercial Observer": "https://commercialobserver.com/feed/",
        "Multi-Housing News": "https://www.multihousingnews.com/feed/",
        "Bisnow National": "https://www.bisnow.com/feed/national/news",
        "HousingWire": "https://www.housingwire.com/feed/",
    }

    cre_news_tabs = st.tabs(list(CRE_RSS.keys()))
    for tab, (source, url) in zip(cre_news_tabs, CRE_RSS.items()):
        with tab:
            items = fetch_rss_feed(url, max_items=12)
            if items:
                for item in items:
                    title = item["title"]
                    link = item["link"]
                    pub = item["published"][:25] if item["published"] else ""
                    summ = item["summary"][:150] + "..." if len(item["summary"]) > 150 else item["summary"]
                    st.markdown(
                        f'<div class="news-card">'
                        f'<a href="{link}" target="_blank" class="news-link">{title}</a>'
                        f'<p class="news-date">{pub}</p>'
                        f'<p class="news-summary">{summ}</p></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.caption(f"⚠️ Feed indisponível")



# =============================================================================
# PAGE: NOTÍCIAS
# =============================================================================

elif page == "📰 Notícias":

    st.markdown("# 📰 Notícias do Mercado")
    st.markdown("Feeds RSS atualizados a cada 15 min")

    def render_news_items(items):
        """Renderiza lista de notícias."""
        if not items:
            st.caption("⚠️ Feed indisponível ou vazio")
            return
        for item in items:
            title = item["title"]
            link = item["link"]
            pub = item["published"][:25] if item["published"] else ""
            summ = item["summary"][:150] + "..." if len(item["summary"]) > 150 else item["summary"]
            st.markdown(
                f'<div class="news-card">'
                f'<a href="{link}" target="_blank" class="news-link">{title}</a>'
                f'<p class="news-date">{pub}</p>'
                f'<p class="news-summary">{summ}</p></div>',
                unsafe_allow_html=True,
            )

    for region, sources in RSS_FEEDS_SECTIONED.items():
        st.markdown(f"## {region}")

        # Tabs por fonte
        source_tabs = st.tabs(list(sources.keys()))

        for src_tab, (source_name, sections) in zip(source_tabs, sources.items()):
            with src_tab:
                if len(sections) == 1:
                    # Fonte sem seções — mostra direto
                    url = list(sections.values())[0]
                    items = fetch_rss_feed(url, max_items=15)
                    render_news_items(items)
                else:
                    # Fonte com seções — tabs internas
                    section_tabs = st.tabs(list(sections.keys()))
                    for sec_tab, (sec_name, sec_url) in zip(section_tabs, sections.items()):
                        with sec_tab:
                            items = fetch_rss_feed(sec_url, max_items=12)
                            render_news_items(items)

        st.markdown("---")

    if st.button("🔄 Atualizar notícias"):
        st.cache_data.clear()
        st.rerun()
