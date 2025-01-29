// source : https://github.com/don/BluetoothSerial?tab=readme-ov-file
// source : https://github.com/neodynamic/js-escpos-builder

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


async function loadAndConvertImageToB64(url) {
  const load = await new Promise((resolve) => {
    try {
      let img = new Image()
      img.src = url
      img.onload = () => {
        let canvas = document.createElement('canvas')
        let ctx = canvas.getContext('2d')
        canvas.height = img.naturalHeight;
        canvas.width = img.naturalWidth;
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        const base64String = canvas.toDataURL('image/png')
        resolve(base64String)
      }
    } catch (error) {
      console.log('-> loadAndConvertImageToB64,', error)
      resolve(null)
    }
  })
  return load
}

async function escPosImageLoad(url) {
  return await new Promise(async (resolve) => {
    try {
      const escpos = Neodynamic.JSESCPOSBuilder
      const imageB64 = await loadAndConvertImageToB64(url)
      escpos.ESCPOSImage.load(imageB64).then(image => {
        resolve(image)
      })
    } catch (error) {
      console.log('-> EscPosImageLoad,', error)
      resolve(null)
    }
  })
}

/**
 * async bluetooth connect
 * @param {string} macAddress 
 * @returns 
 */
async function bluetoothConnect(macAddress) {
  const test = await new Promise((resolve) => {
    bluetoothSerial.connect(macAddress, async (result) => {
      resolve(true)
    }, (error) => {
      resolve(false)
      console.log(`-> bluetoothConnect, error = ${error}`)
    })
  })
  return test
}
/**
 * async bluetooth is connected
 */
async function bluetoothIsConnected() {
  const test = await new Promise((resolve) => {
    bluetoothSerial.isConnected(() => {
      resolve(true)
    }, (error) => {
      resolve(false)
      console.log(`-> bluetoothIsConnected, error = ${error}`)
    })
  })
  return test
}


async function bluetoothSerialWrite(contentToWrite) {
  const write = await new Promise((resolve) => {
    bluetoothSerial.write(contentToWrite, () => {
      resolve(true)
    }, (error) => {
      resolve(false)
      console.log(`-> bluetoothSerialWrite, error = ${error}`)
    })
  })
  return write
}


async function bluetoothDisconnect() {
  const disconnect = await new Promise((resolve) => {
    bluetoothSerial.disconnect(() => {
      resolve(true)
    }, (error) => {
      resolve(false)
      console.log(`-> bluetoothDisconnect, error = ${error}`)
    })
  })
  return disconnect
}

/**
 * Print command, largeur impression max par ligne = 32 caractères
 * @param {Array} content 
 */
export async function bluetoothWrite(content) {
  let connect = null
  const macAddress = await bluetoothGetMacAddress("InnerPrinter")
  console.log('macAddress =', macAddress)

  const isConnected = await bluetoothIsConnected()
  console.log('bluetoothIsConnected =', isConnected)

  if (isConnected !== true) {
    connect = await bluetoothConnect(macAddress)
    console.log('bluetoot connect =', connect)
  }

  const escpos = Neodynamic.JSESCPOSBuilder
  const escposCommands = new escpos.Document()
  // fonte par défaut
  escposCommands.font(escpos.FontFamily.A)
  window.escpos = escpos  // dev
  // process data
  for (let i = 0; i < content.length; i++) {
    const line = content[i]
    let readLineType = false // pour le dev

    // image
    if (line.type === 'image') {
      const image = await escPosImageLoad(line.value)
      escposCommands.image(image, escpos.BitmapDensity.D24)
      readLineType = true
    }

    // text
    if (line.type === 'text') {
      escposCommands.text(line.value)
      readLineType = true
    }

    // barcode
    if (line.type === 'barcode') {
      escposCommands.linearBarcode(line.value, escpos.Barcode1DType.EAN13, new escpos.Barcode1DOptions(2, 100, true, escpos.BarcodeTextPosition.Below, escpos.BarcodeFont.A))
      readLineType = true
    }

    // qrcode
    if (line.type === 'qrcode') {
      escposCommands.qrCode(line.value, new escpos.BarcodeQROptions(escpos.QRLevel.L, 6))
      readLineType = true
    }

    // size
    if (line.type === 'size') {
      escposCommands.size(line.value, line.value)
      readLineType = true
    }

    // align
    if (line.type === 'align') {
      let result = escpos.TextAlignment.Center
      if (line.value === "left") {
        result = escpos.TextAlignment.LeftJustification
      }
      if (line.value === "right") {
        result = escpos.TextAlignment.RightJustification
      }
      escposCommands.align(result)
      readLineType = true
    }

    // font
    if (line.type === 'font') {
      if (line.value === "A") {
        escposCommands.font(Neodynamic.JSESCPOSBuilder.FontFamily.A)
      }
      if (line.value === "B") {
        escposCommands.font(Neodynamic.JSESCPOSBuilder.FontFamily.B)
      }
      if (line.value === "C") {
        escposCommands.font(Neodynamic.JSESCPOSBuilder.FontFamily.C)
      }
      readLineType = true
    }

    /* ne fonctionne pas
     // bold
     if (line.type === 'bold') {
      if (line.value === 1) {
        console.log('-> bold =', escpos.FontStyle.Bold)
        
        escposCommands.style([escpos.FontStyle.Bold])
      } else {
        escposCommands.style([])
      }
      readLineType = true
    }
    */

    // feed
    if (line.type === 'feed') {
      escposCommands.feed(line.value)
      readLineType = true
    }

    // cut
    if (line.type === 'cut') {
      escposCommands.cut()
      readLineType = true
    }

    if (readLineType === false) {
      console.log('-> Todo: line =', line)
    }
  }

  const result = escposCommands.generateUInt8Array()

  const state = bluetoothSerialWrite(result)
  console.log('impression =', await state)
  await bluetoothDisconnect()
}

export async function bluetoothOpenCashDrawer() {
  let connect = null
  const macAddress = await bluetoothGetMacAddress("InnerPrinter")
  console.log('macAddress =', macAddress)

  const isConnected = await bluetoothIsConnected()
  console.log('bluetoothIsConnected =', isConnected)

  if (isConnected !== true) {
    connect = await bluetoothConnect(macAddress)
    console.log('bluetoot connect =', connect)
  }

  console.log('-> bluetoothOpenCashDrawer !')
  let data = new Uint8Array(5)
  data[0] = 0x10
  data[1] = 0x14
  data[2] = 0x00
  data[3] = 0x00
  data[4] = 0x00
  bluetoothSerial.write(data, (success) => {
    console.log('cash drawer open!')
    // efface le menu
    document.querySelector('#menu-burger-conteneur').classList.remove('burger-show')
  }, (error) => {
    console.log('bluetoothSerial.write :', error)
  })

  await bluetoothDisconnect()
}