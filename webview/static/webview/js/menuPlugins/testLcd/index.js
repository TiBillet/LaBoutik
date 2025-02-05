import { bluetoothLcd } from '../../modules/mobileDevice.js'

window.testLcdInterface = async function () {
  // efface le menu
  document.querySelector('#menu-burger-conteneur').classList.remove('burger-show')
  console.log('test lcd')
  const result = await bluetoothLcd()
  console.log('result =', result)
}

export const menu = {
  func: "testLcdInterface", // fonction à lancer
  icon: "fas fa-cube", // icon, font awesome 5
  i8nIndex: "testLcd,uppercase", // text traduit à partir de .../modules/languages/*
  conditions: ['hasSunmiPrinter']
}
