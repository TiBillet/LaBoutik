# -*- coding: utf-8 -*-

import hashlib
import hmac
import json
import numpy as np
import numpy.typing as npt
import os
import random
import requests
import time
from typing import Any, Dict, List, Tuple
from PIL import Image
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

ALIGN_LEFT  : int = 0
ALIGN_CENTER: int = 1
ALIGN_RIGHT : int = 2

HRI_POS_ABOVE: int = 1
HRI_POS_BELOW: int = 2

DIFFUSE_DITHER  : int = 0
THRESHOLD_DITHER: int = 2

COLUMN_FLAG_BW_REVERSE: int = 1 << 0
COLUMN_FLAG_BOLD      : int = 1 << 1
COLUMN_FLAG_DOUBLE_H  : int = 1 << 2
COLUMN_FLAG_DOUBLE_W  : int = 1 << 3

def unicode_to_utf8(unicode: int) -> bytes:
    if unicode <= 0x7f:
        n = unicode & 0x7f
        return n.to_bytes(1, 'big')
    if unicode >= 0x80 and unicode <= 0x7ff:
        n  = (((unicode >> 6) & 0x1f) | 0xc0) << 8
        n |= (((unicode     ) & 0x3f) | 0x80)
        return n.to_bytes(2, 'big')
    if unicode >= 0x800 and unicode <= 0xffff:
        n  = (((unicode >> 12) & 0x0f) | 0xe0) << 16
        n |= (((unicode >> 6 ) & 0x3f) | 0x80) << 8
        n |= (((unicode      ) & 0x3f) | 0x80)
        return n.to_bytes(3, 'big')
    if unicode >= 0x010000 and unicode <= 0x10ffff:
        n  = (((unicode >> 18) & 0x07) | 0xf0) << 24
        n |= (((unicode >> 12) & 0x3f) | 0x80) << 16
        n |= (((unicode >> 6 ) & 0x3f) | 0x80) << 8
        n |= (((unicode      ) & 0x3f) | 0x80)
        return n.to_bytes(4, 'big')
    return b''

class SunmiCloudPrinter:

    def __init__(self, dots_per_line: int, app_id: str = None, app_key: str = None, printer_sn: str = None) -> None:
        self._DOTS_PER_LINE: int = dots_per_line
        self._charHSize: int = 1
        self._asciiCharWidth: int = 12
        self._cjkCharWidth: int = 24
        self._orderData: bytes = b''
        self._columnSettings: List[Tuple[int, ...]] = []

        # Get APPID & APPKEY from parameters or environment variables
        self._app_id = app_id or os.getenv('APP_ID')
        self._app_key = app_key or os.getenv('APP_KEY')
        self._printer_sn = printer_sn or os.getenv('PRINTER_SN')

        # Raise error if APP_ID or APP_KEY is not provided
        if not self._app_id or not self._app_key:
            raise ValueError("APP_ID and APP_KEY must be provided either as parameters or in the .env file")

        # Raise error if PRINTER_SN is not provided
        if not self._printer_sn:
            raise ValueError("PRINTER_SN must be provided either as a parameter or in the .env file")

        random.seed()

    @property
    def DOTS_PER_LINE(self) -> int:
        return self._DOTS_PER_LINE

    @property
    def orderData(self) -> bytes:
        return self._orderData

    def clear(self) -> None:
        self._orderData = b''

    def widthOfChar(self, c: int) -> int:
        if (c >= 0x00020 and c <= 0x0036f):
            return self._asciiCharWidth
        if (c >= 0x0ff61 and c <= 0x0ff9f):
            return self._cjkCharWidth // 2
        if (c == 0x02010                 ) or \
           (c >= 0x02013 and c <= 0x02016) or \
           (c >= 0x02018 and c <= 0x02019) or \
           (c >= 0x0201c and c <= 0x0201d) or \
           (c >= 0x02025 and c <= 0x02026) or \
           (c >= 0x02030 and c <= 0x02033) or \
           (c == 0x02035                 ) or \
           (c == 0x0203b                 ):
            return self._cjkCharWidth
        if (c >= 0x01100 and c <= 0x011ff) or \
           (c >= 0x02460 and c <= 0x024ff) or \
           (c >= 0x025a0 and c <= 0x027bf) or \
           (c >= 0x02e80 and c <= 0x02fdf) or \
           (c >= 0x03000 and c <= 0x0318f) or \
           (c >= 0x031a0 and c <= 0x031ef) or \
           (c >= 0x03200 and c <= 0x09fff) or \
           (c >= 0x0ac00 and c <= 0x0d7ff) or \
           (c >= 0x0f900 and c <= 0x0faff) or \
           (c >= 0x0fe30 and c <= 0x0fe4f) or \
           (c >= 0x1f000 and c <= 0x1f9ff):
            return self._cjkCharWidth
        if (c >= 0x0ff01 and c <= 0x0ff5e) or \
           (c >= 0x0ffe0 and c <= 0x0ffe5):
            return self._cjkCharWidth
        return self._asciiCharWidth

    def generateSign(self, body: str, timestamp: str, nonce: str) -> str:
        msg: str = body + self._app_id + timestamp + nonce
        return hmac.new(key=self._app_key.encode('utf-8'), msg=msg.encode('utf-8'), digestmod=hashlib.sha256).hexdigest()

    def httpPost(self, path: str, body: Dict[str, Any]) -> str:
        url: str = 'https://openapi.sunmi.com' + path
        timestamp: str = str(int(time.time()))
        nonce: str = '{:06d}'.format(random.randint(0, 999999))
        body_data: str = json.dumps(obj=body, ensure_ascii=False)

        headers: Dict[str, str] = {}
        headers['Sunmi-Appid'] = self._app_id
        headers['Sunmi-Timestamp'] = timestamp
        headers['Sunmi-Nonce'] = nonce
        headers['Sunmi-Sign'] = self.generateSign(body_data, timestamp, nonce)
        headers['Source'] = 'openapi'
        headers['Content-Type'] = 'application/json'

        response: requests.Response = requests.post(url=url, data=body_data.encode('utf-8'), headers=headers)
        print(json.loads(response.text))
        return response.text

    def bindShop(self, sn: str, shop_id: int) -> None:
        body: Dict[str, Any] = {}
        body['sn'] = sn
        body['shop_id'] = shop_id
        self.httpPost('/v2/printer/open/open/device/bindShop', body)

    def unbindShop(self, sn: str, shop_id: int) -> None:
        body: Dict[str, Any] = {}
        body['sn'] = sn
        body['shop_id'] = shop_id
        self.httpPost('/v2/printer/open/open/device/unbindShop', body)

    def onlineStatus(self, sn: str) -> None:
        body: Dict[str, Any] = {}
        body['sn'] = sn
        self.httpPost('/v2/printer/open/open/device/onlineStatus', body)

    def clearPrintJob(self, sn: str) -> None:
        body: Dict[str, Any] = {}
        body['sn'] = sn
        self.httpPost('/v2/printer/open/open/device/clearPrintJob', body)

    def pushVoice(self, sn: str, content: str, cycle: int = 1, interval: int = 2, expire_in: int = 300) -> None:
        body: Dict[str, Any] = {}
        body['sn'] = sn
        body['content'] = content
        body['cycle'] = cycle
        body['interval'] = interval
        body['expire_in'] = expire_in
        self.httpPost('/v2/printer/open/open/device/pushVoice', body)

    def pushContent(self, trade_no: str, sn: str, count: int, order_type: int = 1, media_text: str = '', cycle: int = 1) -> None:
        body: Dict[str, Any] = {}
        body['trade_no'] = trade_no
        body['sn'] = sn
        body['order_type'] = order_type
        body['content'] = self._orderData.hex()
        body['count'] = count
        body['media_text'] = media_text
        body['cycle'] = cycle
        self.httpPost('/v2/printer/open/open/device/pushContent', body)

    def printStatus(self, trade_no: str) -> None:
        body: Dict[str, Any] = {}
        body['trade_no'] = trade_no
        self.httpPost('/v2/printer/open/open/ticket/printStatus', body)

    def newTicketNotify(self, sn: str) -> None:
        body: Dict[str, Any] = {}
        body['sn'] = sn
        self.httpPost('/v2/printer/open/open/ticket/newTicketNotify', body)

    ##################################################
    # Basic ESC/POS Commands
    ##################################################

    # Append raw data.
    def appendRawData(self, data: bytes) -> None:
        self._orderData += data

    # Append unicode character.
    def appendUnicode(self, unicode: int, count: int) -> None:
        if count > 0:
            self._orderData += unicode_to_utf8(unicode) * count

    # Append text.
    def appendText(self, text: str) -> None:
        self._orderData += text.encode(encoding='utf-8', errors='ignore')

    # [LF] Print data in the buffer and feed lines.
    def lineFeed(self, n: int = 1) -> None:
        if n > 0:
            self._orderData += b'\x0a' * n

    # [ESC @] Restore default settings.
    def restoreDefaultSettings(self) -> None:
        self._charHSize = 1
        self._orderData += b'\x1b\x40'

    # [ESC 2] Restore default line spacing.
    def restoreDefaultLineSpacing(self) -> None:
        self._orderData += b'\x1b\x32'

    # [ESC 3] Set line spacing.
    def setLineSpacing(self, n: int) -> None:
        if n >= 0 and n <= 255:
            self._orderData += b'\x1b\x33' + n.to_bytes(1, 'little')

    # [ESC !] Set print modes.
    def setPrintModes(self, bold: bool, double_h: bool, double_w: bool) -> None:
        n = 0
        if bold:
            n |= 8
        if double_h:
            n |= 16
        if double_w:
            n |= 32
            self._charHSize = 2
        else:
            self._charHSize = 1
        self._orderData += b'\x1b\x21' + n.to_bytes(1, 'little')

    # [GS !] Set character size.
    def setCharacterSize(self, h: int, w: int) -> None:
        n = 0
        if h >= 1 and h <= 8:
            n |= (h - 1)
        if w >= 1 and w <= 8:
            n |= (w - 1) << 4
            self._charHSize = w
        self._orderData += b'\x1d\x21' + n.to_bytes(1, 'little')

    # [HT] Jump to next TAB position.
    def horizontalTab(self, n: int) -> None:
        if n > 0:
            self._orderData += b'\x09' * n

    # [ESC $] Set absolute print position.
    def setAbsolutePrintPosition(self, n: int) -> None:
        if n >= 0 and n <= 65535:
            self._orderData += b'\x1b\x24' + n.to_bytes(2, 'little')

    # [ESC \] Set relative print position.
    def setRelativePrintPosition(self, n: int) -> None:
        if n >= -32768 and n <= 32767:
            self._orderData += b'\x1b\x5c' + n.to_bytes(2, 'little')

    # [ESC a] Set alignment.
    def setAlignment(self, n: int) -> None:
        if n >= 0 and n <= 2:
            self._orderData += b'\x1b\x61' + n.to_bytes(1, 'little')

    # [ESC -] Set underline mode.
    def setUnderlineMode(self, n: int) -> None:
        if n >= 0 and n <= 2:
            self._orderData += b'\x1b\x2d' + n.to_bytes(1, 'little')

    # [GS B] Set black-white reverse mode.
    def setBlackWhiteReverseMode(self, enabled: bool) -> None:
        if enabled:
            self._orderData += b'\x1d\x42\x01'
        else:
            self._orderData += b'\x1d\x42\x00'

    # [ESC {] Set upside down mode.
    def setUpsideDownMode(self, enabled: bool) -> None:
        if enabled:
            self._orderData += b'\x1b\x7b\x01'
        else:
            self._orderData += b'\x1b\x7b\x00'

    # [GS V m] Cut paper.
    def cutPaper(self, full_cut: bool) -> None:
        if full_cut:
            self._orderData += b'\x1d\x56\x30'
        else:
            self._orderData += b'\x1d\x56\x31'

    # [GS V m n] Postponed cut paper.
    # Upon receiving this command, the printer will not perform the cut until
    # (d + n) dot lines are fed, where d is the distance between the print position
    # and the cut position.
    def postponedCutPaper(self, full_cut: bool, n: int) -> None:
        if n >= 0 and n <= 255:
            if full_cut:
                self._orderData += b'\x1d\x56\x61'
            else:
                self._orderData += b'\x1d\x56\x62'
            self._orderData += n.to_bytes(1, 'little')

    ##################################################
    # Sunmi Proprietary Commands
    ##################################################

    # Set CJK encoding (effective when UTF-8 mode is disabled).
    #   n  encoding
    # ---  --------
    #   0  GB18030
    #   1  BIG5
    #  11  Shift_JIS
    #  12  JIS 0208
    #  21  KS C 5601
    # 128  Disable CJK mode
    # 255  Restore to default
    def setCjkEncoding(self, n: int) -> None:
        if n >= 0 and n <= 255:
            self._orderData += b'\x1d\x28\x45\x03\x00\x06\x01' + n.to_bytes(1, 'little')

    # Set UTF-8 mode.
    #   n  mode
    # ---  ----
    #   0  Disabled
    #   1  Enabled
    # 255  Restore to default
    def setUtf8Mode(self, n: int) -> None:
        if n >= 0 and n <= 255:
            self._orderData += b'\x1d\x28\x45\x03\x00\x06\x03' + n.to_bytes(1, 'little')

    # Set Latin character size of vector font.
    def setHarfBuzzAsciiCharSize(self, n: int) -> None:
        if n >= 0 and n <= 255:
            self._asciiCharWidth = n
            self._orderData += b'\x1d\x28\x45\x03\x00\x06\x0a' + n.to_bytes(1, 'little')

    # Set CJK character size of vector font.
    def setHarfBuzzCjkCharSize(self, n: int) -> None:
        if n >= 0 and n <= 255:
            self._cjkCharWidth = n
            self._orderData += b'\x1d\x28\x45\x03\x00\x06\x0b' + n.to_bytes(1, 'little')

    # Set other character size of vector font.
    def setHarfBuzzOtherCharSize(self, n: int) -> None:
        if n >= 0 and n <= 255:
            self._orderData += b'\x1d\x28\x45\x03\x00\x06\x0c' + n.to_bytes(1, 'little')

    # Select font for Latin characters.
    #     n  font
    # -----  ----
    #     0  Built-in lattice font
    #     1  Built-in vector font
    # >=128  The (n-128)th custom vector font
    def selectAsciiCharFont(self, n: int) -> None:
        if n >= 0 and n <= 255:
            self._orderData += b'\x1d\x28\x45\x03\x00\x06\x14' + n.to_bytes(1, 'little')

    # Select font for CJK characters.
    #     n  font
    # -----  ----
    #     0  Built-in lattice font
    #     1  Built-in vector font
    # >=128  The (n-128)th custom vector font
    def selectCjkCharFont(self, n: int) -> None:
        if n >= 0 and n <= 255:
            self._orderData += b'\x1d\x28\x45\x03\x00\x06\x15' + n.to_bytes(1, 'little')

    # Select font for other characters.
    #     n  font
    # -----  ----
    #   0,1  Built-in vector font
    # >=128  The (n-128)th custom vector font
    def selectOtherCharFont(self, n: int) -> None:
        if n >= 0 and n <= 255:
            self._orderData += b'\x1d\x28\x45\x03\x00\x06\x16' + n.to_bytes(1, 'little')

    # Set print density.
    def setPrintDensity(self, n: int) -> None:
        if n >= 0 and n <= 255:
            self._orderData += b'\x1d\x28\x45\x02\x00\x07' + n.to_bytes(1, 'little')

    # Set print speed.
    def setPrintSpeed(self, n: int) -> None:
        if n >= 0 and n <= 255:
            self._orderData += b'\x1d\x28\x45\x02\x00\x08' + n.to_bytes(1, 'little')

    # Set cutter mode.
    # n  mode
    # -  ----
    # 0  Perform full-cut or partial-cut according to the cutting command
    # 1  Perform partial-cut always on any cutting command
    # 2  Perform full-cut always on any cutting command
    # 3  Never cut on any cutting command
    def setCutterMode(self, n: int) -> None:
        if n >= 0 and n <= 255:
            self._orderData += b'\x1d\x28\x45\x02\x00\x10' + n.to_bytes(1, 'little')

    # Clear paper-not-taken alarm.
    def clearPaperNotTakenAlarm(self) -> None:
        self._orderData += b'\x1d\x28\x54\x01\x00\x04'

    ##################################################
    # Print in Columns
    ##################################################

    def setupColumns(self, columns: Tuple[Tuple[int, ...], ...]) -> None:
        self._columnSettings = []
        remain: int = self._DOTS_PER_LINE
        for col in columns:
            width: int = col[0]
            alignment: int = col[1]
            flag: int = col[2]
            if width == 0 or width > remain:
                width = remain
            self._columnSettings.append((width, alignment, flag))
            remain -= width
            if remain == 0:
                return

    def printInColumns(self, texts: Tuple[str, ...]) -> None:
        if not self._columnSettings or not texts:
            return

        strcur: List[str] = []
        strrem: List[str] = []
        strwidth: List[int] = []
        num_of_columns: int = min(len(self._columnSettings), len(texts))

        for i in range(num_of_columns):
            strcur.append('')
            strrem.append(texts[i])
            strwidth.append(0)

        while True:
            done = True
            pos = 0

            for i in range(num_of_columns):
                width = self._columnSettings[i][0]
                alignment = self._columnSettings[i][1]
                flag = self._columnSettings[i][2]

                if not strrem[i]:
                    pos += width
                    continue

                done = False
                strcur[i] = ''
                strwidth[i] = 0
                j = 0
                while j < len(strrem[i]):
                    c = ord(strrem[i][j])
                    if c == ord('\n'):
                        j += 1
                        break
                    else:
                        w = self.widthOfChar(c) * self._charHSize
                        if flag & COLUMN_FLAG_DOUBLE_W:
                            w *= 2
                        if strwidth[i] + w > width:
                            break
                        else:
                            strcur[i] += chr(c)
                            strwidth[i] += w
                    j += 1
                if j < len(strrem[i]):
                    strrem[i] = strrem[i][j:]
                else:
                    strrem[i] = ''

                if alignment == 1:
                    self.setAbsolutePrintPosition(pos + (width - strwidth[i]) // 2)
                elif alignment == 2:
                    self.setAbsolutePrintPosition(pos + (width - strwidth[i]))
                else:
                    self.setAbsolutePrintPosition(pos)
                if flag & COLUMN_FLAG_BW_REVERSE:
                    self.setBlackWhiteReverseMode(True)
                if flag & (COLUMN_FLAG_BOLD | COLUMN_FLAG_DOUBLE_H | COLUMN_FLAG_DOUBLE_W):
                    bold = True if flag & COLUMN_FLAG_BOLD else False
                    double_h = True if flag & COLUMN_FLAG_DOUBLE_H else False
                    double_w = True if flag & COLUMN_FLAG_DOUBLE_W else False
                    self.setPrintModes(bold, double_h, double_w)
                self.appendText(strcur[i])
                if flag & (COLUMN_FLAG_BOLD | COLUMN_FLAG_DOUBLE_H | COLUMN_FLAG_DOUBLE_W):
                    self.setPrintModes(False, False, False)
                if flag & COLUMN_FLAG_BW_REVERSE:
                    self.setBlackWhiteReverseMode(False)
                pos += width

            if not done:
                self.lineFeed()
            else:
                break

    ##################################################
    # Barcode & QR Code Printing
    ##################################################

    # Append a barcode.
    def appendBarcode(self, hri_pos: int, height: int, module_size: int, barcode_type: int, text: str) -> None:
        text_length = len(text)

        if text_length == 0:
            return
        if text_length > 255:
            text_length = 255
        if height < 1:
            height = 1
        elif height > 255:
            height = 255
        if module_size < 1:
            module_size = 1
        elif module_size > 6:
            module_size = 6

        hri_pos &= 3

        self._orderData += b'\x1d\x48' + hri_pos.to_bytes(1, 'little')
        self._orderData += b'\x1d\x66\x00'
        self._orderData += b'\x1d\x68' + height.to_bytes(1, 'little')
        self._orderData += b'\x1d\x77' + module_size.to_bytes(1, 'little')
        self._orderData += b'\x1d\x6b' + barcode_type.to_bytes(1, 'little') + text_length.to_bytes(1, 'little')
        self._orderData += text.encode(encoding='utf-8', errors='ignore')

    # Append a QR code.
    def appendQRcode(self, module_size: int, ec_level: int, text: str) -> None:
        content = text.encode(encoding='utf-8', errors='ignore')
        text_length = len(content)

        if text_length == 0:
            return
        if text_length > 65535:
            text_length = 65535
        if module_size < 1:
            module_size = 1
        elif module_size > 16:
            module_size = 16
        if ec_level < 0:
            ec_level = 0
        elif ec_level > 3:
            ec_level = 3

        ec_level += 48
        text_length += 3

        self._orderData += b'\x1d\x28\x6b\x04\x00\x31\x41\x00\x00'
        self._orderData += b'\x1d\x28\x6b\x03\x00\x31\x43' + module_size.to_bytes(1, 'little')
        self._orderData += b'\x1d\x28\x6b\x03\x00\x31\x45' + ec_level.to_bytes(1, 'little')
        self._orderData += b'\x1d\x28\x6b' + text_length.to_bytes(2, 'little') + b'\x31\x50\x30'
        self._orderData += content
        self._orderData += b'\x1d\x28\x6b\x03\x00\x31\x51\x30'

    ##################################################
    # Image Printing
    ##################################################

    # Grayscale to monochrome - diffuse dithering algorithm.
    def diffuseDither(self, src_data: npt.NDArray[np.int_], width: int, height: int) -> List[int]:
        if width <= 0 or height <= 0:
            return []

        bmwidth = (width + 7) // 8
        dst_data = [0] * (bmwidth * height)
        line_buffer = np.zeros((2, width), dtype=np.int_) # type: ignore
        line1 = 0
        line2 = 1

        for i in range(width):
            line_buffer[0][i] = 0
            line_buffer[1][i] = src_data[0][i]

        for y in range(height):
            tmp = line1
            line1 = line2
            line2 = tmp
            not_last_line = True if y < height - 1 else False

            if not_last_line:
                for i in range(width):
                    line_buffer[line2][i] = src_data[y + 1][i]

            q = y * bmwidth
            for i in range(bmwidth):
                dst_data[q] = 0
                q += 1

            b1 = 0
            b2 = 0
            q = y * bmwidth
            mask = 0x80

            for x in range(1, width + 1):
                if line_buffer[line1][b1] < 128: # Black pixel
                    err = line_buffer[line1][b1]
                    dst_data[q] |= mask
                else:
                    err = line_buffer[line1][b1] - 255
                b1 += 1
                if mask == 1:
                    q += 1
                    mask = 0x80
                else:
                    mask >>= 1
                e7 = ((err * 7) + 8) >> 4
                e5 = ((err * 5) + 8) >> 4
                e3 = ((err * 3) + 8) >> 4
                e1 = err - (e7 + e5 + e3)
                if x < width:
                    line_buffer[line1][b1] += e7
                if not_last_line:
                    line_buffer[line2][b2] += e5
                    if x > 1:
                        line_buffer[line2][b2 - 1] += e3
                    if x < width:
                        line_buffer[line2][b2 + 1] += e1
                b2 += 1
        return dst_data

    # Grayscale to monochrome - threshold dithering algorithm.
    def thresholdDither(self, src_data: npt.NDArray[np.int_], width: int, height: int) -> List[int]:
        if width <= 0 or height <= 0:
            return []

        bmwidth = (width + 7) // 8
        dst_data = [0] * (bmwidth * height)
        q = 0

        for y in range(height):
            k = q
            mask = 0x80
            for x in range(width):
                if src_data[y][x] < 128: # Black pixel
                    dst_data[k] |= mask
                if mask == 1:
                    k += 1
                    mask = 0x80
                else:
                    mask >>= 1
            q += bmwidth
        return dst_data

    # Convert image pixel data from RGB to grayscale.
    def convertToGray(self, img: Image.Image) -> npt.NDArray[np.int_]:
        width, height = img.size
        data = np.asarray(img) # type: ignore
        gray_data = np.zeros((height, width), dtype=np.int_) # type: ignore
        for y in range(height):
            for x in range(width):
                r = data[y][x][0]
                g = data[y][x][1]
                b = data[y][x][2]
                gray_data[y][x] = ((r * 11 + g * 16 + b * 5) // 32) & 0xff
        return gray_data

    # Append an image.
    def appendImage(self, image_file: str, mode: int = THRESHOLD_DITHER, width: int = 0) -> None:
        try:
            img_org = Image.open(image_file)
        except:
            return

        if width == 0:
            width = self._DOTS_PER_LINE

        w, h = img_org.size
        if w > width:
            h = width * h // w;
            w = width
            img_res = img_org.resize((w, h))
        else:
            img_res = img_org

        gray_data = self.convertToGray(img_res)
        if mode == DIFFUSE_DITHER:
            mono_data = self.diffuseDither(gray_data, w, h)
        elif mode == THRESHOLD_DITHER:
            mono_data = self.thresholdDither(gray_data, w, h)
        else:
            return

        w = (w + 7) // 8
        self._orderData += b'\x1d\x76\x30\x00'
        self._orderData += w.to_bytes(2, 'little')
        self._orderData += h.to_bytes(2, 'little')
        for i in range(len(mono_data)):
            self._orderData += mono_data[i].to_bytes(1, 'little')

    ##################################################
    # Page Mode Commands
    ##################################################

    # [ESC L] Enter page mode.
    def enterPageMode(self) -> None:
        self._orderData += b'\x1b\x4c'

    # [ESC W] Set print area in page mode.
    # x, y: origin of the print area
    # w, h: width and height of the print area
    def setPrintAreaInPageMode(self, x: int, y: int, w: int, h: int) -> None:
        self._orderData += b'\x1b\x57'
        self._orderData += x.to_bytes(2, 'little')
        self._orderData += y.to_bytes(2, 'little')
        self._orderData += w.to_bytes(2, 'little')
        self._orderData += h.to_bytes(2, 'little')

    # [ESC T] Select print direction in page mode.
    # dir: 0:normal; 1:rotate 90-degree clockwise; 2:rotate 180-degree clockwise; 3:rotate 270-degree clockwise
    def setPrintDirectionInPageMode(self, dir: int) -> None:
        if dir >= 0 and dir <= 3:
            self._orderData += b'\x1b\x54' + dir.to_bytes(1, 'little')

    # [GS $] Set absolute vertical print position in page mode.
    def setAbsoluteVerticalPrintPositionInPageMode(self, n: int) -> None:
        if n >= 0 and n <= 65535:
            self._orderData += b'\x1d\x24' + n.to_bytes(2, 'little')

    # [GS \] Set relative vertical print position in page mode.
    def setRelativeVerticalPrintPositionInPageMode(self, n: int) -> None:
        if n >= -32768 and n <= 32767:
            self._orderData += b'\x1d\x5c' + n.to_bytes(2, 'little')

    # [FF] Print data in the buffer and exit page mode.
    def printAndExitPageMode(self) -> None:
        self._orderData += b'\x0c'

    # [ESC FF] Print data in the buffer (and keep in page mode).
    def printInPageMode(self) -> None:
        self._orderData += b'\x1b\x0c'

    # [CAN] Clear data in the buffer (and keep in page mode).
    def clearInPageMode(self) -> None:
        self._orderData += b'\x18'

    # [ESC S] Exit page mode and discard data in the buffer without printing.
    def exitPageMode(self) -> None:
        self._orderData += b'\x1b\x53'

if __name__ == '__main__':
    # Get APP_ID, APP_KEY, and PRINTER_SN from environment variables
    app_id = os.getenv('APP_ID')
    app_key = os.getenv('APP_KEY')
    printer_sn = os.getenv('PRINTER_SN')

    try:
        printer = SunmiCloudPrinter(384, app_id=app_id, app_key=app_key, printer_sn=printer_sn)
    except ValueError as e:
        print(f"Error: {e}")
        print("Please make sure APP_ID, APP_KEY, and PRINTER_SN are set in the .env file.")
        exit(1)

    printer.lineFeed()

    printer.setLineSpacing(80)
    printer.setPrintModes(True, True, False)
    printer.setAlignment(ALIGN_CENTER)
    printer.appendText('*** 打印测试 ***\n')

    printer.restoreDefaultLineSpacing()
    printer.setPrintModes(False, False, False)
    printer.setAlignment(ALIGN_LEFT)

    printer.setupColumns((
        (96 , ALIGN_LEFT  , 0),
        (144, ALIGN_CENTER, 0),
        (0  , ALIGN_RIGHT , COLUMN_FLAG_BW_REVERSE),
    ))
    printer.printInColumns(('商品名称', '数量\n(单位：随意)', '小计\n(单位：元)'))
    printer.lineFeed()
    printer.printInColumns(('这是\"一个很长的品名\"', 'x1000', '￥2020.99'))
    printer.lineFeed()
    printer.printInColumns(('橙子', '【备注：赠品购物满1,000,000元送一只】', '￥0.00'))
    printer.lineFeed()

    printer.setAlignment(ALIGN_CENTER)

    printer.appendBarcode(HRI_POS_BELOW, 160, 3, 73, 'Abc-000789')
    printer.lineFeed()

    printer.appendQRcode(5, 1, 'https://docs.sunmi.com/docking-debugging/商米云打印机合作伙伴对接说明/1-了解一下对接流程/')
    printer.lineFeed()

    printer.setAlignment(ALIGN_LEFT)

    # Print in page mode
    printer.setAlignment(ALIGN_CENTER)
    printer.appendText('---- 页模式多区域打印 ----\n')
    printer.setAlignment(ALIGN_LEFT)
    printer.enterPageMode()
    # Area 1
    printer.setPrintAreaInPageMode(0, 0, 144, 500)
    printer.setPrintDirectionInPageMode(0)
    printer.appendText('永和九年，岁在癸丑，暮春之初，会于会稽山阴之兰亭，修禊事也。群贤毕至，少长咸集。' +
        '此地有崇山峻岭，茂林修竹；又有清流激湍，映带左右，引以为流觞曲水，列坐其次。\n')
    # Area 2
    printer.setPrintAreaInPageMode(156, 0, 144, 500)
    printer.setPrintDirectionInPageMode(2)
    printer.appendText('鎌倉アナウンサーはまず流暢な中国語でアナウンサーとしての豊富な経験を紹介されました。\n')
    # Area 3
    printer.setPrintAreaInPageMode(312, 0, 72, 500)
    printer.setPrintDirectionInPageMode(3)
    printer.appendText('Scarlett is a woman who can deal with a nation at war, Atlanta burning.\n')
    # Print and exit page mode
    printer.printAndExitPageMode()

    printer.lineFeed(4)
    printer.cutPaper(False)

    printer.pushContent(
        trade_no=f"{printer._printer_sn}_{int(time.time())}",
        sn=printer._printer_sn,
        count=1,
        media_text='您有新的订单')
