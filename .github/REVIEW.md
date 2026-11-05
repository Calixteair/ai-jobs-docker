# Consignes du bot de review (ai-jobs-docker)

Lues par le bot sur la branche `dev`, jamais dans la PR relue (ce fichier est sous CODEOWNERS).

## Le projet

Projet étudiant ESIEA : application Web d'analyse du marché de l'emploi IA. **Streamlit** (`app/`),
**MySQL 8.4** (`database/`, scripts d'initialisation), **Docker Compose**, tests `pytest` (`tests/unit`,
`tests/integration`), style `ruff`. Données importées depuis un CSV public, aucune donnée personnelle.

## À refuser

- Requête SQL construite par concaténation ou f-string avec une valeur venue de l'utilisateur ou du CSV
  (requêtes paramétrées obligatoires).
- Secret, mot de passe ou jeton en clair (y compris dans les tests ou la doc) ; `.env` versionné.
- Appel réseau vers un service externe non prévu, téléchargement ou exécution de code au démarrage.
- `unsafe_allow_html=True` avec un contenu non maîtrisé (XSS dans Streamlit).
- Code qui casse visiblement l'application ou les tests existants, ou qui supprime des tests sans raison.

## Remarques mineures (sans bloquer)

Nommage, duplication, test manquant pour une nouvelle fonction, message d'erreur peu clair.
