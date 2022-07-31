#Snapshot diver allows you to pull a single election's data from Snapshot. Bugs? Ping me on Twitter @edgecaser.

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

st.write('# Snapshot Diver')
st.write('### By @Edgecaser')

st.markdown('<p class="bigger-font">This tool will help you pull the detailed results of any Proposal for a Single DAO within Snapshot.</p>', unsafe_allow_html=True)

st.markdown('<p class="bigger-font">DAO stands for Decentralized Autonomous Organization, a bottoms-up team or organization. These are run by votes recorded on the Blockchain.</p>', unsafe_allow_html=True)

st.markdown('<p class="bigger-font">Some DAOs voting power has a 1:1 correlation with their token holdings. Others use different schemes that distribute voting power in different ways, all the way down to one-wallet-one-vote. </p>', unsafe_allow_html=True)


st.markdown('<p class="bigger-font"> If you are interested in analyzing a DAO\'s governance power patterns across all its proposals, visit Snapshotsurfer </p>', unsafe_allow_html=True)
st.markdown('[Snapshotsurfer](https://edgecaser-snapshotsurfer-snapshotsurfer-yyutu2.streamlitapp.com/)')


#instructions
st.markdown(
    '<p class="bigger-font">To use this tool, you will need to know the name space of the DAO you are looking for. For example, OlympusDAO has a url like https://snapshot.org/#/olympusdao.eth. Therefore, write olympusdao.eth when queried to get its data.</p>',
    unsafe_allow_html=True)
st.write('')

st.markdown(
    '<p class="bigger-font">Once you have entered a spacename, you will see the choices of proposals available to analyze.</p>',
    unsafe_allow_html=True)
st.write('')


spacename = st.text_input('Where to pull from? Type your selection then press START',help='Which space, eg: curve.eth')

if len(spacename)>=3:

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

    proposals_snapshots = sg.query_df([
        proposals.title,
        proposals.id,
        proposals.body,
        proposals.scores_total,
        proposals.created
    ])


    #test
    proposals_choices = sg.query(proposals.choices)

    proposals_choices = pd.DataFrame(proposals_choices)

    dao_governance_view = pd.concat([proposals_snapshots, proposals_choices], axis=1)

    #remove duplicates
    dao_governance_view_clean = dao_governance_view.copy(deep=True)

    dao_governance_view_clean = db.query("select  to_timestamp(proposals_created) as proposal_date,*  "
                                         "from dao_governance_view_clean order by proposals_created desc").df()

    dao_governance_view_clean.insert(0, 'DAO', spacename)

    st.write('Directory of proposals available:',dao_governance_view_clean)


    #st.write(snapshots.head(10))

    shape = dao_governance_view_clean.shape
    number_of_choices = shape[1]-6

    number_of_columns = shape[1]

    st.write('columns:',number_of_columns,' number of choices:', number_of_choices)


    snapshots = db.query("select distinct proposals_title, proposals_body from dao_governance_view_clean  ").df()

    choice = ''

    choice = (st.selectbox('Select Proposal and press START',snapshots,1))
    choiceOG = choice

    if len(choice)>3:
        #st.write(choice)

        choicedf = pd.DataFrame(columns=['proposals_title'])

        #st.write(choicedf)


        row = pd.DataFrame({'proposals_title': [choice]})

        #st.write(row)

        choice = choicedf.append(row,ignore_index=True)

        st.write(choice)

        propid = db.query("select distinct dao_governance_view_clean.proposals_id from dao_governance_view_clean join choice on dao_governance_view_clean.proposals_title = choice.proposals_title").df()

        proposal_id=propid.iloc[0,0]

        row_data = db.query("select * from dao_governance_view_clean join choice on dao_governance_view_clean.proposals_title = choice.proposals_title").df()


        vote_tracker = snapshot.Query.votes(
            orderBy='created',
            orderDirection='desc',
            first=10000,
            where=[
                snapshot.Vote.proposal == proposal_id
            ]
        )

        voting_snapshots_list = sg.query_df([
            vote_tracker.id,
            vote_tracker.voter,
            vote_tracker.created,
            vote_tracker.choice,
            vote_tracker.vp
        ])


        #generate a list of choices made per voter
        options = dao_governance_view_clean
        options.drop(options.columns[[0, 1, 2,3,4,5]], axis=1, inplace=True)

        choice_list = db.query("select distinct votes_voter, votes_choice, votes_created from voting_snapshots_list order by votes_created desc").df()


        # add an empty column for the choice text to choice_list
        choice_list.insert(2, 'vote_text', '')

        # now we add the actual body, row by row,  using the vote choice number as the lookup index in dao_governance_view_clean (accounting for the first 6 columns

        shape = choice_list.shape
        number_of_voters = shape[0]-1

        st.write('total voters:', number_of_voters)

        z = 0
        while z<=number_of_voters:
            choice_val = choice_list.iloc[z,1]
            position = 6+ choice_val
            choice_text = row_data.iloc[0,position]

            choice_list.at[z,'vote_text']=choice_text
            z=z+1


        choice_table = db.query("select distinct votes_voter,votes_choice,vote_text from choice_list").df()

        voting_snapshots_list = voting_snapshots_list.merge(choice_list, left_on=['votes_voter'], right_on=['votes_voter'], how='left')

        voting_snapshots_list.rename(columns={'votes_created_x': 'votes_created', 'votes_choice_x': 'votes_choice'}, inplace=True)

        voting_snapshots_list.drop(['votes_created_y','votes_choice_y'], axis=1)


        #st.write('Sample vote records:', voting_snapshots_list)

        @st.cache
        def convert_df(df):
            return df.to_csv().encode('utf-8')


        crunch_data = db.query("select " 
                                   "votes_voter "
                                   ",votes_created"
                                   ",to_timestamp(votes_created) vote_time"
                                   ",votes_choice"
                                   ",votes_vp" 
                                   ",vote_text" 
                                   ",sum(votes_vp) over (order by votes_vp desc, votes_created asc) as cumulative_vp"
                                   ",sum(votes_vp) over (order by votes_vp desc, votes_created asc rows between unbounded preceding and unbounded following) as total_vp"
                                   ",(votes_vp::decimal/sum(votes_vp::decimal) over (order by votes_vp desc, votes_created asc , votes_created asc rows between unbounded preceding and unbounded following)) as percentage_of_total_vp "
                                   ",((sum(votes_vp) over (order by votes_vp desc, votes_created asc))::decimal/sum(votes_vp::decimal) over (order by votes_vp desc rows between unbounded preceding and unbounded following)) as cum_percentage_of_total_vp "
                               ",round((sum(votes_vp) over (order by votes_vp desc, votes_created asc))::decimal/sum(votes_vp::decimal) over (order by votes_vp desc rows between unbounded preceding and unbounded following)) as cum_percentange_of_total_vp_stepped "
                                   ",row_number() over (order by votes_vp desc, votes_created asc) as proposal_voter_rank "
                                   ",count(votes_voter) over (order by votes_vp, votes_created asc rows between unbounded preceding and unbounded following) total_voters "
                                   ",(count(*) over (order by votes_vp desc, votes_created asc))::decimal/(count(*) over (order by votes_vp rows between unbounded preceding and unbounded following))::decimal percentage_voters_counted "
                                   ",round(100*(count(*) over (order by votes_vp desc, votes_created asc))::decimal/(count(*) over (order by votes_vp rows between unbounded preceding and unbounded following)))::decimal percentage_voters_counted_stepped "
                               
                               "from "
                               "    voting_snapshots_list  "
                               ""
                               "Group by "
                               "    votes_voter"
                               "    ,votes_choice"
                               "    , votes_vp "
                               "    , votes_created "  
                               "    , vote_text "
                               ""
                               "Order by "
                               "    votes_vp desc "
                               "    , votes_created asc"
                               "").df()
        crunch_data.insert(0, 'DAO', spacename)

        crunch_data.head(n=10)




        crunch_data.head(n=10)

        st.write('Sample voting records',crunch_data)


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

        st.write('Sample Aggregate data')

        fig = plt.figure(figsize=(20, 8))

        plt.rc("figure", figsize=(40, 20))
        sns.set_style("whitegrid")
        plt.rc("font", size=18)
        data_means = crunch_data.groupby("percentage_voters_counted_stepped")[
            "cum_percentage_of_total_vp", "percentage_voters_counted"].agg("mean").reset_index()
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

        voters = db.query("select count(distinct votes_voter) from voting_snapshots_list").df()
        voters = voters.iloc[0, 0]

        #st.write(Voters)
        st.write('### It took ', p50display, '% out of',voters ,' voters to accumulate half of the voting power in "',choiceOG, '".')

        st.write('The chart below describes all proposals in', spacename,
                 '.The orange markers represent what percentage of the population it takes to reach a given percentage of voting power.')

        # sns.lineplot(data=crunch_data, y="cum_percentage_of_total_vp",x="percentage_voters_counted_stepped", hue="Proposal",zorder=-3).set(title=plot_title,xlabel='% of voters',ylabel='% of voting power')#, legend=False)
        ax = sns.lineplot(data=crunch_data, y="cum_percentage_of_total_vp", x="percentage_voters_counted_stepped").set(
            title=plot_title, xlabel='% of voters', ylabel='% of voting power')
        st.pyplot(fig)

        chart_data=db.query("select vote_text, sum(percentage_of_total_vp) as percentage_of_total_vp from crunch_data group by 1").df()

        st.write(chart_data)

        fig2 = plt.figure(figsize=(10, 4))

        chart = sns.barplot(data=chart_data, y ="percentage_of_total_vp", x="vote_text", hue= "vote_text"  ).set(
            title=('Results: '+choiceOG), xlabel='Choice', ylabel='% of voting power')
        st.pyplot(fig2)

        #$st.bar_chart(data=chart_data, use_container_width=True)

        #st.altair_chart(chart_data, use_container_width=False).mark_arc()


        st.markdown(
            '<p class="bigger-font">All done. Enjoy! Feel free to enter another space name, or choose another snapshot from the drop-down menu, to pull more data.</p>',
            unsafe_allow_html=True)
        # The chart above shows what % of all possible votes has been cast (Y axis) as each incremental percent of the voting population casts their vote (X axis). Each line is a Proposal and has a unique color, so that a dot on each percent point represents what % of total voting power was accumulated by that group. The color represents which vote was cast.
        # The Orange X shows the average % of power accumulated across all elections.