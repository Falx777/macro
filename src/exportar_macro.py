import base64
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from bcb import Expectativas
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

START = pd.Timestamp("2003-01-01")
ANO_EXPECTATIVA_BCB = 2026

MARCAR_EVENTOS = True
MARCAR_MANDATOS_PRESIDENTES = True
MARCAR_QUEBRA_PNAD = True
MOSTRAR_FOTOS = True

PRESIDENT_PHOTOS = {
    "Dilma": "imagens/dilma.png",
    "Temer": "imagens/temer.png",
    "Bolsonaro": "imagens/bolsonaro.png",
    "Lula": "imagens/lula.png",
}

MANDATOS_BRASIL = [
    ("Lula 1", "2003-01-01", "Lula"),
    ("Lula 2", "2007-01-01", "Lula"),
    ("Dilma 1", "2011-01-01", "Dilma"),
    ("Dilma 2", "2015-01-01", "Dilma"),
    ("Temer", "2016-08-31", "Temer"),
    ("Bolsonaro", "2019-01-01", "Bolsonaro"),
    ("Lula 3", "2023-01-01", "Lula"),
]

EVENTOS = [("Início da pandemia de COVID-19", "2020-03-01")]
QUEBRAS_PNAD = [("COVID-19", "2020-03-01")]

BANDAS_META = [
    ("2003-01-01", "2003-12-31", 2.5),
    ("2004-01-01", "2004-12-31", 2.5),
    ("2005-01-01", "2005-12-31", 2.5),
    ("2006-01-01", "2015-12-31", 2.0),
    ("2016-01-01", "2016-12-31", 2.0),
    ("2017-01-01", "2017-12-31", 1.5),
    ("2018-01-01", "2018-12-31", 1.5),
    ("2019-01-01", "2024-12-31", 1.5),
    ("2025-01-01", "2099-12-31", 1.5),
]

IPCA_SGS = {
    433: "IPCA geral",
    1635: "Alimentação e bebidas",
    1636: "Habitação",
    1637: "Artigos de residência",
    1638: "Vestuário",
    1639: "Transportes",
    1640: "Comunicação",
    1641: "Saúde e cuidados pessoais",
    1642: "Despesas pessoais",
    1643: "Educação",
}

PRODUCAO = {
    "90687": "Agropecuária - total",
    "90691": "Indústria - total",
    "90696": "Serviços - total",
    "90705": "Valor adicionado a preços básicos",
}

DESPESAS = {
    "93404": "Despesa de consumo das famílias",
    "93405": "Despesa de consumo da administração pública",
    "93406": "Formação bruta de capital fixo",
    "93407": "Exportação de bens e serviços",
    "93408": "Importação de bens e serviços (-)",
    "90707": "PIB a preços de mercado",
}

ALL_CATS = list(PRODUCAO) + list(DESPESAS)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "macro-github-pages/1.0"})
SESSION.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=5,
            connect=5,
            read=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
    ),
)


def sgs_series(codigo, nome, start=START):
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
    cursor = pd.Timestamp(start).normalize()
    end_all = pd.Timestamp.today().normalize()
    data = []
    while cursor <= end_all:
        end = min(cursor + pd.DateOffset(years=9) - pd.Timedelta(days=1), end_all)
        params = {
            "formato": "json",
            "dataInicial": cursor.strftime("%d/%m/%Y"),
            "dataFinal": end.strftime("%d/%m/%Y"),
        }
        chunk = None
        last_text = ""
        for tentativa in range(5):
            try:
                r = SESSION.get(url, params=params, timeout=60)
                last_text = r.text if r is not None else ""
                if r.status_code in (429, 502, 503, 504):
                    time.sleep(2 ** tentativa)
                    continue
                r.raise_for_status()
                if not r.text or not r.text.strip():
                    time.sleep(2 ** tentativa)
                    continue
                parsed = r.json()
                if not isinstance(parsed, list):
                    time.sleep(2 ** tentativa)
                    continue
                chunk = parsed
                break
            except (requests.RequestException, ValueError) as exc:
                if tentativa == 4:
                    raise RuntimeError(
                        f"Falha ao obter/decodificar SGS {codigo} ({cursor:%Y-%m-%d} a {end:%Y-%m-%d}): {last_text[:200]}"
                    ) from exc
                time.sleep(2 ** tentativa)
        if chunk:
            data.extend(chunk)
        cursor = end + pd.Timedelta(days=1)
        time.sleep(0.35)
    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=["data", "valor", "codigo", "serie"])
    df["data"] = pd.to_datetime(df["data"], dayfirst=True, errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"].astype(str).str.replace(",", "."), errors="coerce")
    df = df.dropna(subset=["data"]).sort_values("data")
    df["codigo"] = codigo
    df["serie"] = nome
    return df


def ipea_series(codigo, nome, tema=None, start=START):
    url = f"https://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{codigo}')"
    for tentativa in range(5):
        try:
            r = SESSION.get(url, timeout=90)
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** tentativa)
                continue
            r.raise_for_status()
            break
        except requests.RequestException:
            if tentativa == 4:
                raise
            time.sleep(2 ** tentativa)
    df = pd.DataFrame(r.json().get("value", []))
    if df.empty:
        raise ValueError(f"IPEADATA retornou série vazia: {codigo}")
    df["data"] = pd.to_datetime(df["VALDATA"], errors="coerce", utc=True).dt.tz_convert(None)
    df["valor"] = pd.to_numeric(df["VALVALOR"], errors="coerce")
    df = df.dropna(subset=["data", "valor"]).sort_values("data")
    df = df[df["data"] >= pd.Timestamp(start)].copy()
    df["codigo"] = codigo
    df["serie"] = nome
    return df


def parse_quarter(code):
    s = str(code).strip()
    return pd.Period(year=int(s[:4]), quarter=int(s[-2:]), freq="Q")


def sidra_series(table, variable, categories, start_year=2016):
    desc_url = f"https://apisidra.ibge.gov.br/DescritoresTabela/t/{table}"
    r_desc = SESSION.get(desc_url, timeout=60)
    r_desc.raise_for_status()
    desc = r_desc.json()
    class_id = desc["Classificacoes"][0]["Id"]

    url = f"https://apisidra.ibge.gov.br/values/t/{table}/n1/1/v/{variable}/p/all/c{class_id}/all"
    raw = None
    for tentativa in range(5):
        try:
            r = SESSION.get(url, timeout=120)
            if r.status_code in (429, 502, 503, 504):
                time.sleep(2 ** tentativa)
                continue
            r.raise_for_status()
            raw = r.json()
            break
        except (requests.RequestException, ValueError) as exc:
            if tentativa == 4:
                raise RuntimeError(f"Falha ao consultar SIDRA tabela {table}, variável {variable}") from exc
            time.sleep(2 ** tentativa)

    df = pd.DataFrame(raw[1:])
    df = df.rename(
        columns={
            "D3C": "periodo_codigo",
            "D4C": "categoria_codigo",
            "D4N": "categoria",
            "V": "valor",
        }
    )
    df["valor"] = pd.to_numeric(df["valor"].replace("..", np.nan), errors="coerce")
    df["trimestre"] = df["periodo_codigo"].map(parse_quarter)
    df["data"] = df["trimestre"].dt.start_time
    df = df[df["trimestre"].dt.year >= start_year].copy()
    wanted = {str(k) for k in categories}
    df = df[df["categoria_codigo"].astype(str).isin(wanted)].copy()
    return df.sort_values(["categoria", "trimestre"])


def to_iso_list(series_dt):
    return pd.DatetimeIndex(pd.to_datetime(series_dt)).strftime("%Y-%m-%d").tolist()


def to_num_list(series_num):
    return [None if pd.isna(v) else round(float(v), 4) for v in series_num]


def df_to_series_dict(df_wide):
    return {col: to_num_list(df_wide[col]) for col in df_wide.columns}


def resumo_destaque(df, col, maximize="abs"):
    valid = df.dropna(subset=["data", col]).sort_values("data").reset_index(drop=True)
    if valid.empty:
        return None
    idx = valid[col].abs().idxmax() if maximize == "abs" else valid[col].idxmax()
    ext = valid.loc[idx]
    ult = valid.iloc[-1]
    return {
        "extremo_data": ext["data"].strftime("%Y-%m-%d"),
        "extremo_valor": round(float(ext[col]), 4),
        "ultimo_data": ult["data"].strftime("%Y-%m-%d"),
        "ultimo_valor": round(float(ult[col]), 4),
    }



def ultimo_registro(df, coluna="valor"):
    """Retorna valor e data da observação mais recente não nula."""
    valid = df.dropna(subset=["data", coluna]).sort_values("data")
    if valid.empty:
        return None
    row = valid.iloc[-1]
    return {
        "data": row["data"].strftime("%Y-%m-%d"),
        "valor": round(float(row[coluna]), 4),
    }


def variacao_desde(df, coluna, dias):
    """Variação percentual contra a última observação em/antes da data de referência."""
    valid = df.dropna(subset=["data", coluna]).sort_values("data")
    if len(valid) < 2:
        return None
    atual = valid.iloc[-1]
    corte = atual["data"] - pd.Timedelta(days=dias)
    anteriores = valid[valid["data"] <= corte]
    if anteriores.empty:
        return None
    base = anteriores.iloc[-1]
    if float(base[coluna]) == 0:
        return None
    return {
        "data_base": base["data"].strftime("%Y-%m-%d"),
        "valor_base": round(float(base[coluna]), 4),
        "variacao_pct": round((float(atual[coluna]) / float(base[coluna]) - 1) * 100, 4),
    }


def ponto_trimestral(df, trimestre, categoria):
    if categoria not in df.columns or trimestre not in df.index or pd.isna(df.loc[trimestre, categoria]):
        return None
    return round(float(df.loc[trimestre, categoria]), 4)


def data_trimestre(periodo):
    return f"{periodo.year}-T{periodo.quarter}"


def carregar_fotos_b64():
    if not MOSTRAR_FOTOS:
        return {}
    out = {}
    for pessoa, rel_path in PRESIDENT_PHOTOS.items():
        p = Path(rel_path)
        if p.exists():
            b64 = base64.b64encode(p.read_bytes()).decode("ascii")
            out[pessoa] = f"data:image/png;base64,{b64}"
    return out


def main():
    # 1. IPCA mensal -> acumulado 12m + meta e banda
    ipca_mensal = pd.concat([sgs_series(c, n) for c, n in IPCA_SGS.items()], ignore_index=True)
    wide = ipca_mensal.pivot_table(index="data", columns="serie", values="valor", aggfunc="last").sort_index()
    ipca_12m_df = ((1 + wide / 100).rolling(12, min_periods=12).apply(np.prod, raw=True) - 1) * 100

    meta = sgs_series(13521, "Meta de inflação")
    meta["ano"] = meta["data"].dt.year
    meta = meta.drop_duplicates("ano", keep="last").set_index("ano")["valor"]

    cal = pd.DataFrame(index=ipca_12m_df.index)
    cal["ipca_geral_12m"] = ipca_12m_df["IPCA geral"]
    cal["meta_pct"] = cal.index.year.map(meta)
    cal["banda_pp"] = np.nan
    for a, b, band in BANDAS_META:
        mask = cal.index.to_series().between(pd.Timestamp(a), pd.Timestamp(b))
        cal.loc[mask, "banda_pp"] = band
    cal["limite_inferior"] = cal["meta_pct"] - cal["banda_pp"]
    cal["limite_superior"] = cal["meta_pct"] + cal["banda_pp"]

    ipca_componentes = {
        col: {
            "datas": to_iso_list(ipca_12m_df.index),
            "valores": to_num_list(ipca_12m_df[col]),
        }
        for col in ipca_12m_df.columns
    }

    # 2. Expectativas anuais BCB (IPCA e Selic)
    em = Expectativas()
    ep = em.get_endpoint("ExpectativasMercadoAnuais")

    try:
        q_ipca = (
            ep.query()
            .filter(ep.Indicador.isin(["IPCA"]))
            .select(ep.Data, ep.Indicador, ep.DataReferencia, ep.Media, ep.Mediana)
        )
    except Exception:
        q_ipca = (
            ep.query()
            .filter(ep.Indicador == "IPCA")
            .select(ep.Data, ep.Indicador, ep.DataReferencia, ep.Media, ep.Mediana)
        )
    exp_ipca = q_ipca.collect()
    exp_ipca["Data"] = pd.to_datetime(exp_ipca["Data"], errors="coerce")
    exp_ipca = exp_ipca.dropna(subset=["Data"]).copy()
    exp_ipca["DataReferencia"] = exp_ipca["DataReferencia"].astype(str)
    exp_ipca_cons = exp_ipca.groupby(["Data", "DataReferencia"], as_index=False).agg(
        Media=("Media", "median"), Mediana=("Mediana", "median")
    )
    latest_ipca_date = exp_ipca_cons["Data"].max()
    exp_ipca_lat = exp_ipca_cons[exp_ipca_cons["Data"] == latest_ipca_date].copy()
    if ANO_EXPECTATIVA_BCB is not None:
        exp_ipca_lat = exp_ipca_lat[exp_ipca_lat.DataReferencia == str(ANO_EXPECTATIVA_BCB)]
    else:
        ano_ref = str(latest_ipca_date.year if latest_ipca_date.month < 11 else latest_ipca_date.year + 1)
        cand = exp_ipca_lat[exp_ipca_lat.DataReferencia == ano_ref]
        if not cand.empty:
            exp_ipca_lat = cand

    exp_ipca_ponto = None
    if not exp_ipca_lat.empty:
        r0 = exp_ipca_lat.iloc[0]
        exp_ipca_ponto = {
            "data": latest_ipca_date.strftime("%Y-%m-%d"),
            "ano_referencia": str(r0["DataReferencia"]),
            "media": round(float(r0["Media"]), 4),
        }

    # 3. Selic efetiva + expectativa anual Selic
    selic = sgs_series(432, "Meta Selic definida pelo Copom").dropna(subset=["valor"])
    qs = (
        ep.query()
        .filter(ep.Indicador == "Selic")
        .select(ep.Data, ep.Indicador, ep.DataReferencia, ep.Media, ep.Mediana)
    )
    ex_selic = qs.collect()
    ex_selic["Data"] = pd.to_datetime(ex_selic["Data"], errors="coerce")
    ex_selic = ex_selic.dropna(subset=["Data"]).copy()
    ex_selic["DataReferencia"] = ex_selic["DataReferencia"].astype(str)
    ex_selic_cons = ex_selic.groupby(["Data", "DataReferencia"], as_index=False).agg(
        Media=("Media", "median"), Mediana=("Mediana", "median")
    )
    latest_selic_date = ex_selic_cons["Data"].max()
    ex_selic_lat = ex_selic_cons[ex_selic_cons["Data"] == latest_selic_date].copy()
    anos_ref = pd.to_numeric(ex_selic_lat["DataReferencia"], errors="coerce")
    anos_futuros = anos_ref[anos_ref >= latest_selic_date.year]
    ano_sel = int(anos_futuros.min()) if not anos_futuros.empty else int(anos_ref.max())
    ex_selic_lat = ex_selic_lat[pd.to_numeric(ex_selic_lat["DataReferencia"], errors="coerce") == ano_sel].head(1)

    exp_selic_ponto = None
    if not ex_selic_lat.empty:
        s0 = ex_selic_lat.iloc[0]
        exp_selic_ponto = {
            "data": latest_selic_date.strftime("%Y-%m-%d"),
            "ano_referencia": str(s0["DataReferencia"]),
            "media": round(float(s0["Media"]), 4),
        }

    # 4. Taxa de desocupação (IPEADATA)
    des = ipea_series("PNADC12_TDESOC12", "Taxa de desocupação (14 anos ou mais)")

    payload = {
        "gerado_em_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "config": {
            "marcar_eventos": MARCAR_EVENTOS,
            "marcar_mandatos_presidentes": MARCAR_MANDATOS_PRESIDENTES,
            "marcar_quebra_pnad": MARCAR_QUEBRA_PNAD,
            "mandatos": [
                {"mandato": m, "inicio": d, "presidente": p}
                for m, d, p in MANDATOS_BRASIL
            ],
            "eventos": [{"label": l, "data": d} for l, d in EVENTOS],
            "quebras_pnad": [{"label": l, "data": d} for l, d in QUEBRAS_PNAD],
            "fotos_b64": carregar_fotos_b64(),
        },
        "ipca_componentes": ipca_componentes,
        "ipca_meta": {
            "datas": to_iso_list(cal.index),
            "ipca_12m": to_num_list(cal["ipca_geral_12m"]),
            "meta_pct": to_num_list(cal["meta_pct"]),
            "limite_inferior": to_num_list(cal["limite_inferior"]),
            "limite_superior": to_num_list(cal["limite_superior"]),
            "expectativa": exp_ipca_ponto,
        },
        "selic": {
            "datas": to_iso_list(selic["data"]),
            "valores": to_num_list(selic["valor"]),
            "expectativa": exp_selic_ponto,
        },
        "desemprego": {
            "datas": to_iso_list(des["data"]),
            "valores": to_num_list(des["valor"]),
        },
    }

    # 5. PIB SIDRA 1621 (índice encadeado) e 6613 (valores encadeados)
    gdp1621 = sidra_series(1621, 584, ALL_CATS, start_year=2016)
    gdp6613 = sidra_series(6613, 9319, ALL_CATS, start_year=2016)

    idx = gdp1621.pivot_table(index="trimestre", columns="categoria", values="valor", aggfunc="last").sort_index()
    qoq = (idx.pct_change() * 100).dropna(how="all")
    yoy = ((idx / idx.shift(4) - 1) * 100).dropna(how="all")

    last_q = yoy.index.max()
    yoy_recent = yoy[yoy.index >= last_q - 3]

    val = gdp6613.pivot_table(index="trimestre", columns="categoria", values="valor", aggfunc="last").sort_index()
    roll4 = val.rolling(4, min_periods=4).sum()

    shares_prod = pd.DataFrame(index=roll4.index)
    for name in PRODUCAO.values():
        if (
            name != "Valor adicionado a preços básicos"
            and name in roll4
            and "Valor adicionado a preços básicos" in roll4
        ):
            shares_prod[name] = 100 * roll4[name] / roll4["Valor adicionado a preços básicos"]
    shares_prod = shares_prod.dropna(how="all")
    shares_prod_recent = shares_prod[shares_prod.index >= shares_prod.index.max() - 3]

    shares_desp = pd.DataFrame(index=roll4.index)
    for name in DESPESAS.values():
        if (
            name != "PIB a preços de mercado"
            and name in roll4
            and "PIB a preços de mercado" in roll4
        ):
            shares_desp[name] = 100 * roll4[name] / roll4["PIB a preços de mercado"]
    shares_desp = shares_desp.dropna(how="all")
    shares_desp_recent = shares_desp[shares_desp.index >= shares_desp.index.max() - 3]

    prod_cols = [c for c in PRODUCAO.values() if c in idx.columns]
    desp_cols = [c for c in DESPESAS.values() if c in idx.columns]

    payload["pib"] = {
        "qoq_datas": pd.DatetimeIndex(qoq.index.to_timestamp()).strftime("%Y-%m-%d").tolist(),
        "qoq_producao": df_to_series_dict(qoq[prod_cols]),
        "qoq_despesas": df_to_series_dict(qoq[desp_cols]),
        "yoy_datas": pd.DatetimeIndex(yoy.index.to_timestamp()).strftime("%Y-%m-%d").tolist(),
        "yoy_producao": df_to_series_dict(yoy[prod_cols]),
        "yoy_despesas": df_to_series_dict(yoy[desp_cols]),
        "yoy_recent_datas": pd.DatetimeIndex(yoy_recent.index.to_timestamp()).strftime("%Y-%m-%d").tolist(),
        "yoy_recent_producao": df_to_series_dict(yoy_recent[prod_cols]),
        "yoy_recent_despesas": df_to_series_dict(yoy_recent[desp_cols]),
        "part_recent_prod_datas": pd.DatetimeIndex(shares_prod_recent.index.to_timestamp()).strftime("%Y-%m-%d").tolist(),
        "part_recent_producao": df_to_series_dict(shares_prod_recent),
        "part_recent_desp_datas": pd.DatetimeIndex(shares_desp_recent.index.to_timestamp()).strftime("%Y-%m-%d").tolist(),
        "part_recent_despesas": df_to_series_dict(shares_desp_recent),
    }

    # 6. Câmbio diário, NFSP (nominal e primário), Dívida Bruta e Ibovespa
    cambio_comercial = ipea_series("GM366_ERV366", "Câmbio comercial venda — média (R$/US$)", "07_cambio")
    cambio_turismo = ipea_series("GM366_ERTUR366", "Câmbio turismo venda — média (R$/US$)", "07_cambio")

    cambio_diario = (
        cambio_comercial[["data", "valor"]]
        .rename(columns={"valor": "comercial_R$_por_USD"})
        .merge(
            cambio_turismo[["data", "valor"]].rename(columns={"valor": "turismo_R$_por_USD"}),
            on="data",
            how="outer",
        )
        .sort_values("data")
        .reset_index(drop=True)
    )
    ref_comercial = pd.merge_asof(
        cambio_diario[["data"]].sort_values("data"),
        cambio_comercial[["data", "valor"]]
        .rename(columns={"valor": "comercial_referencia_ate_3dias"})
        .sort_values("data"),
        on="data",
        direction="nearest",
        tolerance=pd.Timedelta(days=3),
    )
    cambio_diario["comercial_referencia_ate_3dias"] = ref_comercial["comercial_referencia_ate_3dias"].to_numpy()
    cambio_diario["razao_turismo_comercial"] = (
        cambio_diario["turismo_R$_por_USD"] / cambio_diario["comercial_referencia_ate_3dias"]
    )
    cambio_diario["turismo_alerta_discrepancia"] = (
        cambio_diario["comercial_referencia_ate_3dias"].notna()
        & cambio_diario["turismo_R$_por_USD"].notna()
        & ~cambio_diario["razao_turismo_comercial"].between(0.5, 1.5)
    )
    cambio_diario["turismo_plot_R$_por_USD"] = cambio_diario["turismo_R$_por_USD"].where(
        ~cambio_diario["turismo_alerta_discrepancia"]
    )

    nominal_fonte = ipea_series("BM12_NFSPNNAS12", "NFSP nominal — fonte IPEADATA (R$ milhões)", "08_deficit_nominal")
    nominal_tratado = nominal_fonte[["data", "valor"]].copy()
    nominal_tratado["deficit_R$_bilhoes"] = -nominal_tratado["valor"] / 1000.0

    divida_bruta = sgs_series(13762, "Dívida bruta do governo geral (% PIB) — metodologia a partir de 2008")

    primario_fonte = ipea_series("BM12_NFSPPNAS12", "NFSP primária — fonte IPEADATA (R$ milhões)", "10_deficit_primario")
    primario_tratado = primario_fonte[["data", "valor"]].copy()
    primario_tratado["resultado_primario_sinal_invertido_R$_bilhoes"] = -primario_tratado["valor"] / 1000.0

    ibovespa = ipea_series("GM366_IBVSP366", "Índice de ações — Ibovespa — fechamento", "11_ibovespa", start=START)
    volatilidade_ibovespa = ipea_series(
        "GM366_IBVSPV366",
        "Volatilidade do índice de ações — Ibovespa — fechamento",
        "12_volatilidade_ibovespa",
        start=START,
    )

    payload["novos_temas"] = {
        "cambio": {
            "datas": to_iso_list(cambio_diario["data"]),
            "comercial": to_num_list(cambio_diario["comercial_R$_por_USD"]),
            "turismo_plot": to_num_list(cambio_diario["turismo_plot_R$_por_USD"]),
        },
        "deficit_nominal": {
            "datas": to_iso_list(nominal_tratado["data"]),
            "valores": to_num_list(nominal_tratado["deficit_R$_bilhoes"]),
            "destaque": resumo_destaque(nominal_tratado, "deficit_R$_bilhoes", maximize="abs"),
        },
        "divida_bruta": {
            "datas": to_iso_list(divida_bruta["data"]),
            "valores": to_num_list(divida_bruta["valor"]),
            "destaque": resumo_destaque(divida_bruta, "valor", maximize="value"),
        },
        "deficit_primario": {
            "datas": to_iso_list(primario_tratado["data"]),
            "valores": to_num_list(primario_tratado["resultado_primario_sinal_invertido_R$_bilhoes"]),
            "destaque": resumo_destaque(
                primario_tratado, "resultado_primario_sinal_invertido_R$_bilhoes", maximize="abs"
            ),
        },
        "ibovespa": {
            "datas": to_iso_list(ibovespa["data"]),
            "valores": to_num_list(ibovespa["valor"]),
            "destaque": resumo_destaque(ibovespa, "valor", maximize="value"),
        },
        "volatilidade_ibovespa": {
            "datas": to_iso_list(volatilidade_ibovespa["data"]),
            "valores": to_num_list(volatilidade_ibovespa["valor"]),
        },
    }


    # 7. Resumo executivo: último dado, data de referência e fonte
    ipca_valid = cal.dropna(subset=["ipca_geral_12m"]).sort_index()
    ipca_last_date = ipca_valid.index[-1]
    ipca_last = ipca_valid.iloc[-1]
    ipca_comp_last = {}
    for nome in ipca_12m_df.columns:
        serie = ipca_12m_df[nome].dropna()
        if not serie.empty:
            d = serie.index[-1]
            ipca_comp_last[nome] = {
                "valor_pct_12m": round(float(serie.iloc[-1]), 4),
                "data": d.strftime("%Y-%m-%d"),
                "fonte": "Banco Central do Brasil — SGS; cálculo próprio a partir da série mensal",
            }

    selic_last = ultimo_registro(selic)
    des_last = ultimo_registro(des)
    cambio_last = ultimo_registro(cambio_comercial)
    ibov_last = ultimo_registro(ibovespa)
    nominal_last = ultimo_registro(nominal_tratado, "deficit_R$_bilhoes")
    divida_last = ultimo_registro(divida_bruta)
    primario_last = ultimo_registro(primario_tratado, "resultado_primario_sinal_invertido_R$_bilhoes")

    pib_last_q = idx.index.max()
    pib_last_yoy = yoy.loc[pib_last_q] if pib_last_q in yoy.index else pd.Series(dtype=float)
    pib_last_qoq = qoq.loc[pib_last_q] if pib_last_q in qoq.index else pd.Series(dtype=float)

    producao_variacoes = {}
    for nome in PRODUCAO.values():
        producao_variacoes[nome] = {
            "variacao_interanual_pct": (
                round(float(pib_last_yoy[nome]), 4)
                if nome in pib_last_yoy.index and pd.notna(pib_last_yoy[nome]) else None
            ),
            "variacao_trimestral_pct": (
                round(float(pib_last_qoq[nome]), 4)
                if nome in pib_last_qoq.index and pd.notna(pib_last_qoq[nome]) else None
            ),
            "trimestre": data_trimestre(pib_last_q),
            "fonte": "IBGE — SIDRA, tabela 1621; cálculo próprio sobre índice encadeado",
        }

    despesas_variacoes = {}
    for nome in DESPESAS.values():
        despesas_variacoes[nome] = {
            "variacao_interanual_pct": (
                round(float(pib_last_yoy[nome]), 4)
                if nome in pib_last_yoy.index and pd.notna(pib_last_yoy[nome]) else None
            ),
            "variacao_trimestral_pct": (
                round(float(pib_last_qoq[nome]), 4)
                if nome in pib_last_qoq.index and pd.notna(pib_last_qoq[nome]) else None
            ),
            "trimestre": data_trimestre(pib_last_q),
            "fonte": "IBGE — SIDRA, tabela 1621; cálculo próprio sobre índice encadeado",
        }

    # Participações calculadas exclusivamente com os valores do último trimestre.
    part_prod_ultimo = {}
    if not val.empty and "Valor adicionado a preços básicos" in val.columns:
        q = val.index.max()
        denominador = val.loc[q, "Valor adicionado a preços básicos"]
        if pd.notna(denominador) and denominador != 0:
            for nome in PRODUCAO.values():
                if nome != "Valor adicionado a preços básicos" and nome in val.columns:
                    v = val.loc[q, nome]
                    if pd.notna(v):
                        part_prod_ultimo[nome] = round(float(v / denominador * 100), 4)

    part_desp_ultimo = {}
    if not val.empty and "PIB a preços de mercado" in val.columns:
        q = val.index.max()
        denominador = val.loc[q, "PIB a preços de mercado"]
        if pd.notna(denominador) and denominador != 0:
            for nome in DESPESAS.values():
                if nome != "PIB a preços de mercado" and nome in val.columns:
                    v = val.loc[q, nome]
                    if pd.notna(v):
                        part_desp_ultimo[nome] = round(float(v / denominador * 100), 4)

    meta_valor = float(ipca_last["meta_pct"]) if pd.notna(ipca_last["meta_pct"]) else None
    ipca_valor = float(ipca_last["ipca_geral_12m"])
    payload["resumo"] = {
        "gerado_em_utc": payload["gerado_em_utc"],
        "ipca": {
            "data": ipca_last_date.strftime("%Y-%m-%d"),
            "ipca_12m_pct": round(ipca_valor, 4),
            "meta_pct": round(meta_valor, 4) if meta_valor is not None else None,
            "desvio_meta_pontos_percentuais": round(ipca_valor - meta_valor, 4) if meta_valor is not None else None,
            "componentes": ipca_comp_last,
            "fonte": "Banco Central do Brasil — SGS, série 433 (IPCA) e séries 1635–1643 (grupos); meta: SGS 13521",
        },
        "selic": {
            **(selic_last or {}),
            "fonte": "Banco Central do Brasil — SGS, série 432 (Meta Selic definida pelo Copom)",
        },
        "desocupacao": {
            **(des_last or {}),
            "fonte": "IPEA — Ipeadata, série PNADC12_TDESOC12 (PNAD Contínua, 14 anos ou mais)",
        },
        "dolar_comercial": {
            **(cambio_last or {}),
            "variacao_1_semana": variacao_desde(cambio_comercial, "valor", 7),
            "variacao_1_mes": variacao_desde(cambio_comercial, "valor", 30),
            "unidade": "R$/US$",
            "fonte": "IPEA — Ipeadata, série GM366_ERV366 (câmbio comercial venda, média)",
        },
        "ibovespa": {
            **(ibov_last or {}),
            "variacao_1_semana": variacao_desde(ibovespa, "valor", 7),
            "variacao_1_mes": variacao_desde(ibovespa, "valor", 30),
            "unidade": "pontos",
            "fonte": "IPEA — Ipeadata, série GM366_IBVSP366 (fechamento)",
        },
        "resultado_nominal_12m": {
            **(nominal_last or {}),
            "unidade": "R$ bilhões",
            "fonte": "IPEA — Ipeadata, série BM12_NFSPNNAS12; sinal invertido conforme convenção do script",
        },
        "divida_bruta_governo_geral": {
            **(divida_last or {}),
            "unidade": "% do PIB",
            "fonte": "Banco Central do Brasil — SGS, série 13762",
        },
        "resultado_primario_12m": {
            **(primario_last or {}),
            "unidade": "R$ bilhões",
            "fonte": "IPEA — Ipeadata, série BM12_NFSPPNAS12; sinal invertido conforme convenção do script",
        },
        "pib_producao": {
            "trimestre": data_trimestre(pib_last_q),
            "variacoes": producao_variacoes,
            "participacao_ultimo_trimestre_pct": part_prod_ultimo,
            "fonte_participacao": "IBGE — SIDRA, tabela 6613, valores do trimestre; participação sobre valor adicionado a preços básicos",
        },
        "pib_despesas": {
            "trimestre": data_trimestre(pib_last_q),
            "variacoes": despesas_variacoes,
            "participacao_ultimo_trimestre_pct": part_desp_ultimo,
            "fonte_participacao": "IBGE — SIDRA, tabela 6613, valores do trimestre; participação sobre PIB a preços de mercado",
        },
        "metodologia_variacoes_pib": "São informadas a variação contra o trimestre imediatamente anterior (trimestral) e contra o mesmo trimestre do ano anterior (interanual), ambas calculadas sobre o índice encadeado da tabela 1621.",
    }


    # Estrutura tabular pronta para a camada visual (frontend).
    tabela_resumo = []

    def adicionar_linha(indicador, registro, unidade, fonte, data=None):
        if registro is None:
            return
        tabela_resumo.append({
            "indicador": indicador,
            "resultado": registro.get("valor"),
            "unidade": unidade,
            "data": data or registro.get("data"),
            "fonte": fonte,
        })

    adicionar_linha("IPCA — acumulado em 12 meses", {"valor": round(ipca_valor, 4)}, "%", payload["resumo"]["ipca"]["fonte"], ipca_last_date.strftime("%Y-%m-%d"))
    adicionar_linha("Meta de inflação", {"valor": round(meta_valor, 4) if meta_valor is not None else None}, "%", "Banco Central do Brasil — SGS, série 13521", ipca_last_date.strftime("%Y-%m-%d"))
    adicionar_linha("Desvio do IPCA em relação à meta", {"valor": round(ipca_valor - meta_valor, 4) if meta_valor is not None else None}, "p.p.", payload["resumo"]["ipca"]["fonte"], ipca_last_date.strftime("%Y-%m-%d"))
    for nome, registro in ipca_comp_last.items():
        adicionar_linha(f"IPCA — {nome}", {"valor": registro["valor_pct_12m"]}, "% em 12 meses", registro["fonte"], registro["data"])
    adicionar_linha("Selic", selic_last, "% a.a.", payload["resumo"]["selic"]["fonte"])
    adicionar_linha("Taxa de desocupação", des_last, "%", payload["resumo"]["desocupacao"]["fonte"])
    adicionar_linha("Dólar comercial", cambio_last, "R$/US$", payload["resumo"]["dolar_comercial"]["fonte"])
    adicionar_linha("Dólar — variação em 1 semana", {"valor": payload["resumo"]["dolar_comercial"]["variacao_1_semana"]["variacao_pct"], "data": cambio_last["data"]} if cambio_last and payload["resumo"]["dolar_comercial"]["variacao_1_semana"] else None, "%", payload["resumo"]["dolar_comercial"]["fonte"])
    adicionar_linha("Dólar — variação em 1 mês", {"valor": payload["resumo"]["dolar_comercial"]["variacao_1_mes"]["variacao_pct"], "data": cambio_last["data"]} if cambio_last and payload["resumo"]["dolar_comercial"]["variacao_1_mes"] else None, "%", payload["resumo"]["dolar_comercial"]["fonte"])
    adicionar_linha("Ibovespa", ibov_last, "pontos", payload["resumo"]["ibovespa"]["fonte"])
    adicionar_linha("Ibovespa — variação em 1 semana", {"valor": payload["resumo"]["ibovespa"]["variacao_1_semana"]["variacao_pct"], "data": ibov_last["data"]} if ibov_last and payload["resumo"]["ibovespa"]["variacao_1_semana"] else None, "%", payload["resumo"]["ibovespa"]["fonte"])
    adicionar_linha("Ibovespa — variação em 1 mês", {"valor": payload["resumo"]["ibovespa"]["variacao_1_mes"]["variacao_pct"], "data": ibov_last["data"]} if ibov_last and payload["resumo"]["ibovespa"]["variacao_1_mes"] else None, "%", payload["resumo"]["ibovespa"]["fonte"])
    adicionar_linha("Resultado nominal acumulado em 12 meses", nominal_last, "R$ bilhões", payload["resumo"]["resultado_nominal_12m"]["fonte"])
    adicionar_linha("Dívida bruta do governo geral", divida_last, "% do PIB", payload["resumo"]["divida_bruta_governo_geral"]["fonte"])
    adicionar_linha("Resultado primário acumulado em 12 meses", primario_last, "R$ bilhões", payload["resumo"]["resultado_primario_12m"]["fonte"])

    for nome, registro in producao_variacoes.items():
        adicionar_linha(f"PIB — produção — {nome} (interanual)", {"valor": registro["variacao_interanual_pct"]}, "%", registro["fonte"], registro["trimestre"])
        adicionar_linha(f"PIB — produção — {nome} (trimestral)", {"valor": registro["variacao_trimestral_pct"]}, "%", registro["fonte"], registro["trimestre"])
    for nome, registro in despesas_variacoes.items():
        adicionar_linha(f"PIB — despesas — {nome} (interanual)", {"valor": registro["variacao_interanual_pct"]}, "%", registro["fonte"], registro["trimestre"])
        adicionar_linha(f"PIB — despesas — {nome} (trimestral)", {"valor": registro["variacao_trimestral_pct"]}, "%", registro["fonte"], registro["trimestre"])

    payload["resumo"]["tabela"] = tabela_resumo
    payload["resumo"]["graficos_pizza"] = {
        "producao": {
            "trimestre": data_trimestre(pib_last_q),
            "dados": [{"componente": k, "participacao_pct": v} for k, v in part_prod_ultimo.items()],
        },
        "despesas": {
            "trimestre": data_trimestre(pib_last_q),
            "dados": [{"componente": k, "participacao_pct": v} for k, v in part_desp_ultimo.items()],
        },
    }

    out_file = Path("docs/dados/macro_dados.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print("JSON salvo em:", out_file)


if __name__ == "__main__":
    main()
