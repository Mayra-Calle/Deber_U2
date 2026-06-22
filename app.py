import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sweetviz as sv
import tempfile, os
import warnings
warnings.filterwarnings("ignore")

# Configurar estilo de matplotlib
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10

# ─── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Matrícula UEP 2015-2023",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎓 Análisis de Matrícula – Universidades y Escuelas Politécnicas del Ecuador (2015–2023)")

# ─── Carga de datos ────────────────────────────────────────────────────────────
FILE_PATH = "Base_estadistica_matricula_UEP_15_23.xlsx"
HEADER_ROW = 14

@st.cache_data(show_spinner="Cargando base de datos… puede tardar unos segundos")
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Base", header=HEADER_ROW)
    df.columns = df.columns.str.strip()
    df = df.dropna(how="all")
    df["TOTAL"] = pd.to_numeric(df["TOTAL"], errors="coerce")
    df["AÑO"]  = pd.to_numeric(df["AÑO"],   errors="coerce").astype("Int64")
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
    return df

with st.spinner("Cargando datos…"):
    df = load_data(FILE_PATH)

# ─── Sidebar – filtros ─────────────────────────────────────────────────────────
st.sidebar.header("🔎 Filtros")

años_disp = sorted(df["AÑO"].dropna().unique().tolist())
años_sel  = st.sidebar.multiselect("Año(s)", años_disp, default=años_disp)

tipo_fin = ["Todos"] + sorted(df["TIPO_FINANCIAMIENTO"].unique().tolist())
fin_sel  = st.sidebar.selectbox("Tipo de financiamiento", tipo_fin)

modalidad = ["Todas"] + sorted(df["MODALIDAD"].unique().tolist())
mod_sel   = st.sidebar.selectbox("Modalidad", modalidad)

sexo     = ["Todos"] + sorted(df["SEXO"].unique().tolist())
sexo_sel = st.sidebar.selectbox("Sexo", sexo)

mask = df["AÑO"].isin(años_sel)
if fin_sel  != "Todos":  mask &= df["TIPO_FINANCIAMIENTO"] == fin_sel
if mod_sel  != "Todas":  mask &= df["MODALIDAD"]           == mod_sel
if sexo_sel != "Todos":  mask &= df["SEXO"]                == sexo_sel

dff = df[mask].copy()

# ─── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Datos", "📊 Estadísticas descriptivas", "📈 Visualizaciones", "🔬 Perfilado Sweetviz"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 – TABLA INTERACTIVA
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Tabla interactiva de datos")

    c1, c2, c3 = st.columns(3)
    c1.metric("Registros filtrados",  f"{len(dff):,}")
    c2.metric("Variables",            len(dff.columns))
    c3.metric("Total matrículas",     f"{int(dff['TOTAL'].sum()):,}")

    max_rows = st.slider("Filas a mostrar", 50, 5000, 500, step=50)
    st.dataframe(dff.head(max_rows), use_container_width=True, height=420)

    csv = dff.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Descargar CSV filtrado", csv, "matricula_filtrada.csv", "text/csv")

    if st.button("📝 Generar archivo CSV en disco"):
        output_path = "matricula_filtrada.csv"
        dff.to_csv(output_path, index=False, encoding="utf-8")
        st.success(f"Archivo generado: {output_path}")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 – ESTADÍSTICAS DESCRIPTIVAS
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Información general del dataset")

    ca, cb, cc, cd = st.columns(4)
    ca.metric("N° registros",   f"{len(dff):,}")
    cb.metric("N° variables",   len(dff.columns))
    cc.metric("Valores nulos",  f"{dff.isnull().sum().sum():,}")
    cd.metric("Años cubiertos", f"{dff['AÑO'].nunique()}")

    st.markdown("#### Tipos de datos por columna")
    tipos = pd.DataFrame({
        "Variable": dff.columns,
        "Tipo":     dff.dtypes.astype(str).values,
        "Nulos":    dff.isnull().sum().values,
        "% Nulos":  (dff.isnull().mean() * 100).round(2).values,
        "Únicos":   dff.nunique().values,
    })
    st.dataframe(tipos, use_container_width=True)

    st.markdown("#### Estadísticas descriptivas – variable TOTAL")
    st.dataframe(dff[["TOTAL"]].describe().T, use_container_width=True)

    st.markdown("#### Frecuencia de variables categóricas")
    cat_col = st.selectbox(
        "Selecciona variable",
        [c for c in dff.columns if c not in ("TOTAL", "AÑO")],
        key="cat_freq"
    )
    freq = dff[cat_col].value_counts().reset_index()
    freq.columns = [cat_col, "Frecuencia"]
    st.dataframe(freq, use_container_width=True)

    st.markdown("#### Filas con valores nulos") 
    st.dataframe(df[df.isnull().any(axis=1)].head())
    st.write("Número de filas con al menos un valor nulo:", df.isnull().any(axis=1).sum())

    drop_na = st.checkbox("Eliminar filas con valores nulos", value=False)
    if drop_na:
        dff.dropna(inplace=True)
        st.success("Filas con valores nulos eliminadas. Actualiza las estadísticas y visualizaciones.")

    fill_na = st.checkbox("Rellenar valores nulos con 0 (solo para TOTAL)", value=False)
    if fill_na:
        if "TOTAL" in dff.columns:
            dff["TOTAL"] = dff["TOTAL"].fillna(0)
            st.success("Valores nulos en TOTAL rellenados con 0. Actualiza las estadísticas y visualizaciones.")
        else:
            st.warning("La columna TOTAL no está presente en el dataset.")

df.describe(include="all").T
Q1 = df["TOTAL"].quantile(0.25)
Q3 = df["TOTAL"].quantile(0.75) 
IQR = Q3 - Q1
outliers = df[(df["TOTAL"] < Q1 - 1.5 * IQR) | (df["TOTAL"] > Q3 + 1.5 * IQR)]
st.markdown("#### Análisis de outliers en variable TOTAL")
st.write(f"Rango intercuartílico (IQR): {IQR:.2f}")
st.write(f"Valores atípicos detectados: {len(outliers)}")
if not outliers.empty:
    st.dataframe(outliers[["AÑO", "NOMBRE_IES", "TOTAL"]].head())           


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 – VISUALIZACIONES
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Visualizaciones exploratorias")

    st.markdown("##### Evolución de matrículas por año")
    by_year = dff.groupby("AÑO")["TOTAL"].sum().reset_index()
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(by_year["AÑO"], by_year["TOTAL"], color='steelblue', edgecolor='black')
    ax.set_xlabel("Año", fontsize=12, fontweight='bold')
    ax.set_ylabel("Matrículas", fontsize=12, fontweight='bold')
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height):,}', ha='center', va='bottom', fontsize=9)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)

    st.markdown("##### Matrículas por sexo y año")
    by_sexo = dff.groupby(["AÑO", "SEXO"])["TOTAL"].sum().reset_index()
    fig, ax = plt.subplots(figsize=(12, 6))
    for sexo in by_sexo["SEXO"].unique():
        data = by_sexo[by_sexo["SEXO"] == sexo]
        ax.plot(data["AÑO"], data["TOTAL"], marker='o', label=sexo, linewidth=2, markersize=8)
    ax.set_xlabel("Año", fontsize=12, fontweight='bold')
    ax.set_ylabel("Matrículas", fontsize=12, fontweight='bold')
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)

    st.markdown("##### Top 15 instituciones por matrícula")
    top_ies = dff.groupby("NOMBRE_IES")["TOTAL"].sum().nlargest(15).reset_index()
    top_ies = top_ies.sort_values("TOTAL")
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.barh(top_ies["NOMBRE_IES"], top_ies["TOTAL"], color='steelblue', edgecolor='black')
    ax.set_xlabel("Matrículas", fontsize=12, fontweight='bold')
    ax.set_ylabel("Institución", fontsize=12, fontweight='bold')
    for i, (idx, row) in enumerate(top_ies.iterrows()):
        ax.text(row["TOTAL"], i, f' {int(row["TOTAL"]):,}', va='center', fontsize=9)
    plt.tight_layout()
    st.pyplot(fig)

    st.markdown("##### Distribución por campo amplio de conocimiento")
    by_campo = dff.groupby("CAMPO_AMPLIO")["TOTAL"].sum().reset_index()
    fig, ax = plt.subplots(figsize=(10, 8))
    wedges, texts, autotexts = ax.pie(by_campo["TOTAL"], labels=by_campo["CAMPO_AMPLIO"], 
                                        autopct='%1.1f%%', startangle=90)
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
    plt.tight_layout()
    st.pyplot(fig)

    st.markdown("##### Matrículas por tipo de financiamiento y año")
    by_fin = dff.groupby(["AÑO", "TIPO_FINANCIAMIENTO"])["TOTAL"].sum().reset_index()
    fig, ax = plt.subplots(figsize=(12, 6))
    fin_types = by_fin["TIPO_FINANCIAMIENTO"].unique()
    x = by_fin["AÑO"].unique()
    width = 0.2
    for i, fin in enumerate(fin_types):
        data = by_fin[by_fin["TIPO_FINANCIAMIENTO"] == fin]
        ax.bar(data["AÑO"] + i*width - width*len(fin_types)/2, data["TOTAL"], 
               width=width, label=fin, edgecolor='black')
    ax.set_xlabel("Año", fontsize=12, fontweight='bold')
    ax.set_ylabel("Matrículas", fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)

    st.markdown("##### Matrículas por nivel de formación")
    by_nivel = dff.groupby("NIVEL_FORMACION")["TOTAL"].sum().reset_index()
    by_nivel = by_nivel.sort_values("TOTAL", ascending=True)
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.barh(by_nivel["NIVEL_FORMACION"], by_nivel["TOTAL"], color='steelblue', edgecolor='black')
    ax.set_xlabel("Matrículas", fontsize=12, fontweight='bold')
    ax.set_ylabel("Nivel de Formación", fontsize=12, fontweight='bold')
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height()/2.,
                f' {int(width):,}', ha='left', va='center', fontsize=9)
    plt.tight_layout()
    st.pyplot(fig)

    st.markdown("##### Distribución por etnia")
    by_etnia = dff.groupby("ETNIA")["TOTAL"].sum().reset_index()
    by_etnia = by_etnia.sort_values("TOTAL", ascending=True)
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.barh(by_etnia["ETNIA"], by_etnia["TOTAL"], color='teal', edgecolor='black')
    ax.set_xlabel("Matrículas", fontsize=12, fontweight='bold')
    ax.set_ylabel("Etnia", fontsize=12, fontweight='bold')
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height()/2.,
                f' {int(width):,}', ha='left', va='center', fontsize=9)
    plt.tight_layout()
    st.pyplot(fig)

    st.markdown("##### Mapa de calor – Provincia de residencia × Año")
    prov_año = dff.groupby(["PROVINCIA_RESIDENCIA", "AÑO"])["TOTAL"].sum().reset_index()
    pivot = prov_año.pivot(index="PROVINCIA_RESIDENCIA", columns="AÑO", values="TOTAL").fillna(0)
    fig, ax = plt.subplots(figsize=(14, 10))
    sns.heatmap(pivot, annot=True, fmt='.0f', cmap='Blues', cbar_kws={'label': 'Matrículas'}, ax=ax)
    ax.set_title("Matrículas por Provincia y Año", fontsize=14, fontweight='bold')
    plt.tight_layout()
    st.pyplot(fig)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 – SWEETVIZ
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Reporte de perfilado con Sweetviz")
    st.info("El reporte se genera sobre una muestra de los datos filtrados para mayor velocidad.")

    sample_n = st.slider(
        "Tamaño de muestra", 500, min(20_000, len(dff)),
        value=min(5_000, len(dff)), step=500
    )

    if st.button("🔬 Generar reporte Sweetviz"):
        with st.spinner("Generando reporte…"):
            sample_df = dff.sample(n=sample_n, random_state=42).reset_index(drop=True)
            report = sv.analyze(sample_df)
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
                tmp_path = tmp.name
            report.show_html(tmp_path, open_browser=False)
            with open(tmp_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            os.unlink(tmp_path)

        st.download_button(
            "⬇️ Descargar reporte HTML",
            html_content,
            file_name="reporte_sweetviz.html",
            mime="text/html"
        )
        st.components.v1.html(html_content, height=900, scrolling=True)

