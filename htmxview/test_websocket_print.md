# Test impression sous sunmi:
## Lancer un environnement de dev en htts
## Ajouter l'appareil sunmi## infos
Soit un domain "tibillet.org"

## client browser
https://tibillet.org/htmx/tuto_js/print/

Cliquer sur le bouton "Send" (pas besoin de renseigner le input) lancera la commande
sur le sunmi (v2 ou d3mini)

## client sunmi
- L'url est codé en dur pour le sunmi dans le fichier points_ventes.js
`wss://${window.location.host}/ws/tuto_js/print/`

- Le client websocket attend un message parsé en Json (ligne 57):  
{
  'message': 'print',
  'data': ticket,
  'user': "test"
}

- La variable dat.message = 'print' lance l'impression (ligne 29)

## Attention
Le code spécifiant l'impression que pour les sunmi n'est pas encore créé.
