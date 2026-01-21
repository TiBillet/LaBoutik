# Documentation de la Base de Données - LaBoutik

## Présentation Rapide
LaBoutik est une application de gestion de point de vente (POS) et de paiement **Cashless**. Elle permet de gérer des membres, des catalogues de produits, des transactions via cartes NFC ou terminaux (Stripe), ainsi que le service en salle (gestion des tables) et la comptabilité.

---

## Liste des Tables par Modules

### 💳 Cashless & Paiement (Cœur du système)
- **MoyenPaiement** : Définit les types de monnaies acceptées (Euro, Tokens, etc.).
- **CarteCashless** : Cartes physiques liées aux membres pour les paiements.
- **Assets** : Soldes et crédits disponibles sur une carte pour une monnaie donnée.
- **CarteMaitresse** : Cartes spéciales avec des droits étendus (ex: staff).

### 👥 Utilisateurs & Membres
- **TibiUser** : Utilisateurs du système (staff/admin) avec authentification par clé publique.

### 📦 Catalogue & Ventes
- **Articles** : Produits en vente avec prix, TVA et méthode de préparation.
- **Categorie** / **GroupementCategorie** : Organisation hiérarchique du catalogue.
- **PointDeVente** : Lieux physiques où les ventes sont effectuées.
- **TauxTVA** : Configuration des taxes applicables.

### 🍽️ Gestion de Salle
- **Table** : Tables physiques pour le suivi des commandes clients.
- **CategorieTable** : Types de zones ou de tables (Terrasse, Salle, etc.).
- **CommandeSauvegarde** : Paniers ou commandes ouvertes en attente de paiement.
- **ArticleCommandeSauvegarde** : Détails des articles dans une commande ouverte.

### 📊 Comptabilité & Rapports
- **ArticleVendu** : Archive de chaque article vendu pour les statistiques.
- **ClotureCaisse** : Enregistrement des fins de service et totaux financiers.
- **RapportArticlesVendu** / **RapportTableauComptable** : Vues agrégées pour la gestion.

### ⚙️ Matériel & Configuration
- **Printer** : Configuration des imprimantes thermiques (Epson, Sunmi).
- **Appareil** / **Terminal** : Terminaux physiques (tablettes, terminaux de paiement).
- **Configuration** : Paramètres globaux de l'application (Stripe, Odoo, Dokos, etc.).
