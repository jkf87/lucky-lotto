import datetime
import json

from datetime import timedelta
from enum import Enum

from bs4 import BeautifulSoup as BS

import auth
from HttpClient import HttpClientSingleton

class Lotto645Mode(Enum):
    AUTO = 1      # 자동 번호 선택 모드
    MANUAL = 2    # 수동 번호 선택 모드
    BUY = 10      # 구매 모드
    CHECK = 20    # 당첨 확인 모드

class Lotto645:

    # 로또 웹사이트 요청에 필요한 기본 헤더 정보
    _REQ_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '" Not;A Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
        "sec-ch-ua-mobile": "?0",
        "Upgrade-Insecure-Requests": "1",
        "Origin": "https://ol.dhlottery.co.kr",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Referer": "https://ol.dhlottery.co.kr/olotto/game/game645.do",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8,ko-KR;q=0.7",
    }

    def __init__(self):
        # HTTP 클라이언트 인스턴스 가져오기
        self.http_client = HttpClientSingleton.get_instance()

    def buy_lotto645(
        self, 
        auth_ctrl: auth.AuthController, 
        cnt: int, 
        mode: Lotto645Mode
    ) -> dict:
        # 로또 구매 메인 함수
        assert type(auth_ctrl) == auth.AuthController
        assert type(cnt) == int and 1 <= cnt <= 5
        assert type(mode) == Lotto645Mode

        # 인증 정보로 요청 헤더 생성
        headers = self._generate_req_headers(auth_ctrl)
        # 로또 구매에 필요한 정보(IP, 추첨일, 지급기한) 가져오기
        requirements = self._getRequirements(headers)

        # 선택한 모드에 따라 구매 데이터 생성 (자동 또는 수동)
        data = (
            self._generate_body_for_auto_mode(cnt, requirements)
            if mode == Lotto645Mode.AUTO
            else self._generate_body_for_manual(cnt)
        )

        # 실제 구매 요청 보내기
        body = self._try_buying(headers, data)

        # 구매 결과 처리 및 반환
        self._show_result(body)
        return body

    def _generate_req_headers(self, auth_ctrl: auth.AuthController) -> dict:
        # 인증 정보를 포함한 요청 헤더 생성
        assert type(auth_ctrl) == auth.AuthController

        return auth_ctrl.add_auth_cred_to_headers(self._REQ_HEADERS)

    def _generate_body_for_auto_mode(self, cnt: int, requirements: list) -> dict:
        # 자동 번호 선택 모드에서 구매 요청 본문 생성
        assert type(cnt) == int and 1 <= cnt <= 5

        # 로또 게임 슬롯 이름 (A부터 E까지)
        SLOTS = [
            "A",
            "B",
            "C",
            "D",
            "E",
        ]  

        return {
            "round": self._get_round(),                # 현재 회차 정보
            "direct": requirements[0],                 # 직접 IP 정보
            "nBuyAmount": str(1000 * cnt),             # 구매 금액 (1게임당 1000원)
            "param": json.dumps(
                [
                    {"genType": "0", "arrGameChoiceNum": None, "alpabet": slot}
                    for slot in SLOTS[:cnt]
                ]
            ),                                         # 게임 정보 (자동 선택)
            'ROUND_DRAW_DATE' : requirements[1],       # 추첨일자
            'WAMT_PAY_TLMT_END_DT' : requirements[2],  # 지급기한
            "gameCnt": cnt                             # 구매할 게임 수
        }

    def _generate_body_for_manual(self, cnt: int) -> dict:
        # 수동 번호 선택 모드에서 구매 요청 본문 생성 (아직 구현되지 않음)
        assert type(cnt) == int and 1 <= cnt <= 5

        raise NotImplementedError()

    def _getRequirements(self, headers: dict) -> list: 
        # 로또 구매에 필요한 정보(IP, 추첨일, 지급기한) 가져오기
        org_headers = headers.copy()

        headers["Referer"] ="https://ol.dhlottery.co.kr/olotto/game/game645.do"
        headers["Content-Type"] = "application/json; charset=UTF-8"
        headers["X-Requested-With"] ="XMLHttpRequest"


		#no param needed at now
        # 직접 IP 정보 가져오기
        res = self.http_client.post(
            url="https://ol.dhlottery.co.kr/olotto/game/egovUserReadySocket.json", 
            headers=headers
        )
        
        direct = json.loads(res.text)["ready_ip"]
        
        # 추첨일과 지급기한 정보 가져오기
        res = self.http_client.post(
            url="https://ol.dhlottery.co.kr/olotto/game/game645.do", 
            headers=org_headers
        )
        html = res.text
        soup = BS(
            html, "html5lib"
        )
        draw_date = soup.find("input", id="ROUND_DRAW_DATE").get('value')
        tlmt_date = soup.find("input", id="WAMT_PAY_TLMT_END_DT").get('value')

        return [direct, draw_date, tlmt_date]

    def _get_round(self) -> str:
        # 현재 회차 정보 가져오기 (마지막 추첨 회차 + 1)
        res = self.http_client.get("https://www.dhlottery.co.kr/common.do?method=main")
        html = res.text
        soup = BS(
            html, "html5lib"
        )  # 'html5lib' : in case that the html don't have clean tag pairs
        last_drawn_round = int(soup.find("strong", id="lottoDrwNo").text)
        return str(last_drawn_round + 1)

    def get_balance(self, auth_ctrl: auth.AuthController) -> str: 
        # 사용자 계정의 잔액 조회
        headers = self._generate_req_headers(auth_ctrl)
        res = self.http_client.post(
            url="https://dhlottery.co.kr/userSsl.do?method=myPage", 
            headers=headers
        )

        html = res.text
        soup = BS(
            html, "html5lib"
        )
        balance = soup.find("p", class_="total_new").find('strong').text
        return balance
        
    def _try_buying(self, headers: dict, data: dict) -> dict:
        # 실제 로또 구매 요청 보내기
        assert type(headers) == dict
        assert type(data) == dict

        headers["Content-Type"]  = "application/x-www-form-urlencoded; charset=UTF-8"

        res = self.http_client.post(
            "https://ol.dhlottery.co.kr/olotto/game/execBuy.do",
            headers=headers,
            data=data,
        )
        res.encoding = "utf-8"
        return json.loads(res.text)

    def check_winning(self, auth_ctrl: auth.AuthController) -> dict:
        # 당첨 내역 확인하기
        assert type(auth_ctrl) == auth.AuthController

        # 인증 정보로 요청 헤더 생성
        headers = self._generate_req_headers(auth_ctrl)

        # 검색 기간 설정 (최근 1주일)
        parameters = self._make_search_date()

        # 당첨 내역 조회 요청 데이터
        data = {
            "nowPage": 1, 
            "searchStartDate": parameters["searchStartDate"],
            "searchEndDate": parameters["searchEndDate"],
            "winGrade": 2,
            "lottoId": "LO40", 
            "sortOrder": "DESC"
        }

        # 기본 결과 데이터 (당첨 내역 없음)
        result_data = {
            "data": "no winning data"
        }

        try:
            # 당첨 내역 목록 조회
            res = self.http_client.post(
                "https://dhlottery.co.kr/myPage.do?method=lottoBuyList",
                headers=headers,
                data=data
            )

            html = res.text
            soup = BS(html, "html5lib")

            winnings = soup.find("table", class_="tbl_data tbl_data_col").find_all("tbody")[0].find_all("td")

            # 상세 정보 URL에서 필요한 파라미터 추출
            get_detail_info = winnings[3].find("a").get("href")

            order_no, barcode, issue_no = get_detail_info.split("'")[1::2]
            url = f"https://dhlottery.co.kr/myPage.do?method=lotto645Detail&orderNo={order_no}&barcode={barcode}&issueNo={issue_no}"

            # 상세 정보 조회
            response = self.http_client.get(url)

            soup = BS(response.text, "html5lib")

            # 로또 결과 정보 파싱
            lotto_results = []

            for li in soup.select("div.selected li"):
                label = li.find("strong").find_all("span")[0].text.strip()
                status = li.find("strong").find_all("span")[1].text.strip().replace("낙첨","0등")
                nums = li.select("div.nums > span")

                status = " ".join(status.split())

                # 번호 정보 포맷팅
                formatted_nums = []
                for num in nums:
                    ball = num.find("span", class_="ball_645")
                    if ball:
                        formatted_nums.append(f"✨{ball.text.strip()}")
                    else:
                        formatted_nums.append(num.text.strip())

                lotto_results.append({
                    "label": label,
                    "status": status,
                    "result": formatted_nums
                })

            # 당첨 내역이 없는 경우 기본 결과 반환
            if len(winnings) == 1:
                return result_data

            # 당첨 내역 정보 구성
            result_data = {
                "round": winnings[2].text.strip(),         # 회차
                "money": winnings[6].text.strip(),         # 당첨금액
                "purchased_date": winnings[0].text.strip(), # 구매일자
                "winning_date": winnings[7].text.strip(),   # 당첨일자
                "lotto_details": lotto_results              # 상세 번호 정보
            }
        except:
            pass

        return result_data
    
    def _make_search_date(self) -> dict:
        # 검색 기간 설정 (최근 1주일)
        today = datetime.datetime.today()
        today_str = today.strftime("%Y%m%d")
        weekago = today - timedelta(days=7)
        weekago_str = weekago.strftime("%Y%m%d")
        return {
            "searchStartDate": weekago_str,
            "searchEndDate": today_str
        }

    def _show_result(self, body: dict) -> None:
        # 구매 결과 처리
        assert type(body) == dict

        # 로그인 상태 확인
        if body.get("loginYn") != "Y":
            return

        # 구매 성공 여부 확인
        result = body.get("result", {})
        if result.get("resultMsg", "FAILURE").upper() != "SUCCESS":    
            return
