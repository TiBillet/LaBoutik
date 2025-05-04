# Sunmi Cloud NT311 Printer Integration

This directory contains scripts for integrating with the Sunmi Cloud NT311 printer.

## Files

- `sunmi_cloud_printer.py`: The main library file that provides the `SunmiCloudPrinter` class with all printer functionality
- `test_sunmi_printer.py`: A test script to verify connectivity and functionality with your Sunmi printer

## Prerequisites

Before using these scripts, make sure you have:

1. A Sunmi Cloud NT311 printer
2. The printer's Serial Number (SN)
3. The required Python dependencies:
   - requests
   - numpy
   - pillow (PIL)
   - python-dotenv

You can install the dependencies with:

```bash
pip install requests numpy pillow python-dotenv
```

## Configuration

The scripts use environment variables for configuration. A `.env` file is provided with the following default values:

- Application: Application101217
- AppID: 154b0530286044779df5554b51623940
- AppKey: 7036da4938c546c59e7773e90bf41956
- Printer SN: N411245U00527

You can modify the `.env` file to use your own credentials and printer serial number:

```
# Required - Your Sunmi Cloud Printer credentials
APP_ID=1234
APP_KEY=12345

# Optional - Your printer's serial number
PRINTER_SN=N1234
```

The scripts will automatically load these values from the `.env` file. Note that APP_ID and APP_KEY are required for the printer to function. If they are not provided in the .env file or as parameters when creating the SunmiCloudPrinter instance, an error will be raised.

## Using the Test Script

The test script provides a simple way to verify that your printer is working correctly.

### Running the Script

```bash
python test_sunmi_printer.py [PRINTER_SN]
```

Where `[PRINTER_SN]` is your printer's serial number (optional, you can also enter it when prompted).

### Features

The test script provides the following options:

1. **Check printer status**: Verify if your printer is online and connected
2. **Print test receipt**: Send a test receipt to the printer with various formatting options
3. **Print Hello World**: Print a simple Hello World message
4. **Clear print jobs**: Clear any pending print jobs from the queue
5. **Send notification sound**: Send a notification sound to the printer
6. **Exit**: Exit the script

### Setting the Printer SN

You must set your printer's serial number in the `.env` file:

1. Open the `.env` file in the epsonprinter directory
2. Find the line with `PRINTER_SN=N411245U00527`
3. Replace the value with your printer's SN, e.g., `PRINTER_SN=N411245U00123`

The PRINTER_SN is required for the printer to function. If it is not provided in the .env file or as a parameter when creating the SunmiCloudPrinter instance, an error will be raised.

## Integration into Your Application

To integrate the Sunmi Cloud Printer into your own application:

1. Import the necessary modules:
   ```python
   import os
   from dotenv import load_dotenv
   from sunmi_cloud_printer import SunmiCloudPrinter

   # Load environment variables from .env file
   load_dotenv()
   ```

2. Create a printer instance:
   ```python
   # Get APP_ID, APP_KEY, and PRINTER_SN from environment variables
   app_id = os.getenv('APP_ID')
   app_key = os.getenv('APP_KEY')
   printer_sn = os.getenv('PRINTER_SN')

   # Create printer instance with APP_ID, APP_KEY, and PRINTER_SN
   printer = SunmiCloudPrinter(384, app_id=app_id, app_key=app_key, printer_sn=printer_sn)  # 384 dots per line for 80mm printer
   ```

   Note: If APP_ID, APP_KEY, or PRINTER_SN are not provided as parameters and not found in the .env file, a ValueError will be raised.

3. Format your receipt using the various methods:
   ```python
   printer.appendText("Hello, World!\n")
   printer.lineFeed()
   ```

4. Send the print job to the printer:
   ```python
   printer.pushContent(
       trade_no=f"{printer._printer_sn}_{int(time.time())}",
       sn=printer._printer_sn,
       count=1,
       media_text="Receipt"
   )
   ```

## Documentation

For more details on the Sunmi Cloud Printer API, refer to the official documentation:
https://developer.sunmi.com/docs/en-US/xeghjk491/fmqeghjk513

## Troubleshooting

If you encounter issues:

1. Make sure your printer is powered on and connected to the internet
2. Verify that the SN you're using is correct
3. Check that the Application, AppID, and AppKey are correctly configured
4. Look for error messages in the console output
5. Try clearing the print jobs and trying again
