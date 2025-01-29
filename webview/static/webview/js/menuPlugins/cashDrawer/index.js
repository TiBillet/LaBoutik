import { isCordovaApp, bluetoothOpenCashDrawer } from '../../modules/mobileDevice.js'

window.cashDrawerInterface = async function () {
  console.log('Bt ouvrir caisse cliquer !')
  await bluetoothOpenCashDrawer()
}

export const menu = {
  func: "cashDrawerInterface", // fonction à lancer
  icon: "fas fa-key", // icon, font awesome 5
  i8nIndex: "cashDrawer,uppercase" // text traduit à partir de .../modules/languages/*
}
