"""Point d'entrée Streamlit — AI Jobs Market 2025-2026.

Squelette du Sprint 1 : connexion à MySQL, gestion des erreurs et page
d'accueil minimale. Le contenu du dashboard arrive au Sprint 2
(cf. docs/MAQUETTE.md). Aucun SQL n'est écrit ici : tout passe par db.py.
"""

import streamlit as st
from sqlalchemy.engine import Engine

from db import DatabaseUnavailable, DbConfig, create_db_engine, fetch_dataframe, wait_for_database

st.set_page_config(page_title="AI Jobs Market 2025-2026", page_icon="📊", layout="wide")


@st.cache_resource(show_spinner="Connexion à la base de données…")
def get_engine() -> Engine:
    """Crée le moteur SQLAlchemy une seule fois pour toutes les sessions.

    En cas d'échec, l'exception n'est pas mise en cache : la connexion est
    retentée au prochain rechargement de la page.
    """
    engine = create_db_engine(DbConfig.from_env())
    wait_for_database(engine, attempts=5, delay=2.0)
    return engine


def show_connection_error(error: Exception) -> None:
    st.error("Impossible de se connecter à la base de données.")
    st.caption(f"Détail : {error}")
    st.info(
        "Vérifiez que le service `db` est démarré et en bonne santé "
        "(`docker compose ps`), puis rechargez la page."
    )


def main() -> None:
    st.title("AI Jobs Market 2025-2026")
    st.write(
        "Analyse de 1 500 offres d'emploi liées à l'intelligence artificielle : "
        "métiers, salaires, localisation, télétravail, compétences et demande."
    )

    try:
        engine = get_engine()
        jobs = fetch_dataframe(engine, "SELECT COUNT(*) AS n FROM jobs")
    except (ValueError, DatabaseUnavailable) as error:
        show_connection_error(error)
        st.stop()

    st.success(f"Connecté à MySQL — {int(jobs.loc[0, 'n'])} offres disponibles.")
    st.info("Le dashboard (KPI, filtres et visualisations) arrive au Sprint 2.")


main()
