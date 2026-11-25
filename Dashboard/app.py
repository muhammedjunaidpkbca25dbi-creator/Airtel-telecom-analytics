import os                                         # to find the database
import sqlite3                                    # to open it
import pandas as pd                               # to hold query rows
import plotly.express as px                       # to draw the charts
import streamlit as st                            # to build the page
st.set_page_config(page_title='DASHBOARD NAME',   # the browser tab
                   layout='wide')                 # full browser width
CSS = ('<style>'                                  # page spacing:
       '[data-testid="stMainBlockContainer"]'     # the main page area
       '{padding-top: 2.5rem; padding-bottom: 0rem}'  # less space
       '[data-testid="stHeader"] {height: 0rem}'  # no blank top bar
       '</style>')                                # end of the spacing
st.markdown(CSS, unsafe_allow_html=True)          # apply it to the page
HERE = os.path.dirname(os.path.abspath(__file__)) # the dashboard folder
DB = os.path.join(HERE, '..', 'Data', 'raw',      # up one level,
                  'airtel_slim.db')               # into data/raw
@st.cache_data                                    # run each query once
def q(sql, params=()):                            # every query, here
    con = sqlite3.connect(DB)                     # open the database
    try:                                          # run the query...
        return pd.read_sql_query(sql, con,        # ...and hand back
                                 params=params)   # its rows
    finally:                                      # ...then always
        con.close() 
        
st.title("AIRTEL TELECOM ANALYSIS - muhammed junaid pk")
st.caption("For the revenue analyst, understanding what money the base "
           "really brings in, and which plans and circles carry it.")

# ------------------------------------------------------------
# DOMAIN B : REVENUE   (filters: Connection Type and Region)
# ------------------------------------------------------------

RED = '#E40000'                                   # Airtel red
GREY = '#9E9E9E'                                  # for the "stated" bars


def tidy(fig, h=240):
    # make every chart small, with tight margins and no legend title
    fig.update_layout(height=h, margin=dict(l=5, r=5, t=5, b=5),
                      legend_title_text='',
                      legend=dict(orientation='h', y=1.15))
    return fig


def show_table(df):
    # show a small table: no index, full width, height fits the rows
    st.dataframe(df, hide_index=True, use_container_width=True,
                 height=38 * (len(df) + 1))


# ---------- sidebar filters ----------
st.sidebar.header("Filters")

all_types = ['Prepaid', 'Postpaid']
all_regions = q("SELECT DISTINCT region FROM customer_features ORDER BY region")['region'].tolist()

types = st.sidebar.multiselect("Connection Type", all_types, default=all_types)
regions = st.sidebar.multiselect("Region", all_regions, default=all_regions)

# stop early if a filter is empty
if len(types) == 0 or len(regions) == 0:
    st.warning("Please select at least one Connection Type and one Region.")
    st.stop()

# build the WHERE part of every query from the two filters
type_marks = ','.join(['?'] * len(types))         # example: ?,?
region_marks = ','.join(['?'] * len(regions))
WHERE = ("WHERE connection_type IN (" + type_marks + ") "
         "AND region IN (" + region_marks + ")")
P = tuple(types) + tuple(regions)                 # the values for the ?

# the same filters, written for queries that join recharges (r) to customers (c)
JOIN_WHERE = ("WHERE r.recharge_date BETWEEN '2025-01-01' AND '2025-06-30' "
              "AND c.connection_type IN (" + type_marks + ") "
              "AND c.region IN (" + region_marks + ")")

# ---------- the two pages ----------
tab1, tab2 = st.tabs(["Overview — Whole Base", "Plan — One Plan at a Time"])


# ============================================================
# PAGE 1 : OVERVIEW
# ============================================================
with tab1:
    # ---------- B2 + B3 + B9 : headline numbers ----------
    kpi = q("SELECT COUNT(*) AS subs, "
            "AVG(stated_arpu) AS stated, "
            "AVG(actual_arpu_6m) AS actual, "
            "SUM(stated_arpu) AS stated_total, "
            "SUM(actual_arpu_6m) AS actual_total, "
            "SUM(recharge_count = 0) AS paid_nothing "
            "FROM customer_features " + WHERE, P)

    subs = int(kpi['subs'][0])
    stated = kpi['stated'][0]
    actual = kpi['actual'][0]
    stated_total = kpi['stated_total'][0]
    actual_total = kpi['actual_total'][0]
    paid_nothing = int(kpi['paid_nothing'][0])

    # how much the plan-price figure overstates the money received
    overstate = 100 * (stated_total - actual_total) / actual_total

    # ---------- B7 : money received Jan - Jun 2025 ----------
    money = q("SELECT SUM(r.amount_inr) AS total_inr "
              "FROM recharges r "
              "JOIN customer_features c ON c.customer_id = r.customer_id "
              + JOIN_WHERE, P)
    crore = money['total_inr'][0] / 10000000

    # all six numbers sit in one row
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Subscribers", f"{subs:,}")
    c2.metric("Actual ARPU (INR)", f"{actual:,.2f}")
    c3.metric("Stated ARPU (INR)", f"{stated:,.2f}")
    c4.metric("Stated overstates by", f"{overstate:.2f}%")
    c5.metric("Paid nothing (6 months)", f"{paid_nothing:,}")
    c6.metric("Received Jan-Jun (crore)", f"{crore:.2f}")

    # ---------- row of three charts ----------
    g1, g2, g3 = st.columns(3)

    # B4 : stated vs actual ARPU by connection type
    with g1:
        st.markdown("**Stated vs actual ARPU (INR)**")
        by_type = q("SELECT connection_type, "
                    "AVG(stated_arpu) AS stated, "
                    "AVG(actual_arpu_6m) AS actual "
                    "FROM customer_features " + WHERE +
                    " GROUP BY connection_type", P)
        # turn the two columns into rows so plotly can draw grouped bars
        by_type_long = by_type.melt(id_vars='connection_type',
                                    var_name='Measure', value_name='ARPU')
        fig1 = px.bar(by_type_long, x='connection_type', y='ARPU',
                      color='Measure', barmode='group', text_auto=True,
                      color_discrete_sequence=[RED, GREY],
                      labels={'connection_type': ''})
        st.plotly_chart(tidy(fig1), use_container_width=True)

    # B5 : top five plans by actual monthly revenue
    with g2:
        st.markdown("**Top 5 plans by monthly revenue (INR)**")
        plans = q("SELECT plan_name, "
                  "SUM(actual_arpu_6m) AS revenue "
                  "FROM customer_features " + WHERE +
                  " GROUP BY plan_name ORDER BY revenue DESC LIMIT 5", P)
        fig2 = px.bar(plans, x='revenue', y='plan_name', orientation='h',
                      color_discrete_sequence=[RED],
                      labels={'revenue': '', 'plan_name': ''})
        fig2.update_yaxes(autorange='reversed')       # biggest on top
        st.plotly_chart(tidy(fig2), use_container_width=True)

    # B6 : top five circles by actual monthly revenue
    with g3:
        st.markdown("**Top 5 circles by monthly revenue (INR)**")
        circles = q("SELECT circle_name, "
                    "SUM(actual_arpu_6m) AS revenue "
                    "FROM customer_features " + WHERE +
                    " GROUP BY circle_name ORDER BY revenue DESC LIMIT 5", P)
        fig3 = px.bar(circles, x='revenue', y='circle_name', orientation='h',
                      color_discrete_sequence=[RED],
                      labels={'revenue': '', 'circle_name': ''})
        fig3.update_yaxes(autorange='reversed')
        st.plotly_chart(tidy(fig3), use_container_width=True)

    # ---------- row of two charts and the first table ----------
    h1, h2, h3 = st.columns(3)

    # B8 : does tenure change ARPU?
    with h1:
        st.markdown("**Actual ARPU by tenure (years)**")
        tenure = q("SELECT tenure_years, "
                   "AVG(actual_arpu_6m) AS arpu "
                   "FROM customer_features " + WHERE +
                   " GROUP BY tenure_years ORDER BY tenure_years", P)
        fig4 = px.bar(tenure, x='tenure_years', y='arpu', text_auto=True,
                      color_discrete_sequence=[RED],
                      labels={'tenure_years': '', 'arpu': ''})
        fig4.update_traces(texttemplate='%.0f')
        st.plotly_chart(tidy(fig4), use_container_width=True)

    # B7 detail : money received each month
    with h2:
        st.markdown("**Money received each month (INR)**")
        monthly = q("SELECT strftime('%Y-%m', r.recharge_date) AS month, "
                    "SUM(r.amount_inr) AS total_inr "
                    "FROM recharges r "
                    "JOIN customer_features c ON c.customer_id = r.customer_id "
                    + JOIN_WHERE +
                    " GROUP BY month ORDER BY month", P)
        fig5 = px.line(monthly, x='month', y='total_inr', markers=True,
                       color_discrete_sequence=[RED],
                       labels={'month': '', 'total_inr': ''})
        st.plotly_chart(tidy(fig5), use_container_width=True)

    # TABLE 1 : revenue by region
    with h3:
        st.markdown("**Table 1 - Revenue by region**")
        t1 = q("SELECT region AS Region, "
               "COUNT(*) AS Subscribers, "
               "ROUND(AVG(actual_arpu_6m), 2) AS 'Actual ARPU', "
               "ROUND(SUM(actual_arpu_6m), 0) AS 'Monthly revenue' "
               "FROM customer_features " + WHERE +
               " GROUP BY region", P)
        t1['Share %'] = (100 * t1['Monthly revenue'] / actual_total).round(1)
        show_table(t1.sort_values('Monthly revenue', ascending=False))

    # TABLE 2 : zero-payers by connection type
    st.markdown("**Table 2 - Who paid nothing in six months, by connection type**")
    t2 = q("SELECT connection_type AS 'Connection Type', "
           "COUNT(*) AS Subscribers, "
           "SUM(recharge_count = 0) AS 'Paid nothing', "
           "ROUND(100.0 * AVG(recharge_count = 0), 1) AS '% paid nothing', "
           "ROUND(AVG(recharge_count), 2) AS 'Avg payments' "
           "FROM customer_features " + WHERE +
           " GROUP BY connection_type", P)
    show_table(t2)


# ============================================================
# PAGE 2 : ONE PLAN AT A TIME
# ============================================================
with tab2:
    # list the plans that exist in the filtered base, best earner first
    plan_list = q("SELECT plan_name, SUM(actual_arpu_6m) AS revenue "
                  "FROM customer_features " + WHERE +
                  " GROUP BY plan_name ORDER BY revenue DESC", P)

    plan = st.selectbox("Pick a plan (biggest revenue first)",
                        plan_list['plan_name'].tolist())

    # same filters, plus the chosen plan
    PLAN_WHERE = WHERE + " AND plan_name = ?"
    PP = P + (plan,)

    info = q("SELECT MAX(plan_type) AS plan_type, "
             "MAX(price_inr) AS price, "
             "COUNT(*) AS subs, "
             "AVG(actual_arpu_6m) AS actual, "
             "SUM(actual_arpu_6m) AS revenue, "
             "SUM(recharge_count = 0) AS paid_nothing "
             "FROM customer_features " + PLAN_WHERE, PP)

    p_revenue = info['revenue'][0]
    p_nothing = int(info['paid_nothing'][0])

    # share of all revenue in the current filters that this plan brings
    p_share = 100 * p_revenue / actual_total

    # six numbers in one row
    a1, a2, a3, a4, a5, a6 = st.columns(6)
    a1.metric("Plan type", info['plan_type'][0])
    a2.metric("Plan price (INR)", f"{info['price'][0]:,.0f}")
    a3.metric("Subscribers", f"{int(info['subs'][0]):,}")
    a4.metric("Actual ARPU (INR)", f"{info['actual'][0]:,.2f}")
    a5.metric("Monthly revenue (INR)", f"{p_revenue:,.0f}")
    a6.metric("Share of revenue", f"{p_share:.1f}%")

    st.caption(f"{p_nothing:,} subscribers on this plan paid nothing in six months.")

    # ---------- row of three charts ----------
    x1, x2, x3 = st.columns(3)

    # actual ARPU by tenure for this plan
    with x1:
        st.markdown("**Actual ARPU by tenure (years)**")
        p_tenure = q("SELECT tenure_years, "
                     "AVG(actual_arpu_6m) AS arpu "
                     "FROM customer_features " + PLAN_WHERE +
                     " GROUP BY tenure_years ORDER BY tenure_years", PP)
        fig6 = px.bar(p_tenure, x='tenure_years', y='arpu', text_auto=True,
                      color_discrete_sequence=[RED],
                      labels={'tenure_years': '', 'arpu': ''})
        st.plotly_chart(tidy(fig6), use_container_width=True)

    # top five circles for this plan
    with x2:
        st.markdown("**Top 5 circles for this plan (INR)**")
        p_circles = q("SELECT circle_name, "
                      "SUM(actual_arpu_6m) AS revenue "
                      "FROM customer_features " + PLAN_WHERE +
                      " GROUP BY circle_name ORDER BY revenue DESC LIMIT 5", PP)
        fig7 = px.bar(p_circles, x='revenue', y='circle_name', orientation='h',
                      color_discrete_sequence=[RED],
                      labels={'revenue': '', 'circle_name': ''})
        fig7.update_yaxes(autorange='reversed')
        st.plotly_chart(tidy(fig7), use_container_width=True)

    # money received each month for this plan
    with x3:
        st.markdown("**Money received each month (INR)**")
        p_monthly = q("SELECT strftime('%Y-%m', r.recharge_date) AS month, "
                      "SUM(r.amount_inr) AS total_inr "
                      "FROM recharges r "
                      "JOIN customer_features c ON c.customer_id = r.customer_id "
                      + JOIN_WHERE + " AND c.plan_name = ? "
                      "GROUP BY month ORDER BY month", PP)
        fig8 = px.line(p_monthly, x='month', y='total_inr', markers=True,
                       color_discrete_sequence=[RED],
                       labels={'month': '', 'total_inr': ''})
        st.plotly_chart(tidy(fig8), use_container_width=True)

    # ---------- two tables side by side ----------
    y1, y2 = st.columns(2)

    # TABLE 1 : this plan by region
    with y1:
        st.markdown("**Table 1 - SELECTED plan by region**")
        pt1 = q("SELECT region AS Region, "
                "COUNT(*) AS Subscribers, "
                "ROUND(AVG(actual_arpu_6m), 2) AS 'Actual ARPU', "
                "ROUND(SUM(actual_arpu_6m), 0) AS 'Monthly revenue' "
                "FROM customer_features " + PLAN_WHERE +
                " GROUP BY region", PP)
        show_table(pt1.sort_values('Monthly revenue', ascending=False))

    # TABLE 2 : this plan against all plans
    with y2:
        st.markdown("**Table 2 - SELECTED plan vs all plans**")
        cols = ("AVG(stated_arpu) AS stated, "
                "AVG(actual_arpu_6m) AS actual, "
                "100.0 * AVG(recharge_count = 0) AS zero_pct, "
                "100.0 * AVG(is_churned) AS churn ")
        this_row = q("SELECT " + cols + "FROM customer_features " + PLAN_WHERE, PP)
        all_row = q("SELECT " + cols + "FROM customer_features " + WHERE, P)

        compare = pd.DataFrame({
            'Measure': ['Stated ARPU (INR)', 'Actual ARPU (INR)',
                        'Gap (INR)', 'Paid nothing (%)', 'Churn (%)'],
            'This plan': [this_row['stated'][0], this_row['actual'][0],
                          this_row['stated'][0] - this_row['actual'][0],
                          this_row['zero_pct'][0], this_row['churn'][0]],
            'All plans': [all_row['stated'][0], all_row['actual'][0],
                          all_row['stated'][0] - all_row['actual'][0],
                          all_row['zero_pct'][0], all_row['churn'][0]],
        }).round(2)
        show_table(compare)