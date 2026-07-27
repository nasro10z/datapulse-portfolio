# DataPulse — Référence UI

Cible visuelle du dashboard, extraite de **`DataPulse - Identity v2 (standalone).html`**
et des captures d'écran de référence (`docs/screenshots/`). Sert de source de
vérité pour le look & feel (profondeur, cartes surélevées, charts Recharts,
icônes Lucide, animations Framer Motion).

> Les PNG de référence sont à déposer dans `docs/screenshots/` (01-apercu.png …
> 10-vue-globale.png). Ce document en capture les specs.

## Palette (chart / statut — extraite du HTML)

Palette **feutrée** utilisée pour les charts et badges de statut (distincte des
accents vifs des tokens) :

| Statut | Libellé FR | Hex | Usage |
|---|---|---|---|
| healthy | **Sain** | `#3FA69C` (teal) | score ≥ 82 |
| watch | **Surveillance** | `#B8823E` (or) | score 68–81 |
| critical | **Critique** | `#C1443B` (rouge) | score < 68 |

Seuils de statut : `score >= 82 ? 'healthy' : score >= 68 ? 'watch' : 'critical'`.

Accents / surfaces :
- Accent : `#2F6BFF` (bleu), `accent-soft` pour surbrillance nav active.
- Sidebar : **slate foncé** persistant (`--sidebar` ≈ `#1E2434`), toujours sombre.
- Canvas : gris clair `#F3F4F6`. Cartes : blanc pur, `rounded-2xl`, `shadow-md/lg`.

## Layout (image 2)

- Conteneur parent `flex flex-row` : sidebar à gauche (largeur fixe, fond slate
  foncé), main `flex-1` poussé à droite — **pas d'overlay**.
- Header : titre + sous-titre à gauche ; à droite, bouton thème + langue +
  horloge « SYNCHRONISÉ · HH:MM ».
- Cartes métriques : blanc, coins très arrondis, ombre portée subtile (élévation).
- Animations Framer Motion : fade-in + slide-up à l'entrée, léger scale au survol.

## Sous-scores du site (Santé du site — images 1/2/3)

Pondérés → score global = 87·0.30 + 81·0.25 + 66·0.25 + 90·0.20 = **81**.

| Sous-score | Score | Poids | Statut | Détail |
|---|---|---|---|---|
| Environnement | 87 | 30 % | Sain | Temp 23,4° · HR 46 % · 10 salles dans la plage |
| Énergie | 81 | 25 % | Surveillance | Charge onduleur 68 % · FP 0,98 · secteur stable |
| Batterie | 66 | 25 % | Critique | 2 chaînes · capacité UPS-2 en dégradation |
| Alarmes | 90 | 20 % | Sain | 4 ouvertes · 0 critique · MTBA 14h |

Répartition parc (14 actifs) : 9 sain · 3 surveillance · 2 critique.

Familles d'équipement : STULZ ASD 522 AS · Climatisation (×10, score 84),
SOCOMEC 200 kVA · Onduleur (×2, 75), YANAN Diesel · Groupes électrogènes (×2, 83).

## Écrans de référence (captures)

1. **Aperçu** — score global 81 (sparkline pulse), résumé sous-scores (barres
   Environnement/Énergie/Batterie/Alarmes), cartes « prochaine PM » / « prochaine panne prédite ».
2. **Santé du site** — chart multi-lignes « Évolution du score par sous-score »
   (7j/30j/90j), cartes de détail par sous-score avec jauge radiale + poids + statut.
3. **Santé du site (suite)** — cartes Batterie/Alarmes, « par famille d'équipement »
   (mini-sparklines + score + tendance), chart « évolution alarmes par famille ».
4. **Prédiction de pannes** — chart score global + prévision + bande de confiance +
   ligne seuil critique ; sous-scores par famille (seuil atteint dans ~Nj).
5. **Prédiction (suite)** — alertes de franchissement (Critique/Risque élevé/Élevé),
   diagramme de Gantt « fenêtres de risque · 60 prochains jours ».
6. **Anomalies** — 3 modèles de détection (Temp/HR, SCADA, UPS) + stats (total, taux,
   contributeur) + histogramme « nombre d'anomalies par modèle ».
7. **Anomalies (suite)** — histogramme temporel (barres, 1 rouge = pic) + table
   d'épisodes (équipement, famille, début, durée, sévérité, statut, score).
8. **Maintenance** — calendrier mensuel (légende par famille) + formulaire + « planning calculé ».
9. **Rappels** — filtres (Tous/Critique/Seuils/Maintenance) + cartes de rappel
   (Reporter / Acquitter, badges Immédiat/Imminent/Planifié).
10. **Vue globale** — cartes par site (jauge radiale + problèmes + anomalies + PM),
    « principale panne prédite par site », « meilleure performance », « vue d'ensemble par domaine ».

## Librairies

- **Recharts** — charts (lignes, barres, jauges radiales, aires de confiance).
- **lucide-react** — icônes (nav, statuts, alertes).
- **framer-motion** — animations d'entrée + survol des cartes.
