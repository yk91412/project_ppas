from flask import Flask, render_template, request, send_file, make_response, redirect, url_for
from wtforms import StringField, SelectField, DateField, SubmitField
import pandas as pd
import matplotlib.pyplot as plt
from markupsafe import Markup
from flask_assets import Environment, Bundle
import matplotlib.font_manager as fm
import os
from datetime import date
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm  # FlaskForm 추가
import zipfile
from io import BytesIO
import uuid
from googletrans import Translator
import deepl
import matplotlib.gridspec as gridspec
import seaborn as sns
import re
import requests


app = Flask(__name__)
app.config.from_pyfile('config.py')

csrf = CSRFProtect(app)


# Google Cloud Translation API 인증이 필요해서 인증 필요없는 library package 사용
## pip install googletrans==4.0.0rc1 필요
## pip install deepl 필요

# 구글 번역
def translate_keyword_g(keyword, target_language='en'):
    translator = Translator()
    keyword = keyword.replace(' ', '')
    translation = translator.translate(keyword, dest=target_language)
    return translation.text

# deepl 번역
def translate_keyword_d(keyword):
    auth_key = "c6d7b043-1235-44d4-96bd-331cc0ec8c35:fx"
    translator = deepl.Translator(auth_key)
    keyword = keyword.replace(' ', '')
    result = translator.translate_text(keyword, target_lang='EN-US')
    return result.text

# 네이버 번역
def translate_keyword_n(text):
    url = "https://naveropenapi.apigw.ntruss.com/nmt/v1/translation"
    headers = {"X-NCP-APIGW-API-KEY-ID": "3r1tnk1ohr", "X-NCP-APIGW-API-KEY": "twwiSo88HbmrNatHLlWYn618dWpK5P9XcD6B6Hkr"}
    text = text.replace(' ', '')
    data = {"source": "ko","target": "en","text": text}
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        result = response.json()
        translated_text = result['message']['result']['translatedText']
        if translated_text.lower().startswith('a '): translated_text = translated_text.replace('a ', '', 1)
        elif translated_text.lower().startswith('an '): translated_text = translated_text.replace('an ', '', 1)
        return translated_text
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None
        
# 폼 클래스 정의
class SearchForm(FlaskForm):
    application_fields = StringField('Application Fields')
    filter_type = SelectField('Filter Type', choices=[('patent', '특허실용신안'), ('applicant', '출원인')])
    search_keyword = StringField('Search Keyword')
    start_date = DateField('Start Date', format='%Y-%m-%d', default=date(2013, 1, 1))
    end_date = DateField('End Date', format='%Y-%m-%d', default=date.today())
    submit = SubmitField('검색')
    download = SubmitField('다운로드')
    plot = SubmitField('Plot')  # 플롯 필드 추가

current_directory = os.getcwd()
font_path = os.path.join(current_directory, 'NanumBarunGothic.ttf')

if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    font_prop = fm.FontProperties(fname=font_path)
    plt.rc("font", family=font_prop.get_name())
    plt.rcParams['axes.unicode_minus'] = False

plt.switch_backend('Agg')

assets = Environment(app)

css = Bundle('css/style.css', output='gen/packed.css', filters='cssmin')
js = Bundle('js/scripts.js', output='gen/packed.js', filters='jsmin')

assets.register('css_all', css)
assets.register('js_all', js)

css.build()
js.build()

df_patents = pd.read_excel('result_mod_30June2024.xlsx')
df_papers = pd.read_excel('Papers_Arxiv.xlsx')

df_patents['application_date'] = pd.to_datetime(df_patents['application_date'], errors='coerce')
filtered_data_patents = pd.DataFrame()
filtered_data_papers = pd.DataFrame()


# categories = {
#     '제너럴': ['인공 지능','인공지능','뉴럴 네트워크','chat gpt','챗 gpt','챗 지피티','제미나이','메타 라마','ILSVRC','이미지넷','이미지 넷','알렉스넷','알렉스 넷','추론','신경망','신경 망','학습','훈련방법','ai','지능형','훈련 방법','지도방법','지도 방법','학습방법','학습 방법','머신러닝','머신 러닝','딥러닝','딥 러닝','패턴인식','패턴 인식','블록체인','블록 체인','이미지인식','이미지 인식','비전','자연어 처리','자연어처리','챗봇','기계학습','기계 학습','심층학습','심층 학습','제스처 인식','제스쳐 인식','피사체 인식','객체 인식','오브젝트 인식','동작 인식','모션 인식','안면 인식','거대 언어','거대언어','생성형','일반 인공지능','일반 인공 지능','일반 ai','자율 인공지능','자율 ai','자율 학습'],
#     '의료':['의료','항체','헬스','치료','항체','건강','유전자','병원','유도체','환자','동물','의료기기','의료 기기','의료정보','의료 정보','바이오의료','바이오 의료','의학','약물','수술','재활','임상','의사','간호','응급','진단','면역','질환','질병','치료제','보건','헬스케어','생체'],
#     '전자상거래서비스': ['상거래','상품','주문','맞춤 서비스','클라이언트','배송','판매','결제','공급망','공급 망','판매망','판매 망','서비스','전자상거래플랫폼','전자 상거래 플랫폼','전자상거래 플랫폼','온라인쇼핑','온라인 쇼핑','온라인 거래','디지털결제','디지털 결제','온라인서비스','온라인 서비스','온라인 플랫폼','온라인플랫폼','인터넷 거래','인터넷거래','인터넷 서비스','인터넷서비스','고객','구매자','트래픽','방문자','페이지뷰','세션 시간','세션시간','이메일 구독','이메일구독','마케팅','광고','QR','연관 상품','연관상품','통관','관세','환율'],
#     '자동차': ['자동차','주행','진입','변속기','자율주행','자율 주행','도로','차량','충돌','교통','비행','보행자','차선','신호등','전기차','하이브리드','내연기관','커넥티드카','커넥티드 카','스마트카','스마트 카','운전 보조 시스템','운전보조 시스템','운전보조시스템','ADAS','차량용센서','차량센서','차량 센서','차량용 센서','모빌리티','운송','운전','주차','헤드업 디스플레이','헤드업디스플레이','내비게이션'],
#     '금융': ['금융','코인','트레이딩','투자','신용','자산','블록체인','블록 체인','디지털자산','디지털 자산','간편결제','자동결제','입금','출금','재정','은행','보험','경제','자산','부채','대출','이자','지불','결제','송금','환율','외환','주식','채권','증권','펀드','연금','퇴직금','저축','예금','지급 보증','핀테크','온라인 뱅킹','온라인뱅킹','인터넷 뱅킹','인터넷뱅킹','크라우드 펀딩','크라우드펀딩','크립토커런시','비트코인','알트코인','캐피털'],
#     '교육': ['교육','강의','교육용','시험','성적','학생','학습관리','학습 관리','자기주도학습','학교','대학','강의','교수','교실','e러닝','이러닝','에듀테크','가상 교실','가상 수업','디지털 교과서','교사','교육자'],
#     '농업': ['농업','농사','작황','작물','스마트농업','스마트 농업','농작물','농약','수확','스마트팜','품종'],
#     '엔터테인먼트': ['콘텐츠','컨텐츠','증강 현실','증강현실','게임','미디어','사용자인터페이스','가상현실','음성인식','가상현실콘텐츠','엔터테인먼트','영화','드라마','애니메이션','뮤지컬','공연','콘서트','음악','음원','음반','뮤직비디오','뮤직 비디오','라디오','팟캐스트','팟 캐스트','오디오북','오디오 북','웹툰','웹소설','웹 소설','스트리밍','넷플릭스','디즈니','아마존','유튜브','트위치','틱톡','페이스북','인스타그램','전시회'],
#     '보안': ['보안','침입','탐지','데이터보호','데이터 보호','위협예측','위협 예측','인증','암호화','암호','안전기술','위험','방화벽','바이러스','스파이','랜섬웨어','피싱','스팸','해독','디지털 서명','디지털서명','디지털 인증서','디지털인증서','토큰','보안 프로토콜','보안프로토콜','위협 방지','위협 분석','위협 대응','위협 완화','위협 모니터링','위협 방어','위협 평가','위협 예측','위협 방어','위협 차단','위협 관리','침해 탐지','침해 방지','침해 분석','침해 대응','침해 완화','침해 모니터링','침해 평가','침해 예측','침해 방어','침해 차단','침해 관리'],
#     '자동화시스템': ['자동화','로봇자동화','로봇 자동화','제어시스템','제어 시스템','IoT','로봇제어','로봇 제어','스마트시스템','스마트 시스템','온라인서비스','온라인 서비스'],
#     '반도체': ['뉴로모픽', '인공지능 반도체', 'ai 반도체', 'npu', '양자 소자','양자 컴퓨팅','양자 알고리즘']
# } 

categories = {
    '제너럴': ['artificial intelligence', 'neural network', 'chat gpt', 'gemini', 'meta llama', 'ilsvrc', 'imagenet', 'alexnet', 'inference', 'learning', 'training methods', 'ai', 'intelligent', 'training method', 'supervised methods', 'learning methods', 'machine learning', 'deep learning', 'pattern recognition', 'blockchain', 'image recognition', 'vision', 'natural language processing', 'chatbot', 'gesture recognition', 'object recognition', 'motion recognition', 'facial recognition', 'large language models', 'generative', 'general ai', 'autonomous ai', 'autonomous learning'],
    '의료': ['healthcare', 'antibody', 'health', 'treatment', 'wellness', 'gene', 'hospital', 'derivative', 'patient', 'animal', 'medical device', 'medical information', 'bio-medical', 'medicine', 'drug', 'surgery', 'rehabilitation', 'clinical', 'doctor', 'nurse', 'emergency', 'diagnosis', 'immune', 'disease', 'disorder', 'therapy', 'public health', 'biometrics'],
    '전자상거래서비스': ['commerce', 'product', 'order', 'customized services', 'client', 'delivery', 'sales', 'payment', 'supply chain', 'service', 'e-commerce platform', 'online shopping', 'online transaction', 'digital payment', 'online service', 'online platform', 'internet transaction', 'internet service', 'customer', 'buyer', 'traffic', 'visitor', 'page view', 'session time', 'email subscription', 'marketing', 'advertisement', 'qr', 'related products', 'customs clearance', 'tariff', 'exchange rate'],
    '자동차': ['automobile', 'driving', 'entry', 'transmission', 'autonomous driving', 'road', 'vehicle', 'collision', 'traffic', 'flight', 'pedestrian', 'lane', 'traffic light', 'electric vehicle', 'hybrid', 'internal combustion engine', 'connected car', 'smart car', 'driver assistance system', 'adas', 'vehicle sensor', 'mobility', 'transportation', 'parking', 'head-up display', 'navigation'],
    '금융': ['finance', 'coin', 'trading', 'investment', 'credit', 'asset', 'blockchain', 'digital asset', 'easy payment', 'automatic payment', 'deposit', 'withdrawal', 'bank', 'insurance', 'economy', 'liability', 'loan', 'interest', 'remittance', 'exchange rate', 'foreign exchange', 'stock', 'bond', 'securities', 'fund', 'pension', 'retirement fund', 'savings', 'guarantee', 'fintech', 'online banking', 'internet banking', 'crowdfunding', 'cryptocurrency', 'bitcoin', 'altcoin', 'capital'],
    '교육': ['education', 'lecture', 'educational', 'exam', 'grade', 'student', 'learning management', 'self-directed learning', 'school', 'university', 'professor', 'classroom', 'e-learning', 'edutech', 'virtual classroom', 'virtual class', 'digital textbook', 'teacher', 'educator'],
    '농업': ['agriculture', 'farming', 'crop', 'smart agriculture', 'agricultural products', 'pesticide', 'harvest', 'smart farm', 'varieties'],
    '엔터테인먼트': ['content', 'augmented reality', 'game', 'media', 'user interface', 'virtual reality', 'voice recognition', 'vr content', 'entertainment', 'movie', 'drama', 'animation', 'musical', 'performance', 'concert', 'music', 'music source', 'album', 'music video', 'radio', 'podcast', 'audiobook', 'webtoon', 'web novel', 'streaming', 'netflix', 'disney', 'amazon', 'youtube', 'twitch', 'tiktok', 'facebook', 'instagram', 'exhibition'],
    '보안': ['security', 'intrusion', 'detection', 'data protection', 'threat prediction', 'authentication', 'encryption', 'safe technology', 'risk', 'firewall', 'virus', 'spyware', 'ransomware', 'phishing', 'spam', 'decryption', 'digital signature', 'digital certificate', 'token', 'security protocol', 'threat prevention', 'threat analysis', 'threat response', 'threat mitigation', 'threat monitoring', 'threat defense', 'threat assessment', 'intrusion detection', 'intrusion prevention', 'intrusion analysis', 'intrusion response', 'intrusion mitigation', 'intrusion monitoring', 'intrusion assessment'],
    '자동화시스템': ['automation', 'robotic automation', 'control system', 'iot', 'robot control', 'smart system', 'online service'],
    '반도체': ['neuromorphic', 'ai semiconductor', 'npu', 'quantum device', 'quantum computing', 'quantum algorithm']
}


@app.route('/')
def index():
    form = SearchForm()
    return render_template('Web.html', date=date, form=form)

@app.route('/search', methods=['POST'])
@csrf.exempt
def search():
    global filtered_data_patents
    global filtered_data_papers

    form = SearchForm()
    if form.validate_on_submit():
        application_fields = request.form.getlist('application_fields')
        filter_type = form.filter_type.data
        search_keyword = form.search_keyword.data
        start_date = form.start_date.data.strftime('%Y-%m-%d')
        end_date = form.end_date.data.strftime('%Y-%m-%d')
        # 검색 키워드를 영어로 번역
        translated_keyword_g = translate_keyword_g(search_keyword)  ## Google Translation
        translated_keyword_d = translate_keyword_d(search_keyword)  ## Deepl Translation
        translated_keyword_n = translate_keyword_n(search_keyword)  ## Naver PAPAGO Translation
        # 3가지 번역된 키워드 리스트
        translated_keywords = [translated_keyword_g.lower(), translated_keyword_d.lower(), translated_keyword_n.lower()]
        print(f"Translated Keyword: {translated_keywords}")

        try:
            # 특허 데이터 필터링
            field_conditions = [(df_patents[field] == 1) for field in application_fields]
            filtered_df_patents = df_patents[pd.concat(field_conditions, axis=1).any(axis=1)]

            if filter_type == 'applicant':
                filtered_df_patents = filtered_df_patents[filtered_df_patents['applicant'].str.contains(search_keyword, na=False)]
            else:
                filtered_df_patents = filtered_df_patents[(filtered_df_patents['title'].str.contains(search_keyword, na=False)) | 
                                                          (filtered_df_patents['summary'].str.contains(search_keyword, na=False))]

            filtered_df_patents = filtered_df_patents[(filtered_df_patents['application_date'] >= start_date) & (filtered_df_patents['application_date'] <= end_date)]

            filtered_df_patents = filtered_df_patents.rename(columns={
                'status': 'Status',
                'title': 'Title',
                'ap_num': 'Application Number',
                'application_date': 'Application Date',
                'applicant': 'Applicant'
            })

            # Add hyperlink to Application Number in patent table
            filtered_df_patents['Application Number'] = filtered_df_patents.apply(
                lambda row: f'<a href="https://patents.google.com/?q=KR{row["Application Number"]}" target="_blank">{row["Application Number"]}</a>',
                axis=1
            )

            filtered_data_patents = filtered_df_patents
            print(f"Filtered patents data: {filtered_data_patents.shape}")

            if filtered_df_patents.empty:
                return render_template('Web.html', table="", plot="", top3_table="", top5_table="", paper_table="", date=date, form=form)

            # 논문 데이터 필터링
            if filter_type == 'patent':
                paper_conditions = []
                for field in application_fields:
                    for keyword in categories.get(field, []):
                        paper_conditions.append((df_papers['title'].str.contains(keyword, na=False)) | 
                                                (df_papers['Abstract'].str.contains(keyword, na=False)))
                if paper_conditions:
                    filtered_df_papers = df_papers[pd.concat(paper_conditions, axis=1).any(axis=1)]
                    # 필터 조건 생성
                    filter_condition = pd.Series([False] * len(filtered_df_papers), index=filtered_df_papers.index)
                    for translated_keyword in translated_keywords:
                        filter_condition |= filtered_df_papers['title'].str.contains(translated_keyword, na=False) | \
                                            filtered_df_papers['Abstract'].str.contains(translated_keyword, na=False)
                    filtered_df_papers = filtered_df_papers[filter_condition]
                    filtered_data_papers = filtered_df_papers
                else:
                    filtered_data_papers = pd.DataFrame()

                if not filtered_data_papers.empty:
                    filtered_df_papers['title'] = filtered_df_papers.apply(
                        lambda row: f'<a href="{row["pdf_link"]}" target="_blank">{row["title"]}</a>',
                        axis=1
                    )
                    paper_table_html = filtered_df_papers[['title', 'Abstract', 'submit_date']]
                    paper_table_html = paper_table_html.rename(columns={
                        'title': '제목',
                        'Abstract': '요약',
                        'submit_date': '등록일'
                    })
                    paper_table_html = paper_table_html.to_html(index=False, classes="table", escape=False)
                else:
                    paper_table_html = ""
            else:
                filtered_data_papers = pd.DataFrame()
                paper_table_html = ""

            table_html = filtered_df_patents[['Application Number', 'Application Date', 'Applicant', 'Title', 'Status']]
            table_html = table_html.rename(columns={
                'Application Number' : '출원번호',
                'Application Date' : '출원일',
                'Applicant' : '출원인',
                'Title' : '제목',
                'Status' :'상태'
            })
            table_html = table_html.to_html(index=False, classes="table", escape=False)
            print("Generated table HTML")

            top3_df = filtered_df_patents['Applicant'].value_counts().head(3).reset_index()
            if len(top3_df) < 3:
                empty_rows = pd.DataFrame([['N/A', 'N/A']] * (3 - len(top3_df)), columns=top3_df.columns)
                top3_df = pd.concat([top3_df, empty_rows], ignore_index=True)
            top3_df.columns = ['출원인', '출원 건수']
            top3_table = top3_df.to_html(index=False, classes="table", escape=False) if not top3_df.empty else ""
            print("Generated top 3 table")

            # Define the stopwords
            stopwords = [' 주식회사', '주식회사 ', '주식회사', '(주)']

            # Function to remove stopwords
            def remove_stopwords(name, stopwords):
                if name is not None:
                    for stopword in stopwords:
                        name = name.replace(stopword, '')
                return name.strip() if name is not None else ''
                
            filtered_df_etc_domestic = filtered_df_patents[filtered_df_patents['applicant_lgrp'].isin(['etc', '국내기업'])]
            top5_df = filtered_df_etc_domestic['Applicant'].value_counts().head(10).reset_index()
            if len(top5_df) < 10:
                empty_rows = pd.DataFrame([['N/A', 'N/A']] * (10 - len(top5_df)), columns=top5_df.columns)
                top5_df = pd.concat([top5_df, empty_rows], ignore_index=True)
            top5_df.columns = ['출원인', '출원 건수']
            
            if not top5_df.empty:
                top5_df['출원인'] = top5_df.apply(
                    lambda row: f'<a href="https://www.wanted.co.kr/search?query={remove_stopwords(row["출원인"], stopwords)}&tab=company" target="_blank">{row["출원인"]}</a>',
                    axis=1
                )
                top5_table = top5_df.to_html(index=False, classes="table", escape=False)
                print("Generated top 5 table")
            else:
                top5_table = ""

            return render_template('Web.html', table=Markup(table_html), patents_length=len(df_patents), papers_length=len(df_papers),
                                   top3_table=Markup(top3_table), top5_table=Markup(top5_table),
                                   paper_table=Markup(paper_table_html),
                                   application_fields=application_fields, filter_type=filter_type,
                                   search_keyword=search_keyword, start_date=start_date, end_date=end_date, date=date, form=form)

        except Exception as e:
            print(f"Error during search: {e}")
            return render_template('Web.html', table="An error occurred: {}".format(e), top3_table="", top5_table="", paper_table="", date=date, form=form)

    print("Form validation failed or not submitted")
    return render_template('Web.html', date=date, form=form)

@app.route('/download', methods=['POST'])
@csrf.exempt
def download():
    global filtered_data_patents
    global filtered_data_papers

    # 특허 데이터 컬럼 선택
    patent_columns = ['Application Number', 'Application Date', 'Applicant', 'Title', 'Status']
    if not filtered_data_patents.empty:
        filtered_patent_data = filtered_data_patents[patent_columns]
        patent_csv = filtered_patent_data.to_csv(index=False)
    else:
        patent_csv = "No data available for patents"

    # 논문 데이터 컬럼 선택
    paper_columns = ['title', 'Abstract', 'submit_date']
    if not filtered_data_papers.empty:
        filtered_paper_data = filtered_data_papers[paper_columns]
        paper_csv = filtered_paper_data.to_csv(index=False)
    else:
        paper_csv = "No data available for papers"

    # 메모리 내에서 압축 파일 생성
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        zf.writestr("filtered_patents.csv", patent_csv)
        zf.writestr("filtered_papers.csv", paper_csv)

    memory_file.seek(0)

    # 응답 데이터 생성
    response = make_response(memory_file.read())
    response.headers["Content-Disposition"] = "attachment; filename=filtered_data.zip"
    response.headers["Content-Type"] = "application/zip"
    
    return response

@app.route('/plot')
@csrf.exempt
def plot():
    global filtered_data_patents
    global filtered_data_papers
    global df_patents
    global df_papers

    print("Plot endpoint called")  # 디버깅 로그 추가

    fig = plt.figure(figsize=(14, 14))
    gs = gridspec.GridSpec(9, 6)            # 2X3 Plot
    if (not filtered_data_patents.empty) & (not filtered_data_papers.empty):
        ax1 = fig.add_subplot(gs[:3, :3]); ax2 = fig.add_subplot(gs[:3, 3:]); ax3 = fig.add_subplot(gs[3:6, :3])
        ax4 = fig.add_subplot(gs[3:6, 3:]); ax5 = fig.add_subplot(gs[6:, :3]); ax6 = fig.add_subplot(gs[6:, 3:])
    elif (not filtered_data_patents.empty) & (filtered_data_papers.empty):
        ax1 = fig.add_subplot(gs[:3, :3]); ax3 = fig.add_subplot(gs[:3, 3:])
        ax4 = fig.add_subplot(gs[3:6, 1:4]); ax5 = fig.add_subplot(gs[6:, :3]); ax6 = fig.add_subplot(gs[6:, 3:])
    elif (filtered_data_patents.empty) & (not filtered_data_papers.empty):
        ax2 = fig.add_subplot(gs[:3, :3]); ax3 = fig.add_subplot(gs[:3, 3:])

    # Group the original data by year
    df_patents['application_date'] = pd.to_datetime(df_patents['application_date'], errors='coerce')
    df_patents['application_year'] = df_patents['application_date'].dt.year
    total_patent_counts = df_patents.groupby('application_year').size()

    df_papers['submit_date'] = pd.to_datetime(df_papers['submit_date'], errors='coerce')
    df_papers['submit_year'] = df_papers['submit_date'].dt.year
    total_paper_counts = df_papers.groupby('submit_year').size()


    if not filtered_data_patents.empty:
        filtered_data_patents['application_year'] = filtered_data_patents['Application Date'].dt.year
        filtered_counts = filtered_data_patents.groupby(['application_year', 'applicant_lgrp']).size().unstack(fill_value=0)
        filtered_patent_counts = filtered_data_patents.groupby('application_year').size()

        if not filtered_data_papers.empty:                  # Create a common index
            filtered_data_papers['submit_date'] = pd.to_datetime(filtered_data_papers['submit_date'], errors='coerce')
            filtered_data_papers['submit_year'] = filtered_data_papers['submit_date'].dt.year
            common_index = total_patent_counts.index.union(total_paper_counts.index).union(filtered_data_patents['application_year'].dropna().unique()).union(filtered_data_papers['submit_year'].dropna().unique())
            
        else: common_index = total_patent_counts.index.union(filtered_data_patents['application_year'].dropna().unique())
        # Reindex to ensure all indices match
        total_patent_counts = total_patent_counts.reindex(common_index, fill_value=0)
        filtered_patent_counts = filtered_patent_counts.reindex(common_index, fill_value=0)

        # Calculate the percentage
        filtered_patent_percentage = (filtered_patent_counts / total_patent_counts * 100).fillna(0)

        applicant_group_counts = filtered_data_patents['applicant_lgrp'].value_counts()

        top10_total = filtered_data_patents['Applicant'].value_counts().head(10).reset_index()
        top10_total.columns = ['Applicant', 'Patent Count']

        filtered_df_etc_domestic = filtered_data_patents[filtered_data_patents['applicant_lgrp'].isin(['etc', '국내기업'])]
        top10_etc_domestic = filtered_df_etc_domestic['Applicant'].value_counts().head(10).reset_index()
        top10_etc_domestic.columns = ['Applicant', 'Patent Count']

        filtered_counts.plot(kind='bar', stacked=True, ax=ax1)
        ax1.set_title('Number of Patents(Domestic) by Year')
        ax1.set_xlabel('Year', fontsize=14)
        ax1.set_ylabel('Number of Patents', fontsize=14)
        ax1.set_xticks(range(len(filtered_counts.index)))
        ax1.set_xticklabels(filtered_counts.index, rotation=45, ha='right', fontsize=12)
        ax1.legend(title="Groups")
        ax1.tick_params(axis='y', labelsize=12, direction='in', left=True, right=True)
        ax1.tick_params(axis='x', labelsize=12, direction='in', bottom=False, top=False)


        sns.lineplot(x=filtered_patent_percentage.index, y=filtered_patent_percentage, ax=ax3, color='blue', label='Patents', legend=False, marker='o', markersize=8, markerfacecolor='none', markeredgecolor='blue')
        ax3.set_title("Filtered Patent/Paper' Portions of Total by Year")
        ax3.set_xlabel('Year', fontsize=14)
        ax3.set_ylabel('Percentage of Patents [%]', fontsize=14, color='blue')
        ax3.tick_params(axis='x', labelsize=12, direction='in', bottom=True, top=False)
        ax3.tick_params(axis='y', labelsize=12, direction='in', left=True, right=False, colors='blue')

        # 그룹 이름을 리스트로 추출
        group_names = applicant_group_counts.index.tolist()
        # explode 값 설정: 기본적으로 모두 0으로 초기화
        explode = [0] * len(group_names)

        # 특정 그룹 이름에 대해 0.1 할당 (예: 'etc'와 '국내기업' 강조)
        for i, group in enumerate(group_names):
            if group in ['etc', '국내기업']:
                explode[i] = 0.1

        wedges, texts, autotexts = ax4.pie(applicant_group_counts, explode=explode, autopct='%1.1f%%', shadow=True, startangle=90)
        ax4.legend(wedges, applicant_group_counts.index, title="Groups", loc="center left", bbox_to_anchor=(1, 0.5, 0.1, 0.2), prop={'weight': 'bold'})
        ax4.set_aspect('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        # ax4.set_title('Applicant Distribution')
        #fig.text(0.78, 0.38, 'Applicant Distribution', ha='center', fontsize=14)
        ax4.annotate('Applicant Distribution', xy=(0, 0), xytext=(0, -140),textcoords='offset points', ha='center',fontsize=14)

        bars5 = sns.barplot(x='Patent Count', y='Applicant', data=top10_total, hue='Applicant', legend=False, orient='h', errorbar=None, width=0.7, palette='bone', ax=ax5)
        ax5.set_title('Top 10 Applicants')
        ax5.set_xlabel('Number of Patents', fontsize=14)
        ax5.set_ylabel('Applicants', fontsize=14)
        ax5.tick_params(axis='y', labelsize=12, direction='in', left=False, right=False)
        ax5.tick_params(axis='x', labelsize=12, direction='in', bottom=True, top=False)
        for container in bars5.containers:
            ax5.bar_label(container, padding=3)

        bars6 = sns.barplot(x='Patent Count', y='Applicant', data=top10_etc_domestic, hue='Applicant', legend=False, orient='h', errorbar=None, width=0.7, palette='nipy_spectral', ax=ax6)
        ax6.set_title('Top 10 Applicants: Domestic StartUps')
        ax6.set_xlabel('Number of Patents', fontsize=14)
        ax6.set_ylabel('Applicants', fontsize=14)
        ax6.tick_params(axis='y', labelsize=12, direction='in', left=False, right=False)
        ax6.tick_params(axis='x', labelsize=12, direction='in', bottom=True, top=False)
        for container in bars6.containers:
            ax6.bar_label(container, padding=3)

        # y축 레이블 글자수 제한 및 "(주)", "주식회사" 제거
        def shorten_labels(labels, max_length=7):
            shortened = []
            for label in labels:
                text = label.get_text().strip()
                text = re.sub(r'\s*주식회사\s*|\s*\(주\)\s*', '', text)
                if len(text) > max_length:
                    text = text[:max_length] + '...'
                shortened.append(text)
            return shortened

        ax5.set_yticks(ax5.get_yticks())  # Add this line to set the ticks explicitly
        ax5.set_yticklabels(shorten_labels(ax5.get_yticklabels()))
        ax6.set_yticks(ax6.get_yticks())
        ax6.set_yticklabels(shorten_labels(ax6.get_yticklabels()))

    else:
        print("No data available for patents-plotting")  # 디버깅 로그 추가

    if not filtered_data_papers.empty:
        filtered_paper_counts = filtered_data_papers.groupby(['submit_year']).size()

        if filtered_data_patents.empty:
            common_index = total_paper_counts.index.union(filtered_data_papers['submit_year'].dropna().unique())

        # Reindex to ensure all indices match
        total_paper_counts = total_paper_counts.reindex(common_index, fill_value=0)
        filtered_paper_counts = filtered_paper_counts.reindex(common_index, fill_value=0)

        # Calculate the percentage
        filtered_paper_percentage = (filtered_paper_counts / total_paper_counts * 100).fillna(0)


        filtered_paper_counts.plot(kind='bar', color=sns.color_palette("bright"), ax=ax2)  # pastel, deep, mated, bright, dark,colorblind
        ax2.set_title('Number of Papers(WorldWide) by Year')
        ax2.set_xlabel('Year', fontsize=14)
        ax2.set_ylabel('Number of Papers', fontsize=14)
        ax2.set_xticks(range(len(filtered_paper_counts.index)))
        ax2.set_xticklabels(filtered_paper_counts.index, rotation=45, ha='right', fontsize=12)
        ax2.tick_params(axis='y', labelsize=12, direction='in', left=True, right=True)
        ax2.tick_params(axis='x', labelsize=12, direction='in', bottom=False, top=False)

        # Line plot for percentages
        ax3_twin = ax3.twinx()
        sns.lineplot(x=filtered_paper_percentage.index, y=filtered_paper_percentage, ax=ax3_twin, color='green', label='Papers', legend=False, marker='o', markersize=8, markerfacecolor='none', markeredgecolor='green')
        ax3.set_title("Filtered Patent/Paper' Portions of Total by Year")
        ax3.set_xlabel('Year', fontsize=14)
        ax3_twin.set_ylabel('Percentage of Papers [%]', fontsize=14, color='green')
        ax3.tick_params(axis='x', labelsize=12, direction='in', bottom=True, top=False)
        ax3_twin.tick_params(axis='y', labelsize=12, direction='in', left=False, right=True, colors='green')

        #if not filtered_data_patents.empty:
        # Combine legends for ax3 and ax3_twin
        lines, labels = ax3.get_legend_handles_labels()
        lines2, labels2 = ax3_twin.get_legend_handles_labels()
        ax3.legend(lines + lines2, labels + labels2, loc='upper center', bbox_to_anchor=(0.5, 0.98), ncol=2, frameon=False)

    else:
        print("No data available for papers-plotting")  # 디버깅 로그 추가

    plt.tight_layout()
    # Save the plot as an image file
    image_filename = 'static/plot_01.png'
    fig.savefig(image_filename, bbox_inches='tight')
    plt.close(fig)

    print(f"Plot saved to {image_filename}")  # 디버깅 로그 추가
    return render_template('plot.html', plot_image=image_filename)


if __name__ == '__main__':
    app.run(debug=True)

