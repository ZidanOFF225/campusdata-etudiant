# Comprendre les tables et la logique métier

Ce document explique les trois tables déclarées dans
[`api/app/models.py`](../api/app/models.py) avec un exemple fictif.

## Vue d'ensemble

CampusData organise les données ainsi :

```text
Dataset (jeu de données)
  ├── Ingestion (fichier CSV déposé)
  │     └── Measurement (mesures extraites de ce fichier)
  └── Measurement (mesures appartenant au jeu)
```

Un jeu de données peut recevoir plusieurs fichiers. Chaque fichier traité peut
produire plusieurs mesures. Le lien direct entre une mesure et son jeu permet
de retrouver toutes les mesures du jeu; le lien vers l'ingestion indique quel
fichier a fourni la mesure.

## 1. `datasets` : organiser les mesures

Un jeu de données est un conteneur logique, par exemple un bâtiment, une
période ou un ensemble de relevés.

| Champ | Rôle |
|---|---|
| `id` | Identifiant UUID du jeu, généré par défaut. |
| `name` | Nom obligatoire, limité à 120 caractères et unique. |
| `description` | Description facultative. |
| `owner` | Responsable déclaré, « Équipe » par défaut; ce n'est pas un compte authentifié. |
| `created_at` | Date de création en UTC. |

Exemple :

| id | name | owner |
|---|---|---|
| `11111111-1111-4111-8111-111111111111` | Bâtiment A - octobre | Équipe |

La contrainte d'unicité sur `name` empêche, par exemple, de créer deux jeux
nommés exactement « Bâtiment A - octobre ».

## 2. `ingestions` : garder la trace des fichiers

Une ingestion représente un fichier envoyé pour être traité dans un jeu.

| Champ | Rôle |
|---|---|
| `id` | Identifiant UUID de l'ingestion. |
| `dataset_id` | Jeu auquel le fichier est rattaché. |
| `filename` | Nom original du fichier. |
| `content` | Contenu brut du fichier en octets; le traitement peut ensuite vérifier l'encodage. |
| `status` | État du traitement : `pending`, `running`, `succeeded` ou `failed`. |
| `rows_total`, `rows_accepted`, `rows_rejected`, `rows_duplicate` | Compteurs remplis par la logique de traitement. |
| `errors`, `error_message` | Détails des erreurs de ligne ou du problème global. |
| `created_at`, `started_at`, `finished_at` | Dates de création, de début et de fin. Les dates de début et de fin peuvent être absentes avant les étapes correspondantes. |

Exemple juste après le dépôt :

| id | dataset_id | filename | status |
|---|---|---|---|
| `aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa` | `11111111-1111-4111-8111-111111111111` | `mesures-matin.csv` | `pending` |

Le parcours visé est :

1. L'API enregistre le fichier en `pending`.
2. Un worker le prend en charge et le passe à `running`.
3. Le worker valide les lignes, crée les mesures acceptées et met à jour les compteurs.
4. Le traitement se termine en `succeeded` ou en `failed`.

La contrainte SQL vérifie que le statut fait partie des quatre valeurs
autorisées. Elle ne suffit pas à imposer l'ordre des transitions : cette règle
doit être appliquée par le code métier.

## 3. `measurements` : conserver les relevés validés

Une ligne de cette table correspond à une mesure dans une salle à un instant
donné.

| Champ | Rôle |
|---|---|
| `id` | Identifiant numérique de la mesure. |
| `dataset_id` | Jeu auquel la mesure appartient. |
| `ingestion_id` | Fichier qui a produit la mesure. |
| `room` | Identifiant de la salle. |
| `measured_at` | Date et heure du relevé. |
| `co2_ppm` | Concentration de CO₂, autorisée entre 250 et 10 000 ppm. |
| `temperature_c` | Température, autorisée entre -30 et 60 °C. |
| `humidity_pct` | Humidité, autorisée entre 0 et 100 %. |

Les limites sont appliquées par des contraintes SQL. Elles protègent la base
même si une autre partie du programme essaie d'enregistrer une valeur invalide.

## Exemple complet de traitement CSV

Supposons que l'équipe a créé le jeu « Bâtiment A - octobre », puis déposé ce
fichier :

```csv
room,measured_at,co2_ppm,temperature_c,humidity_pct
A101,2026-10-05 09:00:00,720,21.5,42.0
A101,2026-10-05 09:05:00,810,21.7,43.0
A101,2026-10-05 09:10:00,950,22.0,130.0
```

Les deux premières lignes respectent les limites du modèle. Après validation,
elles peuvent être enregistrées dans `measurements` :

| dataset | ingestion | room | measured_at | CO₂ (ppm) | température (°C) | humidité (%) |
|---|---|---|---|---:|---:|---:|
| Bâtiment A - octobre | `mesures-matin.csv` | A101 | 2026-10-05 09:00 | 720 | 21,5 | 42,0 |
| Bâtiment A - octobre | `mesures-matin.csv` | A101 | 2026-10-05 09:05 | 810 | 21,7 | 43,0 |

La troisième ligne a une humidité de 130 %, supérieure à la limite SQL de
100 %. La logique d'import doit la rejeter et garder une explication dans le
rapport d'erreurs plutôt que l'enregistrer comme mesure.

L'ingestion pourrait ensuite afficher :

| rows_total | rows_accepted | rows_rejected | rows_duplicate | status |
|---:|---:|---:|---:|---|
| 3 | 2 | 1 | 0 | `succeeded` |

Ces compteurs sont un exemple de résultat attendu : le modèle déclare les
colonnes, mais c'est le worker qui doit les calculer et les enregistrer.

## Comment la règle contre les doublons fonctionne

La contrainte unique `uq_measurement` porte sur le triplet
`(dataset_id, room, measured_at)`.

Si un autre fichier contient une mesure pour le même jeu, la salle `A101` et
l'instant `2026-10-05 09:00`, la base refuse une deuxième ligne avec cette même
combinaison. Le code d'import doit gérer ce conflit et compter la ligne comme
doublon. En revanche :

- une mesure à `09:00` dans la salle `A102` n'a pas la même clé et est permise;
- une mesure à `09:00` dans un autre jeu n'a pas la même clé et est permise;
- une mesure dans `A101` à `09:05` est permise, car l'instant diffère.

Cette règle rend possible une réimportation sans dupliquer les relevés déjà
présents, à condition que le code métier traite correctement le conflit.

## Effet de la suppression d'un jeu

Les clés étrangères utilisent `ON DELETE CASCADE`. Supprimer un jeu entraîne
donc la suppression de ses ingestions et de ses mesures liées. Supprimer une
ingestion entraîne aussi la suppression des mesures issues de ce fichier.
Cette suppression en cascade est pratique pour nettoyer les données d'un jeu,
mais elle est définitive sans sauvegarde.

## À retenir

- `datasets` organise les mesures.
- `ingestions` conserve le fichier déposé, son statut et le bilan de son traitement.
- `measurements` contient les relevés validés et leurs valeurs.
- Les clés étrangères relient ces enregistrements et les contraintes protègent
  les règles fondamentales.
- `models.py` décrit la structure et les contraintes; il ne réalise pas à lui
  seul la réception du CSV, le traitement asynchrone, le calcul des compteurs
  ni les indicateurs métier.
