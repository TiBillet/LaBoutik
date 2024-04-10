window.addEventListener('DOMContentLoaded', () => {
  // Pour bloquer l'actualisation de la page préparation lors des tests(glob.testPagePrepa === true)
  window.testPagePrepa = false
  // tableau contenant des méthodes à exécuter après le rendu html
  window.methods_after_render = []

  // charge un script qui importe un/des module(s)
  let elementScript = document.createElement("script")
  elementScript.src ='http://django-local.org:8001/static/webview/electron_proj1/insertModuleTests.js'
  document.head.appendChild(elementScript)
  console.log('site en visu !')
  // login
  if (document.querySelector('#login-form')) {
    document.querySelector('#id_username').value = 'rootsuperpowerofthedead'
    document.querySelector('#id_password').value = 'f5quei3eiNgiu0ahT1moor.oo2ohquoe'
    document.querySelector('#login-form .submit-row input').click()
  }
})