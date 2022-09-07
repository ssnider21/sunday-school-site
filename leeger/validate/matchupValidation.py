from leeger.enum.MatchupType import MatchupType
from leeger.exception.InvalidMatchupFormatException import InvalidMatchupFormatException
from leeger.model.league.Matchup import Matchup


def runAllChecks(matchup: Matchup) -> None:
    """
    Runs all checks on the given Matchup.
    """
    checkAllTypes(matchup)
    checkForIllegalMatchupOutcomes(matchup)


def checkAllTypes(matchup: Matchup) -> None:
    """
    Checks all types that are within the Matchup object.
    """
    if type(matchup.teamAId) != str:
        raise InvalidMatchupFormatException("teamAId must be type 'str'.")
    if type(matchup.teamBId) != str:
        raise InvalidMatchupFormatException("teamBId must be type 'str'.")
    if type(matchup.teamAScore) != float and type(matchup.teamAScore) != int:
        raise InvalidMatchupFormatException("teamAScore must be type 'float' or 'int'.")
    if type(matchup.teamBScore) != float and type(matchup.teamBScore) != int:
        raise InvalidMatchupFormatException("teamBScore must be type 'float' or 'int'.")
    if type(matchup.teamAHasTiebreaker) != bool:
        raise InvalidMatchupFormatException("teamAHasTiebreaker must be type 'bool'.")
    if type(matchup.teamBHasTiebreaker) != bool:
        raise InvalidMatchupFormatException("teamBHasTiebreaker must be type 'bool'.")
    if type(matchup.matchupType) != MatchupType:
        raise InvalidMatchupFormatException("matchupType must be type 'MatchupType'.")


def checkForIllegalMatchupOutcomes(matchup: Matchup) -> None:
    """
    Checks that no playoff/championship matchup ends in a tie.
    """
    from leeger.util.navigator.MatchupNavigator import MatchupNavigator
    if matchup.matchupType in [MatchupType.PLAYOFF,
                               MatchupType.CHAMPIONSHIP] and MatchupNavigator.getTeamIdOfMatchupWinner(
        matchup, validate=False) is None:
        raise InvalidMatchupFormatException("Playoff and Championship matchups cannot end in a tie.")
