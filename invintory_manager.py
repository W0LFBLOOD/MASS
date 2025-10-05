import os
import re
import numpy as np
import cv2
from mss import mss
import pytesseract
import keyboard
import pyautogui
import winsound
import csv
import requests
import tkinter as tk
from ctypes import windll
import time
import threading

root = tk.Tk()
root.attributes('-topmost', True)      # Always on top
root.config(bg='black')                # Background to match transparency color
root.overrideredirect(True)            # Removes window border/title bar
root.geometry("600x120+800+50")       # Size and position

# Create the text label
text_var = tk.StringVar(value="Overlay Active")
label = tk.Label(root, textvariable=text_var, fg="lime", bg="black", font=("Arial", 18))
label.pack(padx=10, pady=10)


# Make window click-through
hwnd = windll.user32.GetParent(root.winfo_id())
# 0x20 = WS_EX_TRANSPARENT | 0x80000 = WS_EX_LAYERED
windll.user32.SetWindowLongW(hwnd, -20, 0x20 | 0x80000)

response = requests.get(f"https://api.uexcorp.uk/2.0/marketplace_averages_all")

if response.ok:
    data = response.json()
else:
    print(f"Error: {response.status_code}")
    print(response.text)
    raise Exception("Failed to fetch data from API")

def abbreviate_number(num, decimals=1):
    """
    Convert a number into a human-readable abbreviated form.
    Example: 1234 -> '1.2K', 1234567 -> '1.2M'
    """
    # Handle negative numbers
    if num is None:
        return "no transactions"
    sign = '-' if num < 0 else ''
    num = abs(num)

    # Define suffixes for thousands, millions, etc.
    suffixes = ['', 'K', 'M', 'B', 'T', 'P', 'E']

    # Determine magnitude
    if num < 1000:
        return f"{sign}{num}"

    magnitude = 0
    while num >= 1000 and magnitude < len(suffixes) - 1:
        num /= 1000.0
        magnitude += 1

    # Format with the given number of decimals
    formatted = f"{num:.{decimals}f}".rstrip('0').rstrip('.')
    return f"{sign}{formatted}{suffixes[magnitude]}"


# Define region of interest (replace with your coordinates)
ROI = {
    "top": 120,
    "left": 1460,
    "width": 320,
    "height": 170,
}

def extract_before_volume(text):
    """
    Return everything before the first line containing 'Volume:'.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    collected = []
    for line in lines:
        if re.search(r'\bVolume[:=]', line, re.IGNORECASE):
            return "\n".join(collected), line
        collected.append(line)
    return None, None  # no Volume: found

def main_loop():
    cap = mss()
    items = {"amount": 0 , "buy price": None, "sell price": None}
    print("Scanning ROI for text before 'Volume:'... Press Ctrl+C to stop.")
    volume_line = None
    
    while not keyboard.is_pressed("e"):
        if not volume_line:
            text_var.set("searching for item...")
        sct_img = np.array(cap.grab(ROI))
        frame = cv2.cvtColor(sct_img, cv2.COLOR_BGRA2BGR)

        text = pytesseract.image_to_string(frame, config="--oem 3 --psm 6")

        before, volume_line = extract_before_volume(text)
        if volume_line:
            if "Capacity:" in before:
                before = before.split("\nCapacity:")[0]
            if "\n" in before:
                before = before.replace("\n", " ").strip()
            for item in data["data"]:
                        if before in item["item_name"]:
                            buyPrice= abbreviate_number(item["price_buy"])
                            sellPrice = abbreviate_number(item["price_sell"])
                            break
                        else:
                            buyPrice= "no data found"
                            sellPrice = "no data found"
            strToPrint = f"Item: {before}\nBuy Price: {buyPrice}\nSell Price: {sellPrice}"
            text_var.set(strToPrint)
            if keyboard.is_pressed("b"):
                winsound.PlaySound(".\\Quack_Sound_Effect.wav", winsound.SND_FILENAME)

                #format string to remove noise
                if before in items:
                    items[before]["amount"] += 1
                    print("added "+ before)
                    for item in data["data"]:
                        if item["item_name"] in items:
                            items[item["item_name"]]["buy price"] = item["price_buy"]
                            items[item["item_name"]]["sell price"] = item["price_sell"]


                # Small delay so it doesn’t print multiple times on one press
                text_var.set("item added: " + before)


    winsound.PlaySound(".\\Quack_Sound_Effect.wav", winsound.SND_FILENAME)
    text_var.set("exit key pressed\nsaving to csv...")

    with open('mycsvfile.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['item', 'amount', "buy price", "sell price"])  # Write header
        for key, value in items.items():
            if value:
                writer.writerow([key, value["amount"], value["buy price"], value["sell price"]])
    text_var.set("done")
    os._exit(0)
    

if __name__ == "__main__":
    threading.Thread(target=main_loop, daemon=True).start()
    root.mainloop()