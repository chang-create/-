"""
🔥 V3.0 단타 매매 시스템 - 완전 통합 버전
기존 scalping_engine.py + 새로운 모듈들 통합
"""

import asyncio
import sys
import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

# 기존 모듈 import
from scalping_engine import (
    get_valid_access_token, ensure_token_for_full_trading_day,
    get_condition_codes, get_stock_info, get_current_price,
    normalize_code, is_etf_etn, WS_URL, CONDITION_SEQ_LIST,
    INITIAL_CAPITAL, MAX_POSITION_VALUE, MAX_POSITIONS,
    PROFIT_TARGET, STOP_LOSS, TRADING_START_HOUR, TRADING_END_HOUR,
    FORCE_SELL_HOUR, FORCE_SELL_MINUTE, LOOP_INTERVAL
)

# 새로운 모듈 import
from virtual_money_manager import VirtualMoneyManager, VirtualTransaction
from scalping_portfolio import ScalpingPortfolio, ScalpingPosition
from scalping_monitor import ScalpingMonitor

class ScalpingEngineV3:
    """🔥 V3.0 단타 매매 엔진 - 완전 통합 버전"""
    
    def __init__(self, log_dir: str = None):
        self.log_dir = log_dir
        
        # 🔥 새로운 모듈들로 구성
        self.money_manager = VirtualMoneyManager(INITIAL_CAPITAL, log_dir)
        self.portfolio = ScalpingPortfolio(MAX_POSITIONS, MAX_POSITION_VALUE, log_dir)
        self.monitor = ScalpingMonitor(self.portfolio, self.money_manager, log_dir)
        
        # 기존 호환성을 위한 속성들
        self.virtual_capital = INITIAL_CAPITAL
        self.daily_trades = []
        
        # 기존 상태 복원 시도
        if log_dir:
            self._load_existing_state()
    
    def _load_existing_state(self):
        """기존 상태 복원"""
        try:
            # 오늘 날짜로 기존 상태 로드
            today = datetime.now().strftime('%Y%m%d')
            
            # 가상 자금 상태 복원
            if self.money_manager.load_daily_transactions(today):
                print("[INFO] 💰 기존 가상 자금 상태 복원 완료")
            
            # 포트폴리오 상태 복원
            if self.portfolio.load_portfolio_state(today):
                print("[INFO] 📊 기존 포트폴리오 상태 복원 완료")
                
        except Exception as e:
            print(f"[WARN] 기존 상태 복원 실패: {e}")
    
    @property
    def available_cash(self):
        """기존 코드 호환성"""
        return self.money_manager.available_cash
    
    @property
    def positions(self):
        """기존 코드 호환성"""
        return self.portfolio.positions
    
    @property
    def traded_today(self):
        """기존 코드 호환성"""
        return self.portfolio.traded_today
    
    @property
    def daily_pnl(self):
        """기존 코드 호환성"""
        return self.money_manager.daily_pnl
    
    def log_activity(self, message: str):
        """활동 로그 기록"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        print(log_entry, flush=True)
        
        if self.log_dir:
            try:
                log_file = os.path.join(self.log_dir, f"scalping_log_{datetime.now().strftime('%Y%m%d')}.txt")
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(log_entry + "\n")
            except Exception:
                pass
    
    def can_buy_stock(self, code: str) -> Tuple[bool, str]:
        """매수 가능 여부 확인 (기존 호환성)"""
        return self.portfolio.can_buy_stock(code, self.money_manager.available_cash)
    
    def buy_stock(self, code: str, name: str, price: int, condition_seq: int = 0, buy_amount: int = 0) -> bool:
        """🔥 V3.0 가상 매수 실행"""
        code = normalize_code(code)
        
        # 매수 가능 여부 확인
        can_buy, reason = self.portfolio.can_buy_stock(code, self.money_manager.available_cash)
        if not can_buy:
            self.log_activity(f"❌ 매수 실패 {name}({code}): {reason}")
            return False
        
        # 가상 매수 실행
        transaction = self.money_manager.execute_virtual_buy(
            code, name, price, MAX_POSITION_VALUE, condition_seq
        )
        
        if not transaction:
            self.log_activity(f"❌ 매수 실패 {name}({code}): 자금 부족")
            return False
        
        # 포트폴리오에 포지션 추가
        success = self.portfolio.add_position(
            code, name, price, transaction.quantity, condition_seq, buy_amount
        )
        
        if not success:
            self.log_activity(f"❌ 매수 실패 {name}({code}): 포트폴리오 추가 실패")
            return False
        
        # 기존 호환성을 위한 거래 기록
        trade_record = {
            "type": "buy",
            "code": code,
            "name": name,
            "price": price,
            "quantity": transaction.quantity,
            "amount": transaction.amount,
            "buy_amount": buy_amount,
            "time": datetime.now().strftime("%H:%M:%S"),
            "condition_seq": condition_seq
        }
        self.daily_trades.append(trade_record)
        
        self.log_activity(f"✅ 매수 {name}({code}) {transaction.quantity}주 @{price:,}원 "
                         f"(투자: {transaction.amount:,}원)")
        return True
    
    def sell_position(self, position: ScalpingPosition, current_price: int, reason: str) -> bool:
        """🔥 V3.0 포지션 매도"""
        if position not in self.portfolio.positions:
            return False
        
        # 해당 포지션의 매수 거래 찾기
        buy_transaction = None
        for transaction in self.money_manager.transactions:
            if (transaction.type == 'buy' and 
                transaction.code == position.code and 
                transaction.quantity == position.quantity):
                buy_transaction = transaction
                break
        
        if not buy_transaction:
            self.log_activity(f"⚠️  매수 거래 기록을 찾을 수 없음: {position.name}")
            return False
        
        # 가상 매도 실행
        sell_transaction = self.money_manager.execute_virtual_sell(
            buy_transaction, current_price, reason
        )
        
        if not sell_transaction:
            return False
        
        # 포트폴리오에서 제거
        removed_position = self.portfolio.remove_position(position.code)
        if not removed_position:
            return False
        
        # 기존 호환성을 위한 거래 기록
        trade_record = {
            "type": "sell",
            "code": position.code,
            "name": position.name,
            "buy_price": position.buy_price,
            "sell_price": current_price,
            "quantity": position.quantity,
            "profit_amount": sell_transaction.profit_amount,
            "profit_rate": sell_transaction.profit_rate,
            "reason": reason,
            "time": datetime.now().strftime("%H:%M:%S"),
            "hold_duration": str(datetime.now() - position.buy_time).split('.')[0]
        }
        self.daily_trades.append(trade_record)
        
        emoji = "🟢" if sell_transaction.profit_amount > 0 else "🔴"
        self.log_activity(f"{emoji} 매도 {position.name}({position.code}) "
                         f"{position.buy_price:,}→{current_price:,} "
                         f"({sell_transaction.profit_rate:+.2f}%) {reason}")
        
        return True
    
    def check_exit_conditions(self, token: str) -> int:
        """🔥 V3.0 청산 조건 체크 및 실행"""
        if not self.portfolio.positions:
            return 0
        
        exit_count = 0
        current_prices = {}
        
        # 현재가 조회
        for position in self.portfolio.positions:
            try:
                current_price = get_current_price(position.code, token)
                if current_price > 0:
                    current_prices[position.code] = current_price
            except Exception as e:
                self.log_activity(f"⚠️  {position.name} 현재가 조회 실패: {e}")
        
        # 청산 조건 체크 및 실행
        positions_to_exit = []
        for position in self.portfolio.positions:
            current_price = current_prices.get(position.code, 0)
            if current_price > 0:
                should_exit, exit_reason = position.should_exit(current_price, PROFIT_TARGET, STOP_LOSS)
                if should_exit:
                    positions_to_exit.append((position, current_price, exit_reason))
        
        # 청산 실행
        for position, current_price, reason in positions_to_exit:
            if self.sell_position(position, current_price, reason):
                exit_count += 1
        
        return exit_count
    
    def force_sell_all(self, token: str) -> int:
        """🔥 V3.0 강제 청산 (15:10)"""
        if not self.portfolio.positions:
            return 0
        
        self.log_activity("🚨 강제 청산 시작 (15:10)")
        
        force_sell_count = 0
        positions_copy = self.portfolio.positions.copy()
        
        for position in positions_copy:
            try:
                current_price = get_current_price(position.code, token)
                if current_price > 0:
                    if self.sell_position(position, current_price, "강제청산"):
                        force_sell_count += 1
            except Exception as e:
                self.log_activity(f"⚠️  {position.name} 강제청산 실패: {e}")
        
        self.log_activity(f"🚨 강제 청산 완료: {force_sell_count}건")
        return force_sell_count
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """🔥 V3.0 포트폴리오 현황 (기존 호환성)"""
        money_status = self.money_manager.get_portfolio_value()
        portfolio_summary = self.portfolio.get_portfolio_summary()
        
        return {
            "virtual_capital": self.virtual_capital,
            "available_cash": money_status['available_cash'],
            "position_count": portfolio_summary['total_positions'],
            "position_value": portfolio_summary['total_invested'],
            "total_capital": money_status['total_value'],
            "daily_pnl": money_status['daily_pnl'],
            "daily_return": money_status['daily_return'],
            "traded_stocks_count": portfolio_summary['traded_today_count']
        }
    
    def print_status(self, token: str = None):
        """🔥 V3.0 현황 출력 (완전히 새로운 모니터 사용)"""
        if token and self.portfolio.positions:
            # 현재가 조회
            current_prices = {}
            for position in self.portfolio.positions:
                try:
                    current_prices[position.code] = get_current_price(position.code, token)
                except Exception:
                    current_prices[position.code] = 0
            
            self.monitor.print_comprehensive_status(current_prices)
        else:
            self.monitor.print_comprehensive_status()
    
    def print_detailed_positions(self, token: str):
        """🔥 V3.0 상세 포지션 테이블"""
        if not self.portfolio.positions:
            print("[INFO] 📝 현재 보유 포지션이 없습니다.")
            return
        
        # 현재가 조회
        current_prices = {}
        for position in self.portfolio.positions:
            try:
                current_prices[position.code] = get_current_price(position.code, token)
            except Exception:
                current_prices[position.code] = 0
        
        self.monitor.print_detailed_positions_table(current_prices)
    
    def save_comprehensive_report(self):
        """🔥 V3.0 종합 보고서 저장"""
        if self.log_dir:
            # 모니터링 보고서 저장
            self.monitor.save_monitoring_report()
            
            # 기존 형식 보고서도 저장 (호환성)
            self._save_legacy_report()
    
    def _save_legacy_report(self):
        """기존 형식 호환성 보고서"""
        if not self.log_dir:
            return
        
        today = datetime.now().strftime('%Y%m%d')
        report_file = os.path.join(self.log_dir, f"daily_report_{today}.json")
        
        try:
            status = self.get_portfolio_status()
            buy_trades = [t for t in self.daily_trades if t["type"] == "buy"]
            sell_trades = [t for t in self.daily_trades if t["type"] == "sell"]
            
            report_data = {
                "date": today,
                "summary": {
                    "initial_capital": INITIAL_CAPITAL,
                    "final_capital": status["available_cash"] + status["position_value"],
                    "daily_pnl": status["daily_pnl"],
                    "daily_return": status["daily_return"],
                    "total_trades": len(buy_trades),
                    "completed_trades": len(sell_trades),
                    "remaining_positions": len(self.portfolio.positions)
                },
                "trades": self.daily_trades,
                "traded_stocks": list(self.portfolio.traded_today),
                "final_positions": [
                    {
                        "code": pos.code,
                        "name": pos.name,
                        "buy_price": pos.buy_price,
                        "quantity": pos.quantity,
                        "cost": pos.cost
                    } for pos in self.portfolio.positions
                ]
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            print(f"[저장 완료] 📄 호환성 보고서: {report_file}")
            
        except Exception as e:
            print(f"[ERROR] 호환성 보고서 저장 실패: {e}")

# ================================================================================
# 🔥 V3.0 조건검색 함수 (기존과 동일하지만 새 엔진 사용)
# ================================================================================

async def find_scalping_targets_v3(engine: ScalpingEngineV3, token: str, top_n: int = None) -> List[Dict]:
    """🔥 V3.0 단타 매수 대상 검색"""
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
                process_count = len(codes)
            else:
                process_count = min(len(codes), top_n)
            
            # 종목 정보 수집 및 필터링
            candidates = []
            for i, code in enumerate(codes[:process_count]):
                if i > 0:
                    time.sleep(0.1)
                
                code = normalize_code(code)
                info = get_stock_info(code, token)
                
                if not info:
                    continue
                
                if is_etf_etn(info.get("name", "")):
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
            
            # 거래대금 순으로 정렬
            candidates.sort(key=lambda x: x["amount"], reverse=True)
            
            # 매수 가능한 종목만 전체 후보에 추가
            for candidate in candidates:
                can_buy, reason = engine.can_buy_stock(candidate["code"])
                if can_buy:
                    all_candidates.append(candidate)
                    
        except Exception as e:
            print(f"[WARN] 조건검색식 {seq} 실행 실패: {e}", flush=True)
        
        time.sleep(0.5)
    
    # 전체 후보 거래대금 순으로 정렬
    all_candidates.sort(key=lambda x: x["amount"], reverse=True)
    
    return all_candidates

# ================================================================================
# 🔥 V3.0 메인 실행 루프
# ================================================================================

async def execute_scalping_loop_v3(engine: ScalpingEngineV3, token: str, loop_count: int) -> int:
    """🔥 V3.0 단타 매매 한 루프 실행"""
    
    executed_actions = 0
    
    try:
        # 1. 청산 조건 체크
        print(f"🔍 청산 조건 체크 중...", flush=True)
        exit_count = engine.check_exit_conditions(token)
        
        if exit_count > 0:
            print(f"✅ {exit_count}개 포지션 청산 완료", flush=True)
            executed_actions += exit_count
        else:
            print(f"📝 청산 대상 없음", flush=True)
        
        # 2. 신규 매수 대상 검색
        available_slots = engine.portfolio.get_available_slots()
        
        if available_slots > 0:
            print(f"🔍 신규 매수 대상 검색 중... (빈 자리: {available_slots}개)", flush=True)
            
            candidates = await find_scalping_targets_v3(engine, token, top_n=None)
            
            if candidates:
                print(f"📋 매수 후보 {len(candidates)}개 발견", flush=True)
                
                buy_count = 0
                for i, candidate in enumerate(candidates, 1):
                    if buy_count >= available_slots:
                        break
                    
                    success = engine.buy_stock(
                        candidate["code"],
                        candidate["name"],
                        candidate["price"],
                        candidate["condition_seq"],
                        candidate["amount"]
                    )
                    
                    if success:
                        buy_count += 1
                        executed_actions += 1
                    
                    time.sleep(0.3)
                
                if buy_count > 0:
                    print(f"🎉 신규 매수 완료: {buy_count}개 종목", flush=True)
            else:
                print(f"📝 매수 후보 없음", flush=True)
        else:
            print(f"📊 포트폴리오 만석 - 청산 대기 중", flush=True)
        
        # 3. 현재 포지션 현황 출력
        if engine.portfolio.positions:
            engine.print_detailed_positions(token)
        else:
            print(f"📝 현재 보유 포지션 없음", flush=True)
        
    except Exception as e:
        print(f"❌ 루프 실행 중 오류: {e}", flush=True)
        import traceback
        traceback.print_exc()
    
    return executed_actions