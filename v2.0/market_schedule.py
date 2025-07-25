# ================================================================================
# 🔥 완전한 시장 대기모드 시스템
# ================================================================================

import requests
import ntplib
from datetime import datetime, timedelta, date
import time
import json
import os

# 한국거래소 휴장일 API (또는 수동 관리)
HOLIDAYS_2025 = [
    "2025-01-01",  # 신정
    "2025-01-28",  # 설날 연휴
    "2025-01-29",  # 설날
    "2025-01-30",  # 설날 연휴
    "2025-03-01",  # 삼일절
    "2025-05-05",  # 어린이날
    "2025-05-06",  # 부처님오신날 대체공휴일
    "2025-06-06",  # 현충일
    "2025-08-15",  # 광복절
    "2025-09-06",  # 추석 연휴
    "2025-09-07",  # 추석 연휴
    "2025-09-08",  # 추석
    "2025-09-09",  # 추석 연휴
    "2025-10-03",  # 개천절
    "2025-10-09",  # 한글날
    "2025-12-25",  # 성탄절
]

def get_ntp_time():
    """NTP 서버에서 정확한 시간 가져오기"""
    try:
        ntp_servers = [
            'time.google.com',
            'pool.ntp.org', 
            'time.nist.gov',
            'time.windows.com'
        ]
        
        for server in ntp_servers:
            try:
                client = ntplib.NTPClient()
                response = client.request(server, version=3, timeout=5)
                ntp_time = datetime.fromtimestamp(response.tx_time)
                print(f"🌐 NTP 시간 동기화 완료: {server} ({ntp_time.strftime('%Y-%m-%d %H:%M:%S')})")
                return ntp_time
            except Exception:
                continue
                
        print("⚠️  NTP 동기화 실패 - 로컬 시간 사용")
        return datetime.now()
        
    except Exception as e:
        print(f"⚠️  시간 동기화 오류: {e} - 로컬 시간 사용")
        return datetime.now()

def is_market_holiday(check_date=None):
    """한국거래소 휴장일 여부 확인"""
    if check_date is None:
        check_date = get_ntp_time().date()
    
    # 문자열로 변환하여 비교
    date_str = check_date.strftime('%Y-%m-%d')
    
    # 주말 체크
    weekday = check_date.weekday()  # 0=월요일, 6=일요일
    if weekday >= 5:  # 토요일(5), 일요일(6)
        return True, "주말"
    
    # 공휴일 체크
    if date_str in HOLIDAYS_2025:
        return True, "공휴일"
    
    return False, "개장일"

def get_next_trading_day():
    """다음 개장일 찾기"""
    current_date = get_ntp_time().date()
    
    # 오늘부터 최대 10일 후까지 검색
    for i in range(10):
        check_date = current_date + timedelta(days=i)
        is_holiday, reason = is_market_holiday(check_date)
        
        if not is_holiday:
            return check_date, reason
    
    # 10일 후에도 개장일이 없으면 (연휴가 매우 긴 경우)
    return current_date + timedelta(days=1), "추정개장일"

def is_trading_session():
    """현재 장시간인지 확인"""
    now = get_ntp_time()
    
    # 1. 휴장일 체크
    is_holiday, holiday_reason = is_market_holiday(now.date())
    if is_holiday:
        return False, f"휴장일 ({holiday_reason})"
    
    # 2. 시간대 체크
    current_time = now.time()
    
    # 장 시작 전 (00:00 ~ 09:04)
    if current_time < datetime.strptime("09:05", "%H:%M").time():
        return False, "장시작전"
    
    # 장중 (09:05 ~ 15:30)
    elif datetime.strptime("09:05", "%H:%M").time() <= current_time <= datetime.strptime("15:30", "%H:%M").time():
        return True, "장중"
    
    # 장 종료 후 (15:31 ~ 23:59)
    else:
        return False, "장종료"

def calculate_time_until_market():
    """장 시작까지 남은 시간 계산"""
    now = get_ntp_time()
    
    # 오늘이 개장일인지 확인
    is_holiday, holiday_reason = is_market_holiday(now.date())
    
    if not is_holiday:
        # 오늘이 개장일이면
        market_start_today = now.replace(hour=9, minute=5, second=0, microsecond=0)
        
        if now < market_start_today:
            # 오늘 장 시작 전
            return market_start_today - now, "오늘"
    
    # 오늘이 휴장일이거나 장 종료 후라면 다음 개장일 찾기
    next_trading_date, _ = get_next_trading_day()
    
    # 다음 개장일의 9시 5분
    if next_trading_date == now.date():
        # 오늘이 개장일인데 장 종료 후
        next_market_start = (now + timedelta(days=1)).replace(hour=9, minute=5, second=0, microsecond=0)
        next_trading_date, _ = get_next_trading_day()  # 내일이 개장일인지 재확인
        next_market_start = datetime.combine(next_trading_date, datetime.strptime("09:05", "%H:%M").time())
    else:
        next_market_start = datetime.combine(next_trading_date, datetime.strptime("09:05", "%H:%M").time())
    
    time_diff = next_market_start - now
    return time_diff, next_trading_date.strftime('%Y-%m-%d')

def print_market_status():
    """시장 상태 출력"""
    now = get_ntp_time()
    is_trading, status = is_trading_session()
    
    print("="*80)
    print("📈 한국거래소 시장 상태")
    print("="*80)
    print(f"🕐 현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if is_trading:
        print(f"🟢 상태: {status}")
        print("🎯 매매 실행 가능!")
    else:
        print(f"🔴 상태: {status}")
        
        time_diff, target_date = calculate_time_until_market()
        
        if target_date == "오늘":
            print(f"⏰ 장 시작까지: {format_time_diff(time_diff)}")
        else:
            print(f"📅 다음 개장일: {target_date}")
            print(f"⏰ 개장까지: {format_time_diff(time_diff)}")
    
    print("="*80)

def format_time_diff(time_diff):
    """시간 차이를 읽기 쉽게 포맷"""
    total_seconds = int(time_diff.total_seconds())
    
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}일")
    if hours > 0:
        parts.append(f"{hours}시간")
    if minutes > 0:
        parts.append(f"{minutes}분")
    if seconds > 0 and days == 0:  # 일 단위가 없을 때만 초 표시
        parts.append(f"{seconds}초")
    
    return " ".join(parts) if parts else "0초"

def wait_for_market_with_countdown():
    """시장 개장까지 카운트다운 대기"""
    print_market_status()
    
    is_trading, status = is_trading_session()
    if is_trading:
        print("✅ 이미 장중입니다 - 매매 시작!")
        return
    
    print("\n⏳ 시장 개장 대기 모드 시작...")
    
    # 8시 50분부터 토큰 체크 활성화
    token_check_started = False
    
    while True:
        now = get_ntp_time()
        time_diff, target_date = calculate_time_until_market()
        
        # 음수면 이미 장시간
        if time_diff.total_seconds() <= 0:
            print("\n🟢 장 시작! 매매 시작합니다!")
            break
        
        # 8시 50분 토큰 체크
        if now.hour == 8 and 50 <= now.minute <= 55 and not token_check_started:
            print("\n🔑 [08:50] 토큰 사전 체크 시작...")
            token_check_started = True
            # 여기서 토큰 체크 로직 실행 가능
        
        # 실시간 카운트다운 표시
        formatted_time = format_time_diff(time_diff)
        
        if target_date == "오늘":
            countdown_msg = f"⏰ 장 시작까지: {formatted_time}"
        else:
            countdown_msg = f"📅 {target_date} 개장까지: {formatted_time}"
        
        print(f"\r{countdown_msg} (현재: {now.strftime('%H:%M:%S')})", end="", flush=True)
        
        time.sleep(1)  # 1초마다 업데이트

# ================================================================================
# 🔥 사용 예시
# ================================================================================

if __name__ == "__main__":
    # 시장 상태 확인
    print_market_status()
    
    # 개장 대기 (테스트용 - 실제로는 주석 처리)
    # wait_for_market_with_countdown()
    
    # 다음 개장일 확인
    next_date, reason = get_next_trading_day()
    print(f"\n📅 다음 개장일: {next_date} ({reason})")
    
    # 휴장일 여부 확인
    is_holiday, holiday_reason = is_market_holiday()
    print(f"📊 오늘 상태: {'휴장일' if is_holiday else '개장일'} ({holiday_reason})")