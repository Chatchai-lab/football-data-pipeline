"""Lasttest der Matchlytics-API mit Locust.

Ein simulierter Nutzer verhaelt sich wie das Dashboard: Er holt zuerst Saisons und Teams und ruft danach
die Gold-Endpunkte auf, mit kurzen Denkpausen dazwischen. Die Gewichte (task) sagen, wie oft ein Endpunkt
im Vergleich zu den anderen aufgerufen wird.

Das Dashboard selbst wird nicht getestet: Streamlit arbeitet mit WebSockets, die ein reiner HTTP-Test
nicht abbildet. Gemessen wird hier nur die API.
"""
import random

from locust import HttpUser, between, task


class DashboardUser(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self):
        seasons = self.client.get("/seasons", name="/seasons").json()
        self.season = seasons[0] if seasons else "2025"
        self.teams = self.client.get("/teams", params={"season": self.season}, name="/teams").json()

    def team_filter(self) -> list[tuple[str, str]]:
        """Zwei bis vier zufaellige Teams als ?team=A&team=B, wie im Dashboard-Filter."""
        if not self.teams:
            return []
        chosen = random.sample(self.teams, k=min(len(self.teams), random.randint(2, 4)))
        return [("team", name) for name in chosen]

    @task(5)
    def standings(self):
        self.client.get("/standings", params={"season": self.season}, name="/standings")

    @task(3)
    def ratings(self):
        self.client.get("/ratings", params={"season": self.season}, name="/ratings")

    @task(3)
    def matches(self):
        self.client.get("/matches", params={"season": self.season}, name="/matches")

    @task(2)
    def season_trend(self):
        params = [("season", self.season)] + self.team_filter()
        self.client.get("/season-trend", params=params, name="/season-trend")

    @task(2)
    def team_form(self):
        params = [("season", self.season)] + self.team_filter()
        self.client.get("/team-form", params=params, name="/team-form")

    @task(2)
    def home_away(self):
        self.client.get("/home-away", params={"season": self.season}, name="/home-away")

    @task(1)
    def highlights(self):
        self.client.get("/highlights", params={"season": self.season}, name="/highlights")
