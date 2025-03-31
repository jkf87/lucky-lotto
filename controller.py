import os
import sys
from dotenv import load_dotenv

import auth
import lotto645
import win720
import notification
import time

# 로또 6/45 구매 함수
def buy_lotto645(authCtrl: auth.AuthController, cnt: int, mode: str):
    # Lotto645 객체 생성
    lotto = lotto645.Lotto645()
    # 구매 모드 설정 (AUTO/MANUAL)
    _mode = lotto645.Lotto645Mode[mode.upper()]
    # 로또 구매 요청 및 응답 수신
    response = lotto.buy_lotto645(authCtrl, cnt, _mode)
    # 잔액 조회하여 응답에 추가
    response['balance'] = lotto.get_balance(auth_ctrl=authCtrl)
    return response

# 로또 6/45 당첨 확인 함수
def check_winning_lotto645(authCtrl: auth.AuthController) -> dict:
    lotto = lotto645.Lotto645()
    # 당첨 내역 조회
    item = lotto.check_winning(authCtrl)
    return item

# 연금복권 720+ 구매 함수
def buy_win720(authCtrl: auth.AuthController, username: str):
    # Win720 객체 생성
    pension = win720.Win720()
    # 연금복권 구매 요청 및 응답 수신
    response = pension.buy_Win720(authCtrl, username)
    # 잔액 조회하여 응답에 추가
    response['balance'] = pension.get_balance(auth_ctrl=authCtrl)
    return response

# 연금복권 720+ 당첨 확인 함수
def check_winning_win720(authCtrl: auth.AuthController) -> dict:
    pension = win720.Win720()
    # 당첨 내역 조회
    item = pension.check_winning(authCtrl)
    return item

# 알림 메시지 전송 함수
def send_message(mode: int, lottery_type: int, response: dict, webhook_url: str):
    # Notification 객체 생성
    notify = notification.Notification()

    # mode: 0=당첨확인, 1=구매알림
    # lottery_type: 0=로또6/45, 1=연금복권720+
    if mode == 0:  # 당첨 확인 알림
        if lottery_type == 0:  # 로또 6/45
            notify.send_lotto_winning_message(response, webhook_url)
        else:  # 연금복권 720+
            notify.send_win720_winning_message(response, webhook_url)
    elif mode == 1:  # 구매 알림
        if lottery_type == 0:  # 로또 6/45
            notify.send_lotto_buying_message(response, webhook_url)
        else:  # 연금복권 720+
            notify.send_win720_buying_message(response, webhook_url)

# 당첨 확인 메인 함수
def check():
    # 환경변수 로드
    load_dotenv()

    # 환경변수에서 계정 정보 및 웹훅 URL 가져오기
    username = os.environ.get('USERNAME')
    password = os.environ.get('PASSWORD')
    slack_webhook_url = os.environ.get('SLACK_WEBHOOK_URL') 
    discord_webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')

    # 인증 컨트롤러 생성 및 로그인
    globalAuthCtrl = auth.AuthController()
    globalAuthCtrl.login(username, password)
    
    # 로또 6/45 당첨 확인 및 알림 전송
    response = check_winning_lotto645(globalAuthCtrl)
    send_message(0, 0, response=response, webhook_url=discord_webhook_url)

    # API 요청 간 간격 두기
    time.sleep(10)
    
    # 연금복권 720+ 당첨 확인 및 알림 전송
    response = check_winning_win720(globalAuthCtrl)
    send_message(0, 1, response=response, webhook_url=discord_webhook_url)

# 복권 구매 메인 함수
def buy(): 
    # 환경변수 로드
    load_dotenv() 

    # 환경변수에서 계정 정보, 구매 수량 및 웹훅 URL 가져오기
    username = os.environ.get('USERNAME')
    password = os.environ.get('PASSWORD')
    count = int(os.environ.get('COUNT'))
    discord_webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
    # 환경변수에서 연금복권 구매 여부 확인 (기본값: 구매안함)
    buy_win720 = os.environ.get('BUY_WIN720', 'false').lower() == 'true'
    mode = "AUTO"  # 자동 구매 모드 설정

    # 인증 컨트롤러 생성 및 로그인
    globalAuthCtrl = auth.AuthController()
    globalAuthCtrl.login(username, password)

    # 로또 6/45 구매 및 알림 전송
    response = buy_lotto645(globalAuthCtrl, count, mode) 
    send_message(1, 0, response=response, webhook_url=discord_webhook_url)

    # 연금복권 구매 여부 확인
    if buy_win720:
        # API 요청 간 간격 두기
        time.sleep(10)

        # 연금복권 720+ 구매 및 알림 전송
        response = buy_win720(globalAuthCtrl, username) 
        send_message(1, 1, response=response, webhook_url=discord_webhook_url)

# 명령줄에서 실행 시 처리하는 함수
def run():
    # 매개변수가 없으면 사용법 출력
    if len(sys.argv) < 2:
        print("Usage: python controller.py [buy|check]")
        return

    # buy: 복권 구매, check: 당첨 확인
    if sys.argv[1] == "buy":
        buy()
    elif sys.argv[1] == "check":
        check()
  

# 스크립트 직접 실행 시 엔트리 포인트
if __name__ == "__main__":
    run()
