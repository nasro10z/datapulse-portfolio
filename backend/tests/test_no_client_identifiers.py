"""Garde-fou d'anonymisation — aucun identifiant client ne doit revenir dans le dépôt.

Le dépôt public ne doit porter ni le nom de l'opérateur ni celui de ses sites. Une
passe d'anonymisation les a retirés une fois ; ce test empêche qu'ils reviennent à
la faveur d'un copier-coller, d'une reprise de documentation ou d'un merge.

La liste des termes interdits vit dans `.anonymization-map.local.md` à la racine,
**gitignoré** : l'écrire dans ce fichier reviendrait à republier ce qu'on cherche à
retirer. Sans ce fichier, le test est *skippé* — même logique que les tests de
fidélité, qui exigent les données brutes privées. Il protège donc là où c'est
utile : sur la machine qui détient la correspondance, avant de pousser.
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MAP_FILE = REPO_ROOT / ".anonymization-map.local.md"

# Dossiers hors périmètre : données privées (gitignorées), dépendances, artefacts de
# build, et les worktrees des sessions Claude Code, qui portent d'autres états du dépôt.
SKIP_DIRS = {
    ".git", ".claude", "node_modules", ".venv", "__pycache__", "dist",
    ".pytest_cache", "data",
}
# Binaires et fichiers de verrouillage : illisibles en texte, ou bruit de hachage.
SKIP_SUFFIXES = {".db", ".joblib", ".xlsx", ".csv", ".png", ".svg", ".ico", ".shm", ".wal"}
SKIP_NAMES = {"package-lock.json", ".env", MAP_FILE.name}


def _forbidden_patterns() -> list[re.Pattern]:
    """Motifs interdits, lus dans les deux blocs de la table de correspondance.

    Deux modes, parce qu'un seul ne suffit pas :

    - bloc `text` → **sous-chaîne**, indispensable pour les identifiants composés :
      un nom de site collé à un autre jeton par un souligné n'a pas de limite de mot ;
    - bloc `words` → **mot entier**, pour les noms courts qui sont aussi des
      sous-chaînes françaises banales : l'un des noms de ville de la liste se trouve
      au milieu d'un participe présent très courant, ce qui a réellement fait échouer
      ce test sur un fichier parfaitement propre.

    Et ce module ne cite évidemment aucun des termes qu'il interdit : il se serait
    signalé lui-même — c'est arrivé.
    """
    text = MAP_FILE.read_text(encoding="utf-8")
    patterns: list[re.Pattern] = []
    for fence, template in (("text", "{}"), ("words", r"\b{}\b")):
        for block in re.findall("```" + fence + r"\n(.*?)```", text, re.S):
            for line in block.splitlines():
                if line.strip():
                    patterns.append(
                        re.compile(template.format(re.escape(line.strip())), re.IGNORECASE))
    assert patterns, f"Aucun terme interdit trouvé dans {MAP_FILE.name}"
    return patterns


def _scanned_files():
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(REPO_ROOT).parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES or path.name in SKIP_NAMES:
            continue
        yield path


@pytest.mark.skipif(not MAP_FILE.exists(), reason="table de correspondance absente")
def test_no_client_identifier_in_repo():
    patterns = _forbidden_patterns()
    hits = []
    for path in _scanned_files():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue  # binaire ou illisible : rien à vérifier
        for n, line in enumerate(lines, 1):
            for rank, pattern in enumerate(patterns, 1):
                if pattern.search(line):
                    rel = path.relative_to(REPO_ROOT).as_posix()
                    # Le rang, jamais le terme : ce message peut finir dans un log de CI.
                    hits.append(f"{rel}:{n} — terme interdit n°{rank}")
    assert not hits, (
        "Identifiant client retrouvé dans le dépôt :\n  " + "\n  ".join(hits[:20])
        + f"\n({len(hits)} occurrence(s)). Voir {MAP_FILE.name} pour le remplacement attendu."
    )
