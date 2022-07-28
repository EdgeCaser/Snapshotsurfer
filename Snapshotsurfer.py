##this script pulls data from a DAO within snapshot.org and shows its voting data

from datetime import datetime
from datetime import date
from subgrounds.subgraph import SyntheticField, FieldPath
from subgrounds.subgrounds import Subgrounds
import math as mt
import pandas as pd
import  os as os
import duckdb as db
import seaborn as sns
import matplotlib.pyplot as plt
import streamlit as st

spacename = st.text_input('Where to pull from?',help='Which space, eg: curve.eth')


if len(spacename)>1:

    file = st.text_input('Where to write to?',placeholder= None,help='Where in your HDD to save ouput',type="password")

    if len(file) > 1:

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
            proposals.scores,
            proposals.scores_total
        ])

        proposals_choices = sg.query(proposals.choices)

        proposals_choices = pd.DataFrame(proposals_choices)

        olympus_governance_view = pd.concat([proposals_snapshots,proposals_choices], axis=1)

        ##let's view the output just to make sure
        olympus_governance_view.head(5)

        #let's remove duplicate rows the easy way, and add the name of the DAO to the table
        olympus_governance_view_clean = olympus_governance_view.copy(deep=True)
        olympus_governance_view_clean.insert(0, 'DAO', spacename)
        olympus_governance_view_clean.head(10)

        path =file+'/'+spacename+'_proposals_table_'+str(date.today().strftime("%b-%d-%Y"))+'_'+str(len(olympus_governance_view_clean))+'_proposals.csv'
        olympus_governance_view_clean.to_csv(path, index = False)

        total_proposals = len(olympus_governance_view_clean)
        #total_proposals

        proposal_id = olympus_governance_view_clean.iloc[0,2]
        #proposal_id

        vote_tracker = snapshot.Query.votes(
        orderBy = 'created',
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

        st.write('sample output: voting snapshots',voting_snapshots_list.head(10))


        st.write('Pulling vote records...')

        mybar = st.progress(0)
        x=0
        while x <total_proposals:
            proposal_id = olympus_governance_view_clean.iloc[x,2]

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
            if progress%5==0:
                st.write ("Progress",progress,"%")

        print(len(voting_snapshots_list),' records')

        #spit out the file
        path =file+'/'+spacename+'_voting_snapshots_list_'+str(date.today().strftime("%b-%d-%Y"))+'_'+str(len(olympus_governance_view_clean))+'.csv'
        voting_snapshots_list.to_csv(path, index = False)
        st.write('Proposals list Saved')


        #I join these two tables to create my charts as it makes life easier. We are going to build the charts here now, so here we go
        governance_data = pd.merge(voting_snapshots_list, olympus_governance_view_clean, how='inner', left_on='Proposal', right_on='proposals_id')
        del governance_data["proposals_body"]
        st.write(governance_data.head(10))

        #Spit out the file, but save it in its own folder for easy access
        final_file = file+'\\'+'final'
        final_raw_file = final_file
        os.makedirs(final_raw_file, exist_ok=True)
        final_path =file+'\\'+spacename+'governance_data_'+str(date.today().strftime("%b-%d-%Y"))+'_'+str(len(governance_data))+'.csv'
        governance_data.to_csv(final_path, index = False)
        st.write('votes data Saved')

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
                               ",round((sum(votes_vp) over (Partition by Proposal  order by votes_vp desc, votes_created asc))::decimal/sum(votes_vp::decimal) over (Partition by Proposal)) as cum_percentange_of_total_vp_stepped "
                                   ",row_number() over (Partition by Proposal order by votes_vp desc, votes_created asc) as proposal_voter_rank "
                                   ",count(votes_voter) over (Partition by Proposal  order by votes_vp desc, votes_created asc) voters_counted "
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
                               "    , votes_created asc"
                               "").df()
        crunch_data.insert(0, 'DAO', spacename)
        crunch_data.head(n=10)

        ##spit out the file!
        crunch_data_path =final_file+'\\'+spacename+'_crunch_data_path'+str(date.today().strftime("%b-%d-%Y"))+'_'+str(len(crunch_data))+'.csv'
        crunch_data.to_csv(crunch_data_path, index = False)
        st.write('Aggregate data saved')

        fig = plt.figure(figsize=(20, 8))

        plt.rc("figure", figsize=(40, 20))
        sns.set_style("whitegrid")
        plt.rc("font", size=18)
        data_means = crunch_data.groupby("percentage_voters_counted_stepped")["cum_percentage_of_total_vp"].agg("mean").reset_index()
        ##print(data_means)
        plot_title = spacename + ' snapshots % of vote along population'


        #sns.lineplot(data=crunch_data, y="cum_percentage_of_total_vp",x="percentage_voters_counted_stepped", hue="Proposal",zorder=-3).set(title=plot_title,xlabel='% of voters',ylabel='% of voting power')#, legend=False)
        ax = sns.scatterplot(data=crunch_data, y="cum_percentage_of_total_vp", x="percentage_voters_counted_stepped").set(title=plot_title, xlabel='% of voters', ylabel='% of voting power')
        chart = sns.scatterplot(data=data_means, x="percentage_voters_counted_stepped", y="cum_percentage_of_total_vp", zorder=3, s=400, marker='X', color='orange')
        # and save the chart file, too
        plt.savefig(final_file+'\\'+spacename+' vote power distribution.png', dpi=50)
        st.write('Chart Saved')
        #st.pyplot(sns.scatterplot(data=data_means, x="percentage_voters_counted_stepped", y="cum_percentage_of_total_vp", zorder=3, s=600, marker='X', color='orange'))
        st.pyplot(fig)

        p50 = db.query("select percentage_voters_counted "
                       "from crunch_data  where cum_percentange_of_total_vp_stepped>=0.5 "
                       "order by cum_percentange_of_total_vp_stepped asc limit 1").df()

        p50display = round((100 * p50), 2)
        p50display = p50display.iloc[0,0]
        st.write('On average, a proposal at ', spacename, 'takes ',p50display,'% of the voting population.' )

        st.write('all done. Enjoy!')
        # The chart above shows what % of all possible votes has been cast (Y axis) as each incremental percent of the voting population casts their vote (X axis). Each line is a Proposal and has a unique color, so that a dot on each percent point represents what % of total voting power was accumulated by that group. The color represents which vote was cast.
        # The Orange X shows the average % of power accumulated across all elections.

