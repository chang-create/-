"""
🔥 V3.0 단타 매매 시스템 사용 예시
"""
import asyncio
import os
from datetime import datetime
from integrated_scalping_v3 import ScalpingEngineV3, execute_scalping_loop_v3
from scalping_engine import ensure_token_for_full_trading_day, is_test_mode

async def test_v3_system():
    """V3.0 시스템 테스트"""
    print("🔥 V3.0 단타 매매 시스템 테스트 시작")
    print("=" * 80)
    
    # 테스트 모드 설정
    os.environ['SCALPING_TEST_MODE'] = '1'
    
    try:
        # 1. 토큰 준비
        token = ensure_token_for_full_trading_day()
        
        # 2. V3.0 엔진 초기화
        today = datetime.now().strftime('%Y%m%d')
        log_dir = os.path.join("auto_signals", today, "scalping_v3_test")
        engine = ScalpingEngineV3(log_dir)
        
        # 3. 시스템 헤더 출력
        engine.monitor.print_system_header("테스트 모드")
        
        # 4. 초기 상태 출력
        print("\n📊 [초기 상태]")
        engine.print_status()
        
        # 5. 테스트 루프 실행 (1회만)
        print("\n🧪 [테스트 루프 실행]")
        engine.monitor.print_loop_header(1)
        actions = await execute_scalping_loop_v3(engine, token, 1)
        print(f"✅ 테스트 루프 완료: {actions}건 실행")
        
        # 6. 거래 요약 출력
        engine.monitor.print_trading_summary()
        
        # 7. 최종 상태 출력
        print("\n📊 [최종 상태]")
        engine.print_status(token)
        
        # 8. 보고서 저장
        engine.save_comprehensive_report()
        
        # 9. 최종 요약
        engine.monitor.print_final_summary("테스트 모드")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

async def run_v3_full_system():
    """V3.0 시스템 실제 실행"""
    print("🔥 V3.0 단타 매매 시스템 실제 실행")
    print("=" * 80)
    
    # 실제 모드 설정
    if 'SCALPING_TEST_MODE' in os.environ:
        del os.environ['SCALPING_TEST_MODE']
    
    try:
        # 1. 토큰 준비
        token = ensure_token_for_full_trading_day()
        
        # 2. V3.0 엔진 초기화
        today = datetime.now().strftime('%Y%m%d')
        log_dir = os.path.join("auto_signals", today, "scalping_v3_real")
        engine = ScalpingEngineV3(log_dir)
        
        # 3. 시스템 시작
        engine.monitor.print_system_header("실제 매매")
        
        # 4. 매매 루프 (간단한 예시 - 3회만)
        for loop_count in range(1, 4):
            print(f"\n{'='*60}")
            print(f"🔄 [{loop_count}번째 루프 시작]")
            
            # 루프 헤더
            engine.monitor.print_loop_header(loop_count)
            engine.monitor.update_loop_count()
            
            # 매매 실행
            actions = await execute_scalping_loop_v3(engine, token, loop_count)
            
            # 루프 요약
            engine.monitor.print_trading_summary()
            
            # 다음 루프까지 대기 (실제로는 300초, 테스트는 10초)
            print(f"\n⏳ 다음 루프까지 대기...")
            await asyncio.sleep(10)  # 테스트용 짧은 대기
        
        # 5. 최종 보고서
        engine.save_comprehensive_report()
        engine.monitor.print_final_summary("실제 매매")
        
    except Exception as e:
        print(f"❌ 실행 실패: {e}")
        import traceback
        traceback.print_exc()

def manual_test_components():
    """개별 컴포넌트 수동 테스트"""
    print("🧪 개별 컴포넌트 테스트")
    print("=" * 50)
    
    # 1. 가상 자금 관리 테스트
    print("\n💰 [가상 자금 관리 테스트]")
    from virtual_money_manager import VirtualMoneyManager
    
    money_manager = VirtualMoneyManager(500_000)
    print(f"초기 자금: {money_manager.available_cash:,}원")
    
    # 가상 매수 테스트
    transaction = money_manager.execute_virtual_buy("A005930", "삼성전자", 70000, 100_000)
    if transaction:
        print(f"매수: {transaction.name} {transaction.quantity}주 @{transaction.price:,}원")
        print(f"남은 자금: {money_manager.available_cash:,}원")
        
        # 가상 매도 테스트 (5% 수익)
        sell_price = int(transaction.price * 1.05)
        sell_transaction = money_manager.execute_virtual_sell(transaction, sell_price, "익절")
        if sell_transaction:
            print(f"매도: {sell_transaction.name} @{sell_price:,}원 "
                  f"수익률: {sell_transaction.profit_rate:+.2f}%")
    
    money_manager.print_money_status()
    
    # 2. 포트폴리오 관리 테스트
    print("\n📊 [포트폴리오 관리 테스트]")
    from scalping_portfolio import ScalpingPortfolio
    
    portfolio = ScalpingPortfolio(5, 100_000)
    
    # 포지션 추가 테스트
    success = portfolio.add_position("A005930", "삼성전자", 70000, 1, 1, 1000000)
    print(f"포지션 추가 성공: {success}")
    
    # 재매수 시도 (실패해야 함)
    can_buy, reason = portfolio.can_buy_stock("A005930")
    print(f"재매수 가능: {can_buy} ({reason})")
    
    portfolio.print_portfolio_status()
    
    # 3. 모니터링 시스템 테스트
    print("\n📊 [모니터링 시스템 테스트]")
    from scalping_monitor import ScalpingMonitor
    
    monitor = ScalpingMonitor(portfolio, money_manager)
    monitor.print_system_header("테스트")
    monitor.print_comprehensive_status()
    
    print("\n✅ 모든 컴포넌트 테스트 완료!")

if __name__ == "__main__":
    print("🔥 V3.0 단타 매매 시스템 사용법 예시")
    print("=" * 50)
    print("1️⃣  개별 컴포넌트 테스트")
    print("2️⃣  V3.0 시스템 테스트")
    print("3️⃣  V3.0 실제 실행 (짧은 버전)")
    print("0️⃣  종료")
    
    choice = input("\n선택하세요 (1/2/3/0): ").strip()
    
    if choice == "1":
        manual_test_components()
    elif choice == "2":
        asyncio.run(test_v3_system())
    elif choice == "3":
        asyncio.run(run_v3_full_system())
    elif choice == "0":
        print("👋 종료")
    else:
        print("❌ 잘못된 선택")