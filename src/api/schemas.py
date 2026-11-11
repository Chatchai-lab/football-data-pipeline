from pydantic import BaseModel
from datetime import datetime


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    database: str

class StatusResponse(BaseModel):
    last_update: datetime | None
    match_count: int
    team_count: int
    season_count: int

class StandingRow(BaseModel):
    team_name: str
    tla: str | None
    matches_played: int
    total_points: int
    total_goals_for: int
    total_goals_against: int
    goal_diff: int
    points_per_match: float


class SeasonTrendRow(BaseModel):
    team_name: str
    matchday: int
    cumulative_points: int


class TeamFormRow(BaseModel):
    team_name: str
    tla: str | None
    form_trend: str



class HomeAwayRow(BaseModel):
    team_name: str
    home_matches: int
    home_points: int
    home_goals_for: int
    home_goals_against: int
    home_wins: int
    home_ppg: float
    away_matches: int
    away_points: int
    away_goals_for: int
    away_goals_against: int
    away_wins: int
    away_ppg: float
    total_points: int


class RatingRow(BaseModel):
    team_name: str
    total_games: int
    goals_per_game: float
    goals_conceded_per_game: float
    clean_sheets: int


class MatchRow(BaseModel):
    matchday: int | None
    match_timestamp: datetime | None
    home_team_name: str
    away_team_name: str
    goals_home: int | None
    goals_away: int | None
    status: str


class LeagueLeader(BaseModel):
    team_name: str
    total_points: int


class HomeKing(BaseModel):
    team_name: str
    home_points: int


class AttackKing(BaseModel):
    team_name: str
    goals_per_game: float


class FormKing(BaseModel):
    team_name: str
    form_trend: str


class TeamMeta(BaseModel):
    team_name: str
    tla: str | None
    crest_url: str | None


class HighlightsResponse(BaseModel):
    leader: LeagueLeader | None
    home_king: HomeKing | None
    attack_king: AttackKing | None
    form_king: FormKing | None
