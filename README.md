# 1xBet Scraper - Apify Actor

🏆 **Scraper professionnel pour 1xbet.com** - Extraction complète de données sportives pré-match et post-match avec monitoring avancé.

## 📋 Description

Cet Actor Apify permet d'extraire des données sportives complètes depuis 1xbet.com, incluant :

### 🎯 Données Pré-Match
- **Matchs à venir** avec équipes, cotes et horaires
- **Cotes détaillées** (1X2, Over/Under, Handicap, etc.)
- **Compositions d'équipes** et joueurs
- **Conditions météorologiques** pour les matchs en extérieur
- **Statistiques des équipes** et historique

### 📊 Données Post-Match
- **Résultats finaux** et scores détaillés
- **Événements de match** (buts, cartons, remplacements)
- **Statistiques complètes** (possession, tirs, passes, etc.)
- **Performances individuelles** des joueurs
- **Résumés de match** et analyses

### 🔧 Fonctionnalités Avancées
- **Monitoring en temps réel** avec alertes
- **Limitation de taux intelligente** pour éviter les blocages
- **Gestion d'erreurs robuste** avec retry automatique
- **Validation des données** avec Pydantic
- **Support multi-sports** (Football, Basketball, Tennis, etc.)
- **Extraction parallèle** pour optimiser les performances

## 🚀 Installation et Configuration

### Prérequis
- Python 3.8+
- Compte Apify (pour déploiement)
- Docker (optionnel, pour développement local)

### Installation Locale

```bash
# Cloner le repository
git clone https://github.com/cresus-ui/scraper-1xbet.git
cd scraper-1xbet

# Installer les dépendances
pip install -r requirements.txt

# Installer Playwright (pour le rendu JavaScript)
playwright install chromium
```

### Configuration

Créez un fichier `.env` (optionnel) :

```env
# Configuration optionnelle
APIFY_TOKEN=your_apify_token
LOG_LEVEL=INFO
MAX_RETRIES=3
REQUEST_DELAY=2
```

## 📖 Utilisation

### 🎮 Via Apify Console

1. **Accédez à l'Actor** sur [Apify Console](https://console.apify.com)
2. **Configurez les paramètres** d'entrée
3. **Lancez l'extraction** et surveillez les résultats
4. **Téléchargez les données** au format JSON/CSV/Excel

### 💻 Développement Local

```bash
# Exécution directe
python -m src.main

# Avec configuration personnalisée
python -m src.main --config config.json

# Mode debug
python -m src.main --debug
```

### 🐳 Avec Docker

```bash
# Build de l'image
docker build -t 1xbet-scraper .

# Exécution
docker run -v $(pwd)/data:/app/data 1xbet-scraper
```

## ⚙️ Configuration d'Entrée

### Paramètres Principaux

```json
{
  "sports": ["football", "basketball", "tennis"],
  "extraction_type": "both",
  "max_matches_per_sport": 50,
  "include_odds": true,
  "include_statistics": true,
  "include_lineups": true,
  "date_range": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  },
  "output_format": "json",
  "monitoring": {
    "enable_alerts": true,
    "health_check_interval": 300,
    "max_error_rate": 0.1
  }
}
```

### Options Avancées

| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| `sports` | Array | Sports à extraire | `["football"]` |
| `extraction_type` | String | `"prematch"`, `"postmatch"`, `"both"` | `"both"` |
| `max_matches_per_sport` | Number | Limite par sport | `100` |
| `include_odds` | Boolean | Inclure les cotes | `true` |
| `include_statistics` | Boolean | Inclure les statistiques | `true` |
| `include_lineups` | Boolean | Inclure les compositions | `false` |
| `parallel_requests` | Number | Requêtes parallèles | `3` |
| `request_delay` | Number | Délai entre requêtes (sec) | `2` |
| `max_retries` | Number | Tentatives max | `3` |

## 📊 Format de Sortie

### Structure des Données

```json
{
  "matches": [
    {
      "match_id": "12345",
      "sport": "football",
      "competition": "Premier League",
      "teams": {
        "home": {
          "name": "Manchester United",
          "logo": "https://...",
          "odds": 2.1
        },
        "away": {
          "name": "Liverpool",
          "logo": "https://...",
          "odds": 3.2
        }
      },
      "match_time": "2024-01-15T15:00:00Z",
      "status": "upcoming",
      "odds": {
        "1x2": {"1": 2.1, "x": 3.4, "2": 3.2},
        "over_under": {"over_2_5": 1.8, "under_2_5": 2.0}
      },
      "statistics": {
        "possession": {"home": 55, "away": 45},
        "shots": {"home": 12, "away": 8}
      },
      "events": [
        {
          "minute": "23",
          "type": "goal",
          "player": "Marcus Rashford",
          "team": "home"
        }
      ]
    }
  ],
  "metadata": {
    "extracted_at": "2024-01-15T10:30:00Z",
    "total_matches": 150,
    "sports_covered": ["football", "basketball"],
    "extraction_duration": "00:05:23"
  }
}
```

## 🔍 Monitoring et Métriques

### Tableau de Bord

L'Actor fournit des métriques détaillées :

- **Taux de succès** par sport et type d'extraction
- **Temps de réponse** moyen des requêtes
- **Erreurs détectées** et actions correctives
- **Utilisation des ressources** (CPU, mémoire)
- **Progression en temps réel** de l'extraction

### Alertes Automatiques

- **Taux d'erreur élevé** (>10%)
- **Temps de réponse lent** (>30s)
- **Blocage détecté** par le site
- **Données manquantes** ou incohérentes

## 🛠️ Architecture Technique

### Modules Principaux

```
src/
├── main.py                 # Point d'entrée principal
├── config.py              # Configuration et validation
├── session_manager.py     # Gestion des sessions Playwright
├── data_processor.py      # Traitement et validation des données
├── monitoring.py          # Système de monitoring
└── extractors/
    ├── prematch_extractor.py   # Extraction pré-match
    └── postmatch_extractor.py  # Extraction post-match
```

### Technologies Utilisées

- **[Playwright](https://playwright.dev/)** - Automatisation navigateur
- **[Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/)** - Parsing HTML
- **[Pydantic](https://pydantic-docs.helpmanual.io/)** - Validation des données
- **[Asyncio](https://docs.python.org/3/library/asyncio.html)** - Programmation asynchrone
- **[Apify SDK](https://docs.apify.com/sdk/python/)** - Intégration plateforme

## 🚨 Gestion d'Erreurs

### Stratégies de Récupération

1. **Retry automatique** avec backoff exponentiel
2. **Rotation des User-Agents** pour éviter la détection
3. **Gestion des timeouts** avec délais adaptatifs
4. **Validation des données** avant stockage
5. **Alertes en temps réel** pour intervention manuelle

### Codes d'Erreur

| Code | Description | Action |
|------|-------------|--------|
| `E001` | Site inaccessible | Retry avec délai |
| `E002` | Captcha détecté | Pause et retry |
| `E003` | Données manquantes | Log et continue |
| `E004` | Rate limit atteint | Attente et retry |
| `E005` | Erreur de parsing | Validation et skip |

## 📈 Performance

### Optimisations

- **Extraction parallèle** jusqu'à 5 threads
- **Cache intelligent** pour éviter les requêtes dupliquées
- **Compression des données** pour réduire l'usage mémoire
- **Pagination optimisée** pour les grandes listes
- **Sélecteurs CSS optimisés** pour un parsing rapide

### Benchmarks

- **~200 matchs/minute** en mode standard
- **~500 matchs/minute** en mode rapide (sans statistiques détaillées)
- **Utilisation mémoire** : ~100MB pour 1000 matchs
- **Taux de succès** : >95% en conditions normales

## 🤝 Contribution

### Développement

```bash
# Fork et clone
git clone https://github.com/votre-username/scraper-1xbet.git

# Créer une branche
git checkout -b feature/nouvelle-fonctionnalite

# Installer en mode développement
pip install -e .

# Lancer les tests
pytest tests/

# Vérifier le code
flake8 src/
black src/
```

### Guidelines

1. **Tests unitaires** obligatoires pour nouvelles fonctionnalités
2. **Documentation** mise à jour
3. **Code style** : Black + Flake8
4. **Commits** : Convention Conventional Commits
5. **Pull Request** avec description détaillée

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

## 🆘 Support

### Ressources

- **[Documentation Apify](https://docs.apify.com/)**
- **[Issues GitHub](https://github.com/cresus-ui/scraper-1xbet/issues)**
- **[Discord Apify](https://discord.com/invite/jyEM2PRvMU)**

### Contact

Pour toute question ou support :

- 📧 **Email** : support@cresus-ui.com
- 💬 **Discord** : Rejoignez notre serveur
- 🐛 **Bugs** : Créez une issue GitHub

---

**⭐ Si ce projet vous aide, n'hésitez pas à lui donner une étoile !**

*Développé avec ❤️ par l'équipe Cresus UI*
