import requests
import pandas as pd
import time
from flask import Flask, request, render_template_string
import re

# --- Flask 앱 초기화 ---
app = Flask(__name__)

# [추가] 가격 문자열을 숫자로 변환하는 함수 (단위: 만원)
def convert_price_to_number(price_str):
    """ '5억', '1억 2,000', '30,000/100' 등의 가격 문자열을 숫자(만원 단위)로 변환합니다. """
    price_str = price_str.replace(',', '')
    
    # 월세의 경우 보증금을 기준으로 변환 (예: 30,000/100 -> 30000)
    if '/' in price_str:
        price_str = price_str.split('/')[0]

    num = 0
    if '억' in price_str:
        parts = price_str.split('억')
        num += int(parts[0]) * 10000
        if len(parts) > 1 and parts[1]:
            num += int(parts[1])
    else:
        num = int(price_str)
        
    return num

# --- 기능 수정: 모든 거래 유형의 매물 데이터 수집 ---
def fetch_real_estate_data(complex_no, max_page=10):
    """ 단지 고유번호를 사용하여 모든 매물 목록을 가져옵니다. """
    # (기존과 동일하여 코드는 생략... 필요시 이전 코드 내용을 여기에 그대로 유지)
    all_articles = []
    trade_types = {'A1': '매매', 'B1': '전세', 'B2': '월세'}

    for trade_type_code, trade_type_name in trade_types.items():
        print(f"\n단지번호 {complex_no}의 '{trade_type_name}' 유형 매물을 수집합니다.")
        page = 1
        while page <= max_page:
            print(f"{page}페이지에서 데이터를 가져오는 중...")
            cookies = { 'NNB': 'VAE72MMG5ZTWQ' } # 간단한 쿠키 예시
            headers = {
                'accept': '*/*', 'accept-language': 'ko-KR,ko;q=0.9',
                'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3NTE2NDE5MDAsImV4cCI6MTc1MTY1MjcwMH0.mKryVG_HhDJtcGj64v3RM0c_sWOT5tKkNnY8TjHVyK8',
                'referer': f'https://new.land.naver.com/complexes/{complex_no}',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            }
            base_url = 'https://new.land.naver.com/api/articles/complex'
            params = {
                'realEstateType': 'APT:ABYG:JGC:PRE', 'tradeType': trade_type_code,
                'page': page, 'complexNo': complex_no, 'order': 'rank',
            }
            try:
                response = requests.get(f"{base_url}/{complex_no}", params=params, cookies=cookies, headers=headers)
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


# --- HTML 템플릿 ---
INDEX_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>네이버 부동산 데이터 조회</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style> body { font-family: 'Noto Sans KR', sans-serif; } </style>
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
                       class="mt-1 block w-full px-4 py-3 bg-gray-50 border border-gray-300 rounded-md"
                       placeholder="예: 8692">
            </div>
            <div>
                <label for="max_page" class="text-sm font-medium text-gray-700">최대 페이지 수 (유형별)</label>
                <input type="number" id="max_page" name="max_page" min="1" value="10"
                       class="mt-1 block w-full px-4 py-3 bg-gray-50 border border-gray-300 rounded-md">
            </div>
            <div>
                <button type="submit"
                        class="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-lg font-medium text-white bg-indigo-600 hover:bg-indigo-700">
                    데이터 조회
                </button>
            </div>
        </form>
    </div>
</body>
</html>
"""

# [수정] 필터 및 정렬 기능이 추가된 결과 페이지
RESULTS_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>조회 결과</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style> 
        body { font-family: 'Noto Sans KR', sans-serif; } 
        thead th { position: sticky; top: 0; z-index: 10; }
        .filter-controls { position: sticky; top: 41px; z-index: 10; }
    </style>
</head>
<body class="bg-gray-100">
    <div class="container mx-auto p-4 sm:p-6 lg:p-8">
        <div class="flex justify-between items-center mb-4">
            <h1 class="text-2xl sm:text-3xl font-bold text-gray-800">매물 조회 결과 (단지번호: {{ complex_no }})</h1>
            <a href="/" class="px-4 py-2 bg-indigo-600 text-white font-semibold rounded-md hover:bg-indigo-700">새로 조회하기</a>
        </div>

        {% if table %}
        <div class="filter-controls p-4 bg-gray-50 rounded-lg shadow mb-4 flex flex-wrap items-center gap-x-6 gap-y-4">
            <div class="flex items-center gap-4">
                <span class="font-semibold text-sm">거래유형:</span>
                <label class="inline-flex items-center"><input type="checkbox" class="trade-type-filter" value="매매" checked> <span class="ml-2">매매</span></label>
                <label class="inline-flex items-center"><input type="checkbox" class="trade-type-filter" value="전세" checked> <span class="ml-2">전세</span></label>
                <label class="inline-flex items-center"><input type="checkbox" class="trade-type-filter" value="월세" checked> <span class="ml-2">월세</span></label>
            </div>
            <div class="flex items-center gap-2">
                 <span class="font-semibold text-sm">가격(만원):</span>
                 <input type="number" id="min-price" placeholder="최소" class="w-24 p-1 border rounded-md text-sm">
                 <span class="mx-1">~</span>
                 <input type="number" id="max-price" placeholder="최대" class="w-24 p-1 border rounded-md text-sm">
            </div>
            <div class="flex items-center gap-2">
                <span class="font-semibold text-sm">정렬:</span>
                <select id="sort-column" class="p-1 border rounded-md text-sm">
                    <option value="3">가격</option>
                    <option value="4">타입(m²)</option>
                </select>
                <select id="sort-order" class="p-1 border rounded-md text-sm">
                    <option value="asc">오름차순</option>
                    <option value="desc">내림차순</option>
                </select>
            </div>
        </div>

        <div class="overflow-x-auto bg-white rounded-lg shadow">
            <div class="max-h-[75vh] overflow-y-auto">
                <table class="w-full text-sm text-left text-gray-600" id="results-table">
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
        {% endif %}
    </div>

<script>
document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.querySelector("#results-table tbody");
    if (!tableBody) return;

    // 원본 데이터 행들을 배열로 저장
    const originalRows = Array.from(tableBody.querySelectorAll("tr"));

    // 필터 컨트롤 요소들
    const tradeTypeFilters = document.querySelectorAll('.trade-type-filter');
    const minPriceInput = document.getElementById('min-price');
    const maxPriceInput = document.getElementById('max-price');
    const sortColumnSelect = document.getElementById('sort-column');
    const sortOrderSelect = document.getElementById('sort-order');

    // 모든 필터 컨트롤에 이벤트 리스너 추가
    const allControls = [...tradeTypeFilters, minPriceInput, maxPriceInput, sortColumnSelect, sortOrderSelect];
    allControls.forEach(control => control.addEventListener('change', applyFiltersAndSort));

    function applyFiltersAndSort() {
        // 1. 현재 필터 값들 가져오기
        const selectedTradeTypes = Array.from(tradeTypeFilters)
            .filter(cb => cb.checked)
            .map(cb => cb.value);

        const minPrice = parseFloat(minPriceInput.value) || 0;
        const maxPrice = parseFloat(maxPriceInput.value) || Infinity;
        
        // 2. 필터링: 원본 행들을 기준으로 필터링하여 보여줄 행들 결정
        const filteredRows = originalRows.filter(row => {
            const cells = row.querySelectorAll('td');
            const tradeType = cells[1].textContent.trim();
            const price = parseFloat(cells[3].dataset.price);

            // 거래유형 필터
            if (!selectedTradeTypes.includes(tradeType)) return false;
            // 가격범위 필터
            if (price < minPrice || price > maxPrice) return false;

            return true;
        });

        // 3. 정렬
        const sortColumnIndex = parseInt(sortColumnSelect.value, 10);
        const sortOrder = sortOrderSelect.value;
        const isNumericSort = sortColumnIndex === 3 || sortColumnIndex === 4;

        filteredRows.sort((a, b) => {
            const a_cells = a.querySelectorAll('td');
            const b_cells = b.querySelectorAll('td');

            let valA, valB;
            if (isNumericSort) {
                // 가격과 면적은 data 속성의 숫자 값을 사용
                valA = parseFloat(a_cells[sortColumnIndex].dataset.value);
                valB = parseFloat(b_cells[sortColumnIndex].dataset.value);
            } else {
                // 그 외는 텍스트 값을 사용
                valA = a_cells[sortColumnIndex].textContent.trim();
                valB = b_cells[sortColumnIndex].textContent.trim();
            }

            if (valA < valB) return sortOrder === 'asc' ? -1 : 1;
            if (valA > valB) return sortOrder === 'asc' ? 1 : -1;
            return 0;
        });

        // 4. 테이블 업데이트
        // tableBody의 모든 내용을 지우고, 필터링 및 정렬된 행들로 다시 채움
        tableBody.innerHTML = ''; 
        filteredRows.forEach(row => tableBody.appendChild(row));
    }
});
</script>
</body>
</html>
"""

# --- Flask 라우트 설정 ---
@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/scrape', methods=['POST'])
def scrape():
    complex_no = request.form.get('complex_no')
    max_page = int(request.form.get('max_page', '10'))

    if not complex_no: return "단지 번호를 입력해주세요.", 400

    articles = fetch_real_estate_data(complex_no, max_page)
    if not articles: return render_template_string(RESULTS_HTML, table=None, complex_no=complex_no)

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

    # [수정] 정렬/필터링을 위한 숫자 데이터 생성
    if '가격' in df_selected.columns:
        df_selected['price_numeric'] = df_selected['가격'].apply(convert_price_to_number)
    if '타입(m²)' in df_selected.columns:
        df_selected['area_numeric'] = pd.to_numeric(df_selected['타입(m²)'], errors='coerce')


    # HTML 테이블 생성
    table_head_html = "".join([f"<th scope='col' class='px-6 py-3 text-left'>{name}</th>" for name in df_selected.columns if not name.endswith('_numeric')])
    
    table_body_html = ""
    for _, row in df_selected.iterrows():
        table_body_html += "<tr class='bg-white hover:bg-gray-50'>"
        # [수정] 각 셀에 data-value 속성 추가
        table_body_html += f"<td class='px-6 py-4'>{row.get('단지명', '')}</td>"
        table_body_html += f"<td class='px-6 py-4'>{row.get('거래', '')}</td>"
        table_body_html += f"<td class='px-6 py-4'>{row.get('층', '')}</td>"
        table_body_html += f"<td class='px-6 py-4' data-value='{row.get('price_numeric', 0)}' data-price='{row.get('price_numeric', 0)}'>{row.get('가격', '')}</td>"
        table_body_html += f"<td class='px-6 py-4' data-value='{row.get('area_numeric', 0)}'>{row.get('타입(m²)', '')}</td>"
        table_body_html += f"<td class='px-6 py-4'>{row.get('향', '')}</td>"
        table_body_html += f"<td class='px-6 py-4'>{row.get('동', '')}</td>"
        table_body_html += f"<td class='px-6 py-4'>{row.get('부동산', '')}</td>"
        table_body_html += f"<td class='px-6 py-4'>{row.get('확인일', '')}</td>"
        table_body_html += f"<td class='px-6 py-4'>{row.get('매물 특징', '')}</td>"
        table_body_html += "</tr>"


    return render_template_string(RESULTS_HTML, table=True, 
                                  table_head=f"<tr>{table_head_html}</tr>", 
                                  table_body=table_body_html, 
                                  complex_no=complex_no)

if __name__ == '__main__':
    app.run(debug=True)