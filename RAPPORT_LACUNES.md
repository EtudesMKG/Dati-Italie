# Italie – rapport de couverture et de lacunes

Extraction du 28/09/2026. Classeur : `data/it/Italie_donnees_consolidees.xlsx`. Tables unitaires : `data/it/*.parquet` et `*.csv`. Scripts : `scripts/it/`, avec `run_all.py` comme point d'entrée. Les fichiers bruts sont dans `raw/<source>/<date>/`.
Clé de jointure : `cod_istat`, un texte à 6 chiffres. La commune 001168 « None » est conservée, ce qui est vérifié dans l'onglet « Contrôles ».

Légende des niveaux : **C** = commune, **P** = province, **R** = région, **N** = national.

## 1. Référentiel et cartographie

| Donnée | Niveau | Millésime | Statut |
|---|---|---|---|
| Liste des communes, sigles, codes Belfiore, codes 2017-2025 et 2010-2016, NUTS | C | 01/01/2026 | ✅ |
| Table de passage de la Sardaigne (recodage 2026) | C | 2026 | ✅ |
| Contours simplifiés (communes, provinces, régions) en EPSG:4326 et centroïdes | C | 01/01/2026 | ✅ `communes_it.geojson`, `communes_it_centroides.csv` |
| Superficie, altitude, couronnes urbaines | C | 2021 / 2026 | ✅ |
| Variations commune par commune (fusions) | C | – | ⚠️ Publiées uniquement dans SITUAS (situas.istat.it), qui est une application web. Le fichier « Variazioni 1991-2025 » ne contient que des comptages. Palliatif : colonnes de codes historiques et table de la Sardaigne. |

Castegnero Nanto (024129) est une fusion postérieure aux contours du 01/01/2026 : son contour est l'union des polygones de 024027 et 024071, signalée dans la colonne `contour_statut`.

## 2. Démographie

| Donnée | Niveau | Millésime | Statut |
|---|---|---|---|
| Population par âge simple et sexe (POSAS), tranches FR 0-19 / 20-64 / 65+ et tranches ISTAT | C | 1/1/2019 → 1/1/2026 (2026 = estimation) | ✅ Somme des tranches = total, contrôlé sur 100 % des lignes. |
| Série de population 2014-2026 (reconstruction intercensitaire + POSAS) | C | 2014-2026 | ✅ |
| Bilan démographique (naissances, décès, migrations, ménages) | C | 2019-2025 | ✅ |

## 3. Emploi, entreprises, revenus

| Donnée | Niveau | Millésime | Statut |
|---|---|---|---|
| Établissements et actifs par classe de taille (0-9, 10-49, 50-249, 250+) | C | 2012-2023 | ✅ Remplace la liste nominative française, mais sans les noms. |
| Établissements et actifs par section Ateco | C | 2023 | ✅ |
| Institutions publiques : nombre d'unités locales | C | 2011, 2015, 2017, 2020 | ✅ Nombre seulement. |
| Institutions publiques : **personnel** | C | – | ❌ Non diffusé par commune. |
| Institutions **non profit** (unités, salariés) | C | – | ❌ Pas de flux communal SDMX. Seul le niveau national / régional est disponible (740_1091, 741_1096). |
| **Recensement agricole 2020**, main-d'œuvre | C | – | ❌ Pas de flux communal SDMX (102_974 national / régional). |
| « Emplois totaux au lieu de travail » | C | – | ❌ Non constructible : ASIA exclut l'agriculture, l'administration publique et le non profit, et ces trois composantes n'existent pas en effectifs par commune. |
| Actifs résidents (occupés, chômeurs, inactifs) | C | 2018-2024 (pas de 2020) | ✅ |
| Salariés / indépendants résidents | C | 2021 | ✅ |
| Salariés, chiffre d'affaires, valeur ajoutée au lieu de travail | C | 2017 | ✅ Seule année publiée. |
| Revenus IRPEF (salaires, pensions, indépendants, revenu total, tranches de revenu) | C | années d'imposition 2012-2024 | ✅ Colonnes `CALCUL_*` = revenu moyen, calcul signalé. |
| Nombre d'entreprises (sièges) | P | 2012-2024 | ✅ Par province seulement, non diffusé par commune. |
| Salariés par secteur, sexe, qualification | P | 2012-2017 | ✅ |
| Salaires par qualification (INPS, Osservatorio lavoratori dipendenti) | P | – | ⚠️ Non extrait : le portail `servizi2.inps.it/servizi/osservatoristatistici/` est une application interactive sans export direct identifié. À faire manuellement ou via l'API interne si elle est documentée. |
| Déplacements domicile-travail (origine-destination) | C | 2011 | ✅ Dernier millésime publié ; aucune matrice plus récente issue du recensement permanent. Codes communes de 2011. |
| Sièges d'entreprises actives par commune (Chambres de commerce) | C | – | ❌ Rien d'officiel en open data par commune. CCIAA Marche / InfoCamere existe par province (non ISTAT, déjà intégré). |

## 4. Fiscalité locale

| Donnée | Statut |
|---|---|
| Taux d'IMU (ordinaire, catégorie D2 hôtels) | ❌ `www.finanze.gov.it` répond « Access Denied » (protection Akamai) aux accès automatisés. Pas de copie trouvée sur `www1.finanze.gov.it`. À télécharger manuellement : Dipartimento delle Finanze, « Prospetto aliquote IMU ». |
| Addizionale comunale IRPEF (taux, tranches) | ⚠️ Même blocage pour les barèmes. Les **montants** d'addizionale comunale payés par commune figurent en revanche dans la table IRPEF (colonnes `addizionale_comunale_*`). |
| Imposta di soggiorno (taxe de séjour) | ❌ Aucune base consolidée officielle ouverte. Les délibérations communales sont publiées sur le portail du Dipartimento delle Finanze, qui est bloqué comme ci-dessus. |

## 5. Cadastre et immobilier

| Donnée | Statut |
|---|---|
| Cadastre | Documentation seulement : service WMS de l'Agenzia delle Entrate `https://wms.cartografia.agenziaentrate.gov.it/inspire/wms/ows01.php` (GetCapabilities vérifié ; couches parcelles et bâtiments, INSPIRE). Aucune collecte. |
| Valeurs immobilières OMI (cotations semestrielles par zone, polygones des zones) | ⚠️ Téléchargement soumis à une inscription gratuite. Procédure : portail Agenzia delle Entrate → Servizi → « Forniture dati OMI » → se connecter (SPID/CIE) → demander les fichiers « Quotazioni » et « Zone OMI (KML/SHP) » → déposer les ZIP dans `raw/omi/<date>/`. Le script de traitement reste à écrire à réception des fichiers, car le format dépend de l'export. |
| Volumes de transactions (NTN) par commune | ⚠️ Publiés dans les statistiques OMI (rapports et tableaux). Même procédure, à valider. |

## 6. Mouvements hôteliers (équivalent BODACC) : sources payantes, documentation seulement

- **Registro Imprese / InfoCamere (Telemaco, API)** : accès payant, à l'acte (visures, actes de cession) ou par abonnement. Contact : infocamere.it / registroimprese.it. Aucune collecte faite.
- **AIDA (Bureau van Dijk), Cerved** : bases payantes sur abonnement. Non collectées.
- **Portale delle Vendite Pubbliche** (`pvp.giustizia.it`, ventes judiciaires) : site accessible. Collecte automatisée **non faite** : les CGU sont à vérifier avant tout filtrage « albergo » automatisé.

## 7. Accessibilité

| Donnée | Statut |
|---|---|
| Trafic aéroportuaire mensuel et cumulé par aéroport (national / international / UE) | ✅ Assaeroporti 2012-01 → 2026-07 (l'export Excel `data-upload.assaeroporti.com` est bloqué ; les tableaux HTML ont été lus). |
| Trafic ENAC (rapport annuel) | ⚠️ Page accessible, publications en PDF ; non extrait. |
| Autoroutes, échangeurs, gares OSM, coordonnées des aéroports, plages, forêts, parcs | ❌ **Bloqué par la politique réseau de l'environnement** : `overpass-api.de` et `download.geofabrik.de`. |
| Temps de trajet routier | ⚠️ OSRM public accessible (test Rome → Florence OK) ; pas de calcul de masse. |
| Liste des gares RFI (catégories Platinum…Bronze) | ⚠️ Page accessible, liste non extraite (page dynamique). Fréquentation des gares : pas de source ouverte identifiée. |
| Horaires de train (GTFS) | ❌ Point d'accès national `www.nap.mit.gov.it` **bloqué par la politique réseau**. |

## 8. Offre hôtelière nominative

| Région / source | Établissements | Commune | Nom | Chambres / lits | Coordonnées | CIN |
|---|---|---|---|---|---|---|
| Veneto (registre régional complet) | 8 329 | 99,9 % | ✅ | ✅ | ❌ | ✅ |
| Campania (registre régional au 30/04/2024) | 22 293 | 100 % | ✅ | ✅ | ❌ | ❌ |
| Lombardia (province Monza-Brianza seulement) | 196 | 100 % | ✅ | ❌ | ✅ | ❌ |
| Emilia-Romagna (commune de Bologna seulement) | 890 | 100 % | ❌ nom non publié | ✅ | ✅ | ❌ |
| Toscana (commune de Firenze seulement) | 2 275 | 100 % | ❌ nom non publié | ❌ | ✅ | ❌ |
| Lazio (hôtels 5 étoiles de Roma seulement) | 44 | 100 % | ✅ | ✅ chambres | ❌ | ❌ |
| Friuli-Venezia Giulia (structures à caractère social seulement) | 113 | 99 % | ✅ | ❌ | ❌ | ❌ |

- **Registres trouvés mais bloqués par la politique réseau** (connexion coupée systématiquement) : Piemonte (`api.smartdatanet.it`), Marche (`dati.regione.marche.it`), Calabria (`dati.regione.calabria.it`), Umbria (`dati.regione.umbria.it`), Sicilia (`dati.regione.sicilia.it`), Puglia (`osservatorio.dms.puglia.it`).
- **Non trouvés sur dati.gov.it** : Lazio (hors Rome 5 étoiles), Liguria, Toscana (hors Florence), Sardegna, Abruzzo, Molise, Basilicata, Valle d'Aosta, Trento, Bolzano (ASTAT), Friuli-Venezia Giulia (registre général). Il faut chercher sur chaque portail régional.
- **BDSR / CIN (Ministero del Turismo)** : les CSV référencés sur dati.gov.it renvoient une page anti-robot (Radware). Documentation seulement, pas d'extraction en masse.
- **Géolocalisation de secours OSM `tourism=hotel`** : bloquée (Overpass).

## 9. Demande

| Donnée | Niveau | Statut |
|---|---|---|
| Arrivées et nuitées (hôtels / extra-hôtelier, résidents / non-résidents) | C | ✅ 2014-2025 annuel, 2022-2025 mensuel. |
| Capacité (établissements, lits, chambres par étoiles) | C | ✅ 2019-2025 dans le classeur (2002-2025 dans les fichiers bruts). |
| Taux d'utilisation des lits hôteliers | C | ✅ **Calcul** (nuitées / lits × jours) ; vide quand les nuitées sont sous secret (*). La série officielle ISTAT R / P n'a pas été extraite. |
| Provenance des clients (pays / régions) | P | ✅ 2019-2025. |
| **Part affaires** (voyageurs étrangers : nuitées, dépenses par motif, dont travail / affaires, et par hébergement) | P (province visitée) | ✅ Banca d'Italia 2017-2025 (tableaux pivot). Les résidents italiens sont disponibles dans les mêmes fichiers bruts (pivot « ITALIANI »), non encore agrégés. |
| Prix (ADR, RevPAR) | – | ❌ Non publics (sources payantes : STR / CoStar, MKG, Lighthouse, AirDNA). |

## 10. Environnement touristique

| Donnée | Statut |
|---|---|
| Lieux de la culture MiC (musées, monuments, aires archéologiques, parcs historiques) | ✅ 6 197 lieux, 98,3 % rattachés à une commune. Coordonnées quand publiées (5 723). |
| Fréquentation des sites | ⚠️ ISTAT musées par commune 2011-2020 (déjà intégré). Visiteurs et recettes des sites d'État (MiC, `statistica.cultura.gov.it`) : page de données non localisée (l'ancienne URL renvoie 404). Tables ISTAT 2022 / 2025 : non trouvées en fichier communal. |
| Sites UNESCO | ⚠️ `whc.unesco.org` bloque les robots (Cloudflare). Remplacé par Wikidata (P757) : **source non officielle**, 287 biens / composantes, 96 % rattachés à une commune par leurs coordonnées. |
| Aires protégées (EUAP / WDPA) | ❌ L'ancienne page EUAP du ministère renvoie 404. WDPA (`protectedplanet.net`) est accessible, mais son téléchargement demande l'acceptation d'une licence : non fait. |
| Forêts, plans d'eau, plages, parcs de loisirs (OSM) | ❌ Bloqué (Overpass / Geofabrik). |

## Accès réseau à ouvrir pour compléter

Ces hôtes sont bloqués par la politique réseau de l'environnement ; il faut les ouvrir dans les paramètres réseau de l'environnement :
- `overpass-api.de`
- `download.geofabrik.de`
- `www.nap.mit.gov.it`
- `www.cin.turismo.gov.it`
- `api.smartdatanet.it`
- `dati.regione.marche.it`
- `dati.regione.calabria.it`
- `dati.regione.umbria.it`
- `dati.regione.sicilia.it`
- `osservatorio.dms.puglia.it`
- `data-upload.assaeroporti.com`

Deux autres sources bloquent l'accès de leur côté, avec leur propre protection anti-robot : `www.finanze.gov.it` et `whc.unesco.org`. Ouvrir le réseau n'y changera rien : téléchargement manuel.
