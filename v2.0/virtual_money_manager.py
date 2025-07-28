"""
🔥 V2.3 가상 자금 관리 시스템 - 누적 수익률 강화 + 백테스팅 분석
Real-time cumulative returns tracking with comprehensive backtesting analysis
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from tabulate import tabulate
import glob
import uuid

@dataclass
class Trade:
    """거래 정보 - ScalpingEngine 완전 호환"""
    code: str = ""
    name: str = ""
    action: str = ""
    quantity: int = 0
    price: int = 0
    amount: int = 0
    timestamp: str = ""
    session_id: str = ""
    transaction_type: str = ""
    condition_seq: str = ""
    
    def get_date(self) -> str:
        """거래 날짜 반환 (YYYY-MM-DD)"""
        if not self.timestamp:
            return datetime.now().strftime('%Y-%m-%d')
        
        # 다양한 timestamp 형식 지원
        try:
            # ISO 형식: YYYY-MM-DD HH:MM:SS
            if len(self.timestamp) >= 19 and '-' in self.timestamp and ':' in self.timestamp:
                return self.timestamp.split(' ')[0]
            # 날짜만: YYYY-MM-DD
            elif len(self.timestamp) == 10 and '-' in self.timestamp:
                return self.timestamp
            # YYYYMMDD 형식
            elif len(self.timestamp) == 8 and self.timestamp.isdigit():
                return f"{self.timestamp[:4]}-{self.timestamp[4:6]}-{self.timestamp[6:8]}"
            # YYYYMMDD_HHMMSS 형식
            elif '_' in self.timestamp:
                date_part = self.timestamp.split('_')[0]
                if len(date_part) == 8 and date_part.isdigit():
                    return f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
            else:
                # 기본값으로 파싱 시도
                dt = datetime.strptime(self.timestamp, '%Y-%m-%d %H:%M:%S')
                return dt.strftime('%Y-%m-%d')
        except (ValueError, IndexError):
            pass
        
        # 파싱 실패 시 현재 날짜 반환
        return datetime.now().strftime('%Y-%m-%d')
    
    def __post_init__(self):
        """자동 설정 및 호환성 처리"""
        # timestamp 자동 생성
        if not self.timestamp:
            self.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
        # session_id 자동 생성  
        if not self.session_id:
            self.session_id = str(uuid.uuid4())[:8]
            
        # action ↔ transaction_type 양방향 변환
        if self.action and not self.transaction_type:
            if self.action in ["매수", "buy"]:
                self.transaction_type = "buy"
            elif self.action in ["매도", "sell"]:
                self.transaction_type = "sell"
                
        if self.transaction_type and not self.action:
            if self.transaction_type == "buy":
                self.action = "매수"
            elif self.transaction_type == "sell":
                self.action = "매도"
                
        # 기본값 설정
        if not self.action:
            self.action = "매수"
        if not self.transaction_type:
            self.transaction_type = "buy"
                
        # amount 자동 계산
        if not self.amount and self.quantity and self.price:
            self.amount = self.quantity * self.price
            
    def to_dict(self) -> Dict:
        """완전한 딕셔너리 변환"""
        return asdict(self)
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'Trade':
        """안전한 딕셔너리 복원"""
        # 필수 필드만 추출하여 안전하게 생성
        trade_data = {}
        for field in ["code", "name", "action", "quantity", "price", "amount", 
                     "timestamp", "session_id", "transaction_type", "condition_seq"]:
            trade_data[field] = data.get(field, "")
            
        # 숫자 필드 타입 변환
        for field in ["quantity", "price", "amount"]:
            try:
                trade_data[field] = int(trade_data[field]) if trade_data[field] else 0
            except (ValueError, TypeError):
                trade_data[field] = 0
                
        return cls(**trade_data)

@dataclass
class VirtualTransaction:
    """가상 거래 내역"""
    transaction_id: str
    timestamp: str
    type: str  # "buy" or "sell"
    code: str
    name: str
    quantity: int
    price: int
    amount: int
    condition_seq: int = 0
    
    # 매도 전용 필드들
    buy_transaction_id: str = ""
    profit_amount: int = 0
    profit_rate: float = 0.0
    reason: str = ""

@dataclass 
class DailyReturn:
    """일별 수익률 기록"""
    date: str
    start_capital: int
    end_capital: int
    daily_pnl: int
    daily_return: float
    cumulative_return: float
    trades_count: int

@dataclass
class PeriodAnalysis:
    """기간별 분석 결과"""
    period_name: str
    start_date: str
    end_date: str
    start_capital: int
    end_capital: int
    total_return: float
    daily_avg_return: float
    volatility: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    trading_days: int

class VirtualMoneyManager:
    """🔥 누적 수익률 강화 + 백테스팅 분석 가상 자금 관리 시스템"""
    
    def __init__(self, initial_capital: int = 500_000, save_dir: str = "virtual_money_data"):
        self.save_dir = save_dir
        self.ensure_save_dir()
        
        # 🔥 전날 결과 및 히스토리 로드 (누적 방식)
        previous_result = self.load_previous_day_result()
        self.daily_returns_history = self.load_daily_returns_history()
        
        if previous_result:
            # 전날 최종 자금으로 시작 (누적 모드)
            self.available_cash = previous_result['final_cash']
            self.initial_capital = previous_result['final_cash']  # 오늘 시작점
            self.cumulative_days = previous_result.get('cumulative_days', 0) + 1
            self.original_capital = previous_result.get('original_capital', 500_000)
            self.max_capital = previous_result.get('max_capital', self.available_cash)
            self.min_capital = previous_result.get('min_capital', self.available_cash)
            
            print(f"[누적 모드] 📈 {self.cumulative_days}일차 시작")
            print(f"[누적 모드] 💰 전날 종료: {self.available_cash:,}원")
            
            # 🔥 누적 수익률 즉시 표시
            cumulative_pnl = self.available_cash - self.original_capital
            cumulative_return = (cumulative_pnl / self.original_capital * 100) if self.original_capital > 0 else 0
            print(f"[누적 모드] 🎯 누적 수익: {cumulative_pnl:+,}원 ({cumulative_return:+.2f}%)")
            
        else:
            # 최초 시작
            self.available_cash = initial_capital
            self.initial_capital = initial_capital
            self.cumulative_days = 1
            self.original_capital = initial_capital
            self.max_capital = initial_capital
            self.min_capital = initial_capital
            
            print(f"[누적 모드] 🚀 최초 시작: {initial_capital:,}원")
        
        self.total_invested = 0
        self.buy_transactions: List[VirtualTransaction] = []
        self.sell_transactions: List[VirtualTransaction] = []
        self.daily_pnl = 0
        
        # 🔥 추가된 통계 속성들
        self.cumulative_return = 0.0
        self.total_return = 0.0
        self.win_rate = 0.0
        self.max_drawdown = 0.0
        
        # 오늘 거래 내역 로드 (복구 기능)
        self.load_today_transactions()
    
    def ensure_save_dir(self):
        """저장 디렉토리 생성"""
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir, exist_ok=True)
    
    def load_previous_day_result(self) -> Optional[Dict]:
        """🔥 전날 최종 결과 로드 (누적 방식)"""
        # 최근 7일간 검색
        for days_back in range(1, 8):
            check_date = datetime.now() - timedelta(days=days_back)
            date_str = check_date.strftime('%Y%m%d')
            file_path = os.path.join(self.save_dir, f"virtual_transactions_{date_str}.json")
            
            try:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    portfolio = data.get('portfolio_summary', {})
                    if portfolio.get('total_value'):
                        print(f"[누적 모드] 📅 {date_str} 결과 로드: {portfolio['total_value']:,}원")
                        return {
                            'final_cash': portfolio['total_value'],
                            'cumulative_days': portfolio.get('cumulative_days', 0),
                            'original_capital': portfolio.get('original_capital', 500_000),
                            'max_capital': portfolio.get('max_capital', portfolio['total_value']),
                            'min_capital': portfolio.get('min_capital', portfolio['total_value'])
                        }
            except Exception as e:
                print(f"[WARN] {file_path} 로드 실패: {e}")
                continue
        
        return None
    
    def load_daily_returns_history(self) -> List[DailyReturn]:
        """🔥 일별 수익률 히스토리 로드"""
        history_file = os.path.join(self.save_dir, "daily_returns_history.json")
        
        try:
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return [DailyReturn(**item) for item in data]
        except Exception as e:
            print(f"[WARN] 수익률 히스토리 로드 실패: {e}")
        
        return []
    
    def save_daily_returns_history(self):
        """🔥 일별 수익률 히스토리 저장"""
        history_file = os.path.join(self.save_dir, "daily_returns_history.json")
        
        try:
            data = [asdict(item) for item in self.daily_returns_history]
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] 수익률 히스토리 저장 실패: {e}")
    
    def load_today_transactions(self):
        """오늘 거래 내역 로드 (복구 기능)"""
        today_str = datetime.now().strftime('%Y%m%d')
        file_path = os.path.join(self.save_dir, f"virtual_transactions_{today_str}.json")
        
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 기존 거래 복구
                buy_data = data.get('buy_transactions', [])
                sell_data = data.get('sell_transactions', [])
                
                self.buy_transactions = [VirtualTransaction(**tx) for tx in buy_data]
                self.sell_transactions = [VirtualTransaction(**tx) for tx in sell_data]
                
                # 현재 투자 금액 재계산
                active_buys = [tx for tx in self.buy_transactions 
                              if not any(sell.buy_transaction_id == tx.transaction_id 
                                        for sell in self.sell_transactions)]
                self.total_invested = sum(tx.amount for tx in active_buys)
                
                # 오늘 손익 재계산
                self.daily_pnl = sum(tx.profit_amount for tx in self.sell_transactions)
                
                if buy_data or sell_data:
                    print(f"[복구] 오늘 거래 {len(buy_data)}매수 {len(sell_data)}매도 복구완료")
                    
        except Exception as e:
            print(f"[WARN] 오늘 거래 복구 실패: {e}")
    
    # ================================================================================
    # 🔥 백테스팅 분석 기능들
    # ================================================================================
    
    def load_all_historical_data(self) -> Dict[str, Dict]:
        """🔥 모든 과거 데이터 로드"""
        historical_data = {}
        
        # virtual_money_data 폴더의 모든 JSON 파일 검색
        pattern = os.path.join(self.save_dir, "virtual_transactions_*.json")
        files = glob.glob(pattern)
        
        for file_path in sorted(files):
            try:
                date_str = os.path.basename(file_path).replace("virtual_transactions_", "").replace(".json", "")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                historical_data[date_str] = data
                
            except Exception as e:
                print(f"[WARN] {file_path} 로드 실패: {e}")
        
        return historical_data
    
    def analyze_historical_performance(self, days: int = None) -> PeriodAnalysis:
        """🔥 과거 성과 분석"""
        historical_data = self.load_all_historical_data()
        
        if not historical_data:
            return PeriodAnalysis(
                period_name="데이터 없음",
                start_date="", end_date="", start_capital=0, end_capital=0,
                total_return=0, daily_avg_return=0, volatility=0, max_drawdown=0,
                win_rate=0, total_trades=0, trading_days=0
            )
        
        # 날짜 정렬
        sorted_dates = sorted(historical_data.keys())
        
        # 기간 설정
        if days:
            # 최근 N일
            analysis_dates = sorted_dates[-days:] if len(sorted_dates) > days else sorted_dates
            period_name = f"최근 {len(analysis_dates)}일"
        else:
            # 전체 기간
            analysis_dates = sorted_dates
            period_name = f"전체 {len(analysis_dates)}일"
        
        if not analysis_dates:
            return PeriodAnalysis(
                period_name="데이터 없음",
                start_date="", end_date="", start_capital=0, end_capital=0,
                total_return=0, daily_avg_return=0, volatility=0, max_drawdown=0,
                win_rate=0, total_trades=0, trading_days=0
            )
        
        # 시작/종료 자본
        start_date = analysis_dates[0]
        end_date = analysis_dates[-1]
        
        start_portfolio = historical_data[start_date].get('portfolio_summary', {})
        end_portfolio = historical_data[end_date].get('portfolio_summary', {})
        
        start_capital = start_portfolio.get('total_value', 500_000)
        end_capital = end_portfolio.get('total_value', 500_000)
        
        # 총 수익률
        total_return = ((end_capital - start_capital) / start_capital * 100) if start_capital > 0 else 0
        
        # 일별 수익률 데이터 수집
        daily_returns = []
        max_value = start_capital
        max_drawdown = 0
        
        for date in analysis_dates:
            data = historical_data[date]
            portfolio = data.get('portfolio_summary', {})
            
            daily_return = portfolio.get('daily_return', 0)
            total_value = portfolio.get('total_value', 0)
            
            daily_returns.append(daily_return)
            
            # 최대 자본 및 드로우다운 계산
            if total_value > max_value:
                max_value = total_value
            
            current_drawdown = ((max_value - total_value) / max_value * 100) if max_value > 0 else 0
            max_drawdown = max(max_drawdown, current_drawdown)
        
        # 일평균 수익률
        daily_avg_return = sum(daily_returns) / len(daily_returns) if daily_returns else 0
        
        # 변동성 (표준편차)
        if len(daily_returns) > 1:
            variance = sum((r - daily_avg_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
            volatility = variance ** 0.5
        else:
            volatility = 0
        
        # 승률 및 총 거래 계산
        total_trades = 0
        win_trades = 0
        
        for date in analysis_dates:
            data = historical_data[date]
            sell_transactions = data.get('sell_transactions', [])
            
            for sell_tx in sell_transactions:
                total_trades += 1
                if sell_tx.get('profit_amount', 0) > 0:
                    win_trades += 1
        
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
        
        return PeriodAnalysis(
            period_name=period_name,
            start_date=start_date,
            end_date=end_date,
            start_capital=start_capital,
            end_capital=end_capital,
            total_return=total_return,
            daily_avg_return=daily_avg_return,
            volatility=volatility,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            total_trades=total_trades,
            trading_days=len(analysis_dates)
        )
    
    def print_historical_data_summary(self):
        """🔥 과거 거래 기록 요약"""
        historical_data = self.load_all_historical_data()
        
        if not historical_data:
            print("📝 저장된 과거 데이터가 없습니다.")
            return
        
        print(f"\n📊 과거 거래 기록 요약")
        print("="*70)
        
        sorted_dates = sorted(historical_data.keys())
        
        table_data = []
        for date in sorted_dates:
            data = historical_data[date]
            portfolio = data.get('portfolio_summary', {})
            daily_stats = data.get('daily_stats', {})
            
            # 날짜 포맷팅
            try:
                date_obj = datetime.strptime(date, '%Y%m%d')
                formatted_date = date_obj.strftime('%m/%d')
            except:
                formatted_date = date
            
            total_value = portfolio.get('total_value', 0)
            daily_pnl = portfolio.get('daily_pnl', 0)
            daily_return = portfolio.get('daily_return', 0)
            cumulative_return = portfolio.get('cumulative_return', 0)
            
            buy_count = daily_stats.get('total_buy_count', 0)
            sell_count = daily_stats.get('total_sell_count', 0)
            
            # 상태 이모지
            if daily_return > 2:
                status = "🚀"
            elif daily_return > 0:
                status = "🟢"
            elif daily_return == 0:
                status = "⚪"
            elif daily_return > -2:
                status = "🔴"
            else:
                status = "💥"
            
            table_data.append([
                formatted_date,
                f"{total_value:,}",
                f"{daily_pnl:+,}",
                f"{daily_return:+.2f}%",
                f"{cumulative_return:+.2f}%",
                f"{buy_count}/{sell_count}",
                status
            ])
        
        print(tabulate(
            table_data,
            headers=["날짜", "총자산", "일손익", "일수익률", "누적수익률", "매수/매도", "상태"],
            tablefmt="grid"
        ))
        
        # 전체 요약
        if sorted_dates:
            first_data = historical_data[sorted_dates[0]]
            last_data = historical_data[sorted_dates[-1]]
            
            first_value = first_data.get('portfolio_summary', {}).get('total_value', 500_000)
            last_value = last_data.get('portfolio_summary', {}).get('total_value', 500_000)
            
            total_return = ((last_value - first_value) / first_value * 100) if first_value > 0 else 0
            total_days = len(sorted_dates)
            
            print(f"\n📈 전체 요약:")
            print(f"   기간: {sorted_dates[0]} ~ {sorted_dates[-1]} ({total_days}일)")
            print(f"   시작: {first_value:,}원 → 종료: {last_value:,}원")
            print(f"   총 수익률: {total_return:+.2f}%")
            print(f"   일평균 수익률: {total_return/total_days:+.2f}%")
    
    def print_period_analysis(self):
        """🔥 기간별 성과 분석"""
        print(f"\n📊 기간별 성과 분석")
        print("="*80)
        
        periods = [
            ("전체", None),
            ("최근 30일", 30),
            ("최근 14일", 14),
            ("최근 7일", 7)
        ]
        
        analysis_results = []
        
        for period_name, days in periods:
            analysis = self.analyze_historical_performance(days)
            
            if analysis.trading_days > 0:
                analysis_results.append([
                    period_name,
                    f"{analysis.trading_days}일",
                    f"{analysis.start_capital:,}→{analysis.end_capital:,}",
                    f"{analysis.total_return:+.2f}%",
                    f"{analysis.daily_avg_return:+.2f}%",
                    f"{analysis.volatility:.2f}%",
                    f"{analysis.max_drawdown:.2f}%",
                    f"{analysis.win_rate:.1f}%",
                    f"{analysis.total_trades}회"
                ])
        
        if analysis_results:
            print(tabulate(
                analysis_results,
                headers=["기간", "일수", "자본변화", "총수익률", "일평균", "변동성", "최대낙폭", "승률", "거래수"],
                tablefmt="grid"
            ))
        else:
            print("📝 분석할 데이터가 충분하지 않습니다.")
        
        # 🔥 상세 분석 (전체 기간)
        full_analysis = self.analyze_historical_performance()
        if full_analysis.trading_days > 0:
            print(f"\n🎯 전체 기간 상세 분석:")
            print(f"   📅 기간: {full_analysis.start_date} ~ {full_analysis.end_date}")
            print(f"   💰 자본: {full_analysis.start_capital:,}원 → {full_analysis.end_capital:,}원")
            print(f"   📈 총 수익률: {full_analysis.total_return:+.2f}%")
            print(f"   📊 일평균 수익률: {full_analysis.daily_avg_return:+.2f}%")
            print(f"   📉 변동성: {full_analysis.volatility:.2f}%")
            print(f"   🕳️  최대 낙폭: {full_analysis.max_drawdown:.2f}%")
            print(f"   🎯 승률: {full_analysis.win_rate:.1f}% ({full_analysis.total_trades}거래)")
            
            # 🔥 연간 수익률 예상
            if full_analysis.daily_avg_return != 0 and full_analysis.trading_days > 0:
                # 기하평균 기반 연간 수익률
                daily_growth = 1 + (full_analysis.total_return / 100) ** (1/full_analysis.trading_days)
                annual_return = ((daily_growth ** 250) - 1) * 100
                print(f"   🚀 연간 수익률 예상: {annual_return:+.1f}%")
                
                # 샤프 비율 (간단 버전)
                if full_analysis.volatility > 0:
                    sharpe_ratio = full_analysis.daily_avg_return / full_analysis.volatility
                    print(f"   ⚖️  샤프 비율: {sharpe_ratio:.2f}")
    
    def analyze_trade_patterns(self):
        """🔥 거래 패턴 분석"""
        historical_data = self.load_all_historical_data()
        
        if not historical_data:
            print("📝 분석할 거래 데이터가 없습니다.")
            return
        
        print(f"\n🔍 거래 패턴 분석")
        print("="*70)
        
        # 모든 매도 거래 수집
        all_sells = []
        condition_stats = {}
        time_stats = {}
        
        for date, data in historical_data.items():
            sells = data.get('sell_transactions', [])
            
            for sell in sells:
                all_sells.append(sell)
                
                # 조건검색식별 통계
                condition_seq = sell.get('condition_seq', 0)
                if condition_seq not in condition_stats:
                    condition_stats[condition_seq] = {'count': 0, 'total_profit': 0, 'wins': 0}
                
                condition_stats[condition_seq]['count'] += 1
                condition_stats[condition_seq]['total_profit'] += sell.get('profit_amount', 0)
                if sell.get('profit_amount', 0) > 0:
                    condition_stats[condition_seq]['wins'] += 1
                
                # 시간대별 통계
                timestamp = sell.get('timestamp', '')
                if timestamp:
                    try:
                        hour = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').hour
                        if hour not in time_stats:
                            time_stats[hour] = {'count': 0, 'total_profit': 0, 'wins': 0}
                        
                        time_stats[hour]['count'] += 1
                        time_stats[hour]['total_profit'] += sell.get('profit_amount', 0)
                        if sell.get('profit_amount', 0) > 0:
                            time_stats[hour]['wins'] += 1
                    except:
                        pass
        
        if not all_sells:
            print("📝 매도 거래가 없습니다.")
            return
        
        # 수익률 분포
        profit_rates = [sell.get('profit_rate', 0) for sell in all_sells]
        
        wins = [p for p in profit_rates if p > 0]
        losses = [p for p in profit_rates if p < 0]
        
        print(f"📊 거래 수익률 분포:")
        print(f"   총 거래: {len(all_sells)}회")
        print(f"   승리: {len(wins)}회 (평균: {sum(wins)/len(wins):+.2f}%)" if wins else "   승리: 0회")
        print(f"   손실: {len(losses)}회 (평균: {sum(losses)/len(losses):+.2f}%)" if losses else "   손실: 0회")
        print(f"   무승부: {len(profit_rates) - len(wins) - len(losses)}회")
        
        # 조건검색식별 성과
        if condition_stats:
            print(f"\n🔍 조건검색식별 성과:")
            for condition_seq in sorted(condition_stats.keys()):
                stats = condition_stats[condition_seq]
                win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
                avg_profit = stats['total_profit'] / stats['count'] if stats['count'] > 0 else 0
                
                print(f"   조건 {condition_seq}: {stats['count']}회, 승률 {win_rate:.1f}%, 평균손익 {avg_profit:+,.0f}원")
        
        # 시간대별 성과
        if time_stats:
            print(f"\n🕐 시간대별 성과:")
            for hour in sorted(time_stats.keys()):
                stats = time_stats[hour]
                win_rate = (stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0
                avg_profit = stats['total_profit'] / stats['count'] if stats['count'] > 0 else 0
                
                print(f"   {hour:2d}시: {stats['count']}회, 승률 {win_rate:.1f}%, 평균손익 {avg_profit:+,.0f}원")
    
    # ================================================================================
    # 기존 기능들 (간소화)
    # ================================================================================
    
    def can_afford(self, amount: int) -> bool:
        """투자 가능 여부 확인"""
        return self.available_cash >= amount
    
    def get_adjusted_investment_amount(self, target_amount: int) -> int:
        """🔥 자금 상황에 따른 투자금액 조정"""
        if self.available_cash >= target_amount:
            return target_amount
        
        # 자금이 부족하면 가용 자금의 90%로 조정
        adjusted = int(self.available_cash * 0.9)
        
        # 최소 투자 금액 (1만원) 확인
        if adjusted < 10_000:
            return 0
        
        return adjusted
    
    def execute_virtual_buy(self, code: str, name: str, price: int, 
                           target_amount: int, condition_seq: int = 0) -> Optional[VirtualTransaction]:
        """🔥 가상 매수 실행 (자금 조정 포함)"""
        
        # 투자 금액 조정
        investment_amount = self.get_adjusted_investment_amount(target_amount)
        
        if investment_amount == 0:
            print(f"[매수 실패] 자금 부족: 가용 {self.available_cash:,}원 < 최소 10,000원")
            return None
        
        # 수량 계산
        quantity = investment_amount // price
        if quantity <= 0:
            print(f"[매수 실패] 수량 부족: {investment_amount:,}원 ÷ {price:,}원 = {quantity}주")
            return None
        
        # 실제 투자 금액
        actual_amount = quantity * price
        
        # 거래 실행
        transaction = VirtualTransaction(
            transaction_id=f"BUY_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{code}",
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            type="buy",
            code=code,
            name=name,
            quantity=quantity,
            price=price,
            amount=actual_amount,
            condition_seq=condition_seq
        )
        
        # 자금 업데이트
        self.available_cash -= actual_amount
        self.total_invested += actual_amount
        self.buy_transactions.append(transaction)
        
        # 통계 속성 업데이트
        current_total = self.available_cash + self.total_invested
        self.cumulative_return = self.calculate_cumulative_return()
        self.total_return = self.cumulative_return
        self.max_capital = max(self.max_capital, current_total)
        self.min_capital = min(self.min_capital, current_total)
        
        # 🔥 자금 조정 안내
        if investment_amount != target_amount:
            print(f"[자금 조정] 목표 {target_amount:,}원 → 실제 {actual_amount:,}원")
        
        self.save_daily_data()
        return transaction
    
    def execute_virtual_sell(self, buy_transaction: VirtualTransaction, 
                           current_price: int, reason: str = "") -> Optional[VirtualTransaction]:
        """🔥 가상 매도 실행 (수익률 기록 강화)"""
        
        # 매도 금액 계산
        sell_amount = buy_transaction.quantity * current_price
        profit_amount = sell_amount - buy_transaction.amount
        profit_rate = (profit_amount / buy_transaction.amount * 100) if buy_transaction.amount > 0 else 0
        
        # 거래 실행
        transaction = VirtualTransaction(
            transaction_id=f"SELL_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{buy_transaction.code}",
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            type="sell",
            code=buy_transaction.code,
            name=buy_transaction.name,
            quantity=buy_transaction.quantity,
            price=current_price,
            amount=sell_amount,
            buy_transaction_id=buy_transaction.transaction_id,
            profit_amount=profit_amount,
            profit_rate=profit_rate,
            reason=reason
        )
        
        # 자금 업데이트
        self.available_cash += sell_amount
        self.total_invested -= buy_transaction.amount
        self.daily_pnl += profit_amount
        self.sell_transactions.append(transaction)
        
        # 🔥 누적 통계 업데이트
        current_total = self.available_cash + self.total_invested
        self.max_capital = max(self.max_capital, current_total)
        self.min_capital = min(self.min_capital, current_total)
        
        # 통계 속성 업데이트
        self.cumulative_return = self.calculate_cumulative_return()
        self.total_return = self.cumulative_return
        self.win_rate = self.calculate_win_rate()
        
        # 최대 손실률 계산
        if self.max_capital > 0:
            self.max_drawdown = ((self.max_capital - current_total) / self.max_capital * 100)
        
        # 🔥 실시간 수익률 출력
        print(f"[매도 완료] 누적 수익률: {self.cumulative_return:+.2f}% (총액: {current_total:,}원)")
        
        self.save_daily_data()
        return transaction
    
    def calculate_detailed_returns(self) -> Dict[str, Any]:
        """🔥 상세 누적 수익률 계산"""
        current_total = self.available_cash + self.total_invested
        
        # 기본 수익률들
        cumulative_pnl = current_total - self.original_capital
        cumulative_return = (cumulative_pnl / self.original_capital * 100) if self.original_capital > 0 else 0
        daily_return = (self.daily_pnl / self.initial_capital * 100) if self.initial_capital > 0 else 0
        
        # 🔥 일평균 수익률 (산술/기하평균)
        if self.cumulative_days > 1:
            arithmetic_avg = cumulative_return / self.cumulative_days
            
            # 기하평균 계산 (복리 수익률)
            if current_total > 0 and self.original_capital > 0:
                geometric_avg = ((current_total / self.original_capital) ** (1/self.cumulative_days) - 1) * 100
            else:
                geometric_avg = 0
        else:
            arithmetic_avg = daily_return
            geometric_avg = daily_return
        
        # 🔥 연간 수익률 예상 (250거래일 기준)
        if geometric_avg != 0:
            annual_return = ((1 + geometric_avg/100) ** 250 - 1) * 100
        else:
            annual_return = 0
        
        # 🔥 최대 손실률 (Maximum Drawdown)
        max_drawdown = 0
        if self.max_capital > 0:
            max_drawdown = ((self.max_capital - current_total) / self.max_capital * 100)
        
        # 🔥 승률 계산
        win_trades = len([tx for tx in self.sell_transactions if tx.profit_amount > 0])
        total_trades = len(self.sell_transactions)
        win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0
        
        # 🔥 샤프 비율 (간단 버전)
        if len(self.daily_returns_history) > 1:
            returns = [dr.daily_return for dr in self.daily_returns_history[-30:]]  # 최근 30일
            avg_return = sum(returns) / len(returns) if returns else 0
            
            if len(returns) > 1:
                variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
                std_dev = variance ** 0.5
                sharpe_ratio = (avg_return / std_dev) if std_dev > 0 else 0
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        return {
            'current_total': current_total,
            'cumulative_pnl': cumulative_pnl,
            'cumulative_return': cumulative_return,
            'daily_return': daily_return,
            'arithmetic_avg_return': arithmetic_avg,
            'geometric_avg_return': geometric_avg,
            'annual_return_forecast': annual_return,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': total_trades,
            'win_trades': win_trades
        }
    
    def print_detailed_returns(self):
        """🔥 상세 누적 수익률 출력"""
        returns = self.calculate_detailed_returns()
        
        print(f"\n{'='*70}")
        print(f"📈 누적 수익률 상세 분석 ({self.cumulative_days}일간)")
        print(f"{'='*70}")
        
        # 기본 정보
        print(f"💰 최초 원금: {self.original_capital:,}원")
        print(f"💎 현재 총액: {returns['current_total']:,}원")
        print(f"📊 누적 손익: {returns['cumulative_pnl']:+,}원")
        print(f"🎯 누적 수익률: {returns['cumulative_return']:+.2f}%")
        print(f"")
        
        # 수익률 분석
        print(f"📅 오늘 수익률: {returns['daily_return']:+.2f}%")
        print(f"📊 일평균 수익률: {returns['arithmetic_avg_return']:+.2f}% (산술평균)")
        print(f"🔄 복리 평균 수익률: {returns['geometric_avg_return']:+.2f}% (기하평균)")
        print(f"🚀 연간 수익률 예상: {returns['annual_return_forecast']:+.1f}%")
        print(f"")
        
        # 리스크 분석
        print(f"🏔️  최대 자금: {self.max_capital:,}원")
        print(f"🕳️  최대 손실률: {returns['max_drawdown']:.2f}%")
        print(f"⚖️  샤프 비율: {returns['sharpe_ratio']:.2f}")
        print(f"")
        
        # 거래 성과
        print(f"🎲 총 거래: {returns['total_trades']}회")
        print(f"🟢 승리 거래: {returns['win_trades']}회")
        print(f"🎯 승률: {returns['win_rate']:.1f}%")
        
        # 🔥 복리 효과 시뮬레이션
        if returns['geometric_avg_return'] > 0:
            print(f"\n🔥 복리 효과 시뮬레이션:")
            months = [1, 3, 6, 12]
            for month in months:
                days = month * 20  # 월 20거래일 가정
                if returns['geometric_avg_return'] != 0:
                    future_value = self.original_capital * ((1 + returns['geometric_avg_return']/100) ** days)
                    growth = ((future_value - self.original_capital) / self.original_capital * 100)
                    print(f"  {month:2d}개월 후 예상: {future_value:,.0f}원 ({growth:+.1f}%)")
        
        print(f"{'='*70}")
    
    def print_recent_performance(self, days: int = 7):
        """🔥 최근 성과 그래프"""
        if len(self.daily_returns_history) < 2:
            print("[INFO] 충분한 데이터가 없습니다. (최소 2일 필요)")
            return
        
        recent_data = self.daily_returns_history[-days:]
        
        print(f"\n📊 최근 {len(recent_data)}일 성과 차트")
        print("="*60)
        
        table_data = []
        for dr in recent_data:
            # 간단한 차트 바
            bar_length = int(abs(dr.daily_return) * 2)  # 2배 확대
            bar_char = "🟢" if dr.daily_return > 0 else "🔴" if dr.daily_return < 0 else "⚪"
            bar = bar_char * min(bar_length, 10)  # 최대 10개
            
            table_data.append([
                dr.date[-4:],  # MMDD
                f"{dr.daily_return:+.2f}%",
                f"{dr.cumulative_return:+.2f}%",
                f"{dr.end_capital:,}",
                bar
            ])
        
        print(tabulate(
            table_data,
            headers=["날짜", "일간", "누적", "총액", "차트"],
            tablefmt="grid"
        ))
    
    def finalize_day(self):
        """🔥 하루 마감 시 일별 수익률 기록"""
        current_total = self.available_cash + self.total_invested
        daily_return_rate = (self.daily_pnl / self.initial_capital * 100) if self.initial_capital > 0 else 0
        cumulative_return_rate = ((current_total - self.original_capital) / self.original_capital * 100) if self.original_capital > 0 else 0
        
        # 오늘 데이터 생성
        today_return = DailyReturn(
            date=datetime.now().strftime('%Y%m%d'),
            start_capital=self.initial_capital,
            end_capital=current_total,
            daily_pnl=self.daily_pnl,
            daily_return=daily_return_rate,
            cumulative_return=cumulative_return_rate,
            trades_count=len(self.sell_transactions)
        )
        
        # 기존 기록에서 오늘 데이터 제거 후 추가 (중복 방지)
        self.daily_returns_history = [dr for dr in self.daily_returns_history 
                                     if dr.date != today_return.date]
        self.daily_returns_history.append(today_return)
        
        # 히스토리 저장
        self.save_daily_returns_history()
        
        print(f"[일별 기록] {today_return.date} 수익률: {daily_return_rate:+.2f}% 기록완료")
    
    def get_portfolio_value(self) -> Dict[str, Any]:
        """포트폴리오 가치 계산"""
        total_value = self.available_cash + self.total_invested
        daily_return = (self.daily_pnl / self.initial_capital * 100) if self.initial_capital > 0 else 0
        
        # 🔥 누적 수익률 계산
        cumulative_return = ((total_value - self.original_capital) / self.original_capital * 100) if self.original_capital > 0 else 0
        
        # 🔥 드로우다운 계산
        drawdown = ((self.max_capital - total_value) / self.max_capital * 100) if self.max_capital > 0 else 0
        
        return {
            'available_cash': self.available_cash,
            'total_invested': self.total_invested,
            'total_value': total_value,
            'daily_pnl': self.daily_pnl,
            'daily_return': daily_return,
            'cumulative_return': cumulative_return,  # 🔥 누적 수익률
            'cumulative_days': self.cumulative_days,  # 🔥 누적 일수
            'max_capital': self.max_capital,  # 🔥 최고 자금
            'min_capital': self.min_capital,  # 🔥 최저 자금
            'drawdown': drawdown,  # 🔥 드로우다운
            'original_capital': self.original_capital  # 🔥 최초 원금
        }
    
    def print_money_status(self):
        """🔥 누적 자금 현황 출력 (상세 수익률 포함)"""
        self.print_detailed_returns()  # 상세 수익률 정보 출력
    
    def save_daily_data(self):
        """일별 데이터 저장"""
        today_str = datetime.now().strftime('%Y%m%d')
        filename = f"virtual_transactions_{today_str}.json"
        filepath = os.path.join(self.save_dir, filename)
        
        portfolio = self.get_portfolio_value()
        
        data = {
            'date': today_str,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'portfolio_summary': portfolio,
            'buy_transactions': [asdict(tx) for tx in self.buy_transactions],
            'sell_transactions': [asdict(tx) for tx in self.sell_transactions],
            'daily_stats': {
                'total_buy_count': len(self.buy_transactions),
                'total_sell_count': len(self.sell_transactions),
                'active_positions': len(self.buy_transactions) - len(self.sell_transactions)
            }
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] 데이터 저장 실패: {e}")
    
    def get_trading_statistics(self) -> Dict[str, Any]:
        """거래 통계 계산"""
        total_sell_trades = len(self.sell_transactions)
        
        if total_sell_trades == 0:
            return {
                'total_sell_trades': 0,
                'win_trades': 0,
                'loss_trades': 0,
                'win_rate': 0,
                'avg_profit_rate': 0,
                'avg_loss_rate': 0,
                'total_profit': 0,
                'total_loss': 0
            }
        
        win_trades = [tx for tx in self.sell_transactions if tx.profit_amount > 0]
        loss_trades = [tx for tx in self.sell_transactions if tx.profit_amount < 0]
        
        win_rate = len(win_trades) / total_sell_trades * 100
        
        avg_profit_rate = sum(tx.profit_rate for tx in win_trades) / len(win_trades) if win_trades else 0
        avg_loss_rate = sum(tx.profit_rate for tx in loss_trades) / len(loss_trades) if loss_trades else 0
        
        total_profit = sum(tx.profit_amount for tx in win_trades)
        total_loss = sum(tx.profit_amount for tx in loss_trades)
        
        return {
            'total_sell_trades': total_sell_trades,
            'win_trades': len(win_trades),
            'loss_trades': len(loss_trades),
            'win_rate': win_rate,
            'avg_profit_rate': avg_profit_rate,
            'avg_loss_rate': avg_loss_rate,
            'total_profit': total_profit,
            'total_loss': total_loss
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """🔥 완전한 통계 정보 반환"""
        # 기본 포트폴리오 정보
        portfolio = self.get_portfolio_value()
        
        # 거래 통계
        trading_stats = self.get_trading_statistics()
        
        # 상세 수익률 정보
        detailed_returns = self.calculate_detailed_returns()
        
        # 통합 통계 반환
        return {
            # 기본 정보
            'available_cash': self.available_cash,
            'total_invested': self.total_invested,
            'total_value': portfolio['total_value'],
            'daily_pnl': self.daily_pnl,
            
            # 수익률 정보
            'daily_return': portfolio['daily_return'],
            'cumulative_return': portfolio['cumulative_return'],
            'total_return': detailed_returns['cumulative_return'],
            'max_drawdown': detailed_returns['max_drawdown'],
            'win_rate': trading_stats['win_rate'],
            
            # 거래 통계
            'total_trades': trading_stats['total_sell_trades'],
            'win_trades': trading_stats['win_trades'],
            'loss_trades': trading_stats['loss_trades'],
            'avg_profit_rate': trading_stats['avg_profit_rate'],
            'avg_loss_rate': trading_stats['avg_loss_rate'],
            
            # 기간 정보
            'cumulative_days': self.cumulative_days,
            'original_capital': self.original_capital,
            'max_capital': self.max_capital,
            'min_capital': self.min_capital
        }
    
    def calculate_positions_value(self) -> int:
        """🔥 정확한 포지션 가치 계산"""
        # 현재 보유 포지션 확인 (매수했지만 매도하지 않은 것들)
        active_buy_transactions = []
        
        for buy_tx in self.buy_transactions:
            # 이 매수 건에 대응하는 매도 건이 있는지 확인
            is_sold = any(sell_tx.buy_transaction_id == buy_tx.transaction_id 
                         for sell_tx in self.sell_transactions)
            if not is_sold:
                active_buy_transactions.append(buy_tx)
        
        # 보유 포지션의 총 매수 금액 반환 (현재가 정보가 없으므로)
        total_position_value = sum(tx.amount for tx in active_buy_transactions)
        return total_position_value
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """🔥 포트폴리오 요약 - 정확한 수치"""
        current_total = self.available_cash + self.total_invested
        positions_value = self.calculate_positions_value()
        
        # 활성 포지션 수 계산
        active_positions = len([tx for tx in self.buy_transactions 
                               if not any(sell.buy_transaction_id == tx.transaction_id 
                                         for sell in self.sell_transactions)])
        
        return {
            'available_cash': self.available_cash,
            'total_invested': self.total_invested,
            'positions_value': positions_value,
            'total_value': current_total,
            'active_positions': active_positions,
            'daily_pnl': self.daily_pnl,
            'daily_return': (self.daily_pnl / self.initial_capital * 100) if self.initial_capital > 0 else 0,
            'cumulative_return': ((current_total - self.original_capital) / self.original_capital * 100) if self.original_capital > 0 else 0,
            'cumulative_days': self.cumulative_days,
            'max_capital': self.max_capital,
            'min_capital': self.min_capital,
            'original_capital': self.original_capital
        }
    
    def calculate_win_rate(self) -> float:
        """🔥 정확한 승률 계산"""
        total_trades = len(self.sell_transactions)
        if total_trades == 0:
            return 0.0
            
        win_trades = len([tx for tx in self.sell_transactions if tx.profit_amount > 0])
        return (win_trades / total_trades) * 100
    
    def calculate_cumulative_return(self) -> float:
        """🔥 누적 수익률 정확 계산"""
        current_total = self.available_cash + self.total_invested
        if self.original_capital <= 0:
            return 0.0
        return ((current_total - self.original_capital) / self.original_capital) * 100
    
    def print_transaction_history(self, limit: int = 10):
        """거래 내역 출력"""
        all_transactions = []
        
        # 매수/매도 거래 합쳐서 시간순 정렬
        for tx in self.buy_transactions:
            all_transactions.append(('매수', tx))
        for tx in self.sell_transactions:
            all_transactions.append(('매도', tx))
        
        # 시간순 정렬
        all_transactions.sort(key=lambda x: x[1].timestamp, reverse=True)
        
        print(f"\n📊 최근 거래 내역 (최대 {limit}건)")
        print("="*80)
        
        count = 0
        for i, (tx_type, tx) in enumerate(all_transactions, 1):
            if count >= limit:
                break
                
            time_str = tx.timestamp.split(' ')[1]  # HH:MM:SS 부분만
            
            if tx_type == '매수':
                print(f"{i:2d}. [{time_str}] 💰 매수 | {tx.name}({tx.code}) "
                      f"{tx.quantity}주 @{tx.price:,}원 = {tx.amount:,}원")
            else:
                profit_emoji = "🟢" if tx.profit_amount > 0 else "🔴" if tx.profit_amount < 0 else "⚪"
                print(f"{i:2d}. [{time_str}] 💸 매도 | {tx.name}({tx.code}) "
                      f"{tx.quantity}주 @{tx.price:,}원 = {tx.amount:,}원 "
                      f"({tx.profit_rate:+.2f}%) {profit_emoji}")
            
            count += 1
        
        print("="*80)
    
    # ================================================================================
    # 🔥 백테스팅 전용 대화형 메뉴 시스템
    # ================================================================================
    
    def reset_virtual_money(self):
        """🔥 가상 자금 초기화"""
        print("\n⚠️  가상 자금 초기화")
        print("="*50)
        print("현재 모든 거래 내역과 누적 자금이 삭제됩니다.")
        print("이 작업은 되돌릴 수 없습니다!")
        
        confirm = input("\n정말로 초기화하시겠습니까? (YES 입력): ").strip()
        
        if confirm == "YES":
            # 모든 JSON 파일 삭제
            pattern = os.path.join(self.save_dir, "virtual_transactions_*.json")
            files = glob.glob(pattern)
            
            try:
                for file_path in files:
                    os.remove(file_path)
                    print(f"✅ {os.path.basename(file_path)} 삭제 완료")
                
                # 히스토리 파일 삭제
                history_file = os.path.join(self.save_dir, "daily_returns_history.json")
                if os.path.exists(history_file):
                    os.remove(history_file)
                    print(f"✅ daily_returns_history.json 삭제 완료")
                
                # 메모리 초기화
                self.__init__(500_000, self.save_dir)
                
                print("✅ 모든 가상 거래 데이터가 초기화되었습니다!")
                
            except Exception as e:
                print(f"❌ 초기화 실패: {e}")
        else:
            print("❌ 초기화가 취소되었습니다.")
    
    def show_menu(self):
        """🔥 백테스팅 전용 대화형 메뉴 표시"""
        while True:
            print(f"\n{'='*70}")
            print(f"📊 가상 자금 관리 시스템 - 백테스팅 분석 (V2.3)")
            print(f"{'='*70}")
            
            # 간단한 현재 상태
            portfolio = self.get_portfolio_value()
            print(f"💎 현재 총액: {portfolio['total_value']:,}원")
            print(f"🎯 누적 수익률: {portfolio['cumulative_return']:+.2f}%")
            print(f"📅 거래일: {self.cumulative_days}일차")
            
            print(f"\n📋 메뉴:")
            print(f"1. 💰 포트폴리오 현황 (상세)")
            print(f"2. 📊 과거 거래 기록")
            print(f"3. 📈 전체 통계 요약")
            print(f"4. 🔍 거래 패턴 분석")
            print(f"5. 📈 최근 성과 차트")
            print(f"6. 📝 하루 마감 처리")
            print(f"7. ⚠️  모든 데이터 초기화")
            print(f"0. 🚪 종료")
            
            try:
                choice = input(f"\n선택하세요 (0-7): ").strip()
                
                if choice == '0':
                    print("👋 가상 자금 관리 시스템을 종료합니다.")
                    break
                elif choice == '1':
                    self.print_money_status()
                elif choice == '2':
                    self.print_historical_data_summary()
                elif choice == '3':
                    self.print_period_analysis()
                elif choice == '4':
                    self.analyze_trade_patterns()
                elif choice == '5':
                    self.print_recent_performance()
                elif choice == '6':
                    self.finalize_day()
                    print("✅ 하루 마감 처리 완료!")
                elif choice == '7':
                    self.reset_virtual_money()
                else:
                    print("❌ 올바른 번호를 입력해주세요. (0-7)")
                    
            except KeyboardInterrupt:
                print(f"\n\n👋 사용자가 종료를 요청했습니다.")
                break
            except Exception as e:
                print(f"❌ 오류 발생: {e}")

# ================================================================================
# 메인 실행부 (백테스팅 분석 메뉴)
# ================================================================================

if __name__ == "__main__":
    def main():
        print("🔥 V2.3 누적 수익률 강화 + 백테스팅 분석 시스템")
        print("="*70)
        
        try:
            # VirtualMoneyManager 생성
            manager = VirtualMoneyManager()
            
            # 백테스팅 분석 메뉴 실행
            manager.show_menu()
            
        except Exception as e:
            print(f"❌ 시스템 오류: {e}")
            import traceback
            traceback.print_exc()
    
    main()