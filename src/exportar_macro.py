import base64
import json
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from bcb import Expectativas

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

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "macro-github-pages/1.0"})

import time


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
        for tentativa in range(4):
            try:
                r = SESSION.get(url, params=params, timeout=60)
                if r.status_code in (429, 502, 503, 504):
                    time.sleep(2 ** tentativa)
                    continue
                r.raise_for_status()
                break
            except requests.RequestException:
                if tentativa == 3:
                    raise
                time.sleep(2 ** tentativa)
        chunk = r.json()
        if isinstance(chunk, list):
            data.extend(chunk)
        cursor = end + pd.Timedelta(days=1)
        time.sleep(0.3)
    df = pd.DataFrame(data)
    if df.empty:
        return pd.DataFrame(columns=["data", "valor", "codigo", "serie"])
    df["data"] = pd.to_datetime(df["data"], dayfirst=True, errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"].astype(str).str.replace(",", "."), errors="coerce")
    df = df.dropna(subset=["data"]).sort_values("data")
    df["codigo"] = codigo
    df["serie"] = nome
    return df


def ipea_series(codigo, nome, start=START):
    url = f"https://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='{codigo}')"
    r = SESSION.get(url, timeout=90)
    r.raise_for_status()
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


def to_iso_list(series_dt):
    return pd.DatetimeIndex(pd.to_datetime(series_dt)).strftime("%Y-%m-%d").tolist()


def to_num_list(series_num):
    return [None if pd.isna(v) else round(float(v), 4) for v in series_num]


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
        q_ipca = ep.query().filter(ep.Indicador.isin(["IPCA"])).select(
            ep.Data, ep.Indicador, ep.DataReferencia, ep.Media, ep.Mediana
        )
    except Exception:
        q_ipca = ep.query().filter(ep.Indicador == "IPCA").select(
            ep.Data, ep.Indicador, ep.DataReferencia, ep.Media, ep.Mediana
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
    qs = ep.query().filter(ep.Indicador == "Selic").select(
        ep.Data, ep.Indicador, ep.DataReferencia, ep.Media, ep.Mediana
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

    out_file = Path("docs/dados/macro_dados.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print("JSON salvo em:", out_file)


if __name__ == "__main__":
    main()
