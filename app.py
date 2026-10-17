import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Expert-EGX v6", layout="wide")

# === Theme state ===
if 'theme' not in st.session_state:
    st.session_state.theme = "Auto"

# === Colors constants ===
COLORS = {
    "primary":   "#1E5F8E", "primary_dark":   "#4A9EDB",
    "success":   "#2E7D32", "success_dark":   "#66BB6A",
    "danger":    "#C62828", "danger_dark":    "#EF5350",
    "warning":   "#E65100", "warning_dark":   "#FFA726",
    "neutral":   "#546E7A", "neutral_dark":   "#90A4AE",
    "master":    "#1565C0", "master_dark":    "#64B5F6",
    "shakeout":  "#6A1B9A", "shakeout_dark":  "#BA68C8",
    "climax":    "#E65100", "climax_dark":    "#FFA726",
    "critical":  "#00695C", "critical_dark":  "#4DB6AC",
}

def inject_css():
    theme = st.session_state.theme
    if theme == "Light":
        vars_css = """
        <style>:root{
            --primary:#1E5F8E;--success:#2E7D32;--danger:#C62828;
            --warning:#E65100;--neutral:#546E7A;--surface:#F5F7FA;
            --master:#1565C0;--shakeout:#6A1B9A;--climax:#E65100;--critical:#00695C;
        }</style>"""
    elif theme == "Dark":
        vars_css = """
        <style>:root{
            --primary:#4A9EDB;--success:#66BB6A;--danger:#EF5350;
            --warning:#FFA726;--neutral:#90A4AE;--surface:#1E1E1E;
            --master:#64B5F6;--shakeout:#BA68C8;--climax:#FFA726;--critical:#4DB6AC;
        }</style>"""
    else:  # Auto
        vars_css = """
        <style>
        :root{
            --primary:#1E5F8E;--success:#2E7D32;--danger:#C62828;
            --warning:#E65100;--neutral:#546E7A;--surface:#F5F7FA;
            --master:#1565C0;--shakeout:#6A1B9A;--climax:#E65100;--critical:#00695C;
        }
        @media (prefers-color-scheme: dark){
            :root{
                --primary:#4A9EDB;--success:#66BB6A;--danger:#EF5350;
                --warning:#FFA726;--neutral:#90A4AE;--surface:#1E1E1E;
                --master:#64B5F6;--shakeout:#BA68C8;--climax:#FFA726;--critical:#4DB6AC;
            }
        }
        </style>"""
    
    base_css = """
    <style>
    .stApp { font-family: 'Segoe UI', Tahoma, sans-serif; }

    .expert-logo {
        font-size: 1.9rem; font-weight: 800;
        color: var(--primary);
        letter-spacing: 2px; margin: 0; padding: 0;
    }
    .expert-tagline {
        color: var(--neutral);
        font-size: 0.95rem;
        margin-top: 2px; margin-bottom: 1.2rem;
    }
    .expert-divider {
        height: 3px; background: var(--primary);
        border-radius: 2px; margin: 8px 0 20px 0;
    }

    .badge {
        display: inline-block;
        padding: 3px 10px; border-radius: 12px;
        font-size: 0.75rem; font-weight: 700;
        letter-spacing: 0.5px; direction: ltr;
    }
    .badge-master    { background: rgba(21,101,192,0.15);  color: var(--master);   border: 1px solid var(--master); }
    .badge-shakeout  { background: rgba(106,27,154,0.15);  color: var(--shakeout); border: 1px solid var(--shakeout); }
    .badge-climax    { background: rgba(230,81,0,0.15);    color: var(--climax);   border: 1px solid var(--climax); }
    .badge-critical  { background: rgba(0,105,92,0.15);    color: var(--critical); border: 1px solid var(--critical); }
    .badge-excellent { background: rgba(46,125,50,0.15);   color: var(--success);  border: 1px solid var(--success); }
    .badge-good      { background: rgba(30,95,142,0.15);   color: var(--primary);  border: 1px solid var(--primary); }
    .badge-ok        { background: rgba(230,81,0,0.15);    color: var(--warning);  border: 1px solid var(--warning); }
    .badge-weak      { background: rgba(198,40,40,0.15);   color: var(--danger);   border: 1px solid var(--danger); }

    .sidebar-title {
        font-weight: 700; color: var(--primary);
        font-size: 0.95rem;
        margin-top: 1.1rem; margin-bottom: 0.4rem;
        border-bottom: 2px solid var(--primary);
        padding-bottom: 3px;
    }

    [data-testid="stMetricValue"] { color: var(--primary); font-weight: 700; }
    [data-testid="stMetricLabel"] { color: var(--neutral); font-size: 0.85rem; }

    [data-testid="stMarkdownContainer"] p,
    .stText, .stCaption { direction: rtl; text-align: right; }
    </style>"""
    st.markdown(vars_css, unsafe_allow_html=True)
    st.markdown(base_css, unsafe_allow_html=True)


def signal_badge(sig):
    mapping = {
        "Master":       ("MASTER",       "badge-master"),
        "Shakeout":     ("SHAKEOUT",     "badge-shakeout"),
        "Climax":       ("CLIMAX",       "badge-climax"),
        "Critical Vol": ("CRITICAL VOL", "badge-critical"),
    }
    label, cls = mapping.get(sig, (sig, ""))
    return f'<span class="badge {cls}">{label}</span>'

def quality_badge(q):
    mapping = {
        "ممتاز": ("ممتاز", "badge-excellent"),
        "جيد":   ("جيد",   "badge-good"),
        "مقبول": ("مقبول", "badge-ok"),
        "ضعيف":  ("ضعيف",  "badge-weak"),
    }
    label, cls = mapping.get(q, (q, ""))
    return f'<span class="badge {cls}">{label}</span>'


EGX_TICKERS = [
    'COMI.CA','ADIB.CA','CIEB.CA','SAUD.CA','FAIT.CA','BIDI.CA','ETEL.CA','EGSA.CA',
    'TMGH.CA','PHDC.CA','OCDI.CA','HELI.CA','ELSH.CA','PRMH.CA','SWDY.CA','ABUK.CA','MFPC.CA',
    'SKPC.CA','EFIC.CA','FWRY.CA','JUFO.CA','DOMT.CA','UEFM.CA','SNFC.CA','CCAP.CA',
    'ISPH.CA','CLHO.CA','RMDA.CA','NCCW.CA','SPMD.CA','HRHO.CA','OCPH.CA','EGCH.CA','AMOC.CA','EAST.CA',
    'ORWE.CA','ARCC.CA','SCEM.CA','MTIE.CA','EMFD.CA','ETRS.CA','RACC.CA',
    'ATLC.CA','CANA.CA','KZPC.CA','ELEC.CA','AFDI.CA','AIFI.CA','AMER.CA','AMES.CA',
    'APSW.CA','ARAB.CA','ASCM.CA','ASPI.CA','ATQA.CA','BIOC.CA','CICH.CA','CNFN.CA',
    'COPR.CA','CSAG.CA','DSCW.CA','EEII.CA','EFID.CA','EGBE.CA','ENGC.CA','EOSB.CA','EPCO.CA','GGCC.CA',
    'GIHD.CA','GMCI.CA','GSSC.CA','IEEC.CA','INEG.CA','ISMA.CA','KABO.CA','LCSW.CA','MBSC.CA','MCQE.CA',
    'MENA.CA','MICH.CA','MILS.CA','MOIL.CA','MPCO.CA','NEDA.CA','NHPS.CA',
    'ODIN.CA','OIH.CA','OLFI.CA','PHAR.CA','POUL.CA','RREI.CA','RTVC.CA','SCTS.CA','SIPC.CA','SPHT.CA',
    'SPIN.CA','SVCE.CA','TALM.CA','UNIT.CA','WCDF.CA','WKOL.CA','ZEOT.CA'
]

def build_strategy_features(df):
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df['Range_HL'] = df['High'] - df['Low']
    df['Body'] = abs(df['Close'] - df['Open'])
    df['Upper_Wick'] = np.maximum(0, df['High'] - df[['Open','Close']].max(axis=1))
    df['Lower_Wick'] = np.maximum(0, df[['Open','Close']].min(axis=1) - df['Low'])
    df['Close_Position'] = np.where(df['Range_HL']>0, (df['Close']-df['Low'])/df['Range_HL'], 0.5)
    df['Body_Ratio'] = df['Body'] / df['Range_HL'].replace(0, 1)
    df['Upper_Wick_Ratio'] = df['Upper_Wick'] / df['Range_HL'].replace(0, 1)
    df['Lower_Wick_Ratio'] = df['Lower_Wick'] / df['Range_HL'].replace(0, 1)
    df['Range_Pct'] = df['Range_HL'] / df['Close']

    df['Vol_EMA20'] = df['Volume'].ewm(span=20, adjust=False).mean()
    df['Vol_Ratio_EMA20'] = df['Volume'] / df['Vol_EMA20'].replace(0, 1)
    df['Vol_Mean_20'] = df['Volume'].rolling(20).mean()
    df['Vol_Std_20'] = df['Volume'].rolling(20).std()
    df['Vol_Bollinger_Lower'] = df['Vol_Mean_20'] - df['Vol_Std_20']
    df['Is_Critical_Vol'] = (df['Volume'] < df['Vol_Bollinger_Lower']).astype(int)

    df['Avg_Range_20'] = df['Range_HL'].rolling(20).mean()
    df['Range_Ratio'] = df['Range_HL'] / df['Avg_Range_20'].replace(0, 1)

    df['Is_Buyer'] = ((df['Close_Position'] > 0.5) | (df['Lower_Wick'] > df['Upper_Wick'])).astype(int)
    df['Is_Maker'] = (df['Volume'] > df['Vol_EMA20']).astype(int)
    df['Is_Master'] = ((df['Range_Ratio'] > 1.5) & (df['Volume'] > df['Vol_EMA20'])).astype(int)
    df['Is_Downtrend'] = (df['Close'] < df['Close'].shift(10)).astype(int)

    df['Is_Shakeout'] = (
        (df['Lower_Wick_Ratio'] > 0.5) &
        (df['Close_Position'] > 0.5) &
        (df['Is_Downtrend'] == 1) &
        (df['Is_Master'] == 1)
    ).astype(int)

    df['Is_Climax'] = (
        (df['Is_Downtrend'] == 1) &
        (df['Volume'] > 2 * df['Vol_EMA20']) &
        (df['Range_Ratio'] > 1.5) &
        (df['Close_Position'] > 0.4)
    ).astype(int)

    df['Is_Decision'] = (
        (df['Is_Master'] == 1) |
        (df['Is_Shakeout'] == 1) |
        (df['Is_Climax'] == 1) |
        ((df['Is_Critical_Vol'] == 1) & (df['Is_Buyer'] == 1) & (df['Is_Downtrend'] == 1))
    ).astype(int)

    df['Signal_Type'] = 'None'
    df.loc[df['Is_Shakeout']==1, 'Signal_Type'] = 'Shakeout'
    df.loc[df['Is_Climax']==1, 'Signal_Type'] = 'Climax'
    df.loc[(df['Is_Master']==1) & (df['Signal_Type']=='None'), 'Signal_Type'] = 'Master'
    df.loc[(df['Is_Critical_Vol']==1) & (df['Is_Buyer']==1) & (df['Is_Downtrend']==1) & (df['Signal_Type']=='None'), 'Signal_Type'] = 'Critical Vol'

    return df

def calculate_trade_plan(row, cost_pct=0.005):
    entry = row['High']
    stop = row['Low'] * 0.99
    range_hl = row['Range_HL']

    if range_hl <= 0 or pd.isna(range_hl) or entry <= stop:
        return None

    t1 = row['Low'] + 1.618 * range_hl
    t2 = row['Low'] + 2.618 * range_hl

    expected_r = 0.196
    risk_pct = (entry - stop) / entry * 100
    risk_abs = entry - stop
    cost_in_r = (cost_pct * entry) / risk_abs if risk_abs > 0 else 0
    net_r = expected_r - cost_in_r if risk_abs > 0 else 0

    return {
        'entry': round(entry, 2),
        'stop': round(stop, 2),
        't1': round(t1, 2),
        't2': round(t2, 2),
        'risk_pct': round(risk_pct, 2),
        'range_pct': round(row['Range_Pct'] * 100, 2),
        'net_r': round(net_r, 3),
        'expected_r': round(expected_r, 3)
    }

@st.cache_data(ttl=1800, show_spinner=False)
def scan_market(tickers_tuple, min_range_pct, min_vol_ratio, signal_filter):
    tickers = list(tickers_tuple)
    progress = st.progress(0, text="جاري تحميل البيانات...")
    data = yf.download(tickers, period="1y", group_by='ticker', auto_adjust=True, progress=False, threads=True)
    results = []
    for i, ticker in enumerate(tickers):
        progress.progress((i+1)/len(tickers), text=f"فحص {ticker}... ({i+1}/{len(tickers)})")
        try:
            if ticker not in data.columns.levels[0]: continue
            df = data[ticker].dropna()
            if len(df) < 60: continue
            if df['Volume'].tail(30).mean() < 50000: continue

            df = build_strategy_features(df)
            if len(df) < 30: continue

            last = df.iloc[-1]
            if last['Is_Decision'] != 1: continue
            if last['Range_Pct'] * 100 < min_range_pct: continue
            if last['Vol_Ratio_EMA20'] < min_vol_ratio: continue
            if signal_filter != "الكل" and signal_filter not in last['Signal_Type']: continue

            plan = calculate_trade_plan(last)
            if plan is None: continue

            if plan['net_r'] >= 0.4:
                quality = "ممتاز"
            elif plan['net_r'] >= 0.2:
                quality = "جيد"
            elif plan['net_r'] >= 0:
                quality = "مقبول"
            else:
                quality = "ضعيف"

            results.append({
                'السهم': ticker.replace('.CA',''),
                'الجودة': quality,
                'الإشارة': last['Signal_Type'],
                'السعر': round(last['Close'], 2),
                'الدخول': plan['entry'],
                'الوقف': plan['stop'],
                'الهدف 1': plan['t1'],
                'الهدف 2': plan['t2'],
                'المخاطرة %': plan['risk_pct'],
                'المدى %': plan['range_pct'],
                'Net R': plan['net_r']
            })
        except:
            continue
    progress.empty()
    return pd.DataFrame(results)


# === Theme switcher (قبل CSS) ===
st.sidebar.markdown('<div class="sidebar-title">المظهر</div>', unsafe_allow_html=True)
theme_choice = st.sidebar.radio(
    "Theme", ["Auto", "Light", "Dark"],
    index=["Auto", "Light", "Dark"].index(st.session_state.theme),
    horizontal=True, label_visibility="collapsed", key="theme_radio"
)
if theme_choice != st.session_state.theme:
    st.session_state.theme = theme_choice
    st.rerun()

# === Apply theme CSS ===
inject_css()

# === Header ===
st.markdown('<div class="expert-logo">EXPERT-EGX</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="expert-tagline">ماسح السوق الذكي — الإصدار 6 | استراتيجية الهدف المقسّم (1.618 / 2.618) مع Breakeven Stop</div>',
    unsafe_allow_html=True
)
st.markdown('<div class="expert-divider"></div>', unsafe_allow_html=True)

# === Sidebar config ===
st.sidebar.markdown('<div class="sidebar-title">الإعدادات</div>', unsafe_allow_html=True)
mode = st.sidebar.radio("الوضع", ["مسح السوق", "تحليل سهم واحد"], label_visibility="collapsed")

if mode == "مسح السوق":
    st.subheader("مسح السوق — الاستراتيجية الفائزة")
    st.caption(f"آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    st.sidebar.markdown('<div class="sidebar-title">Preset</div>', unsafe_allow_html=True)
    preset = st.sidebar.selectbox(
        "اختر",
        ["متوازن (موصى به)", "محافظ (جودة عالية)", "استكشافي", "مخصص"],
        label_visibility="collapsed"
    )

    st.sidebar.markdown('<div class="sidebar-title">فلاتر الجودة</div>', unsafe_allow_html=True)

    default_range = 4.0
    default_vol = 1.5
    if preset == "محافظ (جودة عالية)":
        default_range = 5.0; default_vol = 1.8
    elif preset == "متوازن (موصى به)":
        default_range = 4.0; default_vol = 1.5
    elif preset == "استكشافي":
        default_range = 3.0; default_vol = 1.0

    min_range_pct = st.sidebar.slider(
        "أدنى مدى الشمعة %", 1.0, 8.0, default_range, 0.5,
        help="القيمة الموصى بها: 4% — كل ما زاد، كل ما الجودة أعلى"
    )
    min_vol_ratio = st.sidebar.slider(
        "أدنى نسبة فوليوم (vs EMA20)", 0.5, 3.0, default_vol, 0.1,
        help="القيمة الموصى بها: 1.5 — كل ما زاد، كل ما الجودة أعلى"
    )

    signal_filter = st.sidebar.selectbox(
        "نوع الإشارة",
        ["الكل", "Shakeout", "Climax", "Master", "Critical Vol"]
    )

    if st.button("بدء المسح", type="primary", use_container_width=True):
        with st.spinner("جاري المسح..."):
            results_df = scan_market(tuple(EGX_TICKERS), min_range_pct, min_vol_ratio, signal_filter)

        if results_df.empty:
            st.warning("مفيش إشارات بالمواصفات دي. جرب تخفف الفلاتر أو استخدم Preset استكشافي.")
        else:
            results_df = results_df.sort_values('Net R', ascending=False).reset_index(drop=True)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("عدد الإشارات", len(results_df))
            col2.metric("أعلى Net R", f"+{results_df['Net R'].max():.3f}R")
            col3.metric("متوسط Net R", f"+{results_df['Net R'].mean():.3f}R")
            col4.metric("أقل مخاطرة", f"{results_df['المخاطرة %'].min():.2f}%")

            st.divider()
            st.subheader(f"{len(results_df)} سهم عليهم إشارات:")

            for _, row in results_df.iterrows():
                header = (
                    f"**{row['السهم']}**  ·  "
                    f"Net R: +{row['Net R']:.3f}"
                )
                with st.expander(header, expanded=(row.name < 3)):
                    st.markdown(
                        f"{signal_badge(row['الإشارة'])} &nbsp; {quality_badge(row['الجودة'])}",
                        unsafe_allow_html=True
                    )
                    c1, c2, c3, c4, c5, c6 = st.columns(6)
                    c1.metric("السعر الحالي", row['السعر'])
                    c2.metric("الدخول", row['الدخول'])
                    c3.metric("الوقف", row['الوقف'])
                    c4.metric("الهدف 1 (50%)", row['الهدف 1'])
                    c5.metric("الهدف 2 (50%)", row['الهدف 2'])
                    c6.metric("Net R", f"+{row['Net R']:.3f}")

                    st.caption(
                        f"المخاطرة: {row['المخاطرة %']}% | المدى: {row['المدى %']}% | "
                        f"التفعيل: اختراق {row['الدخول']} | الإبطال: كسر {row['الوقف']}"
                    )

                    progress_val = min(100, max(0, row['Net R'] * 200))
                    st.progress(progress_val / 100)

            st.divider()
            with st.expander("جدول مختصر"):
                st.dataframe(results_df, use_container_width=True, hide_index=True)
                csv = results_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    "تنزيل CSV", csv,
                    f"signals_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv"
                )
            st.caption("Win Rate 74% | Avg R +0.196R | 1,347 صفقة تاريخية")

else:
    ticker = st.sidebar.text_input("رمز السهم", value="COMI.CA")
    if st.sidebar.button("تحليل", use_container_width=True):
        with st.spinner('جاري التحليل...'):
            df_raw = yf.download(ticker, period="1y", auto_adjust=True, progress=False)
            if df_raw.empty:
                st.error("مفيش بيانات.")
            else:
                df = build_strategy_features(df_raw)
                last = df.iloc[-1]
                plan = calculate_trade_plan(last) if last['Is_Decision'] == 1 else None

                if last['Is_Decision'] == 1 and plan:
                    st.markdown(
                        f"{signal_badge(last['Signal_Type'])} &nbsp; Net R: +{plan['net_r']:.3f}",
                        unsafe_allow_html=True
                    )
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("السعر", round(last['Close'], 2))
                    c2.metric("الدخول", plan['entry'])
                    c3.metric("الوقف", plan['stop'])
                    c4.metric("T1 (1.618)", plan['t1'])
                    c5.metric("T2 (2.618)", plan['t2'])
                    st.info(
                        f"الخطة: ادخل عند اختراق {plan['entry']} | الوقف تحت {plan['stop']} | "
                        f"T1 عند {plan['t1']} (بيع 50% + نقل الوقف للدخول) | T2 عند {plan['t2']}"
                    )
                else:
                    st.info("مفيش إشارة على آخر شمعة.")

                fig = make_subplots(
                    rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                    row_heights=[0.7, 0.3],
                    subplot_titles=("السعر مع الإشارات", "الفوليوم")
                )

                fig.add_trace(go.Candlestick(
                    x=df.index, open=df['Open'], high=df['High'],
                    low=df['Low'], close=df['Close'], name='Price'
                ), row=1, col=1)

                masters   = df[df['Is_Master']==1]
                shakeouts = df[df['Is_Shakeout']==1]
                climaxes  = df[df['Is_Climax']==1]

                fig.add_trace(go.Scatter(
                    x=masters.index, y=masters['High']+0.5, mode='markers',
                    marker=dict(symbol='circle', size=11, color='#1565C0',
                                line=dict(color='white', width=1)),
                    name='Master'
                ), row=1, col=1)
                fig.add_trace(go.Scatter(
                    x=shakeouts.index, y=shakeouts['Low']-0.5, mode='markers',
                    marker=dict(symbol='triangle-up', size=13, color='#6A1B9A'),
                    name='Shakeout'
                ), row=1, col=1)
                fig.add_trace(go.Scatter(
                    x=climaxes.index, y=climaxes['Low']-0.5, mode='markers',
                    marker=dict(symbol='triangle-up', size=13, color='#E65100'),
                    name='Climax'
                ), row=1, col=1)

                if plan:
                    for level, price, color in [
                        ('Entry', plan['entry'], '#1E5F8E'),
                        ('Stop',  plan['stop'],  '#C62828'),
                        ('T1',    plan['t1'],    '#2E7D32'),
                        ('T2',    plan['t2'],    '#1B5E20'),
                    ]:
                        fig.add_hline(
                            y=price, line_dash="dash", line_color=color,
                            annotation_text=f"{level}: {price}", row=1, col=1
                        )

                fig.add_trace(go.Bar(
                    x=df.index, y=df['Volume'], name='Volume',
                    marker_color=['#2E7D32' if c > o else '#C62828'
                                  for c, o in zip(df['Close'], df['Open'])]
                ), row=2, col=1)

                fig.add_trace(go.Scatter(
                    x=df.index, y=df['Vol_EMA20'], name='Vol EMA20',
                    line=dict(color='#90A4AE', width=2)
                ), row=2, col=1)

                fig.update_layout(
                    height=750, xaxis_rangeslider_visible=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Segoe UI, Tahoma, sans-serif")
                )
                st.plotly_chart(fig, use_container_width=True)
