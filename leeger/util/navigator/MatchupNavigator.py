from typing import Optional

from leeger.model.league.Matchup import Matchup


class MatchupNavigator:
    """
    Used to navigate the Matchup model.
    """

    @staticmethod
    def getTeamIdOfMatchupWinner(matchup: Matchup, **kwargs) -> Optional[str]:
        """
        Returns the team ID of the team that won the matchup or None if the matchup was a tie.
        """
        winningTeamId = None
        # team A won
        if (matchup.teamAScore > matchup.teamBScore) or (
                matchup.teamAScore == matchup.teamBScore and matchup.teamAHasTiebreaker):
            winningTeamId = matchup.teamAId
        # team B won
        elif (matchup.teamBScore > matchup.teamAScore) or (
                matchup.teamAScore == matchup.teamBScore and matchup.teamBHasTiebreaker):
            winningTeamId = matchup.teamBId
        return winningTeamId
