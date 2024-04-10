const TOKEN_DEBUG = '$a;b2yuMkog45ghe54@4!cd'
const SOCKET_DEBUG = io(SOCKET_DEBUG_ADRESSE , {
  transports: ['websocket'],
  query: 'token=' + TOKEN_DEBUG
})

SOCKET_DEBUG.on('connect_error', (error) => {
  console.error('Socket.io : ',error)
})

window.onerror = function (msg, url, noLigne, noColonne, erreur) {
  let message = `
      <div>Message : ${msg}</div>
      <div>URL : ${ url }</div>
      <div>Ligne : ${ noLigne }</div>
      <div>Colonne : ${ noColonne }</div>
      <div>Objet Error : ${ JSON.stringify(erreur) }</div>
  `
  SOCKET_DEBUG.emit('logErreur', message)
  return true
}
