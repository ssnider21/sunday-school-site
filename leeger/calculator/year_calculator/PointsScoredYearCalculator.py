from pprint import pp
from typing import Optional

from leeger.calculator.parent.YearCalculator import YearCalculator
from leeger.decorator.validators import validateYear
from leeger.model.league.Year import Year
from leeger.util.Deci import Deci
from leeger.util.navigator.YearNavigator import YearNavigator

import requests
import json

with open("sunday_school/players.json") as f:
    PLAYERS = json.load(f)

class PointsScoredYearCalculator(YearCalculator):
    """
    Used to calculate all points scored.
    """

    @classmethod
    @validateYear
    def getPointsScored(cls, year: Year, **kwargs) -> dict[str, Optional[Deci]]:
        """
        Returns the number of Points Scored for each team in the given Year.
        Returns None for a Team if they have no games played in the range.

        Example response:
            {
            "someTeamId": Deci("1009.7"),
            "someOtherTeamId": Deci("1412.2"),
            "yetAnotherTeamId": Deci("1227.1"),
            ...
            }
        """
        filters = cls._getYearFilters(year, **kwargs)

        teamIdAndPointsScored = dict()
        for teamId in YearNavigator.getAllTeamIds(year):
            teamIdAndPointsScored[teamId] = Deci(0)

        for i in range(filters.weekNumberStart - 1, filters.weekNumberEnd):
            week = year.weeks[i]
            for matchup in week.matchups:
                if matchup.matchupType in filters.includeMatchupTypes:
                    teamIdAndPointsScored[matchup.teamAId] += Deci(matchup.teamAScore)
                    teamIdAndPointsScored[matchup.teamBId] += Deci(matchup.teamBScore)

        cls._setToNoneIfNoGamesPlayed(teamIdAndPointsScored, year, filters, **kwargs)
        return teamIdAndPointsScored

    @classmethod
    @validateYear
    def getPointsScoredByPosition(cls, year: Year, **kwargs) -> dict[str, dict[str, Optional[Deci]]]:
        filters = cls._getYearFilters(year, **kwargs)

        teamIdAndPointsScored = dict()
        for teamId in YearNavigator.getAllTeamIds(year):
            teamIdAndPointsScored[teamId] = dict()

        for i in range(filters.weekNumberStart - 1, filters.weekNumberEnd):
            week = year.weeks[i]
            week_stats_res = requests.get(f"https://api.sleeper.com/stats/nfl/{year.yearNumber}/{week.weekNumber}?season_type=regular&position[]=DEF&position[]=K&position[]=QB&position[]=RB&position[]=TE&position[]=WR&order_by=pts_ppr").json()
            week_stats = {}
            for player in week_stats_res:
                week_stats[player.get("player_id")] = player
            for matchup in week.matchups:
                if matchup.matchupType in filters.includeMatchupTypes:
                    for playerA, playerB in zip(matchup.teamAStarters, matchup.teamBStarters):
                        try:
                            playerAPos = PLAYERS.get(playerA).get("position")
                        except:
                            print(playerA)
                            print(matchup)
                        try:
                            playerBPos = PLAYERS.get(playerB).get("position")
                        except:
                            print(playerB)
                            print(matchup)
                        # playerAPts = requests.get(f"https://api.sleeper.com/stats/nfl/player/{playerA}?season_type=regular&season={year.yearNumber}&week={week.weekNumber}").json().get("stats").get("pts_ppr") or 0
                        # playerBPts = requests.get(f"https://api.sleeper.com/stats/nfl/player/{playerB}?season_type=regular&season={year.yearNumber}&week={week.weekNumber}").json().get("stats").get("pts_ppr") or 0
                        try:
                            playerAPts = week_stats.get(playerA).get("stats").get("pts_ppr") or 0
                        except Exception:
                            playerAPts = 0
                        try:
                            playerBPts = week_stats.get(playerB).get("stats").get("pts_ppr") or 0
                        except Exception:
                            playerBPts = 0
                        # playerAPts = week_stats.get(playerA).get("stats").get("pts_ppr") or 0
                        # playerBPts = week_stats.get(playerB).get("stats").get("pts_ppr") or 0
                        if playerAPos not in teamIdAndPointsScored[matchup.teamAId]:
                            teamIdAndPointsScored[matchup.teamAId][playerAPos] = Deci(playerAPts)
                        else:
                            teamIdAndPointsScored[matchup.teamAId][playerAPos] += Deci(playerAPts)
                        if playerBPos not in teamIdAndPointsScored[matchup.teamBId]:
                            teamIdAndPointsScored[matchup.teamBId][playerBPos] = Deci(playerBPts)
                        else:
                            teamIdAndPointsScored[matchup.teamBId][playerBPos] += Deci(playerBPts)
        cls._setToNoneIfNoGamesPlayed(teamIdAndPointsScored, year, filters, **kwargs)
        return teamIdAndPointsScored

    @classmethod
    @validateYear
    def getPointsScoredPerGame(cls, year: Year, **kwargs) -> dict[str, Optional[Deci]]:
        """
        Returns the number of Points Scored per game for each team in the given Year.
        Returns None for a Team if they have no games played in the range.

        Example response:
            {
            "someTeamId": Deci("100.7"),
            "someOtherTeamId": Deci("141.2"),
            "yetAnotherTeamId": Deci("122.1"),
            ...
            }
        """

        teamIdAndPointsScored = cls.getPointsScored(year, **kwargs)
        teamIdAndNumberOfGamesPlayed = YearNavigator.getNumberOfGamesPlayed(year,
                                                                            cls._getYearFilters(year,
                                                                                                **kwargs))

        teamIdAndPointsScoredPerGame = dict()
        allTeamIds = YearNavigator.getAllTeamIds(year)
        for teamId in allTeamIds:
            # to avoid division by zero, we'll just set the points scored per game to 0 if the team has no games played
            if teamIdAndNumberOfGamesPlayed[teamId] == 0:
                teamIdAndPointsScoredPerGame[teamId] = None
            else:
                teamIdAndPointsScoredPerGame[teamId] = teamIdAndPointsScored[teamId] / teamIdAndNumberOfGamesPlayed[
                    teamId]

        return teamIdAndPointsScoredPerGame

    @classmethod
    @validateYear
    def getOpponentPointsScored(cls, year: Year, **kwargs) -> dict[str, Optional[Deci]]:
        """
        Returns the number of opponent Points Scored for each team in the given Year.
        Returns None for a Team if they have no games played in the range.

        Example response:
            {
            "someTeamId": Deci("1009.7"),
            "someOtherTeamId": Deci("1412.2"),
            "yetAnotherTeamId": Deci("1227.1"),
            ...
            }
        """
        filters = cls._getYearFilters(year, **kwargs)

        teamIdAndOpponentPointsScored = dict()
        for teamId in YearNavigator.getAllTeamIds(year):
            teamIdAndOpponentPointsScored[teamId] = Deci(0)

        for i in range(filters.weekNumberStart - 1, filters.weekNumberEnd):
            week = year.weeks[i]
            for matchup in week.matchups:
                if matchup.matchupType in filters.includeMatchupTypes:
                    teamIdAndOpponentPointsScored[matchup.teamAId] += Deci(matchup.teamBScore)
                    teamIdAndOpponentPointsScored[matchup.teamBId] += Deci(matchup.teamAScore)

        cls._setToNoneIfNoGamesPlayed(teamIdAndOpponentPointsScored, year, filters, **kwargs)
        return teamIdAndOpponentPointsScored

    @classmethod
    @validateYear
    def getOpponentPointsScoredPerGame(cls, year: Year, **kwargs) -> dict[str, Optional[Deci]]:
        """
        Returns the number of opponent Points Scored per game for each team in the given Year.
        Returns None for a Team if they have no games played in the range.

        Example response:
            {
            "someTeamId": Deci("100.7"),
            "someOtherTeamId": Deci("141.2"),
            "yetAnotherTeamId": Deci("122.1"),
            ...
            }
        """

        teamIdAndOpponentPointsScored = cls.getOpponentPointsScored(year, **kwargs)
        teamIdAndNumberOfGamesPlayed = YearNavigator.getNumberOfGamesPlayed(year,
                                                                            cls._getYearFilters(year,
                                                                                                **kwargs))

        teamIdAndOpponentPointsScoredPerGame = dict()
        allTeamIds = YearNavigator.getAllTeamIds(year)
        for teamId in allTeamIds:
            # to avoid division by zero, we'll just set the opponent points scored per game to 0 if the team has no games played
            if teamIdAndNumberOfGamesPlayed[teamId] == 0:
                teamIdAndOpponentPointsScoredPerGame[teamId] = None
            else:
                teamIdAndOpponentPointsScoredPerGame[teamId] = teamIdAndOpponentPointsScored[teamId] / \
                                                               teamIdAndNumberOfGamesPlayed[teamId]

        return teamIdAndOpponentPointsScoredPerGame
