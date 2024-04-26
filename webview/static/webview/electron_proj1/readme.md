#Tests front
##Attention (pour le moment)
- Les tests sont dépendants de la base de données 
- Avant chaque test:   
. Supprimer les commandes(admin).   
. Libérer les tables.

## Informations sur le contenu du dossier "electron_proj1"
- ./BaseTest.js:   
  Module contant le framework de test et les noms des fichers tests à lancer(**let fonctionsTests**).   
- ./besoinTests.js:   
  Remplace le fichier lecteur_nfc.js (en cours de traitement).   
- ./insertModuleTests.js:   
  Charge dynamiquement des modules "navigateur" et non "nodejs"
- ./main.js:   
  programme que lance électron au démarrage
- ./package.json:   
  Utiliser par npm, contient diverses informations, dont les modules installés.
  Ces modules sont pour électron et l'application.
  La commande "npm install" utilise ce fichier pour installer les modules nécéssaires.
- ./preloadSiteVisite.js:   
  Permet d'insérer du code javascript dans la page du navigateur avant tout traitement de celle-ci.
- ./tests/*:
  Dossier contenat les tests à lancer.
## Préparation
- Se rendre dans le dossier "electron_proj1"
- Installer les modules nodejs du fichier "package.json":   
```
npm install
```
## Lancer les tests(électon)
```
npm start
```
## Contenu d'un fichier test de base:
```
export default function () {
  // module "Test" qui appelle une de ses fonctions "titre"n, la quelle configure un titre (obligatoire).   
  Test.titre('titre du test !')   
   
  ...   
    utilisation des fonctions du module Test(BaseTest.js)   
  ...   
   
  // cette fonction "afficherBlockslogs", affiche les résultats et lance le prochain test (obligatoire).   
  Test.afficherBlockslogs()   
}
```
- Le nom de ce fichier doit être ajouter au tableau "fonctionsTests" dans BaseTests.js
- Le chargement ou l'actualisation de l'application lance les tests
## Fonctions du module Test(BaseTest.js):
- **Test.elementExiste**({   
    **selecteur**: '.menu-burger-icon',  
    **msgOk**: `- L'élement existe !`,   
    **msgEr**: `. L'élement n'existe pas !`   
  })   
  . selecteur = Prend les sélecteurs css (text/string).  
  . msgOk = Text affiché si l'élément existe (optionel).  
  . msgEr = Text affiché si l'élément n'existe pas (optionel).  
  msgOk et msgEr sont créés et affichés automatiquement si non renseignés !   



- **Test.elementExistePas**({   
    **selecteur**: '.menu-burger-icon',   
    **msgOk**: `- L'élement existe pas!`,   
    **msgEr**: `. L'élement existe !`   
  })   
  . selecteur = Prend les sélecteurs css (text/string).  
  . msgOk = Text affiché si l'élément n'existe pas (optionel).  
  . msgEr = Text affiché si l'élément existe (optionel).  
  msgOk et msgEr sont créés et affichés automatiquement si non renseignés !   

  
- **Test.textElementEgal**({   
    **selecteur**: '.menu-burger-icon',  
    **valeur**: 'hahah',
    **msgOk**: `- L'élement est égale à "hahah" !`,   
    **msgEr**: `. L'élement n'est pas égale à "hahah" !`   
  })   
  . selecteur = Prend les sélecteurs css (text/string).  
  . valeur = Text à comparer à l'élément provenant du innerHtml du "selecteur" 
  . msgOk = Text affiché si l'élément est égal (optionel).  
  . msgEr = Text affiché si l'élément n'est pas égal (optionel).  
  msgOk et msgEr sont créés et affichés automatiquement si non renseignés !   


- **Test.numElementEgal**({   
    **selecteur**: '.menu-burger-icon',  
    **valeur**: 5.5,
    **msgOk**: `- Le nombre est égal à 5.5 !`,   
    **msgEr**: `. Le nombre n'est pas égal à 5.5 !`   
  })   
  . selecteur = Prend les sélecteurs css (text/string).  
  . valeur = nombre à comparer à l'élément provenant du innerHtml du "selecteur"   
             converti en nombre flotant.
  . msgOk = Text affiché si l'élément est égal (optionel).  
  . msgEr = Text affiché si l'élément n'est pas égal (optionel).  
  msgOk et msgEr sont créés et affichés automatiquement si non renseignés !   


- **Test.elementVide**({   
    **selecteur**: '.menu-burger-icon',
    **msgOk**: `- L'élément est vide !`,   
    **msgEr**: `. L'élément n'est pas vide !`   
  })   
  . selecteur = Prend les sélecteurs css (text/string).  
  . msgOk = Text affiché si l'élément est vide (optionel).  
  . msgEr = Text affiché si l'élément n'est pas vide (optionel).  
  msgOk et msgEr sont créés et affichés automatiquement si non renseignés !   


- **Test.elementPasVide**({   
    **selecteur**: '.menu-burger-icon',
    **msgOk**: `- L'élément n'est pas vide !`,   
    **msgEr**: `. L'élément est vide !`   
  })   
  . selecteur = Prend les sélecteurs css (text/string).  
  . msgOk = Text affiché si l'élément n'est pas vide (optionel).  
  . msgEr = Text affiché si l'élément est vide (optionel).  
  msgOk et msgEr sont créés et affichés automatiquement si non renseignés !   


- **Test.elementTextInclut**({   
    **selecteur**: '.menu-burger-icon',
    **valeur**: 'hahah',
    **msgOk**: `- Le text est bien inclus dans l'élément !`,   
    **msgEr**: `. Le text n'est pas inclus dans l'élément !`   
  })   
  . selecteur = Prend les sélecteurs css (text/string).  
  . valeur = Text, test son inclusion dans le text de l'élément provenant
              du innerHtml du "selecteur".
  . msgOk = Text affiché si l'élément n'est pas vide (optionel).  
  . msgEr = Text affiché si l'élément est vide (optionel).  
  msgOk et msgEr sont créés et affichés automatiquement si non renseignés !   


- **Test.elementInclutLesMots**({   
    **selecteur**: '.menu-burger-icon',
    **mots**: ['mot1','mot2',...,'mot10'],
    **msgOk**: `- L'élément inclut bien tous les mots !`,   
    **msgEr**: `. L'élément n'inclut pas tous les mots !`   
  })   
  . selecteur = Prend les sélecteurs css (text/string).  
  . valeur = Tableau de text/string, ces mots sont-ils inclus dans le text
             de l'élément provenant du innerHtml du "selecteur".
  . msgOk = Text affiché si tous les mots sont inclus (optionel).  
  . msgEr = Text affiché si tous les mots ne sont pas inclus  (optionel).  
  msgOk et msgEr sont créés et affichés automatiquement si non renseignés !   

## bd
### git pull en premier (attention)
### récupération deb (à la racine du projet)
- rsync ubuntu@51.210.107.73:/home/ubuntu/RaffinerieProd/TibilletCashlessDev/SaveDb/dumps/raffinerie* SaveDb/
- ls SaveDb
  raffinerie-M0097-2021-10-25-22-05.sql
  . M0097 -> /media/travail/developpement/TibilletCashlessDev/DjangoFiles/APIcashless/migrations/
  . 2021-10-25-22-05 -> date et heure
### Arréter les conteneurs du doosier Docker
- cd Docker
- docker-compose down
### supprimer db en cours (à la racine du projet)
- sudo rm -fr Postgres/dbdata
### relenacer conteneur
- cd Docker
- docker-compose up -d
### Charger la db dans le conteneur
#### entrer dans le conteneur
- dexe cashless_django bash
#### peupler la base 
- load_sql /SaveDb/raffinerie-M0097-2021-10-25-22-05.sql
#### Synchronistaion orm base de données
- mm
#### lancer serveur
- rsp
## bd
### git pull en premier (attention)
### récupération deb
- rsync ubuntu@51.210.107.73:/home/ubuntu/RaffinerieProd/TibilletCashlessDev/SaveDb/dumps/raffinerie* SaveDb/
- ls SaveDb
  raffinerie-M0097-2021-10-25-22-05.sql
  . M0097 -> /media/travail/developpement/TibilletCashlessDev/DjangoFiles/APIcashless/migrations/
  . 2021-10-25-22-05 -> date et heure
### Arréter les conteneurs du doosier Docker
- cd Docker
- docker-compose down
### supprimer db en cours
- sudo rm -fr Postgres/dbdata/
### relenacer conteneur
- cd Docker
- docker-compose up -d
### Charger la db dans le conteneur
#### entrer dans le conteneur
- dexe cashless_django bash
#### peupler la base 
- load_sql /SaveDb/raffinerie-M0097-2021-10-25-22-05.sql
#### Synchronistaion orm base de données
- mm
#### lancer serveur
- rsp
