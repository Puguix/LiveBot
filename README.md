# Live Bot

Liste des commandes pour set-up le projet:

```
git clone https://github.com/Puguix/LiveBot.git
```

```
bash ./LiveBot/install.sh
```

Puis modifier secret.json et ligne 25 de trix.py -> "./LiveBot/secret.json"

Et enfin:

```
crontab -e
```

Puis rentrer 1 pour éditer avec nano si demandé, et mettre à la fin:

```
0 * * * * python3 LiveBot/trix.py >> cronlog.log
```
