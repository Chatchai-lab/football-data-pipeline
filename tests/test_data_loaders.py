"""Tests für die Daten-Lade-Schicht (data_loaders.py)."""

import pandas as pd
from unittest.mock import patch, MagicMock


def _no_cache(*args, **kwargs):
    """Ersatz für st.cache_data: unterstützt @st.cache_data und @st.cache_data(ttl=...)."""
    if args and callable(args[0]):
        return args[0]
    return lambda f: f


def test_get_team_crests_returns_dict():
    """get_team_crests gibt ein Dict {team_name: crest_url} zurück."""
    fake_data = pd.DataFrame({
        'team_name': ['FC Bayern', 'Borussia Dortmund'],
        'crest_url': ['https://bayern.png', 'https://bvb.png'],
    })
    mock_conn = MagicMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    with patch('src.utils.data_loaders.engine', mock_engine), \
         patch('pandas.read_sql', return_value=fake_data), \
         patch('streamlit.cache_data', _no_cache):  # Cache deaktivieren
        # Modul neu laden um den Decorator-Cache zu umgehen
        import importlib
        import src.utils.data_loaders as dl
        importlib.reload(dl)
        result = dl.get_team_crests()

    assert isinstance(result, dict)
    assert result['FC Bayern'] == 'https://bayern.png'
    assert result['Borussia Dortmund'] == 'https://bvb.png'
