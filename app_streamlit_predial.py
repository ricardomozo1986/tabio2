
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout='wide')
st.title("📊 Dashboard Predial Municipal")

# --- Cargar archivo ---
uploaded_file = st.file_uploader("Sube tu archivo Excel de predios", type=["xlsx"])
if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # --- Campos calculados ---
    df['Cumplimiento'] = df['Pago'].apply(lambda x: 1 if x == 'Si' else 0)

    # --- Indicadores clave ---
    st.markdown("### Indicadores clave")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Predios", len(df))
    col2.metric("Facturado", f"${df['VlrImpuest'].sum():,.0f}")
    col3.metric("Recaudado", f"${df['Recaudo'].sum():,.0f}")
    col4.metric("Cumplimiento", f"{df['Cumplimiento'].mean() * 100:.2f}%")

    # --- Filtros ---
    st.sidebar.header("Filtros")
    sector = st.sidebar.selectbox("Sector", ['Todos'] + sorted(df['Sector'].dropna().unique().tolist()))
    uso = st.sidebar.selectbox("Uso del predio", ['Todos'] + sorted(df['Destino_Ec'].dropna().unique().tolist()))
    impuesto = st.sidebar.slider("Rango de impuesto ($)", float(df['VlrImpuest'].min()), float(df['VlrImpuest'].max()), (float(df['VlrImpuest'].min()), float(df['VlrImpuest'].max())))
    area_lote = st.sidebar.slider("Área del lote", float(df['AreaTerren'].min()), float(df['AreaTerren'].max()), (float(df['AreaTerren'].min()), float(df['AreaTerren'].max())))
    area_const = st.sidebar.slider("Área construida", float(df['AreaConstr'].min()), float(df['AreaConstr'].max()), (float(df['AreaConstr'].min()), float(df['AreaConstr'].max())))
    descuentos = st.sidebar.slider("Descuentos ($)", float(df['Descuentos'].min()), float(df['Descuentos'].max()), (float(df['Descuentos'].min()), float(df['Descuentos'].max())))

    # Aplicar filtros
    dff = df.copy()
    if sector != 'Todos':
        dff = dff[dff['Sector'] == sector]
    if uso != 'Todos':
        dff = dff[dff['Destino_Ec'] == uso]
    dff = dff[
        (dff['VlrImpuest'].between(impuesto[0], impuesto[1])) &
        (dff['AreaTerren'].between(area_lote[0], area_lote[1])) &
        (dff['AreaConstr'].between(area_const[0], area_const[1])) &
        (dff['Descuentos'].between(descuentos[0], descuentos[1]))
    ]

    # --- Gráficos ---
    st.markdown("### Distribución del impuesto predial")
    fig = px.histogram(dff, x='VlrImpuest', nbins=30, title='Distribución del valor del impuesto')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Top 10 predios en mora")
    top_morosos = dff[dff['Pago'] == 'No'].sort_values(by='VlrImpuest', ascending=False).head(10)
    fig2 = px.bar(top_morosos, x='Vereda', y='VlrImpuest', color='Destino_Ec', title='Top 10 morosos')
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### Tabla de resultados filtrados")
    st.dataframe(dff[['Vereda', 'Sector', 'Destino_Ec', 'VlrImpuest', 'Recaudo', 'AreaTerren', 'AreaConstr', 'Descuentos']])

    # --- Análisis adicionales ---
    st.markdown("## 🧮 Análisis adicionales")

    # 1. Cumplimiento tributario por vereda
    st.markdown("### 1. Cumplimiento tributario por vereda")
    cumplimiento_por_vereda = df.groupby('Vereda')['Cumplimiento'].mean().sort_values(ascending=False) * 100
    fig_cump = px.bar(cumplimiento_por_vereda, title='Tasa de cumplimiento por vereda (%)', labels={'value': 'Cumplimiento (%)'})
    st.plotly_chart(fig_cump, use_container_width=True)

    # 2. Segmentación de cartera morosa
    st.markdown("### 2. Segmentación de cartera morosa")
    morosos = df[df['Pago'] == 'No']
    morosos['RangoDeuda'] = pd.cut(morosos['VlrImpuest'], bins=[0, 50000, 100000, 300000, 1000000, df['VlrImpuest'].max()],
                                    labels=['<50K', '50K-100K', '100K-300K', '300K-1M', '>1M'])
    st.bar_chart(morosos['RangoDeuda'].value_counts().sort_index())

    # 3. Oportunidades de actualización catastral
    st.markdown("### 3. Oportunidades de actualización catastral")
    sin_construccion = df[(df['AreaConstr'] == 0) & (df['VlrImpuest'] > 0)]
    st.write(f"Predios con avalúo > 0 pero sin área construida registrada: {len(sin_construccion)}")
    st.dataframe(sin_construccion[['Vereda', 'Sector', 'VlrImpuest', 'AreaTerren', 'AreaConstr']].head(10))

    # 4. Estrategias de cobro
    st.markdown("### 4. Predios con prioridad para cobro coactivo")
    prioridad_cobro = df[(df['Pago'] == 'No') & (df['VlrImpuest'] > df['VlrImpuest'].quantile(0.75))]
    st.write(f"Predios candidatos a gestión de cobro prioritaria: {len(prioridad_cobro)}")
    st.dataframe(prioridad_cobro[['Vereda', 'VlrImpuest', 'Recaudo', 'Destino_Ec']].head(10))

    # 5. Simulación de escenarios
    st.markdown("### 5. Simulación de incremento de recaudo")
    morosos_rurales = df[(df['Pago'] == 'No') & (df['Sector'] == 'RURAL')]
    simulado_recaudo = morosos_rurales['VlrImpuest'].sum() * 0.10
    st.write(f"Recaudo potencial si el 10% de los morosos rurales paga: ${simulado_recaudo:,.0f}")

    # --- Mapa interactivo de predios morosos ---
    st.markdown("### 🗺️ Mapa interactivo de predios en mora")

    import folium
    from folium.plugins import MarkerCluster
    from streamlit_folium import st_folium

    mapa = folium.Map(location=[df['latitud'].mean(), df['longitud'].mean()], zoom_start=12)
    cluster = MarkerCluster().add_to(mapa)

    for _, row in df[df['Pago'] == 'No'].iterrows():
        folium.Marker(
            location=[row['latitud'], row['longitud']],
            popup=(
                f"Vereda: {row['Vereda']}<br>"
                f"Sector: {row['Sector']}<br>"
                f"Imp.: ${row['VlrImpuest']:,.0f}"
            )
        ).add_to(cluster)

    st_folium(mapa, width=700, height=500)
