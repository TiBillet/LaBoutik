#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for Sunmi Cloud NT311 Printer
This script demonstrates how to connect to and print with a Sunmi Cloud NT311 printer.

Application: Application101217
AppID: 154b0530286044779df5554b51623940
AppKey: 7036da4938c546c59e7773e90bf41956
"""

import time
import sys
import os
import traceback
from dotenv import load_dotenv
from sunmi_cloud_printer import SunmiCloudPrinter, ALIGN_CENTER, ALIGN_LEFT, HRI_POS_BELOW

# Load environment variables from .env file
load_dotenv()

def check_dependencies():
    """Check if all required dependencies are installed."""
    try:
        import requests
        import numpy
        from PIL import Image
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install required packages with:")
        print("pip install requests numpy pillow")
        return False

def print_hello_world(printer):
    """Print a simple Hello World message."""
    print("Creating Hello World receipt...")

    # Add header
    printer.lineFeed()
    printer.setAlignment(ALIGN_CENTER)
    printer.setPrintModes(True, True, False)  # Bold, double height, normal width
    printer.appendText("*** HELLO WORLD ***\n")
    printer.setPrintModes(False, False, False)  # Reset print modes
    printer.appendText("------------------------\n")

    # Add content
    printer.setAlignment(ALIGN_CENTER)
    printer.appendText("Hello, World!\n")
    printer.lineFeed()

    # Cut the paper
    printer.lineFeed(3)
    printer.cutPaper(False)  # Partial cut

    # Generate a unique trade number for this print job
    trade_no = f"{printer._printer_sn}_{int(time.time())}"

    # Send the print job to the printer
    print(f"Sending Hello World to printer {printer._printer_sn}...")
    try:
        printer.pushContent(
            trade_no=trade_no,
            sn=printer._printer_sn,
            count=1,
            media_text="Hello World"
        )
        print("Print job sent successfully!")
        return True
    except Exception as e:
        print(f"Error sending print job: {e}")
        traceback.print_exc()
        return False

def print_test_receipt(printer):
    """Print a test receipt with various formatting options."""
    # Create a simple test receipt
    print("Creating test receipt...")

    # Add header
    printer.lineFeed()
    printer.setAlignment(ALIGN_CENTER)
    printer.setPrintModes(True, True, False)  # Bold, double height, normal width
    printer.appendText("*** TEST RECEIPT ***\n")
    printer.setPrintModes(False, False, False)  # Reset print modes
    printer.appendText("Sunmi Cloud NT311 Printer\n")
    printer.appendText("------------------------\n")

    # Add content
    printer.setAlignment(ALIGN_LEFT)
    printer.appendText("Date: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
    printer.appendText("Application: Application101217\n")
    printer.appendText("\n")
    printer.appendText("This is a test receipt to verify\n")
    printer.appendText("that your Sunmi Cloud Printer is\n")
    printer.appendText("working correctly.\n")
    printer.appendText("\n")

    # Add QR code
    printer.setAlignment(ALIGN_CENTER)
    printer.appendQRcode(5, 1, "https://developer.sunmi.com")
    printer.lineFeed()

    # Add barcode
    printer.appendBarcode(HRI_POS_BELOW, 100, 2, 73, "12345678")
    printer.lineFeed()

    # Add footer
    printer.appendText("Thank you for testing!\n")

    # Cut the paper
    printer.lineFeed(3)
    printer.cutPaper(False)  # Partial cut

    # Generate a unique trade number for this print job
    trade_no = f"{printer._printer_sn}_{int(time.time())}"

    # Send the print job to the printer
    print(f"Sending print job to printer {printer._printer_sn}...")
    try:
        printer.pushContent(
            trade_no=trade_no,
            sn=printer._printer_sn,
            count=1,
            media_text="Test Receipt"
        )
        print("Print job sent successfully!")

        # Check print status (optional)
        print("Checking print status...")
        printer.printStatus(trade_no)
        return True

    except Exception as e:
        print(f"Error sending print job: {e}")
        traceback.print_exc()
        return False

def check_printer_status(printer):
    """Check if the printer is online and return its status."""
    print(f"Checking if printer {printer._printer_sn} is online...")
    try:
        printer.onlineStatus(printer._printer_sn)
        print("Printer status check completed. If no error was shown, the printer should be online.")
        return True
    except Exception as e:
        print(f"Error checking printer status: {e}")
        traceback.print_exc()
        return False

def main():
    # Check if dependencies are installed
    if not check_dependencies():
        return

    # The serial number of your printer
    # You can provide it as a command-line argument or enter it when prompted
    if len(sys.argv) > 1:
        printer_sn = sys.argv[1]
        print(f"Using printer SN from command line: {printer_sn}")
    else:
        printer_sn = input("Enter your printer's serial number (SN) or press Enter to use default: ")

    if not printer_sn:
        # Get default SN from environment variable or use empty string
        default_sn = os.getenv('PRINTER_SN', "")  # e.g., "N411245U00123"

        if default_sn:
            printer_sn = default_sn
            print(f"Using default printer SN: {printer_sn}")
        else:
            print("No SN provided. Please check your printer for its serial number.")
            return

    # Create a printer instance with 384 dots per line (standard for 80mm thermal printer)
    # Get APP_ID and APP_KEY from environment variables
    app_id = os.getenv('APP_ID')
    app_key = os.getenv('APP_KEY')

    try:
        printer = SunmiCloudPrinter(384, app_id=app_id, app_key=app_key, printer_sn=printer_sn)
    except ValueError as e:
        print(f"Error: {e}")
        print("Please make sure APP_ID, APP_KEY, and PRINTER_SN are set in the .env file.")
        return

    # Display menu
    while True:
        print("\n=== Sunmi Cloud Printer Test Menu ===")
        print("1. Check printer status")
        print("2. Print test receipt")
        print("3. Print Hello World")
        print("4. Clear print jobs")
        print("5. Send notification sound")
        print("6. Exit")

        choice = input("\nEnter your choice (1-6): ")

        if choice == '1':
            # Check printer status
            check_printer_status(printer)

        elif choice == '2':
            # First check if printer is online
            if check_printer_status(printer):
                # Print test receipt
                if print_test_receipt(printer):
                    print("\nTest completed. Check your printer for the test receipt.")

        elif choice == '3':
            # Print Hello World
            if check_printer_status(printer):
                if print_hello_world(printer):
                    print("\nHello World printed successfully. Check your printer.")

        elif choice == '4':
            # Clear print jobs
            try:
                print(f"Clearing print jobs for printer {printer._printer_sn}...")
                printer.clearPrintJob(printer._printer_sn)
                print("Print jobs cleared successfully!")
            except Exception as e:
                print(f"Error clearing print jobs: {e}")
                traceback.print_exc()

        elif choice == '5':
            # Send notification sound
            try:
                print(f"Sending notification sound to printer {printer._printer_sn}...")
                printer.pushVoice(
                    sn=printer._printer_sn,
                    content="New order",
                    cycle=3,  # Play 3 times
                    interval=2,  # 2 seconds between plays
                    expire_in=60  # Expire after 60 seconds
                )
                print("Notification sound sent successfully!")
            except Exception as e:
                print(f"Error sending notification sound: {e}")
                traceback.print_exc()

        elif choice == '6':
            print("Exiting...")
            break

        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
