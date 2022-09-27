from datetime import datetime
from datetime import date
from subgrounds.subgraph import SyntheticField, FieldPath
from subgrounds.subgrounds import Subgrounds
import math
import pandas as pd
import  os as os
import duckdb as db
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(layout="wide")

if st.button('START'):
    sg = Subgrounds()
    holders = sg.load_api('https://api.studio.thegraph.com/query/28103/token-holders/0.0.13')

    token_balances = holders.Query.tokenHolderBalances(
        orderBy='timestamp',
        first=1000 ,
        orderdirection = 'asc',
        #where=[
          #      token_balances.date  > '2022-09-24'
         #     ]
    )


    balances = sg.query_df([
        token_balances.date,
        token_balances.holder.token,
        token_balances.holder.holder,
        token_balances.balance
    ])
    balances

    n=0
    done = 0
    rowcount = 0
    while done == 0:
        n=n+1
        token_balances_2 = holders.Query.tokenHolderBalances(
            orderBy='timestamp',
            first=1000,
            skip = 1000*1+n,
            orderdirection = 'asc',
            #where=[
             #   token_balances.date  > '2022-09-24'
             # ]
        )

        balances_2 = sg.query_df([
            token_balances_2.date,
            token_balances_2.holder.token,
            token_balances_2.holder.holder,
            token_balances_2.balance
        ])
        last_date = max(balances['tokenHolderBalances_date'])
        rowcount = len(balances_2)
        st.write("iteration:",n,"rows:",rowcount, last_date)
        frames = [balances, balances_2]
        balances = pd.concat(frames)
        if rowcount<1000:
            done=1

    balances

    def convert_df(df):
        return df.to_csv().encode('utf-8')

    csv = convert_df(balances)

    st.download_button(
        "Press to download balances data",
        csv,
        "balances.csv",
        "text/csv",
        key='download-csv'
    )