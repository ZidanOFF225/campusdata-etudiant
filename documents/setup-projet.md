# Guide de setup du projet étudiant

Ce guide décrit la préparation sous Windows avec PowerShell, la création du
dépôt étudiant et l'installation des dépendances Python. Les commandes Git
partent du dossier parent qui contient `campusdata-starter` et
`campusdata-etudiant`.

## 1. Installer Python 3.12

Dans PowerShell, installer Python avec WinGet :

```powershell
winget install --exact --id Python.Python.3.12
```

Si WinGet demande d'accepter les conditions de la source Microsoft Store,
les lire avant de répondre. Ouvrir un nouveau terminal, puis vérifier que
Python 3.12 est disponible :

```powershell
py -0p
py -3.12 --version
```

## 2. Créer le dépôt étudiant sur GitHub

1. Créer un dépôt séparé du kit `campusdata-starter` (par exemple
   `campusdata-etudiant`) et choisir la visibilité demandée par le cours
   (le dépôt créé pour ce projet est privé).
2. Pour un dépôt vide, ne pas demander à GitHub de créer un README, un
   `.gitignore` ou une licence : ces fichiers viennent du kit.
3. Depuis GitHub, copier l'URL HTTPS du dépôt. Dans PowerShell, se placer
   dans le dossier parent du kit et cloner le dépôt :

```powershell
Set-Location "C:\chemin\vers\PROJECT"
git clone "COLLER_ICI_L_URL_HTTPS_DU_DEPOT"
```

Remplacer le texte entre guillemets par l'URL HTTPS copiée. Le dossier cloné
doit être à côté de `campusdata-starter`.

## 3. Copier le kit sans l'environnement local ni les secrets

Depuis le dossier parent, copier les fichiers du kit dans le dépôt cloné :

```powershell
robocopy ".\campusdata-starter" ".\campusdata-etudiant" /E /XD ".venv" ".git" /XF ".env" ".env.*" "cloud.env"
```

La commande exclut l'environnement virtuel, le dossier Git et les fichiers
d'environnement. `robocopy` peut retourner un code de sortie compris entre
0 et 7 même si la copie s'est déroulée normalement ; un code de 8 ou plus
signale une erreur de copie.

La règle `.env.*` exclut aussi le modèle `.env.example`. Si ce modèle existe
dans le kit, le copier séparément :

```powershell
if (Test-Path ".\campusdata-starter\.env.example") {
    Copy-Item ".\campusdata-starter\.env.example" ".\campusdata-etudiant\.env.example"
}
```

Le `.env.example` doit contenir uniquement des valeurs fictives ou des
placeholders. Ne pas copier ni versionner `.env`, `cloud.env`, des mots de
passe réels, des jetons ou des clés privées.

## 4. Créer le venv dans le dépôt étudiant

Créer l'environnement virtuel à la racine de `campusdata-etudiant`, et non
dans `campusdata-starter`. L'environnement est local à la machine et ne doit
pas être copié dans Git :

```powershell
Set-Location ".\campusdata-etudiant"
py -3.12 -m venv .venv
```

PowerShell peut bloquer l'activation des scripts. Autoriser l'activation
pour le terminal courant uniquement, puis activer le venv :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Cette politique ne persiste pas après la fermeture du terminal. Si
l'activation reste bloquée, utiliser directement l'interpréteur du venv :

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r api/requirements-dev.lock
.\.venv\Scripts\python.exe -m pip check
```

## 5. Installer et vérifier les dépendances

Avec le venv activé, vérifier Python et installer le lock de développement :

```powershell
python --version
python -c "import sys; print(sys.executable)"
python -m pip install -r api/requirements-dev.lock
python -m pip check
```

`python --version` doit afficher Python 3.12.x et le chemin de
`sys.executable` doit pointer vers `campusdata-etudiant\.venv`. Le lock de
développement inclut les dépendances runtime, les outils de test et Ruff.
`pip check` vérifie les incompatibilités entre dépendances ; il ne remplace
pas l'exécution des tests.

Pour vérifier si un paquet particulier est installé dans l'interpréteur actif :

```powershell
python -m pip show fastapi
```

Cette commande affiche la version installée, mais ne garantit pas qu'elle
correspond au lock. Pour vérifier le lock sans installer ni modifier de
paquets, utiliser :

```powershell
python -m pip install --dry-run --no-deps -r api/requirements-dev.lock
```

La mise à jour de pip est facultative. Si elle est souhaitée, l'effectuer avec
le venv activé :

```powershell
python -m pip install --upgrade pip
```

Elle ne change pas les versions des dépendances déclarées dans les locks.

## 6. Configurer `.env` et démarrer PostgreSQL et l'API

Depuis la racine de `campusdata-etudiant`, créer `.env` à partir du modèle
uniquement s'il n'existe pas déjà :

```powershell
if (-not (Test-Path .\.env)) { Copy-Item .\.env.example .\.env }
```

Générer un mot de passe aléatoire et le copier dans le presse-papiers sans
l'afficher dans le terminal :

```powershell
$bytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes)
$secret = -join ($bytes | ForEach-Object { $_.ToString("x2") })
$rng.Dispose()
Set-Clipboard -Value $secret
Remove-Variable secret, bytes, rng
```

Ouvrir `.env` et remplacer les deux occurrences de `CHANGE_ME` par ce mot de
passe, puis enregistrer. Ne pas partager le contenu de `.env`. Conserver
`DATABASE_URL` avec l'hôte `db` et le port `5432` dans ce fichier : il sert à
Compose. Le `.gitignore` exclut `.env`; vérifier avec :

```powershell
git check-ignore .env
```

Vérifier que Docker Desktop est lancé, puis démarrer uniquement la base de
données de développement :

```powershell
docker compose --env-file .\.env -f .\compose.dev.yaml up -d db
docker compose --env-file .\.env -f .\compose.dev.yaml ps
```

Le résultat attendu est un service `db` `Up (healthy)` et le port
`127.0.0.1:5433` relié au port PostgreSQL `5432` du conteneur.

Pour lancer l'API sur le poste, utiliser un DSN qui pointe vers
`127.0.0.1:5433`. Dans le terminal qui servira à lancer Uvicorn, se placer à
la racine du dépôt et activer le venv. Si c'est un nouveau terminal, la
politique `Process` peut devoir être réappliquée :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python --version
python -c "import sys; print(sys.executable)"
```

Vérifier que Python affiche `3.12.x` et que son chemin contient
`campusdata-etudiant\.venv`. Toujours depuis la racine du dépôt, charger le
mot de passe depuis `.env` sans l'afficher, puis se placer dans `api/` avant
de démarrer Uvicorn :

```powershell
$passwordLine = Get-Content .\.env | Where-Object { $_ -match '^POSTGRES_PASSWORD=' } | Select-Object -First 1
if (-not $passwordLine) { throw "POSTGRES_PASSWORD absent de .env" }
$password = $passwordLine -replace '^POSTGRES_PASSWORD=', ''
$env:DATABASE_URL = "postgresql+psycopg://campus:$password@127.0.0.1:5433/campus"
Remove-Variable password, passwordLine
Set-Location .\api
python -m uvicorn app.main:app --reload
```

Le terminal doit maintenant se trouver dans
`campusdata-etudiant\api`. Ce changement de dossier est nécessaire : le
paquet `app` se trouve dans `api\app`. Si Uvicorn est lancé depuis la racine
du dépôt, l'erreur `No module named 'app'` apparaît.

Laisser ce terminal ouvert. Dans un second terminal, vérifier les sondes :

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/ready
Invoke-RestMethod http://127.0.0.1:8000/api/version
```

La réponse attendue est `ok` pour la liveness, `ready` pour la readiness et
`dev` pour la version locale. La readiness vérifie une connexion PostgreSQL
avec `SELECT 1`; elle ne valide pas encore les tables métier. Le starter ne
fournit que ces routes de santé et de version.

Pour arrêter l'API, utiliser `Ctrl+C` dans son terminal. Pour arrêter la base
sans supprimer ses données, depuis la racine du dépôt :

```powershell
docker compose --env-file .\.env -f .\compose.dev.yaml stop db
```

Ne pas ajouter `--volumes` à une commande de nettoyage si les données locales
doivent être conservées.

## 7. Vérifier, committer et pousser le dépôt

Se placer dans le dossier parent qui contient `campusdata-etudiant` avant les
commandes Git ci-dessous :

```powershell
Set-Location "C:\chemin\vers\PROJECT"
git -C .\campusdata-etudiant status --short --branch
```

Avant le premier commit, vérifier que les secrets ne sont pas inclus et que
`.env.example` ne contient que des placeholders. Le `.gitignore` du kit
exclut `.venv/`, `.env`, `.env.*` (sauf `.env.example`) et `cloud.env`.

Ajouter les fichiers, puis vérifier ce qui sera commité :

```powershell
git -C .\campusdata-etudiant add .
git -C .\campusdata-etudiant status --short
git -C .\campusdata-etudiant diff --cached --check
git -C .\campusdata-etudiant diff --cached --stat
```

Si la liste est attendue et qu'aucun secret ou fichier local n'est indexé,
créer le commit initial et le pousser :

```powershell
git -C .\campusdata-etudiant commit -m "Initialise le dépôt étudiant"
git -C .\campusdata-etudiant push -u origin main
git -C .\campusdata-etudiant status --short --branch
```

Après le push, le statut attendu est `## main...origin/main` sans fichier
modifié. Un `M` devant un chemin indique une modification locale non commitée :
`git push` ne l'envoie pas. Examiner le changement avec `git diff -- chemin`,
puis l'ajouter, le vérifier, le committer et le pousser s'il doit être partagé.
