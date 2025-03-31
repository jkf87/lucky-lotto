import copy
import requests
from HttpClient import HttpClientSingleton

# 동행복권 로그인 및 인증 관리를 담당하는 클래스
class AuthController:
    # 웹 요청에 사용될 기본 HTTP 헤더 정보 (실제 브라우저처럼 보이기 위한 설정)
    _REQ_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '" Not;A Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
        "sec-ch-ua-mobile": "?0",
        "Upgrade-Insecure-Requests": "1",
        "Origin": "https://dhlottery.co.kr",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Referer": "https://dhlottery.co.kr/",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8,ko-KR;q=0.7",
    }

    # 인증 세션 ID를 저장하는 변수
    _AUTH_CRED = ""

    # 초기화 함수: HTTP 클라이언트 싱글톤 인스턴스를 가져옴
    def __init__(self):
        self.http_client = HttpClientSingleton.get_instance()

    # 실제 로그인 프로세스를 수행하는 메인 함수
    def login(self, user_id: str, password: str):
        assert type(user_id) == str
        assert type(password) == str

        # 로그인 전 기본 세션 ID 획득
        default_auth_cred = (
            self._get_default_auth_cred()
        )  # JSessionId 값을 받아온 후, 그 값에 인증을 씌우는 방식

        # 기본 세션 ID로 요청 헤더 생성
        headers = self._generate_req_headers(default_auth_cred)

        # 로그인 요청 본문 데이터 생성 (ID, 비밀번호 포함)
        data = self._generate_body(user_id, password)

        # 로그인 요청 전송
        _res = self._try_login(headers, data)  # 새로운 값의 JSESSIONID가 내려오는데, 이 값으론 로그인 안됨

        # 획득한 세션 ID를 인증 정보로 업데이트
        self._update_auth_cred(default_auth_cred)

    # 기존 헤더에 인증 세션 정보를 추가하는 함수
    def add_auth_cred_to_headers(self, headers: dict) -> str:
        assert type(headers) == dict

        copied_headers = copy.deepcopy(headers)
        copied_headers["Cookie"] = f"JSESSIONID={self._AUTH_CRED}"
        return copied_headers

    # 웹사이트 방문을 통해 기본 세션 ID를 획득하는 함수
    def _get_default_auth_cred(self):
        res = self.http_client.get(
            "https://dhlottery.co.kr/gameResult.do?method=byWin&wiselog=H_C_1_1"
        )

        return self._get_j_session_id_from_response(res)

    # HTTP 응답에서 JSESSIONID 쿠키 값을 추출하는 함수
    def _get_j_session_id_from_response(self, res: requests.Response):
        assert type(res) == requests.Response

        for cookie in res.cookies:
            if cookie.name == "JSESSIONID":
                return cookie.value

        raise KeyError("JSESSIONID cookie is not set in response")

    # 세션 ID를 포함한 요청 헤더를 생성하는 함수
    def _generate_req_headers(self, j_session_id: str):
        assert type(j_session_id) == str

        copied_headers = copy.deepcopy(self._REQ_HEADERS)
        copied_headers["Cookie"] = f"JSESSIONID={j_session_id}"
        return copied_headers

    # 로그인 요청 본문(폼 데이터)을 생성하는 함수
    def _generate_body(self, user_id: str, password: str):
        assert type(user_id) == str
        assert type(password) == str

        return {
            "returnUrl": "https://dhlottery.co.kr/common.do?method=main",
            "userId": user_id,
            "password": password,
            "checkSave": "on",
            "newsEventYn": "",
        }

    # 로그인 요청을 실제로 보내는 함수
    def _try_login(self, headers: dict, data: dict):
        assert type(headers) == dict
        assert type(data) == dict

        res = self.http_client.post(
            "https://www.dhlottery.co.kr/userSsl.do?method=login",
            headers=headers,
            data=data,
        )
        return res

    # 로그인 후 인증 세션 ID를 저장하는 함수
    def _update_auth_cred(self, j_session_id: str) -> None:
        assert type(j_session_id) == str

        # TODO: judge whether login is success or not
        # 로그인 실패해도 jsession 값이 갱신되기 때문에, 마이페이지 방문 등으로 판단해야 할 듯
        # + 비번 5번 틀렸을 경우엔 비번 정확해도 로그인 실패함
        self._AUTH_CRED = j_session_id
