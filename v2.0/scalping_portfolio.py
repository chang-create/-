from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import os

@dataclass
class ScalpingPosition:
    """단타 포지션 정보"""
    code: str
    name: str
    buy_price: int
    quantity: int
    buy_time: datetime
    condition_seq: int
    buy_amount: int  # 매수시점 거래대금
    cost: int  # 총 매수 비용
    
    def get_current_value(self, current_price: int) -> int:
        """현재 평가금액"""
        return current_price * self.quantity
    
    def get_profit_loss(self, current_price: int) -> Tuple[int, float]:
        """손익 계산 (원, %)"""
        current_value = self.get_current_value(current_price)
        profit_amount = current_value - self.cost
        profit_rate = (profit_amount / self.cost * 100) if self.cost > 0 else 0
        return profit_amount, profit_rate
    
    def should_exit(self, current_price: int, profit_target: float = 5.0, stop_loss: float = -5.0) -> Tuple[bool, str]:
        """청산 조건 체크"""
        _, profit_rate = self.get_profit_loss(current_price)
        
        if profit_rate >= profit_target:
            return True, "익절"
        elif profit_rate <= stop_loss:
            return True, "손절"
        
        return False, ""
    
    def get_hold_duration(self) -> timedelta:
        """보유 시간"""
        return datetime.now() - self.buy_time

class ScalpingPortfolio:
    """🔥 V2.0 단타 전용 포트폴리오 관리"""
    
    def __init__(self, max_positions: int = 5, max_position_value: int = 100_000, save_dir: str = None):
        self.max_positions = max_positions
        self.max_position_value = max_position_value
        self.positions: List[ScalpingPosition] = []
        self.traded_today: Set[str] = set()  # 오늘 거래한 종목들
        self.blocked_codes: Set[str] = set()  # 일시적 차단 종목
        self.save_dir = save_dir
        
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
    
    def normalize_code(self, code: str) -> str:
        """종목코드 정규화"""
        code = str(code).replace("A", "").zfill(6)
        return "A" + code
    
    def can_buy_stock(self, code: str, available_cash: int = None) -> Tuple[bool, str]:
        """단타 매수 가능 여부 종합 판단"""
        code = self.normalize_code(code)
        
        # 1. 이미 거래한 종목인가? (재매수 금지)
        if code in self.traded_today:
            return False, "재매수금지"
        
        # 2. 일시적 차단 종목인가?
        if code in self.blocked_codes:
            return False, "일시차단"
        
        # 3. 포지션 한도 초과?
        if len(self.positions) >= self.max_positions:
            return False, "포지션한도초과"
        
        # 4. 자금 부족?
        if available_cash is not None and available_cash < self.max_position_value:
            return False, "자금부족"
        
        # 5. 이미 보유 중인 종목?
        if self.get_position_by_code(code):
            return False, "이미보유"
        
        return True, "매수가능"
    
    def add_position(self, code: str, name: str, buy_price: int, quantity: int, 
                    condition_seq: int = 0, buy_amount: int = 0) -> bool:
        """포지션 추가"""
        code = self.normalize_code(code)
        
        # 재매수 가능 여부 확인
        can_buy, reason = self.can_buy_stock(code)
        if not can_buy:
            return False
        
        # 포지션 생성
        position = ScalpingPosition(
            code=code,
            name=name,
            buy_price=buy_price,
            quantity=quantity,
            buy_time=datetime.now(),
            condition_seq=condition_seq,
            buy_amount=buy_amount,
            cost=buy_price * quantity
        )
        
        # 포지션 추가
        self.positions.append(position)
        self.traded_today.add(code)
        
        # 저장
        self._save_portfolio_state()
        
        return True
    
    def remove_position(self, code: str) -> Optional[ScalpingPosition]:
        """포지션 제거"""
        code = self.normalize_code(code)
        
        for i, position in enumerate(self.positions):
            if position.code == code:
                removed_position = self.positions.pop(i)
                self._save_portfolio_state()
                return removed_position
        
        return None
    
    def get_position_by_code(self, code: str) -> Optional[ScalpingPosition]:
        """코드로 포지션 조회"""
        code = self.normalize_code(code)
        
        for position in self.positions:
            if position.code == code:
                return position
        
        return None
    
    def get_positions_for_exit_check(self, profit_target: float = 5.0, 
                                   stop_loss: float = -5.0) -> List[Tuple[ScalpingPosition, str]]:
        """청산 조건에 해당하는 포지션들 반환"""
        exit_candidates = []
        
        for position in self.positions:
            # 현재가는 외부에서 조회해야 함 (API 호출)
            # 여기서는 조건만 확인하는 구조로 설계
            exit_candidates.append((position, "check_needed"))
        
        return exit_candidates
    
    def get_available_slots(self) -> int:
        """사용 가능한 포지션 슬롯 수"""
        return max(0, self.max_positions - len(self.positions))
    
    def is_portfolio_full(self) -> bool:
        """포트폴리오 만석 여부"""
        return len(self.positions) >= self.max_positions
    
    def block_code_temporarily(self, code: str, duration_minutes: int = 30):
        """종목 일시적 차단 (API 오류 등의 경우)"""
        code = self.normalize_code(code)
        self.blocked_codes.add(code)
        
        # TODO: 시간 기반 자동 해제 로직 필요
        # 현재는 간단하게 set으로만 관리
    
    def unblock_code(self, code: str):
        """종목 차단 해제"""
        code = self.normalize_code(code)
        self.blocked_codes.discard(code)
    
    def get_portfolio_summary(self) -> Dict:
        """포트폴리오 요약 정보"""
        total_cost = sum(pos.cost for pos in self.positions)
        
        return {
            'total_positions': len(self.positions),
            'max_positions': self.max_positions,
            'available_slots': self.get_available_slots(),
            'total_invested': total_cost,
            'traded_today_count': len(self.traded_today),
            'blocked_codes_count': len(self.blocked_codes),
            'is_full': self.is_portfolio_full(),
            'utilization_rate': (len(self.positions) / self.max_positions * 100) if self.max_positions > 0 else 0
        }
    
    def get_position_details(self, include_current_prices: bool = False) -> List[Dict]:
        """포지션 상세 정보"""
        details = []
        
        for i, pos in enumerate(self.positions, 1):
            hold_duration = pos.get_hold_duration()
            
            detail = {
                'rank': i,
                'code': pos.code,
                'name': pos.name,
                'buy_price': pos.buy_price,
                'quantity': pos.quantity,
                'cost': pos.cost,
                'buy_time': pos.buy_time.strftime('%H:%M:%S'),
                'hold_duration': str(hold_duration).split('.')[0],  # 마이크로초 제거
                'condition_seq': pos.condition_seq,
                'buy_amount': pos.buy_amount
            }
            
            details.append(detail)
        
        return details
    
    def reset_daily_trading_list(self):
        """일일 거래 종목 목록 초기화 (새로운 거래일)"""
        self.traded_today.clear()
        self.blocked_codes.clear()
        self._save_portfolio_state()
    
    def force_close_all_positions(self) -> List[ScalpingPosition]:
        """모든 포지션 강제 종료 (15:10 청산용)"""
        closed_positions = self.positions.copy()
        self.positions.clear()
        self._save_portfolio_state()
        return closed_positions
    
    def _save_portfolio_state(self):
        """포트폴리오 상태 저장"""
        if not self.save_dir:
            return
        
        today = datetime.now().strftime('%Y%m%d')
        state_file = os.path.join(self.save_dir, f"portfolio_state_{today}.json")
        
        try:
            # 포지션 데이터를 JSON 직렬화 가능한 형태로 변환
            positions_data = []
            for pos in self.positions:
                positions_data.append({
                    'code': pos.code,
                    'name': pos.name,
                    'buy_price': pos.buy_price,
                    'quantity': pos.quantity,
                    'buy_time': pos.buy_time.isoformat(),
                    'condition_seq': pos.condition_seq,
                    'buy_amount': pos.buy_amount,
                    'cost': pos.cost
                })
            
            state_data = {
                'positions': positions_data,
                'traded_today': list(self.traded_today),
                'blocked_codes': list(self.blocked_codes),
                'portfolio_summary': self.get_portfolio_summary(),
                'last_updated': datetime.now().isoformat()
            }
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"[WARN] 포트폴리오 상태 저장 실패: {e}")
    
    def load_portfolio_state(self, date_str: str = None) -> bool:
        """포트폴리오 상태 로드"""
        if not self.save_dir:
            return False
        
        if not date_str:
            date_str = datetime.now().strftime('%Y%m%d')
        
        state_file = os.path.join(self.save_dir, f"portfolio_state_{date_str}.json")
        
        try:
            if not os.path.exists(state_file):
                return False
            
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            # 포지션 복원
            self.positions = []
            for pos_data in state_data.get('positions', []):
                position = ScalpingPosition(
                    code=pos_data['code'],
                    name=pos_data['name'],
                    buy_price=pos_data['buy_price'],
                    quantity=pos_data['quantity'],
                    buy_time=datetime.fromisoformat(pos_data['buy_time']),
                    condition_seq=pos_data.get('condition_seq', 0),
                    buy_amount=pos_data.get('buy_amount', 0),
                    cost=pos_data['cost']
                )
                self.positions.append(position)
            
            # 거래 목록 복원
            self.traded_today = set(state_data.get('traded_today', []))
            self.blocked_codes = set(state_data.get('blocked_codes', []))
            
            return True
            
        except Exception as e:
            print(f"[WARN] 포트폴리오 상태 로드 실패: {e}")
            return False
    
    def print_portfolio_status(self):
        """포트폴리오 현황 출력"""
        summary = self.get_portfolio_summary()
        
        print(f"\n{'='*60}")
        print(f"📊 단타 포트폴리오 현황")
        print(f"{'='*60}")
        print(f"📈 보유 포지션: {summary['total_positions']}/{summary['max_positions']}개 "
              f"({summary['utilization_rate']:.1f}% 활용)")
        print(f"💰 총 투자금: {summary['total_invested']:,}원")
        print(f"🔄 오늘 거래: {summary['traded_today_count']}개 종목")
        
        if summary['blocked_codes_count'] > 0:
            print(f"🚫 차단 종목: {summary['blocked_codes_count']}개")
        
        if self.positions:
            print(f"\n📋 개별 포지션:")
            details = self.get_position_details()
            for detail in details:
                print(f"  {detail['rank']}. {detail['name']} "
                      f"({detail['quantity']}주 @{detail['buy_price']:,}원) "
                      f"보유: {detail['hold_duration']}")
        
        print(f"{'='*60}")