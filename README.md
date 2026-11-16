# 🏴‍☠️ Alertes tournois – One Piece Official Shop Paris (Les Halles)

Ce petit robot vérifie Bandai TCG+ toutes les 15 minutes et t'envoie un message Discord :

- **🏴‍☠️ Nouveau tournoi publié** dès qu'un tournoi apparaît pour la boutique officielle du Forum des Halles (tournois en anglais **et** en français) ;
- **🔔 Inscriptions ouvertes** quand les inscriptions d'un tournoi déjà annoncé ouvrent.

Chaque message donne la date, le prix, le nombre de places, la langue des cartes et le lien direct vers la page d'inscription TCG+.

Ça tourne gratuitement sur GitHub Actions : pas besoin de laisser ton PC allumé.

---

## Installation (10 minutes environ)

### 1. Créer le webhook Discord
1. Sur ton serveur Discord, fais un clic droit sur le salon qui doit recevoir les alertes, puis **Modifier le salon**.
2. Va dans **Intégrations**, puis **Webhooks**, puis **Nouveau webhook**.
3. Clique sur **Copier l'URL du webhook** et garde-la de côté.

> Pas de serveur Discord ? Crée-en un pour toi seul : bouton **+** à gauche, puis **Créer le mien**.

### 2. Mettre le code sur GitHub
1. Crée un compte gratuit sur https://github.com si tu n'en as pas.
2. Clique sur **New repository**, donne-lui un nom (par exemple `op-halles-watch`) et choisis **Public**. Les minutes d'exécution sont illimitées pour un dépôt public. Ton webhook ne sera pas visible, voir l'étape 3.
3. Clique sur **uploading an existing file** et glisse **tout le contenu** du dossier, y compris le dossier `.github` (voir l'astuce plus bas), puis **Commit changes**.

> **Astuce pour le dossier `.github` :** le Finder (Mac) et l'Explorateur (Windows) cachent parfois les dossiers qui commencent par un point. Si c'est le cas, crée le fichier à la main sur GitHub : clique sur **Add file**, puis **Create new file**, tape `.github/workflows/watch.yml` comme nom, colle le contenu du fichier, puis **Commit**.

### 3. Ajouter le webhook en secret
Dans ton dépôt, va dans **Settings**, puis **Secrets and variables**, puis **Actions**, puis **New repository secret** :
- **Name :** `DISCORD_WEBHOOK_URL`
- **Secret :** l'URL copiée à l'étape 1

### 4. Lancer le premier test
Va dans l'onglet **Actions**. Si GitHub demande d'activer les workflows, accepte. Clique ensuite sur **Surveillance tournois OP Halles**, puis **Run workflow**.

Au bout d'une minute environ, tu dois recevoir sur Discord :
> ✅ Surveillance activée : N tournoi(s) à venir déjà publiés…

Ce sont les tournois déjà en ligne : ils ne sont pas renvoyés un par un. À partir de là, tu ne recevras que les **nouveautés**.

---

## Réglages possibles

| Quoi | Où |
|---|---|
| Fréquence de vérification | `cron` dans `.github/workflows/watch.yml` (`*/30 * * * *` = toutes les 30 min) |
| Désactiver l'alerte « inscriptions ouvertes » | ajoute `NOTIFY_REG_OPEN: "0"` sous `env:` dans le workflow |
| Surveiller une autre boutique | ajoute `ORGANIZER_ID: "<id>"` sous `env:` (l'identifiant de la boutique sur TCG+) |

## Bon à savoir
- **Coût :** 0 € avec un dépôt public. En privé, garde une vérification toutes les 30 min pour rester dans les 2 000 minutes gratuites par mois.
- GitHub peut lancer les vérifications planifiées avec quelques minutes de retard aux heures chargées.
- Le script enregistre un petit commit `state.json` une fois par semaine. Ça évite que GitHub mette en pause les tâches planifiées d'un dépôt inactif.
- L'API de Bandai TCG+ n'est pas documentée officiellement. Si Bandai la modifie, la vérification apparaîtra en rouge dans l'onglet **Actions** (GitHub t'envoie aussi un e-mail), et il faudra adapter `watcher.py`.
- Boutique surveillée : **One Piece Official Shop Paris**, identifiant TCG+ `7388`, Westfield Forum des Halles, niveau -3.
