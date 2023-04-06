#Snapshot diver allows you to look at a DAO's elections on snapshot to see how decentralized they are. Bugs? Ping me on Twitter @edgecaser.

from datetime import datetime
import time
from subgrounds.subgraph import SyntheticField, FieldPath
from subgrounds.subgrounds import Subgrounds
import pandas as pd
import  os as os
import duckdb as db
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st
import re

st.set_page_config(layout="wide")

st.markdown("""
<style>
.bigger-font {
    font-size:18px !important;
}
.biggest-font {
    font-size:20px !important;
}

</style>
""", unsafe_allow_html=True)



st.write('# Snapshot Surfer')
st.write('## By @Edgecaser')
st.write('Version 2')

st.markdown('<p class="bigger-font">This tool will help you view how decentralized a DAO\'s voting power is.</p>', unsafe_allow_html=True)

st.markdown('<p class="bigger-font">DAO stands for Decentralized Autonomous Organization, a bottoms-up team or organization. These are run by votes recorded on the Blockchain.</p>', unsafe_allow_html=True)

st.markdown('<p class="bigger-font">Some DAOs voting power has a 1:1 correlation with their token holdings. Others use different schemes that distribute voting power in different ways, all the way down to one-wallet-one-vote. </p>', unsafe_allow_html=True)

st.markdown('<p class="bigger-font"> When a few people hold a lot of voting power, a small minority drives the result of any proposal on Snapshot. This is not good or bad. There\'s examples of successful organizations with all kinds of power distribution schemes.</p>', unsafe_allow_html=True)

st.markdown('<p class="bigger-font"> This tool helps illustrate how decentralized voting power is in any DAO in Snapshot It will pull down all proposals data and analyze the distribution of power. It will download the data to the folder of your choice </p>', unsafe_allow_html=True)

st.markdown('<p class="bigger-font"> If you are interested in analyzing a single election in more detail, I recommend you visit Snapshot Diver </p>', unsafe_allow_html=True)
st.markdown('[Snapshot Diver](https://edgecaser-snapshotsurfer-snapshotdiver-jilc2t.streamlitapp.com/)')



st.write('### Instructions')

st.markdown('<p class="bigger-font"> Trolls happen. Some DAOs are bombed with fake proposals that gather a handful of voters. This filter lets you ignore them in the analysis (but will be kept in the downloaded data). I find 20 is good enough for small DAOs. For larger DAOs I recommend values of 50 or more.</p>', unsafe_allow_html=True)

filter = st.slider(
    'Only choose proposals that had at least these many voters:',
    int(0), 200, 20, 10)

st.markdown(
    '<p class="bigger-font">Enter the DAO you want to study below by entering its namespace in Snapshot. For example, OlympusDAO has a url like https://snapshot.org/#/olympusdao.eth so its userspace is olympusdao.eth.</p>',
    unsafe_allow_html=True)
st.write('')

spacename = ''
spacename = st.text_input('Where to pull from? Type your selection then press START',help='Which space, eg: curve.eth')

daysLimitInput =''
#daysLimit = 10
daysLimitInput = ''

daysLimit = st.text_input('How many days in the past do you want to go?',help='Snapshotsurfer will pull data going this many days back')
#daysLimit = int(daysLimitInput)


if st.button('START'):

    sg = Subgrounds()
    snapshot = sg.load_api('https://hub.snapshot.org/graphql')

    snapshot.Proposal.datetime = SyntheticField(
      lambda timestamp: str(datetime.fromtimestamp(timestamp)),
      SyntheticField.STRING,
      snapshot.Proposal.end,
    )

    proposals = snapshot.Query.proposals(
        orderBy='created',
        orderDirection='desc',
        first=1000,
        where=[
            snapshot.Proposal.space == spacename,  ##'fuse.eth',
            snapshot.Proposal.state == 'closed'
            ##snapshot.Proposal.title == 'OIP-18: Reward rate framework and reduction',
        ]
    )

    st.write('Let\'s get started! Pulling from: ', spacename, ':sunglasses:')

    proposals_snapshots = sg.query_df([
        proposals.title,
        proposals.created,
        proposals.id,
        proposals.start,
        proposals.end,
        proposals.votes
    ])

    proposals_snapshots['createdDate'] = (pd.to_datetime(proposals_snapshots['proposals_created'], unit='s'))
    proposals_snapshots['startDate'] = (pd.to_datetime(proposals_snapshots['proposals_start'], unit='s'))
    proposals_snapshots['endDate'] = (pd.to_datetime(proposals_snapshots['proposals_end'], unit='s'))
    #pattern = r'^[^-]+-[^-:]+'
    proposals_snapshots['Symbol'] = proposals_snapshots['proposals_title'].str.extract(r'^([^-\s]+[-\s][^-\s:]+)')
    #proposals_snapshots['proposals_title']

    total_snapshots = len(proposals_snapshots)

    proposals_choices = sg.query(proposals.choices)

    proposals_choices = pd.DataFrame(proposals_choices)

    olympus_governance_view = pd.DataFrame()
    olympus_governance_view = pd.concat([proposals_snapshots, proposals_choices], axis=1)

    ##let's view the output just to make sure
    olympus_governance_view.head(5)

    #let's remove duplicate rows the easy way, and add the name of the DAO to the table
    olympus_governance_view.drop_duplicates()

    #olympus_governance_view.insert(0, 'DAO', spacename)


    st.write("Sample list of Proposals")
    st.write(olympus_governance_view.head(10))

    @st.cache
    def convert_df(df):
        return df.to_csv().encode('utf-8')


    csv = convert_df(olympus_governance_view)

    st.download_button(
        "Press to download list of Proposals",
        csv,
        "olympus_governance_view_clean.csv",
        "text/csv",
        key='download-csv'
    )


    st.write('Pulling vote records...')
    #mybar = st.progress(0)

    voteTicker = 0
    totalProposals = len(olympus_governance_view)
    voteslist = pd.DataFrame()
    votesDb = pd.DataFrame()
    voteListLength = 1000
    datediff = 0
    now = 0
    daysAgo = 0
    # daysLimit = 90
    datediff = 0
    epochlimit = (90 * 86400)
    ut = time.time()
    limitTimestamp = int(ut - epochlimit)
    limitDate = datetime.fromtimestamp(limitTimestamp)
    limitDate = limitDate.strftime('%m-%d-%Y')
    exit = False

    while int(datediff) < int(daysLimit):
        proposal_id = olympus_governance_view.iloc[voteTicker, 2]
        skipValue = (voteTicker) * (1000)
        vote_tracker = snapshot.Query.votes(
            # orderBy = 'created',
            # orderDirection='asc',
            first=1000,
            where=[
                snapshot.Vote.proposal == proposal_id
                # snapshot.Vote.created > limitTimestamp
            ]
        )
        voting_snapshots = sg.query_df([
            vote_tracker.id,
            vote_tracker.voter,
            vote_tracker.created,
            vote_tracker.choice,
            vote_tracker.vp
        ])

        voting_snapshots['proposals_id'] = olympus_governance_view.iloc[voteTicker, 2]
        # voteDate = votesDb.iat[voteTicker,4]

        votesDb = pd.concat([voting_snapshots, votesDb])
        votesDb['createdDate'] = (pd.to_datetime(votesDb['votes_created'], unit='s'))
        then = votesDb.iat[voteTicker, 6]
        now = datetime.now()
        delta = now - then
        datediff = delta.days
        votesDbLength = len(votesDb)
        voteListLength = len(voting_snapshots)
        recordTimestamp1 = votesDb.iat[voteTicker, 2]
        recordTimestamp = datetime.fromtimestamp(recordTimestamp1)
        now = (int(datetime.utcnow().timestamp()))
        # datediff=abs(int(now) - recordTimestamp1)

        #print('ticker', voteTicker, 'proposal', proposal_id, 'records:', voteListLength, 'DB size:', votesDbLength,'    -days ago:', datediff, '     -date', then, '    -exit?', exit)
        # print(proposal_id, voteDate, datediff)

        #chartprogress = (voteTicker/totalProposals)
        #chartprogress = int(datediff)/int(daysLimit)
        #print(chartprogress)
        ##clear_output(wait=True)
        #mybar.progress(chartprogress)
        voteTicker = voteTicker + 1

    #votesDb.drop_duplicates

    votesDb.rename(columns={"createdDate": "voteDate"}, inplace=True)
    votesDb.drop_duplicates(inplace=True)
    votesDb.drop_duplicates()
    votesDb.head(10000)

    st.write('Sample output: Vote records',votesDb.head(10))

    @st.cache
    def convert_df(df):
        return df.to_csv().encode('utf-8')
    csv = convert_df(votesDb)

    st.download_button(
        "Press to download vote records",
        csv,
        "voting_snapshots_list.csv",
        "text/csv",
        key='download-csv'
    )

    governance_data  = pd.DataFrame()

    #I join these two tables to create my charts as it makes life easier. We are going to build the charts here now, so here we go
    governance_data = pd.merge(votesDb, olympus_governance_view, how='inner', left_on='proposals_id',
                           right_on='proposals_id')
    st.write('sample output: governance data', governance_data.head(10))

    @st.cache
    def convert_df(df):
        return df.to_csv().encode('utf-8')

    csv = convert_df(governance_data)

    st.download_button(
        "Press to download joined governance data",
        csv,
        "governance_data.csv",
        "text/csv",
        key='download-csv'
    )
    crunch_data = db.query("select "
                           "A.proposals_id"
                           "    ,A.startDate "
                           "    ,A.proposals_title "
                           "    ,A.votes_voter "
                           "    ,A.votes_vp "
                           "    ,A.voteDate "
                           ",sum(A.votes_vp) over (Partition by proposals_id  order by votes_vp desc, voteDate asc) as cumulative_vp "
                           ",sum(A.votes_vp) over (Partition by proposals_id) as total_vp "
                           ",(votes_vp::decimal/sum(votes_vp::decimal) over (Partition by proposals_id)) as percentage_of_total_vp "
                           ",((sum(A.votes_vp) over (Partition by proposals_id  order by votes_vp desc, voteDate asc))::decimal/sum(votes_vp::decimal) over (Partition by proposals_id)) as cum_percentage_of_total_vp "
                           ",round((sum(A.votes_vp) over (Partition by proposals_id  order by votes_vp desc, voteDate asc))::decimal/sum(votes_vp::decimal) over (Partition by proposals_id)) as cum_percentage_of_total_vp_stepped "
                           ",row_number() over (Partition by proposals_id order by votes_vp desc, voteDate asc) as proposal_voter_rank "

                           ",(count(*) over (Partition by proposals_id))::decimal total_voters "

                           ",(count(*) over (Partition by proposals_id  order by votes_vp desc, voteDate asc))::decimal/(count(*) over (Partition by proposals_id))::decimal percentage_voters_counted "

                           ",round(100*(count(*) over (Partition by proposals_id  order by votes_vp desc, voteDate asc))::decimal/(count(*) over (Partition by proposals_id)))::decimal percentage_voters_counted_stepped "
                           "from "
                           "    governance_data  A "
                           # "where   to_timestamp((votes_Created::bigint))<'2023-01-01' "
                           ""
                           "Group by "
                           "A.proposals_id"
                           "    ,A.startDate "
                           "    ,A.proposals_title "
                           "    ,A.votes_voter "
                           "    ,A.votes_vp "
                           "    ,A.voteDate "
                           ""
                           "Order by "
                           "    A.startDate  asc "
                           "    , votes_vp desc "
                           "    , voteDate asc"
                           "").df()

    crunch_data.insert(0, 'DAO', spacename)




    #leaders = crunch_data.loc[crunch_data['proposal_voter_rank'] <= 3]
    #leader_count = leaders.votes_voter.nunique()

    leader_ranks = db.query("with leader_ranks as "
                        "(Select distinct "
                        "   B.proposals_id"
                        "   ,B.votes_voter"
                        "   ,B.proposal_voter_rank "
                        "   ,(B.proposal_voter_rank +1) as leader_rank "
                        "From "
                        "   (select "
                        "proposals_id"
                        ",votes_voter "
                        ",votes_choice"
                        ",votes_vp"
                        ",votes_created  "
                        ",sum(votes_vp) over (Partition by proposals_id  order by votes_vp desc, votes_created asc) as cumulative_vp"
                        ",sum(votes_vp) over (Partition by proposals_id) as total_vp"
                        ",(votes_vp::decimal/sum(votes_vp::decimal) over (Partition by proposals_id)) as percentage_of_total_vp "
                        ",((sum(votes_vp) over (Partition by proposals_id  order by votes_vp desc, votes_created asc))::decimal/sum(votes_vp::decimal) over (Partition by proposals_id)) as cum_percentage_of_total_vp "
                        "    ,round((sum(votes_vp) over (Partition by proposals_id  order by votes_vp desc, votes_created asc))::decimal/sum(votes_vp::decimal) over (Partition by proposals_id)) as cum_percentage_of_total_vp_stepped "
                        ",row_number() over (Partition by proposals_id order by votes_vp desc, votes_created asc) as proposal_voter_rank "
                        ",count(votes_voter) over (Partition by proposals_id  order by votes_vp desc, votes_created asc) total_voters "
                        ",(count(*) over (Partition by proposals_id  order by votes_vp desc, votes_created asc))::decimal/(count(*) over (Partition by proposals_id))::decimal percentage_voters_counted "
                        ",round(100*(count(*) over (Partition by proposals_id  order by votes_vp desc, votes_created asc))::decimal/(count(*) over (Partition by proposals_id)))::decimal percentage_voters_counted_stepped "
                        "from "
                        "    governance_data  "
                        ""
                        "Group by "
                        "    proposals_id"
                        "    ,votes_voter"
                        "    ,votes_choice"
                        "    , votes_vp "
                        "    , votes_created "
                        ""
                        "Order by "
                        "    proposals_id "
                        "    ,votes_vp desc "
                        "    , votes_created asc) B "
                        "where "
                        "   B.cum_percentage_of_total_vp<=0.5) "
                        ""
                        "Select "
                        "   *"
                        "From crunch_data A"
                        "   Join leader_ranks B on A.proposal_voter_rank = B.leader_rank and A.proposals_id = B.proposals_id"
                        ""
                        ).df()
    #st.write(leader_ranks)

    dao_members = crunch_data.groupby('DAO').votes_voter.nunique()
    dao_members = dao_members.iloc[0]
    leader_count =leader_ranks.votes_voter.nunique()
    elite = round((leader_count)/(dao_members),4)

    #$print(dao_members, "{0:.2%}".format(elite))

    st.write('Sample Stats data')
    st.write(crunch_data.head(10))
    ##spit out the file!


    crunch_data = crunch_data.loc[crunch_data['total_voters']>filter]

    @st.cache
    def convert_df(df):
        return df.to_csv().encode('utf-8')
    csv = convert_df(crunch_data)
    st.download_button(
        "Press to download Stats data",
        csv,
        "aggregated_data.csv",
        "text/csv",
        key='download-csv'
    )

    curve_data = db.query(
        "select "
        "   percentage_voters_counted_stepped "
        "   , avg(percentage_voters_counted) avg_percentage_voters_counted "
        "   , avg(cum_percentage_of_total_vp) avg_percentage_of_total_vp "
        "   ,'Grand Average' as proposal "
        "from crunch_data "
        " group by 1 "
        "UNION ALL "
        "SELECT "
        "   percentage_voters_counted_stepped "
        "   ,percentage_voters_counted "
        "   ,cum_percentage_of_total_vp "
        "   ,proposals_id "
        "FROM crunch_data "
         ).df()

    @st.cache
    def convert_df(df):
        return df.to_csv().encode('utf-8')
    csv = convert_df(curve_data)
    st.download_button(
        "Press to download aggregate curve data",
        csv,
        "aggregated_data.csv",
        "text/csv",
        key='download-csv'
    )

    plt.rc("figure", figsize=(40, 20))
    #sns.set_style("whitegrid")
    plt.rc("font", size=25)
    data_means = crunch_data.groupby("percentage_voters_counted_stepped")["cum_percentage_of_total_vp","percentage_voters_counted"].agg("mean").reset_index()
    ##print(data_means)
    plot_title = spacename + ' snapshots % of vote along population with Average as X'

    fig = plt.figure(figsize=(30, 15))

    #plt.rc("figure", figsize=(40, 20))
    sns.set_style("whitegrid")
    plt.rc("font", size=25)
    data_means = crunch_data.groupby("percentage_voters_counted_stepped")[
        "cum_percentage_of_total_vp", "percentage_voters_counted"].agg("mean").reset_index()
    ##print(data_means)

    p50 = db.query("select min(percentage_voters_counted) "
                   "from data_means  where cum_percentage_of_total_vp>=0.5 ").df()
    p50_val = p50.iloc[0, 0]
    p50display = round(100 * (p50.iloc[0, 0]), 2)

    st.write('### On average, a proposal at ', ("{0}".format(spacename)), 'takes ', ("{0:.2%}".format(p50_val)),
             'of the voting population to accumulate half or more of all the votes.')

    st.write('### A total of ', ("{0}".format(leader_count)), 'addresses have driven the result of all proposals at',
             spacename, '.')
    st.write('### That\'s', ("{0:.2%}".format(elite)), 'of all', ("{0}".format(dao_members)),
             'voters the DAO has had in the last',("{0}".format(daysLimit)),'days.')

    st.write('### Let\'s visualize this: The chart below describes all proposals in', spacename,
             '.The orange markers represent what percentage of the population it takes to reach a given percentage of voting power.')


    crunch_data['symbol'] = crunch_data['proposals_title'].str.extract(r'^([^-\s]+[-\s][^-\s:]+)')
    crunch_data['symbol'] = crunch_data['symbol'].str.strip('[]')


    plot_title = spacename + ' snapshots\' % of vote along population with Average as X'

    ax = sns.scatterplot(data=crunch_data, hue="symbol", y="cum_percentage_of_total_vp",
                         x="percentage_voters_counted_stepped").set(title=plot_title, xlabel='% of voters',
                                                                    ylabel='% of voting power')
    chart = sns.scatterplot(data=data_means, x="percentage_voters_counted_stepped", y="cum_percentage_of_total_vp",
                            zorder=3, s=800, marker='X', color='orange')
    plt.legend(bbox_to_anchor=(1.02, 0.99), loc='upper left', borderaxespad=0)
    st.pyplot(fig)

    voterCounts = db.query("Select"
                           " symbol "
                           ",count(distinct votes_voter) as voters "
                           "From crunch_data "
                           "Group by 1").df()

    #Second chart
    fig = plt.figure(figsize=(30, 15))
    #plt.rc("figure", figsize=(40, 20))
    sns.set_style("whitegrid")
    plt.rc("font", size=25)
    plot_title = spacename + ': Voters per proposal'
    chart = sns.barplot(data=voterCounts, x="symbol", y="voters", color='orange')
    chart.set_xticklabels(chart.get_xticklabels(), rotation=45, ha='right')
    st.pyplot(fig)


    st.markdown(
        '<p class="bigger-font">All done. Enjoy! Feel free to enter another space name to pull more data.</p>',
        unsafe_allow_html=True)
    # The chart above shows what % of all possible votes has been cast (Y axis) as each incremental percent of the voting population casts their vote (X axis). Each line is a Proposal and has a unique color, so that a dot on each percent point represents what % of total voting power was accumulated by that group. The color represents which vote was cast.
    # The Orange X shows the average % of power accumulated across all elections.

