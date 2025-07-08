import tkinter as tk
from tkinter import scrolledtext, messagebox
import requests
from bs4 import BeautifulSoup
import random
import time

def get_text_only(url):
    # Mimic a real browser
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        )
    }
    # Add a small random delay to avoid being flagged as a bot
    time.sleep(random.uniform(1.2, 2.7))
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

def fetch_and_display():
    url = url_entry.get()
    if not url.startswith("http"):
        url = "http://" + url
    output_text.delete(1.0, tk.END)
    try:
        text = get_text_only(url)
        output_text.insert(tk.END, text)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load page:\n{e}")

root = tk.Tk()
root.title("Webpage Text Extractor")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

tk.Label(frame, text="Enter URL:").pack(side=tk.LEFT)
url_entry = tk.Entry(frame, width=50)
url_entry.pack(side=tk.LEFT, padx=5)
tk.Button(frame, text="Fetch Text", command=fetch_and_display).pack(side=tk.LEFT)

output_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=80, height=30)
output_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

root.mainloop()