

---

````md
# Telegram Channel Post Creator 🤖📢

A web-based tool to create and publish **Telegram channel posts** using a bot that is already an admin.  
Supports **text posts, image posts, and unlimited inline buttons** with a clean UI.

🔗 **Live Demo:**  
https://make-admin-lovat.vercel.app/

---

## 🚀 Features

- Send **text messages** to Telegram channels
- Send **image posts with captions**
- Add **unlimited inline buttons** (dynamic button builder)
- Supports `@channelusername` and numeric `-100xxxxxxxxxx` chat IDs
- Works for both **channels and supergroups**
- Clean, responsive UI using Bootstrap
- Handles Telegram API quirks correctly (no keyboard parse errors)

---

## 🛠️ Tech Stack

- **Backend:** Python, Flask  
- **Frontend:** HTML, Bootstrap 5, JavaScript  
- **API:** Telegram Bot API  

---

## 📋 Requirements

- Python 3.8+
- A Telegram bot created via `@BotFather`
- Bot must be **admin** in the target channel with:
  - Post Messages permission

---

## ⚙️ Installation & Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/mhdashikofficial/make-admin.git
   cd make-admin
````

2. **Install dependencies**

   ```bash
   pip install flask requests
   ```

3. **Run the application**

   ```bash
   python app.py
   ```

4. Open your browser and visit:

   ```
   http://127.0.0.1:5000
   ```

---

## 🧪 How to Use

1. Enter your **Bot Token**
2. Enter **Chat ID** or **@channelusername**
3. Write your message or caption
4. (Optional) Upload an image
5. Add **one or more inline buttons**
6. Click **Send Post**

The post will be published instantly in your Telegram channel.

---

## ⚠️ Telegram Limits & Notes

* Image caption limit: **1024 characters**
* Inline buttons:

  * Max 8 buttons per row
  * Max 100 buttons total
* URLs must be valid and preferably HTTPS
* Bot must have posting rights

---

## 🔒 Security Notes

* Bot token is never stored
* No database usage
* Runs entirely on user input and Telegram API

---

## 📌 Live Deployment

This project is deployed and live at:

👉 [https://make-admin-lovat.vercel.app/](https://make-admin-lovat.vercel.app/)

---

## 👤 Author

**Coded by:**
[@alexanderthegreatxx](https://t.me/alexanderthegreatxx)

GitHub: [https://github.com/mhdashikofficial](https://github.com/mhdashikofficial)

---

## 📄 License

This project is provided for educational and personal use.
Feel free to fork and modify, but please keep the credits intact.

```

---

If you want, I can also:
- Add badges (Python, Flask, Telegram)
- Write a stricter license
- Add screenshots section
- Optimize it for GitHub SEO

Just say it.
```
