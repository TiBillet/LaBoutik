// source : https://github.com/NielsLeenheer/EscPosEncoder
// https://github.com/NielsLeenheer/EscPosEncoder/blob/v2.1.0/README.md
//import EscPosEncoder from './esc-pos-encoder.esm.js'
import ReceiptPrinterEncoder from './receipt-printer-encoder.esm.js'

/**
 * Cordova add
 * @module ./modules/mobileDevice.js
 */


/**
 * read a file an convert it in Json object
 * @public
 * @param {string} pathToFile - path file to read
 * @returns {JSON | null}
 */
export async function cordovaReadFileJson(pathToFile) {
  // console.log('-> cordovaReadFileJson, pathToFile =', pathToFile)
  const promiseReadFromFile = new Promise((resolve) => {
    try {
      window.resolveLocalFileSystemURL(pathToFile, function (fileEntry) {
        fileEntry.file(function (file) {
          const reader = new FileReader()
          reader.onloadend = function (e) {
            resolve(JSON.parse(this.result))
          }
          reader.readAsText(file)
        }, () => { resolve(null) })
      }, () => { resolve(null) })
    } catch (error) {
      console.log('-> cordovaReadFromFile,', error)
      resolve(null)
    }
  })
  return await promiseReadFromFile
}


/**
 * Write configuration file
 * @param {string} basePath - path
 * @param {string} saveFileName - file name
 * @param {object} rawData - content file
 * @returns {boolean}
 */
export async function cordovaWriteToFile(basePath, saveFileName, rawData) {
  // console.log('-> writeToFile, saveFileName =', saveFileName, '  --  basePath =', basePath)
  const data = JSON.stringify(rawData)

  const promiseWiteToFile = new Promise((resolve) => {
    window.resolveLocalFileSystemURL(basePath, function (directoryEntry) {
      directoryEntry.getFile(saveFileName, { create: true },
        function (fileEntry) {
          fileEntry.createWriter(function (fileWriter) {
            fileWriter.onwriteend = function (e) {
              // console.log('info , write of file "' + saveFileName + '" completed.')
              resolve(true)
            }
            fileWriter.onerror = function (e) {
              // you could hook this up with our global error handler, or pass in an error callback
              console.log('info, write failed: ' + e.toString())
            }
            const blob = new Blob([data], { type: 'text/plain' })
            fileWriter.write(blob)
          }, () => { resolve(false) })
        }, () => { resolve(false) })
    }, () => { resolve(false) })
  })
  return await promiseWiteToFile
}

/**
 * Is cordova application ?
 * @public
 * @returns {boolean}
 */
export function isCordovaApp() {
  try {
    if (cordova) {
      return true
    }
  } catch (error) {
    return false
  }
}

export async function enableBluetooth() {
  return await new Promise((resolve, reject) => {
    bluetoothSerial.enable(
      function () {
        console.log("Bluetooth is enabled");
        resolve(true)
      },
      function () {
        console.log("The user did *not* enable Bluetooth");
        reject(false)
      }
    );
  })

}

export async function bluetoothGetMacAddress(name) {
  let retour = 'unknown'
  const list = await new Promise((resolve, reject) => {
    // list devices
    bluetoothSerial.list(function (devices) {
      resolve(devices)
    }, (error) => {
      console.log('error =', error);
      reject(error)
    });
  })

  for (let i = 0; i < list.length; i++) {
    const device = list[i];
    if (device.name === name) {
      retour = device.id
      break
    }
  }
  return retour
}


export function bluetoothWriteText(msg) {
  let encoder = new ReceiptPrinterEncoder({
    language: 'esc-pos',
    columns: 48,
    feedBeforeCut: 4
  })

  let result = encoder
    .initialize()
    .text('------ test 3 -----')
    .box({ width: 30, align: 'left', style: 'double', marginLeft: 0 },'The quick brown fox jumps over the lazy dog')
    .newline()
    .qrcode('https://tibillet.org/')
    .newline()
    .barcode('313063057461', 'ean13', {
      height: 100,
      text: true
    })
    .newline()
    .newline()
    .raw([0x1d, 0x56, 0x42])
    .encode()

  console.log('impression =', result);
  bluetoothSerial.write(result, (status) => {
    console.log('-> bluetoothWriteText, success:', status)
    bluetoothDisconnect()
  }, (error) => {
    console.log('-> bluetoothWriteText,error :', error)
  });
}

export function bluetoothWrite(content) {
  let encoder = new ReceiptPrinterEncoder({
    language: 'esc-pos',
    columns: 48,
    feedBeforeCut: 4
  })

    let result = encoder
    .initialize()
    .text(content)
    .newline()
    .encode()


  console.log('-> bluetoothWrite, impression =', content);
  bluetoothSerial.write(result, (status) => {
    console.log('-> bluetoothWriteText, success:', status)
    bluetoothDisconnect()
  }, (error) => {
    console.log('-> bluetoothWriteText,error :', error)
  });
}


export function bluetoothDisconnect() {
  bluetoothSerial.disconnect((success) => {
    console.log('-> bluetoothDisconnect, success:', success)
  }, (error) => {
    console.log('-> bluetoothDisconnect,error :', error)
  })
}