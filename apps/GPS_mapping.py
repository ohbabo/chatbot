import requests, os, math
import pandas as pd
from .models import db, WelfareCenter, Program




def get_lat_lng_from_address(address):
    # Google Geocoding API 이용
    try:
        google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not google_maps_api_key:
            raise ValueError("Google Maps API 키가 설정되지 않았습니다.")
        
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={google_maps_api_key}&language=ko"
        response = requests.get(url)
        data = response.json()
        
        #print(f"Geocoding API 호출 결과: {data}")
        
        if data["status"] != "OK":
            raise ValueError(f"Geocoding API 오류: {data['status']}")
        
        location = data["results"][0]["geometry"]["location"]
        return location["lat"], location["lng"]
    
    except Exception as e:
        print(f"주소 변환 중 오류 발생: {e}")
        return None, None

def distance_km(lat1, lng1, lat2, lng2):
    R = 6371.0  # 지구 반지름 (km)
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(d_lng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c
