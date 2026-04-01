"""
Unit-Tests für die Form-Trend-Parsing-Logik (reine Logik, keine DB nötig).
Testet parse_form_trend aus der Team-Analyse-Seite.
"""

import pytest
import pandas as pd


# --- Funktion direkt hier importieren wäre ideal, aber sie lebt in einer
#     Streamlit-Page. Daher extrahieren wir die reine Logik zum Testen. ---
def parse_form_trend(form_str: str) -> list[str]:
    """Kopie der Logik aus 02_Team_Analyse.py für isoliertes Testen."""
    if not form_str or pd.isna(form_str):
        return []
    tokens = [t.strip().upper() for t in str(form_str).split("-") if t.strip()]
    return [t for t in tokens if t in {"W", "D", "L"}]


# ─── Normale Fälle ───

class TestParseFormTrend:
    def test_standard_form_string(self):
        """Standardformat: 'W-D-L-W-W' → ['W', 'D', 'L', 'W', 'W']"""
        result = parse_form_trend("W-D-L-W-W")
        assert result == ["W", "D", "L", "W", "W"]

    def test_all_wins(self):
        result = parse_form_trend("W-W-W-W-W")
        assert result == ["W", "W", "W", "W", "W"]

    def test_all_losses(self):
        result = parse_form_trend("L-L-L-L-L")
        assert result == ["L", "L", "L", "L", "L"]

    def test_all_draws(self):
        result = parse_form_trend("D-D-D-D-D")
        assert result == ["D", "D", "D", "D", "D"]

    def test_mixed_form(self):
        result = parse_form_trend("L-W-D-W-L")
        assert result == ["L", "W", "D", "W", "L"]

    def test_single_result(self):
        result = parse_form_trend("W")
        assert result == ["W"]


# ─── Edge Cases ───

class TestParseFormTrendEdgeCases:
    def test_empty_string(self):
        assert parse_form_trend("") == []

    def test_none_value(self):
        assert parse_form_trend(None) == []

    def test_nan_value(self):
        assert parse_form_trend(float("nan")) == []

    def test_numpy_nan(self):
        import numpy as np
        assert parse_form_trend(np.nan) == []

    def test_lowercase_input(self):
        """Kleinbuchstaben sollten erkannt werden."""
        result = parse_form_trend("w-d-l")
        assert result == ["W", "D", "L"]

    def test_whitespace_around_tokens(self):
        """Leerzeichen um Tokens sollten ignoriert werden."""
        result = parse_form_trend(" W - D - L ")
        assert result == ["W", "D", "L"]

    def test_invalid_tokens_filtered(self):
        """Ungültige Zeichen (X, Z) sollten herausgefiltert werden."""
        result = parse_form_trend("W-X-D-Z-L")
        assert result == ["W", "D", "L"]

    def test_only_invalid_tokens(self):
        result = parse_form_trend("X-Y-Z")
        assert result == []


# ─── Rückgabetyp ───

class TestParseFormTrendTypes:
    def test_returns_list(self):
        assert isinstance(parse_form_trend("W-D-L"), list)

    def test_elements_are_strings(self):
        result = parse_form_trend("W-D-L")
        assert all(isinstance(r, str) for r in result)

    def test_length_matches_valid_tokens(self):
        result = parse_form_trend("W-D-L-W-L")
        assert len(result) == 5
