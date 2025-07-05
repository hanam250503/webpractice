import requests
import pandas as pd
import time
from flask import Flask, request, render_template_string

# --- Flask 앱 초기화 ---
app = Flask(__name__)

# --- 기능 수정: 모든 거래 유형의 매물 데이터 수집 ---
def fetch_real_estate_data(complex_no, max_page=10):
    """
    단지 고유번호(complexNo)를 사용하여 해당 단지의 모든 유형(매매, 전세, 월세)의 매물 목록을 가져옵니다.
    """
    all_articles = []
    trade_types = {'A1': '매매', 'B1': '전세', 'B2': '월세'}

    for trade_type_code, trade_type_name in trade_types.items():
        print(f"\n단지번호 {complex_no}의 '{trade_type_name}' 유형 매물을 수집합니다.")
        
        page = 1
        while page <= max_page:
            print(f"{page}페이지에서 데이터를 가져오는 중...")
            
            cookies = {
                'page_uid': 'jbQXmdqo1SCssZk3hNZssssstTK-372045', 'NNB': 'VAE72MMG5ZTWQ', 'SRT30': '1751641734', 'SRT5': '1751641734',
                'nhn.realestate.article.rlet_type_cd': 'A01', 'nhn.realestate.article.trade_type_cd': '""', 'nhn.realestate.article.ipaddress_city': '1100000000',
                '_fwb': '53JJx1l2AHgfBjfEQnEEE9.1751641735846', 'landHomeFlashUseYn': 'Y', 'NAC': 'xT6RBswEpCNE', 'NACT': '1',
                'REALESTATE': 'Sat%20Jul%2005%202025%2000%3A11%3A40%20GMT%2B0900%20(Korean%20Standard%20Time)',
                'PROP_TEST_KEY': '1751641900195.fa5ca6a61d0baaab8c40280944c052b07732a3f5f974f4c3e88b5c5c74798974',
                'PROP_TEST_ID': '5dfbdc78923f59459dc2566769e039cccc129ee71b5fe1971faf52292e364d20',
                'BUC': 'Hmh7fYWF1f9QQYHVl--h-qebXSwj_tEQn9A8GVm-Suw=',
            }
            headers = {
                'accept': '*/*', 'accept-language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3NTE2NDE5MDAsImV4cCI6MTc1MTY1MjcwMH0.mKryVG_HhDJtcGj64v3RM0c_sWOT5tKkNnY8TjHVyK8',
                'priority': 'u=1, i', 'referer': f'https://new.land.naver.com/complexes/{complex_no}',
                'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"', 'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"', 'sec-fetch-dest': 'empty', 'sec-fetch-mode': 'cors', 'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            }
            base_url = 'https://new.land.naver.com/api/articles/complex'
            
            params = {
                'realEstateType': 'APT:ABYG:JGC:PRE', 
                'tradeType': trade_type_code, # 현재 루프의 거래 유형 코드를 사용
                'tag': '::', 'rentPriceMin': '0', 'rentPriceMax': '900000000',
                'priceMin': '0', 'priceMax': '900000000', 'areaMin': '0', 'areaMax': '900000000', 'oldBuildYears': '',
                'recentlyBuildYears': '', 'minHouseHoldCount': '', 'maxHouseHoldCount': '', 'showArticle': 'false', 'sameAddressGroup': 'false',
                'minMaintenanceCost': '', 'maxMaintenanceCost': '', 'priceType': 'RETAIL', 'directions': '', 'page': page,
                'complexNo': complex_no, 'buildingNos': '', 'areaNos': '', 'type': 'list', 'order': 'rank',
            }
            try:
                response = requests.get(f"{base_url}/{complex_no}", params=params, cookies=cookies, headers=headers)
                response.raise_for_status()
                data = response.json()
                article_list = data.get("articleList", [])
                
                if not article_list: 
                    print(f"'{trade_type_name}' 유형의 매물이 더 이상 없습니다.")
                    break # 현재 거래 유형의 페이지 루프 중단
                
                all_articles.extend(article_list)
                
                if not data.get("isMoreData", False): 
                    print(f"'{trade_type_name}' 유형의 모든 페이지를 수집했습니다.")
                    break # 현재 거래 유형의 페이지 루프 중단
                
                page += 1
                time.sleep(0.5)
            except requests.exceptions.RequestException as e:
                print(f"요청 중 예외 발생: {e}")
                break # 현재 거래 유형의 페이지 루프 중단
    
    return all_articles

# --- HTML 템플릿 ---
INDEX_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>네이버 부동산 데이터 조회</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Noto Sans KR', sans-serif; }
    </style>
</head>
<body class="bg-gray-100 flex items-center justify-center min-h-screen">
    <div class="w-full max-w-lg p-8 space-y-8 bg-white rounded-xl shadow-lg">
        <div class="text-center">
            <h1 class="text-3xl font-bold text-gray-800">네이버 부동산 스크래퍼</h1>
            <p class="mt-2 text-gray-600">조회할 아파트 단지 번호를 입력하세요.</p>
        </div>
        <form action="/scrape" method="post" class="space-y-6">
            <div>
                <label for="complex_no" class="text-sm font-medium text-gray-700">단지 번호 (Complex No.)</label>
                <input type="text" id="complex_no" name="complex_no" required
                       class="mt-1 block w-full px-4 py-3 bg-gray-50 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                       placeholder="예: 8692">
            </div>
            <div>
                <label for="max_page" class="text-sm font-medium text-gray-700">최대 페이지 수 (유형별)</label>
                <input type="number" id="max_page" name="max_page" min="1" value="10"
                       class="mt-1 block w-full px-4 py-3 bg-gray-50 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500">
            </div>
            <div>
                <button type="submit"
                        class="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-lg font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors duration-300">
                    데이터 조회
                </button>
            </div>
        </form>
    </div>
</body>
</html>
"""

# 결과 표시 페이지 (타이틀 수정)
RESULTS_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>조회 결과</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Noto Sans KR', sans-serif; }
        th { position: sticky; top: 0; background-color: #f3f4f6; }
    </style>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto p-4 sm:p-6 lg:p-8">
        <div class="flex justify-between items-center mb-6">
            <h1 class="text-2xl sm:text-3xl font-bold text-gray-800">전체 매물 조회 결과 (단지번호: {{ complex_no }})</h1>
            <a href="/" class="px-4 py-2 bg-indigo-600 text-white font-semibold rounded-md hover:bg-indigo-700 transition-colors duration-300">새로 조회하기</a>
        </div>

        {% if table %}
        <div class="overflow-x-auto bg-white rounded-lg shadow">
            <div class="max-h-[80vh] overflow-y-auto">
                <table class="w-full text-sm text-left text-gray-600">
                    <thead class="text-xs text-gray-700 uppercase bg-gray-200">
                        {{ table_head|safe }}
                    </thead>
                    <tbody>
                        {{ table_body|safe }}
                    </tbody>
                </table>
            </div>
        </div>
        {% else %}
        <div class="bg-white rounded-lg shadow p-8 text-center">
            <h2 class="text-xl font-semibold text-gray-700">조회된 매물이 없습니다.</h2>
            <p class="mt-2 text-gray-500">단지 번호를 확인하시거나 다른 번호로 시도해보세요.</p>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

# --- Flask 라우트 설정 ---
@app.route('/')
def index():
    """메인 페이지를 렌더링합니다."""
    return render_template_string(INDEX_HTML)

@app.route('/scrape', methods=['POST'])
def scrape():
    """폼에서 단지 번호를 받아 스크래핑을 수행하고 결과를 보여줍니다."""
    complex_no = request.form.get('complex_no')
    max_page_str = request.form.get('max_page', '10')

    if not complex_no:
        return "단지 번호를 입력해주세요.", 400
    
    try:
        max_page = int(max_page_str)
    except (ValueError, TypeError):
        max_page = 10

    # 데이터 스크래핑
    articles = fetch_real_estate_data(complex_no, max_page)

    if not articles:
        return render_template_string(RESULTS_HTML, table=None, complex_no=complex_no)

    # Pandas DataFrame으로 변환
    df = pd.DataFrame(articles)
    
    # 보여줄 컬럼 선택 및 이름 변경
    columns_map = {
        'articleName': '단지명', 'tradeTypeName': '거래', 'floorInfo': '층',
        'dealOrWarrantPrc': '가격', 'areaName': '타입(m²)', 'direction': '향',
        'buildingName': '동', 'realtorName': '부동산', 'articleConfirmYmd': '확인일',
        'articleFeatureDesc': '매물 특징'
    }
    
    # 실제 데이터에 있는 컬럼만 선택
    existing_columns = [col for col in columns_map.keys() if col in df.columns]
    
    if not existing_columns:
        # 가져온 데이터에 원하는 컬럼이 하나도 없을 경우
        return "조회된 매물에서 유효한 정보를 찾을 수 없습니다.", 200

    df_selected = df[existing_columns].copy()
    df_selected.rename(columns=columns_map, inplace=True)
    
    # DataFrame을 HTML 테이블의 thead와 tbody로 분리
    html_table = df_selected.to_html(classes="divide-y divide-gray-200", border=0, index=False)
    table_head = "<thead>" + html_table.split("<thead>")[1].split("</thead>")[0] + "</thead>"
    table_head = table_head.replace("<th>", "<th scope='col' class='px-6 py-3 text-left'>")
    table_body = "<tbody>" + html_table.split("<tbody>")[1].split("</tbody>")[0] + "</tbody>"
    table_body = table_body.replace("<tr>", "<tr class='bg-white hover:bg-gray-50'>")
    table_body = table_body.replace("<td>", "<td class='px-6 py-4 font-medium text-gray-900 whitespace-nowrap'>")

    return render_template_string(RESULTS_HTML, table=True, table_head=table_head, table_body=table_body, complex_no=complex_no)

# --- 앱 실행 ---
if __name__ == '__main__':
    # host='0.0.0.0'으로 설정하여 외부에서도 접속 가능하게 할 수 있습니다.
    # debug=True는 개발 중에만 사용하세요.
    app.run(debug=True)
