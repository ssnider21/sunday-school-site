from sleeper_wrapper import League, Stats
import json

import pandas as pd
import random


league = League("854402777273720832")
stats = Stats()
with open("sunday_school/players.json") as f:
    PLAYERS = json.load(f)

injuries = {
    "QB": [.025, 3],
    "RB": [.052, 4],
    "WR": [.045, 3],
    "TE": [.049, 3],
}

class Team:
    def __init__(self, owner_id):
        self.roster = self._get_roster_by_id(owner_id)
        self.player_week_scoring = self.get_player_week_scoring()

    def _get_roster_by_id(self, owner_id):
        all_rosters = league.get_rosters()
        for roster in all_rosters:
            if roster.get("owner_id") == owner_id:
                return roster.get("players")

    def get_player_name(self, player_id):
        return f"{PLAYERS.get(player_id).get('first_name')} {PLAYERS.get(player_id).get('last_name')}"

    def get_player_week_scoring(self):
        week_breakdown = {}
        for player in self.roster:
            week_breakdown[self.get_player_name(player)] = []
            for week in range(1, 15):
                week_stats = stats.get_week_stats("regular", 2022, week)
                week_breakdown[self.get_player_name(player)].append(stats.get_player_week_score(week_stats, player).get("pts_ppr"))
        return week_breakdown


class SundaySchool:
    def __init__(self):
        self.rosters = league.get_rosters()
        self.users = league.get_users()
        self.user_dict = self._get_user_dict(self.users)
        self.nicknames = self._get_team_nicknames()

    def get_player_name(self, player_id):
        return f"{PLAYERS.get(player_id).get('first_name')} {PLAYERS.get(player_id).get('last_name')}"

    def get_player_position(self, player_id):
        return PLAYERS.get(player_id).get("position")

    def _get_team_nicknames(self):
        nickname_dict = {}
        for user in self.user_dict.keys():
            nn = self.user_dict.get(user).get("metadata").get("team_name")
            if nn is not None:
                nickname_dict[user] = nn
            else:
                nickname_dict[user] = self.user_dict.get(user).get("display_name")
        return nickname_dict

    def _get_user_dict(self, users):
        nd = {}
        for item in users:
            nd[item.get("user_id")] = item
        return nd

    def get_roster_season_projections(self):
        combined_total = {}
        projections = stats.get_all_projections(season_type="regular", season=2022)
        for roster in self.rosters:
            owner_id = roster.get("owner_id")
            team_name = self.nicknames.get(owner_id)
            combined_total[team_name] = {"no_injuries": 0, "injuries": 0}
            all_players = roster.get("starters")
            for player in all_players:
                try:
                    proj = projections.get(player).get("pts_ppr")
                    combined_total[team_name]["no_injuries"] += proj
                    pos = self.get_player_position(player)
                except Exception as e:
                    proj = 0
                    combined_total[team_name]["no_injuries"] += proj
                    pos = None
                for i in range(18):
                    if injuries.get(pos) is not None and random.random() < injuries.get(pos)[0]:
                        i += injuries.get(pos)[1]
                        proj -= ((proj/17)*injuries.get(pos)[1])
                combined_total[team_name]["injuries"] += proj
        df = pd.DataFrame.from_dict(combined_total, orient='index')
        df["no_inj_rank"] = df["no_injuries"].rank(ascending=False)
        df["inj_rank"] = df["injuries"].rank(ascending=False)
        df.columns = ["Season Starters Total", "With Simulated Injuries", "Total Rank", "Injuries Rank"]
        df = df[["Season Starters Total", "Total Rank", "With Simulated Injuries", "Injuries Rank"]]

        df_styled =  df.style.format(lambda x: f'{x:,.1f}' if isinstance(x, float) else f'{x}').set_table_attributes('class="table"').set_table_styles([dict(selector='th', props=[('text-align', 'center')])]).background_gradient(cmap='RdYlGn').to_html()

        return df_styled

    def get_roster_season_projections_breakdown(self):
        breakdown_by_player = {}
        projections = stats.get_all_projections(season_type="regular", season=2022)
        for roster in self.rosters:
            owner_id = roster.get("owner_id")
            team_name = self.nicknames.get(owner_id)
            breakdown_by_player[team_name] = {}
            all_players = roster.get("players")
            for player in all_players:
                player_name = self.get_player_name(player)
                breakdown_by_player[team_name][player_name] = projections.get(player).get("pts_ppr")
        return breakdown_by_player