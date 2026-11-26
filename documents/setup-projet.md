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

## 6. Vérifier, committer et pousser le dépôt

Après l'installation Python, le terminal se trouve dans `campusdata-etudiant`.
Revenir dans le dossier parent avant les commandes Git ci-dessous :

```powershell
Set-Location ".."
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
