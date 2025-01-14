<div align="center">
  <img src="https://raw.githubusercontent.com/izzleton/imagehosting/refs/heads/main/TotoMagic.jpg" alt="TOTO Magic Logo" width="120" />
  
  <h1>TOTO Magic </h1>
  <strong>Bringing the magic of a fortune-telling arcade machine to Telegram & the cloud 🎩</strong>
</div>

---

## Table of Contents
- [✨ Overview](#1--overview)
- [⚙ Features](#2--features)
- [🚀 Architecture](#3--architecture)
- [🛠 Technical Stack](#4--technical-stack)
- [☁ AWS Services Used](#5--aws-services-used)
- [📦 Installation & Setup](#6--installation--setup)
  - [Requirements](#requirements)
  - [Steps](#steps)
- [🧪 Testing](#7--testing-instructions)
- [🤖 Amazon Q Usage](#8--amazon-q-developer-usage)
- [🤝 Contributing](#9--contributing)
- [📜 License](#9--contributing)

---

## 1. ✨ Overview 
**TOTO Magic** is a **Telegram-based mini app** designed to replicate the excitement of vintage arcade fortune machines—infused with **modern gameplay elements** and viral social sharing elements. It lives inside Telegram as a WebApp, letting users:

- **Authenticate seamlessly** via Telegram  
- **Make Wishes** for daily rewards, fortunes, and achievements  
- **Invite Friends** to earn extra rewards via a referral system  
- **Explore** leaderboards, quests, ads-based reward options, and more  

Our broader vision is an ecosystem (the **Lilypad arcade**) where **TOTO Magic** is the gateway to a growing suite of blockchain-enabled mini games and interactive experiences.

---

## 2. ⚙ Features
1. **Daily Wishes & Rewards**  
   Players get up to 3 wishes every 8 hours—earning fortunes and coin rewards.

2. **Referral Bonuses**  
   Invite a friend, both get a bonus. Organic community growth through word-of-mouth.

3. **Social Quests**  
   Earn **one-time large coin rewards** and **extra wishes** for quests like joining partner mini apps, following the project X account, or engaging on social media.

4. **Ads Integration**  
   Watch up to 3 ads per day for extra wishes (max 3 daily).

5. **User Growth & Leaderboards**  
   Ranks top players by their coin balance, fostering friendly competition.

---

## 3. 🚀 Architecture
```plaintext
                       Telegram Mini App (HTML / CSS / JS)
                                       |
                            [Theming + Inline Mode]
                                       |
                          ┌─────────────────────────┐
                          │    AWS Load Balancer    │
                          │ (ALB/ELB distributing   │
                          │    incoming traffic)    │
                          └────────────┬────────────┘
                                       │
                         ┌─────────────┴─────────────┐
                         │        AWS Firewall       │
                         │   (WAF / Security Groups) │
                         └─────────────┬─────────────┘
                                       │
                          ┌────────────┴────────────┐
                          │       Nginx Reverse     │
                          │        Proxy Layer       │
                          └────────────┬────────────┘
                                       │
                      ┌────────────────┴────────────────┐
                      │  Gunicorn + Flask + systemd     │
                      │   (Python-based server on EC2)  │
                      └────────────────┬────────────────┘
                                       │
                                ┌──────┴──────┐
                                │   MySQL DB   │
                                │(AWS-hosted or│
                                │ on the same  │
                                │    EC2)      │
                                └──────────────┘
```
Key Points in This Diagram:

**AWS Load Balancer**: Accepts inbound traffic (HTTP/HTTPS) from Telegram, distributes to your EC2 instance(s).
**AWS Firewall (WAF/Security Groups)**: Filters or restricts traffic at L7 or IP/port level.
**MySQL DB**: Stores user data (wishes, referrals, balances). May live on the same EC2 or a dedicated AWS RDS MySQL instance.
**Telegram WebApp**: Inline usage, theme sync  
**Flask**: Python framework for server logic  
**Gunicorn & systemd**: Reliable process management on AWS EC2  
**Nginx**: Reverse proxy for security, SSL termination, load balancing  

---

## 4. 🛠 Technical Stack
- **Frontend**: HTML5, CSS3, vanilla JavaScript (integrated with Telegram Web Apps)  
- **Backend**: Python + Flask + Gunicorn + systemd on Linux (Amazon EC2)  
- **Database**: MySQL (replaced SQLite due to concurrency and scaling)  
- **Cloud**: AWS for hosting (EC2) + Nginx reverse proxy (for the Lilypad host to connect to cPanel) 
- **Dev Tool**: Amazon Q Developer (Visual Studio Code extension) for code suggestions & security improvements  

---

## 5. ☁ AWS Services Used
- **Amazon EC2**  
  Hosting for Flask app, MySQL DB, ensuring reliability under high concurrency.  
- **Amazon Q Developer**  
  Seamless code analysis in Visual Studio. Alerts for concurrency and potential security flaws.  
- **AWS Load Balancer (ALB/ELB)**
  Distributes inbound traffic from Telegram (or the open Internet) across multiple EC2 instances
  Provides health checks, can terminate HTTPS, and route traffic to Nginx
  - **AWS WAF**
(Web Application Firewall) for L7 security or Security Groups for inbound/outbound rule sets.
Filters malicious requests, helps block suspicious IP ranges, ensures only allowed ports (e.g., 80/443) are open.
- **Elastic IP**
A static, public IPv4 address you can attach to your EC2 instance if you want a stable address for direct access or debugging.
---

## 6. 📦 Installation & Setup

### Requirements
- Python 3.9+
- MySQL 5.7+ (or higher)
- Telegram Bot Token (`BOT_TOKEN`)
- AWS or local environment (e.g., an Amazon EC2 instance)

### Steps

1. **Clone the Repo**  
   ```
   git clone https://github.com/YourUserName/TOTO-Magic.git
   cd TOTO-Magic
   ```
2. **Create Virtual Env & Install Requirements**
   
After cloning the repository in **Step 1**, proceed with environment setup and dependency installation:

Step 2: Create a virtual environment
```
python3 -m venv venv
```
 Activate your virtual environment (Linux/macOS)
 ```
source venv/bin/activate
```
 On Windows, use:
 ```
 .\venv\Scripts\activate
```
 Step 3: Install dependencies
```
pip install -r requirements.txt
```
3. **Environment Variables**

Create an `.env` file in the project root (never commit this file!) containing your **sensitive** info, for example:

```
# .env
BOT_TOKEN="your-telegram-bot-token"
FLASK_SECRET_KEY="your-flask-secret-key"
DB_HOST="localhost"
DB_USER="db_username"
DB_PASSWORD="db_password"
DB_NAME="db_name"
```
**Note:** Keep .env out of version control for security. You should also ensure .env is in your .gitignore. 

 4. **Database Setup**
**MySQL (Recommended)**

Create a database named db_name.
Create a user db_username with password db_password.
Grant privileges, for example:
sql
```
CREATE DATABASE db_name;
CREATE USER 'db_username'@'%' IDENTIFIED BY 'db_password';
GRANT ALL PRIVILEGES ON db_name.* TO 'db_username'@'%';
FLUSH PRIVILEGES;
```
(Optional) Import a .sql schema if provided, or rely on the app’s table-creation logic if it exists.
**SQLite (Prototype Only)**

If your code has fallback logic for SQLite, you can test it locally.
However, concurrency issues may arise under production loads.
5. **Running Locally**
You can run TOTO Magic in development mode with Flask or in a more production-like environment with Gunicorn:

5.1 **Flask Development Server**

1. Activate your virtual environment
```
source venv/bin/activate
```
2. Run the Flask development server
```
python app.py
```
The app will typically listen on http://127.0.0.1:5000 or 0.0.0.0:8000, depending on your config.
5.2 **Gunicorn Production Server**

```
gunicorn app:app --bind 0.0.0.0:8000
```
Gunicorn is recommended for handling concurrency.
Point your browser or Telegram mini app to http://your-server-ip:8000.

6. **Deploying to Production**

6.1 **Systemd + Gunicorn (on AWS EC2 or similar)**

Create a systemd service file, for instance /etc/systemd/system/toto_magic.service:
```
[Unit]
Description=Gunicorn instance to serve TOTO Magic
After=network.target

[Service]
User=ec2-user
Group=www-data
WorkingDirectory=/home/ec2-user/toto_magic
Environment="PATH=/home/ec2-user/toto_magic/venv/bin"
ExecStart=/home/ec2-user/toto_magic/venv/bin/gunicorn app:app --bind 0.0.0.0:8000

[Install]
WantedBy=multi-user.target
Enable and start your service:
```
```
sudo systemctl enable toto_magic.service
sudo systemctl start toto_magic.service
sudo systemctl status toto_magic.service
```
**Configure Nginx** (optional) as a reverse proxy to serve TOTO Magic over ports 80/443 and handle SSL/TLS.

**AWS Firewall/Security Groups** should allow inbound traffic on the relevant ports (e.g., 80 for HTTP, 443 for HTTPS).

---

## 7. 🧪 Testing Instructions

1. **Open Telegram** and locate your bot’s username. Example:  
   [@totomagicbot](https://t.me/totomagicbot)

2. **Start** the bot. Telegram will handle the mini app authentication.

3. **Make a Wish**  
   - Use "Make Wish" button in the inline UI.  
   - Observe if you receive a fortune, coins, or other rewards.

4. **Leaderboards & Shop** (in-progress features)  
   - Check the Leaderboard tab for user rankings and referral counts.  
   - Shop is still under construction but will showcase items or coin usage in future updates.

5. **Invite Friends**  
   - Go to the **Social** tab and click "Invite a Friend."  
   - Confirm you and your friend both receive referral-based rewards.

6. **Monitor Logs** on your server:

       sudo journalctl -u toto_magic.service -f

   Check real-time concurrency or DB logs for potential errors.

7. **Database Verification** (Optional)
   
       USE db_name;
       SELECT * FROM users LIMIT 10;

   Verify correct user data, balances, referrals, etc.

---

## 8. 🤖 Amazon Q Developer Usage

To improve code quality and security, we integrated **Amazon Q** into our development workflow as a plugin in Visual Studio Code:

- **Real-time Scans**: Amazon Q spots concurrency pitfalls (like potential `database locked` states) or missing validations in the referral logic.
- **Security Reviews**: Highlights vulnerabilities such as unsanitized input or potential XSS concerns in any templated output.
- **Refactoring Suggestions**: Encourages best practices and optimizations to keep code readable and secure.

---

## 9. 🤝 Contributing

We welcome contributions from the community. Here’s an example on how to get started:

1. **Fork** the repository on GitHub.
2. **Create a new branch** for your feature or fix:
   
       git checkout -b feature/new-referral-logic

3. **Commit** changes with helpful messages:
   
       git commit -m "Add stricter validation for referral invites"

4. **Push** your branch:
   
       git push origin feature/new-referral-logic

5. **Open a Pull Request** describing your changes. We’ll review and merge if it aligns with the project goals.

Feel free to open **Issues** for bug reports, feature requests, or discussions about potential improvements.

---

## 10. 📜 License

TOTO Magic is under the [MIT License](https://opensource.org/licenses/MIT).  
You are free to fork, modify, and distribute the code. We disclaim all warranties and assume no liability.

---

## 11. Helpful Links

- **Live Bot**: [@totomagicbot](https://t.me/totomagicbot)  
- **Project Demo**: [lilypad.croakey.io](https://lilypad.croakey.io/games)  
- **Source Code**: [GitHub Repo](https://github.com/izzleton/TOTO-Magic)  
- **Project Story**: [Hackathon Entry](https://devpost.com/software/toto-magic)
- **AWS Docs**: [Amazon Web Services](https://aws.amazon.com/documentation/)
- **Amazon Q**: [Amazon Q Developer](https://aws.amazon.com/q/developer/)
- **Telegram Bot API**: [Telegram Docs](https://core.telegram.org/bots/api)

![License](https://img.shields.io/badge/license-MIT-green.svg)
![AWS Services](https://img.shields.io/badge/AWS%20Services-EC2%2C%20Q%2C%20S3-blue.svg)
![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)
![Contributions](https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg)
