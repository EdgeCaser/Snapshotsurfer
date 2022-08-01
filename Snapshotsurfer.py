#Snapshot diver allows you to look at a DAO's elections on snapshot to see how decentralized they are. Bugs? Ping me on Twitter @edgecaser.

from datetime import datetime
from datetime import date
from subgrounds.subgraph import SyntheticField, FieldPath
from subgrounds.subgrounds import Subgrounds

import pandas as pd
import duckdb as db
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st

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
    '<p class="bigger-font">Enter the DAO you want to study below by entering its namespace in Snapshot. For example, OlympusDAO has a url like https://snapshot.org/#/olympusdao.eth. Its userspace is olympusdao.eth.</p>',
    unsafe_allow_html=True)
st.write('')


spacename = st.text_input('Where to pull from? Type your selection then press START',help='Which space, eg: curve.eth')


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
      first=10000,

      where=[
        snapshot.Proposal.space == spacename, ##'fuse.eth',
        snapshot.Proposal.state == 'closed'
        ##snapshot.Proposal.title == 'OIP-18: Reward rate framework and reduction',
      ]
    )

    st.write('Let\'s get started! Pulling from: ', spacename, ':sunglasses:')


    proposals_snapshots = sg.query_df([
        proposals.title,
        proposals.id,
        proposals.body,
        proposals.scores_total,
        proposals.created
    ])

    proposals_choices = sg.query(proposals.choices)

    proposals_choices = pd.DataFrame(proposals_choices)

    olympus_governance_view = pd.concat([proposals_snapshots,proposals_choices], axis=1)

    ##let's view the output just to make sure
    olympus_governance_view.head(5)

    #let's remove duplicate rows the easy way, and add the name of the DAO to the table
    olympus_governance_view_clean = olympus_governance_view.copy(deep=True)

    olympus_governance_view_clean = db.query("select  to_timestamp(proposals_created) as proposal_date,*  "
                                         "from olympus_governance_view_clean order by proposals_created desc").df()

    olympus_governance_view_clean.insert(0, 'DAO', spacename)


    st.write("Sample list of Proposals")
    st.write(olympus_governance_view_clean.head(10))

    @st.cache
    def convert_df(df):
        return df.to_csv().encode('utf-8')


    csv = convert_df(olympus_governance_view_clean)

    st.download_button(
        "Press to download list of Proposals",
        csv,
        "olympus_governance_view_clean.csv",
        "text/csv",
        key='download-csv'
    )

    total_proposals = len(olympus_governance_view_clean)
    #total_proposals

    proposal_id = olympus_governance_view_clean.iloc[0,2]
    #proposal_id

    #st.write("HIYA - just checking")

    vote_tracker = snapshot.Query.votes(
        orderBy='created',
        orderDirection='desc',
        first=10000,
        where=[
            snapshot.Vote.proposal == proposal_id
        ]
    )
    #st.write("HIYA2 - just checking")

    voting_snapshots_list = sg.query_df([
        vote_tracker.id,
        vote_tracker.voter,
        vote_tracker.created,
        vote_tracker.choice,
        vote_tracker.vp
    ])

    #st.write("HIYA3 - just checking")

    st.write('Pulling vote records...')
    mybar = st.progress(0)
    x=0

    while x <total_proposals:
        proposal_id = olympus_governance_view_clean.iloc[x,3]
        #st.write(proposal_id)
        vote_tracker = snapshot.Query.votes(
        orderBy = 'created',
        orderDirection='desc',
        first=10000,
        where=[
          snapshot.Vote.proposal == proposal_id
        ]
        )

        voting_snapshots = sg.query_df([
        vote_tracker.id,
        vote_tracker.voter,
        vote_tracker.created,
        vote_tracker.choice,
        vote_tracker.vp
        ])

        voting_snapshots['Proposal'] = proposal_id
        voting_snapshots_list=pd.concat([voting_snapshots_list, voting_snapshots])

        x=x+1
        chartprogress = min((x/total_proposals),1)
        progress = 100*(round(x/total_proposals,4))
        ##clear_output(wait=True)
        mybar.progress(chartprogress)

    st.write('Sample output: Vote records',voting_snapshots_list.head(10))

    @st.cache
    def convert_df(df):
        return df.to_csv().encode('utf-8')
    csv = convert_df(voting_snapshots_list)

    st.download_button(
        "Press to download vote records",
        csv,
        "voting_snapshots_list.csv",
        "text/csv",
        key='download-csv'
    )



    #I join these two tables to create my charts as it makes life easier. We are going to build the charts here now, so here we go
    governance_data = pd.merge(voting_snapshots_list, olympus_governance_view_clean, how='inner', left_on='Proposal', right_on='proposals_id')
    del governance_data["proposals_body"]
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
                           "Proposal"
                           ",votes_voter "
                           ",votes_choice"
                           ",votes_vp"
                           ",votes_created"
                           ",sum(votes_vp) over (Partition by Proposal  order by votes_vp desc, votes_created asc) as cumulative_vp"
                           ",sum(votes_vp) over (Partition by Proposal) as total_vp"
                           ",(votes_vp::decimal/sum(votes_vp::decimal) over (Partition by Proposal)) as percentange_of_total_vp "
                           ",((sum(votes_vp) over (Partition by Proposal  order by votes_vp desc, votes_created asc))::decimal/sum(votes_vp::decimal) over (Partition by Proposal)) as cum_percentage_of_total_vp "
                           ",round((sum(votes_vp) over (Partition by Proposal  order by votes_vp desc, votes_created asc))::decimal/sum(votes_vp::decimal) over (Partition by Proposal)) as cum_percentage_of_total_vp_stepped "
                           ",row_number() over (Partition by Proposal order by votes_vp desc, votes_created asc) as proposal_voter_rank "
                           ",count(votes_voter) over (Partition by Proposal  order by votes_vp desc, votes_created asc) total_voters "
                           ",(count(*) over (Partition by Proposal  order by votes_vp desc, votes_created asc))::decimal/(count(*) over (Partition by Proposal))::decimal percentage_voters_counted "
                           ",round(100*(count(*) over (Partition by Proposal  order by votes_vp desc, votes_created asc))::decimal/(count(*) over (Partition by Proposal)))::decimal percentage_voters_counted_stepped "
                       "from "
                       "    governance_data  "
                       ""
                       "Group by "
                       "    Proposal"
                       "    ,votes_voter"
                       "    ,votes_choice"
                       "    , votes_vp "
                       "    , votes_created "
                       ""
                       "Order by "
                       "    Proposal, "
                       "    votes_vp desc "
                       "    , votes_created asc"                           ""
                       "").df()





    crunch_data = crunch_data.loc[crunch_data['total_voters']>filter]

    crunch_data.insert(0, 'DAO', spacename)
    crunch_data.head(n=10)

    st.write('Sample Stats data')
    st.write(crunch_data.head(10))
    ##spit out the file!

    max_voters = crunch_data['total_voters'].max()
    st.write(max_voters, 'max_count')

    leaders = crunch_data.loc[crunch_data['percentange_of_total_vp'] >= 0.25]
    leader_count = leaders.votes_voter.nunique()

    st.write(leader_count, 'leaders')


    dao_members = crunch_data.groupby('DAO').votes_voter.nunique()
    dao_members = dao_members.iloc[0]

    elite = round((leader_count) / (max_voters), 4)



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

    #crunch_data_path =final_file+'\\'+spacename+'_crunch_data_path'+str(date.today().strftime("%b-%d-%Y"))+'_'+str(len(crunch_data))+'.csv'
    #crunch_data.to_csv(crunch_data_path, index = False)
    st.write('Sample Aggregate data')

    fig = plt.figure(figsize=(20, 8))

    plt.rc("figure", figsize=(40, 20))
    sns.set_style("whitegrid")
    plt.rc("font", size=18)
    data_means = crunch_data.groupby("percentage_voters_counted_stepped")["cum_percentage_of_total_vp","percentage_voters_counted","cum_percentage_of_total_vp_stepped"].agg("mean").reset_index()
    ##print(data_means)
    plot_title = spacename + ' snapshots % of vote along population'

    st.write(data_means)

    @st.cache
    def convert_df(df):
        return df.to_csv().encode('utf-8')

    csv = convert_df(data_means)

    st.download_button(
        "Press to download Aggregated data",
        csv,
        "aggregated_data.csv",
        "text/csv",
        key='download-csv'
    )


    p50 = db.query("select min(percentage_voters_counted) "
                   "from data_means  where cum_percentage_of_total_vp>=0.5 ").df()

    p50display = round(100 * (p50.iloc[0, 0]), 2)

    st.write('### On average, a proposal at ', spacename, 'takes ', p50display,
             '% of the voting population to accumulate half or more of all the votes.')

    st.write('### A total of ', leader_count, 'has driven the result of all proposals at', spacename, )
    st.write('### That\'s', ("{0:.2%}".format(elite)), 'of all DAO voters.')

    st.write('### The chart below describes all proposals in', spacename,'.The orange markers represent what percentage of the population it takes to reach a given percentage of voting power.')

    #sns.lineplot(data=crunch_data, y="cum_percentage_of_total_vp",x="percentage_voters_counted_stepped", hue="Proposal",zorder=-3).set(title=plot_title,xlabel='% of voters',ylabel='% of voting power')#, legend=False)
    ax = sns.scatterplot(data=crunch_data, y="cum_percentage_of_total_vp", x="percentage_voters_counted_stepped").set(
        title=plot_title, xlabel='% of voters', ylabel='% of voting power')
    chart = sns.scatterplot(data=data_means, x="percentage_voters_counted_stepped", y="cum_percentage_of_total_vp",
                            zorder=3, s=300, marker='X', color='orange')
    # and save the chart file, too
    #plt.savefig(final_file + '\\' + spacename + ' vote power distribution.png', dpi=50)
    #st.write('Chart Saved')
    # st.pyplot(sns.scatterplot(data=data_means, x="percentage_voters_counted_stepped", y="cum_percentage_of_total_vp", zorder=3, s=600, marker='X', color='orange'))
    st.pyplot(fig)

    st.markdown(
        '<p class="bigger-font">All done. Enjoy! Feel free to enter another space name to pull more data.</p>',
        unsafe_allow_html=True)
    # The chart above shows what % of all possible votes has been cast (Y axis) as each incremental percent of the voting population casts their vote (X axis). Each line is a Proposal and has a unique color, so that a dot on each percent point represents what % of total voting power was accumulated by that group. The color represents which vote was cast.
    # The Orange X shows the average % of power accumulated across all elections.

