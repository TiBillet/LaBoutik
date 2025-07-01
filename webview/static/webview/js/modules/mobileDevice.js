// source : https://github.com/don/BluetoothSerial?tab=readme-ov-file
// source : https://github.com/NielsLeenheer/ReceiptPrinterEncoder/tree/main

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
    window.bluetoothSerial.enable(
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

export async function bluetoothSerialAvailable() {
  return await new Promise((resolve) => {
    try {
      window.bluetoothSerial.available(() => {
        // console.log('-> bluetoothSerialAvailable =  succès')
        resolve(true)
      }, () => {
        // console.log('-> bluetoothSerialAvailable =  no')
        resolve(false)
      })
    } catch (error) {
      resolve(false)
    }
  })
}



export async function bluetoothGetMacAddress(name) {
  let retour = 'unknown'
  const testBluetoothSerialAvailable = await bluetoothSerialAvailable()
  // console.log('testBluetoothSerialAvailable =', testBluetoothSerialAvailable)

  if (testBluetoothSerialAvailable) {
    const list = await new Promise((resolve) => {
      // list devices
      window.bluetoothSerial.list(function (devices) {
        resolve(devices)
      }, (error) => {
        console.log('error =', error);
        resolve([])
      });
    })

    for (let i = 0; i < list.length; i++) {
      const device = list[i];
      if (device.name === name) {
        retour = device.id
        break
      }
    }
  }
  return retour
}

async function loadImage(url) {
  const load = await new Promise((resolve) => {
    try {
      let img = new Image()
      img.src = url
      img.onload = () => {
        resolve(img)
      }
    } catch (error) {
      console.log('-> loadAndConvertImageToB64,', error)
      resolve(null)
    }
  })
  return load
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
    window.bluetoothSerial.connect(macAddress, async (result) => {
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
export async function bluetoothIsConnected() {
  const test = await new Promise((resolve) => {
    window.bluetoothSerial.isConnected(() => {
      resolve(true)
    }, (error) => {
      resolve(false)
    })
  })
  return test
}


async function bluetoothSerialWrite(contentToWrite) {
  const write = await new Promise((resolve) => {
    window.bluetoothSerial.write(contentToWrite, () => {
      resolve(true)
    }, (error) => {
      resolve(false)
      console.log(`-> bluetoothSerialWrite, error = ${error}`)
    })
  })
  return write
}

export async function bluetoothDisconnect() {
  const disconnect = await new Promise((resolve) => {
    window.bluetoothSerial.disconnect(() => {
      resolve(true)
    }, (error) => {
      resolve(false)
      console.log(`-> bluetoothDisconnect, error = ${error}`)
    })
  })
  return disconnect
}

export async function bluetoothConnection() {
  const connection = await new Promise((resolve) => {
    async function tryConnection () {
      let connect = false
      console.log('-> bluetoothConnection -', new Date())

      const macAddress = await bluetoothGetMacAddress("InnerPrinter")
      const isConnected = await bluetoothIsConnected()

      if (isConnected === false) {
        connect = await bluetoothConnect(macAddress)
        resolve(connect)
      } else {
        connect = true
        resolve(connect)
      }
      // tentative de reconnexion après 2 secondes
      if (connect === false) {
        setTimeout(tryConnection, 2 * 1000)
      }
    }
    tryConnection()
  })
  return connection
}


/**
 * Print command
 * @param {String} currentPrintUuid 
 */
export async function bluetoothWrite(currentPrintUuid) {
  const currentPrint = sunmiPrintQueue.find(queue => queue.printUuid === currentPrintUuid)
  const content = currentPrint.content

  // 2 - interprets and print
  await bluetoothConnection()
  console.log('-> Après bluetoothConnection')

  // columns: 48
  let encoder = new ReceiptPrinterEncoder({
    imageMode: 'raster',
    columns: 48
  })

  let result = encoder.initialize().font('A')

  // process data
  for (let i = 0; i < content.length; i++) {
    const line = content[i]

    // image
    if (line.type === 'image') {
      const image = await loadImage(line.value)
      result.image(image, 64, 64, 'atkinson')
    }

    // text
    if (line.type === 'text') {
      result.line(line.value)
    }

    // ligne horizontale
    if (line.type === 'line') {
      result.rule(line.value)
    }


    // barcode
    if (line.type === 'barcode') {
      result.barcode(line.value, 'EAN13', {
        height: 100,
        text: true
      })
    }

    // qrcode
    if (line.type === 'qrcode') {
      result.qrcode(line.value)
    }

    // size: 1 - 8
    if (line.type === 'size') {
      result.size(line.value + 1)
    }

    // align left/center/right
    if (line.type === 'align') {
      result.align(line.value)
    }

    // font A/B/C
    if (line.type === 'font') {
      result.font(line.value)
    }

    // bold 0/1 
    if (line.type === 'bold') {
      if (line.value === 0) {
        result.bold(false)
      }
      if (line.value === 1) {
        result.bold(true)
      }
    }

    if (line.type === 'invert') {
      if (line.value === 0) {
        result.invert(false)
      }
      if (line.value === 1) {
        result.invert(true)
      }
    }

    // feed number
    if (line.type === 'feed') {
      for (let i = 0; i < line.value; i++) {
        result.line('')
      }
    }

    // cut
    if (line.type === 'cut') {
      result.cut()
    }
  }

  const rPrint = await bluetoothSerialWrite(result.encode())
  console.log('-> bluetoothSerialWrite status print =', rPrint)

  // 3 - enlever l'impression faite de la queue d'impression
  if (rPrint) {
    sunmiPrintQueue = sunmiPrintQueue.filter(queue => queue.printUuid !== currentPrintUuid)
  }

  // 4 - boucler sur la queue d'impression si non vide
  if (sunmiPrintQueue.length > 0) {
    await bluetoothWrite(sunmiPrintQueue[0])
  }

  // pour la gestion d'une queue d'impression, il est indispenssable de déconneté le bluetooth à la fin
  await bluetoothDisconnect()
  return rPrint
}

export async function bluetoothOpenCashDrawer() {
  await bluetoothConnection()

  let encoder = new ReceiptPrinterEncoder()
  const data = encoder.raw([0x10, 0x14, 0x00, 0x00, 0x00]).encode()

  const state = await bluetoothSerialWrite(data)
  await bluetoothDisconnect()
  return state
}
