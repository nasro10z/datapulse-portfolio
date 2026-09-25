# DataPulse — Choix data science & ML : pourquoi ces décisions

Ce document explique **pourquoi** le pipeline est ce qu'il est : ce que la problématique
métier imposait, ce que les données permettaient, et ce qui a été écarté en chemin.
Il complète :

- [`data-architecture.md`](data-architecture.md) — l'architecture (bronze/silver/gold),
- [`ml-data-integration.md`](ml-data-integration.md) — l'implémentation et l'inventaire des données,
- [`../handover/current-state.md`](../handover/current-state.md) — ce qui est réel vs démo.

**Sources** : notebooks livrés (`environmental_fixed.ipynb`, `health_scores.ipynb`),
package `mlops-api` vendorisé sous `app/ml/`, `metadata.json` des trois modèles, journal
de décisions `SESSIONS.md`, et les tests de fidélité. **Règle d'honnêteté** : aucun
chiffre de performance n'est avancé au-delà de ce que portent les artefacts livrés et nos
propres tests. Ce qui n'est pas prouvé est signalé comme tel (§5).

---

## 1. La problématique, et ce qu'elle impose au ML

DataPulse est une **couche d'aide à la décision** pour un data center télécom — pas un
système d'alarme autonome. Trois personas, trois attentes :

| Persona | Attente | Conséquence directe sur le ML |
|---|---|---|
| Manager de sites | Vue d'ensemble, comparaison, priorisation | Un **score agrégé** lisible, décomposable en sous-scores, avec un **driver dominant** — donc une formule explicable, pas une boîte noire |
| Superviseur d'alarmes | Réduire la fatigue liée aux **fausses alertes** | La **précision de ce qui est affiché** prime sur le rappel : mieux vaut taire une anomalie douteuse que noyer l'opérateur (§3.6, §4.4) |
| Technicien de maintenance | **Anticiper** la dégradation avant la panne | Un horizon de prévision, et une **bande d'incertitude** honnête plutôt qu'une courbe qui affirme |

Deux conséquences transversales, qui reviennent partout dans ce document :

1. **Rien ne décide à la place de l'humain.** Le pipeline produit des scores, des épisodes
   et des explications — jamais un ordre d'intervention. C'est ce qui permet d'assumer un
   modèle imparfait : son erreur coûte une lecture, pas un arrêt d'équipement.
2. **Tout affichage doit être défendable.** D'où le choix systématique, en cas de doute,
   de la version la plus conservatrice : filtrer plutôt que surfacer, amortir plutôt
   qu'extrapoler, élargir la bande plutôt qu'inventer une courbe.

---

## 2. Ce que les données permettent — et ce qu'elles interdisent

Trois sources, fournies en **exports CSV/XLSX** (la base PostgreSQL source est sur une
plateforme isolée, non joignable) :

| Source | Volume brut | Ce qu'elle porte |
|---|---|---|
| `temp_humid_msc10.csv` | 140 077 lignes | Température / humidité de la salle switch, pas de 120 s |
| `logs_msc10.xlsx` + `ups_socomec1_msc10_events.csv` | 2 250 + 1 024 lignes | Journal d'alarmes SCADA et événements onduleur (2026) |
| `alarmes_scada_2022.xlsx` | 35 408 lignes (2 664 pour le site) | Historique d'alarmes multi-sites 2022 |

**Cinq contraintes structurantes en découlent :**

1. **Un seul capteur pour toute la salle.** Il n'existe aucune mesure par unité de
   climatisation. → La détection environnementale est **par salle**, jamais par unité
   STULZ. Tout ce qui prétendrait « l'unité 3 chauffe » serait inventé. C'est la
   contrainte la plus déterminante du projet.
2. **Aucune vérité terrain de panne.** Aucun historique labellisé « panne à telle date ».
   → Pas d'apprentissage supervisé de la panne. On se rabat sur du **non supervisé** (HMM,
   IsolationForest) et sur des **proxys explicites** (franchissement de seuils).
3. **Des données figées.** L'export s'arrête en mai 2026. → Pas de temps réel (Phase 8 H
   bloquée), et toute fenêtre glissante doit être ancrée sur la **fin de la couverture
   capteur**, pas sur l'horloge — sinon elle tombe entièrement après la fin des données.
4. **Un historique déséquilibré selon les familles.** Climatisation installée en 2019,
   onduleurs en 2020, groupes YANAN en **2025** — ces derniers n'ont pas d'historique
   exploitable. → Le domaine batterie est scoré par formule, pas par modèle appris.
5. **Les alarmes 2022 n'ont jamais entraîné le modèle.** Constat fait en auditant le
   notebook : leur format de date (`2/21/2022 2:02:53 PM`) échouait au parsing →
   2 664 `log_time` à `NaT`, supprimés par le `dropna` suivant. Le modèle livré est
   **entièrement entraîné sur 2026**. Notre ingestion exclut 2022 explicitement pour
   reproduire ce périmètre à l'identique, et le lecteur `load_scada_alarms_2022` est
   conservé pour un éventuel backfill historique plus large.

---

## 3. Décisions d'EDA et de préprocessing

Chaque décision suit le même schéma : **constat dans les données → décision → pourquoi
c'était le bon arbitrage ici**.

### 3.1 Doublons de timestamps — garder la ligne la plus complète

**Constat** : 242 timestamps portent plusieurs lignes, dont certaines dégradées (humidité
absente).

**Décision** : tri par complétude puis `drop_duplicates(keep="first")` — la ligne la plus
renseignée gagne (`dedupe_and_index`).

**Pourquoi** : ces doublons ne sont pas des mesures concurrentes mais des **valeurs de
repli** du capteur. Choisir au hasard, ou moyenner, aurait injecté le repli dans la série.
La règle « le plus complet gagne » est déterministe et rejouable.

### 3.2 Les replis capteur sont des données manquantes, pas des mesures

**Constat** : l'export brut encode une défaillance capteur par une humidité qui tombe à
**0-11 %** puis remonte à 44 % à la lecture suivante — physiquement impossible dans une
salle. Le fichier de référence livré porte `NaN` à ces mêmes timestamps. Quelques lignes
présentent aussi des champs concaténés (ex. « 4523.9 »).

**Décision** : bornes de plausibilité physique — humidité ≥ 15 %, température ∈ [5, 60] °C
— hors desquelles la lecture est traitée comme **manquante**
(`ml/health_score/config.ENV_PLAUSIBLE_*`).

**Pourquoi** : comptées comme mesures, ces valeurs faisaient exploser l'**écart-type
horaire** et, via l'échelle p95 qui normalise le terme de variabilité, **déréglaient le
score sur toute la série**. Les bornes retenues restent largement en deçà du vécu réel du
fichier de référence (min observés : 23,5 % et 17,9 °C) : elles n'écartent aucune mesure
valide. Écart résiduel mesuré sur le score global après correction : **0,45 point**,
attribuable au millésime de l'export.

### 3.3 Continuité : le seuil à 125 s et la segmentation

**Constat** : le pas nominal est de 120 s, mais la série est trouée — coupures secteur et
pannes de communication SCADA.

**Décision** : tout écart > **125 s** est une discontinuité ; les segments continus sont
numérotés par `cumsum()` sur ces discontinuités → **1 905 segments** sur 107 047 lignes.

**Pourquoi** : les features glissantes (§3.4) n'ont de sens que **dans** un segment
continu. Une moyenne sur 2 h 36 à cheval sur une coupure de six heures n'est pas une
moyenne, c'est une invention. La marge de 5 s absorbe la gigue d'horodatage sans laisser
passer une vraie coupure. La segmentation sert aussi de feature : `segment_freshness` dit
au modèle « on vient de reprendre après une coupure », un contexte où l'anormalité
apparente est attendue.

### 3.4 Trois échelles de fenêtres glissantes — 12 / 36 / 78 points

**Constat** : l'autocorrélation (ACF) de la série montre une dépendance qui persiste bien
au-delà de la minute.

**Décision** : trois fenêtres — **court 12** (~24 min), **moyen 36** (~1 h 12),
**long 78** (~2 h 36) — chacune avec `min_periods` à la moitié.

**Pourquoi trois échelles** : la salle a une dynamique lente. Un pic de 10 minutes et une
dérive de 3 heures sont deux phénomènes différents, et un modèle qui n'en voit qu'un seul
les confond. Le **delta court ↔ long** (`temp_short_long_delta`) est précisément ce qui
distingue « il fait chaud depuis toujours » de « ça monte maintenant ». `min_periods` à la
moitié évite qu'un début de segment produise des statistiques calculées sur deux points.

### 3.5 Seuils de sévérité par Tukey, et directionnels

**Constat** : aucune spécification constructeur exploitable n'est disponible pour la
salle.

**Décision** : seuils dérivés de la **distribution observée** par la méthode de Tukey
(IQR), et **directionnels** — température : `mild_upper` **26,75 °C**, `extreme_upper`
**28,65 °C** (q1 23,9 / q3 25,8 / IQR 1,9), avec les bornes basses symétriques
(`thresholds.json`).

**Pourquoi Tukey** : à défaut de spec, le seul référentiel défendable est le
**comportement normal réel de cette salle**. Un seuil à 27 °C choisi à la main n'aurait
été ni traçable ni transposable à un autre site ; la même formule appliquée à un autre
capteur redonne des seuils adaptés à ce capteur. Les facteurs 0,5 / 1,0 / 1,5 × IQR
donnent trois niveaux (mild / strong / extreme) au lieu d'un binaire, ce qui alimente
directement la sévérité affichée.

**Pourquoi directionnel** : une salle trop froide et une salle trop chaude n'ont ni la
même cause ni le même risque. L'épisode porte donc une `direction` (`high`/`low`), et
l'excursion dominante décide quand les deux bornes sont franchies dans le même run.

### 3.6 Hystérésis : la décision qui répond au persona « superviseur »

**Constat** : une température qui oscille autour du seuil génère, avec un simple test
`> seuil`, un épisode à chaque oscillation.

**Décision** : détection à hystérésis — on **entre** en épisode au franchissement, on n'en
**sort** qu'après être repassé sous le seuil d'une marge (`exit_margin = 0,5 °C`) pendant
une durée minimale (`min_exit_duration = 5` lectures).

**Pourquoi** : c'est la traduction technique directe de « réduire la fatigue liée aux
fausses alertes ». Sans hystérésis, un même événement physique devient dix alertes ; le
superviseur apprend à les ignorer, et le produit a échoué. Sur le périmètre du pipeline
livré, l'hystérésis ramène **201 runs bruts à 27-36 épisodes cohérents**.

### 3.7 Bronze = copie fidèle, le nettoyage vit en silver

**Constat** : les fichiers bruts sont hétérogènes — latin-1 au lieu d'utf-8, en-tête sur
la ligne 1, dates en `DD/MM/YYYY` d'un côté et `M/D/YYYY h:mm AM/PM` de l'autre, fichier
2022 multi-sites, états `Q` et `Acquittement - Système` absents du périmètre
d'entraînement.

**Décision** : l'ingestion **normalise uniquement la forme** (encodage, reconstruction du
`ts`, en-têtes, filtrage du site) et écrit une copie fidèle en bronze ; la déduplication
et le nettoyage n'interviennent qu'en **silver** — d'où 140 077 lignes en bronze contre
107 047 en silver.

**Pourquoi** : garder le brut intact rend le pipeline **rejouable** (un changement de
règle de nettoyage se rejoue sans redemander les fichiers) et rend la **fidélité
prouvable** — c'est ce qui permet les golden tests du §5.

---

## 4. Choix des modèles

### 4.1 Environnement — HMM gaussien à 6 états

**Le problème posé par les données** : 24 °C peut être parfaitement normal ou franchement
anormal selon le **régime** dans lequel se trouve la salle et selon la **dynamique** qui
précède. Une anomalie environnementale est **contextuelle**, pas ponctuelle.

**Pourquoi un modèle à états latents** : une salle climatisée passe par des régimes non
observés directement — fonctionnement nominal, cycle de dégivrage, charge thermique
élevée, reprise après coupure. Un HMM apprend ces régimes **et** les transitions entre
eux ; c'est exactement la structure du phénomène. Les alternatives ont été écartées pour
des raisons précises :

| Alternative | Pourquoi écartée ici |
|---|---|
| Seuil simple sur la température | Ne voit aucun contexte ; c'est d'ailleurs un *complément* retenu en filtre (§4.4), pas un détecteur |
| IsolationForest sur les lectures | Traite les points comme i.i.d. — il ignore la **séquence**, qui porte l'essentiel du signal ici |
| Supervisé (classification d'anomalie) | Pas de labels (§2, contrainte 2) |

**Sélection du modèle** (protocole livré, reproduit) : `n_states ∈ {2,3,4,5,6}` ×
`prop_cutoff ∈ {0.05, 0.10, 0.20, 0.30}`, **5 graines** (0, 7, 21, 42, 99), 500
itérations, une configuration n'étant retenue que si **chaque état contient ≥ 20 points**.
Retenu : **6 états**, `prop_cutoff = 0,05`, **F1 anomalie 0,83** (`metadata.json`). La
contrainte de taille d'état écarte les solutions qui « expliquent » une anomalie en créant
un état à trois points — un surapprentissage déguisé en finesse.

**19 features, et pourquoi elles** : les deux mesures brutes, leurs moyennes aux trois
échelles, les écarts-types courts (la **variabilité** est un signal en soi), les deltas
court ↔ long (la dérive), les variations instantanées et à 10 minutes (la **vitesse**), et
les trois `segment_freshness` (le contexte post-coupure). L'ordre des colonnes est figé :
le scaler et le HMM sont dépicklés tels quels, une permutation les rendrait silencieusement
faux.

**Ce que ce choix coûte** : 4 états sur 6 sont marqués anormaux, donc le HMM est
**généreux**. D'où le filtre produit du §4.4.

### 4.2 SCADA / onduleurs — IsolationForest

**Décision** : IsolationForest, 300 arbres, `contamination = 3 %`, entraîné sur
**720 événements** agrégés, 10 features d'événement (durée, nombre d'alarmes, types
uniques, actives/effacées, taux, diversité, facteur de répétition, ratio d'actives, heure).

**Pourquoi** : pas de labels (§2), **720 événements seulement** — un volume où un modèle
profond ou un ensemble supervisé n'a rien à apprendre —, et des features tabulaires
hétérogènes sans structure temporelle exploitable au niveau de l'événement agrégé.
IsolationForest est robuste dans ce régime, ne demande pas d'hypothèse de distribution, et
son unique paramètre fort (`contamination`) est une **hypothèse explicite et discutable**
sur le taux d'anomalies — 3 % — plutôt qu'un seuil implicite.

**Statut honnête** : ce modèle est entraîné et chargeable, mais **n'est pas branché au
gold** (Phase 9). Aucune anomalie affichée aujourd'hui n'en provient. La `dimension` des
épisodes servis vaut `environment`, jamais `scada`.

### 4.3 Score de santé — une formule pondérée explicite, pas un modèle appris

**Décision** : le score de santé du site n'est pas appris. C'est une composition pondérée,
versionnée (`weight_version = v1.0`), portée du notebook `health_scores.ipynb` :

```
risque_final(domaine) = risque_base(domaine)
                        × (1 + w_anomalie · charge_anomalie)
                        × (1 + w_PM · risque_PM)
score(domaine)        = 100 − risque_final
score_global          = 0,30·environnement + 0,35·énergie + 0,35·batterie
```

**Pourquoi ne pas apprendre ce score** : il n'existe **aucune cible** à apprendre — aucune
vérité terrain ne dit « le site était à 62/100 ce jour-là ». Un modèle appris aurait donc
appris un proxy arbitraire, sans gagner en justesse, et en perdant l'essentiel : chaque
point de score est **décomposable** en domaine, puis en terme, ce qui permet d'afficher le
**driver dominant**, une priorité de maintenance et une action conseillée. Pour les trois
personas, savoir *pourquoi* le score baisse vaut plus qu'un dixième de précision.

**Détails de conception qui comptent** :

- **Poids intra-domaine** (environnement : température 0,40, humidité 0,25, variabilité
  température 0,20, variabilité humidité 0,15) : la température pèse le plus parce que
  c'est elle qui menace les équipements ; la **variabilité** pèse 35 % au total parce
  qu'une salle qui oscille signale une régulation en difficulté avant que le niveau ne
  dérive.
- **Le terme `persistence` en batterie porte le poids le plus fort (0,25)**, et a été
  ajouté au formalisme initial à cinq termes. Raison : le comptage brut d'alarmes ne
  distingue pas un défaut qui s'efface immédiatement d'un défaut **qui ne s'efface pas** —
  or c'est précisément cette différence qui sépare le bruit de la dégradation réelle.
- **Risque de PM** linéaire de 0 à 1 sur l'intervalle attendu (90 j climatisation, 180 j
  énergie) puis plafonné : le risque cesse de croître une fois la maintenance très en
  retard, il est déjà au maximum.
- **Batteries** : aucune date de service connue → ancrage sur le premier point de données,
  décision explicite plutôt qu'une date inventée.
- **Versionnement** : `weight_version` et `score_version` sont écrits dans **chaque ligne
  gold**, pour qu'un score servi reste traçable jusqu'à la configuration qui l'a produit.

**Limite connue et assumée** : `ENV_LAST_PM_DATE` (2026-03-01) et `ENERGY_LAST_PM_DATE`
(2022-12-13) sont en dur. La date énergie précède la fenêtre de logs, donc le risque de PM
énergie est **à son plafond sur toute la période scorée**. C'est arithmétiquement correct
au vu de l'entrée, et il faut le savoir avant d'interpréter ce sous-score. Le branchement
sur les `pm_schedules` réellement saisis reste ouvert.

### 4.4 Ce qui est affiché : HMM **et** franchissement de seuil réel

**Décision produit, pas décision de modélisation** : un run d'état anormal du HMM dont la
**température ne franchit aucun seuil Tukey** n'est pas surfacé comme épisode. Effet
mesuré sur notre déroulé du HMM sur tout le silver : **~1 383 runs bruts → 388 épisodes**.

**Pourquoi** : le HMM est généreux (§4.1) et détecte aussi des anomalies d'humidité ou
purement contextuelles. Affichées telles quelles à un superviseur, elles produisent
exactement ce que le produit existe pour éviter. On **sacrifie du rappel pour de la
précision perçue**, et on l'assume : ce qui est affiché est toujours une excursion
thermique réelle, vérifiable par l'opérateur sur la courbe.

Le reste du mapping « run → épisode » est également explicite : pic = température extrême
du run, sévérité `critical` au franchissement du seuil `extreme`, type `collective` (le HMM
détecte du multivarié contextuel), équipement `SALLE_SWITCH` (granularité réelle, §2
contrainte 1), identifiants `EP-0001…` stables dans l'ordre chronologique — stabilité
indispensable puisque les acquittements utilisateur sont persistés **par identifiant**.

### 4.5 Prévision — XGBoost sur le **delta** à 6 h, top 20 features

**Le constat qui a tout décidé** : `overall_site_health` se comporte comme un processus
**AR(1)**. Tant que la cible apprise était le **niveau** du score, aucun modèle ne battait
la persistance — ni le notebook (test : persistance 6,00 vs linéaire 6,18 vs gradient
boosting 10,55 vs 16,14), ni notre premier portage (validation : persistance 6,44 vs
linéaire 6,61 vs GB 11,03). Servir un modèle moins bon que « le score reste où il est »
aurait été une régression déguisée en modèle — la persistance a donc été servie dans un
premier temps, assumée comme telle.

**Le changement de cible** :

```
cible          = target_health_change_6h = santé(t+6h) − santé(t)
reconstruction = clip(santé_courante + delta_prédit, 0, 100)
```

**Pourquoi c'est ce qui débloque tout** : prédire le niveau demande à des arbres
d'**extrapoler une tendance**, ce qu'ils ne savent structurellement pas faire (un arbre ne
sort jamais de l'enveloppe de ses feuilles). Sur le delta, la persistance se réduit à
« delta = 0 » et le modèle n'a plus qu'un **écart** à apprendre — un problème centré,
borné, à la portée d'un ensemble d'arbres.

**Pourquoi une sélection top-N** : la fabrique de features produit **~1 200 features
dynamiques** (retards, variations, vitesses, statistiques et **pentes** glissantes en forme
fermée, accélération, compteurs de dégradation continue, interactions entre sous-systèmes)
pour seulement **1 474 heures d'entraînement**. Plus de features que d'exemples : le
surapprentissage est garanti. D'où un XGBoost « large » qui **classe** les features, puis
un réentraînement sur les top 20 / 50 / 100 / 200, N choisi sur la **validation** :

| N features | MAE validation |
|---|---|
| **20** | **5,804** ← retenu |
| 50 | 6,278 |
| 100 | 6,251 |
| 200 | 6,191 |

Le notebook obtient 5,79 sur le même protocole : le portage est fidèle.

**Les 20 features retenues sont interprétables** et cohérentes avec le métier : moyennes et
maxima glissants du risque énergie (6 h, 12 h), interaction environnement × énergie,
retards 24 h/48 h de la santé batterie, amplitude glissante 24 h de la santé
environnementale, charge d'anomalie énergie. Autrement dit, le modèle apprend que la
dégradation à 6 h se lit dans la **dynamique récente de l'énergie** et dans l'**état
batterie de la veille** — pas dans le niveau courant.

**Alternatives écartées** :

| Alternative | Pourquoi écartée |
|---|---|
| Persistance (delta = 0) | Reste la référence de comparaison ; battue de peu, mais surtout : **elle ne bouge jamais**, donc n'anticipe rien pour le technicien |
| Variante pondérée sur les heures de chute (poids 1,25 / 1,75 / 2,50) | Meilleure sur les chutes (rappel 0,40 vs 0,33), mais MAE globale dégradée (7,05 vs 6,08) → conservée dans les métriques, **non servie** |
| LightGBM | MAE test 5,025, à 0,007 d'XGBoost top 20 — écart non significatif, écarté pour ne pas ajouter une seconde dépendance de gradient boosting |
| Modèle par sous-score | Aucun modèle validé par domaine → projection à niveau constant avec bande élargie. Une bande large qui dit « on ne sait pas » vaut mieux qu'une courbe inventée |

**Au-delà de +6 h — amortissement** (décision propre à l'application, absente du notebook,
qui ne fait pas de multi-pas) : le modèle n'est validé qu'à +6 h. Réappliqué récursivement
tel quel, son delta se compose et la trajectoire à 7 jours **saturait à 100/100** —
annoncer « site parfait pendant une semaine » est un mensonge pire qu'une droite plate.
Chaque delta au-delà du premier pas est donc réduit géométriquement
(`RECURSIVE_DELTA_DAMPING = 0,5`), ce qui borne l'excursion totale à ~2× le premier pas, et
la bande s'élargit en √pas à partir de l'écart-type des résidus de test (10,50). Résultat
servi : 69,9 → convergence vers 76,4 au lieu de 100.

**Chiffres honnêtes** (split test, 317 heures) :

| Modèle | MAE | RMSE | R² | Précision haut risque |
|---|---|---|---|---|
| Persistance | 6,124 | 10,147 | 0,274 | 0,333 |
| **XGBoost top 20 (servi)** | **6,085** | 10,503 | 0,222 | 0,500 |

Le notebook rapporte +0,97 de MAE contre la persistance ; **nous obtenons +0,04**. Les MAE
de **validation** coïncident (5,80 vs 5,79), donc la méthode est fidèlement portée :
l'écart vient du jeu de test lui-même (~316 heures, erreur à queue lourde) et du millésime
de l'export environnemental. **Ne pas citer le +0,97 du notebook comme étant le nôtre.** Le
gain réel pour le produit n'est pas le dixième de MAE — c'est que **la courbe bouge, portée
par un modèle**, au lieu de répéter la dernière valeur.

**Classifieur de chute** (alerte « chute > 10 points à 6 h ») : RandomForest, seuil choisi
sur le F1 de validation. Sur le test : précision **0,107**, rappel 0,607, PR-AUC 0,085 —
159 alertes pour 28 événements réels. **C'est faible, et ce n'est pas survendu** : il sert
de signal secondaire, pas d'alarme.

---

## 5. Ce qui est prouvé, ce qui ne l'est pas

**Prouvé par des tests automatisés** (78 tests verts) :

| Ce qui est vérifié | Référence | Résultat |
|---|---|---|
| Ingestion SCADA | `msc10_combined_ups.csv` | **100 % exact** (2 569/2 569, catégories comprises) |
| Ingestion environnementale | `temp_humid_last.csv` | temp **99,95 %**, humidité **99,76 %** (seuil ≥ 99,5 %) |
| Portage du scoring | `site_health_scores_v1_0.csv` (sortie du notebook) | **égalité < 1e-6** sur les 4 scores |

Le résidu environnemental (~0,1-0,3 %) est un écart de **millésime d'export** (timestamps
supplémentaires, résolution des doublons), pas une divergence de logique.

**Non prouvé — à dire explicitement** :

- **Le F1 de 0,83 du modèle environnemental n'est pas une validation contre des pannes
  réelles.** Il provient du protocole du notebook, dont les labels sont eux-mêmes des
  proxys de seuils. Aucun jeu de labels externe n'existe.
- **La prévision n'est validée qu'à +6 h.** Les horizons 7 j et 30 j sont un déroulé amorti
  à conditions inchangées — une projection, pas une prédiction validée.
- **Aucune évaluation *walk-forward*** (les cellules 192-222 du notebook — pipeline v2,
  temps d'avance des alertes, validation inter-périodes 2022, réglage Optuna — ne sont pas
  portées).
- **Aucune validation par unité d'équipement** : la granularité réelle est la salle (§2).
- **Les poids v1.0 sont figés** : le notebook expose des curseurs (ipywidgets) non portés,
  faute de surface UI pour les piloter.

---

## 6. Limites assumées et suites identifiées

| Limite | Conséquence pour la lecture des résultats | Suite envisagée |
|---|---|---|
| Détection par salle | Aucun score ne mesure l'état d'une unité STULZ particulière | Instrumentation par unité (hors périmètre données) |
| Dates de PM en dur | Le risque de PM énergie est à son plafond sur toute la période | Brancher sur `pm_schedules` (état applicatif) |
| `alarm_anomaly` non branché | Aucune anomalie affichée ne vient du SCADA | Phase 9 — UPS / groupes |
| 2022 hors entraînement | Le modèle ne connaît qu'un an de saisonnalité | Backfill historique élargi |
| Données figées (mai 2026) | Fenêtres ancrées sur la fin de couverture, pas sur l'horloge | Phase 8 H — bloquée, pas de flux source |
| `family` = `stulz/socomec/yanan` | Clé **technique** portant les trois domaines (environnement/énergie/batterie) — l'écran libelle bien par domaine | Renommer la clé si le contrat d'API évolue |

---

## 7. Où lire quoi

| Fichier | Ce qu'il porte |
|---|---|
| `app/ml/environmental/config.py` | Seuil de continuité, fenêtres, marges d'hystérésis, grille de sélection HMM, ordre des 19 features |
| `app/ml/environmental/preprocessing.py` | Déduplication, segmentation, seuils de Tukey, features glissantes |
| `app/ml/models/*/metadata.json` | Métriques et hyperparamètres **des artefacts livrés** — source des chiffres de ce document |
| `app/ml/models/environmental/thresholds.json` | Seuils Tukey température / humidité |
| `app/ml/health_score/config.py` | Poids v1.0, multiplicateurs anomalie/PM, dates de PM, bornes de plausibilité |
| `app/ml/health_score/forecasting.py` | Cible delta, sélection top-N, déroulé amorti |
| `app/etl/detect.py` | Mapping run HMM → épisode, filtre « seuil réel », sévérité, statut |
| `backend/tests/` | Les golden tests qui prouvent le §5 |
| `SESSIONS.md` | Le journal des décisions — le « pourquoi » au fil de l'eau |
