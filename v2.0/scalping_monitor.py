import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from tabulate import tabulate
import os
import json

from scalping_portfolio import ScalpingPortfolio, ScalpingPosition
from virtual_money_manager import VirtualMoneyManager

class ScalpingMonitor:
    """🔥 V2.0 단타 매매 실시간 모니터링 시스템"""
    
    def __init__(self, portfolio: ScalpingPortfolio, money_manager: VirtualMoneyManager, 
                 save_dir: str = None):
        self.portfolio = portfolio
        self.money_manager = money_manager
        self.save_dir = save_dir
        
        # 모니터링 설정
        self.profit_target = 5.0
        self.stop_loss = -5.0
        self.warning_profit = 4.5  # 익절 임박 경고
        self.warning_loss = -4.5   # 손절 임박 경고
        
        # 성능 추적
        self.loop_count = 0
        self.last_update_time = datetime.now()
        self.monitoring_start_time = datetime.now()
        
    def update_loop_count(self):
        """루프 카운트 업데이트"""
        self.loop_count += 1
        self.last_update_time = datetime.now()
    
    def print_system_header(self, mode: str = "실제 매매"):
        """시스템 시작 헤더"""
        now = datetime.now()
        
        print("="*100)
        print(f"🔥 V2.0 단타 매매 모니터링 시스템 [{mode}]")
        print("="*100)
        print(f"🕐 시작 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"💰 시작 자금: {self.money_manager.initial_capital:,}원 (가상)")
        print(f"📊 최대 포지션: {self.portfolio.max_positions}개")
        print(f"💵 종목당 한도: {self.portfolio.max_position_value:,}원")
        print(f"🎯 익절/손절: +{self.profit_target}% / {self.stop_loss}%")
        print("="*100)
    
    def print_loop_header(self, loop_count: int):
        """루프 시작 헤더"""
        now = datetime.now()
        portfolio_summary = self.portfolio.get_portfolio_summary()
        money_status = self.money_manager.get_portfolio_value()
        
        print(f"\n{'='*80}")
        print(f"🔄 [{loop_count}번째 루프] {now.strftime('%H:%M:%S')} - 단타 매매 실행")
        print(f"💰 자금현황: {money_status['available_cash']:,}원 | "
              f"포지션: {portfolio_summary['total_positions']}/{self.portfolio.max_positions}개 | "
              f"손익: {money_status['daily_pnl']:+,}원 ({money_status['daily_return']:+.2f}%)")
        print(f"{'='*80}")
    
    def check_exit_alerts(self, current_prices: Dict[str, int]) -> List[Dict]:
        """청산 알림 체크"""
        alerts = []
        
        for position in self.portfolio.positions:
            current_price = current_prices.get(position.code, 0)
            if current_price <= 0:
                continue
            
            _, profit_rate = position.get_profit_loss(current_price)
            
            # 알림 조건 체크
            if profit_rate >= self.warning_profit:
                alerts.append({
                    'type': 'profit_warning',
                    'position': position,
                    'current_price': current_price,
                    'profit_rate': profit_rate,
                    'message': f"🟢 익절 임박: {position.name} ({profit_rate:+.2f}%)"
                })
            elif profit_rate <= self.warning_loss:
                alerts.append({
                    'type': 'loss_warning',
                    'position': position,
                    'current_price': current_price,
                    'profit_rate': profit_rate,
                    'message': f"🔴 손절 임박: {position.name} ({profit_rate:+.2f}%)"
                })
        
        return alerts
    
    def print_detailed_positions_table(self, current_prices: Dict[str, int]):
        """상세 포지션 현황 테이블"""
        
        if not self.portfolio.positions:
            print("[INFO] 📝 현재 보유 포지션이 없습니다.")
            return
        
        print(f"\n📊 [실시간 포지션 상세 현황] {len(self.portfolio.positions)}개")
        
        table_data = []
        total_cost = 0
        total_current_value = 0
        total_profit = 0
        
        alerts = self.check_exit_alerts(current_prices)
        
        for i, pos in enumerate(self.portfolio.positions, 1):
            current_price = current_prices.get(pos.code, 0)
            
            if current_price > 0:
                current_value = pos.get_current_value(current_price)
                profit_amount, profit_rate = pos.get_profit_loss(current_price)
                
                total_cost += pos.cost
                total_current_value += current_value
                total_profit += profit_amount
                
                # 보유 시간 계산
                hold_duration = pos.get_hold_duration()
                hold_minutes = int(hold_duration.total_seconds() / 60)
                hold_time_str = f"{hold_minutes}분" if hold_minutes < 60 else f"{hold_minutes//60}시간{hold_minutes%60}분"
                
                # 상태 표시
                if profit_rate >= self.warning_profit:
                    status = "🟢 익절임박"
                elif profit_rate >= 2.0:
                    status = "🟢 수익확대"
                elif profit_rate > 0:
                    status = "🟢 수익"
                elif profit_rate >= -2.0:
                    status = "⚪ 소폭손실"
                elif profit_rate >= self.warning_loss:
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
                    status
                ])
            else:
                table_data.append([
                    i,
                    pos.name[:8] + "..." if len(pos.name) > 8 else pos.name,
                    f"{pos.buy_price:,}",
                    "조회실패",
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
                    "매수시거래대금", "상태"
                ],
                tablefmt="grid"
            ))
            
            # 포트폴리오 종합 요약
            if total_cost > 0:
                total_profit_rate = (total_profit / total_cost * 100)
                print(f"\n💼 포트폴리오 종합: 투자금 {total_cost:,}원 → "
                      f"평가금액 {total_current_value:,}원 "
                      f"({total_profit:+,}원, {total_profit_rate:+.2f}%)")
            
            # 알림 표시
            if alerts:
                print(f"\n⚠️ 주요 알림:")
                for alert in alerts:
                    print(f"   {alert['message']}")
    
    def print_trading_summary(self):
        """거래 요약 출력"""
        money_status = self.money_manager.get_portfolio_value()
        trading_stats = self.money_manager.get_trading_statistics()
        portfolio_summary = self.portfolio.get_portfolio_summary()
        
        print(f"\n{'='*60}")
        print(f"📊 루프 완료 요약")
        print(f"{'='*60}")
        print(f"🔄 매수 실행: {trading_stats['total_buy_trades']}건")
        print(f"💰 매도 실행: {trading_stats['total_sell_trades']}건")
        
        if trading_stats['total_sell_trades'] > 0:
            print(f"🟢 수익 거래: {trading_stats['profit_trades']}건")
            print(f"🔴 손실 거래: {trading_stats['loss_trades']}건")
            print(f"🎯 승률: {trading_stats['win_rate']:.1f}%")
            
            if trading_stats['profit_trades'] > 0:
                print(f"📈 평균 수익률: {trading_stats['avg_profit_rate']:+.2f}%")
        
        print(f"💵 현재 자금: {money_status['available_cash']:,}원")
        print(f"📊 일일 손익: {money_status['daily_pnl']:+,}원 ({money_status['daily_return']:+.2f}%)")
        print(f"🏠 포트폴리오: {portfolio_summary['total_positions']}/{self.portfolio.max_positions}개 활용")
    
    def print_comprehensive_status(self, current_prices: Dict[str, int] = None):
        """종합 현황 출력"""
        money_status = self.money_manager.get_portfolio_value()
        portfolio_summary = self.portfolio.get_portfolio_summary()
        trading_stats = self.money_manager.get_trading_statistics()
        
        print(f"\n{'='*80}")
        print(f"🎯 단타 매매 종합 현황")
        print(f"{'='*80}")
        
        # 자금 현황
        print(f"💰 자금 현황:")
        print(f"   🏦 시작 자금: {money_status['initial_capital']:,}원")
        print(f"   💵 사용 가능: {money_status['available_cash']:,}원")
        print(f"   📊 투자 중: {portfolio_summary['total_invested']:,}원")
        print(f"   💰 총 자산: {money_status['total_value']:,}원")
        print(f"   📈 일일 손익: {money_status['daily_pnl']:+,}원 ({money_status['daily_return']:+.2f}%)")
        
        # 포트폴리오 현황
        print(f"\n📊 포트폴리오:")
        print(f"   🏠 보유 포지션: {portfolio_summary['total_positions']}/{self.portfolio.max_positions}개")
        print(f"   📈 활용률: {portfolio_summary['utilization_rate']:.1f}%")
        print(f"   🔄 거래 종목: {portfolio_summary['traded_today_count']}개")
        
        # 거래 통계
        if trading_stats['total_sell_trades'] > 0:
            print(f"\n📊 거래 성과:")
            print(f"   🔄 총 거래: {trading_stats['total_buy_trades']}매수 / {trading_stats['total_sell_trades']}매도")
            print(f"   🟢 수익 거래: {trading_stats['profit_trades']}건 (평균 {trading_stats['avg_profit_rate']:+.2f}%)")
            print(f"   🔴 손실 거래: {trading_stats['loss_trades']}건 (평균 {trading_stats['avg_loss_rate']:+.2f}%)")
            print(f"   🎯 승률: {trading_stats['win_rate']:.1f}%")
        
        # 시스템 성능
        runtime = datetime.now() - self.monitoring_start_time
        print(f"\n⚡ 시스템 성능:")
        print(f"   🔄 실행 루프: {self.loop_count}회")
        print(f"   ⏱️ 총 운영: {str(runtime).split('.')[0]}")
        print(f"   🔄 마지막 업데이트: {self.last_update_time.strftime('%H:%M:%S')}")
        
        print(f"{'='*80}")
        
        # 포지션 상세 (현재가 있을 때만)
        if current_prices and self.portfolio.positions:
            self.print_detailed_positions_table(current_prices)
    
    def save_monitoring_report(self):
        """모니터링 보고서 저장"""
        if not self.save_dir:
            return
        
        today = datetime.now().strftime('%Y%m%d')
        report_file = os.path.join(self.save_dir, f"monitoring_report_{today}.json")
        
        try:
            os.makedirs(self.save_dir, exist_ok=True)
            
            money_status = self.money_manager.get_portfolio_value()
            portfolio_summary = self.portfolio.get_portfolio_summary()
            trading_stats = self.money_manager.get_trading_statistics()
            
            runtime = datetime.now() - self.monitoring_start_time
            
            report_data = {
                'monitoring_summary': {
                    'start_time': self.monitoring_start_time.isoformat(),
                    'runtime_seconds': runtime.total_seconds(),
                    'loop_count': self.loop_count,
                    'last_update': self.last_update_time.isoformat()
                },
                'money_status': money_status,
                'portfolio_summary': portfolio_summary,
                'trading_statistics': trading_stats,
                'current_positions': self.portfolio.get_position_details(),
                'settings': {
                    'profit_target': self.profit_target,
                    'stop_loss': self.stop_loss,
                    'max_positions': self.portfolio.max_positions,
                    'max_position_value': self.portfolio.max_position_value
                },
                'generated_at': datetime.now().isoformat()
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            print(f"[저장 완료] 📄 모니터링 보고서: {report_file}")
            
        except Exception as e:
            print(f"[ERROR] 모니터링 보고서 저장 실패: {e}")
    
    def print_final_summary(self, mode: str = "실제 매매"):
        """최종 요약 출력"""
        completion_time = datetime.now()
        runtime = completion_time - self.monitoring_start_time
        
        money_status = self.money_manager.get_portfolio_value()
        trading_stats = self.money_manager.get_trading_statistics()
        
        print(f"\n{'='*100}")
        print(f"🎉 V2.0 단타 매매 완료! [{mode}]")
        print(f"{'='*100}")
        
        print(f"🏁 [최종 결과]")
        print(f"   🕐 완료 시간: {completion_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   ⏱️ 총 운영 시간: {str(runtime).split('.')[0]}")
        print(f"   🔄 총 실행 루프: {self.loop_count}회")
        
        print(f"\n💰 [자금 결과]")
        print(f"   💰 시작 자금: {money_status['initial_capital']:,}원")
        print(f"   💵 최종 자금: {money_status['available_cash']:,}원")
        print(f"   📊 총 손익: {money_status['daily_pnl']:+,}원 ({money_status['daily_return']:+.2f}%)")
        
        if trading_stats['total_sell_trades'] > 0:
            print(f"\n📊 [거래 결과]")
            print(f"   🔄 총 거래: {trading_stats['total_buy_trades']}매수 / {trading_stats['total_sell_trades']}매도")
            print(f"   🟢 수익 거래: {trading_stats['profit_trades']}건")
            print(f"   🔴 손실 거래: {trading_stats['loss_trades']}건")
            print(f"   🎯 최종 승률: {trading_stats['win_rate']:.1f}%")
            
            if trading_stats['profit_trades'] > 0:
                print(f"   📈 평균 수익률: {trading_stats['avg_profit_rate']:+.2f}%")
                print(f"   💰 총 수익금: {trading_stats['total_profit_amount']:+,}원")
        
        print(f"{'='*100}")