from flask import Flask, request, jsonify
from flask_caching import Cache
import requests
import re
import time
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# ================= CACHE CONFIGURATION =================
# Configure Flask-Caching with SimpleCache (in-memory)
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # 5 minutes (300 seconds)
app.config['CACHE_THRESHOLD'] = 100  # Maximum number of items to cache

cache = Cache(app)

# ================= PROXIES =================
PROXIES = [
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_14068911_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_76090875_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_55959051_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_20782905_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_15476846_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_55677753_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_36922492_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_58760767_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_25856756_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_18064269_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_90704531_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_80377955_time_15:4318888@change5.owlproxy.com:7778",
    "http://Lz8gYXGWn190_custom_zone_IN_st__city_sid_91038744_time_15:4318888@change5.owlproxy.com:7778",
]

# ================= CONFIGURATION =================
NEW_VEHICLE_API = "https://vehicle-chass-id.vercel.app/info?vehicle="
REQUEST_TIMEOUT = 10

# Legacy cache for chassis data (keeping for backward compatibility)
legacy_cache = {}

def get_legacy_cache_key(rc):
    return f"info_{rc}"

def get_from_legacy_cache(key):
    if key in legacy_cache:
        data, timestamp = legacy_cache[key]
        if datetime.now() - timestamp < timedelta(seconds=300):  # 5 minutes
            return data
        else:
            del legacy_cache[key]
    return None

def set_to_legacy_cache(key, data):
    legacy_cache[key] = (data, datetime.now())

# ================= PROXY MANAGEMENT =================
def get_proxy_dict(proxy_url):
    """Convert proxy URL to dictionary format for requests"""
    return {"http": proxy_url, "https": proxy_url}

def make_request_with_proxies(method, url, **kwargs):
    """Make request trying different proxies if one fails"""
    timeout = kwargs.pop('timeout', REQUEST_TIMEOUT)
    headers = kwargs.pop('headers', {})
    data = kwargs.pop('data', None)
    
    for i, proxy_url in enumerate(PROXIES):
        try:
            proxy_dict = get_proxy_dict(proxy_url)
            print(f"Trying proxy {i+1}/{len(PROXIES)}: {proxy_url.split('@')[1] if '@' in proxy_url else proxy_url[:50]}")
            
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, proxies=proxy_dict, timeout=timeout, **kwargs)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, proxies=proxy_dict, timeout=timeout, data=data, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code == 200:
                print(f"Success with proxy {i+1}")
                return response
            else:
                print(f"Proxy {i+1} returned status {response.status_code}")
                
        except Exception as e:
            print(f"Proxy {i+1} failed: {str(e)[:100]}")
            continue
    
    # If all proxies fail, try without proxy as fallback
    print("All proxies failed, trying without proxy...")
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=timeout, **kwargs)
        else:
            response = requests.post(url, headers=headers, timeout=timeout, data=data, **kwargs)
        return response
    except Exception as e:
        print(f"Request without proxy also failed: {e}")
        raise

# ================= GET CHASSIS FROM API =================
def get_chassis_last5(rc):
    try:
        response = make_request_with_proxies("GET", NEW_VEHICLE_API + rc, timeout=REQUEST_TIMEOUT)
        data = response.json()

        if data.get("statusCode") != 200:
            return None, None

        chassis = data.get("response", {}).get("chassis", "")

        if not chassis or chassis == "N/A":
            return None, None

        return chassis[-5:], data.get("response", {})

    except Exception as e:
        print(f"Chassis fetch error: {e}")
        return None, None

# ================= MOBILE FETCH =================
def get_mobile(rc, last5):
    session = requests.Session()
    
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive"
    })

    HP = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/statevalidation/homepage.xhtml?statecd=Mzc2MzM2MzAzNjY0MzIzODM3NjIzNjY0MzY2MjM3NDQ0Yw=="
    HB = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/statevalidation/homepage.xhtml"
    LI = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/usermgmt/login.xhtml"
    FR = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/balanceservice/form_reschedule_fitness.xhtml"

    # Function to make requests with proxy retry for each step
    def proxy_request(method, url, **kwargs):
        timeout = kwargs.pop('timeout', REQUEST_TIMEOUT)
        headers = kwargs.pop('headers', {})
        data = kwargs.pop('data', None)
        
        for i, proxy_url in enumerate(PROXIES):
            try:
                proxy_dict = get_proxy_dict(proxy_url)
                if method.upper() == "GET":
                    response = session.get(url, headers=headers, proxies=proxy_dict, timeout=timeout, **kwargs)
                else:
                    response = session.post(url, headers=headers, proxies=proxy_dict, timeout=timeout, data=data, **kwargs)
                
                if response.status_code == 200:
                    return response
            except Exception:
                continue
        
        # Fallback without proxy
        if method.upper() == "GET":
            return session.get(url, headers=headers, timeout=timeout, **kwargs)
        else:
            return session.post(url, headers=headers, timeout=timeout, data=data, **kwargs)

    try:
        # Step 1: Get homepage
        r = proxy_request("GET", HP)
        
        vs = re.search(r'<input[^>]*name="javax\.faces\.ViewState"[^>]*value="([^"]+)"', r.text)
        if not vs:
            return None
        vs = vs.group(1)

        cid = "j_idt193"
        cm = re.search(r'<div[^>]*id="(j_idt\d+)"[^>]*class="[^"]*ui-chkbox', r.text)
        if cm:
            cid = cm.group(1)

        AH = {
            "Accept": "application/xml, text/xml, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded",
            "Faces-Request": "partial/ajax",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://vahan.parivahan.gov.in",
            "Referer": HP
        }

        # Step 2: Office select
        r = proxy_request("POST", HB, headers=AH, data={
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": "fit_c_office_to",
            "javax.faces.partial.execute": "fit_c_office_to",
            "javax.faces.behavior.event": "change",
            "homepageformid": "homepageformid",
            "fit_c_office_to_input": "1",
            "javax.faces.ViewState": vs
        })

        m = re.search(r'<update id="j_id1:javax\.faces\.ViewState:0"><!\[CDATA\[(.*?)\]\]></update>', r.text)
        if m:
            vs = m.group(1)

        # Step 3: Checkbox
        r = proxy_request("POST", HB, headers=AH, data={
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": cid,
            "javax.faces.partial.execute": cid,
            "javax.faces.partial.render": "proccedHomeButtonId",
            "javax.faces.behavior.event": "change",
            "homepageformid": "homepageformid",
            f"{cid}_input": "on",
            "javax.faces.ViewState": vs
        })

        m = re.search(r'<update id="j_id1:javax\.faces\.ViewState:0"><!\[CDATA\[(.*?)\]\]></update>', r.text)
        if m:
            vs = m.group(1)

        # Step 4: Proceed button
        r = proxy_request("POST", HB, headers=AH, data={
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": "proccedHomeButtonId",
            "javax.faces.partial.execute": "@all",
            "proccedHomeButtonId": "proccedHomeButtonId",
            "homepageformid": "homepageformid",
            f"{cid}_input": "on",
            "javax.faces.ViewState": vs
        })

        m = re.search(r'<update id="j_id1:javax\.faces\.ViewState:0"><!\[CDATA\[(.*?)\]\]></update>', r.text)
        if m:
            vs = m.group(1)

        # Step 5: Dialog button
        dlg = "j_idt536"
        dm = re.search(r'id="(j_idt\d+)"[^>]*class="[^"]*ui-button', r.text)
        if dm:
            dlg = dm.group(1)

        r = proxy_request("POST", HB, headers=AH, data={
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": dlg,
            "javax.faces.partial.execute": "@all",
            dlg: dlg,
            "homepageformid": "homepageformid",
            f"{cid}_input": "on",
            "javax.faces.ViewState": vs
        })

        m = re.search(r'<update id="j_id1:javax\.faces\.ViewState:0"><!\[CDATA\[(.*?)\]\]></update>', r.text)
        if m:
            vs = m.group(1)

        # Step 6: Login page
        r = proxy_request("GET", LI + "?faces-redirect=true", headers={"Referer": HP})
        
        vs = re.search(r'<input[^>]*name="javax\.faces\.ViewState"[^>]*value="([^"]+)"', r.text)
        if not vs:
            return None
        vs = vs.group(1)

        fit = "j_idt506"
        fm = re.search(r'id="(j_idt\d+)"[^>]*type="submit"', r.text)
        if fm:
            fit = fm.group(1)

        proxy_request("POST", LI, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://vahan.parivahan.gov.in",
            "Referer": LI + "?faces-redirect=true"
        }, data={
            "loginForm": "loginForm",
            fit: fit,
            "javax.faces.ViewState": vs,
            "fitbalcTest": "fitbalcTest",
            "pur_cd": "86"
        })

        # Step 7: Fitness page
        r = proxy_request("GET", FR, headers={"Referer": LI + "?faces-redirect=true"})
        
        vs = re.search(r'<input[^>]*name="javax\.faces\.ViewState"[^>]*value="([^"]+)"', r.text)
        if not vs:
            return None
        vs = vs.group(1)

        # Step 8: Validate and get mobile
        r = proxy_request("POST", FR, headers={**AH, "Referer": FR}, data={
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": "balanceFeesFine:validate_dtls",
            "javax.faces.partial.execute": "@all",
            "javax.faces.partial.render": "balanceFeesFine:auth_panel",
            "balanceFeesFine:validate_dtls": "balanceFeesFine:validate_dtls",
            "balanceFeesFine": "balanceFeesFine",
            "balanceFeesFine:tf_reg_no": rc,
            "balanceFeesFine:tf_chasis_no": last5,
            "javax.faces.ViewState": vs
        })

        # Extract mobile
        for pattern in [
            r'id="balanceFeesFine:tf_mobile"[^>]*value="(\d{10})"',
            r'value="(\d{10})"[^>]*id="balanceFeesFine:tf_mobile"',
            r'tf_mobile[^>]*value="(\d{10})"'
        ]:
            m = re.search(pattern, r.text)
            if m and m.group(1)[0] in "6789":
                return m.group(1)

        nums = re.findall(r'\b[6-9]\d{9}\b', r.text)
        if nums:
            return nums[0]

        return None

    except Exception as e:
        print(f"Mobile fetch error: {e}")
        return None

# ================= MAIN ENDPOINT WITH FLASK-CACHING =================
@app.route("/info", methods=["GET"])
@cache.cached(timeout=300, query_string=True)  # Cache for 5 minutes based on query parameters
def get_vehicle_info():
    start_time = time.time()
    
    vehicle = request.args.get("vehicle", "").strip().upper()
    vehicle = re.sub(r'[^A-Z0-9]', '', vehicle)

    if not vehicle:
        return jsonify({
            "error": "Vehicle parameter required",
            "example": "/info?vehicle=AP05CU6210"
        }), 400

    # Fetch vehicle details (this won't be cached by Flask-Caching for errors)
    last5, vehicle_details = get_chassis_last5(vehicle)

    if not last5 or not vehicle_details:
        return jsonify({
            "error": "Vehicle not found or invalid registration number",
            "reg_no": vehicle,
            "response_time": round(time.time() - start_time, 2)
        }), 404

    # Fetch mobile number
    mobile = get_mobile(vehicle, last5)

    response_data = {
        "reg_no": vehicle,
        "chassis": vehicle_details.get("chassis"),
        "chassis_last5": last5,
        "engine": vehicle_details.get("engine"),
        "mobile": mobile if mobile else "Not Available",
        "manufacturer": vehicle_details.get("manufacturer"),
        "vehicle_model": vehicle_details.get("vehicle"),
        "reg_date": vehicle_details.get("regDate"),
        "fuel_type": vehicle_details.get("fuelType"),
        "cubic_capacity": vehicle_details.get("cubicCapacity"),
        "owner_name": vehicle_details.get("owner"),
        "vehicle_class": vehicle_details.get("vehicleClass"),
        "status": vehicle_details.get("status"),
        "response_time": round(time.time() - start_time, 2),
        "cached": False  # This will be overridden by Flask-Caching if served from cache
    }

    return jsonify(response_data)

# Optional: Endpoint to clear cache manually
@app.route("/clear_cache", methods=["POST"])
def clear_cache():
    cache.clear()
    return jsonify({"message": "Cache cleared successfully"}), 200

# ================= START =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=False, threaded=True)
