import requests
import pandas as pd
import time
from flask import Flask, request, render_template
import re

# --- Flask 앱 초기화 ---
app = Flask(__name__)

# 가격 문자열을 숫자로 변환하는 함수 (단위: 만원)
def convert_price_to_number(price_str):
    """ '5억', '1억 2,000', '30,000/100' 등의 가격 문자열을 숫자(만원 단위)로 변환합니다. """
    price_str = str(price_str).replace(',', '')
    
    if '/' in price_str:
        price_str = price_str.split('/')[0]

    num = 0
    try:
        if '억' in price_str:
            parts = price_str.split('억')
            num += int(parts[0]) * 10000
            if len(parts) > 1 and parts[1]:
                num += int(parts[1].strip())
        else:
            num = int(price_str)
    except (ValueError, TypeError):
        return 0
        
    return num

# --- 기능 수정: 모든 거래 유형의 매물 데이터 수집 ---
def fetch_real_estate_data(complex_no, max_page=10):
    """ 단지 고유번호를 사용하여 모든 매물 목록을 가져옵니다. (보안 토큰 제거) """
    all_articles = []
    trade_types = {'A1': '매매', 'B1': '전세', 'B2': '월세'}

    for trade_type_code, trade_type_name in trade_types.items():
        print(f"\n단지번호 {complex_no}의 '{trade_type_name}' 유형 매물을 수집합니다.")
        page = 1
        while page <= max_page:
            print(f"{page}페이지에서 데이터를 가져오는 중...")
            
            # [보안 수정] 하드코딩된 쿠키와 인증 토큰을 모두 제거합니다.
            headers = {
                'accept': '*/*',
                'accept-language': 'ko-KR,ko;q=0.9',
                'referer': f'https://new.land.naver.com/complexes/{complex_no}',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            }
            base_url = 'https://new.land.naver.com/api/articles/complex'
            params = {
                'realEstateType': 'APT:ABYG:JGC:PRE', 'tradeType': trade_type_code,
                'page': page, 'complexNo': complex_no, 'order': 'rank',
            }
            try:
                # [보안 수정] cookies=... 부분을 제거합니다.
                response = requests.get(f"{base_url}/{complex_no}", params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                article_list = data.get("articleList", [])
                
                if not article_list: break
                all_articles.extend(article_list)
                if not data.get("isMoreData", False): break
                
                page += 1
                time.sleep(0.3)
            except requests.exceptions.RequestException as e:
                print(f"요청 중 예외 발생: {e}")
                break
    return all_articles

# --- Flask 라우트 설정 ---
@app.route('/')
def index():
    """메인 페이지를 렌더링합니다."""
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    """폼에서 단지 번호를 받아 스크래핑을 수행하고 결과를 보여줍니다."""
    complex_no = request.form.get('complex_no')
    max_page = int(request.form.get('max_page', '10'))

    if not complex_no: return "단지 번호를 입력해주세요.", 400

    articles = fetch_real_estate_data(complex_no, max_page)
    if not articles: 
        return render_template('results.html', table=None, complex_no=complex_no)

    df = pd.DataFrame(articles)
    columns_map = {
        'articleName': '단지명', 'tradeTypeName': '거래', 'floorInfo': '층',
        'dealOrWarrantPrc': '가격', 'areaName': '타입(m²)', 'direction': '향',
        'buildingName': '동', 'realtorName': '부동산', 'articleConfirmYmd': '확인일',
        'articleFeatureDesc': '매물 특징'
    }
    
    existing_columns = [col for col in columns_map.keys() if col in df.columns]
    if not existing_columns: return "조회된 매물에서 유효한 정보를 찾을 수 없습니다.", 200

    df_selected = df[existing_columns].copy()
    df_selected.rename(columns=columns_map, inplace=True)

    if '가격' in df_selected.columns:
        df_selected['price_numeric'] = df_selected['가격'].apply(convert_price_to_number)
    if '타입(m²)' in df_selected.columns:
        df_selected['area_numeric'] = pd.to_numeric(df_selected['타입(m²)'], errors='coerce')

    table_data = df_selected.to_dict('records')

    return render_template('results.html', table=table_data, complex_no=complex_no)

# --- 앱 실행 ---
if __name__ == '__main__':
    app.run(debug=True)