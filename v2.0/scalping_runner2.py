import asyncio
import sys
import os
import time
from datetime import datetime, timedelta, date
from tabulate import tabulate
import json
import requests
import ntplib

# ================================================================================
# 🔥 완전한 시장 대기모드 시스템 (리팩토링)
# ================================================================================

# 한국거래소 휴장일 (2025년)
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

# 🔥 글로벌 시간 관리 변수
_ntp_time_offset = 0  # NTP와 로컬 시간의 차이
_last_ntp_sync = 0    # 마지막 NTP 동기화 시각
_ntp_sync_interval = 3600  # 1시간마다 재동기화

def sync_ntp_time(force=False):
    """NTP 시간 동기화 (1시간마다 또는 강제 동기화)"""
    global _ntp_time_offset, _last_ntp_sync
    
    current_time = time.time()
    
    # 강제 동기화가 아니고, 마지막 동기화로부터 1시간이 지나지 않았으면 스킵
    if not force and (current_time - _last_ntp_sync) < _ntp_sync_interval:
        return True
    
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
                ntp_timestamp = response.tx_time
                local_timestamp = time.time()
                
                _ntp_time_offset = ntp_timestamp - local_timestamp
                _last_ntp_sync = current_time
                
                # 동기화 성공 메시지 (조건부 출력)
                ntp_time = datetime.fromtimestamp(ntp_timestamp)
                time_diff = abs(_ntp_time_offset)
                
                if time_diff > 2:  # 2초 이상 차이날 때만 경고
                    print(f"⚠️  시간 차이 감지: {time_diff:.1f}초 - NTP 동기화 적용 ({server})")
                elif force:  # 강제 동기화일 때만 성공 메시지
                    print(f"🌐 NTP 시간 동기화 완료: {server} ({ntp_time.strftime('%Y-%m-%d %H:%M:%S')})")
                
                return True
                
            except Exception:
                continue
                
        # 모든 서버 실패 시
        if force:
            print("⚠️  NTP 동기화 실패 - 로컬 시간 사용")
        return False
        
    except Exception as e:
        if force:
            print(f"⚠️  시간 동기화 오류: {e} - 로컬 시간 사용")
        return False

def get_ntp_time():
    """NTP 동기화된 시간 반환 (효율적 버전)"""
    # 첫 동기화 또는 1시간마다 재동기화
    sync_ntp_time()
    
    # 오프셋을 적용한 현재 시간 반환
    return datetime.fromtimestamp(time.time() + _ntp_time_offset)

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
        # 오늘이 개장일인데 장 종료 후 - 다음 개장일 재계산
        tomorrow = now.date() + timedelta(days=1)
        for i in range(10):
            check_date = tomorrow + timedelta(days=i)
            is_holiday, _ = is_market_holiday(check_date)
            if not is_holiday:
                next_trading_date = check_date
                break
    
    next_market_start = datetime.combine(next_trading_date, datetime.strptime("09:05", "%H:%M").time())
    time_diff = next_market_start - now
    return time_diff, next_trading_date.strftime('%Y-%m-%d')

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

def print_market_status():
    """시장 상태 출력"""
    now = get_ntp_time()
    is_trading, status = is_trading_session()
    
    print("="*80)
    print("📈 한국거래소 시장 상태")
    print("="*80)
    print(f"🕐 현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')} (NTP)")
    
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

def wait_for_market_with_countdown():
    """🔥 리팩토링: 효율적인 시장 개장 대기 (NTP 최적화)"""
    
    # 🔥 초기 NTP 동기화 (한 번만)
    print("🌐 NTP 시간 동기화 중...")
    sync_ntp_time(force=True)
    
    print_market_status()
    
    is_trading, status = is_trading_session()
    if is_trading:
        print("✅ 이미 장중입니다 - 매매 시작!")
        return
    
    print("\n⏳ 시장 개장 대기 모드 시작...")
    print("🔑 08:50부터 토큰 사전 체크가 시작됩니다.")
    print("💡 Ctrl+C로 언제든 종료 가능합니다.")
    
    # 🔥 최적화된 대기 루프
    token_check_started = False
    last_minute = -1
    last_sync_hour = -1
    
    try:
        while True:
            now = get_ntp_time()
            time_diff, target_date = calculate_time_until_market()
            
            # 음수면 이미 장시간
            if time_diff.total_seconds() <= 0:
                print(f"\n🟢 장 시작! 매매 시작합니다! ({now.strftime('%H:%M:%S')})")
                break
            
            # 🔥 시간별 NTP 재동기화 (조용히)
            if now.hour != last_sync_hour:
                sync_ntp_time()  # 강제하지 않음 (조용한 동기화)
                last_sync_hour = now.hour
            
            # 8시 50분 토큰 체크 (1회만)
            if now.hour == 8 and 50 <= now.minute <= 55 and not token_check_started:
                print(f"\n🔑 [08:{now.minute:02d}] 토큰 사전 체크 시작...")
                token_check_started = True
                
                try:
                    from scalping_engine import get_valid_access_token
                    token = get_valid_access_token()
                    print("✅ 토큰 사전 체크 완료!")
                except Exception as e:
                    print(f"⚠️  토큰 사전 체크 실패: {e}")
            
            # 🔥 분이 바뀔 때마다 상태 업데이트 (깔끔한 출력)
            if now.minute != last_minute:
                last_minute = now.minute
                formatted_time = format_time_diff(time_diff)
                
                if target_date == "오늘":
                    status_msg = f"\n⏰ [{now.strftime('%H:%M')}] 장 시작까지: {formatted_time}"
                else:
                    status_msg = f"\n📅 [{now.strftime('%H:%M')}] {target_date} 개장까지: {formatted_time}"
                
                print(status_msg)
            
            # 🔥 깔끔한 실시간 카운트다운 (한 줄 업데이트)
            formatted_time = format_time_diff(time_diff)
            current_time_str = now.strftime('%H:%M:%S')
            
            # 진행 표시를 위한 회전 문자
            spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            spinner = spinner_chars[now.second % len(spinner_chars)]
            
            print(f"\r{spinner} {current_time_str} | 대기중... {formatted_time}     ", end="", flush=True)
            
            time.sleep(1)  # 1초마다 업데이트
            
    except KeyboardInterrupt:
        print(f"\n\n👋 사용자가 대기를 중단했습니다.")
        raise

# ================================================================================
# 🔥 V2.0 실행 모드 선택 (기존 유지)
# ================================================================================

def select_trading_mode():
    """거래 모드 선택 메뉴"""
    print("="*80)
    print("🔥 V2.0 단타 매매 시스템")
    print("="*80)
    print("실행 모드를 선택하세요:")
    print()
    print("1️⃣  테스트 모드 (시간 제약 없음, 빠른 루프)")
    print("   - 언제든지 실행 가능")
    print("   - 30초 간격으로 빠른 테스트")
    print("   - 강제청산 없음")
    print()
    print("2️⃣  실제 매매 모드 (장시간 준수)")
    print("   - 시장 대기모드 포함")
    print("   - 공휴일/주말 자동 감지")
    print("   - NTP 시간 동기화")
    print("   - 09:05~14:00 매매시간 준수")
    print("   - 15:10 강제청산")
    print()
    print("0️⃣  종료")
    print("="*80)
    
    while True:
        try:
            choice = input("선택하세요 (1/2/0): ").strip()
            
            if choice == "1":
                os.environ['SCALPING_TEST_MODE'] = '1'
                print("\n✅ 테스트 모드 선택됨!")
                print("⚡ 시간 제약 없이 매매 실행")
                return True
            
            elif choice == "2":
                if 'SCALPING_TEST_MODE' in os.environ:
                    del os.environ['SCALPING_TEST_MODE']
                print("\n✅ 실제 매매 모드 선택됨!")
                print("📈 완전한 시장 대기모드 포함")
                return True
            
            elif choice == "0":
                print("\n👋 시스템 종료")
                return False
            
            else:
                print("❌ 잘못된 선택입니다. 1, 2, 또는 0을 입력하세요.")
                
        except KeyboardInterrupt:
            print("\n👋 시스템 종료")
            return False

# ScalpingEngine import
from scalping_engine import (
    ScalpingEngine,
    find_scalping_targets,
    ensure_token_for_full_trading_day,
    get_valid_access_token,
    ensure_parent_dir,
    is_trading_time_safe,    # 🔥 수정된 함수
    is_force_sell_time_safe, # 🔥 수정된 함수
    is_test_mode,           # 🔥 새 함수
    CONDITION_SEQ_LIST,
    MAX_POSITIONS,
    TRADING_START_HOUR,
    TRADING_END_HOUR,
    FORCE_SELL_HOUR,
    FORCE_SELL_MINUTE,
    LOOP_INTERVAL,
    INITIAL_CAPITAL
)

# ================================================================================
# V2.0 단타 매매 시스템 설정 (기존 유지)
# ================================================================================

def print_system_header():
    """시스템 시작 헤더 출력"""
    now = get_ntp_time()  # 🔥 NTP 시간 사용
    print("="*100, flush=True)
    print(f"🔥 V2.0 단타 매매 시스템 시작{' [테스트 모드]' if is_test_mode() else ' [실제 매매]'}", flush=True)
    print(f"🕐 현재시각: {now.strftime('%Y-%m-%d %H:%M:%S')} (NTP 동기화)", flush=True)
    print(f"💰 시작 자금: {INITIAL_CAPITAL:,}원 (가상)", flush=True)
    print(f"📊 최대 포지션: {MAX_POSITIONS}개", flush=True)
    print(f"🎯 익절/손절: +5% / -5%", flush=True)
    
    if is_test_mode():
        print(f"⚡ 테스트 모드: 시간 제약 없음", flush=True)
    else:
        print(f"⏰ 매매 시간: 09:05~14:00 (5분 간격)", flush=True)
        print(f"🚨 강제 청산: 15:10", flush=True)
        print(f"📅 공휴일/주말 자동 감지", flush=True)
    
    print(f"🔄 조건검색식: {CONDITION_SEQ_LIST}", flush=True)
    print("="*100, flush=True)

def print_loop_header(loop_count: int, engine: ScalpingEngine):
    """루프 시작 헤더 출력"""
    now = get_ntp_time()  # 🔥 NTP 시간 사용
    status = engine.get_portfolio_status()
    
    print(f"\n{'='*80}", flush=True)
    print(f"🔄 [{loop_count}번째 루프] {now.strftime('%H:%M:%S')} - 단타 매매 실행", flush=True)
    print(f"💰 자금현황: {status['available_cash']:,}원 | "
          f"포지션: {status['position_count']}/{MAX_POSITIONS}개 | "
          f"손익: {status['daily_pnl']:+,}원 ({status['daily_return']:+.2f}%)", flush=True)
    print(f"{'='*80}", flush=True)

def print_trading_summary(engine: ScalpingEngine):
    """거래 요약 출력"""
    status = engine.get_portfolio_status()
    
    # 거래 통계
    buy_trades = [t for t in engine.daily_trades if t["type"] == "buy"]
    sell_trades = [t for t in engine.daily_trades if t["type"] == "sell"]
    profit_trades = [t for t in sell_trades if t["profit_amount"] > 0]
    loss_trades = [t for t in sell_trades if t["profit_amount"] <= 0]
    
    print(f"\n{'='*60}", flush=True)
    print(f"📊 루프 완료 요약", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"🔄 매수 실행: {len(buy_trades)}건", flush=True)
    print(f"💰 매도 실행: {len(sell_trades)}건", flush=True)
    if sell_trades:
        print(f"🟢 수익 거래: {len(profit_trades)}건", flush=True)
        print(f"🔴 손실 거래: {len(loss_trades)}건", flush=True)
        
        if profit_trades:
            avg_profit = sum(t["profit_rate"] for t in profit_trades) / len(profit_trades)
            print(f"📈 평균 수익률: {avg_profit:+.2f}%", flush=True)
    
    print(f"💵 현재 자금: {status['available_cash']:,}원", flush=True)
    print(f"📊 일일 손익: {status['daily_pnl']:+,}원 ({status['daily_return']:+.2f}%)", flush=True)

def print_position_table(engine: ScalpingEngine, token: str):
    """보유 포지션 테이블 출력"""
    if not engine.positions:
        print(f"[INFO] 📝 현재 보유 포지션이 없습니다.", flush=True)
        return
    
    print(f"\n📋 [보유 포지션 현황] {len(engine.positions)}개", flush=True)
    
    table_data = []
    total_cost = 0
    total_current_value = 0
    
    for i, pos in enumerate(engine.positions, 1):
        try:
            from scalping_engine import get_current_price
            current_price = get_current_price(pos.code, token)
            
            if current_price > 0:
                current_value = pos.get_current_value(current_price)
                profit_amount, profit_rate = pos.get_profit_loss(current_price)
                
                total_cost += pos.cost
                total_current_value += current_value
                
                # 상태 표시
                if profit_rate >= 4.0:
                    status = "🟢 익절대기"
                elif profit_rate <= -4.0:
                    status = "🔴 손절대기"
                elif profit_rate > 0:
                    status = "🟢 수익"
                elif profit_rate < 0:
                    status = "🔴 손실"
                else:
                    status = "⚪ 보합"
                
                table_data.append([
                    i,
                    pos.name[:10],
                    pos.code,
                    f"{pos.buy_price:,}",
                    f"{current_price:,}",
                    f"{profit_rate:+.2f}%",
                    f"{profit_amount:+,}",
                    status
                ])
        except Exception:
            table_data.append([
                i,
                pos.name[:10],
                pos.code,
                f"{pos.buy_price:,}",
                "조회실패",
                "-",
                "-",
                "❓ 오류"
            ])
    
    if table_data:
        print(tabulate(
            table_data,
            headers=[
                "순번", "종목명", "코드", "매수가", "현재가", 
                "수익률", "손익금액", "상태"
            ],
            tablefmt="grid"
        ), flush=True)
        
        # 포트폴리오 요약
        if total_cost > 0:
            total_profit = total_current_value - total_cost
            total_profit_rate = (total_profit / total_cost * 100)
            print(f"\n💼 포트폴리오 요약: 투자금 {total_cost:,}원 → "
                  f"평가금액 {total_current_value:,}원 "
                  f"({total_profit:+,}원, {total_profit_rate:+.2f}%)", flush=True)

def save_daily_report(engine: ScalpingEngine, log_dir: str):
    """일일 거래 보고서 저장"""
    today = get_ntp_time().strftime('%Y%m%d')  # 🔥 NTP 시간 사용
    report_file = os.path.join(log_dir, f"daily_report_{today}.json")
    
    try:
        ensure_parent_dir(report_file)
        
        status = engine.get_portfolio_status()
        buy_trades = [t for t in engine.daily_trades if t["type"] == "buy"]
        sell_trades = [t for t in engine.daily_trades if t["type"] == "sell"]
        
        report_data = {
            "date": today,
            "summary": {
                "initial_capital": INITIAL_CAPITAL,
                "final_capital": status["available_cash"] + sum(pos.cost for pos in engine.positions),
                "daily_pnl": status["daily_pnl"],
                "daily_return": status["daily_return"],
                "total_trades": len(buy_trades),
                "completed_trades": len(sell_trades),
                "remaining_positions": len(engine.positions)
            },
            "trades": engine.daily_trades,
            "traded_stocks": list(engine.traded_today),
            "final_positions": [
                {
                    "code": pos.code,
                    "name": pos.name,
                    "buy_price": pos.buy_price,
                    "quantity": pos.quantity,
                    "cost": pos.cost
                } for pos in engine.positions
            ]
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"[저장 완료] 📄 일일 보고서: {report_file}", flush=True)
        
    except Exception as e:
        print(f"[ERROR] 일일 보고서 저장 실패: {e}", flush=True)

# ================================================================================
# 🔥 V2.0 메인 실행 루프 (시장 대기모드 적용)
# ================================================================================

async def execute_scalping_loop(engine: ScalpingEngine, token: str, loop_count: int) -> int:
    """단타 매매 한 루프 실행"""
    
    executed_actions = 0
    
    try:
        # 1. 청산 조건 체크 (5% 익절/손절)
        print(f"🔍 청산 조건 체크 중...", flush=True)
        exit_count = engine.check_exit_conditions(token)
        
        if exit_count > 0:
            print(f"✅ {exit_count}개 포지션 청산 완료", flush=True)
            executed_actions += exit_count
        else:
            print(f"📝 청산 대상 없음 (익절/손절 조건 미달성)", flush=True)
        
        # 2. 신규 매수 대상 검색 (빈 자리가 있을 때만)
        available_slots = MAX_POSITIONS - len(engine.positions)
        
        if available_slots > 0:
            print(f"🔍 신규 매수 대상 검색 중... (빈 자리: {available_slots}개)", flush=True)
            
            # 🔥 리팩토링: top_n=None으로 전체 결과 처리
            candidates = await find_scalping_targets(engine, token, top_n=None)
            
            if candidates:
                print(f"📋 매수 후보 {len(candidates)}개 발견:", flush=True)
                for i, candidate in enumerate(candidates[:3], 1):
                    print(f"  {i}. {candidate['name']} - 거래대금 {candidate['amount']:,}원", flush=True)
                
                print(f"\n💰 매수 시도 시작... (최대 {available_slots}개)", flush=True)
                
                # 상위 종목들 매수 시도
                buy_count = 0
                for i, candidate in enumerate(candidates, 1):
                    if buy_count >= available_slots:
                        print(f"🔄 포지션 한도 도달 - 매수 중단", flush=True)
                        break
                    
                    print(f"🎯 [{i}번째 시도] {candidate['name']} 매수 중...", flush=True)
                    
                    success = engine.buy_stock(
                        candidate["code"],
                        candidate["name"],
                        candidate["price"],
                        candidate["condition_seq"],
                        candidate["amount"]  # 🔥 매수시점 거래대금
                    )
                    
                    if success:
                        buy_count += 1
                        executed_actions += 1
                        print(f"✅ [{i}번째] 매수 성공! (총 {buy_count}개 매수 완료)", flush=True)
                    else:
                        print(f"❌ [{i}번째] 매수 실패", flush=True)
                    
                    time.sleep(0.3)  # API 호출 간격
                
                if buy_count > 0:
                    print(f"🎉 신규 매수 완료: {buy_count}개 종목", flush=True)
                else:
                    print(f"📝 신규 매수 없음 (모든 후보 조건 불충족)", flush=True)
            else:
                print(f"📝 매수 후보 없음 (조건검색 결과 없음)", flush=True)
        else:
            print(f"📊 포트폴리오 만석 ({MAX_POSITIONS}/{MAX_POSITIONS}) - 청산 대기 중", flush=True)
        
        # 3. 현재 포지션 현황 출력
        if engine.positions:
            print_position_table(engine, token)
        else:
            print(f"📝 현재 보유 포지션 없음", flush=True)
        
    except Exception as e:
        print(f"❌ 루프 실행 중 오류: {e}", flush=True)
        import traceback
        traceback.print_exc()
    
    return executed_actions

async def main():
    """🔥 리팩토링: V2.0 단타 매매 메인 실행 (완전한 시장 대기모드)"""
    
    # 🔥 실행 모드 선택
    if not select_trading_mode():
        return
    
    # 🔥 실제 매매 모드에서는 시장 대기모드 실행
    if not is_test_mode():
        print("\n🌐 시장 상태 확인 및 대기모드 시작...")
        try:
            wait_for_market_with_countdown()
        except KeyboardInterrupt:
            print("\n👋 시장 대기 중단 - 시스템 종료")
            return
    
    # 1. 시스템 초기화
    print_system_header()
    
    # 2. 토큰 준비
    try:
        token = ensure_token_for_full_trading_day()
    except Exception as e:
        print(f"[ERROR] 토큰 획득 실패: {e}")
        sys.exit(1)
    
    # 3. 디렉토리 설정
    today = get_ntp_time().strftime('%Y%m%d')  # 🔥 NTP 시간 사용
    mode_suffix = "test" if is_test_mode() else "real"
    log_dir = os.path.join("auto_signals", today, f"scalping_v2_{mode_suffix}")
    os.makedirs(log_dir, exist_ok=True)
    
    # 4. 단타 엔진 초기화
    engine = ScalpingEngine(log_dir)
    
    print(f"📁 로그 디렉토리: {log_dir}", flush=True)
    
    # 5. 매매 설정
    loop_count = 0
    total_actions = 0
    
    mode_text = "테스트 모드" if is_test_mode() else "실제 매매"
    print(f"[INFO] 🎯 단타 매매 시작! ({mode_text})", flush=True)
    
    # ================================================================================
    # 🔥 메인 매매 루프 - 시장 대기모드 적용
    # ================================================================================
    
    while is_trading_time_safe() and not is_force_sell_time_safe():
        loop_count += 1
        
        try:
            # 🔥 실제 모드에서는 NTP 시간으로 장시간 재확인
            if not is_test_mode():
                is_trading, market_status = is_trading_session()
                if not is_trading:
                    print(f"\n🚨 장시간 종료 감지: {market_status}", flush=True)
                    break
            
            # 루프 헤더 출력
            print_loop_header(loop_count, engine)
            
            # 토큰 상태 재검증
            token = get_valid_access_token()
            
            # 🔥 단타 매매 실행
            actions = await execute_scalping_loop(engine, token, loop_count)
            total_actions += actions
            
            # 루프 요약
            print_trading_summary(engine)
            
            # 🔥 실제 모드에서 14:00 체크 (NTP 시간 기준)
            if not is_test_mode():
                now = get_ntp_time()
                if now.hour >= TRADING_END_HOUR:
                    print(f"\n🚨 [14:00 도달] 신규 매매 종료 - 청산 대기 모드", flush=True)
                    break
            
            # 15:10 강제 청산 체크 (테스트 모드에서는 건너뛰기)
            if is_force_sell_time_safe():
                print(f"\n🚨 [15:10 도달] 강제 청산 시간", flush=True)
                break
            
            # 다음 루프 대기
            next_time = get_ntp_time() + timedelta(seconds=LOOP_INTERVAL)  # 🔥 NTP 시간 사용
            remaining_minutes = LOOP_INTERVAL // 60
            
            # 🔥 모드별 대기시간 및 메시지
            if is_test_mode():
                print(f"\n⏳ [테스트 모드] 30초 후 다음 루프 ({next_time.strftime('%H:%M:%S')})", flush=True)
                time.sleep(30)
            else:
                print(f"\n⏳ [실제 모드] {remaining_minutes}분 후 다음 루프 ({next_time.strftime('%H:%M:%S')})", flush=True)
                time.sleep(LOOP_INTERVAL)
            
        except KeyboardInterrupt:
            print(f"\n[INFO] 사용자 중단 요청 - 강제 청산 진행", flush=True)
            break
        except Exception as e:
            print(f"❌ 루프 {loop_count} 실행 중 오류: {e}", flush=True)
            try:
                token = get_valid_access_token()
                print(f"[INFO] 토큰 재발급 후 계속 진행", flush=True)
            except Exception as token_error:
                print(f"❌ 토큰 재발급 실패: {token_error}", flush=True)
            time.sleep(30)
    
    # ================================================================================
    # 🚨 강제 청산 단계 (모드별 처리)
    # ================================================================================
    
    try:
        print(f"\n{'='*100}", flush=True)
        if is_test_mode():
            print(f"🧪 테스트 완료 - 포지션 정리", flush=True)
        else:
            print(f"🚨 강제 청산 단계 시작 (15:10)", flush=True)
        print(f"{'='*100}", flush=True)
        
        # 토큰 재검증
        token = get_valid_access_token()
        
        # 강제 청산 실행
        if engine.positions:
            if is_test_mode():
                print(f"🧪 테스트 종료 - 보유 포지션 {len(engine.positions)}개 정리 중...", flush=True)
            else:
                print(f"🚨 미결제 포지션 {len(engine.positions)}개 강제 청산 중...", flush=True)
            
            force_sell_count = engine.force_sell_all(token)
            
            if is_test_mode():
                print(f"🧪 테스트 정리 완료: {force_sell_count}건", flush=True)
            else:
                print(f"🚨 강제 청산 완료: {force_sell_count}건", flush=True)
        else:
            print(f"✅ 미결제 포지션 없음 - 청산 불필요", flush=True)
        
        # 최종 현황 출력
        print(f"\n{'='*100}", flush=True)
        if is_test_mode():
            print(f"🧪 V2.0 단타 매매 테스트 완료!", flush=True)
        else:
            print(f"🎉 V2.0 단타 매매 완료! (시장 대기모드)", flush=True)
        print(f"{'='*100}", flush=True)
        
        engine.print_status()
        
        # 일일 보고서 저장
        save_daily_report(engine, log_dir)
        
        # 최종 통계
        final_status = engine.get_portfolio_status()
        completion_time = get_ntp_time()  # 🔥 NTP 시간 사용
        
        print(f"\n🏁 [최종 결과] ({'테스트 모드' if is_test_mode() else '실제 매매'})", flush=True)
        print(f"   🕐 완료 시간: {completion_time.strftime('%Y-%m-%d %H:%M:%S')} (NTP)", flush=True)
        print(f"   💰 시작 자금: {INITIAL_CAPITAL:,}원", flush=True)
        print(f"   💵 최종 자금: {final_status['available_cash']:,}원", flush=True)
        print(f"   📊 총 손익: {final_status['daily_pnl']:+,}원 ({final_status['daily_return']:+.2f}%)", flush=True)
        print(f"   🔄 총 실행: {loop_count}루프, {total_actions}건 거래", flush=True)
        print(f"   🎯 거래 종목: {len(engine.traded_today)}개", flush=True)
        
        # 🔥 시장 대기모드 완료 메시지
        if is_test_mode():
            print(f"\n🧪 [테스트 모드 완료]", flush=True)
            print(f"   ⚡ 시간 제약 없이 테스트 실행", flush=True)
            print(f"   📊 실제 매매를 원하면 모드 2 선택", flush=True)
        else:
            print(f"\n✅ [실제 매매 완료 - 시장 대기모드]", flush=True)
            print(f"   🌐 NTP 시간 동기화 적용", flush=True)
            print(f"   📅 공휴일/주말 자동 감지", flush=True)
            print(f"   ⏰ 장시간 완전 준수", flush=True)
            print(f"   🔑 08:50 토큰 사전 체크", flush=True)
            print(f"   🚨 15:10 강제청산 적용", flush=True)
        
        # 🔥 다음 개장일 안내 (실제 모드에서만)
        if not is_test_mode():
            next_trading_date, reason = get_next_trading_day()
            if next_trading_date > get_ntp_time().date():
                print(f"\n📅 [다음 개장일 안내]", flush=True)
                print(f"   📆 다음 개장일: {next_trading_date.strftime('%Y-%m-%d (%A)')} ({reason})", flush=True)
                print(f"   ⏰ 시장 대기모드로 자동 재시작하려면 다시 실행하세요", flush=True)
        
    except Exception as e:
        print(f"[ERROR] 청산 단계 실패: {e}", flush=True)

# ================================================================================
# 🔥 메인 실행부 (시장 대기모드 적용)
# ================================================================================

if __name__ == "__main__":
    # 🔥 초기 NTP 동기화 (프로그램 시작 시 한 번)
    start_time = get_ntp_time()
    print(f"🚀 V2.0 단타 매매 시스템 (시장 대기모드): {start_time.strftime('%Y-%m-%d %H:%M:%S')} (NTP)", flush=True)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n[INFO] 사용자 중단 요청 - 시스템 종료", flush=True)
    except Exception as e:
        print(f"[ERROR] 시스템 실행 실패: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        end_time = get_ntp_time()  # 🔥 NTP 시간 사용
        print(f"🕐 V2.0 단타 매매 시스템 종료: {end_time.strftime('%Y-%m-%d %H:%M:%S')} (NTP)", flush=True)
        
        # 🔥 실행 시간 통계
        if 'start_time' in locals():
            runtime = end_time - start_time
            print(f"⏱️  총 실행 시간: {format_time_diff(runtime)}", flush=True)