"""
🔥 V3.1 단타 매매 엔진 - 누적 수익률 강화 VirtualMoneyManager 완전 통합
Real-time scalping engine with cumulative returns tracking
"""

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

import sys
import io
import asyncio
import json
import requests
from datetime import datetime, timedelta
import os
import time
from tabulate import tabulate
from typing import List, Dict, Any, Optional, Tuple

# 🔥 누적 수익률 강화 VirtualMoneyManager 통합
from virtual_money_manager import VirtualMoneyManager, VirtualTransaction

# ================================================================================
# 환경설정 및 상수
# ================================================================================
WS_URL = "wss://api.kiwoom.com:10000/api/dostk/websocket"
CONDITION_SEQ_LIST = [3, 4, 5, 6, 7]
TOKEN_FILE = "access_token.json"
TOKEN_ISSUE_SCRIPT = "kiwoom_auth.py"

# 🔥 V3.1 단타 매매 설정 (동적 조정 지원)
INITIAL_CAPITAL = 500_000      # 시작 자금 50만원 (최초에만)
BASE_POSITION_VALUE = 100_000  # 기본 종목당 투자금액
BASE_MAX_POSITIONS = 5         # 기본 최대 종목수
PROFIT_TARGET = 5.0            # +5% 익절
STOP_LOSS = -5.0               # -5% 손절
TRADING_START_HOUR = 9         # 09:05 매매 시작
TRADING_END_HOUR = 14          # 14:00 매매 종료
FORCE_SELL_HOUR = 15           # 15:10 강제 청산
FORCE_SELL_MINUTE = 10
LOOP_INTERVAL = 300            # 5분(300초) 간격

# 출력 인코딩 설정
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding="utf-8")

# ================================================================================
# 유틸리티 함수들
# ================================================================================

def normalize_code(code):
    """종목코드 정규화 (A 접두사 추가)"""
    code = str(code).replace("A", "").zfill(6)
    return "A" + code

def ensure_parent_dir(file_path):
    """파일의 상위 디렉토리 생성"""
    dir_path = os.path.dirname(os.path.abspath(file_path))
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

def is_etf_etn(stock_name: str) -> bool:
    """ETF/ETN 종목 필터링"""
    if not stock_name or stock_name.strip() == "":
        return True
    name_upper = stock_name.upper()
    ETF_ETN_KEYWORDS = [
        "ETF", "ETN", "KODEX", "TIGER", "HANARO", "KBSTAR", "KOSEF", 
        "ARIRANG", "TREX", "SOL", "TIMEFOLIO"
    ]
    return any(word in name_upper for word in ETF_ETN_KEYWORDS)

# ================================================================================
# 토큰 관리 시스템 (기존 코드 유지)
# ================================================================================

def get_token_info():
    """토큰 상세 정보 조회"""
    try:
        if not os.path.exists(TOKEN_FILE):
            return None
            
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        expires_in = data.get("expires_in")
        issued_at_str = data.get("issued_at")
        
        if not expires_in or not issued_at_str:
            return None
            
        issued_at = datetime.strptime(issued_at_str, "%Y-%m-%d %H:%M:%S")
        expired_time = issued_at + timedelta(seconds=int(expires_in))
        
        return {
            "issued_at": issued_at,
            "expired_time": expired_time,
            "remaining_hours": (expired_time - datetime.now()).total_seconds() / 3600
        }
    except Exception:
        return None

def should_refresh_token():
    """토큰 재발급 필요 여부 종합 판단"""
    now = datetime.now()
    
    # 1. 8시 50분 ~ 8시 55분 정기 재발급
    morning_refresh = now.replace(hour=8, minute=50, second=0, microsecond=0)
    if morning_refresh <= now <= morning_refresh + timedelta(minutes=5):
        return True, "8시 50분 정기 재발급"
    
    # 2. 토큰 정보 확인
    token_info = get_token_info()
    if not token_info:
        return True, "토큰 파일 없음 또는 손상"
    
    # 3. 장 마감까지 시간 확인
    market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)
    
    # 장중이고 토큰이 장 마감 전에 만료될 경우
    if 9 <= now.hour <= 15:
        if token_info["expired_time"] <= market_end + timedelta(minutes=10):
            return True, f"장중 만료 위험 (만료: {token_info['expired_time'].strftime('%H:%M:%S')})"
    
    # 4. 남은 시간이 2시간 미만
    if token_info["remaining_hours"] < 2:
        return True, f"토큰 만료 임박 (남은시간: {token_info['remaining_hours']:.1f}시간)"
    
    return False, f"토큰 정상 (만료: {token_info['expired_time'].strftime('%H:%M:%S')})"

def load_access_token(token_path=TOKEN_FILE):
    """기본 토큰 로드 (만료 체크 포함)"""
    if not os.path.exists(token_path):
        raise FileNotFoundError(f"{token_path} 파일이 없습니다. 토큰을 먼저 발급하세요.")
    
    with open(token_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    access_token = data.get("access_token")
    expires_in = data.get("expires_in")
    issued_at_str = data.get("issued_at")
    
    if not access_token:
        raise ValueError("access_token이 없습니다. 토큰 파일을 확인하세요.")
    if not expires_in or not issued_at_str:
        raise ValueError("expires_in 또는 issued_at 정보가 없습니다. 토큰 파일을 확인하세요.")
    
    issued_at = datetime.strptime(issued_at_str, "%Y-%m-%d %H:%M:%S")
    expired_time = issued_at + timedelta(seconds=int(expires_in))
    
    if datetime.now() > expired_time:
        raise ValueError(f"토큰이 만료되었습니다. (만료시각: {expired_time.strftime('%Y-%m-%d %H:%M:%S')})")
    
    return access_token

def try_issue_token():
    """토큰 재발급 실행"""
    print("[INFO] 🔄 토큰 재발급을 시작합니다...", flush=True)
    
    import subprocess
    try:
        subprocess.run(["python", TOKEN_ISSUE_SCRIPT], check=True)
    except Exception as e:
        raise RuntimeError(f"토큰 발급 스크립트 실행 실패: {e}")
    
    # 1분간 토큰 파일 생성 대기
    for i in range(12):
        time.sleep(5)
        try:
            token = load_access_token()
            print(f"[INFO] ✅ 토큰 재발급 완료! ({(i+1)*5}초 소요)", flush=True)
            return token
        except Exception:
            continue
    
    raise RuntimeError("토큰 발급 실패!")

def get_valid_access_token():
    """완벽한 토큰 관리 - 8시 50분 재발급 + 장중 만료 방지"""
    should_refresh, reason = should_refresh_token()
    
    if should_refresh:
        print(f"[토큰 재발급] {reason}", flush=True)
        
        # 재발급 전 현재 토큰 정보 출력
        token_info = get_token_info()
        if token_info:
            print(f"[기존 토큰] 발급: {token_info['issued_at'].strftime('%m/%d %H:%M')}, "
                  f"만료: {token_info['expired_time'].strftime('%m/%d %H:%M')}", flush=True)
        
        new_token = try_issue_token()
        
        # 새 토큰 정보 출력
        new_token_info = get_token_info()
        if new_token_info:
            print(f"[새 토큰] 발급: {new_token_info['issued_at'].strftime('%m/%d %H:%M')}, "
                  f"만료: {new_token_info['expired_time'].strftime('%m/%d %H:%M')}", flush=True)
        
        return new_token
    else:
        # 상태 정보 출력 (너무 자주 출력하지 않도록 조건부)
        now = datetime.now()
        if now.minute % 30 == 0 and now.second < 30:  # 30분마다 한 번씩만
            print(f"[토큰 상태] {reason}", flush=True)
        return load_access_token()

def ensure_token_for_full_trading_day():
    """하루 거래용 토큰 완전성 검증"""
    print("[INFO] 🔍 하루 거래용 토큰 상태 점검...", flush=True)
    
    token = get_valid_access_token()
    
    # 토큰 정보 상세 출력
    token_info = get_token_info()
    if token_info:
        now = datetime.now()
        market_end = now.replace(hour=15, minute=30, second=0, microsecond=0)
        
        print(f"[토큰 정보] 📅 발급: {token_info['issued_at'].strftime('%m/%d %H:%M')}, "
              f"⏰ 만료: {token_info['expired_time'].strftime('%m/%d %H:%M')}", flush=True)
        print(f"[토큰 정보] 🕐 남은시간: {token_info['remaining_hours']:.1f}시간", flush=True)
        
        # 장 마감 후까지 안전한지 확인
        if token_info['expired_time'] > market_end:
            print("[INFO] ✅ 장 마감까지 토큰 안전!", flush=True)
        else:
            print("[WARN] ⚠️  장중 토큰 만료 가능성 있음", flush=True)
    
    return token

# ================================================================================
# 간소화된 API 호출 함수들 (기존 유지)
# ================================================================================

def make_api_call_with_retry(url, headers, body, stock_code, max_retries=2, delay=0.3):
    """API 호출 재시도 로직 (간소화)"""
    for attempt in range(max_retries):
        try:
            r = requests.post(url, headers=headers, json=body, timeout=8)
            
            if r.status_code == 429:
                time.sleep(delay * (2 ** attempt))
                continue
            elif r.status_code != 200:
                return None
            
            return r.json()
            
        except Exception:
            if attempt == max_retries - 1:
                return None
            time.sleep(delay)
    
    return None

def get_stock_info(stock_code: str, token: str) -> Dict[str, Any]:
    """종목 정보 조회 (이름, 현재가, 거래대금)"""
    url = "https://api.kiwoom.com/api/dostk/stkinfo"
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "authorization": f"Bearer {token}",
        "api-id": "ka10001"
    }
    body = {"stk_cd": stock_code.replace("A", "").zfill(6)}
    
    data = make_api_call_with_retry(url, headers, body, stock_code)
    if not data:
        return {}
    
    try:
        name = data.get("stk_nm", "")
        cur_prc = data.get("cur_prc", "0")
        trde_qty = data.get("trde_qty", "0")
        
        price = int(str(cur_prc).replace("+", "").replace("-", "").replace(",", ""))
        qty = int(str(trde_qty).replace(",", ""))
        amount = price * qty
        
        return {
            "name": name,
            "price": price,
            "amount": amount
        }
    except Exception:
        return {}

def get_current_price(stock_code: str, token: str) -> int:
    """현재가 조회"""
    info = get_stock_info(stock_code, token)
    return info.get("price", 0)

# ================================================================================
# 웹소켓 조건검색식 함수들 (기존 유지)
# ================================================================================

async def get_condition_codes(seq: int, token: str) -> Tuple[List[str], str]:
    """웹소켓을 통한 조건검색식 결과 조회"""
    import websockets
    
    try:
        async with websockets.connect(WS_URL) as ws:
            # 로그인
            await ws.send(json.dumps({"trnm": "LOGIN", "token": token}))
            while True:
                res = json.loads(await ws.recv())
                if res.get("trnm") == "LOGIN" and res["return_code"] == 0:
                    break
            
            # 조건검색식 목록 조회
            await ws.send(json.dumps({"trnm": "CNSRLST"}))
            while True:
                res = json.loads(await ws.recv())
                if res.get("trnm") == "CNSRLST":
                    conds = res["data"]
                    break
            
            # 조건검색식 실행
            cond_seq = str(seq)
            match = next((item for item in conds if str(item[0]) == cond_seq), None)
            if not match:
                return [], ""
            
            cond_name = match[1]
            req = {
                "trnm": "CNSRREQ",
                "seq": cond_seq,
                "name": cond_name,
                "search_type": "0",
                "stex_tp": "K",
                "cont_yn": "N",
                "next_key": ""
            }
            
            await ws.send(json.dumps(req))
            while True:
                res = json.loads(await ws.recv())
                if res.get("trnm") == "CNSRREQ":
                    codes = [normalize_code(s.get("9001", "")) for s in res.get("data", [])]
                    return codes, cond_name
                    
    except Exception as e:
        print(f"[ERROR] 조건검색식 {seq} 조회 실패: {e}", flush=True)
        return [], ""

# ================================================================================
# 🔥 V3.1 핵심: 동적 전략 조정 시스템
# ================================================================================

class TradingStrategy:
    """🔥 자금 상황에 따른 동적 전략 조정"""
    
    def __init__(self):
        self.max_position_value = BASE_POSITION_VALUE
        self.max_positions = BASE_MAX_POSITIONS
        self.last_update_time = datetime.now()
    
    def update_strategy_based_on_capital(self, current_capital: int) -> Tuple[int, int]:
        """🔥 자금 상황에 따른 전략 동적 조정"""
        
        if current_capital >= 2_000_000:  # 200만원 이상 (대형)
            position_value = min(400_000, current_capital // 5)  # 40만원 또는 1/5
            max_positions = 6
            strategy_name = "🚀 대형 전략"
            
        elif current_capital >= 1_000_000:  # 100만원 이상 (중형)
            position_value = min(200_000, current_capital // 5)  # 20만원 또는 1/5
            max_positions = 5
            strategy_name = "📈 중형 전략"
            
        elif current_capital >= 500_000:  # 50만원 이상 (일반)
            position_value = min(100_000, current_capital // 5)  # 10만원 또는 1/5  
            max_positions = 5
            strategy_name = "📊 일반 전략"
            
        elif current_capital >= 200_000:  # 20만원 이상 (소형)
            position_value = min(50_000, current_capital // 4)   # 5만원 또는 1/4
            max_positions = 4
            strategy_name = "⚠️  소형 전략"
            
        else:  # 20만원 미만 (최소)
            position_value = min(30_000, current_capital // 3)   # 3만원 또는 1/3
            max_positions = 3
            strategy_name = "🔴 최소 전략"
        
        # 전략 변경 알림 (5분마다 한 번씩만)
        now = datetime.now()
        if (now - self.last_update_time).total_seconds() > 300:  # 5분
            if position_value != self.max_position_value or max_positions != self.max_positions:
                print(f"[전략 조정] {strategy_name}: 종목당 {position_value:,}원, 최대 {max_positions}종목")
                self.last_update_time = now
        
        self.max_position_value = position_value
        self.max_positions = max_positions
        
        return position_value, max_positions

# ================================================================================
# 🔥 V3.1 핵심: Position 클래스 (누적 VirtualMoneyManager 연동)
# ================================================================================

class Position:
    """개별 포지션 관리 (누적 VirtualMoneyManager와 연동)"""
    def __init__(self, code: str, name: str, buy_price: int, quantity: int, 
                 condition_seq: int = 0, buy_amount: int = 0, virtual_transaction: VirtualTransaction = None):
        self.code = normalize_code(code)
        self.name = name
        self.buy_price = buy_price
        self.quantity = quantity
        self.condition_seq = condition_seq
        self.buy_time = datetime.now()
        self.cost = buy_price * quantity
        self.buy_amount = buy_amount  # 매수시점 거래대금
        self.virtual_transaction = virtual_transaction  # 🔥 VirtualTransaction 연결
        
    def get_current_value(self, current_price: int) -> int:
        """현재 평가금액"""
        return current_price * self.quantity
    
    def get_profit_loss(self, current_price: int) -> Tuple[int, float]:
        """손익 계산 (원, %)"""
        current_value = self.get_current_value(current_price)
        profit_amount = current_value - self.cost
        profit_rate = (profit_amount / self.cost * 100) if self.cost > 0 else 0
        return profit_amount, profit_rate
    
    def should_exit(self, current_price: int) -> Tuple[bool, str]:
        """청산 조건 체크"""
        _, profit_rate = self.get_profit_loss(current_price)
        
        if profit_rate >= PROFIT_TARGET:
            return True, "익절"
        elif profit_rate <= STOP_LOSS:
            return True, "손절"
        
        return False, ""

# ================================================================================
# 🔥 V3.1 핵심: ScalpingEngine 클래스 (누적 수익률 강화 VirtualMoneyManager 완전 통합)
# ================================================================================

class ScalpingEngine:
    """🔥 누적 수익률 강화 단타 매매 엔진"""
    
    def __init__(self, log_dir: str = None):
        # 🔥 누적 수익률 강화 VirtualMoneyManager로 자금 관리
        self.money_manager = VirtualMoneyManager(INITIAL_CAPITAL, "virtual_money_data")
        
        # 🔥 동적 전략 조정 시스템
        self.trading_strategy = TradingStrategy()
        
        self.positions: List[Position] = []
        self.traded_today: set = set()  # 오늘 거래한 종목들
        
        # 로그 설정
        if log_dir:
            ensure_parent_dir(log_dir)
            self.log_file = os.path.join(log_dir, f"scalping_log_{datetime.now().strftime('%Y%m%d')}.txt")
        else:
            self.log_file = None
        
        # 🔥 시작 시 자금 상황 점검 및 전략 조정
        self.update_trading_strategy()
    
    def log_activity(self, message: str):
        """활동 로그 기록"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        print(log_entry, flush=True)
        
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(log_entry + "\n")
            except Exception:
                pass
    
    @property
    def available_cash(self):
        """🔥 VirtualMoneyManager에서 가져오기"""
        return self.money_manager.available_cash
    
    @property  
    def daily_pnl(self):
        """🔥 VirtualMoneyManager에서 가져오기"""
        return self.money_manager.daily_pnl
    
    def update_trading_strategy(self):
        """🔥 자금 상황에 따른 전략 업데이트"""
        current_total = self.money_manager.available_cash + self.money_manager.total_invested
        position_value, max_positions = self.trading_strategy.update_strategy_based_on_capital(current_total)
        return position_value, max_positions
    
    def can_buy_stock(self, code: str) -> Tuple[bool, str]:
        """매수 가능 여부 확인 (동적 전략 적용)"""
        code = normalize_code(code)
        
        # 🔥 전략 업데이트
        position_value, max_positions = self.update_trading_strategy()
        
        # 1. 이미 거래한 종목?
        if code in self.traded_today:
            return False, "재매수금지"
        
        # 2. 포지션 한도 초과? (동적 조정)
        if len(self.positions) >= max_positions:
            return False, f"포지션한도초과({max_positions})"
        
        # 3. 자금 부족? (🔥 VirtualMoneyManager의 자동 조정 활용)
        min_required = min(10_000, position_value)  # 최소 1만원 또는 목표 투자금액
        if not self.money_manager.can_afford(min_required):
            return False, "자금부족"
        
        return True, "매수가능"
    
    def buy_stock(self, code: str, name: str, price: int, condition_seq: int = 0, buy_amount: int = 0) -> bool:
        """🔥 가상 매수 실행 (누적 VirtualMoneyManager + 동적 전략 사용)"""
        code = normalize_code(code)
        
        can_buy, reason = self.can_buy_stock(code)
        if not can_buy:
            self.log_activity(f"❌ 매수 실패 {name}({code}): {reason}")
            return False
        
        # 🔥 동적 투자 금액 결정
        position_value, _ = self.update_trading_strategy()
        
        # 🔥 VirtualMoneyManager로 매수 실행 (자동 자금 조정 포함)
        virtual_transaction = self.money_manager.execute_virtual_buy(
            code, name, price, position_value, condition_seq
        )
        
        if not virtual_transaction:
            self.log_activity(f"❌ 매수 실패 {name}({code}): VirtualMoneyManager 오류")
            return False
        
        # Position 객체 생성 (VirtualTransaction과 연결)
        position = Position(
            code, name, price, virtual_transaction.quantity, 
            condition_seq, buy_amount, virtual_transaction
        )
        self.positions.append(position)
        self.traded_today.add(code)
        
        # 🔥 누적 수익률 정보와 함께 로그
        portfolio = self.money_manager.get_portfolio_value()
        cumulative_return = portfolio.get('cumulative_return', 0)
        
        self.log_activity(f"✅ 매수 {name}({code}) {virtual_transaction.quantity}주 @{price:,}원 "
                         f"(투자: {virtual_transaction.amount:,}원, 누적: {cumulative_return:+.2f}%)")
        return True
    
    def sell_position(self, position: Position, current_price: int, reason: str) -> bool:
        """🔥 포지션 매도 (누적 VirtualMoneyManager 사용)"""
        if position not in self.positions:
            return False
        
        # 🔥 VirtualMoneyManager로 매도 실행
        if not position.virtual_transaction:
            self.log_activity(f"❌ 매도 실패 {position.name}: VirtualTransaction 없음")
            return False
        
        sell_transaction = self.money_manager.execute_virtual_sell(
            position.virtual_transaction, current_price, reason
        )
        
        if not sell_transaction:
            self.log_activity(f"❌ 매도 실패 {position.name}: VirtualMoneyManager 오류")
            return False
        
        # 포지션 제거
        self.positions.remove(position)
        
        # 🔥 누적 수익률 정보와 함께 로그
        portfolio = self.money_manager.get_portfolio_value()
        cumulative_return = portfolio.get('cumulative_return', 0)
        
        emoji = "🟢" if sell_transaction.profit_amount > 0 else "🔴"
        self.log_activity(f"{emoji} 매도 {position.name}({position.code}) "
                         f"{position.buy_price:,}→{current_price:,} "
                         f"({sell_transaction.profit_rate:+.2f}%) {reason} | 누적: {cumulative_return:+.2f}%")
        
        return True
    
    def check_exit_conditions(self, token: str) -> int:
        """청산 조건 체크 및 실행"""
        if not self.positions:
            return 0
        
        exit_count = 0
        positions_to_exit = []
        
        # 현재가 조회 및 청산 조건 체크
        for position in self.positions:
            try:
                current_price = get_current_price(position.code, token)
                if current_price > 0:
                    should_exit, exit_reason = position.should_exit(current_price)
                    if should_exit:
                        positions_to_exit.append((position, current_price, exit_reason))
            except Exception as e:
                self.log_activity(f"⚠️  {position.name} 현재가 조회 실패: {e}")
        
        # 청산 실행
        for position, current_price, reason in positions_to_exit:
            if self.sell_position(position, current_price, reason):
                exit_count += 1
        
        return exit_count
    
    def force_sell_all(self, token: str) -> int:
        """강제 청산 (15:10)"""
        if not self.positions:
            return 0
        
        self.log_activity("🚨 강제 청산 시작 (15:10)")
        
        force_sell_count = 0
        positions_copy = self.positions.copy()
        
        for position in positions_copy:
            try:
                current_price = get_current_price(position.code, token)
                if current_price > 0:
                    if self.sell_position(position, current_price, "강제청산"):
                        force_sell_count += 1
            except Exception as e:
                self.log_activity(f"⚠️  {position.name} 강제청산 실패: {e}")
        
        # 🔥 하루 마감 처리
        self.money_manager.finalize_day()
        
        self.log_activity(f"🚨 강제 청산 완료: {force_sell_count}건")
        return force_sell_count
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """🔥 포트폴리오 현황 (누적 VirtualMoneyManager에서 가져오기)"""
        # VirtualMoneyManager에서 기본 정보 가져오기
        money_status = self.money_manager.get_portfolio_value()
        
        # 동적 전략 정보 추가
        position_value, max_positions = self.update_trading_strategy()
        
        return {
            **money_status,  # VirtualMoneyManager의 모든 정보 포함
            "position_count": len(self.positions),
            "traded_stocks_count": len(self.traded_today),
            "current_position_value": position_value,
            "current_max_positions": max_positions
        }
    
    def print_status(self, token: str = None):
        """🔥 현황 출력 (누적 수익률 강화 정보 포함)"""
        
        # 🔥 VirtualMoneyManager의 상세 누적 수익률 정보 출력
        self.money_manager.print_money_status()
        
        # 🔥 동적 전략 정보 출력
        position_value, max_positions = self.update_trading_strategy()
        current_total = self.money_manager.available_cash + self.money_manager.total_invested
        
        print(f"\n🎯 현재 전략 설정:")
        print(f"  💰 총 자금: {current_total:,}원")
        print(f"  📊 종목당 투자: {position_value:,}원")
        print(f"  📈 최대 종목수: {max_positions}개")
        print(f"  📋 현재 보유: {len(self.positions)}개")
        
        # 개별 포지션 현황 (기존 로직 유지하되 누적 수익률 추가)
        if self.positions and token:
            print(f"\n📋 보유 포지션 상세:")
            for i, pos in enumerate(self.positions, 1):
                try:
                    current_price = get_current_price(pos.code, token)
                    if current_price > 0:
                        _, profit_rate = pos.get_profit_loss(current_price)
                        emoji = "🟢" if profit_rate > 0 else "🔴" if profit_rate < 0 else "⚪"
                        print(f"  {i}. {pos.name}: {profit_rate:+.2f}% "
                              f"({pos.buy_price:,}→{current_price:,}) {emoji}")
                except Exception:
                    print(f"  {i}. {pos.name}: 조회실패")
        
        # 🔥 최근 성과 차트 (VirtualMoneyManager에서)
        self.money_manager.print_recent_performance(5)
        
        print(f"{'='*60}")

# ================================================================================
# 조건검색식 결과 처리 함수들 (동적 전략 반영)
# ================================================================================

def print_condition_results_table(candidates: List[Dict], engine: ScalpingEngine, condition_seq: int = 0, condition_name: str = ""):
    """조건검색식 결과를 상세 테이블로 표시 (동적 전략 반영)"""
    
    if not candidates:
        print(f"📝 조건검색식 {condition_seq}번 결과 없음", flush=True)
        return
    
    print(f"\n📋 [조건검색식 {condition_seq}번 결과{' - ' + condition_name if condition_name else ''}] 총 {len(candidates)}개 종목", flush=True)
    
    table_data = []
    
    for rank, candidate in enumerate(candidates, 1):
        code = candidate['code']
        name = candidate['name']
        price = candidate['price']
        amount = candidate['amount']
        
        # 매수 가능 여부 및 상태 확인
        can_buy, reason = engine.can_buy_stock(code)
        
        if can_buy:
            status = "🟢 매수가능"
        elif "재매수금지" in reason:
            status = "🚫 재매수금지"
        elif "포지션한도초과" in reason:
            status = f"📊 {reason}"
        elif reason == "자금부족":
            status = "💸 자금부족"
        else:
            status = "❓ 기타"
        
        table_data.append([
            rank,
            name[:10] + "..." if len(name) > 10 else name,
            code,
            f"{price:,}",
            f"{amount:,.0f}",
            status
        ])
    
    # 상위 10개만 표시
    display_data = table_data[:10]
    
    print(tabulate(
        display_data,
        headers=[
            "순위", "종목명", "코드", "현재가", "거래대금", "상태"
        ],
        tablefmt="grid"
    ), flush=True)
    
    if len(candidates) > 10:
        print(f"   ... 외 {len(candidates) - 10}개 종목", flush=True)
    
    # 상태별 요약
    total = len(candidates)
    buyable = len([c for c in candidates if engine.can_buy_stock(c['code'])[0]])
    already_traded = len([c for c in candidates if "재매수금지" in engine.can_buy_stock(c['code'])[1]])
    
    # 🔥 현재 전략 정보 추가
    position_value, max_positions = engine.update_trading_strategy()
    print(f"\n📊 검색 결과 요약: 전체 {total}개 | 매수가능 {buyable}개 | 재매수금지 {already_traded}개")
    print(f"🎯 현재 전략: 종목당 {position_value:,}원, 최대 {max_positions}종목")

def print_detailed_positions_table(engine: ScalpingEngine, token: str):
    """상세 포지션 현황 테이블 (누적 수익률 정보 포함)"""
    
    if not engine.positions:
        print(f"[INFO] 📝 현재 보유 포지션이 없습니다.", flush=True)
        return
    
    print(f"\n📊 [실시간 포지션 상세 현황] {len(engine.positions)}개", flush=True)
    
    table_data = []
    total_cost = 0
    total_current_value = 0
    total_profit = 0
    
    for i, pos in enumerate(engine.positions, 1):
        try:
            current_price = get_current_price(pos.code, token)
            
            if current_price > 0:
                current_value = pos.get_current_value(current_price)
                profit_amount, profit_rate = pos.get_profit_loss(current_price)
                
                total_cost += pos.cost
                total_current_value += current_value
                total_profit += profit_amount
                
                # 보유 시간 계산
                hold_duration = datetime.now() - pos.buy_time
                hold_minutes = int(hold_duration.total_seconds() / 60)
                hold_time_str = f"{hold_minutes}분" if hold_minutes < 60 else f"{hold_minutes//60}시간{hold_minutes%60}분"
                
                # 현재 거래대금 조회 (실시간)
                current_stock_info = get_stock_info(pos.code, token)
                current_amount = current_stock_info.get('amount', 0) if current_stock_info else 0
                
                # 상태 표시
                if profit_rate >= 4.5:
                    status = "🟢 익절임박"
                elif profit_rate >= 2.0:
                    status = "🟢 수익확대"
                elif profit_rate > 0:
                    status = "🟢 수익"
                elif profit_rate >= -2.0:
                    status = "⚪ 소폭손실"
                elif profit_rate >= -4.5:
                    status = "🔴 손실확대"
                else:
                    status = "🔴 손절임박"
                
                table_data.append([
                    i,
                    pos.name[:8] + "..." if len(pos.name) > 8 else pos.name,
                    f"{pos.buy_price:,}",
                    f"{current_price:,}",
                    f"{profit_rate:+.2f}%",
                    hold_time_str,
                    f"{pos.buy_amount:,.0f}" if pos.buy_amount > 0 else "-",
                    f"{current_amount:,.0f}" if current_amount > 0 else "-",
                    status
                ])
        except Exception as e:
            table_data.append([
                i,
                pos.name[:8] + "..." if len(pos.name) > 8 else pos.name,
                f"{pos.buy_price:,}",
                "조회실패",
                "-",
                "-",
                "-",
                "-",
                "❓ 오류"
            ])
    
    if table_data:
        print(tabulate(
            table_data,
            headers=[
                "순번", "종목명", "매수가", "현재가", "수익률", "보유시간", 
                "매수시거래대금", "현재거래대금", "상태"
            ],
            tablefmt="grid"
        ), flush=True)
        
        # 포트폴리오 종합 요약 + 누적 수익률
        if total_cost > 0:
            total_profit_rate = (total_profit / total_cost * 100)
            portfolio = engine.money_manager.get_portfolio_value()
            cumulative_return = portfolio.get('cumulative_return', 0)
            
            print(f"\n💼 포트폴리오 종합: 투자금 {total_cost:,}원 → "
                  f"평가금액 {total_current_value:,}원 "
                  f"({total_profit:+,}원, {total_profit_rate:+.2f}%)")
            print(f"🎯 누적 수익률: {cumulative_return:+.2f}% (원금 대비)")
            
            # 익절/손절 임박 알림
            near_profit = len([p for p in table_data if "익절임박" in str(p[-1])])
            near_loss = len([p for p in table_data if "손절임박" in str(p[-1])])
            
            if near_profit > 0:
                print(f"🟢 익절 임박: {near_profit}개 종목 (+4.5% 이상)")
            if near_loss > 0:
                print(f"🔴 손절 임박: {near_loss}개 종목 (-4.5% 이하)")

# ================================================================================
# 조건검색 함수 (기존 유지)
# ================================================================================

async def find_scalping_targets(engine: ScalpingEngine, token: str, top_n: int = None) -> List[Dict]:
    """단타 매수 대상 종목 검색"""
    all_candidates = []
    
    print(f"\n🔍 조건검색식 매수 대상 검색 시작...", flush=True)
    
    for seq in CONDITION_SEQ_LIST:
        try:
            print(f"\n📡 조건검색식 {seq}번 실행 중...", flush=True)
            codes, cond_name = await get_condition_codes(seq, token)
            
            if not codes:
                print(f"📝 조건검색식 {seq}번 결과 없음", flush=True)
                continue
            
            print(f"✅ 조건검색식 {seq}번 ({cond_name}) - {len(codes)}개 종목 발견", flush=True)
            
            # 처리할 종목 수 결정
            if top_n is None:
                process_count = len(codes)  # 전체 처리
                print(f"📊 디버깅: 전체 {process_count}개 종목 처리 중...", flush=True)
            else:
                process_count = min(len(codes), top_n)
                print(f"📊 디버깅: 상위 {process_count}개 종목 처리 중...", flush=True)
            
            # 종목 정보 수집 및 필터링
            candidates = []
            etf_count = 0
            api_fail_count = 0
            
            for i, code in enumerate(codes[:process_count]):
                if i > 0:
                    time.sleep(0.1)  # API 호출 간격
                
                code = normalize_code(code)
                info = get_stock_info(code, token)
                
                if not info:
                    api_fail_count += 1
                    print(f"  ❌ API 실패: {code}", flush=True)
                    continue
                
                if is_etf_etn(info.get("name", "")):
                    etf_count += 1
                    print(f"  🚫 ETF/ETN 제외: {info.get('name', '')}({code})", flush=True)
                    continue
                
                candidate = {
                    "code": code,
                    "name": info["name"],
                    "price": info["price"],
                    "amount": info["amount"],
                    "condition_seq": seq,
                    "condition_name": cond_name
                }
                candidates.append(candidate)
                print(f"  ✅ 추가: {info['name']}({code}) - {info['amount']:,}원", flush=True)
            
            # 필터링 결과 요약
            print(f"📊 필터링 결과: {process_count}개 처리 → {len(candidates)}개 유효 "
                  f"(ETF제외: {etf_count}개, API실패: {api_fail_count}개)", flush=True)
            
            # 거래대금 순으로 정렬
            candidates.sort(key=lambda x: x["amount"], reverse=True)
            
            # 조건검색식 결과 테이블 표시 (동적 전략 반영)
            print_condition_results_table(candidates, engine, seq, cond_name)
            
            # 매수 가능한 종목만 전체 후보에 추가
            for candidate in candidates:
                can_buy, reason = engine.can_buy_stock(candidate["code"])
                if can_buy:
                    all_candidates.append(candidate)
                    
        except Exception as e:
            print(f"[WARN] 조건검색식 {seq} 실행 실패: {e}", flush=True)
        
        time.sleep(0.5)  # 조건검색식 간 대기
    
    # 전체 후보 거래대금 순으로 정렬
    all_candidates.sort(key=lambda x: x["amount"], reverse=True)
    
    if all_candidates:
        print(f"\n🎯 최종 매수 후보: {len(all_candidates)}개 종목 (거래대금 순)", flush=True)
        for i, candidate in enumerate(all_candidates[:5], 1):
            print(f"  {i}. {candidate['name']} - {candidate['amount']:,}원 (조건{candidate['condition_seq']})", flush=True)
    else:
        print(f"\n📝 매수 가능한 종목이 없습니다.", flush=True)
    
    return all_candidates

# ================================================================================
# 테스트 모드 지원 함수들 (기존 유지)
# ================================================================================

def is_test_mode():
    """테스트 모드 여부 확인"""
    return os.getenv('SCALPING_TEST_MODE') == '1'

def is_trading_time_safe():
    """매매 가능 시간 확인 (테스트 모드 지원)"""
    if is_test_mode():
        print("[테스트 모드] ⚡ 시간 제약 무시 - 매매 실행", flush=True)
        return True
    
    now = datetime.now()
    return TRADING_START_HOUR <= now.hour < TRADING_END_HOUR

def is_force_sell_time_safe():
    """강제 청산 시간 확인 (테스트 모드 지원)"""
    if is_test_mode():
        print("[테스트 모드] ⚡ 강제청산 방지", flush=True)
        return False
    
    now = datetime.now()
    return now.hour >= FORCE_SELL_HOUR and now.minute >= FORCE_SELL_MINUTE

# ================================================================================
# 테스트용 메인 실행부
# ================================================================================

if __name__ == "__main__":
    async def test_scalping_engine():
        print("🔥 V3.1 누적 수익률 강화 단타 매매 엔진 테스트 시작")
        print("⚠️  [주의] 이는 엔진 테스트용입니다. 실제 시스템은 scalping_runner.py를 사용하세요!")
        print("=" * 80)
        
        try:
            # 하루 거래용 토큰 검증
            token = ensure_token_for_full_trading_day()
            
            # 🔥 누적 수익률 강화 엔진 생성
            engine = ScalpingEngine()
            
            print("🧪 [테스트 모드] 누적 수익률 강화 + 동적 전략 엔진 검증 중...")
            
            # 초기 상태 출력 (누적 수익률 정보 포함)
            engine.print_status()
            
            # 매수 대상 검색
            print("\n🔍 매수 대상 검색 테스트... (전체 결과 처리)")
            candidates = await find_scalping_targets(engine, token, top_n=None)
            
            if candidates:
                print(f"\n📋 테스트용 매수 대상 ({len(candidates)}개):")
                for i, candidate in enumerate(candidates[:3], 1):
                    print(f"  {i}. {candidate['name']} - {candidate['amount']:,}원")
                
                # 테스트 매수 (누적 VirtualMoneyManager + 동적 전략)
                print("\n🧪 [테스트] 2개 종목만 매수 테스트 (누적 VirtualMoneyManager + 동적 전략)...")
                for candidate in candidates[:2]:
                    success = engine.buy_stock(
                        candidate["code"],
                        candidate["name"], 
                        candidate["price"],
                        candidate["condition_seq"],
                        candidate["amount"]
                    )
                    if success:
                        print(f"  ✅ 누적 매수 성공: {candidate['name']}")
                    else:
                        print(f"  ❌ 누적 매수 실패: {candidate['name']}")
                    time.sleep(0.5)
            
            # 매수 후 상태 (누적 수익률 + 동적 전략 정보)
            if engine.positions:
                print_detailed_positions_table(engine, token)
            else:
                engine.print_status()
            
            # 청산 조건 체크 시뮬레이션
            print("\n🔍 청산 조건 체크 테스트...")
            exit_count = engine.check_exit_conditions(token)
            print(f"청산된 포지션: {exit_count}개")
            
            # 최종 상태 (누적 수익률 강화 정보)
            engine.print_status(token)
            
            # 🔥 누적 수익률 상세 통계 출력
            print("\n📊 누적 수익률 상세 통계:")
            engine.money_manager.print_transaction_history(10)
            
            # 토큰 상태 최종 확인
            token_info = get_token_info()
            if token_info:
                print(f"\n🔑 토큰 상태: 남은시간 {token_info['remaining_hours']:.1f}시간")
            
            print("\n" + "=" * 80)
            print("🧪 [테스트 완료] 누적 수익률 강화 + 동적 전략 엔진 검증 완료!")
            print("🚀 실제 거래를 원하시면 'python scalping_runner.py'를 실행하세요!")
            print("💾 누적 거래 내역은 virtual_money_data/ 폴더에 JSON으로 저장됩니다!")
            print("📊 누적 수익률 확인: 'python virtual_money_manager.py' 실행")
            print("🎯 복리 효과와 연간 수익률 예상까지 모든 지표를 확인하세요!")
            
        except Exception as e:
            print(f"❌ 테스트 실행 실패: {e}")
            import traceback
            traceback.print_exc()
    
    asyncio.run(test_scalping_engine())