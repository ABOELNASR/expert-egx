import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Expert-EGX v6", layout="wide")

# ========== Helpers ==========
def get_now_cairo():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Africa/Cairo"))
    except Exception:
        return datetime.now(timezone(timedelta(hours=2)))

def market_is_open(now):
    # البورصة المصرية: الأحد - الخميس، 10:00 - 14:30 (توقيت القاهرة)
    wd = now.weekday()  # Mon=0 ... Sun=6
    if wd in [4, 5]:  # الجمعة والسبت
        return False
    minutes = now.hour * 60 + now.minute
    return (10 * 60) <= minutes < (14 * 60 + 30)

# ========== Theme state ==========
if 'theme' not in st.session_state:
    st.session_state.theme = "Auto"

def inject_css():
    theme = st.session_state.theme
    if theme == "Light":
        vars_css = """<style>:root{
            --primary:#1E5F8E;--success:#2E7D32;--danger:#C62828;
            --warning:#E65100;--neutral:#546E7A;--surface:#F5F7FA;
            --master:#1565C0;--shakeout:#6A1B9A;--climax:#E65100;--critical:#00695C;
        }</style>"""
    elif theme == "Dark":
        vars_css = """<style>:root{
            --primary:#4A9EDB;--success:#66BB6A;--danger:#EF5350;
            --warning:#FFA726;--neutral:#90A4AE;--surface:#1E1E1E;
            --master:#64B5F6;--shakeout:#BA68C8;--climax:#FFA726;--critical:#4DB6AC;
        }</style>"""
    else:
        vars_css = """<style>
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
    base_css = """<style>
    .stApp { font-family: 'Segoe UI', Tahoma, sans-serif; }
    .expert-logo { font-size: 1.9rem; font-weight: 800; color: var(--primary);
        letter-spacing: 2px; margin: 0; padding: 0; }
    .expert-tagline { color: var(--neutral); font-size: 0.95rem;
        margin-top: 2px; margin-bottom: 1.2rem; }
    .expert-divider { height: 3px; background: var(--primary);
        border-radius: 2px; margin: 8px 0 20px 0; }
    .badge { display: inline-block; padding: 3px 10px; border-radius: 12px;
        font-size: 0.75rem; font-weight: 700; letter-spacing: 0.5px; direction: ltr; }
    .badge-master    { background: rgba(21,101,192,0.15); color: var(--master);   border: 1px solid var(--master); }
    .badge-shakeout  { background: rgba(106,27,154,0.15); color: var(--shakeout); border: 1px solid var(--shakeout); }
    .badge-climax    { background: rgba(230,81,0,0.15);   color: var(--climax);   border: 1px solid var(--climax); }
    .badge-critical  { background: rgba(0,105,92,0.15);   color: var(--critical); border: 1px solid var(--critical); }
    .badge-excellent { background: rgba(46,125,50,0.15);  color: var(--success);  border: 1px solid var(--success); }
    .badge-good      { background: rgba(30,95,142,0.15);  color: var(--primary);  border: 1px solid var(--primary); }
    .badge-ok        { background: rgba(230,81,0,0.15);   color: var(--warning);  border: 1px solid var(--warning); }
    .badge-weak      { background: rgba(198,40,40,0.15);  color: var(--danger);   border: 1px solid var(--danger); }
    .badge-closed    { background: rgba(46,125,50,0.15);  color: var(--success);  border: 1px solid var(--success); }
    .badge-forming   { background: rgba(230,81,0,0.15);   color: var(--warning);  border: 1px solid var(--warning); }
    .sidebar-title { font-weight: 700; color: var(--primary); font-size: 0.95rem;
        margin-top: 1.1rem; margin-bottom: 0.4rem;
        border-bottom: 2px solid var(--primary); padding-bottom: 3px; }
    [data-testid="stMetricValue"] { color: var(--primary); font-weight: 700; }
    [data-testid="stMetricLabel"] { color: var(--neutral); font-size: 0.85rem; }
    [data-testid="stMarkdownContainer"] p,
    .stText, .stCaption { direction: rtl; text-align: right; }
    </style>"""
    st.markdown(vars_css, unsafe_allow_html=True)
    st.markdown(base_css, unsafe_allow_html=True)

def signal_badge(sig):
    mapping = {
        "Master": ("MASTER", "badge-master"),
        "Shakeout": ("SHAKEOUT", "badge-shakeout"),
        "Climax": ("CLIMAX", "badge-climax"),
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

def candle_badge(is_closed):
    if is_closed:
        return '<span class="badge badge-closed">مكتملة</span>'
    return '<span class="badge badge-forming">جارية</span>'

# ========== Tickers ==========
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

# ========== Features ==========
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
        (df['Lower_Wick_Ratio'] > 0.5) & (df['Close_Position'] > 0.5) &
        (df['Is_Downtrend'] == 1) & (df['Is_Master'] == 1)
    ).astype(int)
    df['Is_Climax'] = (
        (df['Is_Downtrend'] == 1) & (df['Volume'] > 2 * df['Vol_EMA20']) &
        (df['Range_Ratio'] > 1.5) & (df['Close_Position'] > 0.4)
    ).astype(int)
    df['Is_Decision'] = (
        (df['Is_Master'] == 1) | (df['Is_Shakeout'] == 1) | (df['Is_Climax'] == 1) |
        ((df['Is_Critical_Vol'] == 1) & (df['Is_Buyer'] == 1) & (df['Is_Downtrend'] == 1))
    ).astype(int)
    df['Signal_Type'] = 'None'
    df.loc[df['Is_Shakeout']==1, 'Signal_Type'] = 'Shakeout'
    df.loc[df['Is_Climax']==1, 'Signal_Type'] = 'Climax'
    df.loc[(df['Is_Master']==1) & (df['Signal_Type']=='None'), 'Signal_Type'] = 'Master'
    df.loc[(df['Is_Critical_Vol']==1) & (df['Is_Buyer']==1) & (df['Is_Downtrend']==1) & (df['Signal_Type']=='None'), 'Signal_Type'] = 'Critical Vol'
    return df

# ========== Candle selection ==========
def select_last_candle(df, candle_mode):
    now = get_now_cairo()
    is_open = market_is_open(now)
    last_idx = df.index[-1]
    last_date = last_idx.date() if hasattr(last_idx, 'date') else last_idx
    today = now.date()
    has_today = (last_date == today)

    if candle_mode == "شمعة اليوم":
        return df.iloc[-1], not (has_today and is_open)

    if candle_mode == "شمعة امبارح (مغلقة)":
        if has_today and len(df) >= 2:
            return df.iloc[-2], True
        return df.iloc[-1], True

    # تلقائي
    if has_today and is_open and len(df) >= 2:
        return df.iloc[-2], True
    return df.iloc[-1], True

# ========== Trade plan (R:R + Expectancy) ==========
def calculate_trade_plan(row, cost_pct=0.005, wr=0.74):
    entry = row['High']
    stop = row['Low'] * 0.99
    range_hl = row['Range_HL']

    if range_hl <= 0 or pd.isna(range_hl) or entry <= stop:
        return None

    t1 = row['Low'] + 1.618 * range_hl
    t2 = row['Low'] + 2.618 * range_hl

    risk_abs = entry - stop
    if risk_abs <= 0:
        return None

    r_t1 = (t1 - entry) / risk_abs
    r_t2 = (t2 - entry) / risk_abs
    cost_in_r = (cost_pct * entry) / risk_abs

    # Expectancy = P(Full)×avg_full_R + P(Partial)×avg_partial_R − P(Loss)×1R − costs
    full_pct = wr * 0.53
    partial_pct = wr * 0.47
    loss_pct = 1 - wr
    avg_full_r = 0.5 * r_t1 + 0.5 * r_t2
    avg_partial_r = 0.5 * r_t1
    expectancy = full_pct * avg_full_r + partial_pct * avg_partial_r - loss_pct * 1.0
    net_r = expectancy - cost_in_r

    return {
        'entry': round(entry, 2),
        'stop': round(stop, 2),
        't1': round(t1, 2),
        't2': round(t2, 2),
        'risk_pct': round((entry - stop) / entry * 100, 2),
        'range_pct': round(row['Range_Pct'] * 100, 2),
        'r_t1': round(r_t1, 2),
        'r_t2': round(r_t2, 2),
        'net_r': round(net_r, 3),
    }

# ========== Scan ==========
@st.cache_data(ttl=1800, show_spinner=False)
def scan_market(tickers_tuple, min_range_pct, min_vol_ratio, signal_filter, candle_mode):
    tickers = list(tickers_tuple)
    progress = st.progress(0, text="جاري تحميل البيانات...")
    data = yf.download(tickers, period="1y", group_by='ticker', auto_adjust=True, progress=False, threads=True)
    results = []
    for i, ticker in enumerate(tickers):
        progress.progress((i+1)/len(tickers), text=f"فحص {ticker}... ({i+1}/{len(tickers)})")
        try:
            if ticker not in data.columns.levels[0]:
                continue
            df = data[ticker].dropna()
            if len(df) < 60:
                continue
            if df['Volume'].tail(30).mean() < 50000:
                continue
            df = build_strategy_features(df)
            if len(df) < 30:
                continue

            last, is_closed = select_last_candle(df, candle_mode)

            if last['Is_Decision'] != 1:
                continue
            if last['Range_Pct'] * 100 < min_range_pct:
                continue
            if last['Vol_Ratio_EMA20'] < min_vol_ratio:
                continue
            if signal_filter != "الكل" and signal_filter not in last['Signal_Type']:
                continue

            plan = calculate_trade_plan(last)
            if plan is None:
                continue

            if plan['net_r'] >= 0.15:
                quality = "ممتاز"
            elif plan['net_r'] >= 0.10:
                quality = "جيد"
            elif plan['net_r'] >= 0.05:
                quality = "مقبول"
            else:
                quality = "ضعيف"

            results.append({
                'السهم': ticker.replace('.CA',''),
                'الجودة': quality,
                'الإشارة': last['Signal_Type'],
                'الشمعة': 'مكتملة' if is_closed else 'جارية',
                'السعر': round(last['Close'], 2),
                'الدخول': plan['entry'],
                'الوقف': plan['stop'],
                'الهدف 1': plan['t1'],
                'الهدف 2': plan['t2'],
                'R:R T1': plan['r_t1'],
                'R:R T2': plan['r_t2'],
                'المخاطرة %': plan['risk_pct'],
                'المدى %': plan['range_pct'],
                'Net R': plan['net_r'],
            })
        except Exception:
            continue
    progress.empty()
    return pd.DataFrame(results)

# ========== Theme switcher (before CSS) ==========
st.sidebar.markdown('<div class="sidebar-title">المظهر</div>', unsafe_allow_html=True)
theme_choice = st.sidebar.radio(
    "Theme", ["Auto", "Light", "Dark"],
    index=["Auto", "Light", "Dark"].index(st.session_state.theme),
    horizontal=True, label_visibility="collapsed", key="theme_radio"
)
if theme_choice != st.session_state.theme:
    st.session_state.theme = theme_choice
    st.rerun()

inject_css()

# ========== Header ==========
st.markdown('<div class="expert-logo">EXPERT-EGX</div>', unsafe_allow_html=True)
st.markdown('<div class="expert-tagline">الإصدار 6</div>', unsafe_allow_html=True)
st.markdown('<div class="expert-divider"></div>', unsafe_allow_html=True)

# ========== Candle mode ==========
st.sidebar.markdown('<div class="sidebar-title">الشمعة</div>', unsafe_allow_html=True)
candle_label = st.sidebar.radio(
    "اختر",
    ["تلقائي (موصى به)", "شمعة اليوم", "شمعة امبارح (مغلقة)"],
    label_visibility="collapsed",
    help="تلقائي: آخر شمعة مغلقة (شمعة امبارح لو السوق مفتوح)"
)
candle_mode = {
    "تلقائي (موصى به)": "تلقائي",
    "شمعة اليوم": "شمعة اليوم",
    "شمعة امبارح (مغلقة)": "شمعة امبارح (مغلقة)"
}[candle_label]

# ========== Preset ==========
st.sidebar.markdown('<div class="sidebar-title">Preset</div>', unsafe_allow_html=True)
preset = st.sidebar.selectbox(
    "اختر",
    ["متوازن (موصى به)", "محافظ (جودة عالية)", "استكشافي", "مخصص"],
    label_visibility="collapsed"
)

# ========== Filters ==========
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

# ========== Assumptions (transparent) ==========
st.sidebar.markdown("---")
st.sidebar.markdown("**الافتراضات:**")
st.sidebar.caption(
    "Win Rate 74% (تاريخي) — Full Win 53% من الرابحين | Partial 47% | تكاليف 0.5%"
)

# ========== Main ==========
st.subheader("مسح السوق")
now_cairo = get_now_cairo()
st.caption(f"آخر تحديث: {now_cairo.strftime('%Y-%m-%d %H:%M')} (القاهرة)")

if market_is_open(now_cairo) and candle_mode == "شمعة اليوم":
    st.warning(
        "السوق مفتوح حاليًا — الإشارات مبنية على شمعة اليوم غير المكتملة، "
        "وقابلة للتغير حتى إغلاق السوق (14:30 القاهرة)."
    )

if st.button("بدء المسح", type="primary", use_container_width=True):
    with st.spinner("جاري المسح..."):
        results_df = scan_market(
            tuple(EGX_TICKERS), min_range_pct, min_vol_ratio, signal_filter, candle_mode
        )

    if results_df.empty:
        st.warning("مفيش إشارات بالمواصفات دي. جرب تخفف الفلاتر أو استخدم Preset استكشافي.")
    else:
        results_df = results_df.sort_values('Net R', ascending=False).reset_index(drop=True)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("عدد الإشارات", len(results_df))
        col2.metric("أعلى Net R", f"+{results_df['Net R'].max():.3f}R")
        col3.metric("متوسط Net R", f"+{results_df['Net R'].mean():.3f}R")
        col4.metric("أعلى R:R T2", f"{results_df['R:R T2'].max():.2f}R")

        st.divider()
        st.subheader(f"{len(results_df)} سهم عليهم إشارات:")

        for _, row in results_df.iterrows():
            header = f"**{row['السهم']}**  ·  Net R: +{row['Net R']:.3f}"
            with st.expander(header, expanded=(row.name < 3)):
                st.markdown(
                    f"{signal_badge(row['الإشارة'])} &nbsp; "
                    f"{quality_badge(row['الجودة'])} &nbsp; "
                    f"{candle_badge(row['الشمعة'] == 'مكتملة')}",
                    unsafe_allow_html=True
                )
                c1, c2, c3, c4, c5, c6 = st.columns(6)
                c1.metric("السعر", row['السعر'])
                c2.metric("الدخول", row['الدخول'])
                c3.metric("الوقف", row['الوقف'])
                c4.metric("T1 (50%)", row['الهدف 1'])
                c5.metric("T2 (50%)", row['الهدف 2'])
                c6.metric("Net R", f"+{row['Net R']:.3f}")

                st.caption(
                    f"R:R T1 = {row['R:R T1']:.2f}R | R:R T2 = {row['R:R T2']:.2f}R | "
                    f"المخاطرة: {row['المخاطرة %']}% | المدى: {row['المدى %']}%"
                )
                st.caption(
                    f"التفعيل: اختراق {row['الدخول']} | الإبطال: كسر {row['الوقف']}"
                )

                progress_val = min(100, max(0, row['Net R'] * 500))
                st.progress(progress_val / 100)

        st.divider()
        with st.expander("جدول مختصر"):
            st.dataframe(results_df, use_container_width=True, hide_index=True)
            csv = results_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "تنزيل CSV", csv,
                f"signals_{now_cairo.strftime('%Y%m%d')}.csv", "text/csv"
            )
