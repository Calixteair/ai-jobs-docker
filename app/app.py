"""Dashboard AI Jobs Market 2025–2026 — interface Streamlit.

Affichage uniquement : la connexion est dans db.py, les requêtes SQL dans queries.py.
Lancement : streamlit run app/app.py
"""

import logging

import db
import streamlit as st

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s : %(message)s")
logger = logging.getLogger(__name__)

st.set_page_config(page_title="AI Jobs Market 2025–2026", page_icon="📊", layout="wide")


@st.cache_resource(show_spinner="Connexion à la base de données…")
def get_connection():
    # Une exception n'est pas mise en cache : la connexion est retentée au prochain affichage.
    return db.connect()


st.title("Marché de l'emploi IA 2025–2026")
st.caption("Projet Docker 4A — Streamlit + MySQL, orchestrés par Docker Compose")

try:
    engine, config = get_connection()
except db.DatabaseConfigError as exc:
    logger.error("Configuration de la base invalide : %s", exc)
    st.error(f"**Configuration incomplète.** {exc}")
    st.stop()
except db.DatabaseUnavailable as exc:
    logger.error("Base indisponible : %s", exc)
    st.error(
        f"**Base de données injoignable.** {exc}\n\n"
        "L'application reste disponible. Vérifiez que le service `db` est démarré "
        "(`docker compose ps`, `docker compose logs db`), puis réessayez."
    )
    st.button("Réessayer")  # un clic relance le script, donc la connexion
    st.stop()

st.sidebar.success(f"Base connectée — MySQL {db.server_version(engine)}")
st.sidebar.caption(f"{config.host}:{config.port} · base `{config.database}`")

st.markdown(
    """
Cette application analyse **1 500 offres d'emploi** liées à l'intelligence artificielle
(dataset *AI Jobs Market 2025–2026*) : métiers, salaires, localisation, télétravail,
compétences demandées et niveau de demande.

Les données sont lues dans la base MySQL ; le fichier CSV ne sert qu'à l'import initial.

> Le dataset est un support pédagogique : les résultats ne constituent pas un recensement
> exhaustif du marché réel.
"""
)

st.info("Filtres, indicateurs et graphiques : à venir.")
