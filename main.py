from flask import Flask, render_template
from sunday_school.league import SundaySchool, Team
from leeger.league_loader import SleeperLeagueLoader
from leeger.model.league import League, Year
from leeger.calculator.year_calculator import (
    GameOutcomeYearCalculator,
    PointsScoredYearCalculator,
    SingleScoreYearCalculator,
    ScoringShareYearCalculator,
    ScoringStandardDeviationYearCalculator,
    AWALYearCalculator,
    PlusMinusYearCalculator,
)
from leeger.model.stat.YearStatSheet import YearStatSheet
from leeger.util.stat_sheet import yearStatSheet
from sleeper.api import LeagueAPIClient
from sleeper.enum import Sport
from sleeper.model import (
    League,
    Roster,
    User,
    Matchup,
    PlayoffMatchup,
    Transaction,
    TradedPick,
    SportState,
    LeagueSettings,
)
import pandas as pd
import numpy as np
from decimal import *

import base64
from io import BytesIO
from matplotlib.figure import Figure

import json
import plotly
import plotly.express as px

from pprint import pprint as pp

app = Flask(__name__)

# pd.options.display.float_format = '{:.2f}'.format

sleeperLeagueLoader = SleeperLeagueLoader("917936834150486016", [2021, 2022, 2023])
league = sleeperLeagueLoader.loadLeague()

y2021 = league.years[0]
y2022 = league.years[1]
y2023 = league.years[2]

# pp(x)
def get_team_map(year):
    team_map = {}
    for team in year.teams:
        team_map[team.id] = team.name
    return team_map


def nicknames(d, year):
    nd = {}
    for x in d:
        if isinstance(d[x], Decimal) or isinstance(d[x], float):
            # nd[team_map.get(x)] = d[x].quantize(Decimal('.01'), rounding=ROUND_UP)
            nd[get_team_map(year).get(x)] = float(d[x])
        else:
            nd[get_team_map(year).get(x)] = int(d[x])
    return nd


def nested_nicknames(d, year):
    nd = {}
    for x in d:
        nd[get_team_map(year).get(x)] = {}
        for s in d.get(x):
            if isinstance(d[x][s], Decimal) or isinstance(d[x][s], float):
                # nd[team_map.get(x)] = d[x].quantize(Decimal('.01'), rounding=ROUND_UP)
                nd[get_team_map(year).get(x)][s] = float(d[x][s])
            else:
                nd[get_team_map(year).get(x)][s] = int(d[x][s])
    return nd


def get_year_stats_with_nicknames(year):
    yearstats = yearStatSheet(year, onlyRegularSeason=True, weekNumberEnd=len(year.weeks) - 1).__dict__
    ys_with_nn = {}
    for stat, d in yearstats.items():
        ys_with_nn[stat] = nicknames(d, year)
    return ys_with_nn


def get_weekly_pr_df(year):
    new_ys_with_nn = {}
    for i in range(1, len(year.weeks)):
        temp_yearstats = yearStatSheet(
            year, onlyRegularSeason=True, weekNumberEnd=i
        ).__dict__
        new_ys_with_nn[i] = {}
        for stat, d in temp_yearstats.items():
            new_ys_with_nn[i][stat] = nicknames(d, year)
    # pp(new_ys_with_nn)
    w_pr = {}
    for i in range(1, len(year.weeks)):
        w_pr[i] = {}
        for team in year.teams:
            w_pr[i][team.name] = {}
    final = pd.DataFrame()
    # final.set_index([team.name for team in x.teams])
    for i in range(1, len(year.weeks)):
        for stat, d in new_ys_with_nn.get(i).items():
            if stat in set(
                [
                    "wal",
                    "awal",
                    "smartWins",
                    "pointsScored",
                    "scoringStandardDeviation",
                    "overallWins",
                ]
            ):
                # print(d)
                for team in d:
                    w_pr[i][team][stat] = d.get(team)
        # pp(w_pr)
        test_pwr = pd.DataFrame.from_dict(w_pr[i], orient="index")
        # pp(test_pwr)
        test_pwr["wal_rank"] = test_pwr["wal"].rank(ascending=False)
        test_pwr["awal_rank"] = test_pwr["awal"].rank(ascending=False)
        test_pwr["smartWins_rank"] = test_pwr["smartWins"].rank(ascending=False)
        test_pwr["pointsScored_rank"] = test_pwr["pointsScored"].rank(ascending=False)
        test_pwr["scoringStandardDeviation_rank"] = test_pwr[
            "scoringStandardDeviation"
        ].rank()
        test_pwr["overallWins_rank"] = test_pwr["overallWins"].rank(ascending=False)
        test_pwr[f"Power Rank {i}"] = test_pwr.apply(
            lambda row: (
                (3 * row.wal_rank)
                + row.awal_rank
                + row.smartWins_rank
                + row.pointsScored_rank
                + row.scoringStandardDeviation_rank
                + row.overallWins_rank
            )
            / 8,
            axis=1,
        )
        test_pwr[f"Relative Power Rank {i}"] = test_pwr[f"Power Rank {i}"].rank()
        # pp(test_pwr)
        final[f"Relative Power Rank {i}"] = test_pwr[f"Relative Power Rank {i}"]
    return final


def get_all_stats_table(year):
    df = pd.DataFrame(
        get_year_stats_with_nicknames(year),
        columns=get_year_stats_with_nicknames(year).keys(),
    )
    html = (
        df.style.format(lambda x: f"{x:,.3f}" if isinstance(x, float) else f"{x}")
        .set_table_attributes('class="w-auto table allstats"')
        .set_table_styles([dict(selector="th", props=[("text-align", "center")])])
        .background_gradient(cmap="RdYlGn")
        .to_html()
    )
    return html


def get_ind_stats_tables(year):
    tables = []
    for stat, d in get_year_stats_with_nicknames(year).items():
        df = pd.DataFrame.from_dict(d, orient="index", columns=[stat])
        styled = (
            df.style.format(lambda x: f"{x:,.3f}" if isinstance(x, float) else f"{x}")
            .set_table_attributes('class="table"')
            .set_table_styles([dict(selector="th", props=[("text-align", "center")])])
            .background_gradient(cmap="RdYlGn")
            .to_html()
        )
        tables.append(styled)
    return tables


def get_pr(year):
    pr = {}
    for team in year.teams:
        pr[team.name] = {}
    for stat, d in get_year_stats_with_nicknames(year).items():
        if stat in set(
            [
                "wal",
                "awal",
                "smartWins",
                "pointsScored",
                "scoringStandardDeviation",
                "overallWins",
            ]
        ):
            for team in d:
                # print(team)
                pr[team][stat] = d.get(team)
    pwr = pd.DataFrame.from_dict(pr, orient="index")
    pwr["wal_rank"] = pwr["wal"].rank(ascending=False)
    pwr["awal_rank"] = pwr["awal"].rank(ascending=False)
    pwr["smartWins_rank"] = pwr["smartWins"].rank(ascending=False)
    pwr["pointsScored_rank"] = pwr["pointsScored"].rank(ascending=False)
    pwr["scoringStandardDeviation_rank"] = pwr["scoringStandardDeviation"].rank()
    pwr["overallWins_rank"] = pwr["overallWins"].rank(ascending=False)
    pwr["Power Rank"] = pwr.apply(
        lambda row: (
            (3 * row.wal_rank)
            + row.awal_rank
            + row.smartWins_rank
            + row.pointsScored_rank
            + row.scoringStandardDeviation_rank
            + row.overallWins_rank
        )
        / 8,
        axis=1,
    )
    pwr_styled = (
        pwr.style.format(lambda x: f"{x:,.3f}" if isinstance(x, float) else f"{x}")
        .set_table_attributes('class="table"')
        .set_table_styles([dict(selector="th", props=[("text-align", "center")])])
        .hide_columns(
            [
                "wal_rank",
                "awal_rank",
                "smartWins_rank",
                "pointsScored_rank",
                "scoringStandardDeviation_rank",
                "overallWins_rank",
            ]
        )
        .background_gradient(cmap="RdYlGn")
        .to_html()
    )
    return pwr_styled


def plotly_bar(ss):
    df = pd.DataFrame.from_dict(nested_nicknames(ss, y2023), orient="index")
    fig = px.bar(df, x=df.index, y=[c for c in df.columns])
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON


def plotly_line(df):
    pd.options.plotting.backend = "plotly"
    fig = df.T.plot(markers=True)
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return graphJSON


@app.route("/")
def index():
    l = SundaySchool()
    h = l.get_roster_season_projections()
    return render_template(
        "index.html",
        league=h,
        tables=get_ind_stats_tables(y2023),
        full_table=get_all_stats_table(y2023),
        power=get_pr(y2023),
        pr_chart=plotly_line(get_weekly_pr_df(y2023)),
    )


@app.route("/2021")
def get_2021():
    return render_template(
        "2021.html",
        tables=get_ind_stats_tables(y2021),
        full_table=get_all_stats_table(y2021),
        power=get_pr(y2021),
        pr_chart=plotly_line(get_weekly_pr_df(y2021)),
    )


@app.route("/2022")
def get_2022():
    return render_template(
        "2022.html",
        tables=get_ind_stats_tables(y2022),
        full_table=get_all_stats_table(y2022),
        power=get_pr(y2022),
        pr_chart=plotly_line(get_weekly_pr_df(y2022)),
    )


@app.route("/team_breakdowns")
def team_breakdowns():
    return render_template("team_breakdowns.html", league=SundaySchool())


@app.route("/scoring_share")
def scoring_share():
    ss = PointsScoredYearCalculator.getPointsScoredByPosition(
        y2023, onlyRegularSeason=True
    )
    return render_template("scoring_share.html", graphJSON=plotly_bar(ss))
